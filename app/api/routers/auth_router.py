from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.stock_model import User, UserSettings
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await AuthService.register(
            db, user_data.username, user_data.email, user_data.password
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await AuthService.authenticate(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = AuthService.verify_refresh_token(payload.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 refresh token",
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或未激活",
        )

    access_token = AuthService.create_access_token(user.id)
    new_refresh_token = AuthService.create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return current_user


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    language: str
    theme: str
    timezone: str
    extra: dict


class UserSettingsUpdate(BaseModel):
    language: str | None = None
    theme: str | None = None
    timezone: str | None = None
    extra: dict | None = None


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(
            user_id=current_user.id,
            language="zh-CN",
            theme="dark",
            timezone="Asia/Shanghai",
            extra={},
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(UserSettings).where(UserSettings.user_id == current_user.id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    if settings_data.language is not None:
        settings.language = settings_data.language
    if settings_data.theme is not None:
        settings.theme = settings_data.theme
    if settings_data.timezone is not None:
        settings.timezone = settings_data.timezone
    if settings_data.extra is not None:
        settings.extra = settings_data.extra

    await db.commit()
    await db.refresh(settings)

    return settings
