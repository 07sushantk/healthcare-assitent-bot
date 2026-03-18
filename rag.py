import os
import asyncio
from endee_client import EndeeClient
from embeddings import get_query_embedding
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize Endee Client
endee = EndeeClient()

SYSTEM_INSTRUCTION = (
    "You are a concise healthcare analysis assistant. Do NOT produce greetings. "
    "Use the provided medical context to answer the user query. "
    "If the context doesn't contain the answer, use your general medical knowledge but prioritize the context. "
    "Always provide a helpful, safe, and concise medical response."
)

GEMINI_GENERATION_LOCK = asyncio.Lock()

async def rag_pipeline(query: str, api_key: str = None, img: Image.Image = None) -> str:
    """
    RAG Pipeline:
    1. Convert query to embedding
    2. Search top 3 results from Endee
    3. Combine retrieved context with user query
    4. Send to Gemini model
    5. Return final response
    """
    # 1. Get embedding for the query
    if api_key:
        genai.configure(api_key=api_key)
    query_emb = get_query_embedding(query, api_key or GEMINI_API_KEY)
    
    # 2. Search Endee
    search_results = endee.search(query_emb, n_results=3)
    
    # 3. Extract context
    context_list = search_results.get('documents', [[]])[0]
    context = "\n\n".join(context_list) if context_list else "No specific context found."
    
    # 4. Construct Prompt
    prompt = (
        "Answer the user using the following medical context:\n\n"
        f"{context}\n\n"
        f"User Query: {query}\n\n"
        "Return ONLY a valid JSON object with this exact structure and exact keys:\n\n"
        "{\n"
        '  "symptoms": "Name of the symptom",\n'
        '  "primary_advice": "What might be happening based on the symptoms",\n'
        '  "healthcare_diet_or_advice": "Dietary recommendations and lifestyle advice",\n'
        '  "medicine_to_take": "Which medicine to take based on the context",\n'
        '  "when_to_visit_doctor": "Warning signs to watch out for"\n'
        "}\n\n"
        "Use the retrieved medical context as the primary source. "
        "If the context already contains these fields, preserve that meaning closely instead of rewriting them into markdown. "
        "Do not add markdown, bullet points, code fences, or extra commentary."
    )
    
    # 5. Generate Response
    try:
        # Configure and call Gemini together so request-scoped keys do not bleed across users.
        async with GEMINI_GENERATION_LOCK:
            if api_key:
                genai.configure(api_key=api_key)
            current_model = genai.GenerativeModel(
                "gemini-2.5-flash-lite",
                system_instruction=SYSTEM_INSTRUCTION,
            )
            if img:
                response = await current_model.generate_content_async([prompt, img])
            else:
                response = await current_model.generate_content_async(prompt)
        
        return response.text.strip()
    except Exception as e:
        print(f"Error in RAG pipeline: {e}")
        return "I'm sorry, I encountered an error while processing your request."
