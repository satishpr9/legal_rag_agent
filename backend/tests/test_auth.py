import pytest
from httpx import AsyncClient
from app.core import security
from app.db.models import User
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_password_hashing():
    password = "secretpassword"
    hashed = security.get_password_hash(password)
    assert security.verify_password(password, hashed)
    assert not security.verify_password("wrongpassword", hashed)

@pytest.mark.asyncio
async def test_jwt_token_creation():
    user_id = 1
    token = security.create_access_token(subject=user_id)
    assert isinstance(token, str)
    assert len(token) > 20

@pytest.mark.asyncio
async def test_db_connection(async_client: AsyncClient, db_session):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}

@pytest.mark.asyncio
async def test_list_users_access(async_client: AsyncClient, admin_token, user_token):
    # Admin should succeed
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_response = await async_client.get("/api/v1/admin/users", headers=admin_headers)
    assert admin_response.status_code == 200
    assert isinstance(admin_response.json(), list)

    # Associate should get 403 Forbidden
    user_headers = {"Authorization": f"Bearer {user_token}"}
    user_response = await async_client.get("/api/v1/admin/users", headers=user_headers)
    assert user_response.status_code == 403

