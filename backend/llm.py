
import os
import time
from pathlib import Path

from dotenv import load_dotenv
import litellm
from litellm import completion
from litellm.caching import Cache


# Load environment configuration
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Load the API key pool
API_KEYS = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

MODEL = "gemini/gemini-3.5-flash-lite"

# Enable LiteLLM built-in local caching
litellm.cache = Cache(type="local")


class AllProvidersUnavailable(Exception):
    pass


def is_retryable_error(error):
    status = getattr(error, "status_code", None)

    if status is None:
        status = getattr(
            getattr(error, "response", None),
            "status_code",
            None
        )

    if status in (429, 500, 502, 503):
        return True

    message = str(error).lower()

    return "quota" in message or "rate limit" in message


def generate_reply(messages, simulated_failures=None):
    if len(API_KEYS) < 2:
        raise RuntimeError("At least two API keys are required")

    simulated_failures = simulated_failures or {}

    for index, api_key in enumerate(API_KEYS):

        key_id = f"key_{index + 1}"

        # Simulate failures only when explicitly enabled
        if os.getenv("ENABLE_FAILURE_SIMULATION", "").lower() == "true":
            simulated_status = simulated_failures.get(
                key_id,
                simulated_failures.get("*")
            )

            if simulated_status in (429, 500, 502, 503):
                print(f"{key_id} simulated failure: {simulated_status}")
                continue

        start_time = time.perf_counter()

        try:
            response = completion(
                model=MODEL,
                messages=messages,
                api_key=api_key,
                caching=True
            )

            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            hidden = getattr(response, "_hidden_params", {}) or {}
            cache_hit = bool(hidden.get("cache_hit", False))

            usage = response.usage

            reply = response.choices[0].message.content

            return {
                "reply": reply,
                "model": MODEL,
                "resolution_source": (
                    "LLM_CACHE" if cache_hit
                    else "LIVE_INFERENCE"
                ),
                "latency_ms": latency_ms,
                "input_tokens": usage.prompt_tokens or 0,
                "output_tokens": usage.completion_tokens or 0,
                "key_id": None if cache_hit else key_id,
                "fallback_attempts": 0 if cache_hit else index
            }

        except Exception as error:
            if not is_retryable_error(error):
                raise

            print(f"{key_id} failed: {error}")

    raise AllProvidersUnavailable("all providers unavailable")
