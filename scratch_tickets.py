def append_tickets():
    code = """
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
"""
    with open('backend/tickets.py', 'a') as f:
        f.write(code)

if __name__ == '__main__':
    append_tickets()
