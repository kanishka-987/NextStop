# backend/test_navigation.py
# Automated integration tests for public multi-pages, conductor registration, and protected routes.

import requests
import random
import string

BASE_URL = "http://127.0.0.1:5000"

def random_email():
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"conductor_{rand_str}@nextstop.com"

def test_navigation_and_features():
    s = requests.Session()
    
    print("\n--- 1. Testing Public Pages (Separate Pages) ---")
    pages = [
        ("/", "NextStop:"),
        ("/about", "About NextStop Project"),
        ("/features", "Core System Features"),
        ("/contact", "About NextStop Transit"),
        ("/login", "Welcome Back"),
        ("/register", "Create Conductor Account")
    ]
    for path, expected_text in pages:
        r = s.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, f"Page {path} failed with status {r.status_code}"
        assert expected_text in r.text, f"Text '{expected_text}' not found in {path}"
        print(f"[+] Route {path} loaded successfully.")

    print("\n--- 2. Testing Registration System Validations ---")
    # Duplicate email check using seeded conductor
    r = s.post(f"{BASE_URL}/register", data={
        "full_name": "Test Conductor",
        "email": "conductor@nextstop.com",
        "password": "Password123",
        "confirm_password": "Password123"
    }, allow_redirects=True)
    assert "Email already registered" in r.text, "Duplicate email validation failed"
    print("[+] Duplicate email validation verified.")

    # Password mismatch check
    r = s.post(f"{BASE_URL}/register", data={
        "full_name": "Test Conductor",
        "email": random_email(),
        "password": "Password123",
        "confirm_password": "PasswordMismatch"
    }, allow_redirects=True)
    assert "Passwords do not match" in r.text, "Password mismatch validation failed"
    print("[+] Password mismatch validation verified.")

    # Successful registration
    new_email = random_email()
    r = s.post(f"{BASE_URL}/register", data={
        "full_name": "New Conductor User",
        "email": new_email,
        "password": "Password123",
        "confirm_password": "Password123"
    }, allow_redirects=True)
    assert "Registration successful!" in r.text, "Successful registration failed"
    print(f"[+] Registration successful for {new_email}.")

    print("\n--- 3. Testing Login & Conductor Multi-Page Navigation ---")
    r = s.post(f"{BASE_URL}/login", data={
        "email": new_email,
        "password": "Password123",
        "role": "conductor"
    }, allow_redirects=True)
    assert "Conductor Console" in r.text, "Login for new registered conductor failed"
    print("[+] New conductor login verified.")

    conductor_pages = [
        ("/conductor/dashboard", "Conductor Console"),
        ("/conductor/tickets/generate", "Generate Ticket"),
        ("/conductor/occupancy", "Live Occupancy Dashboard"),
        ("/conductor/profile", "Conductor Profile")
    ]
    for path, expected_text in conductor_pages:
        r = s.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, f"Conductor route {path} failed"
        assert expected_text in r.text, f"Text '{expected_text}' not found in {path}"
        print(f"[+] Conductor multi-page route {path} verified.")

    print("\n--- 4. Testing Admin Multi-Page Navigation ---")
    admin_s = requests.Session()
    r = admin_s.post(f"{BASE_URL}/login", data={
        "email": "admin@nextstop.com",
        "password": "Admin@123",
        "role": "admin"
    }, allow_redirects=True)
    assert "Admin Dashboard" in r.text, "Admin login failed"

    admin_pages = [
        ("/admin/dashboard", "Admin Dashboard"),
        ("/admin/conductors", "Manage Conductors"),
        ("/admin/reports", "Reports & System Analytics"),
        ("/admin/profile", "Admin Profile")
    ]
    for path, expected_text in admin_pages:
        r = admin_s.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, f"Admin route {path} failed"
        assert expected_text in r.text, f"Text '{expected_text}' not found in {path}"
        print(f"[+] Admin multi-page route {path} verified.")

    print("\n[SUCCESS] All Professional UI & Navigation multi-page tests passed successfully!")

if __name__ == "__main__":
    test_navigation_and_features()
