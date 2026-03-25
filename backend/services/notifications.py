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
    """Dispatches a strategic escalation via WhatsApp using Twilio Sandbox."""
    
    if not employee.get('phone'):
        print(f"\033[1;33m⚠️  WHATSAPP SKIPPED — No phone for {employee['name']}\033[0m")
        logger.warning(f"No phone number for {employee['name']}. Skipping WhatsApp.")
        return False
        
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        print(f"\033[1;33m⚠️  WHATSAPP SIMULATED — Twilio credentials not set\033[0m")
        logger.warning("Twilio credentials missing. Simulated WhatsApp send.")
        return True
    
    target_number = employee['phone'].strip()
    if not target_number.startswith('+'):
        target_number = '+' + target_number

    # Use the Twilio WhatsApp Sandbox number (default) or a configured WhatsApp-enabled number
    from_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', '') or 'whatsapp:+14155238886'
    if not from_number.startswith('whatsapp:'):
        from_number = f"whatsapp:{from_number}"

    print(f"\n\033[1;32m{'═' * 60}\033[0m")
    print(f"\033[1;32m💬 DISPATCHING WHATSAPP ESCALATION\033[0m")
    print(f"\033[1;36mFROM:\033[0m {from_number}")
    print(f"\033[1;36mTO:\033[0m {employee['name']} (whatsapp:{target_number}) — {employee['department']}")
    print(f"\033[1;32m{'═' * 60}\033[0m")
        
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message_body = (
            f"🚨 *Strategic Threat Escalation*\n\n"
            f"Hi {employee['name']},\n"
            f"The AI Engine has flagged a competitive threat routed to *{employee['department']}*.\n\n"
            f"*Competitor:* {threat_data.get('competitor')}\n"
            f"*Issue:* {threat_data.get('threat_title')}\n"
            f"*Severity:* {threat_data.get('severity', 'N/A').upper()}\n"
            f"*AI Priority:* {classification.get('priority', 'HIGH').upper()}\n\n"
            f"_{classification.get('reason', 'Review the dashboard for details.')}_\n\n"
            f"— StrategosAI Engine"
        )
            
        message = client.messages.create(
            from_=from_number,
            body=message_body,
            to=f"whatsapp:{target_number}"
        )
        print(f"\033[1;32m✅ WhatsApp SENT → SID: {message.sid}\033[0m\n")
        logger.info(f"Successfully sent WhatsApp to {target_number} (SID: {message.sid})")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"\033[1;31m❌ WhatsApp FAILED → {error_msg}\033[0m")
        if "not a valid WhatsApp" in error_msg or "sandbox" in error_msg.lower():
            print(f"\033[1;33m💡 TIP: Recipient must first send 'join <keyword>' to +14155238886 on WhatsApp to opt into the Twilio Sandbox.\033[0m\n")
        logger.error(f"WhatsApp Error for {target_number}: {e}")
        return False
