# app.py
# NextStop Web Application Entry Point
# Initializes Flask server, registers auth, tickets, gps, and ml blueprints, and defines page routes.

import os
from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from dotenv import load_dotenv
from datetime import datetime, date

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', '9a7c36a43e8d2e8b9f716c02a4b8f05e')

# Define Jinja template filter for location aliases
ALIAS_MAP = {
    "Central Station": "Chennai Central",
    "Oak Avenue": "Guindy",
    "Maple Road": "Tambaram",
    "Aisle Street": "Chengalpattu",
    "City Center": "Mahabalipuram",
    "Tech Park": "Kovalam",
    "South Gate": "Sholinganallur",
    "East Airport": "Chennai Airport"
}

@app.template_filter('alias')
def alias_filter(s):
    if not isinstance(s, str):
        return s
    return ALIAS_MAP.get(s.title(), s)

# Register blueprints
from backend.auth import auth_bp, login_required
app.register_blueprint(auth_bp)

from backend.tickets import tickets_bp
app.register_blueprint(tickets_bp)

from backend.gps import gps_bp
app.register_blueprint(gps_bp)

from backend.ml import ml_bp, get_forecast
app.register_blueprint(ml_bp)

# Check database connection on startup
from backend.db_connection import check_db_status, get_db_connection
db_healthy, db_msg = check_db_status()
if db_healthy:
    print(f"[+] Startup database check: {db_msg}")
else:
    print(f"[WARNING] Startup database check: {db_msg}")

@app.route('/')
def index():
    """Landing Page route."""
    return render_template('landing.html')

@app.route('/about')
def about():
    """About Page route - stripped of personal details."""
    return render_template('about.html')

