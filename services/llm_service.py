import json
from openai import OpenAI
from core.config import settings

class DeepSeekService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com"
        )
        
        # 🚨 THE PREFIX CACHE: This string must NEVER dynamically change. 
        # DeepSeek caches this exact block to save you 90% on tokens.
        self.system_prompt = """
        You are KEMO, an AI desktop assistant system brain.
        Determine if physical PC actions are needed based on the user's request.
        
        Available actions:
        - "openApp" (requires 'app_name')
        - "closeApp" (requires 'app_name')
        - "getSystemStatus" (no arguments)
        - "optimizeSystem" (no arguments)
        - "setupEnvironment" (requires 'package_id')
        - "removeEnvironment" (requires 'package_id')
        
        CRITICAL PACKAGE IDs:
        - Go: "GoLang.Go"
        - Zig: "zig.zig"
        - Python: "Python.Python.3.11"
        - Java: "Microsoft.OpenJDK.17"
        - C++: "Microsoft.VisualStudio.2022.BuildTools"
        - Node.js: "OpenJS.NodeJS"

        You MUST respond in strict JSON format containing a "tasks" array.
        Example: {"tasks": [{"action": "setupEnvironment", "arguments": {"package_id": "OpenJS.NodeJS"}}]}
        If no actions are needed, return: {"tasks": []}
        """

    def generate_plan(self, user_prompt: str) -> list:
        # The dynamic user text is isolated to preserve the static cache above
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.0, # Zero creativity, strict logic
                response_format={"type": "json_object"} # Forces valid JSON
            )
            
            raw_text = response.choices[0].message.content
            parsed_json = json.loads(raw_text)
            return parsed_json.get("tasks", [])
            
        except Exception as e:
            print(f"DeepSeek Service Error: {e}")
            return []