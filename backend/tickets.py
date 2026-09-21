# backend/tickets.py
# NextStop Project - Ticket Management Blueprint
# Implements automatic seat allocation, standing capacity overflow, and real-time occupancy.

import os
from flask import Blueprint, render_template, redirect, url_for, request, session, flash, jsonify
from backend.db_connection import get_db_connection
from backend.auth import login_required
import mysql.connector
from datetime import datetime

tickets_bp = Blueprint('tickets', __name__)

@tickets_bp.route('/conductor/tickets/generate', methods=['GET', 'POST'])
@login_required(role='conductor')
def generate_ticket():
    """
    Renders the ticket generation form for conductors.
    Handles seating capacity (60) and standing capacity (20) auto-allocation.
    """
    conn = None
    cursor = None
    
    # Fetch active buses for dropdown selection
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.bus_number, o.seat_capacity, o.standing_capacity, o.current_occupancy, b.route_name 
            FROM occupancy o
            JOIN buses b ON o.bus_number = b.bus_number
            WHERE b.status = 'active'
        """)
        buses = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error fetching buses: {err}", "danger")
        buses = []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    if request.method == 'POST':
        # Retrieve form data
        bus_number = request.form.get('bus_number', '').strip()
        source_stop = request.form.get('source_stop', '').strip()
        destination_stop = request.form.get('destination_stop', '').strip()
        passenger_count_str = request.form.get('passenger_count', '').strip()
        fare_str = request.form.get('fare', '').strip()
        ticket_date = request.form.get('ticket_date', '').strip()
        ticket_time = request.form.get('ticket_time', '').strip()

        # 1. Validation: Empty Fields
        if not (bus_number and source_stop and destination_stop and passenger_count_str and ticket_date and ticket_time):
            flash("All fields except fare are required. Please fill in the ticket form completely.", "warning")
            return render_template('generate_ticket.html', buses=buses, bus_number=bus_number, 
                                   source_stop=source_stop, destination_stop=destination_stop, 
                                   passenger_count=passenger_count_str, fare=fare_str, 
                                   ticket_date=ticket_date, ticket_time=ticket_time)

        # 2. Validation: Numeric sanity checks
        try:
            passenger_count = int(passenger_count_str)
            if passenger_count <= 0:
                raise ValueError("Passenger count must be a positive integer.")
        except ValueError:
            flash("Invalid passenger count. Must be a positive whole number.", "warning")
            return render_template('generate_ticket.html', buses=buses, bus_number=bus_number, 
                                   source_stop=source_stop, destination_stop=destination_stop, 
                                   passenger_count=passenger_count_str, fare=fare_str, 
                                   ticket_date=ticket_date, ticket_time=ticket_time)

        # 3. Automatic Fare Calculation
        ROUTE_STOPS = [
            'Central Station', 'Oak Avenue', 'Maple Road', 'Aisle Street',
            'City Center', 'Tech Park', 'South Gate', 'East Airport'
        ]
        try:
            src_idx = ROUTE_STOPS.index(source_stop)
            dst_idx = ROUTE_STOPS.index(destination_stop)
            segments = dst_idx - src_idx
            if segments <= 0:
                raise ValueError("Invalid destination stop.")
            
            base_fare_per_pax = 15 + (segments - 1) * 5
            fare = float(base_fare_per_pax * passenger_count)
            fare_str = str(fare)
        except ValueError:
            flash("Invalid source or destination stop selected.", "warning")
            return render_template('generate_ticket.html', buses=buses, bus_number=bus_number, 
                                   source_stop=source_stop, destination_stop=destination_stop, 
                                   passenger_count=passenger_count_str, fare=fare_str, 
                                   ticket_date=ticket_date, ticket_time=ticket_time)

        # 3. Capacity verification and database transaction
        try:
            conn = get_db_connection()
            conn.autocommit = False
            cursor = conn.cursor(dictionary=True)
            
            # Fetch current occupancy records for target bus using lock (SELECT ... FOR UPDATE)
            cursor.execute("SELECT * FROM occupancy WHERE bus_number = %s FOR UPDATE", (bus_number,))
            bus_record = cursor.fetchone()
            
            if not bus_record:
                conn.rollback()
                flash(f"Error: Selected bus '{bus_number}' does not exist in occupancy registries.", "danger")
                return render_template('generate_ticket.html', buses=buses)
            
            seat_capacity = bus_record['seat_capacity']  # 60
            standing_capacity = bus_record['standing_capacity']  # 20
            current_occupancy = bus_record['current_occupancy']
            total_capacity = seat_capacity + standing_capacity  # 80
            
            # Block ticket generation only when combined capacity is exceeded
            if current_occupancy + passenger_count > total_capacity:
                conn.rollback()
                # Exact requested text to display: "Bus has reached its maximum capacity. Ticket cannot be generated."
                flash("Bus has reached its maximum capacity. Ticket cannot be generated.", "danger")
                return render_template('generate_ticket.html', buses=buses, bus_number=bus_number, 
                                       source_stop=source_stop, destination_stop=destination_stop, 
                                       passenger_count=passenger_count_str, fare=fare_str, 
                                       ticket_date=ticket_date, ticket_time=ticket_time)

            # Query available physical seats
            cursor.execute("""
                SELECT seat_number FROM seat_status 
                WHERE bus_number = %s AND status = 'Available' 
                ORDER BY seat_number ASC FOR UPDATE
            """, (bus_number,))
            available_seats = [row['seat_number'] for row in cursor.fetchall()]
            
            # Allocate seats
            allocated_seats = available_seats[:passenger_count]
            standing_count = max(0, passenger_count - len(allocated_seats))
            
            if allocated_seats:
                seat_str = ", ".join(map(str, allocated_seats))
                if standing_count > 0:
                    seat_str += f" (Plus {standing_count} Standing)"
                    # Show warning when all seats are full and some must stand
                    flash("All seats are occupied. Passenger will travel as Standing.", "warning")
            else:
                seat_str = "Standing"
                flash("All seats are occupied. Passenger will travel as Standing.", "warning")

            now_time = datetime.now().strftime('%H:%M:%S')

            # Insert Ticket record (including assigned_seat, status, boarding_time)
            insert_ticket_query = """
            INSERT INTO tickets (bus_number, source_stop, destination_stop, passenger_count, fare, ticket_date, ticket_time, assigned_seat, ticket_status, boarding_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s)
            """
            cursor.execute(insert_ticket_query, (
                bus_number, source_stop, destination_stop, passenger_count, fare, ticket_date, ticket_time, seat_str, now_time
            ))
            ticket_id = cursor.lastrowid
            
            # Update seat status table for allocated seats
            for seat_num in allocated_seats:
                cursor.execute("""
                    UPDATE seat_status 
                    SET status = 'Occupied', ticket_id = %s, boarding_stop = %s, destination_stop = %s
                    WHERE bus_number = %s AND seat_number = %s
                """, (ticket_id, source_stop, destination_stop, bus_number, seat_num))
            
            # Recalculate Occupancies:
            new_occupancy = current_occupancy + passenger_count
            seats_available = max(0, seat_capacity - (seat_capacity - len(available_seats) + len(allocated_seats)))
            standing_occupancy = max(0, new_occupancy - seat_capacity)
            standing_available = max(0, standing_capacity - standing_occupancy)

            # Update Occupancy table
            update_occupancy_query = """
            UPDATE occupancy 
            SET current_occupancy = %s, seats_available = %s, standing_available = %s 
            WHERE bus_number = %s
            """
            cursor.execute(update_occupancy_query, (
                new_occupancy, seats_available, standing_available, bus_number
            ))
            
            conn.commit()
            flash("Ticket generated successfully!", "success")
            
            # Fetch newly created ticket details for displaying receipts
            cursor.execute("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
            new_ticket = cursor.fetchone()
            
            return render_template('generate_ticket.html', buses=buses, generated_ticket=new_ticket)

        except mysql.connector.Error as err:
            if conn: conn.rollback()
            flash(f"Database error during transaction: {err}", "danger")
            return render_template('generate_ticket.html', buses=buses)
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # Default GET rendering: prefill dates & times to local system clock
    now = datetime.now()
    default_date = now.strftime('%Y-%m-%d')
    default_time = now.strftime('%H:%M')
    return render_template('generate_ticket.html', buses=buses, ticket_date=default_date, ticket_time=default_time)

@tickets_bp.route('/conductor/occupancy')
@login_required(role='conductor')
def occupancy_dashboard():
    """
    Renders the live occupancy dashboard for conductors.
    """
    bus_number = request.args.get('bus_number', 'NS-B01')
    conn = None
    cursor = None
    bus_status = None
    buses = []
    seats = []
    recent_tickets = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get list of all buses
        cursor.execute("SELECT bus_number FROM occupancy ORDER BY bus_number ASC")
        buses = cursor.fetchall()
        
        # Fetch status for selected bus
        cursor.execute("SELECT * FROM occupancy WHERE bus_number = %s", (bus_number,))
        bus_status = cursor.fetchone()
        
        if bus_status:
            seat_capacity = bus_status['seat_capacity']  # 60
            standing_capacity = bus_status['standing_capacity']  # 20
            current_occupancy = bus_status['current_occupancy']
            total_capacity = seat_capacity + standing_capacity  # 80
            
            # Count currently occupied seats in seat_status
            cursor.execute("SELECT COUNT(*) as count FROM seat_status WHERE bus_number = %s AND status = 'Occupied'", (bus_number,))
            occupied_seats_count = cursor.fetchone()['count']
            
            # Calculate seated and standing counts
            current_seated = occupied_seats_count
            current_standing = max(0, current_occupancy - seat_capacity)
            
            bus_status['current_seated'] = current_seated
            bus_status['current_standing'] = current_standing
            bus_status['total_capacity'] = total_capacity
            bus_status['available_standing'] = max(0, standing_capacity - current_standing)
            bus_status['occupancy_percentage'] = round((current_occupancy / total_capacity) * 100, 1) if total_capacity > 0 else 0
            
            # Bus Status: Available / Nearly Full / Full
            if current_occupancy >= total_capacity:
                bus_status['status_label'] = 'Full'
            elif current_occupancy >= (total_capacity * 0.8):
                bus_status['status_label'] = 'Nearly Full'
            else:
                bus_status['status_label'] = 'Available'
                
            # Fetch physical seats for the live seat map (60 Seats total)
            cursor.execute("""
                SELECT seat_number, status FROM seat_status 
                WHERE bus_number = %s 
                ORDER BY seat_number ASC
            """, (bus_number,))
            seats = cursor.fetchall()
        
        # Fetch recent tickets for selected bus
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE bus_number = %s 
            ORDER BY ticket_id DESC LIMIT 10
        """, (bus_number,))
        recent_tickets = cursor.fetchall()
        
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('occupancy_dashboard.html', 
                           buses=buses, 
                           bus=bus_status, 
                           seats=seats,
                           selected_bus_number=bus_number,
                           tickets=recent_tickets)

