from fastapi import FastAPI, HTTPException, Body, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime
import sqlite3
import os
import smtplib
import uvicorn
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load configuration
load_dotenv()

app = FastAPI(title="Crown Ridge Land Holdings, LLC API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths for static files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Database Setup
DB_PATH = "submissions.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seller_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            location TEXT,
            acreage REAL,
            apn TEXT,
            reason TEXT,
            submitted_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investor_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institution TEXT,
            email TEXT,
            capacity TEXT,
            regions TEXT,
            submitted_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Models
class SellerLead(BaseModel):
    name: str
    phone: str
    email: str
    location: str
    acreage: float
    apn: str = ""
    reason: str

class InvestorApp(BaseModel):
    institution: str
    email: str
    capacity: str
    regions: str

def send_email(to_email: str, subject: str, body: str):
    """Sends a professional email using the stored credentials with robust connection handling."""
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    server_addr = os.getenv("EMAIL_SMTP_SERVER")
    port_str = os.getenv("EMAIL_SMTP_PORT", "465")
    port = int(port_str)

    if not all([user, password, server_addr]):
        print("Email configuration missing. Skipping email.")
        return

    msg = MIMEMultipart()
    msg['From'] = f"Crown Ridge Land Holdings <{user}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        import ssl
        context = ssl.create_default_context()
        
        if port == 465:
            # Traditional SSL
            with smtplib.SMTP_SSL(server_addr, port, context=context) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            # STARTTLS (usually port 587)
            with smtplib.SMTP(server_addr, port) as server:
                server.starttls(context=context)
                server.login(user, password)
                server.send_message(msg)
                
        print(f"SUCCESS: Email sent to {to_email}")
    except Exception as e:
        print(f"CRITICAL EMAIL FAILURE to {to_email}: {e}")

@app.post("/api/seller")
async def handle_seller_lead(background_tasks: BackgroundTasks, lead: SellerLead):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO seller_leads (name, phone, email, location, acreage, apn, reason, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (lead.name, lead.phone, lead.email, lead.location, lead.acreage, lead.apn, lead.reason, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        # Send Background Notification
        email_body = f"""
NEW SELLER LEAD RECEIVED
------------------------
Name: {lead.name}
Phone: {lead.phone}
Email: {lead.email}
Location: {lead.location}
Acreage: {lead.acreage}
APN: {lead.apn}
Reason: {lead.reason}
Submitted At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        background_tasks.add_task(send_email, os.getenv("NOTIFICATION_RECEIVER"), f"URGENT: New Seller Lead - {lead.name}", email_body)

        # Send Client Confirmation
        client_body = f"""
Dear {lead.name},

Thank you for contacting Crown Ridge Land Holdings, LLC regarding your property in {lead.location}.

We have received your request for a cash offer and our acquisitions team is currently performing a preliminary valuation of your parcel. You can expect to hear from one of our representatives within the next 48 hours.

Best regards,

The Crown Ridge Team
216-532-5358
info@crownridgeland.com
        """
        background_tasks.add_task(send_email, lead.email, "We've Received Your Property Inquiry - Crown Ridge Land Holdings", client_body)

        return {"status": "success", "message": "Lead captured"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/investor")
async def handle_investor_app(background_tasks: BackgroundTasks, app_data: InvestorApp):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO investor_applications (institution, email, capacity, regions, submitted_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (app_data.institution, app_data.email, app_data.capacity, app_data.regions, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        # Send Background Notification
        email_body = f"""
NEW INVESTOR APPLICATION
--------------------------
Institution/Name: {app_data.institution}
Email: {app_data.email}
Capacity: {app_data.capacity}
Regions: {app_data.regions}
Submitted At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        background_tasks.add_task(send_email, os.getenv("NOTIFICATION_RECEIVER"), f"Network Update: New Investor - {app_data.institution}", email_body)

        # Send Client Confirmation
        client_body = f"""
Hello,

Thank you for your application to join the Crown Ridge Land Holdings Investor Network.

Your credentials and capital capacity are currently being vetted by our institutional relations team. Once approved, you will receive a follow-up email with instructions on how to access our exclusive off-market inventory portal.

Best regards,

Investor Relations
Crown Ridge Land Holdings, LLC
        """
        background_tasks.add_task(send_email, app_data.email, "Investor Network Application Received - Crown Ridge", client_body)

        return {"status": "success", "message": "Application received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Static File Serving ---
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(BASE_DIR, "style.css"))

@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(BASE_DIR, "app.js"))

@app.get("/legal")
async def serve_legal():
    return FileResponse(os.path.join(BASE_DIR, "legal.html"))

# Mount assets directory
app.mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets")), name="assets")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
