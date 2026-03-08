import sqlite3

def view_database(db_name):
    print(f"\n{'='*60}")
    print(f"Database: {db_name}")
    print('='*60)
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n--- Table: {table_name} ---")
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"Columns: {column_names}")
        
        # Get all rows
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if rows:
            print(f"Rows ({len(rows)}):")
            for row in rows:
                print(f"  {row}")
        else:
            print("  (empty)")
    
    conn.close()

if __name__ == '__main__':
    view_database('users.db')
    view_database('authorized_users.db')
