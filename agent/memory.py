import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

load_dotenv()
COLLECTION = "incident_memory"
DIM = 768

g = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
q = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))


def embed(text: str) -> list[float]:
    res = g.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=DIM),
    )
    return res.embeddings[0].values


def init_collection():
    if not q.collection_exists(COLLECTION):
        q.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )


def add_incident(pid, alert, root_cause, resolution, outcome):
    q.upsert(COLLECTION, points=[PointStruct(
        id=pid,
        vector=embed(alert),
        payload={"alert": alert, "root_cause": root_cause,
                 "resolution": resolution, "outcome": outcome},
    )])


def search_incidents(alert: str, limit: int = 3):
    res = q.query_points(COLLECTION, query=embed(alert), limit=limit)
    return [(p.score, p.payload) for p in res.points]


SEED = [
    ("EC2 CPU above 95 percent, website slow", "Instance undersized for traffic", "Changed instance_type from t3.micro to t3.small", "success"),
    ("EC2 CPU above 90 percent during traffic spike", "Traffic burst on a single instance", "Moved to t3.medium and added Auto Scaling", "success"),
    ("5xx errors rising on load balancer", "Backend instance out of memory", "Increased instance size and restarted service", "success"),
    ("Monthly AWS bill increased 40 percent", "Idle oversized instances left running", "Right-sized instance type and removed idle resources", "success"),
    ("Disk usage above 90 percent on web server", "Logs filling the volume", "Increased EBS volume size to 30 GB", "success"),
    ("RDS connections maxed out", "Connection leak in the app", "Raised max_connections, fix needed in app", "partial"),
    ("EC2 status check failed", "Underlying host issue", "Instance replaced via Auto Scaling", "success"),
    ("Latency high but CPU normal", "Wrong diagnosis, issue was network", "Increasing instance size did not help", "failed"),
]

if __name__ == "__main__":
    init_collection()
    for i, (a, r, f, o) in enumerate(SEED, start=1):
        add_incident(i, a, r, f, o)
    print("Seeded", len(SEED), "incidents")
    for score, p in search_incidents("web server CPU at 97 percent"):
        print(round(score, 3), "|", p["resolution"], "|", p["outcome"])
