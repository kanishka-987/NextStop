from backend.db_connection import get_db_connection

def patch_db():
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE users MODIFY role ENUM('admin', 'conductor', 'passenger') NOT NULL")
        print('Users role enum updated.')
    except Exception as e:
        print('Error updating users:', e)
    
    try:
        c.execute("ALTER TABLE tickets ADD COLUMN user_id INT NULL")
        print('Tickets user_id column added.')
    except Exception as e:
        print('Error updating tickets:', e)
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    patch_db()
