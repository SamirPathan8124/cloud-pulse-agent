import os, json, time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.8-flash"


def ask_json(prompt: str, retries: int = 6) -> dict:
    for i in range(retries):
        try:
            res = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            return json.loads(res.text)
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(10 * (i + 1))
