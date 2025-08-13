"""
Example: Setting up summarization config for ClickHouseAgent
"""

from agent.config import summarize_config

# --- 1. Setup summarization config using methods ---
summarize_config.set_ai_model("openai:gpt-3.5-turbo")
summarize_config.set_token_limit(1000)  # Set your desired token threshold
# If your summarizer needs an API key, set it here:
# summarize_config.set_model_api_key("openai", "your-openai-api-key")

print("Summarization config set:")
print("  ai_model:", summarize_config.ai_model)
print("  token_limit:", summarize_config.token_limit)
# print("  OPENAI_API_KEY:", summarize_config.model_api.OPENAI_API_KEY)
