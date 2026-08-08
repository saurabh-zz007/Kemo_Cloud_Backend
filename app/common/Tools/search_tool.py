from tavily import AsyncTavilyClient
from app.core.config import settings

class SearchTool:
    def __init__(self):
        self.client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

    async def search(self, query: str, search_depth: str = "basic", chunks: int = 1, max_results: int = 5):
        try:
            response=await self.client.search(
                query=query,
                search_depth=search_depth, #type:ignore
                chunks_per_source=chunks,
                max_results=max_results
            )
            results = response.get("results", [])
            if not results:
                return "Observation: No relevant information found in the knowledge base."
            formatted_output = f"Web Search Results for '{query}':\n\n"
            for index, res in enumerate(results):
                formatted_output += f"Result {index + 1}:\n"
                formatted_output += f"Title: {res.get('title')}\n"
                formatted_output += f"URL: {res.get('url')}\n"
                formatted_output += f"Content: {res.get('content')}\n\n"
                
            return formatted_output
        
        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
            return f"Observation: Search tool encountered an API error: {str(e)}"
