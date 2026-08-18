import asyncio
from app.core.database import engine, Base

import app.modules.auth.model 
import app.modules.mode_chat.models

async def create_tables():
    print("Connecting to database...")
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())