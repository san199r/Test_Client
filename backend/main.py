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

def send_email(to_email: str, subject: str, plain_body: str, html_body: str = None):
    """Sends a professional email with support for HTML and Plain Text."""
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    server_addr = os.getenv("EMAIL_SMTP_SERVER")
    port_str = os.getenv("EMAIL_SMTP_PORT", "465")
    port = int(port_str)

    if not all([user, password, server_addr]):
        print("Email configuration missing. Skipping email.")
        return

    # Create root message
    msg = MIMEMultipart("alternative")
    msg['From'] = f"Crown Ridge Land Holdings <{user}>"
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach both parts (text first, then HTML as preferred)
    msg.attach(MIMEText(plain_body, 'plain'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html'))

    try:
        import ssl
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(server_addr, port, context=context) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(server_addr, port) as server:
                server.starttls(context=context)
                server.login(user, password)
                server.send_message(msg)
        print(f"SUCCESS: Professional email sent to {to_email}")
    except Exception as e:
        print(f"CRITICAL EMAIL FAILURE to {to_email}: {e}")

def get_html_template(title: str, content: str):
    """Generates a professional HTML email wrapper."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .email-container {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; }}
            .header {{ background-color: #0d1b2a; padding: 30px; text-align: center; color: white; }}
            .logo {{ max-width: 150px; margin-bottom: 20px; }}
            .body {{ padding: 40px; color: #333; line-height: 1.6; background-color: #ffffff; }}
            .footer {{ background-color: #f4f4f4; padding: 20px; text-align: center; color: #777; font-size: 12px; }}
            .btn {{ display: inline-block; padding: 12px 25px; background-color: #a37c40; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px; }}
            h1 {{ color: #0d1b2a; margin-top: 0; font-family: 'Georgia', serif; }}
        </style>
    </head>
    <body style="margin:0; padding:20px; background-color: #f9f9f9;">
        <div class="email-container">
            <div class="header">
                <img src="https://crown-ridge-holdings.onrender.com/assets/logo.jpg" alt="Crown Ridge Logo" class="logo">
                <div style="font-size: 14px; letter-spacing: 2px; text-transform: uppercase; color: #a37c40;">Crown Ridge Land Holdings, LLC</div>
            </div>
            <div class="body">
                <h1>{title}</h1>
                {content}
                <p>Best regards,<br><strong>The Crown Ridge Team</strong></p>
                <a href="https://crown-ridge-holdings.onrender.com" class="btn">View Our Portal</a>
            </div>
            <div class="footer">
                &copy; {{datetime.now().year}} Crown Ridge Land Holdings, LLC. All rights reserved.<br>
                216-532-5358 | info@crownridgeland.com
            </div>
        </div>
    </body>
    </html>
    """

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
        admin_body = f"NEW SELLER LEAD: {lead.name} ({lead.location})\nPhone: {lead.phone}\nEmail: {lead.email}\nAPN: {lead.apn}\nReason: {lead.reason}"
        background_tasks.add_task(send_email, os.getenv("NOTIFICATION_RECEIVER"), f"URGENT: New Seller Lead - {lead.name}", admin_body)

        # Send Client Confirmation (Professional HTML)
        html_content = f"""
        <p>Dear {lead.name},</p>
        <p>Thank you for contacting <strong>Crown Ridge Land Holdings, LLC</strong> regarding your property in <strong>{lead.location}</strong>.</p>
        <p>We have received your inquiry and our acquisitions team is currently performing a preliminary valuation of your parcel (APN: {lead.apn}). We pride ourselves on fair, cash offers and quick closings.</p>
        <p><strong>What happens next?</strong></p>
        <ul>
            <li>Our team will review the property data and market comps.</li>
            <li>You can expect a phone call or email from one of our representatives within the next 48 hours.</li>
            <li>If the property meets our criteria, we will present you with a firm cash offer.</li>
        </ul>
        """
        plain_content = f"Dear {lead.name}, Thank you for your inquiry regarding your property in {lead.location}. Our team will review the data and contact you within 48 hours."
        
        email_html = get_html_template("Property Inquiry Received", html_content)
        background_tasks.add_task(send_email, lead.email, "We've Received Your Property Inquiry - Crown Ridge Land Holdings", plain_content, email_html)

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
        admin_body = f"NEW INVESTOR APPLICATION: {app_data.institution}\nEmail: {app_data.email}\nCapacity: {app_data.capacity}\nRegions: {app_data.regions}"
        background_tasks.add_task(send_email, os.getenv("NOTIFICATION_RECEIVER"), f"Network Update: New Investor - {app_data.institution}", admin_body)

        # Send Client Confirmation (Professional HTML)
        html_content = f"""
        <p>Hello,</p>
        <p>Thank you for your application to join the <strong>Crown Ridge Land Holdings Investor Network</strong>.</p>
        <p>Your credentials and capital capacity (Region: {app_data.regions}) are currently being vetted by our institutional relations team. We maintain a selective network to ensure the highest quality off-market inventory for our partners.</p>
        <p>Once your application is approved, you will receive a follow-up email with instructions on how to access our exclusive inventory portal and secure deal flow.</p>
        <p>We look forward to potentially working with <strong>{app_data.institution}</strong>.</p>
        """
        plain_content = f"Hello, thank you for your application to the Crown Ridge Investor Network. Our team is currently vetting your application and will contact you shortly."
        
        email_html = get_html_template("Investor Network Application", html_content)
        background_tasks.add_task(send_email, app_data.email, "Investor Network Application Received - Crown Ridge", plain_content, email_html)

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
