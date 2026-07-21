# backend/auth.py
# NextStop Project Authentication Blueprint
# Handles routes for Login, Logout, Session validation, and access control.

from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from backend.db_connection import get_db_connection
import mysql.connector
import re


# Create a Flask Blueprint for auth module
auth_bp = Blueprint('auth', __name__)

def login_required(role=None):
    """
    Decorator to restrict access to logged-in users.
    Optionally enforces role membership ('admin' or 'conductor').
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                flash("Please log in to access this page.", "danger")
                return redirect(url_for('auth.login'))
            
            # Check if user role matches required role
            if role and session.get('role') != role:
                flash(f"Access Denied: This area is restricted to {role}s.", "danger")
                # Redirect to their own dashboard if logged in but wrong role
                if session.get('role') == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif session.get('role') == 'conductor':
                    return redirect(url_for('conductor_dashboard'))
                return redirect(url_for('auth.login'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect them to their respective dashboard
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'conductor':
            return redirect(url_for('conductor_dashboard'))

    if request.method == 'POST':
        # Retrieve form data
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')

        # 1. Validation: Empty fields
        if not email or not password or not role:
            flash("All fields are required. Please fill in email, password, and role.", "warning")
            return render_template('login.html', email=email, role=role)

        # 2. Database validation
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Query user by email
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            # Close db resources
            cursor.close()
            conn.close()
            
            # 3. Validation: User not found
            if not user:
                flash("User not found. Please verify your email.", "danger")
                return render_template('login.html', email=email, role=role)
                
            # 4. Validation: Wrong password
            if not check_password_hash(user['password'], password):
                flash("Incorrect password. Please try again.", "danger")
                return render_template('login.html', email=email, role=role)
                
            # 5. Validation: Role mismatch
            if user['role'] != role:
                flash(f"Access Denied: This email is not registered as a {role}.", "danger")
                return render_template('login.html', email=email, role=role)

            # Successful login: Set up Flask session
            session.clear()
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            session['role'] = user['role']

            flash(f"Welcome back, {user['full_name']}!", "success")
            
            # Redirect to respective dashboard
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'conductor':
                return redirect(url_for('conductor_dashboard'))

        except mysql.connector.Error as err:
            flash(f"Database error occurred: {err}", "danger")
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return render_template('login.html', email=email, role=role)

    # Render login page (GET request)
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    # Clear the Flask session dict
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'conductor':
            return redirect(url_for('conductor_dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 1. Validation: Empty fields
        if not full_name or not email or not password or not confirm_password:
            flash("All fields are required. Please fill in the registration form completely.", "warning")
            return render_template('register.html', full_name=full_name, email=email)

        # 2. Validation: Invalid email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("Invalid email format. Please enter a valid email address.", "warning")
            return render_template('register.html', full_name=full_name, email=email)

        # 3. Validation: Password length
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return render_template('register.html', full_name=full_name, email=email)

        # 4. Validation: Confirm password match
        if password != confirm_password:
            flash("Passwords do not match. Please verify your password.", "warning")
            return render_template('register.html', full_name=full_name, email=email)

        # 5. Database validation: Duplicate email
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                cursor.close()
                conn.close()
                flash("Email already registered. Please choose another or log in.", "danger")
                return render_template('register.html', full_name=full_name, email=email)
                
            # Create user (Conductor role only)
            hashed_pw = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (full_name, email, password, role)
                VALUES (%s, %s, %s, 'conductor')
            """, (full_name, email, hashed_pw))
            conn.commit()
            
            cursor.close()
            conn.close()
            
            flash("Registration successful! Please log in with your credentials.", "success")
            return redirect(url_for('auth.login'))

        except mysql.connector.Error as err:
            if cursor: cursor.close()
            if conn: conn.close()
            flash(f"Database error during registration: {err}", "danger")
            return render_template('register.html', full_name=full_name, email=email)

    return render_template('register.html')

