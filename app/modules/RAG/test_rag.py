import asyncio
from app.modules.RAG.embedding import EmbeddingService

async def test_embedding():
    print("Testing OpenAI Embedding Service...")
    service = EmbeddingService()
    
    # Dummy interaction
    vector = await service.generate_interaction_embedding(
        user_query="How do I set up Node.js?",
        ai_response="I can install OpenJS.NodeJS via winget for you.",
        mode_name="mode_chat"
    )

    if vector and len(vector) > 0:
        print("✅ SUCCESS! Embedding Service is working.")
        print(f"Vector Length: {len(vector)} floats")
        print(f"Sample: {vector[:3]}...")
    else:
        print("❌ FAILED! Check your OPENAI_API_KEY in .env")

if __name__ == "__main__":
    asyncio.run(test_embedding())