import os, json, time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=60000),
)
MODELS = os.getenv(
    "GEMINI_MODELS",
    "gemini-flash-lite-latest,gemini-3.1-flash-lite,gemini-3.5-flash-lite,"
    "gemini-3.5-flash,gemini-3.6-flash,gemini-3.7-flash",
).split(",")


def ask_json(prompt: str, per_model_retries: int = 2) -> dict:
    last = None
    for model in MODELS:
        for i in range(per_model_retries):
            try:
                res = _client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                print(f"[llm] used {model}")
                return json.loads(res.text)
            except Exception as e:
                last = e
                if "429" in str(e) or "404" in str(e):
                    break  # quota khatam ya model nahi mila, agle model pe jao
                time.sleep(10 * (i + 1))
    raise last
