from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import subprocess
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management and flash messages

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'OrangeJuice@07'
app.config['MYSQL_DB'] = 'studentdb'

mysql = MySQL(app)

def run_streamlit():
    """Run the Streamlit app."""
    subprocess.run(["streamlit", "run", "llama.py", "--server.headless", "true"])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        portal_id = request.form['portal_id']
        password = request.form['password']
        
        # Query the database to verify credentials
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT is_admin FROM users WHERE portal_id = %s AND password = %s
        """, (portal_id, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['portal_id'] = portal_id  # Store portal_id in session
            print(f"Logged in user portal_id: {session['portal_id']}")
            
            is_admin = user[0]  # Extract the is_admin value
            if is_admin == 1:  # Admin user
                flash(f"Welcome Admin, {portal_id}!", 'success')
                return redirect("http://localhost:8501")  # Redirect to Streamlit app
            
            elif is_admin == 0:  # Regular user
                flash(f"Welcome, {portal_id}!", 'success')
                return redirect(url_for('dashboard'))  # Redirect to dashboard
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    portal_id = session.get('portal_id')  # Retrieve logged-in student's portal ID from the session
    if not portal_id:
        flash("You must log in first!", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    # Fetch student data based on portal ID
    cur.execute("""
        SELECT Name, CTPS, L1, L2, L3, L4, L5, PDS, `Total score`
        FROM studentsperformance
        WHERE Portal_ID = %s
    """, (portal_id,))
    student_data = cur.fetchone()  # Fetch one row
    cur.close()

    # Check if the student exists
    if not student_data:
        flash("No data found for your account. Please contact the administrator.", "warning")
        return redirect(url_for('login'))

    # Pass the data to the HTML template
    return render_template('studentDB.html', student=student_data)

@app.route('/logout')
def logout():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
