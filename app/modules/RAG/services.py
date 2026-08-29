from app.modules.RAG.embedding import EmbeddingService
from app.modules.RAG.vector_store import QdrantService
from app.modules.RAG.fast_extractor import FactExtractorService

fact_extractor = FactExtractorService()
embedding_service = EmbeddingService()
qdrant_service = QdrantService()

async def add_memory_service(fact_data: list[str], user_id: str, mode_name: str)->str:
    print("RAG pipeline task started")
    try:
        if not fact_data:
            return "No facts provided to save."
        saved_ids = []
        print(fact_data)

        for fact in fact_data:
            vector = await embedding_service.generate_interaction_embedding(
                fact_data=fact,
                mode_name=mode_name
            )
                
            if vector:
                point_id = await qdrant_service.upsert_embedding(
                    user_id=user_id,
                    vector_data=vector,
                    fact_data =fact,
                    mode_name=mode_name
                )
                saved_ids.append(point_id)
        
        return f"Success: Saved {len(saved_ids)} new memories to long-term storage."
    except Exception as e:
        error_msg = f"Error executing RAG pipeline task: {e}"
        print(f"❌ [RAG PIPELINE ERROR] {error_msg}")
        return error_msg 
    
async def search_memory_service(
        user_id:str, 
        query_text: str, 
        mode_name: str, 
        limit: int = 5, 
        score_threshold: float = 0.5
        )->str:
    try:
        query_vector = await embedding_service.generate_interaction_embedding(
            fact_data=query_text,
            mode_name=mode_name
        )
            
        if not query_vector:
            return "Error: Failed to generate query vector."

        search_results = await qdrant_service.search_embedding(
            user_id=user_id,
            vector=query_vector,
            mode_name=mode_name,
            limit=limit,
            score_threshold=score_threshold
        )
        response = "Top search results:\n"
        for result in search_results:
            response += f"- {result['fact_data']} (Score: {result['score']})(id: {result['id']})\n"
        return response

    except Exception as e:
        print(f"❌ [RAG SEARCH ERROR] Failed to execute search memory service: {e}")
        return "Error: Failed to execute search memory service."

async def update_memory_services(
            user_id: str, 
            point_id: str, 
            update_fact_data: str,
            mode_name: str)->str:
    try:
        updated_vector = await embedding_service.generate_interaction_embedding(
            fact_data=update_fact_data,
            mode_name=mode_name
        )
        if not updated_vector:
            return "Error: Failed to generate new embedding. Memory not updated."
        
        is_updated = await qdrant_service.update_embedding(
            user_id=user_id,
            point_id=point_id,
            updated_vector_data=updated_vector,
            update_fact_data=update_fact_data,
            mode_name=mode_name
        )

        if is_updated:
            return f"Success: Memory {point_id} has been updated."
        else:
            return f"Error: Database failed to update memory {point_id}."
    except Exception as e:
        print(f"❌ [RAG UPDATE ERROR] Failed to execute update memory service: {e}")
        return f"Error: An unexpected exception occurred - {str(e)}"

async def delete_memory_service(
        user_id: str,
        point_id: str,
        mode_name: str) -> str:
    try:
        is_deleted = await qdrant_service.delete_embedding(
            user_id=user_id,
            point_id=point_id,
            mode_name=mode_name
        )

        if is_deleted:
            return f"Success: Memory {point_id} has been deleted."
        else:
            return f"Error: Database failed to delete memory {point_id}."
    except Exception as e:
        print(f"❌ [RAG DELETE ERROR] Failed to execute delete memory service: {e}")
        return f"Error: An unexpected exception occurred - {str(e)}"