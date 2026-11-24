# SafeRoute

A beginner-friendly Flask + MySQL prototype for a personal travel-safety website.

## Included
- Account registration and login (passwords are hashed)
- User dashboard
- Trusted contact storage
- Journey start/completion
- SOS alert logging
- Browser geolocation capture when permission is granted
- Two-minute safety check timer and automatic alert logging

## Important safety limitation
This is an academic prototype, **not a production emergency-response service**. SOS and timeout events are stored in the database only. They do not send SMS, WhatsApp, email, or contact emergency services. Before real-world use, add a verified notification provider, consent and abuse safeguards, reliable background scheduling, HTTPS, monitoring, and security review. A browser tab being closed or a device going offline can prevent the client-side timer from running.

## Requirements
- Python 3.10+
- MySQL 5.7+ / 8+
- VS Code (recommended)

## Setup
1. Create a MySQL database:
   ```sql
   CREATE DATABASE saferoute;
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   ```
3. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and enter your MySQL password and a strong `SECRET_KEY`.
5. Start the app:
   ```bash
   python -c "from app import init_db; init_db()"
   python app.py
   ```
6. Open http://127.0.0.1:5000

## GitHub
Create a new GitHub repository named `SafeRoute`, then:
```bash
git init
git add .
git commit -m "Initial SafeRoute project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/SafeRoute.git
git push -u origin main
```

## Deployment note
GitHub Pages hosts static sites; it cannot run this Flask backend or MySQL database. Deploy the Flask app to a Python-capable host and use a managed MySQL database, then keep secrets in the host's environment-variable settings. Do not commit `.env` or database passwords.
