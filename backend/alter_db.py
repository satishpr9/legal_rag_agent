import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def run():
    async with AsyncSessionLocal() as db:
        await db.execute(text('ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS filters JSON;'))
        await db.commit()
        print('Success')

if __name__ == "__main__":
    asyncio.run(run())
