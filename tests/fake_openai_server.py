"""A fake OpenAI-compatible Chat Completions server for wire-level tests.

Runs in a background thread on 127.0.0.1. The agent reaches it over real HTTP through
pydantic-ai's real OpenAI provider (``OPENAI_BASE_URL`` + an API key), so these tests cover
provider selection, API-key handling and message serialization. No real model is involved.

Every request is checked against the rules the real API enforces (valid roles, conversation
doesn't start with the assistant, every tool call answered). Violations get a 400 response
and are recorded in ``errors``, so tests can assert ``server.errors == []``.
"""

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

Handler = Callable[[dict[str, Any]], dict[str, Any]]

_ROLES = {"system", "developer", "user", "assistant", "tool"}


def validate_request(body: dict[str, Any]) -> list[str]:
    """Return the ways ``body`` would be rejected by the real Chat Completions API."""
    problems: list[str] = []
    messages = body.get("messages")
    if not body.get("model"):
        problems.append("missing model")
    if not isinstance(messages, list) or not messages:
        return problems + ["messages must be a non-empty list"]

    conversation = [m for m in messages if m.get("role") not in ("system", "developer")]
    if conversation and conversation[0].get("role") != "user":
        problems.append(f"first non-system message is {conversation[0].get('role')!r}, expected 'user'")

    pending: set[str] = set()
    for i, m in enumerate(messages):
        role = m.get("role")
        if role not in _ROLES:
            problems.append(f"messages[{i}]: invalid role {role!r}")
        if role == "tool":
            call_id = m.get("tool_call_id")
            if call_id not in pending:
                problems.append(f"messages[{i}]: tool result {call_id!r} has no matching assistant tool call")
            pending.discard(call_id)
            continue
        if pending:
            problems.append(f"messages[{i}]: {role} message before tool calls {sorted(pending)} were answered")
            pending.clear()
        if role == "assistant":
            pending = {c["id"] for c in m.get("tool_calls") or []}
    if pending:
        problems.append(f"unanswered tool calls at end of conversation: {sorted(pending)}")

    for t in body.get("tools") or []:
        if t.get("type") != "function" or not t.get("function", {}).get("name"):
            problems.append(f"malformed tool definition: {t}")
    return problems


def text(content: str) -> dict[str, Any]:
    """An assistant reply with plain text."""
    return {"role": "assistant", "content": content}


def tool_call(name: str, args: dict[str, Any], call_id: str | None = None) -> dict[str, Any]:
    """An assistant reply that calls one tool."""
    call = {
        "id": call_id or f"call_{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }
    return {"role": "assistant", "content": None, "tool_calls": [call]}


def output_tool_name(body: dict[str, Any]) -> str:
    """Name of pydantic-ai's structured-output tool in this request."""
    names = [t["function"]["name"] for t in body.get("tools") or []]
    return next(n for n in names if n.startswith("final_result"))


class FakeOpenAIServer:
    """Serve ``handler(request_body) -> assistant message`` as a Chat Completions endpoint.

    ``prompt_tokens`` is reported as usage on every response, so tests can push the
    conversation over ``summarize_config.token_limit``.
    """

    def __init__(self, handler: Handler, prompt_tokens: int = 100) -> None:
        self.handler = handler
        self.prompt_tokens = prompt_tokens
        self.requests: list[dict[str, Any]] = []
        self.auth_headers: list[str | None] = []
        self.errors: list[str] = []
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_address[1]}/v1"

    def __enter__(self) -> "FakeOpenAIServer":
        self._thread.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    def _respond(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        self.requests.append(body)
        problems = validate_request(body)
        if problems:
            self.errors.extend(problems)
            return 400, {"error": {"message": "; ".join(problems), "type": "invalid_request_error"}}
        message = self.handler(body)
        return 200, {
            "id": f"chatcmpl-{len(self.requests)}",
            "object": "chat.completion",
            "created": 0,
            "model": body["model"],
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                }
            ],
            "usage": {
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": 10,
                "total_tokens": self.prompt_tokens + 10,
            },
        }

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 (http.server API)
                if not self.path.endswith("/chat/completions"):
                    self.send_error(404)
                    return
                server.auth_headers.append(self.headers.get("Authorization"))
                length = int(self.headers.get("Content-Length", "0"))
                try:
                    status, payload = server._respond(json.loads(self.rfile.read(length)))
                except Exception as e:  # surface handler bugs to the test instead of hanging
                    server.errors.append(f"handler error: {e!r}")
                    status, payload = 500, {"error": {"message": repr(e), "type": "server_error"}}
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args: Any) -> None:
                pass

        return _Handler
