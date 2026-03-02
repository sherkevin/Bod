import sqlite3
import os

db_path = "bod.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    try:
        cursor.execute("SELECT hashed_password FROM users LIMIT 1")
        print("Column 'hashed_password' already exists.")
    except sqlite3.OperationalError:
        print("Adding 'hashed_password' column to 'users' table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN hashed_password VARCHAR")
            conn.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
            
    conn.close()
else:
    print("Database file not found.")