@tickets_bp.route('/conductor/occupancy/data')
@login_required()
def occupancy_data():
    """
    Returns JSON occupancy statistics and seat statuses for real-time dashboard updates.
    """
    bus_number = request.args.get('bus_number', 'NS-B01')
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM occupancy WHERE bus_number = %s", (bus_number,))
        bus = cursor.fetchone()
        if not bus:
            return jsonify({"success": False, "error": "Bus not found"})
            
        cursor.execute("SELECT COUNT(*) as count FROM seat_status WHERE bus_number = %s AND status = 'Occupied'", (bus_number,))
        occupied_seats = cursor.fetchone()['count']
        
        current_seated = occupied_seats
        current_standing = max(0, bus['current_occupancy'] - bus['seat_capacity'])
        total_capacity = bus['seat_capacity'] + bus['standing_capacity']
        
        cursor.execute("SELECT seat_number, status FROM seat_status WHERE bus_number = %s ORDER BY seat_number ASC", (bus_number,))
        seats = cursor.fetchall()
        
        return jsonify({
            "success": True,
            "bus_number": bus['bus_number'],
            "current_occupancy": bus['current_occupancy'],
            "seat_capacity": bus['seat_capacity'],
            "seats_available": bus['seats_available'],
            "standing_capacity": bus['standing_capacity'],
            "standing_available": bus['standing_available'],
            "current_seated": current_seated,
            "current_standing": current_standing,
            "total_capacity": total_capacity,
            "occupancy_percentage": round((bus['current_occupancy'] / total_capacity) * 100, 1) if total_capacity > 0 else 0,
            "seats": seats
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@tickets_bp.route('/api/tickets/generate', methods=['POST'])
def api_generate_ticket():
    if session.get('role') != 'passenger':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    bus_number = data.get('bus_number', 'NS-B01')
    source_stop = data.get('source_stop')
    destination_stop = data.get('destination_stop')
    
    if not source_stop or not destination_stop:
        return jsonify({'success': False, 'error': 'Missing source or destination'}), 400
        
    user_id = session.get('user_id')
    now = datetime.now()
    ticket_date = now.strftime('%Y-%m-%d')
    ticket_time = now.strftime('%H:%M:%S')
    now_time = now.strftime('%H:%M:%S')
    
    fare = 15.00 # basic flat fare for passenger tickets
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor(dictionary=True)
        
        # Check occupancy
        cursor.execute("SELECT * FROM occupancy WHERE bus_number = %s FOR UPDATE", (bus_number,))
        bus = cursor.fetchone()
        
        if not bus:
            return jsonify({'success': False, 'error': 'Bus not found'}), 404
            
        seat_capacity = bus['seat_capacity']
        standing_capacity = bus['standing_capacity']
        total_capacity = seat_capacity + standing_capacity
        current_occupancy = bus['current_occupancy']
        
        if current_occupancy >= total_capacity:
            return jsonify({'success': False, 'error': 'Bus is at maximum capacity. No more passengers can be added.'}), 400
            
        # Determine if seat is available
        cursor.execute("SELECT seat_number FROM seat_status WHERE bus_number = %s AND status = 'Available' ORDER BY seat_number ASC LIMIT 1", (bus_number,))
        seat_row = cursor.fetchone()
        
        assigned_seat = None
        is_standing = False
        
        if seat_row:
            assigned_seat = seat_row['seat_number']
        else:
            is_standing = True
            
        # Create ticket
        cursor.execute('''
            INSERT INTO tickets (bus_number, source_stop, destination_stop, passenger_count, fare, ticket_date, ticket_time, assigned_seat, ticket_status, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Active', %s)
        ''', (bus_number, source_stop, destination_stop, 1, fare, ticket_date, ticket_time, assigned_seat, user_id))
        
        ticket_id = cursor.lastrowid
        
        if assigned_seat:
            cursor.execute('''
                UPDATE seat_status 
                SET status = 'Occupied', ticket_id = %s, boarding_stop = %s, destination_stop = %s
                WHERE bus_number = %s AND seat_number = %s
            ''', (ticket_id, source_stop, destination_stop, bus_number, assigned_seat))
            
        # Update Occupancy table
        new_occupancy = current_occupancy + 1
        
        cursor.execute("SELECT COUNT(*) as count FROM seat_status WHERE bus_number = %s AND status = 'Occupied'", (bus_number,))
        occupied_seats = cursor.fetchone()['count']
        
        seats_available = max(0, seat_capacity - occupied_seats)
        standing_occupancy = max(0, new_occupancy - seat_capacity)
        standing_available = max(0, standing_capacity - standing_occupancy)
        
        cursor.execute('''
            UPDATE occupancy 
            SET current_occupancy = %s, seats_available = %s, standing_available = %s 
            WHERE bus_number = %s
        ''', (new_occupancy, seats_available, standing_available, bus_number))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'is_standing': is_standing,
            'assigned_seat': assigned_seat,
            'fare': fare,
            'date': ticket_date
        })
        
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@tickets_bp.route('/api/tickets/my_trips')
def api_my_trips():
    if session.get('role') != 'passenger':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    user_id = session.get('user_id')
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tickets WHERE user_id = %s ORDER BY ticket_id DESC LIMIT 50", (user_id,))
        tickets = cursor.fetchall()
        
        # Format for JSON
        for t in tickets:
            t['ticket_date'] = t['ticket_date'].strftime('%Y-%m-%d')
            if hasattr(t['ticket_time'], 'seconds'):
                # timedelta
                hours, remainder = divmod(t['ticket_time'].seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                t['ticket_time'] = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                t['ticket_time'] = str(t['ticket_time'])
            if t['boarding_time']: t['boarding_time'] = str(t['boarding_time'])
            if t['exit_time']: t['exit_time'] = str(t['exit_time'])
            if t['created_at']: t['created_at'] = str(t['created_at'])
            t['fare'] = float(t['fare'])
            
        return jsonify({'success': True, 'tickets': tickets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
