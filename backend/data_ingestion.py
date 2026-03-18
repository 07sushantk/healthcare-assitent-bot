import json
import os
from endee_client import EndeeClient
from embeddings import get_embedding
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def ingest_data():
    """
    Load JSON data and store embeddings in Endee.
    """
    endee = EndeeClient()
    
    # Load Symptoms
    try:
        with open(BASE_DIR / 'symptoms.json', 'r', encoding='utf-8') as f:
            symptoms_data = json.load(f)
    except FileNotFoundError:
        print("symptoms.json not found. Skipping.")
        symptoms_data = []

    # Load Medicines
    try:
        with open(BASE_DIR / 'medicines.json', 'r', encoding='utf-8') as f:
            medicines_data = json.load(f)
    except FileNotFoundError:
        print("medicines.json not found. Skipping.")
        medicines_data = []

    all_symptom_texts = [
        f"Symptom: {item.get('symptoms', item.get('name', ''))}. "
        f"Primary Advice: {item.get('primary_advice', '')}. "
        f"Diet/Lifestyle: {item.get('healthcare_diet_or_advice', '')}. "
        f"Medicine: {item.get('medicine_to_take', '')}. "
        f"When to Visit Doctor: {item.get('when_to_visit_doctor', '')}" 
        for item in symptoms_data
    ]
    all_medicine_texts = [f"Medicine: {item['name']}. Usage: {item['usage']}. Side Effects: {item['side_effects']}. Dosage: {item['dosage']}" for item in medicines_data]
    
    import google.generativeai as genai
    model_name = "models/gemini-embedding-2-preview"

    all_docs = []
    all_ids = []
    all_embeddings = []
    all_metadatas = []

    print("Generating embeddings in batches to avoid rate limits...")
    import time
    
    # Process Symptoms in batches of 20
    for i in range(0, len(all_symptom_texts), 20):
        batch_texts = all_symptom_texts[i:i+20]
        batch_items = symptoms_data[i:i+20]
        try:
            resp = genai.embed_content(model=model_name, content=batch_texts, task_type="retrieval_document")
            embs = resp['embedding']
            for j, text in enumerate(batch_texts):
                all_docs.append(text)
                all_ids.append(f"symptom_{i+j}")
                all_embeddings.append(embs[j])
                all_metadatas.append({"type": "symptom", "name": batch_items[j].get('symptoms', batch_items[j].get('name', 'Unknown'))})
            time.sleep(2)
        except Exception as e:
            print(f"Failed to embed symptom batch {i}: {e}")

    # Process Medicines in batches of 20
    for i in range(0, len(all_medicine_texts), 20):
        batch_texts = all_medicine_texts[i:i+20]
        batch_items = medicines_data[i:i+20]
        try:
            resp = genai.embed_content(model=model_name, content=batch_texts, task_type="retrieval_document")
            embs = resp['embedding']
            for j, text in enumerate(batch_texts):
                all_docs.append(text)
                all_ids.append(f"medicine_{i+j}")
                all_embeddings.append(embs[j])
                all_metadatas.append({"type": "medicine", "name": batch_items[j]['name']})
            time.sleep(2)
        except Exception as e:
            print(f"Failed to embed medicine batch {i}: {e}")

    if all_docs:
        print(f"Ingesting {len(all_docs)} documents into Endee...")
        endee.add_documents(
            ids=all_ids,
            documents=all_docs,
            embeddings=all_embeddings,
            metadatas=all_metadatas
        )
        print("Ingestion complete.")
    else:
        print("No data to ingest.")

if __name__ == "__main__":
    ingest_data()
