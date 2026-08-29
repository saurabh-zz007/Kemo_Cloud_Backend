from genericpath import exists
import uuid
from qdrant_client import AsyncQdrantClient, models
from app.core.config import settings
import datetime
from typing import Optional
class QdrantService:
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_ENDPOINT,
            api_key=settings.QDRANT_API_KEY
        )
        self.collection_name = "kemo_memory"
        self.vector_size = 3072

    async def ensure_collection_exists(self) -> None:
        exists = await self.client.collection_exists(self.collection_name)

    # 1. Create collection if it doesn't exist
        if not exists:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size, 
                    distance=models.Distance.COSINE
                )
        )

    # 2. Ensure payload indexes are created once (Qdrant ignores if already present)
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="user_id",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="mode_name",
            field_schema=models.PayloadSchemaType.KEYWORD
        )
# READ OPERATION: Inserting & Updating ;-)
    async def upsert_embedding(
        self, 
        user_id: str, 
        vector_data: list[float], 
        fact_data: str,
        mode_name: str)->Optional[str]:
        try:
            await self.ensure_collection_exists()
            point_id=str(uuid.uuid4())
            payload={
                "user_id": str(user_id),
                "mode_name": mode_name,
                "fact_data": fact_data,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
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
            return point_id
        except Exception as e:
            print(f"[QDRANT ERROR] Upsert failed: {e}")
            return None
        
    async def update_embedding(
            self, 
            user_id: str, 
            point_id: str,
            updated_vector_data: list[float], 
            update_fact_data: str,
            mode_name: str
            )->bool:
        try:
            await self.ensure_collection_exists()
            payload={
                "user_id": str(user_id),
                "mode_name": mode_name,
                "fact_data": update_fact_data,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id, 
                        vector=updated_vector_data,
                        payload=payload,
                    )
                ],
                update_mode=models.UpdateMode.UPDATE_ONLY
            )
            return True
        except Exception as e:
            print(f"[QDRANT ERROR] Update failed: {e}")
            return False

#Retrival Operations: Read & search :->
    async def search_embedding(
            self,
            user_id: str,
            vector: list[float],
            mode_name: str,
            limit: int = 5,
            score_threshold: float = 0.5
    )->list[dict]:
        try:
            await self.ensure_collection_exists()
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=str(user_id))
                        ),
                        models.FieldCondition(
                            key="mode_name",
                            match=models.MatchValue(value=str(mode_name))
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold
            )
            if not response or not response.points:
                return []
            memory_blocks = []

            for hit in response.points:
                memory_blocks.append({
                    "id": str(hit.id),
                    "score": hit.score,
                    "fact_data": hit.payload.get("fact_data", "") if hit.payload else "",  # Keep key consistent with upsert
                    "created_at": hit.payload.get("created_at", "") if hit.payload else "",
                    "updated_at": hit.payload.get("updated_at", "") if hit.payload else ""
                })
            print(f"[QDRANT SEARCH] Found {len(memory_blocks)} results for mode '{mode_name}'")
            return memory_blocks
        
        except Exception as e:
            print(f"[RAG SEARCH ERROR] Failed to fetch memory for mode '{mode_name}': {e}")
            return []

    async def read_embedding(
            self,
            user_id: str,
            point_id: str,
            mode_name: str
    )->Optional[dict]:
        try:
            await self.ensure_collection_exists()
            response = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True
            )
            if not response:
                return None
            hit = response[0]
            if not hit.payload:
                return None
            if hit.payload.get("user_id") != user_id or hit.payload.get("mode_name") != mode_name:
                print(f"[SECURITY ALARM] User {user_id} attempted to read memory {point_id} belonging to another scope.")
                return None
            return {
                "id": str(hit.id),
                "fact_data": hit.payload.get("fact_data", "") if hit.payload else "",
                "created_at": hit.payload.get("created_at", "") if hit.payload else "",
                "updated_at": hit.payload.get("updated_at", "") if hit.payload else ""
            }
        except Exception as e:
            print(f"[RAG RETRIEVE ERROR] Failed to retrieve memory for mode '{mode_name}': {e}")
            return None

#Forget Opperation: Delete :-/
    async def delete_embedding(
            self,
            user_id: str,
            point_id: str,
            mode_name: str,
    )->bool:
        try:
            await self.ensure_collection_exists()
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.HasIdCondition(has_id=[str(point_id)]),
                            models.FieldCondition(
                                key="user_id",
                                match=models.MatchValue(value=str(user_id)),
                            ),
                            models.FieldCondition(
                                key="mode_name",
                                match=models.MatchValue(value=str(mode_name)),
                            )
                        ],
                    )
                )
            )
            print(f"[QDRANT DELETE] Memory {point_id} deleted successfully.")
            return True
        except Exception as e:
            print(f"[QDRANT ERROR] Delete failed: {e}")
            return False
