"""Processes message history for the agent, filtering messages based on token usage.

If message_history is set and not empty, a new system prompt is not generated —
we assume the existing message history includes a system prompt.
"""

import logging

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart

logger = logging.getLogger(__name__)

SUMMARY_PREFIX = "Summary of the conversation so far: "


async def history_processor(
    total_tokens: int, messages: list[ModelMessage], selected_provider: str
) -> list[ModelMessage]:
    """Summarize ``messages`` when ``total_tokens`` exceeds ``summarize_config.token_limit``.

    ``selected_provider`` is the main agent's provider. It is kept for backward
    compatibility; the summarizer now uses its own provider and API key.
    """
    if not messages:
        return []

    from .config import apply_api_key, summarize_config

    if not summarize_config.ai_model or not summarize_config.token_limit:
        logger.info("Skipping history processing: summarizer model or token limit not configured.")
        return messages

    if total_tokens <= summarize_config.token_limit:
        return messages

    if not apply_api_key(summarize_config.model_api, summarize_config.model_provider):
        logger.warning(
            "Skipping history summarization: no API key for summarizer provider '%s'. "
            "Call summarize_config.set_model_api_key() or set the provider's env var.",
            summarize_config.model_provider,
        )
        return messages

    return await summarize_old_messages(messages)


async def summarize_old_messages(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Replace ``messages`` with a single user message holding a short summary."""
    from .config import summarize_config
    from .exceptions import HistoryProcessorError

    try:
        summarize_agent = Agent(
            model=summarize_config.ai_model,
            instructions=(
                "Summarize the entire conversation so far in as few tokens as possible. "
                "Do not exceed a paragraph or 50 words."
            ),
        )
        result = await summarize_agent.run(message_history=messages)
    except Exception as e:
        raise HistoryProcessorError("History summarization failed.") from e

    summary = result.output.strip()
    if not summary:
        return []
    # A user message (not a model response) so the history is valid for every provider.
    return [ModelRequest(parts=[UserPromptPart(content=SUMMARY_PREFIX + summary)])]
