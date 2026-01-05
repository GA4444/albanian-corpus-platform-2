#!/usr/bin/env python3
"""
Migration script to add chatbot tables
"""
import sqlite3
import os

DB_PATH = "dev.db"

def migrate():
    """Add chat_sessions and chat_messages tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 Starting database migration for advanced chatbot...")
    
    # Create chat_sessions table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(50),
                session_token VARCHAR(100) UNIQUE NOT NULL,
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                total_messages INTEGER NOT NULL DEFAULT 0,
                user_satisfaction INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_session_token ON chat_sessions(session_token)")
        print("✅ Created table: chat_sessions")
    except sqlite3.OperationalError as e:
        print(f"⚠️  chat_sessions table might already exist: {e}")
    
    # Create chat_messages table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role VARCHAR(20) NOT NULL,
                content TEXT NOT NULL,
                model_used VARCHAR(50),
                tokens_used INTEGER,
                response_time_ms INTEGER,
                context_data TEXT,
                suggested_questions TEXT,
                generated_exercise_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                FOREIGN KEY (generated_exercise_id) REFERENCES exercises(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages(created_at)")
        print("✅ Created table: chat_messages")
    except sqlite3.OperationalError as e:
        print(f"⚠️  chat_messages table might already exist: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration completed successfully!")
    print("Advanced chatbot is now ready with conversation history!")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file '{DB_PATH}' not found!")
        print("Make sure you're running this from the backend/ directory.")
        exit(1)
    
    migrate()
