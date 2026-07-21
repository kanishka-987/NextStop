# backend/db_connection.py
# NextStop Project Database Connection Helper
# Provides reusable connection pooling for MySQL database.

import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Retrieve configuration from environment
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_NAME = os.getenv('DB_NAME', 'nextstop_db')

# Initialize connection pool
db_pool = None

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="nextstop_pool",
        pool_size=5,  # Moderate pool size for concurrent requests
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    print("[+] Database connection pool initialized successfully.")
except mysql.connector.Error as err:
    print(f"[-] Database connection pool initialization failed: {err}")

def get_db_connection():
    """
    Retrieves a connection from the pool.
    If the pool was not initialized (e.g. database does not exist yet), 
    attempts to connect directly.
    """
    global db_pool
    if db_pool:
        try:
            return db_pool.get_connection()
        except mysql.connector.Error:
            # Fall back to direct connection if pool fails
            pass
            
    # Direct fallback connection
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def check_db_status():
    """
    Tests if the database connection is alive.
    Returns (True, message) if healthy, or (False, error_message) if failing.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "Database connection is healthy."
    except Exception as e:
        return False, str(e)
