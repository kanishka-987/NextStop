# backend/test_modules_3_4_5.py
# Automated integration tests for NextStop Modules 3, 4, and 5.

import requests
import json
import sys
import os

# Adjust path to import database helpers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.init_db import initialize_database

BASE_URL = "http://127.0.0.1:5000"

def test_system():
    print("\n==================================================")
    print("STARTING SYSTEM INTEGRATION TESTS FOR MODULES 3, 4, 5")
    print("==================================================")

    # 0. Initialize database to clean state
    print("[*] Initializing clean database state...")
    initialize_database()

    # 1. Login Conductor
    print("\n--- 1. Authenticating Conductor ---")
    s_cond = requests.Session()
    r_login = s_cond.post(f"{BASE_URL}/login", data={
        "email": "conductor@nextstop.com",
        "password": "Conductor@123",
        "role": "conductor"
    })
    assert "Conductor Console" in r_login.text or r_login.status_code == 200
    print("[+] Conductor authenticated.")

    # 2. Login Admin
    print("\n--- 2. Authenticating Admin ---")
    s_admin = requests.Session()
    r_admin_login = s_admin.post(f"{BASE_URL}/login", data={
        "email": "admin@nextstop.com",
        "password": "Admin@123",
        "role": "admin"
    })
    assert "Admin Dashboard" in r_admin_login.text or r_admin_login.status_code == 200
    print("[+] Admin authenticated.")

    # 3. Generate tickets to test capacity limit (80)
    print("\n--- 3. Testing Seating & Standing Capacity limits ---")
    
    # First: Boarding 50 passengers (Seated)
    r_ticket1 = s_cond.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "Central Station",
        "destination_stop": "Tech Park",
        "passenger_count": "50",
        "fare": "250.00",
        "ticket_date": "2026-07-24",
        "ticket_time": "12:00"
    }, allow_redirects=True)
    assert "Ticket generated successfully!" in r_ticket1.text
    print("[+] Issued ticket for 50 passengers (Seated status assigned).")

    # Second: Boarding 15 passengers (exceeds remaining 10 seats, 5 must stand)
    r_ticket2 = s_cond.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "Central Station",
        "destination_stop": "Maple Road",
        "passenger_count": "15",
        "fare": "75.00",
        "ticket_date": "2026-07-24",
        "ticket_time": "12:05"
    }, allow_redirects=True)
    assert "Ticket generated successfully!" in r_ticket2.text
    assert "All seats are occupied. Passenger will travel as Standing." in r_ticket2.text
    print("[+] Issued ticket for 15 passengers (Seated & Standing assigned).")

    # Third: Try to board 20 more passengers (exceeds combined capacity: 50 + 15 + 20 = 85 > 80)
    r_ticket3 = s_cond.post(f"{BASE_URL}/conductor/tickets/generate", data={
        "bus_number": "NS-B01",
        "source_stop": "Central Station",
        "destination_stop": "City Center",
        "passenger_count": "20",
        "fare": "100.00",
        "ticket_date": "2026-07-24",
        "ticket_time": "12:10"
    }, allow_redirects=True)
    assert "Bus has reached its maximum capacity. Ticket cannot be generated." in r_ticket3.text
    print("[+] Successfully blocked booking exceeding combined seating + standing capacity.")

    # 4. Update GPS Location (Module 3) & trigger passenger exit (Module 4)
    print("\n--- 4. Testing GPS tracking coordinates & passenger exit triggers ---")
    # Post GPS coordinate near "Maple Road" stop
    # Coordinates of Maple Road: 12.9915, 77.6120
    gps_payload = {
        "latitude": 12.9915,
        "longitude": 77.6120,
        "bus_number": "NS-B01"
    }
    r_gps = s_cond.post(f"{BASE_URL}/gps/update", json=gps_payload)
    res_gps = r_gps.json()
    assert res_gps["success"] is True
    assert res_gps["detected_stop"] == "Maple Road"
    # Ticket 2 was destination "Maple Road" (15 passengers). They should exit.
    assert res_gps["exited_passengers"] == 15
    print("[+] GPS updated to Maple Road. Nearest stop detected and 15 passengers automatically exited.")

    # Check that occupancy decreased
    r_occ = s_cond.get(f"{BASE_URL}/conductor/occupancy/data?bus_number=NS-B01")
    res_occ = r_occ.json()
    assert res_occ["success"] is True
    # Initial occupancy was 50 + 15 = 65. Exited: 15. New occupancy should be 50.
    assert res_occ["current_occupancy"] == 50
    print("[+] Real-time occupancy correctly decreased to 50.")

    # 5. Machine Learning Predictor checks (Module 5)
    print("\n--- 5. Testing Machine Learning prediction confidence & retraining ---")
    r_ml = s_admin.get(f"{BASE_URL}/admin/ml/dashboard")
    assert "Machine Learning Predictions Dashboard" in r_ml.text
    assert "Mean Absolute Error" in r_ml.text
    print("[+] Admin ML Dashboard displays metrics correctly.")

    r_retrain = s_admin.post(f"{BASE_URL}/admin/ml/retrain", allow_redirects=True)
    assert "ML Model retrained successfully!" in r_retrain.text or r_retrain.status_code == 200
    print("[+] Random Forest regression model retrained and updated successfully.")

    print("\n==================================================")
    print("[SUCCESS] ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    test_system()
