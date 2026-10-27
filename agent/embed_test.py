import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient

load_dotenv()
g = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
res = g.models.embed_content(
    model="gemini-embedding-001",
    contents="CPU above 95% on web instance",
    config=types.EmbedContentConfig(output_dimensionality=768),
)
print("Embedding size:", len(res.embeddings[0].values))

q = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
print("Qdrant connected:", q.get_collections())
