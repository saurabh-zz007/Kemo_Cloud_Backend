from google import genai
from google.genai import types
from app.core.config import settings
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Document

class EmbeddingService:
    def __init__(self):
        # Requires a Google Gemini API key in your .env file
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-embedding-001"


    async def generate_interaction_embedding(self, fact_data: str, mode_name: str) -> list[float]:
        print(f"\n--- [RAG] Starting embedding for: {mode_name} ---")

        combined_text = (
            f"[Mode: {mode_name}]\n"
            f"facts: {fact_data}"
        )

        try:
            # Use client.aio for asynchronous requests
            response = await self.client.aio.models.embed_content(
                model=self.model,
                contents=combined_text,
            )
            
            # The SDK returns the embeddings here
            vector = response.embeddings[0].values #type: ignore
            
            return vector  #type: ignore
            
        except Exception as e:
            print(f"\n[RAG ERROR] Embedding generation failed: {e}\n")
            return []