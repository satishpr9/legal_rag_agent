from fastapi import APIRouter
from app.api.routes import auth, admin, chat

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
