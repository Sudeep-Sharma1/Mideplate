"""Inspect all stored collections and documents in ChromaDB.
"""
from pathlib import Path
import chromadb

CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"
client = chromadb.PersistentClient(path=str(CHROMA_PATH))

print("\n" + "=" * 60)
print("CHROMADB STORED COLLECTIONS & COUNTS:")
print("=" * 60)

for col in client.list_collections():
    print(f"\n[Collection] '{col.name}' -> Total Stored: {col.count()} documents")
    sample = col.peek(limit=1)
    if sample and sample.get("documents"):
        print(f" Sample Data: {sample['documents'][0][:120]}...")

print("\n" + "=" * 60)
