from qdrant_client import AsyncQdrantClient, models
from google import genai
from app.core.config import settings
from app.modules.RAG.query_transformer import QueryTransformerService

class VectorSearchService:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-embedding-001"

        self.qdrant_client = AsyncQdrantClient(
            url=settings.QDRANT_ENDPOINT,
            api_key=settings.QDRANT_API_KEY
        )
        self.collection_name = "kemo_memory"
        self.query_transformer = QueryTransformerService()

    async def search_similar_memories(
        self, 
        user_id: str, 
        query: str, 
        mode_name: str, # <-- Added mode_name parameter
        limit: int = 3, 
        score_threshold: float = 0.65
    ) -> str:
        """
        Embeds the query and searches Qdrant strictly filtered by user_id AND mode_name.
        """
        try:
            # 1. Generate search vector
            transformed_query = await self.query_transformer.transform_query(query)
            print(f"[RAG SEARCH] Transformed query: {transformed_query}")
            response = await self.gemini_client.aio.models.embed_content(
                model=self.model,
                contents=transformed_query,
                config={"task_type": "RETRIEVAL_QUERY"}
            )
            query_vector = response.embeddings[0].values # type: ignore

           # 2. Search Qdrant using the NEW query_points API
            qdrant_response = await self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_vector, # Pass the raw vector array here
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
                with_payload=True
            )

            # 3. In the new API, the actual hits are nested inside the '.points' attribute
            search_results = qdrant_response.points 

            if not search_results:
                return ""
            print(f"[RAG SEARCH] Found {search_results} results for mode '{mode_name}'")
            # 3. Format results
            memory_blocks = []
            for hit in search_results:
                past_query = hit.payload.get("query", "") #type: ignore
                past_response = hit.payload.get("response", "") #type: ignore
                memory_blocks.append(f"- User previously said: {past_query}\n  Kemo replied: {past_response}")

            return "\n".join(memory_blocks)

        except Exception as e:
            print(f"[RAG SEARCH ERROR] Failed to fetch memory for mode '{mode_name}': {e}")
            return ""