import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
import google.generativeai as genai
import chromadb

from embeddings import get_embedding, get_query_embedding

# Persistence is intentionally removed here so the service can run on free-tier
# hosts like Render without needing a disk-backed ChromaDB volume.

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise SystemExit("GEMINI_API_KEY missing")

genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

SYSTEM_INSTRUCTION = (
    "You are a concise healthcare analysis assistant. Do NOT produce greetings. "
    "Use the provided medical context to answer the user query. "
    "If the context doesn't contain the answer, use your general medical knowledge but prioritize the context. "
    "Always provide a helpful, safe, and concise medical response."
)

model = genai.GenerativeModel(
    "gemini-2.5-flash-lite",
    system_instruction=SYSTEM_INSTRUCTION,
)

def _load_json_file(filename: str):
    file_path = BASE_DIR / filename
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def _build_symptom_document(item: dict) -> str:
    return (
        f"Symptom: {item.get('symptoms', item.get('name', ''))}. "
        f"Primary Advice: {item.get('primary_advice', '')}. "
        f"Healthcare Diet or Advice: {item.get('healthcare_diet_or_advice', '')}. "
        f"Medicine to Take: {item.get('medicine_to_take', '')}. "
        f"When to Visit Doctor: {item.get('when_to_visit_doctor', '')}"
    )

def _build_medicine_document(item: dict) -> str:
    return (
        f"Medicine: {item.get('name', '')}. "
        f"Usage: {item.get('usage', '')}. "
        f"Side Effects: {item.get('side_effects', '')}. "
        f"Dosage: {item.get('dosage', '')}"
    )

def _chunk(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]

def initialize_vector_db():
    """
    Initialize ChromaDB in memory and ingest documents at startup.
    Persistence is removed so the app remains free-tier friendly on Render.
    Every restart rebuilds the vector store from the JSON knowledge base.
    """
    client = chromadb.Client()
    collection = client.get_or_create_collection(name="healthcare")

    symptoms_data = _load_json_file("symptoms.json")
    medicines_data = _load_json_file("medicines.json")

    documents = []
    ids = []
    metadatas = []

    for idx, item in enumerate(symptoms_data):
        doc = _build_symptom_document(item)
        doc_id = f"symptom_{idx}"
        documents.append(doc)
        ids.append(doc_id)
        metadatas.append({
            "type": "symptom",
            "name": item.get("symptoms", item.get("name", f"symptom_{idx}")),
        })

    for idx, item in enumerate(medicines_data):
        doc = _build_medicine_document(item)
        doc_id = f"medicine_{idx}"
        documents.append(doc)
        ids.append(doc_id)
        metadatas.append({
            "type": "medicine",
            "name": item.get("name", f"medicine_{idx}"),
        })

    if not documents:
        logger.warning("No documents found to ingest into in-memory ChromaDB.")
        return client, collection

    # Batched embedding generation keeps startup faster and avoids one-by-one writes.
    embeddings = []
    batch_size = 20
    for doc_batch, id_batch, meta_batch in zip(
        _chunk(documents, batch_size),
        _chunk(ids, batch_size),
        _chunk(metadatas, batch_size),
    ):
        batch_embeddings = []
        for doc, meta in zip(doc_batch, meta_batch):
            if meta["type"] == "symptom":
                batch_embeddings.append(get_embedding(doc))
            else:
                batch_embeddings.append(get_embedding(doc))

        # Skip duplicate re-inserts when the collection already contains these ids.
        try:
            existing = collection.get(ids=id_batch)
            existing_ids = set(existing.get("ids", [])) if existing else set()
        except Exception:
            existing_ids = set()

        new_docs = []
        new_ids = []
        new_embs = []
        new_meta = []
        for doc, doc_id, emb, meta in zip(doc_batch, id_batch, batch_embeddings, meta_batch):
            if doc_id in existing_ids:
                continue
            new_docs.append(doc)
            new_ids.append(doc_id)
            new_embs.append(emb)
            new_meta.append(meta)

        if new_docs:
            collection.add(
                ids=new_ids,
                documents=new_docs,
                embeddings=new_embs,
                metadatas=new_meta,
            )
            embeddings.extend(new_embs)

    logger.info("In-memory ChromaDB initialized with collection 'healthcare'.")
    return client, collection


client, collection = initialize_vector_db()


def _build_prompt(context: str, query: str) -> str:
    return (
        "Answer the user using the following medical context:\n\n"
        f"{context}\n\n"
        f"User Query: {query}\n\n"
        "Return ONLY a valid JSON object with these exact keys:\n"
        "{\n"
        '  "symptoms": "Name of the symptom",\n'
        '  "primary_advice": "What might be happening based on the symptoms",\n'
        '  "healthcare_diet_or_advice": "Dietary recommendations and lifestyle advice",\n'
        '  "medicine_to_take": "Which medicine to take based on the context",\n'
        '  "when_to_visit_doctor": "Warning signs to watch out for"\n'
        "}\n\n"
        "Do not add markdown, bullets, code fences, or extra commentary."
    )


@app.route("/chat", methods=["POST"])
def chat():
    try:
        payload = request.get_json(force=True) or {}
        message = (payload.get("message") or "").strip()

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # The request-scoped key is optional only if your architecture keeps server-side Gemini.
        # For this backend version we still support the existing response format and logic.
        api_key = (payload.get("api_key") or "").strip()
        if api_key:
            genai.configure(api_key=api_key)

        query_embedding = get_query_embedding(message, api_key or GEMINI_API_KEY)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
        )

        context_docs = results.get("documents", [[]])[0] if results else []
        context = "\n\n".join(context_docs) if context_docs else "No specific context found."
        context_data = []
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            for i, doc in enumerate(docs):
                similarity = 1.0
                if results.get("distances") and results["distances"] and len(results["distances"][0]) > i:
                    distance = results["distances"][0][i]
                    similarity = max(0, 1 - distance)
                context_data.append({
                    "text": doc,
                    "similarity": similarity,
                })

        prompt = _build_prompt(context, message)

        if api_key:
            genai.configure(api_key=api_key)

        response = model.generate_content(prompt)
        response_text = (response.text or "").strip()

        return jsonify({
            "response": response_text,
            "context": context_data,
        })
    except Exception as e:
        logger.exception("Error in /chat endpoint")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
