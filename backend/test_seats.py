# backend/test_seats.py
# Automated integration tests for Module 2 Automatic Seat Allocation & Standing Room Tracking.

import requests
import random
import string
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.init_db import initialize_database

BASE_URL = "http://127.0.0.1:5000"

def test_automatic_seat_allocation():
    print("[*] Initializing clean database state...")
    initialize_database()
    print("\n--- 1. Testing Conductor Authentication for Allocation ---")
    s = requests.Session()
    r = s.post(f"{BASE_URL}/login", data={
        "email": "conductor@nextstop.com",
        "password": "Conductor@123",
        "role": "conductor"
    }, allow_redirects=True)
    assert "Conductor Console" in r.text, "Failed to authenticate conductor"
    print("[+] Conductor authenticated successfully.")

    # Reset occupancy and seat status database values for testing cleanliness
    # (In integration testing, we can issue tickets and observe consecutive assignments)
    
    print("\n--- 2. Testing First Passenger Seat Allocation ---")
    # Issue ticket for 1 passenger
    r = s.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "A",
        "destination_stop": "B",
        "passenger_count": "1",
        "fare": "5.00",
        "ticket_date": "2026-07-24",
        "ticket_time": "20:00"
    }, allow_redirects=True)
    
    assert "Ticket generated successfully!" in r.text, "Failed to generate ticket"
    assert "Assigned Seat Numbers" in r.text
    print("[+] Single passenger ticket generated and seat assigned.")

    print("\n--- 3. Testing Group Booking (Consecutive Seats) ---")
    # Issue ticket for 4 passengers
    r = s.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "B",
        "destination_stop": "C",
        "passenger_count": "4",
        "fare": "20.00",
        "ticket_date": "2026-07-24",
        "ticket_time": "20:05"
    }, allow_redirects=True)
    
    assert "Ticket generated successfully!" in r.text
    print("[+] Group booking ticket issued successfully.")

    print("\n--- 4. Testing Standing Room & Capacity Cap ---")
    # Issue ticket for 75 passengers (makes total occupancy 80, filling seats and standing capacity)
    r = s.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "C",
        "destination_stop": "D",
        "passenger_count": "75",
        "fare": "375.00",
        "ticket_date": "2026-07-24",
        "ticket_time": "20:10"
    }, allow_redirects=True)
    assert "Ticket generated successfully!" in r.text, "Failed to fill bus capacity"
    assert "All seats are occupied. Passenger will travel as Standing." in r.text
    print("[+] Bus filled to maximum total capacity (80 passengers).")

    # Attempt to issue another ticket when full
    r = s.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "D",
        "destination_stop": "E",
        "passenger_count": "1",
        "fare": "5.00",
        "ticket_date": "2026-07-24",
        "ticket_time": "20:15"
    }, allow_redirects=True)
    
    assert "Bus has reached its maximum capacity. Ticket cannot be generated." in r.text, "Capacity block failed"
    print("[+] Ticket generation block verified on overflow.")

    print("\n--- 5. Testing Live Seat Map Status Rendering ---")
    r = s.get(f"{BASE_URL}/conductor/occupancy?bus_number=NS-B01")
    assert "Live Seat Occupancy Map" in r.text
    # When full, there should be "occupied" seats
    assert "occupied" in r.text
    print("[+] Live Seat Map renders correctly from database status.")

    print("\n[SUCCESS] Module 2 Seat Allocation integration tests passed successfully!")

if __name__ == "__main__":
    test_automatic_seat_allocation()
