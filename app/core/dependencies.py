from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.stock_model import User
from app.services.auth_service import AuthService
from core.providers.market_data_provider import MarketDataProvider
from core.providers.postgres_provider import PostgreSQLProvider

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def get_provider(db: AsyncSession = Depends(get_db)) -> MarketDataProvider:
    """获取市场数据提供者（默认 PostgreSQL）"""
    return PostgreSQLProvider(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        user_id = AuthService.verify_access_token(token)
    except JWTError:
        raise credentials_exception

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """可选认证：未登录返回 None，不抛异常"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        user_id = AuthService.verify_access_token(token)
    except JWTError:
        return None
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
