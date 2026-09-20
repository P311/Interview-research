import os

from dotenv import load_dotenv

load_dotenv()

# Any OpenAI-compatible chat completions endpoint - DeepSeek directly, OpenRouter
# (one key, swap `model` across DeepSeek/Qwen/Gemini/whichever is cheapest), Together,
# Groq, etc. No code changes needed to switch, only these three env vars.
LLM_BASE_URL = os.environ.get("JOBAGENT_LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.environ.get("JOBAGENT_LLM_MODEL", "deepseek-v4-flash")
LLM_API_KEY = os.environ.get("JOBAGENT_LLM_API_KEY", "")

# Dedicated search API for the research workers - decoupled from the LLM provider,
# since none of the cheap chat models offer a hosted web-search tool. https://tavily.com
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

DB_PATH = os.environ.get("JOBAGENT_DB_PATH", "data/applications.db")

# The public demo sets this: a shared host must not accumulate strangers' pasted
# resumes in a persistent file, and dedup across unrelated visitors' inputs isn't
# meaningful anyway.
DISABLE_PERSISTENCE = os.environ.get("DISABLE_PERSISTENCE", "false").lower() == "true"

# rapidfuzz token_sort_ratio (0-100) above which two (company, title) pairs count as the same application
DEDUP_FUZZY_THRESHOLD = int(os.environ.get("JOBAGENT_DEDUP_THRESHOLD", "90"))
