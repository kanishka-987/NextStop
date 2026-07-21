# app.py
# NextStop Web Application Entry Point
# Initializes Flask server, registers auth blueprint, and configures route mappings.

import os
from flask import Flask, render_template, redirect, url_for, session, request, flash
from dotenv import load_dotenv

# Load environment variables from root .env
load_dotenv()

# Initialize Flask app
# Since templates and static are in the root directory relative to this app.py,
# Flask default folders (templates/ and static/) work automatically.
app = Flask(__name__)

# Configure Secret Key for session signing
app.secret_key = os.getenv('SECRET_KEY', '9a7c36a43e8d2e8b9f716c02a4b8f05e')

# Register the Authentication Blueprint
from backend.auth import auth_bp, login_required
app.register_blueprint(auth_bp)

# Register the Ticket Management Blueprint
from backend.tickets import tickets_bp
app.register_blueprint(tickets_bp)

# Check database connection on startup
from backend.db_connection import check_db_status, get_db_connection
db_healthy, db_msg = check_db_status()
if db_healthy:
    print(f"[+] Startup database check: {db_msg}")
else:
    print(f"[WARNING] Startup database check: {db_msg}")
    print("[WARNING] Please check your MySQL service is running and credentials in .env are correct.")

@app.route('/')
def index():
    """Landing Page route."""
    return render_template('landing.html')

@app.route('/about')
def about():
    """About Page route."""
    return render_template('about.html')

@app.route('/features')
def features():
    """Features Section/Page route."""
    return render_template('landing.html', scroll_to_features=True)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact Page route."""
    if request.method == 'POST':
        flash("Thank you for your message! Our team will get back to you soon.", "success")
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    """Protected Admin Dashboard."""
    conn = None
    cursor = None
    buses_occupancy = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM occupancy ORDER BY bus_number ASC")
        buses_occupancy = cursor.fetchall()
    except Exception as e:
        print(f"Error loading admin dashboard metrics: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('admin_dashboard.html', buses=buses_occupancy)

@app.route('/admin/conductors')
@login_required(role='admin')
def admin_conductors():
    """Manage Conductors page for Admin."""
    conn = None
    cursor = None
    conductors = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, full_name, email, created_at FROM users WHERE role = 'conductor' ORDER BY user_id DESC")
        conductors = cursor.fetchall()
    except Exception as e:
        print(f"Error loading conductors: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return render_template('admin_conductors.html', conductors=conductors)

@app.route('/admin/reports')
@login_required(role='admin')
def admin_reports():
    """Reports & Analytics page for Admin."""
    conn = None
    cursor = None
    stats = {'total_tickets': 0, 'total_revenue': 0.0, 'total_conductors': 0}
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total_tickets, COALESCE(SUM(fare), 0) as total_revenue FROM tickets")
        ticket_stats = cursor.fetchone()
        if ticket_stats:
            stats['total_tickets'] = ticket_stats['total_tickets']
            stats['total_revenue'] = float(ticket_stats['total_revenue'])
            
        cursor.execute("SELECT COUNT(*) as conductor_count FROM users WHERE role = 'conductor'")
        c_count = cursor.fetchone()
        if c_count:
            stats['total_conductors'] = c_count['conductor_count']
            
    except Exception as e:
        print(f"Error loading admin reports: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return render_template('admin_reports.html', stats=stats)

@app.route('/admin/profile')
@login_required(role='admin')
def admin_profile():
    """Admin Profile page."""
    return render_template('admin_profile.html')

@app.route('/conductor/dashboard')
@login_required(role='conductor')
def conductor_dashboard():
    """Protected Conductor Dashboard displaying dynamic occupancy status."""
    conn = None
    cursor = None
    bus_status = {
        'bus_number': 'NS-B01',
        'current_occupancy': 0,
        'seat_capacity': 40,
        'seats_available': 40,
        'standing_capacity': 20,
        'standing_available': 20
    }
    recent_tickets = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get active status of conductor's assigned bus (NS-B01 by default)
        cursor.execute("SELECT * FROM occupancy WHERE bus_number = 'NS-B01'")
        db_status = cursor.fetchone()
        if db_status:
            bus_status = db_status
            
        # Get recent tickets for this bus
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE bus_number = 'NS-B01' 
            ORDER BY ticket_id DESC LIMIT 5
        """)
        recent_tickets = cursor.fetchall()
        
    except Exception as e:
        print(f"Error loading conductor dashboard metrics: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('conductor_dashboard.html', bus=bus_status, tickets=recent_tickets)

@app.route('/conductor/profile')
@login_required(role='conductor')
def conductor_profile():
    """Conductor Profile page."""
    return render_template('conductor_profile.html')

@app.context_processor
def inject_user():
    """Injects user information globally into all templates (if logged in)."""
    return dict(
        logged_in=('user_id' in session),
        user_name=session.get('full_name'),
        user_role=session.get('role'),
        user_email=session.get('email')
    )

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error_code=404, error_message="Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error_code=500, error_message="Internal Server Error"), 500

if __name__ == '__main__':
    # Run the application in debug mode on local interface
    app.run(host='127.0.0.1', port=5000, debug=True)
