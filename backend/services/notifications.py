import smtplib
from email.mime.text import MIMEText
import logging
from config import settings
from twilio.rest import Client

logger = logging.getLogger(__name__)

def send_escalation_email(employee: dict, threat_data: dict, classification: dict):
    """Dispatches a strategic escalation email to the assigned employee."""
    
    subject = f"🚨 Strategic Threat Escalation: {threat_data['competitor']} - Action Required"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #ef4444; margin-top: 0;">🚨 Strategic Threat Escalation</h2>
                <p><strong>Immediate Attention Required</strong></p>
                <p>Hello {employee['name']},<br>
                This is a briefing from the Strategic Analysis Team. The AI Engine has flagged a new competitive threat and routed it to <strong>{employee['department']}</strong>.</p>
            </div>
            
            <h3>Threat Details</h3>
            <ul>
                <li><strong>Competitor:</strong> {threat_data['competitor']}</li>
                <li><strong>Issue:</strong> {threat_data['threat_title']}</li>
                <li><strong>Severity:</strong> {threat_data['severity'].upper()}</li>
                <li><strong>AI Priority:</strong> {classification.get('priority', 'HIGH').upper()}</li>
            </ul>
            
            <h3>Summary</h3>
            <p>{threat_data['threat_description']}</p>
            
            <h3>Why It Was Routed To You</h3>
            <p><em>"{classification.get('reason', 'Based on the nature of the threat.')}"</em></p>
            
            <hr style="border: none; border-top: 1px solid #eaeaea; margin: 30px 0;">
            <p style="font-size: 12px; color: #888;">StrategosAI Engine • Auto-generated Escalation • Please coordinate with your team.</p>
        </body>
    </html>
    """
    
    print("\n\033[1;31m" + "═" * 60 + "\033[0m")
    print(f"\033[1;31m🚨 DISPATCHING ESCALATION EMAIL\033[0m")
    print(f"\033[1;36mTO:\033[0m {employee['name']} ({employee['email']}) - Dept: {employee['department']}")
    print(f"\033[1;36mSUBJECT:\033[0m {subject}")
    print("\033[1;31m" + "═" * 60 + "\033[0m\n")
    
    try:
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            msg = MIMEText(html_body, 'html')
            msg['Subject'] = subject
            msg['From'] = settings.FROM_EMAIL or settings.SMTP_USERNAME
            msg['To'] = employee['email']

            # Connect to SMTP server
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Successfully sent escalation email to {employee['email']}")
            return True
        else:
            logger.warning("SMTP Config missing. Simulated email send.")
            return True
    except Exception as e:
        logger.error(f"SMTP Error: {e}")
        return False

def send_whatsapp_message(employee: dict, threat_data: dict, classification: dict):
    """Dispatches a strategic escalation via WhatsApp."""
    print(f"\n\033[1;32m💬 DISPATCHING WHATSAPP\033[0m")
    print(f"\033[1;36mTO:\033[0m {employee['name']} ({employee['phone']}) - Dept: {employee['department']}")
    
    if not employee.get('phone'):
        logger.warning(f"No phone number for {employee['name']}. Skipping WhatsApp.")
        return False
        
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio credentials missing. Simulated WhatsApp send.")
        return True
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message_body = (
            f"🚨 *Strategic Threat Escalation*\n\n"
            f"Hi {employee['name']},\n"
            f"The AI Engine has flagged a competitive threat routed to *{employee['department']}*.\n\n"
            f"*Competitor:* {threat_data.get('competitor')}\n"
            f"*Issue:* {threat_data.get('threat_title')}\n"
            f"*AI Priority:* {classification.get('priority', 'HIGH').upper()}\n\n"
            f"_{classification.get('reason', 'Review the dashboard for details.')}_"
        )
        
        target_number = employee['phone']
        if not target_number.startswith('+'):
            target_number = '+' + target_number
            
        message = client.messages.create(
            from_="whatsapp:+14155238886",
            body=message_body,
            to=f"whatsapp:{target_number}"
        )
        logger.info(f"Successfully sent WhatsApp message to {target_number} (SID: {message.sid})")
        return True
    except Exception as e:
        logger.error(f"WhatsApp Error: {e}")
        return False
