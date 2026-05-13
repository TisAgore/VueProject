import random
import time

from openai import RateLimitError


def call_with_retry(client, kwargs: dict, max_retries: int = 3, base_delay: float = 2.0):
    """Вызывает chat completions с exponential backoff при rate limit провайдера."""

    attempt = 0

    while True:
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as e:
            attempt += 1
            if attempt > max_retries:
                raise

            retry_after = None
            if hasattr(e, "response") and e.response is not None:
                retry_after_raw = e.response.headers.get("Retry-After")
                if retry_after_raw:
                    try:
                        retry_after = float(retry_after_raw)
                    except ValueError:
                        pass

            if retry_after:
                wait = retry_after + random.uniform(0.5, 1.5)
            else:
                wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)

            print(f"   429 Rate limit - попытка {attempt}/{max_retries}, жду {wait:.1f}s...")
            time.sleep(wait)
