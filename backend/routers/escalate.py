from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Employee, Escalation
from agents.escalation import classify_threat_for_escalation
from services.notifications import send_escalation_email

router = APIRouter(prefix="/api/escalate", tags=["escalate"])

class EscalateRequest(BaseModel):
    threat_title: str
    threat_description: str
    severity: str
    competitor: str

def fire_and_forget_escalation(request: EscalateRequest, employee_dict: dict, classification: dict):
    # Sends both email and WhatsApp messages concurrently via background workers
    from services.notifications import send_escalation_email, send_whatsapp_message
    send_escalation_email(employee=employee_dict, threat_data=request.model_dump(), classification=classification)
    send_whatsapp_message(employee=employee_dict, threat_data=request.model_dump(), classification=classification)

@router.post("")
async def escalate_threat(request: EscalateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Receives a threat, classifies it via Gemini, finds the right employee, and alerts them."""
    
    # 1. Classify the threat via Gemini AI to determine Department
    classification = await classify_threat_for_escalation(request.threat_description)
    target_depts = classification.get("departments", ["Leadership"])
    
    # 2. Query the database for employees in that department
    result = await db.execute(select(Employee).where(Employee.department.in_(target_depts)))
    employees = result.scalars().all()
    
    # Fallback if no matching department
    if not employees:
        print(f"No employees found in {target_depts}. Falling back to default (Engineering).")
        result = await db.execute(select(Employee).where(Employee.department == "Engineering"))
        employees = result.scalars().all()
    
    if not employees:
        raise HTTPException(status_code=500, detail="No employees found in the database to escalate to.")
    
    # Snapshot employee data BEFORE any commits (avoids SQLAlchemy session expiry)
    recipients = []
    for emp in employees:
        recipients.append({
            "name": emp.name, 
            "email": emp.email, 
            "department": emp.department, 
            "phone": emp.phone or ""
        })
    
    # 3. Create Escalation record in DB
    new_escalation = Escalation(
        threat_title=request.threat_title,
        threat_description=request.threat_description,
        severity=request.severity,
        department_assigned=", ".join(target_depts),
        status="pending"
    )
    db.add(new_escalation)
    await db.commit()
    await db.refresh(new_escalation)
    
    notified_emails = [r["email"] for r in recipients]
    notified_phones = [r["phone"] for r in recipients if r["phone"]]
    
    for r in recipients:
        background_tasks.add_task(fire_and_forget_escalation, request, r, classification)
        
    # Update DB record with emails and mark sent
    new_escalation.notified_emails = ", ".join(notified_emails)
    new_escalation.status = "sent"
    await db.commit()
    
    print(f"\n\033[1;35m📋 ESCALATION RESPONSE: {len(recipients)} recipients dispatched\033[0m")
    
    return {
        "status": "success", 
        "departments": target_depts, 
        "notified": len(notified_emails),
        "notified_phones": len(notified_phones),
        "channels": ["email", "whatsapp"] if notified_phones else ["email"],
        "reason": classification.get("reason", ""),
        "priority": classification.get("priority", "high"),
        "recipients": recipients,
    }
