import chromadb
from chromadb.config import Settings
import os

class EndeeClient:
    def __init__(self, path="./endee_db"):
        """
        Initialize the Endee (ChromaDB) client.
        """
        self.client = chromadb.PersistentClient(path=path)
        self.collection_name = "health_data"
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def add_documents(self, ids, documents, embeddings, metadatas=None):
        """
        Add documents and their embeddings to the collection.
        """
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search(self, query_embedding, n_results=3):
        """
        Search for the top N results based on the query embedding.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results
