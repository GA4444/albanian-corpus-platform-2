#!/usr/bin/env python3
"""
Migration script to add gamification columns to existing database
"""
import sqlite3
import os

DB_PATH = "dev.db"

def migrate():
    """Add gamification columns to users table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 Starting database migration for gamification...")
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    
    migrations = [
        ("current_streak", "INTEGER DEFAULT 0 NOT NULL"),
        ("longest_streak", "INTEGER DEFAULT 0 NOT NULL"),
        ("last_activity_date", "DATETIME"),
        ("total_achievements", "INTEGER DEFAULT 0 NOT NULL"),
    ]
    
    for column_name, column_def in migrations:
        if column_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}")
                print(f"✅ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"⚠️  Column {column_name} might already exist or error: {e}")
        else:
            print(f"⏭️  Column {column_name} already exists, skipping.")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration completed successfully!")
    print("Now run: python scripts/init_gamification.py")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file '{DB_PATH}' not found!")
        print("Make sure you're running this from the backend/ directory.")
        exit(1)
    
    migrate()
