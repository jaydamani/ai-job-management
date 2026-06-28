from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    RecruiterResponse,
    RegisterRequest,
)
from app.services import auth_service

router = APIRouter()

_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=False)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(key="access_token", value=access_token, max_age=900, **_COOKIE_OPTS)
    response.set_cookie(key="refresh_token", value=refresh_token, max_age=2592000, **_COOKIE_OPTS)


def _clear_auth_cookies(response: Response) -> None:
    response.set_cookie(key="access_token", value="", max_age=0, **_COOKIE_OPTS)
    response.set_cookie(key="refresh_token", value="", max_age=0, **_COOKIE_OPTS)


@router.post("/register", response_model=RecruiterResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    recruiter = await auth_service.register(db, data.email, data.password, data.name)
    access_token, refresh_token = await auth_service.issue_tokens(db, recruiter)
    _set_auth_cookies(response, access_token, refresh_token)
    return recruiter


@router.post("/login", response_model=RecruiterResponse)
async def login(data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    recruiter, access_token, refresh_token = await auth_service.login(db, data.email, data.password)
    _set_auth_cookies(response, access_token, refresh_token)
    return recruiter


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    new_access, new_refresh = await auth_service.refresh_tokens(db, refresh_token)
    _set_auth_cookies(response, new_access, new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        await auth_service.logout(db, refresh_token)
    _clear_auth_cookies(response)
