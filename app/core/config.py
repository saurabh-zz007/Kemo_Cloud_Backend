import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DB_CONNECTION: str
    ALGORITHM: str
    SECRET_KEY: str
    DEEPSEEK_API_KEY: str
    GROQ_API_KEY: str 
    PROJECT_NAME: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    QDRANT_ENDPOINT: str
    QDRANT_API_KEY: str
    TAVILY_API_KEY: str
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str
    OPENROUTER_PLANNER_MODEL_NAME: str
    OPENROUTER_WORKER_MODEL_NAME: str
    OPENROUTER_SYNTHESIZER_MODEL_NAME: str
    TEST_USER_ID: str

settings = Settings() #type: ignore