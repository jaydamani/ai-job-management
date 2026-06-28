import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.recruiter import Recruiter
from app.models.refresh_token import RefreshToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(recruiter_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": recruiter_id, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _create_refresh_jwt(recruiter_id: str, token_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": recruiter_id, "jti": token_id, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def _store_refresh_token(
    db: AsyncSession,
    recruiter_id: uuid.UUID,
    token_id: str,
    raw_token: str,
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    row = RefreshToken(
        id=uuid.UUID(token_id),
        recruiter_id=recruiter_id,
        token_hash=pwd_context.hash(raw_token),
        expires_at=expires_at,
    )
    db.add(row)


async def register(db: AsyncSession, email: str, password: str, name: str | None = None) -> Recruiter:
    result = await db.execute(select(Recruiter).where(Recruiter.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    recruiter = Recruiter(email=email, password_hash=hash_password(password), name=name or "")
    db.add(recruiter)
    await db.commit()
    await db.refresh(recruiter)
    return recruiter


async def issue_tokens(db: AsyncSession, recruiter: Recruiter) -> tuple[str, str]:
    """Create and store a fresh access+refresh token pair for an existing recruiter."""
    access_token = create_access_token(str(recruiter.id))
    token_id = str(uuid.uuid4())
    raw_refresh = _create_refresh_jwt(str(recruiter.id), token_id)
    await _store_refresh_token(db, recruiter.id, token_id, raw_refresh)
    await db.commit()
    return access_token, raw_refresh


async def login(db: AsyncSession, email: str, password: str) -> tuple[Recruiter, str, str]:
    result = await db.execute(select(Recruiter).where(Recruiter.email == email))
    recruiter = result.scalar_one_or_none()
    if not recruiter or not verify_password(password, recruiter.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token, raw_refresh = await issue_tokens(db, recruiter)
    return recruiter, access_token, raw_refresh


async def refresh_tokens(db: AsyncSession, raw_refresh: str) -> tuple[Recruiter, str, str]:
    try:
        payload = jwt.decode(raw_refresh, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    token_id = payload.get("jti")
    recruiter_id = payload.get("sub")
    if not token_id or not recruiter_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(RefreshToken).where(RefreshToken.id == uuid.UUID(token_id)))
    row = result.scalar_one_or_none()

    if not row or row.revoked or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    if not pwd_context.verify(raw_refresh, row.token_hash):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    recruiter_result = await db.execute(select(Recruiter).where(Recruiter.id == row.recruiter_id))
    recruiter = recruiter_result.scalar_one_or_none()
    if not recruiter:
        raise HTTPException(status_code=401, detail="Recruiter not found")

    row.revoked = True

    new_access = create_access_token(recruiter_id)
    new_token_id = str(uuid.uuid4())
    new_raw = _create_refresh_jwt(recruiter_id, new_token_id)
    await _store_refresh_token(db, row.recruiter_id, new_token_id, new_raw)
    await db.commit()
    return recruiter, new_access, new_raw


async def logout(db: AsyncSession, raw_refresh: str) -> None:
    try:
        payload = jwt.decode(raw_refresh, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return

    token_id = payload.get("jti")
    if not token_id:
        return

    result = await db.execute(select(RefreshToken).where(RefreshToken.id == uuid.UUID(token_id)))
    row = result.scalar_one_or_none()
    if row:
        row.revoked = True
        await db.commit()
