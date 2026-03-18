import google.generativeai as genai
import os
from threading import Lock
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_CALL_LOCK = Lock()

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_embedding(text: str, model="models/gemini-embedding-2-preview"):
    """
    Generate embedding for a given text using Gemini.
    """
    if not text:
        return []
    
    # Clean text to avoid issues with newlines or special characters
    text = text.replace("\n", " ")
    
    try:
        # Keep configure+SDK call together so concurrent requests do not mix keys.
        with GEMINI_CALL_LOCK:
            if GEMINI_API_KEY:
                genai.configure(api_key=GEMINI_API_KEY)
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="retrieval_document"
            )
        return result['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []

def get_query_embedding(text: str, api_key: str, model="models/gemini-embedding-2-preview"):
    """
    Generate embedding for a query using Gemini.
    """
    if not text:
        return []
    
    try:
        # Configure Gemini per request instead of relying on global startup state.
        with GEMINI_CALL_LOCK:
            genai.configure(api_key=api_key)
            result = genai.embed_content(
                model=model,
                content=text,
                task_type="retrieval_query"
            )
        return result['embedding']
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return []
