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
    """Run the Streamlit app in a separate thread."""
    subprocess.run(["streamlit", "run", "llama.py", "--server.headless", "true"])

@app.route('/redirect_to_llm')
def redirect_to_streamlit():
    """Redirect to the Streamlit app."""
    threading.Thread(target=run_streamlit, daemon=True).start()
    flash("Redirecting to the Chat with LLM interface...", "info")
    return redirect("http://localhost:8501")  # Default port where Streamlit runs

def get_scores():
    """Fetch scores from the database or return default values."""
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT CTPS, L1, L2, L3, L4, L5, PDS FROM completion_status LIMIT 1")
        result = cur.fetchone()
        cur.close()
        if result:
            return {
                'CTPS': result[0],
                'L1': result[1],
                'L2': result[2],
                'L3': result[3],
                'L4': result[4],
                'L5': result[5],
                'PDS': result[6],
            }
    except Exception as e:
        print(f"Error fetching scores: {e}")
    return {
        'CTPS': 0, 'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0, 'L5': 0, 'PDS': 0
    }
@app.route('/update_completion_status', methods=['POST'])
def update_completion_status():
    """Update the completion scores in the database."""
    try:
        # Extract scores from the form
        CTPS = request.form.get('CTPS')
        L1 = request.form.get('L1')
        L2 = request.form.get('L2')
        L3 = request.form.get('L3')
        L4 = request.form.get('L4')
        L5 = request.form.get('L5')
        PDS = request.form.get('PDS')

        # Update query
        query = """
            UPDATE completion_status
            SET CTPS = %s, L1 = %s, L2 = %s, L3 = %s, L4 = %s, L5 = %s, PDS = %s, last_edited = NOW()
            WHERE id = 1  -- Adjust the WHERE clause as per your table schema
        """
        cur = mysql.connection.cursor()
        cur.execute(query, (CTPS, L1, L2, L3, L4, L5, PDS))
        mysql.connection.commit()
        cur.close()

        # Flash success message and redirect
        flash("Completion scores updated successfully!", "success")
        return redirect(url_for('completion_status'))
    except Exception as e:
        # Handle errors
        print(f"Error updating completion scores: {e}")
        flash("Error updating completion scores. Please try again later.", "danger")
        return redirect(url_for('completion_status'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login and redirection based on role."""
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
                scores = get_scores()  # Fetch scores for admin view
                return render_template("completion_status.html", scores=scores)  # Pass scores
            
            elif is_admin == 0:  # Regular user
                flash(f"Welcome, {portal_id}!", 'success')
                return render_template('studentDB.html')  # Render the dashboard for regular users
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')

@app.route('/completion_status')
def completion_status():
    """Fetch and display the current completion scores."""
    scores = get_scores()
    return render_template('completion_status.html', scores=scores)

if __name__ == '__main__':
    app.run(debug=True)
