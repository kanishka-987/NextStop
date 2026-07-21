# backend/tickets.py
# NextStop Project - Ticket Management Blueprint
# Handles ticket generation, MySQL storage, occupancy calculations, and bus capacity verification.

import os
from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from backend.db_connection import get_db_connection
from backend.auth import login_required
import mysql.connector
from datetime import datetime

# Create the Ticket Blueprint
tickets_bp = Blueprint('tickets', __name__)

@tickets_bp.route('/conductor/tickets/generate', methods=['GET', 'POST'])
@login_required(role='conductor')
def generate_ticket():
    """
    Renders the ticket generation form for conductors.
    Validates bus capacity and records tickets in MySQL.
    """
    conn = None
    cursor = None
    
    # Fetch list of active buses for dropdown selection
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT bus_number, seat_capacity, standing_capacity, current_occupancy FROM occupancy")
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
        if not (bus_number and source_stop and destination_stop and passenger_count_str and fare_str and ticket_date and ticket_time):
            flash("All fields are required. Please fill in the ticket form completely.", "warning")
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

        try:
            fare = float(fare_str)
            if fare < 0:
                raise ValueError("Fare cannot be negative.")
        except ValueError:
            flash("Invalid fare amount. Must be a non-negative number.", "warning")
            return render_template('generate_ticket.html', buses=buses, bus_number=bus_number, 
                                   source_stop=source_stop, destination_stop=destination_stop, 
                                   passenger_count=passenger_count_str, fare=fare_str, 
                                   ticket_date=ticket_date, ticket_time=ticket_time)

        # 3. Capacity verification and database transaction
        try:
            conn = get_db_connection()
            # Turn off autocommit to handle transaction safely
            conn.autocommit = False
            cursor = conn.cursor(dictionary=True)
            
            # Fetch current occupancy records for target bus using lock (SELECT ... FOR UPDATE)
            cursor.execute("SELECT * FROM occupancy WHERE bus_number = %s FOR UPDATE", (bus_number,))
            bus_record = cursor.fetchone()
            
            if not bus_record:
                conn.rollback()
                flash(f"Error: Selected bus '{bus_number}' does not exist in occupancy registries.", "danger")
                return render_template('generate_ticket.html', buses=buses)
            
            seat_capacity = bus_record['seat_capacity']
            standing_capacity = bus_record['standing_capacity']
            current_occupancy = bus_record['current_occupancy']
            total_capacity = seat_capacity + standing_capacity
            
            # Check capacity limits
            if current_occupancy + passenger_count > total_capacity:
                conn.rollback()
                # Exact requested text to display: "Bus Full - Ticket Cannot Be Generated"
                flash("Bus Full - Ticket Cannot Be Generated", "danger")
                return render_template('generate_ticket.html', buses=buses, bus_number=bus_number, 
                                       source_stop=source_stop, destination_stop=destination_stop, 
                                       passenger_count=passenger_count_str, fare=fare_str, 
                                       ticket_date=ticket_date, ticket_time=ticket_time)

            # Insert Ticket record
            insert_ticket_query = """
            INSERT INTO tickets (bus_number, source_stop, destination_stop, passenger_count, fare, ticket_date, ticket_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_ticket_query, (
                bus_number, source_stop, destination_stop, passenger_count, fare, ticket_date, ticket_time
            ))
            ticket_id = cursor.lastrowid
            
            # Recalculate Occupancies:
            # Current Occupancy = Current Occupancy + Passenger Count
            new_occupancy = current_occupancy + passenger_count
            
            # Seats Available = Seat Capacity - Current Occupancy (seated portion)
            # Standing Occupancy = Current Occupancy - Seat Capacity (standing portion)
            # Standing Available = Standing Capacity - Standing Occupancy
            seats_available = max(0, seat_capacity - new_occupancy)
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
            
            # Commit transaction
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
                           selected_bus_number=bus_number,
                           tickets=recent_tickets)

