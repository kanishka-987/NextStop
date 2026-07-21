# backend/test_auth.py
# Automated tests to verify user authentication system

import requests

BASE_URL = "http://127.0.0.1:5000"

def test_endpoints():
    session = requests.Session()
    
    print("\n--- 1. Testing Landing Page ---")
    r = session.get(f"{BASE_URL}/")
    print(f"Status: {r.status_code}")
    assert r.status_code == 200, "Landing page failed"
    assert "NextStop" in r.text, "Landing page text mismatch"
    print("[+] Landing page loads correctly.")

    print("\n--- 2. Testing Login Page (GET) ---")
    r = session.get(f"{BASE_URL}/login")
    print(f"Status: {r.status_code}")
    assert r.status_code == 200, "Login GET failed"
    assert "Select User Role" in r.text, "Login role tabs not found"
    print("[+] Login page UI loads correctly.")

    print("\n--- 3. Testing Empty Fields Validation ---")
    r = session.post(f"{BASE_URL}/login", data={
        "email": "",
        "password": "",
        "role": ""
    })
    print(f"Status: {r.status_code}")
    assert "All fields are required" in r.text, "Empty fields warning validation failed"
    print("[+] Empty fields server-side validation verified.")

    print("\n--- 4. Testing Wrong Password Validation ---")
    r = session.post(f"{BASE_URL}/login", data={
        "email": "admin@nextstop.com",
        "password": "WrongPassword",
        "role": "admin"
    })
    print(f"Status: {r.status_code}")
    assert "Incorrect password" in r.text, "Wrong password validation failed"
    print("[+] Wrong password server-side validation verified.")

    print("\n--- 5. Testing User Not Found Validation ---")
    r = session.post(f"{BASE_URL}/login", data={
        "email": "nonexistent@nextstop.com",
        "password": "Password123",
        "role": "admin"
    })
    print(f"Status: {r.status_code}")
    assert "User not found" in r.text, "User not found validation failed"
    print("[+] User not found server-side validation verified.")

    print("\n--- 6. Testing Role Mismatch Validation ---")
    r = session.post(f"{BASE_URL}/login", data={
        "email": "admin@nextstop.com",
        "password": "Admin@123",
        "role": "conductor"
    })
    print(f"Status: {r.status_code}")
    assert "Access Denied: This email is not registered as a conductor" in r.text, "Role mismatch validation failed"
    print("[+] Role mismatch validation verified.")

    print("\n--- 7. Testing Admin Login and Dashboard Redirect ---")
    r = session.post(f"{BASE_URL}/login", data={
        "email": "admin@nextstop.com",
        "password": "Admin@123",
        "role": "admin"
    }, allow_redirects=True)
    print(f"Status: {r.status_code}")
    assert "Admin Dashboard" in r.text, "Admin dashboard load failed"
    assert "Active Buses" in r.text, "Dashboard content failed"
    print("[+] Admin login and dashboard redirect successful.")

    print("\n--- 8. Testing Conductor Login and Dashboard Redirect ---")
    # Reset session for a new user login
    conductor_session = requests.Session()
    r = conductor_session.post(f"{BASE_URL}/login", data={
        "email": "conductor@nextstop.com",
        "password": "Conductor@123",
        "role": "conductor"
    }, allow_redirects=True)
    print(f"Status: {r.status_code}")
    assert "Conductor Console" in r.text, "Conductor panel load failed"
    assert "Live Seat Occupancy Map" in r.text, "Seat map not found"
    print("[+] Conductor login and dashboard redirect successful.")

    print("\n--- 9. Testing Route Guard Protection ---")
    # Attempting to access admin page with conductor session
    r = conductor_session.get(f"{BASE_URL}/admin/dashboard", allow_redirects=True)
    assert "Access Denied: This area is restricted to admins" in r.text, "Route guard failed"
    print("[+] Route protection guards verified.")

    print("\n--- 10. Testing Logout Session Destruction ---")
    # Log out
    r = conductor_session.get(f"{BASE_URL}/logout", allow_redirects=True)
    # Check that accessing dashboard now redirects to login page
    r = conductor_session.get(f"{BASE_URL}/conductor/dashboard", allow_redirects=True)
    assert "Please log in to access this page" in r.text, "Session destruction test failed"
    print("[+] Logout session clearance verified.")

    print("\n[SUCCESS] All authentication test scenarios passed successfully!")

if __name__ == "__main__":
    test_endpoints()