@app.route('/features')
def features():
    """Features Section/Page route."""
    return render_template('landing.html', scroll_to_features=True)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact Page route - professional project description only, no personal details."""
    if request.method == 'POST':
        flash("Thank you for your feedback! Our project team will review it.", "success")
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    """Protected Admin Dashboard."""
    conn = None
    cursor = None
    buses_occupancy = []
    stats = {
        'total_conductors': 0,
        'total_admins': 0,
        'registered_buses': 0,
        'active_buses': 0,
        'current_occupancy': 0,
        'total_capacity': 80,
        'seats_available': 60,
        'standing_capacity': 20,
        'todays_tickets': 0,
        'ml_model_status': 'Offline',
        'model_accuracy': '88.04%',
        'last_prediction_time': '-'
    }
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query active buses
        cursor.execute("SELECT * FROM occupancy ORDER BY bus_number ASC")
        buses_occupancy = cursor.fetchall()
        
        # Get count of total conductors
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'conductor'")
        stats['total_conductors'] = cursor.fetchone()['count']
        
        # Get count of total admins
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
        stats['total_admins'] = cursor.fetchone()['count']

        # Get count of registered buses
        cursor.execute("SELECT COUNT(*) as count FROM occupancy")
        stats['registered_buses'] = cursor.fetchone()['count']

        # Get count of active buses
        cursor.execute("SELECT COUNT(*) as count FROM occupancy WHERE current_occupancy > 0")
        stats['active_buses'] = cursor.fetchone()['count']
        
        # Get count of today's tickets
        cursor.execute("SELECT COUNT(*) as count FROM tickets WHERE ticket_date = CURRENT_DATE()")
        stats['todays_tickets'] = cursor.fetchone()['count']
        
        # Get current occupancy, capacity, and seat availability metrics
        cursor.execute("SELECT COALESCE(SUM(current_occupancy), 0) as occupancy, COALESCE(SUM(seat_capacity + standing_capacity), 0) as capacity, COALESCE(SUM(seats_available), 0) as seats_available, COALESCE(SUM(standing_capacity), 0) as standing_capacity FROM occupancy")
        occ_cap = cursor.fetchone()
        if occ_cap:
            stats['current_occupancy'] = occ_cap['occupancy']
            stats['total_capacity'] = occ_cap['capacity']
            stats['seats_available'] = occ_cap['seats_available']
            stats['standing_capacity'] = occ_cap['standing_capacity']
            
        # Get latest prediction time
        cursor.execute("SELECT prediction_time FROM predictions ORDER BY prediction_id DESC LIMIT 1")
        last_pred = cursor.fetchone()
        if last_pred and last_pred['prediction_time']:
            stats['last_prediction_time'] = last_pred['prediction_time'].strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        print(f"Error loading admin dashboard metrics: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    # ML status details
    model_path = os.path.join('models', 'rf_occupancy_model.pkl')
    metrics_path = os.path.join('models', 'metrics.pkl')
    stats['ml_model_status'] = 'Online' if os.path.exists(model_path) else 'Offline'
    if os.path.exists(metrics_path):
        try:
            import pickle
            with open(metrics_path, 'rb') as f:
                m_data = pickle.load(f)
                stats['model_accuracy'] = f"{m_data.get('accuracy', 88.04)}%"
        except:
            pass
            
    return render_template('admin_dashboard.html', buses=buses_occupancy, stats=stats)

@app.route('/admin/buses')
@login_required(role='admin')
def admin_buses():
    """Manage Buses page for Admin."""
    conn = None
    cursor = None
    buses = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Join buses with occupancy to show current_occupancy
        cursor.execute("""
            SELECT b.*, COALESCE(o.current_occupancy, 0) as current_occupancy 
            FROM buses b 
            LEFT JOIN occupancy o ON b.bus_number = o.bus_number
            ORDER BY b.bus_id DESC
        """)
        buses = cursor.fetchall()
    except Exception as e:
        flash(f"Error loading buses: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    return render_template('bus_management.html', buses=buses)

@app.route('/admin/buses/add', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_add_bus():
    """Add New Bus page for Admin."""
    if request.method == 'POST':
        bus_number = request.form.get('bus_number', '').strip()
        bus_type = request.form.get('bus_type', '').strip()
        route_name = request.form.get('route_name', '').strip()
        seat_capacity = request.form.get('seat_capacity', '60').strip()
        standing_capacity = request.form.get('standing_capacity', '20').strip()
        status = request.form.get('status', 'active').strip()
        
        try:
            seat_capacity = int(seat_capacity)
            standing_capacity = int(standing_capacity)
            if seat_capacity < 0 or standing_capacity < 0 or (seat_capacity + standing_capacity) <= 0:
                raise ValueError("Invalid capacities.")
        except ValueError:
            flash("Capacities must be valid positive numbers and cannot both be zero.", "warning")
            return redirect(url_for('admin_add_bus'))
            
        if not bus_number:
            flash("Bus number is required.", "warning")
            return redirect(url_for('admin_add_bus'))
            
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            conn.autocommit = False
            cursor = conn.cursor(dictionary=True)
            
            # 1. Insert into buses
            cursor.execute("""
                INSERT INTO buses (bus_number, bus_type, route_name, seat_capacity, standing_capacity, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (bus_number, bus_type, route_name, seat_capacity, standing_capacity, status))
            
            # 2. Insert into occupancy
            cursor.execute("""
                INSERT INTO occupancy (bus_number, current_occupancy, seat_capacity, seats_available, standing_capacity, standing_available)
                VALUES (%s, 0, %s, %s, %s, %s)
            """, (bus_number, seat_capacity, seat_capacity, standing_capacity, standing_capacity))
            
            # 3. Create physical seats
            if seat_capacity > 0:
                seat_values = [(bus_number, i, 'Available') for i in range(1, seat_capacity + 1)]
                cursor.executemany("""
                    INSERT INTO seat_status (bus_number, seat_number, status)
                    VALUES (%s, %s, %s)
                """, seat_values)
                
            conn.commit()
            flash(f"Bus {bus_number} added successfully!", "success")
            return redirect(url_for('admin_buses'))
        except mysql.connector.IntegrityError:
            if conn: conn.rollback()
            flash(f"Bus number '{bus_number}' already exists.", "danger")
            return redirect(url_for('admin_add_bus'))
        except Exception as e:
            if conn: conn.rollback()
            flash(f"Error adding bus: {e}", "danger")
            return redirect(url_for('admin_add_bus'))
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
    return render_template('add_bus.html')

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
    """Protected Conductor Dashboard displaying dynamic occupancy status, live seat map, and ML crowd prediction."""
    conn = None
    cursor = None
    buses = []
    
    bus_number = request.args.get('bus_number', session.get('selected_bus', 'NS-B01'))
    session['selected_bus'] = bus_number

    bus_status = {
        'bus_number': bus_number,
        'current_occupancy': 0,
        'seat_capacity': 60,
        'seats_available': 60,
        'standing_capacity': 20,
        'standing_available': 20,
        'standing_occupancy': 0,
        'current_stop': 'Central Station'
    }
    recent_tickets = []
    seats = []
    gps_info = {"latitude": 12.9716, "longitude": 77.5946, "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    forecast = {"predicted_occupancy": 15, "crowd_level": "Low Crowd", "accuracy": 92.5}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch active buses for dropdown selection
        cursor.execute("SELECT bus_number, route_name FROM buses WHERE status = 'active' ORDER BY bus_number ASC")
        buses = cursor.fetchall()
        
        # If the currently selected bus doesn't exist or isn't active, pick the first one
        valid_buses = [b['bus_number'] for b in buses]
        if bus_number not in valid_buses and valid_buses:
            bus_number = valid_buses[0]
            session['selected_bus'] = bus_number
            bus_status['bus_number'] = bus_number

        # Get active status of the selected bus
        cursor.execute("SELECT * FROM occupancy WHERE bus_number = %s", (bus_number,))
        db_status = cursor.fetchone()
        if db_status:
            bus_status.update(db_status)
            
            # Fetch latest stop from GPS bus_location
            cursor.execute("SELECT current_stop, latitude, longitude, last_updated FROM bus_location WHERE bus_number = %s", (bus_number,))
            gps_rec = cursor.fetchone()
            if gps_rec:
                bus_status['current_stop'] = gps_rec['current_stop']
                gps_info = {
                    "latitude": float(gps_rec['latitude']),
                    "longitude": float(gps_rec['longitude']),
                    "last_updated": gps_rec['last_updated'].strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Count currently occupied seats in seat_status
            cursor.execute("SELECT COUNT(*) as count FROM seat_status WHERE bus_number = %s AND status = 'Occupied'", (bus_number,))
            occupied_seats_count = cursor.fetchone()['count']
            bus_status['standing_occupancy'] = max(0, bus_status['current_occupancy'] - occupied_seats_count)
            
            # Fetch seats map
            cursor.execute("SELECT seat_number, status FROM seat_status WHERE bus_number = %s ORDER BY seat_number ASC", (bus_number,))
            seats = cursor.fetchall()

        # Get recent tickets for this bus
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE bus_number = %s 
            ORDER BY ticket_id DESC LIMIT 5
        """, (bus_number,))
        recent_tickets = cursor.fetchall()
        
        # Predict Occupancy
        try:
            forecast_data = get_forecast(bus_number, bus_status['current_stop'])
            forecast.update(forecast_data)
        except Exception as e:
            print(f"ML Forecast error: {e}")
            
    except Exception as e:
        flash(f"Error loading dashboard: {e}", "danger")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('conductor_dashboard.html', buses=buses, bus=bus_status, tickets=recent_tickets, seats=seats, gps=gps_info, forecast=forecast)

@app.route('/conductor/profile')
@login_required(role='conductor')
def conductor_profile():
    """Conductor Profile page."""
    return render_template('conductor_profile.html')

@app.route('/gps/tracking')
@login_required()
def gps_tracking():
    """
    Renders the interactive live map bus tracking page.
    """
    bus_number = request.args.get('bus_number', 'NS-B01')
    return render_template('gps_tracking.html', bus_number=bus_number)

@app.route('/trip-history')
@login_required()
def trip_history():
    """
    Renders passenger transit history with shift filters.
    """
    bus_filter = request.args.get('bus_number', '').strip()
    time_filter = request.args.get('time_filter', 'today').strip()

    conn = None
    cursor = None
    tickets_list = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = "SELECT * FROM tickets WHERE 1=1"
        params = []
        
        if bus_filter:
            query += " AND bus_number = %s"
            params.append(bus_filter)
            
        if time_filter == 'today':
            query += " AND ticket_date = CURRENT_DATE()"
        elif time_filter == 'shift':
            # Current Shift (mocked as last 8 hours)
            query += " AND ticket_date = CURRENT_DATE() AND ticket_time >= SUBTIME(CURTIME(), '08:00:00')"
            
        query += " ORDER BY ticket_id DESC"
        cursor.execute(query, params)
        tickets_list = cursor.fetchall()
        
    except Exception as e:
        print(f"Error querying trip history: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('trip_history.html', tickets=tickets_list, bus_filter=bus_filter, time_filter=time_filter)

@app.route('/passenger')
def passenger_home():
    """Passenger Home page (Public Portal)"""
    return render_template('passenger_home.html')

@app.route('/passenger/search')
def passenger_search():
    """
    JSON API for Passenger Portal.
    Searches by bus_number or route.
    Retrieves current occupancy, live location, predictions, ETA, and crowd indicators.
    """
    query = request.args.get('q', '').strip().lower()
    
    # Predefined stop list order for routing sequence
    ROUTE_STOPS = ['Central Station', 'Oak Avenue', 'Maple Road', 'Aisle Street', 'City Center', 'Tech Park', 'South Gate', 'East Airport']
    STOP_COORDINATES = {
        'Central Station': (13.0827, 80.2707),
        'Oak Avenue': (13.0067, 80.2206),
        'Maple Road': (12.9249, 80.1000),
        'Aisle Street': (12.6819, 79.9788),
        'City Center': (12.6269, 80.1927),
        'Tech Park': (12.7948, 80.2505),
        'South Gate': (12.9010, 80.2279),
        'East Airport': (12.9716, 80.1836)
    }

    conn = None
    cursor = None
    results = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Select all active buses joined with occupancy
        cursor.execute("""
            SELECT o.*, b.route_name 
            FROM occupancy o
            JOIN buses b ON o.bus_number = b.bus_number
            WHERE b.status = 'active'
        """)
        buses = cursor.fetchall()
        
        for bus in buses:
            bus_num = bus['bus_number']
            route_name = bus['route_name']
            source_stop = "Central Station"
            destination_stop = "East Airport"
            
            # Check if query matches bus number or route name
            if query and (query.lower() not in bus_num.lower() and query.lower() not in route_name.lower()):
                continue
                
            # Fetch latest location of the bus
            cursor.execute("SELECT * FROM bus_location WHERE bus_number = %s ORDER BY last_updated DESC LIMIT 1", (bus_num,))
            loc = cursor.fetchone()
            
            # Fetch latest prediction of the bus
            cursor.execute("SELECT * FROM predictions WHERE bus_number = %s ORDER BY prediction_time DESC LIMIT 1", (bus_num,))
            pred = cursor.fetchone()
            
            current_stop = loc['current_stop'] if loc else 'Central Station'
            latitude = loc['latitude'] if loc else 13.0827
            longitude = loc['longitude'] if loc else 80.2707
            
            # Determine next stop in the sequence
            next_stop = 'East Airport'
            if current_stop in ROUTE_STOPS:
                idx = ROUTE_STOPS.index(current_stop)
                if idx < len(ROUTE_STOPS) - 1:
                    next_stop = ROUTE_STOPS[idx + 1]
                else:
                    next_stop = 'Central Station' # loop back
            
            # Calculate ETA in minutes based on distance
            eta = "N/A"
            if next_stop in STOP_COORDINATES:
                next_lat, next_lon = STOP_COORDINATES[next_stop]
                import math
                dist = math.sqrt((latitude - next_lat)**2 + (longitude - next_lon)**2)
                minutes = int(round(dist * 200))
                eta = f"{max(1, minutes)} mins"
                
            # Determine crowd level & indicator using predictions or current occupancy
            base_predicted = pred['predicted_occupancy'] if pred else bus['current_occupancy']
            pred_15 = int(base_predicted)
            pred_30 = min(80, int(pred_15 * 1.1) + 2) if pred_15 > 0 else 5

            # Calculate the crowd level based on predicted occupancy (15m) relative to total capacity of 80:
            if pred_15 >= 80:
                crowd_level = "Bus Full"
                crowd_indicator = "🔴"
                crowd_color = "danger"
            elif pred_15 > 56:
                crowd_level = "High"
                crowd_indicator = "🔴"
                crowd_color = "danger"
            elif pred_15 > 32:
                crowd_level = "Medium"
                crowd_indicator = "🟡"
                crowd_color = "warning"
            else:
                crowd_level = "Low"
                crowd_indicator = "🟢"
                crowd_color = "success"

            pred_seats_available = max(0, 60 - pred_15)
            standing_warning = pred_15 > 60

            results.append({
                'bus_number': bus_num,
                'route_name': route_name,
                'source_stop': source_stop,
                'destination_stop': destination_stop,
                'current_stop': current_stop,
                'next_stop': next_stop,
                'current_occupancy': bus['current_occupancy'],
                'seat_capacity': bus['seat_capacity'],
                'seats_available': bus['seats_available'],
                'standing_capacity': bus['standing_capacity'],
                'standing_available': bus['standing_available'],
                'pred_15': pred_15,
                'pred_30': pred_30,
                'pred_seats_available': pred_seats_available,
                'standing_warning': standing_warning,
                'crowd_level': crowd_level,
                'crowd_indicator': crowd_indicator,
                'crowd_color': crowd_color,
                'eta': eta,
                'latitude': latitude,
                'longitude': longitude,
                'gps_status': 'Online' if loc else 'Offline'
            })
            
    except Exception as e:
        print(f"Error searching passenger bus data: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return jsonify({'results': results})

@app.context_processor
def inject_user():
    """Injects user information globally into all templates."""
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
    app.run(host='127.0.0.1', port=5000, debug=True)
