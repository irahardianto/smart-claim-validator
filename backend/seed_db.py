import sqlite3
import os

DB_PATH = 'backend/insurance.db'

def seed_database():
    if not os.path.exists('backend'):
        print("Error: Run this from the project root directory")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read seed.sql
    with open('backend/seed.sql', 'r') as f:
        sql_script = f.read()
    
    try:
        cursor.executescript(sql_script)
        conn.commit()
        print("Database seeded successfully.")
        
        # Verify
        cursor.execute("SELECT * FROM claim_rules")
        rows = cursor.fetchall()
        print(f"Verified: {len(rows)} rules found.")
        for row in rows:
            print(f" - {row[1]}")
            
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    seed_database()
