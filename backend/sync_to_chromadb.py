"""Sync patient profiles, lab results, and recipes from SQL/Knowledge into ChromaDB.
"""
from pathlib import Path
import sys

# Ensure backend package can be imported
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import chromadb
from app.db import init_engine, get_session, User, Profile, LabResult
from app import knowledge

CHROMA_PATH = BACKEND_DIR / "chroma_db"


def sync():
    print(f"Connecting to persistent ChromaDB at: {CHROMA_PATH}")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    patient_collection = client.get_or_create_collection(name="patient_records")
    lab_collection = client.get_or_create_collection(name="lab_history")
    recipe_collection = client.get_or_create_collection(name="clinical_recipes")

    # Initialize SQL
    init_engine()
    session = next(get_session())

    # --- 1. SYNC PATIENT PROFILES FROM SQL ---
    profiles = session.query(Profile).all()
    print(f"\n[1/3] Syncing {len(profiles)} patient profiles from SQL...")
    for p in profiles:
        user = p.user
        conditions = ", ".join(p.data.get("conditions", []))
        medicines = ", ".join(p.data.get("medicines", []))
        doc_text = (
            f"Patient ID: {p.user_id}, Name: {user.name}, Age: {p.data.get('age', 'N/A')}, "
            f"Sex: {p.data.get('sex', 'N/A')}, Region: {p.data.get('state', 'N/A')}, "
            f"Diet: {p.data.get('diet_type', 'N/A')}. "
            f"Diagnosed chronic conditions: {conditions}. "
            f"Active medications: {medicines}."
        )
        patient_collection.upsert(
            ids=[f"profile_{p.user_id}"],
            documents=[doc_text],
            metadatas=[{
                "user_id": p.user_id,
                "email": user.email,
                "type": "patient_profile"
            }]
        )
    print("[OK] Successfully stored profiles in ChromaDB collection 'patient_records'")

    # --- 2. SYNC LAB RESULTS FROM SQL ---
    labs = session.query(LabResult).all()
    print(f"\n[2/3] Syncing {len(labs)} lab results from SQL...")
    for lab in labs:
        doc_text = f"Patient {lab.user_id} lab report: {lab.kind.upper()} value is {lab.value} recorded on {lab.taken_on}."
        lab_collection.upsert(
            ids=[f"lab_{lab.id}"],
            documents=[doc_text],
            metadatas=[{
                "user_id": lab.user_id,
                "test": lab.kind,
                "value": float(lab.value),
                "date": str(lab.taken_on)
            }]
        )
    print("[OK] Successfully stored lab results in ChromaDB collection 'lab_history'")

    # --- 3. SYNC CLINICAL RECIPES ---
    k = knowledge.get()
    print(f"\n[3/3] Syncing {len(k.dishes)} clinical recipes...")
    dish_ids, dish_docs, dish_meta = [], [], []
    for dish_id, dish in k.dishes.items():
        nutrients = dish.get("nutrients", {})
        doc_text = (
            f"Recipe: {dish.get('name', dish_id)}. "
            f"Diet: {dish.get('diet', 'veg')}. Meal slot: {dish.get('slot', 'main')}. "
            f"Zones: {', '.join(dish.get('zones', []))}. "
            f"Tags: {', '.join(dish.get('tags', []))}. "
            f"Nutrition: {nutrients.get('energy_kcal', 0)} kcal, "
            f"Sodium: {nutrients.get('sodium_mg', 0)} mg, "
            f"Potassium: {nutrients.get('potassium_mg', 0)} mg, "
            f"Carbs: {nutrients.get('carb_g', 0)} g, "
            f"Protein: {nutrients.get('protein_g', 0)} g, "
            f"Fiber: {nutrients.get('fiber_g', 0)} g."
        )
        dish_ids.append(f"dish_{dish_id}")
        dish_docs.append(doc_text)
        dish_meta.append({
            "dish_id": dish_id,
            "diet": dish.get("diet", "veg"),
            "slot": dish.get("slot", "main")
        })

    # Batch upsert to ChromaDB in chunks of 50
    batch_size = 50
    for i in range(0, len(dish_ids), batch_size):
        recipe_collection.upsert(
            ids=dish_ids[i:i + batch_size],
            documents=dish_docs[i:i + batch_size],
            metadatas=dish_meta[i:i + batch_size]
        )
    print(f"[OK] Successfully stored all {len(dish_ids)} recipes in ChromaDB collection 'clinical_recipes'")

    print("\n" + "=" * 50)
    print("ALL DATA FROM SQL & RECIPES STORED IN CHROMADB!")
    print("ChromaDB Directory:", CHROMA_PATH)
    print("=" * 50)


if __name__ == "__main__":
    sync()
