from simai_search.db import SimaiDB
import os

def debug():
    db_path = "debug_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print(f"Creating DB at {db_path}")
    db = SimaiDB(db_path)
    
    print("Adding song...")
    try:
        sid = db.add_song("Test Title", "Test Artist", "Test Genre", "test/path")
        print(f"Song ID: {sid}")
    except Exception as e:
        print(f"Error adding song: {e}")
        
    print("Checking songs table...")
    try:
        rows = db.conn.execute("SELECT * FROM songs").fetchall()
        print(f"Rows: {rows}")
    except Exception as e:
        print(f"Error verifying: {e}")

if __name__ == "__main__":
    debug()
