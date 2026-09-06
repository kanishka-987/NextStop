# backend/test_admin_register.py
# Automated integration tests for Admin Registration & Passenger Portal.

import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.init_db import initialize_database

BASE_URL = "http://127.0.0.1:5000"

def test_admin_registration_and_portal():
    print("\n==================================================")
    print("STARTING TEST SUITE FOR ADMIN REGISTRATION & PORTAL")
    print("==================================================")

    # 0. Initialize database to clean state
    print("[*] Initializing clean database state...")
    initialize_database()

    s = requests.Session()

    # 1. Verify Passenger Portal page loads without login session
    print("\n--- 1. Testing Passenger Portal (Public Access) ---")
    r_passenger = s.get(f"{BASE_URL}/passenger")
    assert r_passenger.status_code == 200, "Passenger Portal failed to load"
    assert "Passenger Portal" in r_passenger.text or "Public Passenger Portal" in r_passenger.text
    print("[+] Passenger Portal page loads successfully without login.")

    # 2. Verify Passenger search API works
    print("\n--- 2. Testing Passenger Portal Search API ---")
    r_search = s.get(f"{BASE_URL}/passenger/search?q=NS-B01")
    assert r_search.status_code == 200, "Passenger search API failed"
    data = r_search.json()
    assert "results" in data, "Invalid search response schema"
    assert len(data["results"]) > 0, "Default seeded bus 'NS-B01' not found in results"
    bus_info = data["results"][0]
    assert bus_info["bus_number"] == "NS-B01", "Returned wrong bus number"
    assert bus_info["route_name"] == "Route 4 - City Center Line"
    assert bus_info["current_occupancy"] == 0, "Expected initial occupancy to be 0"
    print("[+] Passenger search API successfully returns dynamic bus information.")

    # 3. Verify Admin registration form submit works
    print("\n--- 3. Testing Admin Registration ---")
    r_reg1 = s.post(f"{BASE_URL}/admin/register", data={
        "full_name": "Test Admin One",
        "employee_id": "EMP200",
        "email": "admin200@nextstop.com",
        "phone_number": "9000000001",
        "password": "Password123",
        "confirm_password": "Password123"
    }, allow_redirects=True)
    assert r_reg1.status_code == 200, "Admin registration post request failed"
    assert "Admin account created successfully." in r_reg1.text
    print("[+] Admin registration completed successfully.")

    # 4. Verify Duplicate Email is rejected
    print("\n--- 4. Testing Duplicate Email Rejection ---")
    r_dup_email = s.post(f"{BASE_URL}/admin/register", data={
        "full_name": "Test Admin Two",
        "employee_id": "EMP201",
        "email": "admin200@nextstop.com", # Duplicate Email
        "phone_number": "9000000002",
        "password": "Password123",
        "confirm_password": "Password123"
    }, allow_redirects=True)
    assert "Email already registered" in r_dup_email.text
    print("[+] Duplicate Email correctly rejected.")

    # 5. Verify Duplicate Employee ID is rejected
    print("\n--- 5. Testing Duplicate Employee ID Rejection ---")
    r_dup_emp = s.post(f"{BASE_URL}/admin/register", data={
        "full_name": "Test Admin Three",
        "employee_id": "EMP200", # Duplicate Employee ID
        "email": "admin201@nextstop.com",
        "phone_number": "9000000003",
        "password": "Password123",
        "confirm_password": "Password123"
    }, allow_redirects=True)
    assert "Employee ID already registered" in r_dup_emp.text
    print("[+] Duplicate Employee ID correctly rejected.")

    # 6. Verify Duplicate Phone Number is rejected
    print("\n--- 6. Testing Duplicate Phone Number Rejection ---")
    r_dup_phone = s.post(f"{BASE_URL}/admin/register", data={
        "full_name": "Test Admin Four",
        "employee_id": "EMP202",
        "email": "admin202@nextstop.com",
        "phone_number": "9000000001", # Duplicate Phone Number
        "password": "Password123",
        "confirm_password": "Password123"
    }, allow_redirects=True)
    assert "Phone Number already registered" in r_dup_phone.text
    print("[+] Duplicate Phone Number correctly rejected.")

    # 7. Verify newly registered admin login redirects to Admin Dashboard
    print("\n--- 7. Testing Newly Registered Admin Login ---")
    s_admin = requests.Session()
    r_login = s_admin.post(f"{BASE_URL}/login", data={
        "email": "admin200@nextstop.com",
        "password": "Password123",
        "role": "admin"
    }, allow_redirects=True)
    assert r_login.status_code == 200
    assert "Admin Dashboard" in r_login.text or "Admin Control Panel" in r_login.text
    # Check that stats cards are rendered in Admin Dashboard
    assert "Total Conductors" in r_login.text
    assert "Total Admins" in r_login.text
    assert "Registered Buses" in r_login.text
    assert "Active Buses" in r_login.text
    assert "ML Model Status" in r_login.text
    assert "Model Accuracy" in r_login.text
    assert "Last Prediction Time" in r_login.text
    print("[+] Newly registered Admin logged in and redirected to Admin Dashboard successfully.")

    # 8. Verify existing conductor login continues to work
    print("\n--- 8. Testing Existing Conductor Login ---")
    s_cond = requests.Session()
    r_cond_login = s_cond.post(f"{BASE_URL}/login", data={
        "email": "conductor@nextstop.com",
        "password": "Conductor@123",
        "role": "conductor"
    }, allow_redirects=True)
    assert r_cond_login.status_code == 200
    assert "Conductor Console" in r_cond_login.text
    print("[+] Existing Conductor login continues to function properly.")

    print("\n==================================================")
    print("[SUCCESS] ALL REGISTRATION AND PORTAL TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_admin_registration_and_portal()
