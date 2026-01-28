#!/usr/bin/env python3
"""
Fix PostgreSQL sequence for users table
This script resets the users_id_seq sequence to match the maximum ID in the users table.
"""
import os
import sys
from sqlalchemy import text
from app.database import SessionLocal, engine

def fix_users_sequence():
    """Fix the users_id_seq sequence to prevent duplicate key errors"""
    db = SessionLocal()
    
    try:
        # Get the current maximum ID from users table
        result = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM users"))
        max_id = result.scalar()
        
        print(f"📊 Maximum user ID in database: {max_id}")
        
        # Get current sequence value
        result = db.execute(text("SELECT last_value FROM users_id_seq"))
        current_seq = result.scalar()
        
        print(f"📊 Current sequence value: {current_seq}")
        
        # Reset sequence to max_id + 1 (so next insert gets max_id + 1)
        if max_id >= current_seq:
            new_seq_value = max_id + 1
            db.execute(text(f"SELECT setval('users_id_seq', {new_seq_value}, false)"))
            db.commit()
            print(f"✅ Sequence reset to {new_seq_value}")
        else:
            print(f"✅ Sequence is already correct (current: {current_seq}, max_id: {max_id})")
        
        # Verify the fix
        result = db.execute(text("SELECT last_value FROM users_id_seq"))
        new_seq = result.scalar()
        print(f"✅ New sequence value: {new_seq}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing sequence: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Fixing users_id_seq sequence...")
    print("=" * 50)
    
    if fix_users_sequence():
        print("=" * 50)
        print("✅ Sequence fixed successfully!")
    else:
        print("=" * 50)
        print("❌ Failed to fix sequence")
        sys.exit(1)
