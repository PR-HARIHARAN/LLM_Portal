from flask import Flask, render_template, redirect, url_for, flash, session, request

from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_mysqldb import MySQL
import os
from langchain_community.chat_models import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# MySQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '' 
app.config['MYSQL_DB'] = 'studentdb'

mysql = MySQL(app)

# Database configuration (hardcoded)
DATABASE_CONFIG = {
    "username": "root",
    "password": "",
    "host": "localhost",
    "port": 3306,
    "database": "studentdb"
}


llm = ChatOllama(model="llama3.2")

# Database connection
db = None



def connect_database():
    """Connect to the database using the predefined configuration."""
    global db
    config = DATABASE_CONFIG
    mysql_uri = f"mysql+mysqlconnector://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    db = SQLDatabase.from_uri(mysql_uri)
    print("Database connected successfully!")


def run_query(query):
    """Run a query against the connected database."""
    return db.run(query) if db else "Database is not connected."


def get_database_schema():
    """Get the schema of the connected database."""
    return db.get_table_info() if db else "Database is not connected."


def get_query_from_llm(question):
    """Generate an SQL query using the LLM."""
    template = """below is the schema of MYSQL database, read the schema carefully about the table and column names. Also take care of table or column name case sensitivity.
    Finally answer user's question in the form of SQL query.

    {schema}

    Please only provide the SQL query and nothing else.

    Example:
    question: how many subjects do we have in the database?
    SQL query: SELECT COUNT(*) FROM completion_status

    your turn:
    question: {question}
    SQL query:"""

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm

    response = chain.invoke({
        "question": question,
        "schema": get_database_schema()
    })
    return response.content


def get_response_for_query_result(question, query, result):
    """Generate a natural language response for the query result."""
    template2 = """below is the schema of MYSQL database, read the schema carefully about the table and column names.
    Finally write a response in natural language by looking into the conversation and result.

    {schema}

    Example:
    question: how many students are in the database?
    SQL query: SELECT COUNT(*) FROM studentsperformance;
    Result : [(111,)]
    Response: There are 111 students in the database.

    your turn to write response in natural language:
    question: {question}
    SQL query: {query}
    Result: {result}
    Response:"""

    prompt2 = ChatPromptTemplate.from_template(template2)
    chain2 = prompt2 | llm

    response = chain2.invoke({
        "question": question,
        "schema": get_database_schema(),
        "query": query,
        "result": result
    })

    return response.content

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
    return {'CTPS': 0, 'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0, 'L5': 0, 'PDS': 0}

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login and redirection based on role."""
    if request.method == 'POST':
        portal_id = request.form['portal_id']
        password = request.form['password']

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT is_admin FROM users WHERE portal_id = %s AND password = %s", (portal_id, password))
            user = cur.fetchone()
            cur.close()

            if user:
                session['portal_id'] = portal_id  # Store portal_id in session
                is_admin = user[0]
                if is_admin == 1:  # Admin user
                    flash(f"Welcome Admin, {portal_id}!", 'success')
                    return redirect(url_for("completion_status"))
                elif is_admin == 0:  # Regular user
                    flash(f"Welcome, {portal_id}!", 'success')
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password!', 'danger')
        except Exception as e:
            print(f"Error during login: {e}")
            flash('An error occurred. Please try again.', 'danger')

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



@app.route('/completion_status', methods=['GET', 'POST'])
def completion_status():
    """Display and update the completion scores for admin."""
    try:
        if 'portal_id' not in session:
            flash("You need to log in first.", "warning")
            return redirect(url_for('login'))

        # Check if user is admin
        cur = mysql.connection.cursor()
        cur.execute("SELECT is_admin FROM users WHERE portal_id = %s", (session['portal_id'],))
        user = cur.fetchone()
        cur.close()

        if not user or user[0] != 1:
            flash("Unauthorized access!", "danger")
            return redirect(url_for('login'))

        if request.method == 'POST':
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
                WHERE id = 1
            """
            cur = mysql.connection.cursor()
            cur.execute(query, (CTPS, L1, L2, L3, L4, L5, PDS))
            mysql.connection.commit()
            cur.close()

            flash("Completion scores updated successfully!", "success")
            return redirect(url_for('completion_status'))

        # Fetch current scores for GET request
        scores = get_scores()
        return render_template('completion_status.html', scores=scores)
    except Exception as e:
        print(f"Error in completion_status: {e}")
        flash("An error occurred. Please try again later.", "danger")
        return redirect(url_for('login'))
"""
@app.route('/llm', methods=['GET', 'POST'])
def chat():
    global db
    if db is None:
        try:
            connect_database()
        except Exception as e:
            flash(f"Failed to connect to the database: {e}", "danger")
            return render_template('index.html')

    if request.method == 'POST':
        question = request.form['question']
        query = get_query_from_llm(question)
        result = run_query(query)
        response = get_response_for_query_result(question, query, result)
        return render_template('index.html', question=question, query=query, result=result, response=response)

    return render_template('index.html')"""




# Update the chat route with error handling and debugging
@app.route('/llm', methods=['GET', 'POST'])
def chat():
    global db
    if db is None:
        try:
            connect_database()
        except Exception as e:
            print(f"Database connection error: {e}")  # Added debugging
            flash(f"Failed to connect to the database: {e}", "danger")
            return render_template('index.html')

    if request.method == 'POST':
        try:
            question = request.form['question']
            query = get_query_from_llm(question)
            print(f"Generated query: {query}")  # Added debugging
            
            result = run_query(query)
            print(f"Query result: {result}")  # Added debugging
            
            response = get_response_for_query_result(question, query, result)
            print(f"LLM response: {response}")  # Added debugging
            
            return render_template('index.html', 
                                 question=question, 
                                 query=query, 
                                 result=result, 
                                 response=response)
        except Exception as e:
            print(f"Error in chat route: {e}")  # Added debugging
            flash(f"An error occurred: {e}", "danger")
            return render_template('index.html')

    return render_template('index.html')


@app.route('/logout')
def logout():
    """Log out the current user."""
    session.pop('portal_id', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
