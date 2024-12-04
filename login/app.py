from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
import subprocess
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management and flash messages

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
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
        
        # Query the database to verify credentials and check is_admin value
        cur = mysql.connection.cursor()
        cur.execute("SELECT is_admin FROM Users WHERE portal_id = %s AND password = %s", (portal_id, password))
        user = cur.fetchone()  # Fetch only the is_admin column
        cur.close()

        if user:
            is_admin = user[0]  # Extract the is_admin value
            
            if is_admin == 1:  # Admin user
                flash(f"Welcome Admin, {portal_id}!", 'success')
                # Start Streamlit app in a separate thread
                thread = threading.Thread(target=run_streamlit, daemon=True)
                thread.start()
                return redirect("http://localhost:8501")  # Redirect to the Streamlit app
            
            elif is_admin == 0:  # Regular user
                flash(f"Welcome, {portal_id}!", 'success')
                return render_template('studentDB.html')  # Redirect to the dashboard
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return "This is the dashboard. Login successful!"

if __name__ == '__main__':
    app.run(debug=True)
