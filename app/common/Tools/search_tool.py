from tavily import AsyncTavilyClient
from app.core.config import settings

class WebSearchTool:
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
        
    async def extract(self, url: str, query: str = "", extract_depth: str = "basic", chunks: int = 3):
        try:
            params = {
                "urls": [url] if isinstance(url, str) else url,
                "extract_depth": extract_depth
            }
            
            if query and query.strip():
                params["query"]=query
                params["chunks_per_source"]=chunks
            response=await self.client.extract(**params)
            results = response.get("results", [])
            
            if not results:
                return "Observation: No extractable content found for the provided URL."
            
            formatted_output = f"Extraction Results for '{query}':\n\n" if query else f"Extraction Results:\n\n"
            
            for index, res in enumerate(results):
                formatted_output += f"--- Source {index + 1} ---\n"
                formatted_output += f"URL: {res.get('url')}\n"
                raw_content = res.get("raw_content", "No content found.")
                formatted_output += f"Content:\n{raw_content}\n\n"
                
            return formatted_output
        
        except Exception as e:
            print(f"[EXTRACT ERROR] {e}")
            return f"Observation: Extract tool encountered an API error: {str(e)}"
        
    async def crawl(self, url: str, instructions: str = "", chunks_per_source: int = 3, 
max_depth: int = 1, max_breadth: int = 10, limit: int = 1):
        try:
            params = {
                "url": url,
                "max_depth": max_depth,
                "max_breadth": max_breadth,
                "limit": limit
            }
            
            if instructions and instructions.strip():
               params["instructions"] = instructions
               params["chunks_per_source"] = chunks_per_source

            response=await self.client.extract(**params)
            results = response.get("results", [])
            
            if not results:
                return f"Observation: No crawlable pages found for {url}."
            
            header_text = f"Crawl Results for '{url}':\n"
            if instructions:
                header_text += f"Filter Instructions: {instructions} (Max Chunks/Source: {chunks_per_source})\n"
            header_text += f"[Settings - Depth: {max_depth} | Breadth: {max_breadth} | Limit: {limit}]\n"
            
            formatted_output = header_text + "\n"

            for index, res in enumerate(results):
                formatted_output += f"--- Page {index + 1} ---\n"
                formatted_output += f"URL: {res.get('url')}\n"
                raw_content = res.get("raw_content", "No content found.")
                formatted_output += f"Content:\n{raw_content}\n\n"
                
            return formatted_output
        
        except Exception as e:
            print(f"[CRAWL ERROR] {e}")
            return f"Observation: Crawl tool encountered an API error: {str(e)}"
        
    
