from app.modules.RAG.embedding import EmbeddingService
from app.modules.RAG.vector_store import QdrantService
from app.modules.RAG.fast_extractor import FactExtractorService

fact_extractor = FactExtractorService()
embedding_service = EmbeddingService()
qdrant_service = QdrantService()

async def rag_pipeline_task(user_prompt: str, response: str, user_id: str, mode_name: str):
    print("RAG pipeline task started")
    try:
        facts = await fact_extractor.extract_facts(user_prompt, response)

        if not facts:
            return
    
        print(facts)

        # Step A: Get embedding vector from Gemini
        for fact in facts:
            vector = await embedding_service.generate_interaction_embedding(
                user_query=user_prompt,
                ai_response=fact,
                mode_name=mode_name
            )
                
                # Step B: Upsert vector to Qdrant if embedding succeeded
            if vector:
                await qdrant_service.upsert_embedding(
                    user_id=user_id,
                    vector_data=vector,
                    user_query=user_prompt,
                    ai_response=fact,
                    mode_name=mode_name
                )
    except Exception as e:
        print(f"❌ [RAG PIPELINE ERROR] Error executing RAG pipeline task: {e}")