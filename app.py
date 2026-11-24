import os
from datetime import datetime, timedelta
from functools import wraps

import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-before-deployment")

def db():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "saferoute"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def init_db():
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(190) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS contacts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(100) NOT NULL,
                phone VARCHAR(30) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS journeys (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                start_place VARCHAR(255),
                destination VARCHAR(255),
                status VARCHAR(30) DEFAULT 'active',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at DATETIME NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                journey_id INT NULL,
                alert_type VARCHAR(50) NOT NULL,
                message TEXT,
                latitude DECIMAL(10,7) NULL,
                longitude DECIMAL(10,7) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (journey_id) REFERENCES journeys(id) ON DELETE SET NULL
            )""")
    finally:
        conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.")
            return redirect(url_for("register"))
        conn = db()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users(name,email,password_hash) VALUES(%s,%s,%s)",
                            (name, email, generate_password_hash(password)))
            flash("Account created. Please log in.")
            return redirect(url_for("login"))
        except pymysql.err.IntegrityError:
            flash("That email is already registered.")
        finally:
            conn.close()
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email=%s", (email,))
                user = cur.fetchone()
        finally:
            conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM contacts WHERE user_id=%s ORDER BY id DESC", (session["user_id"],))
            contacts = cur.fetchall()
            cur.execute("SELECT * FROM journeys WHERE user_id=%s ORDER BY id DESC LIMIT 5", (session["user_id"],))
            journeys = cur.fetchall()
            cur.execute("SELECT * FROM alerts WHERE user_id=%s ORDER BY id DESC LIMIT 5", (session["user_id"],))
            alerts = cur.fetchall()
    finally:
        conn.close()
    return render_template("dashboard.html", contacts=contacts, journeys=journeys, alerts=alerts)

@app.route("/contacts", methods=["POST"])
@login_required
def add_contact():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    if name and phone:
        conn = db()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO contacts(user_id,name,phone) VALUES(%s,%s,%s)",
                            (session["user_id"], name, phone))
        finally:
            conn.close()
        flash("Emergency contact saved.")
    return redirect(url_for("dashboard"))

@app.route("/journeys", methods=["POST"])
@login_required
def start_journey():
    start = request.form.get("start_place", "").strip()
    destination = request.form.get("destination", "").strip()
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO journeys(user_id,start_place,destination) VALUES(%s,%s,%s)",
                        (session["user_id"], start, destination))
    finally:
        conn.close()
    flash("Journey started. Keep this page open for safety check reminders.")
    return redirect(url_for("dashboard"))

@app.route("/journeys/<int:journey_id>/end", methods=["POST"])
@login_required
def end_journey(journey_id):
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE journeys SET status='completed', ended_at=NOW() WHERE id=%s AND user_id=%s",
                        (journey_id, session["user_id"]))
    finally:
        conn.close()
    return redirect(url_for("dashboard"))

@app.route("/api/alert", methods=["POST"])
@login_required
def create_alert():
    data = request.get_json(silent=True) or {}
    alert_type = data.get("type", "SOS")
    message = data.get("message", "User requested help.")
    lat, lng = data.get("latitude"), data.get("longitude")
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO alerts(user_id,alert_type,message,latitude,longitude)
                           VALUES(%s,%s,%s,%s,%s)""",
                        (session["user_id"], alert_type, message, lat, lng))
    finally:
        conn.close()
    # Notification delivery is intentionally not claimed here.
    # Connect an SMS/email provider (and verify contact consent) before real-world use.
    return jsonify(ok=True, message="Alert saved in SafeRoute. External notifications are not configured.")

@app.route("/api/contacts")
@login_required
def contacts_api():
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name, phone FROM contacts WHERE user_id=%s", (session["user_id"],))
            return jsonify(cur.fetchall())
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
