# database/init_db.py
# NextStop Project Database Initialization and User Seeding Script
# Supports GPS Tracking, Exit Management, ML Predictions, and 60-seat bus configuration.

import os
import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables if .env file exists
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'nextstop_db')

def initialize_database():
    print(f"Connecting to MySQL server at {DB_HOST}...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
    except mysql.connector.Error as err:
        print(f"[-] MySQL connection failed: {err}")
        return False

    try:
        print(f"Creating database '{DB_NAME}' if it does not exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
    except mysql.connector.Error as err:
        print(f"[-] Failed creating database: {err}")
        conn.close()
        return False

    conn.database = DB_NAME
    print(f"[+] Successfully connected to database '{DB_NAME}'")

    print("Skipping table drops to preserve existing data...")

    # Create tables
    queries = {
        "buses": """
        CREATE TABLE IF NOT EXISTS buses (
            bus_id INT AUTO_INCREMENT PRIMARY KEY,
            bus_number VARCHAR(50) UNIQUE NOT NULL,
            bus_type VARCHAR(100),
            route_name VARCHAR(100),
            seat_capacity INT NOT NULL DEFAULT 60,
            standing_capacity INT NOT NULL DEFAULT 20,
            status ENUM('active','inactive') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        "users": """
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role ENUM('admin', 'conductor') NOT NULL,
            employee_id VARCHAR(50) NULL UNIQUE,
            phone_number VARCHAR(20) NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        "occupancy": """
        CREATE TABLE IF NOT EXISTS occupancy (
            bus_number VARCHAR(50) PRIMARY KEY,
            current_occupancy INT DEFAULT 0,
            seat_capacity INT NOT NULL DEFAULT 60,
            seats_available INT NOT NULL DEFAULT 60,
            standing_capacity INT NOT NULL DEFAULT 20,
            standing_available INT NOT NULL DEFAULT 20,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        "tickets": """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INT AUTO_INCREMENT PRIMARY KEY,
            bus_number VARCHAR(50) NOT NULL,
            source_stop VARCHAR(100) NOT NULL,
            destination_stop VARCHAR(100) NOT NULL,
            passenger_count INT NOT NULL,
            fare DECIMAL(10, 2) NOT NULL,
            ticket_date DATE NOT NULL,
            ticket_time TIME NOT NULL,
            assigned_seat VARCHAR(500) NULL,
            ticket_status ENUM('Active', 'Completed') NOT NULL DEFAULT 'Active',
            boarding_time TIME NULL,
            exit_time TIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        "seat_status": """
        CREATE TABLE IF NOT EXISTS seat_status (
            seat_id INT AUTO_INCREMENT PRIMARY KEY,
            bus_number VARCHAR(50) NOT NULL,
            seat_number INT NOT NULL,
            status ENUM('Available', 'Occupied', 'Reserved') DEFAULT 'Available',
            ticket_id INT NULL,
            boarding_stop VARCHAR(100) NULL,
            destination_stop VARCHAR(100) NULL,
            passenger_name VARCHAR(100) NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY bus_seat_unique (bus_number, seat_number),
            FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE,
            FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        "bus_location": """
        CREATE TABLE IF NOT EXISTS bus_location (
            bus_number VARCHAR(50) PRIMARY KEY,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            current_stop VARCHAR(100) NOT NULL,
            is_demo BOOLEAN DEFAULT FALSE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        "predictions": """
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INT AUTO_INCREMENT PRIMARY KEY,
            bus_number VARCHAR(50) NOT NULL,
            prediction_time DATETIME NOT NULL,
            predicted_occupancy INT NOT NULL,
            predicted_available_seats INT NOT NULL,
            predicted_standing_available INT NOT NULL,
            crowd_level VARCHAR(50) NOT NULL,
            model_accuracy DECIMAL(5, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bus_number) REFERENCES occupancy(bus_number) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    }

    for name, q in queries.items():
        try:
            print(f"Creating '{name}' table...")
            cursor.execute(q)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"[-] Failed creating table '{name}': {err}")
            cursor.close()
            conn.close()
            return False

    # Seed sample bus NS-B01 (Seating: 60, Standing: 20)
    try:
        print("Seeding default bus 'NS-B01'...")
        
        # Insert into buses IF NOT EXISTS
        cursor.execute("""
            INSERT IGNORE INTO buses (bus_number, bus_type, route_name, seat_capacity, standing_capacity, status)
            VALUES ('NS-B01', 'Volvo City Liner', 'Route 4 - City Center', 60, 20, 'active')
        """)

        # Insert into occupancy IF NOT EXISTS
        cursor.execute("""
            INSERT IGNORE INTO occupancy (bus_number, current_occupancy, seat_capacity, seats_available, standing_capacity, standing_available)
            VALUES ('NS-B01', 0, 60, 60, 20, 20)
        """)
        
        # Seed 60 physical seats for NS-B01 in seat_status if they don't exist
        print("Seeding physical seats for 'NS-B01'...")
        for seat_num in range(1, 61):
            cursor.execute("""
                INSERT IGNORE INTO seat_status (bus_number, seat_number, status)
                VALUES ('NS-B01', %s, 'Available')
            """, (seat_num,))
            
        conn.commit()
        print("[+] Seeded NS-B01 occupancy and 60 seats successfully.")
    except mysql.connector.Error as err:
        print(f"[-] Failed seeding bus / seats: {err}")
        cursor.close()
        conn.close()
        return False

    # Seed default users
    seed_users = [
        {
            "full_name": "NextStop Admin",
            "email": "admin@nextstop.com",
            "password": "Admin@123",
            "role": "admin",
            "employee_id": "EMP100",
            "phone_number": "1234567890"
        },
        {
            "full_name": "Bus Conductor One",
            "email": "conductor@nextstop.com",
            "password": "Conductor@123",
            "role": "conductor",
            "employee_id": None,
            "phone_number": None
        }
    ]

    print("Checking and seeding default users...")
    for user_data in seed_users:
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (user_data["email"],))
        result = cursor.fetchone()
        
        if not result:
            hashed_pw = generate_password_hash(user_data["password"])
            insert_query = """
            INSERT INTO users (full_name, email, password, role, employee_id, phone_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                user_data["full_name"],
                user_data["email"],
                hashed_pw,
                user_data["role"],
                user_data["employee_id"],
                user_data["phone_number"]
            ))
            conn.commit()
            print(f"[+] Seeded user: {user_data['full_name']} ({user_data['role']})")

    cursor.close()
    conn.close()
    print("[+] Database initialization complete!")
    return True

if __name__ == '__main__':
    initialize_database()
