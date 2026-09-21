# backend/gps.py
# NextStop Project - GPS Tracking and Passenger Exit Management Blueprint
# Continuously processes coordinates, nearest stop detection, and auto-completes passenger trips.

import math
from flask import Blueprint, request, jsonify, session
from backend.db_connection import get_db_connection
from backend.auth import login_required
import mysql.connector
from datetime import datetime

gps_bp = Blueprint('gps', __name__)

# Predefined stops mapped to Chennai-region real-world coordinates for Demo visual route
STOP_COORDINATES = {
    'Central Station': (13.0827, 80.2707), # Chennai Central
    'Oak Avenue': (13.0067, 80.2206),      # Guindy
    'Maple Road': (12.9249, 80.1143),      # Tambaram
    'Aisle Street': (12.6819, 79.9788),    # Chengalpattu
    'City Center': (12.6269, 80.1927),     # Mahabalipuram
    'Tech Park': (12.7948, 80.2505),       # Kovalam
    'South Gate': (12.9010, 80.2279),      # Sholinganallur
    'East Airport': (12.9716, 80.1836)     # Chennai Airport
}

def detect_nearest_stop(latitude, longitude):
    """
    Computes Euclidean distance to locate the nearest predefined stop.
    """
    min_dist = float('inf')
    nearest_stop = list(STOP_COORDINATES.keys())[0]
    for stop, (stop_lat, stop_lon) in STOP_COORDINATES.items():
        dist = math.sqrt((latitude - stop_lat)**2 + (longitude - stop_lon)**2)
        if dist < min_dist:
            min_dist = dist
            nearest_stop = stop
    return nearest_stop

@gps_bp.route('/gps/update', methods=['POST'])
def update_gps():
    """
    Receives latitude and longitude from active bus conductor consoles.
    Updates location, stop registries, and triggers passenger exits on arrival.
    """
    data = request.get_json() or {}
    latitude_str = data.get('latitude') or request.form.get('latitude')
    longitude_str = data.get('longitude') or request.form.get('longitude')
    bus_number = data.get('bus_number') or request.form.get('bus_number') or 'NS-B01'

    demo_mode = data.get('demo_mode', False)
    if isinstance(demo_mode, str):
        demo_mode = demo_mode.lower() == 'true'

    if not latitude_str or not longitude_str:
        return jsonify({"success": False, "error": "Missing latitude or longitude"}), 400

    try:
        latitude = float(latitude_str)
        longitude = float(longitude_str)
    except ValueError:
        return jsonify({"success": False, "error": "Invalid numerical coordinates"}), 400

    detected_stop = detect_nearest_stop(latitude, longitude)
    conn = None
    cursor = None
    exited_passengers_total = 0

    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)

        # 1. Update bus_location table (Latest single location entry per bus)
        cursor.execute("""
            INSERT INTO bus_location (bus_number, latitude, longitude, current_stop, is_demo)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                latitude = VALUES(latitude),
                longitude = VALUES(longitude),
                current_stop = VALUES(current_stop),
                is_demo = VALUES(is_demo)
        """, (bus_number, latitude, longitude, detected_stop, demo_mode))

        # 2. Check passenger exits (Destination Stop matches Current Stop)
        # Fetch active tickets matching destination stop on this bus
        cursor.execute("""
            SELECT ticket_id, passenger_count, assigned_seat 
            FROM tickets 
            WHERE bus_number = %s AND destination_stop = %s AND ticket_status = 'Active'
            FOR UPDATE
        """, (bus_number, detected_stop))
        matching_tickets = cursor.fetchall()

        now_time = datetime.now().strftime('%H:%M:%S')

        for ticket in matching_tickets:
            ticket_id = ticket['ticket_id']
            p_count = ticket['passenger_count']
            exited_passengers_total += p_count

            # Mark ticket as Completed and record exit time
            cursor.execute("""
                UPDATE tickets 
                SET ticket_status = 'Completed', exit_time = %s 
                WHERE ticket_id = %s
            """, (now_time, ticket_id))

            # Free assigned seats in seat_status table
            cursor.execute("""
                UPDATE seat_status 
                SET status = 'Available', ticket_id = NULL, boarding_stop = NULL, destination_stop = NULL
                WHERE ticket_id = %s
            """, (ticket_id,))

        # 3. Update occupancy capacities if passengers exited
        if exited_passengers_total > 0:
            cursor.execute("SELECT * FROM occupancy WHERE bus_number = %s FOR UPDATE", (bus_number,))
            bus_rec = cursor.fetchone()
            
            if bus_rec:
                seat_capacity = bus_rec['seat_capacity']
                standing_capacity = bus_rec['standing_capacity']
                
                # Fetch currently occupied physical seats
                cursor.execute("SELECT COUNT(*) as count FROM seat_status WHERE bus_number = %s AND status = 'Occupied'", (bus_number,))
                occupied_seats = cursor.fetchone()['count']
                
                # Recalculate Occupancy
                new_occupancy = max(0, bus_rec['current_occupancy'] - exited_passengers_total)
                seats_available = max(0, seat_capacity - occupied_seats)
                standing_occupancy = max(0, new_occupancy - seat_capacity)
                standing_available = max(0, standing_capacity - standing_occupancy)

                cursor.execute("""
                    UPDATE occupancy 
                    SET current_occupancy = %s, seats_available = %s, standing_available = %s 
                    WHERE bus_number = %s
                """, (new_occupancy, seats_available, standing_available, bus_number))

        conn.commit()
        return jsonify({
            "success": True,
            "detected_stop": detected_stop,
            "exited_passengers": exited_passengers_total
        })

    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": f"Transaction failed: {str(e)}"}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@gps_bp.route('/gps/location')
def get_location():
    """
    Returns latest GPS locations.
    """
    bus_number = request.args.get('bus_number', 'NS-B01')
    conn = None
    cursor = None
    location_data = {}

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bus_location WHERE bus_number = %s", (bus_number,))
        res = cursor.fetchone()
        if res:
            location_data = {
                "bus_number": res['bus_number'],
                "latitude": float(res['latitude']),
                "longitude": float(res['longitude']),
                "current_stop": res['current_stop'],
                "is_demo": bool(res.get('is_demo', False)),
                "last_updated": res['last_updated'].strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            # Default fallback coordinates
            location_data = {
                "bus_number": bus_number,
                "latitude": 13.0827,
                "longitude": 80.2707,
                "current_stop": "Central Station",
                "is_demo": False,
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return jsonify(location_data)
