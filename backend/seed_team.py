import os
import sys
import asyncio

# Add backend directory to sys.path to allow imports if run directly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from database import async_session, init_db
from models import Employee
from sqlalchemy import select

TEAM_DATA = [
    {
        "name": "Aravind",
        "role": "Head of Engineering",
        "department": "Engineering",
        "email": "aravind54006@gmail.com",
        "phone": "+917539962693"
    },
    {
        "name": "Dheeran",
        "role": "Head of Product",
        "department": "Product",
        "email": "dheeran2012@gmail.com",
        "phone": "+916383766338"
    },
    {
        "name": "Tejas MD",
        "role": "Head of Sales",
        "department": "Sales",
        "email": "mdtejas.connectnow@gmail.com",
        "phone": "+917395920744"
    },
    {
        "name": "Uvan",
        "role": "Head of Marketing",
        "department": "Marketing",
        "email": "uvanadhithya@gmail.com",
        "phone": "+918754544409"
    }
]

async def seed_team():
    await init_db()
    
    async with async_session() as db:
        try:
            # Check if already seeded
            result = await db.execute(select(Employee))
            existing_count = len(result.scalars().all())
            
            if existing_count > 0:
                print(f"Team already seeded ({existing_count} employees found). Skipping.")
                return

            print("Seeding Strategic Escalation Team...")
            for member_data in TEAM_DATA:
                emp = Employee(**member_data)
                db.add(emp)
            
            await db.commit()
            print(f"Successfully seeded {len(TEAM_DATA)} team members.")
        
        except Exception as e:
            print(f"Error seeding team: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(seed_team())
