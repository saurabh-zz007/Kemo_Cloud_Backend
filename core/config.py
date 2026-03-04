import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY")
    PROJECT_NAME: str = "KEMO Cloud Brain"

settings = Settings()