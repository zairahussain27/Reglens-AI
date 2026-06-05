import chromadb
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid

# Replace these with your values
import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Open local ChromaDB
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_collection("regulations")

# Connect to Qdrant
qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

# Read everything from Chroma
data = collection.get(
    include=["documents", "metadatas", "embeddings"]
)

points = []

for i in range(len(data["ids"])):
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=data["embeddings"][i],
            payload={
                "document": data["documents"][i],
                "metadata": data["metadatas"][i]
            }
        )
    )

print(f"Uploading {len(points)} vectors...")

qdrant.upsert(
    collection_name="regulations",
    points=points
)

print("Migration completed successfully!")