from backend.db_connection import get_db_connection; conn = get_db_connection(); cursor = conn.cursor(dictionary=True); cursor.execute("SELECT * FROM bus_location"); print(cursor.fetchall())
