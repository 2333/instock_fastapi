from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.stock_model import User
from app.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


class AuthService:
    @staticmethod
    async def register(db: AsyncSession, username: str, email: str, password: str) -> User:
        stmt = select(User).where((User.username == username) | (User.email == email))
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("用户名或邮箱已存在")

        user = User(
            username=username,
            email=email,
            hashed_password=pwd_context.hash(password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, username: str, password: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not pwd_context.verify(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_access_token(user_id: int) -> str:
        payload = {
            "sub": str(user_id),
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: int) -> str:
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_token(token: str, expected_type: str = "access") -> int:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != expected_type:
                raise JWTError("Token type mismatch")
            return int(payload["sub"])
        except JWTError:
            raise

    @staticmethod
    def verify_access_token(token: str) -> int:
        return AuthService.verify_token(token, "access")

    @staticmethod
    def verify_refresh_token(token: str) -> int:
        return AuthService.verify_token(token, "refresh")
