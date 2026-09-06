# database/reset_db_test.py
import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'nextstop_db')

def reset_database():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    print("Resetting tickets table...")
    cursor.execute("DELETE FROM tickets")
    
    print("Resetting occupancy table...")
    cursor.execute("UPDATE occupancy SET current_occupancy = 0, seats_available = 40, standing_available = 20 WHERE bus_number = 'NS-B01'")
    
    print("Resetting seat_status table...")
    cursor.execute("UPDATE seat_status SET status = 'Available', ticket_id = NULL, boarding_stop = NULL, destination_stop = NULL, passenger_name = NULL WHERE bus_number = 'NS-B01'")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("[+] Database reset successfully for testing.")

if __name__ == '__main__':
    reset_database()
