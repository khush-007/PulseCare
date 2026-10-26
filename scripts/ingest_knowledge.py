import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from backend.app.core.database import AsyncSessionLocal, init_db
from backend.app.chatbot.rag.ingestion import ingest_directory


async def main():
    kb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledge_base"))
    print(f"[Ingest] Ingesting knowledge documents from: {kb_path}")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        result = await ingest_directory(kb_path, session, reindex=True)
        print(f"[Ingest] Completed! {result['message']}")


if __name__ == "__main__":
    asyncio.run(main())
