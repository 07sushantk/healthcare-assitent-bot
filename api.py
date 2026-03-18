from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from rag import rag_pipeline
from endee_client import EndeeClient
from embeddings import get_query_embedding

app = FastAPI()
endee = EndeeClient()

class ChatRequest(BaseModel):
    message: str
    api_key: str

@app.post("/rag")
async def chat(request: ChatRequest):
    try:
        if not request.api_key.strip():
            raise HTTPException(status_code=400, detail="API key is required")

        # Use the caller-provided Gemini key only for this request.
        # 1. Get embedding for the query to return context to the frontend
        query_emb = get_query_embedding(request.message, request.api_key)
        
        # 2. Search Endee to get the similarity scores and context
        search_results = endee.search(query_emb, n_results=3)
        
        context_data = []
        if search_results and 'documents' in search_results and search_results['documents']:
            docs = search_results['documents'][0]
            # distances are returned by chromadb (lower is more similar for L2, but exact metric depends on config)
            # We'll just pass back the text for the UI to show
            for i, doc in enumerate(docs):
                similarity = 1.0 # Placeholder since chroma might return distances not cosine similarity directly
                if 'distances' in search_results and search_results['distances'] and len(search_results['distances'][0]) > i:
                    distance = search_results['distances'][0][i]
                    # convert distance to a mock similarity score between 0 and 1 for the UI if needed
                    similarity = max(0, 1 - distance) 
                    
                context_data.append({
                    "text": doc,
                    "similarity": similarity
                })

        # 3. Call the actual RAG pipeline to get the AI response
        response_text = await rag_pipeline(request.message, api_key=request.api_key)
        
        return {
            "response": response_text,
            "context": context_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /rag endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
