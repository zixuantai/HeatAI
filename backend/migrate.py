import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences TEXT
        """))
        print("[OK] users.preferences column added")

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                title VARCHAR(200) DEFAULT '新对话',
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_conv_sessions_user ON conversation_sessions(user_id)
        """))
        print("[OK] conversation_sessions table created")

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)
        """))
        print("[OK] messages table created")

        await conn.execute(text("""
            ALTER TABLE organizations ADD COLUMN IF NOT EXISTS avatar TEXT
        """))
        print("[OK] organizations.avatar column added")

        await conn.execute(text("""
            ALTER TABLE organizations ADD COLUMN IF NOT EXISTS phone VARCHAR(20)
        """))
        print("[OK] organizations.phone column added")

        await conn.execute(text("""
            ALTER TABLE organizations ADD COLUMN IF NOT EXISTS email VARCHAR(100)
        """))
        print("[OK] organizations.email column added")

    print("Migration completed!")

if __name__ == "__main__":
    asyncio.run(migrate())
