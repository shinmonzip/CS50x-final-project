from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from cs50 import SQL
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import logging
import re

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['DATABASE_URL'] = os.getenv(
    'DATABASE_URL', 'sqlite:///todo.db')  # Database connection URL
# Secret key for session management
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
db = SQL(app.config['DATABASE_URL'])

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function to check if the user is logged in


def is_logged_in():
    return "user_id" in session

# Decorator to ensure user is logged in


def login_required(f):
    """Decorator to ensure that the user is logged in before accessing a route."""
    def wrap(*args, **kwargs):
        if not is_logged_in():
            flash("You must be logged in to access this page.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Helper function to handle safe database queries


def safe_db_execute(query, *params):
    """Executes a database query and logs errors if any."""
    try:
        return db.execute(query, *params)
    except Exception as e:
        logging.error(f"Database error: {e}")
        flash("An error occurred while processing your request.", "danger")
        return None

# Helper function to show flash messages


def show_flash_message(message, category="info"):
    """Helper function to display flash messages."""
    flash(message, category)

# Helper function to validate user inputs


def validate_username(username):
    """Validates the username format to prevent potential security risks."""
    if not username or len(username) < 3:
        show_flash_message("Username must be at least 3 characters long.", "danger")
        return False
    return True


def validate_password(password):
    """Validates password strength."""
    if len(password) < 6:
        show_flash_message("Password must be at least 6 characters long.", "danger")
        return False
    return True

# Login page route


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not validate_username(username):
            return redirect(url_for('login'))

        user = safe_db_execute("SELECT * FROM users WHERE username = ?", username)

        if user and check_password_hash(user[0]['password'], password):
            session['user_id'] = user[0]['id']
            show_flash_message('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            show_flash_message('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

# Registration page route


@app.route("/register", methods=["GET", "POST"])
def register():
    """Handles user registration."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not validate_username(username) or not validate_password(password):
            return redirect(url_for("register"))

        if password != confirm_password:
            show_flash_message("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        user = safe_db_execute("SELECT * FROM users WHERE username = ?", username)
        if user:
            show_flash_message("Username already exists!", "danger")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        if safe_db_execute("INSERT INTO users (username, password) VALUES (?, ?)", username, password_hash):
            show_flash_message("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

# Main page (to-do list) route


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Displays the main to-do list page."""
    if request.method == "POST":
        title = request.form.get("task")
        priority = request.form.get("priority", 1)
        if title:
            safe_db_execute("INSERT INTO tasks (title, user_id, status, priority) VALUES (?, ?, 'not_done', ?)",
                            title, session["user_id"], priority)
            show_flash_message("Task added successfully!", "success")
        else:
            show_flash_message("Please enter a task title.", "danger")
        return redirect(url_for("index"))

    tasks = safe_db_execute("SELECT * FROM tasks WHERE user_id = ? AND status = 'not_done' ORDER BY priority DESC, id ASC",
                            session["user_id"])
    completed_tasks = safe_db_execute("SELECT * FROM tasks WHERE user_id = ? AND status = 'done' ORDER BY priority DESC, id ASC",
                                      session["user_id"])
    return render_template("index.html", tasks=tasks, completed_tasks=completed_tasks)

# Mark a task as done route


@app.route("/done/<int:task_id>", methods=["POST"])
@login_required
def mark_done(task_id):
    """Marks a task as done."""
    if safe_db_execute("UPDATE tasks SET status = 'done' WHERE id = ?", task_id):
        show_flash_message("Task marked as done!", "success")
    return redirect(url_for("index"))

# Delete a task route


@app.route("/delete/<int:task_id>", methods=["POST"])
@login_required
def delete(task_id):
    """Deletes a task."""
    if safe_db_execute("DELETE FROM tasks WHERE id = ?", task_id):
        show_flash_message("Task deleted successfully.", "success")
    return redirect(url_for("index"))

# Delete a completed task route


@app.route("/delete_completed/<int:task_id>", methods=["POST"])
@login_required
def delete_completed(task_id):
    """Deletes a completed task."""
    if safe_db_execute("DELETE FROM tasks WHERE id = ? AND status = 'done'", task_id):
        show_flash_message("Completed task deleted successfully.", "success")
    else:
        show_flash_message("Error deleting completed task.", "danger")
    return redirect(url_for("completed_tasks"))

# Completed tasks page route


@app.route("/completed_tasks")
@login_required
def completed_tasks():
    """Displays the completed tasks page."""
    completed_tasks = safe_db_execute("SELECT * FROM tasks WHERE user_id = ? AND status = 'done' ORDER BY priority DESC, id ASC",
                                      session["user_id"])
    return render_template("completed_tasks.html", completed_tasks=completed_tasks)

# Update task name route


@app.route("/tasks/<int:task_id>/edit", methods=["POST"])
@login_required
def edit_task(task_id):
    """Updates a task's title or priority."""
    data = request.json
    field = data.get("field")  # Could be 'title' or 'priority'
    new_value = data.get("value")

    if not new_value:
        show_flash_message(f"{field} cannot be empty.", "error")
        return jsonify({"success": False, "message": f"{field} cannot be empty."}), 400

    if field == "title":
        query = "UPDATE tasks SET title = ? WHERE id = ? AND user_id = ?"
    elif field == "priority":
        query = "UPDATE tasks SET priority = ? WHERE id = ? AND user_id = ?"
    else:
        show_flash_message("Invalid field.", "error")
        return jsonify({"success": False, "message": "Invalid field."}), 400

    if safe_db_execute(query, new_value, task_id, session["user_id"]):
        show_flash_message(f"Task {field} updated successfully.", "success")
        return jsonify({"success": True, "message": f"Task {field} updated successfully."})
    else:
        show_flash_message("Failed to update task.", "error")
        return jsonify({"success": False, "message": "Failed to update task."}), 400

# Update task priority route


@app.route("/update_priority/<int:task_id>", methods=["POST"])
@login_required
def update_priority(task_id):
    """Updates a task's priority."""
    new_priority = request.form.get("priority")
    if new_priority and safe_db_execute("UPDATE tasks SET priority = ? WHERE id = ? AND user_id = ?",
                                        new_priority, task_id, session["user_id"]):
        show_flash_message("Task priority updated.", "success")
    return redirect(url_for("index"))

# Log out route


@app.route("/logout")
def logout():
    """Logs out the user."""
    session.clear()
    show_flash_message("You have been logged out.", "info")
    return redirect(url_for("login"))

# Change user password route


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Allows the user to change their password."""
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        if new_password != confirm_new_password:
            show_flash_message("The new passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        user = safe_db_execute("SELECT * FROM users WHERE id = ?", session["user_id"])

        if user and check_password_hash(user[0]["password"], current_password):
            new_password_hash = generate_password_hash(new_password)
            if safe_db_execute("UPDATE users SET password = ? WHERE id = ?", new_password_hash, session["user_id"]):
                show_flash_message("Password changed successfully.", "success")
                return redirect(url_for("index"))
            else:
                show_flash_message("Error updating the password.", "danger")
        else:
            show_flash_message("Incorrect current password.", "danger")

    return render_template("change_password.html")


# Run the app
if __name__ == "__main__":
    app.run(debug=True)
