from openai import AsyncOpenAI
from app.core.config import settings

class QueryTransformerService:
    def __init__(self):
        # Groq client initialization
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "llama-3.1-8b-instant"

        self.system_prompt = """
        You are an elite Query Transformation agent for a RAG memory retrieval pipeline.
        Your job is to convert a user's question or prompt into a hypothetical declarative fact statement that would exist in a vector memory store.

        EXAMPLES:
        - User Query: "What is my name?" -> Transformed Query: "The user's name is"
        - User Query: "What college do I go to?" -> Transformed Query: "The user attends university at"
        - User Query: "Which tech stack am I using?" -> Transformed Query: "The user's technology stack and programming languages"
        - User Query: "Tell me about my recent project." -> Transformed Query: "The user's recent project details and architecture"

        RULES:
        1. Output ONLY the transformed hypothetical fact statement/search phrase.
        2. Keep it concise, focused, and declarative.
        3. Do NOT include conversational filler, explanations, or quotes.
        4. If the query is already a clear statement, return it unchanged.
        """

    async def transform_query(self, query: str) -> str:
        """
        Rewrites the incoming user query using Groq Llama 3.1 into a vector-searchable fact query.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"User Query: {query}"}
                ],
                temperature=0.0
            )

            transformed = response.choices[0].message.content or query
            return transformed.strip()

        except Exception as e:
            print(f"[QUERY TRANSFORM ERROR] Transformation failed, falling back to raw query: {e}")
            return query