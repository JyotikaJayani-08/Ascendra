import asyncio
import sys

# Ensure backend directory is in the path for app imports
import os
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load the root .env file explicitly
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from sqlalchemy import select
from app.database import async_session_factory
from app.auth.models import User

async def main():
    email_to_delete = "unknownhai517@gmail.com"
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email_to_delete))
        user = result.scalar_one_or_none()
        if user:
            await session.delete(user)
            await session.commit()
            print(f"User with email '{email_to_delete}' deleted successfully.")
        else:
            print(f"User with email '{email_to_delete}' not found.")

if __name__ == "__main__":
    asyncio.run(main())
