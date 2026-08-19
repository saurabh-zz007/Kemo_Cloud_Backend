import json
from typing import List
from openai import AsyncOpenAI
from app.core.config import settings

class FactExtractorService:
    def __init__(self):
        # Groq compatibility via AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "openai/gpt-oss-20b"

        self.system_prompt = """
        You are an elite memory extraction agent for an AI assistant.
        Your sole task is to analyze a single conversation turn (User prompt + AI response) and extract PERMANENT facts, preferences, personal details, system setups, or explicit rules about the user.

        RULES FOR EXTRACTION:
        1. Extract ONLY concrete facts stated by or about the user (e.g., name, university, preferences, tech stack, habits, system specs).
        2. DO NOT extract temporary queries, generic chatter, greetings, or questions (e.g., "What is my name?", "How are you?", "Write code for X").
        3. Rephrase facts into clear, self-contained declarative statements in the third person (e.g., "The user's name is Saurabh", "The user studies Mechanical Engineering").
        4. If no permanent facts or preferences are declared in this interaction, return an empty array for facts.

        Output must ALWAYS be valid JSON in this exact structure:
        {
            "has_facts": true | false,
            "facts": ["Statement 1", "Statement 2"]
        }
        """

    async def extract_facts(self, user_prompt: str, ai_response: str) -> List[str]:
        """
        Passes the interaction to Groq Llama 3.1 to extract permanent facts.
        Returns a list of extracted fact strings.
        """
        user_content = f"User Prompt: {user_prompt}\nAI Response: {ai_response}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            raw_text = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_text)

            if parsed.get("has_facts") and isinstance(parsed.get("facts"), list):
                return parsed["facts"]

            return []

        except Exception as e:
            print(f"[FACT EXTRACTION ERROR] Groq extraction failed: {e}")
            return []