# backend/test_tickets.py
# NextStop Project - Ticket Management Integration Tests
# Verifies ticket generation, occupancy adjustments, capacity blocks, and route protections.

import requests
import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

# Load env variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
DB_NAME = os.getenv('DB_NAME', 'nextstop_db')

BASE_URL = "http://127.0.0.1:5000"

def get_direct_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

def reset_bus_occupancy():
    """Resets the NS-B01 bus occupancy back to 0 for a clean test environment."""
    conn = get_direct_db_connection()
    cursor = conn.cursor()
    # Delete test tickets
    cursor.execute("DELETE FROM tickets WHERE bus_number = 'NS-B01'")
    # Reset occupancy
    cursor.execute("""
        UPDATE occupancy 
        SET current_occupancy = 0, seats_available = 40, standing_available = 20 
        WHERE bus_number = 'NS-B01'
    """)
    conn.commit()
    cursor.close()
    conn.close()

def run_tests():
    # 1. Reset database state before starting
    print("[*] Resetting database state for testing...")
    reset_bus_occupancy()

    # Start requests session
    session = requests.Session()

    print("\n--- Test 1: Non-logged in access restriction ---")
    r = session.get(f"{BASE_URL}/conductor/tickets/generate", allow_redirects=True)
    assert "Please log in to access this page" in r.text, "Failed to restrict unauthorized access"
    print("[+] Protected route validation passed.")

    # 2. Log in as Conductor
    print("\n[*] Logging in as Conductor...")
    r = session.post(f"{BASE_URL}/login", data={
        "email": "conductor@nextstop.com",
        "password": "Conductor@123",
        "role": "conductor"
    }, allow_redirects=True)
    assert "Conductor Console" in r.text, "Conductor login failed"
    print("[+] Login successful.")

    # 3. Access ticket generation form
    print("\n--- Test 2: Ticket Generation form check ---")
    r = session.get(f"{BASE_URL}/conductor/tickets/generate")
    assert r.status_code == 200, "Form failed to load"
    assert "Issue Travel Ticket" in r.text, "Ticket form buttons not found"
    print("[+] Ticket form loaded successfully.")

    # 4. Generate Ticket 1 (15 passengers - should consume seats)
    print("\n--- Test 3: Ticket 1 - Seated passengers ---")
    now = datetime.now()
    r = session.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "A",
        "destination_stop": "B",
        "passenger_count": "15",
        "fare": "75.00",
        "ticket_date": now.strftime('%Y-%m-%d'),
        "ticket_time": now.strftime('%H:%M')
    }, allow_redirects=True)
    
    assert "Ticket generated successfully!" in r.text, "Failed to generate valid ticket"
    assert "Ticket Issued" in r.text, "Receipt output failed to display"
    
    # Query database occupancy to verify recalculation
    conn = get_direct_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM occupancy WHERE bus_number = 'NS-B01'")
    bus = cursor.fetchone()
    cursor.close()
    conn.close()

    print(f"Bus state: Occupancy={bus['current_occupancy']}, Seats Available={bus['seats_available']}, Standing Available={bus['standing_available']}")
    assert bus['current_occupancy'] == 15, "Occupancy did not increment correctly"
    assert bus['seats_available'] == 25, "Seats available incorrect (should be 25)"
    assert bus['standing_available'] == 20, "Standing available incorrect (should be 20)"
    print("[+] Seated passenger ticket generation and database update verified.")

    # 5. Generate Ticket 2 (30 passengers - exceeds seats, starts using standing room)
    print("\n--- Test 4: Ticket 2 - Overflow into standing area ---")
    r = session.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "B",
        "destination_stop": "C",
        "passenger_count": "30",
        "fare": "150.00",
        "ticket_date": now.strftime('%Y-%m-%d'),
        "ticket_time": now.strftime('%H:%M')
    }, allow_redirects=True)

    assert "Ticket generated successfully!" in r.text, "Failed to generate ticket 2"
    
    conn = get_direct_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM occupancy WHERE bus_number = 'NS-B01'")
    bus = cursor.fetchone()
    cursor.close()
    conn.close()

    print(f"Bus state: Occupancy={bus['current_occupancy']}, Seats Available={bus['seats_available']}, Standing Available={bus['standing_available']}")
    assert bus['current_occupancy'] == 45, "Occupancy did not increment correctly"
    assert bus['seats_available'] == 0, "Seats available incorrect (should be 0)"
    assert bus['standing_available'] == 15, "Standing available incorrect (should be 15)"
    print("[+] Standing passenger ticket generation and database update verified.")

    # 6. Generate Ticket 3 (20 passengers - exceeds total capacity of 60)
    print("\n--- Test 5: Ticket 3 - Exceed capacity block ---")
    r = session.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "C",
        "destination_stop": "D",
        "passenger_count": "20",
        "fare": "100.00",
        "ticket_date": now.strftime('%Y-%m-%d'),
        "ticket_time": now.strftime('%H:%M')
    }, allow_redirects=True)

    assert "Bus Full - Ticket Cannot Be Generated" in r.text, "Over-capacity block failed"
    
    conn = get_direct_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM occupancy WHERE bus_number = 'NS-B01'")
    bus = cursor.fetchone()
    cursor.close()
    conn.close()

    print(f"Bus state: Occupancy={bus['current_occupancy']}, Seats Available={bus['seats_available']}, Standing Available={bus['standing_available']}")
    assert bus['current_occupancy'] == 45, "Occupancy changed despite error block"
    print("[+] Over-capacity ticket block and error message verified.")

    # 7. Check conductor dashboard displays values
    print("\n--- Test 6: Conductor Dashboard stats rendering ---")
    r = session.get(f"{BASE_URL}/conductor/dashboard")
    assert "Current Occupancy" in r.text, "Occupancy labels missing"
    assert "45 / 60" in r.text, "Dashboard occupancy display incorrect"
    assert "Seats Available" in r.text
    assert "Standing Available" in r.text
    print("[+] Conductor dashboard stats rendering verified.")

    # 8. Clean up database state
    print("\n[*] Cleaning up database after successful test execution...")
    reset_bus_occupancy()
    print("[+] Database cleaned up.")
    print("\n[SUCCESS] All Module 2 Ticket Management integration tests passed successfully!")

if __name__ == "__main__":
    run_tests()
