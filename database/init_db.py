# database/init_db.py
# NextStop Project Database Initialization and User Seeding Script

import os
import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables if .env file exists
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# MySQL connection settings (default values with .env override support)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')  # default empty password for local MySQL root
DB_NAME = os.getenv('DB_NAME', 'nextstop_db')

def initialize_database():
    print(f"Connecting to MySQL server at {DB_HOST}...")
    try:
        # Connect to MySQL server without selecting database first
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"[-] MySQL connection failed: {err}")
        print("Please check your MySQL server and make sure configuration in .env is correct.")
        return False

    try:
        # Create database
        print(f"Creating database '{DB_NAME}' if it does not exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
    except mysql.connector.Error as err:
        print(f"[-] Failed creating database: {err}")
        conn.close()
        return False

    # Select the database
    conn.database = DB_NAME
    print(f"[+] Successfully connected to database '{DB_NAME}'")

    # Create users table
    create_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        role ENUM('admin', 'conductor') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    try:
        print("Creating 'users' table...")
        cursor.execute(create_table_query)
        conn.commit()
        print("[+] 'users' table is ready.")
    except mysql.connector.Error as err:
        print(f"[-] Failed creating table: {err}")
        cursor.close()
        conn.close()
        return False

    # Create occupancy table
    create_occupancy_table = """
    CREATE TABLE IF NOT EXISTS occupancy (
        bus_number VARCHAR(50) PRIMARY KEY,
        current_occupancy INT DEFAULT 0,
        seat_capacity INT NOT NULL DEFAULT 40,
        seats_available INT NOT NULL DEFAULT 40,
        standing_capacity INT NOT NULL DEFAULT 20,
        standing_available INT NOT NULL DEFAULT 20,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    # Create tickets table
    create_tickets_table = """
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id INT AUTO_INCREMENT PRIMARY KEY,
        bus_number VARCHAR(50) NOT NULL,
        source_stop VARCHAR(100) NOT NULL,
        destination_stop VARCHAR(100) NOT NULL,
        passenger_count INT NOT NULL,
        fare DECIMAL(10, 2) NOT NULL,
        ticket_date DATE NOT NULL,
        ticket_time TIME NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    try:
        print("Creating 'occupancy' table...")
        cursor.execute(create_occupancy_table)
        print("Creating 'tickets' table...")
        cursor.execute(create_tickets_table)
        conn.commit()
        print("[+] 'occupancy' and 'tickets' tables are ready.")
    except mysql.connector.Error as err:
        print(f"[-] Failed creating occupancy/tickets tables: {err}")
        cursor.close()
        conn.close()
        return False

    # Seed sample bus NS-B01
    try:
        print("Checking and seeding default bus 'NS-B01'...")
        cursor.execute("SELECT bus_number FROM occupancy WHERE bus_number = 'NS-B01'")
        bus = cursor.fetchone()
        if not bus:
            cursor.execute("""
                INSERT INTO occupancy (bus_number, current_occupancy, seat_capacity, seats_available, standing_capacity, standing_available)
                VALUES ('NS-B01', 0, 40, 40, 20, 20)
            """)
            conn.commit()
            print("[+] Seeded default bus 'NS-B01' (40 seats, 20 standing capacity)")
        else:
            print("[.] Default bus 'NS-B01' already exists. Skipping seeding.")
    except mysql.connector.Error as err:
        print(f"[-] Failed seeding default bus: {err}")
        cursor.close()
        conn.close()
        return False


    # Seed Admin and Conductor accounts
    # Passwords hashed with pbkdf2:sha256 using werkzeug.security
    seed_users = [
        {
            "full_name": "NextStop Admin",
            "email": "admin@nextstop.com",
            "password": "Admin@123",
            "role": "admin"
        },
        {
            "full_name": "Bus Conductor One",
            "email": "conductor@nextstop.com",
            "password": "Conductor@123",
            "role": "conductor"
        }
    ]

    print("Checking and seeding default users...")
    for user_data in seed_users:
        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (user_data["email"],))
        result = cursor.fetchone()
        
        if not result:
            hashed_pw = generate_password_hash(user_data["password"])
            insert_query = """
            INSERT INTO users (full_name, email, password, role)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                user_data["full_name"],
                user_data["email"],
                hashed_pw,
                user_data["role"]
            ))
            conn.commit()
            print(f"[+] Seeded user: {user_data['full_name']} ({user_data['role']}) - Email: {user_data['email']}")
        else:
            print(f"[.] User with email '{user_data['email']}' already exists. Skipping seeding.")

    cursor.close()
    conn.close()
    print("[+] Database initialization complete!")
    return True

if __name__ == '__main__':
    initialize_database()
