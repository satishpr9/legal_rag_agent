import pytest
import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.environ["GEMINI_API_KEY"] = "mock-key-for-testing"

from httpx import AsyncClient, ASGITransport
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

from app.main import app
from app.db.session import Base, get_db
from app.db.models import User, RoleEnum
from app.core import security
from app.core.config import settings

TEST_DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/legal_rag_db"

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-wide event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_engine():
    """Session-scoped database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=pool.NullPool)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="session", autouse=True)
async def setup_db(db_engine):
    """Initialize test database schema once per session."""
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.fixture(scope="session")
def testing_session_maker(db_engine):
    """Fixture yielding the session maker."""
    return async_sessionmaker(db_engine, expire_on_commit=False)

@pytest.fixture
async def db_session(testing_session_maker):
    """Yield a fresh database session for the test case itself."""
    async with testing_session_maker() as session:
        yield session

@pytest.fixture(autouse=True)
async def override_db(testing_session_maker):
    """Override get_db with a fresh session per API request to avoid loop mismatches."""
    async def _get_db():
        async with testing_session_maker() as session:
            yield session
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest.fixture
async def async_client():
    """Create an async HTTP client for the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# Global reusable fixtures for tests
@pytest.fixture
async def admin_user(db_session):
    """Create or retrieve a superuser for admin actions using the test database session."""
    result = await db_session.execute(select(User).where(User.email == "admin@test.com"))
    admin = result.scalar_one_or_none()
    
    if not admin:
        admin = User(
            email="admin@test.com",
            hashed_password=security.get_password_hash("adminpassword"),
            full_name="Admin User",
            role=RoleEnum.admin,
            is_active=True
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(admin)
    else:
        await db_session.commit()
        
    return admin

@pytest.fixture
def admin_token(admin_user):
    return security.create_access_token(subject=admin_user.id)

@pytest.fixture
async def regular_user(db_session):
    """Create a regular associate user for chat testing using the test database session."""
    result = await db_session.execute(select(User).where(User.email == "associate@test.com"))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            email="associate@test.com",
            hashed_password=security.get_password_hash("password"),
            full_name="Associate Lawyer",
            role=RoleEnum.associate,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
    else:
        await db_session.commit()
        
    return user

@pytest.fixture
def user_token(regular_user):
    return security.create_access_token(subject=regular_user.id)
