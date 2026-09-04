from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    generate_registration_code,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
    verify_registration_code,
    TokenUser,
)
from app.database import get_db
from app.db_models.models import User
from app.pydantic_models import auth as models

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=models.TokenResponse)
async def login(body: models.LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == body.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(user.id, user.username, user.role)
    return models.TokenResponse(
        access_token=token,
        username=user.username,
        role=user.role,
    )


@router.post("/register", response_model=models.UserResponse, status_code=201)
async def register(body: models.RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not verify_registration_code(body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration code",
        )

    stmt = select(User).where(User.username == body.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    return models.UserResponse(username=user.username, role=user.role)


@router.get("/me", response_model=models.UserResponse)
async def me(user: TokenUser = Depends(get_current_user)):
    return models.UserResponse(username=user.username, role=user.role)


@router.get("/registration-code", response_model=models.RegistrationCodeResponse)
async def registration_code(_admin: TokenUser = Depends(require_admin)):
    code, expires_in = generate_registration_code()
    return models.RegistrationCodeResponse(code=code, expires_in_seconds=expires_in)
