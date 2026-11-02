"""Demonstrate natural language semantic search in ChromaDB.
"""
from pathlib import Path
import chromadb

CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
recipe_collection = client.get_collection(name="clinical_recipes")

query = "low sodium steamed breakfast for high blood pressure"
print(f"\n[Query] Natural Language Query: '{query}'")
results = recipe_collection.query(
    query_texts=[query],
    n_results=3
)

print("\n--- Top 3 Matches from ChromaDB Vector Search ---")
for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), 1):
    print(f"\n[{i}] {doc}")
