import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models import User, RoleEnum
from app.core import security
from sqlalchemy.future import select

async def main():
    async with AsyncSessionLocal() as session:
        admin_email = "admin@example.com"
        admin_password = "adminpassword123"
        
        result = await session.execute(select(User).where(User.email == admin_email))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"User {admin_email} already exists. Updating password and role to admin...")
            user.hashed_password = security.get_password_hash(admin_password)
            user.role = RoleEnum.admin
            user.is_active = True
        else:
            print(f"Creating new admin user: {admin_email}...")
            user = User(
                email=admin_email,
                hashed_password=security.get_password_hash(admin_password),
                full_name="System Administrator",
                role=RoleEnum.admin,
                is_active=True
            )
            session.add(user)
            
        await session.commit()
        print("--------------------------------------------------")
        print(f"Admin User successfully configured!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        print("--------------------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
