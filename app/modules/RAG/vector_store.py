import uuid
from qdrant_client import AsyncQdrantClient, models
from app.core.config import settings

class QdrantService:
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_ENDPOINT,
            api_key=settings.QDRANT_API_KEY
        )
        self.collection_name = "kemo_memory"
        self.vector_size = 3072

    async def ensure_collection_exists(self)->None:
        exists = await self.client.collection_exists(self.collection_name)

        if not exists:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE)
            )
            await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="user_id",
            field_schema=models.PayloadSchemaType.KEYWORD
        )

    async def upsert_embadding(self, user_id: str, 
        vector_data: list[float], 
        user_query: str, 
        ai_response: str, 
        mode_name: str)->bool:
        try:
            await self.ensure_collection_exists()
            point_id=str(uuid.uuid4())
            payload={
                "user_id": str(user_id),
                "mode_name": mode_name,
                "query": user_query,
                "response": ai_response
            }

            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector_data,
                        payload=payload,
                    )
                ]
            )
            return True
        except Exception as e:
            print(f"[QDRANT ERROR] Upsert failed: {e}")
            return False