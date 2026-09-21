def append_auth():
    code = """
@auth_bp.route('/passenger/login', methods=['GET', 'POST'])
def passenger_login():
    if 'user_id' in session:
        if session.get('role') == 'passenger':
            return redirect(url_for('passenger_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Email and password are required.", "warning")
            return render_template('passenger_login.html')

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM users WHERE email = %s AND role = 'passenger'", (email,))
            user = cursor.fetchone()

            if not user or not check_password_hash(user['password'], password):
                flash("Invalid email or password.", "danger")
                return render_template('passenger_login.html')

            session.clear()
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['role'] = 'passenger'

            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for('passenger_dashboard'))

        except Exception as err:
            flash(f"Database error occurred: {err}", "danger")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    return render_template('passenger_login.html')

@auth_bp.route('/passenger/register', methods=['GET', 'POST'])
def passenger_register():
    if 'user_id' in session:
        if session.get('role') == 'passenger':
            return redirect(url_for('passenger_dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not full_name or not email or not password or not confirm_password:
            flash("All required fields must be filled.", "warning")
            return render_template('passenger_register.html')

        if password != confirm_password:
            flash("Passwords do not match.", "warning")
            return render_template('passenger_register.html')

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered.", "danger")
                return render_template('passenger_register.html')
                
            hashed_pw = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (full_name, email, phone_number, password, role)
                VALUES (%s, %s, %s, %s, 'passenger')
            ''', (full_name, email, phone_number, hashed_pw))
            conn.commit()
            
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('auth.passenger_login'))

        except Exception as err:
            flash(f"Database error: {err}", "danger")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    return render_template('passenger_register.html')
"""
    with open('backend/auth.py', 'a') as f:
        f.write(code)

if __name__ == '__main__':
    append_auth()
