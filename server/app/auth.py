import hashlib
import hmac
import os
import time
from dataclasses import dataclass

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))
REGISTRATION_SECRET = os.getenv("REGISTRATION_SECRET", JWT_SECRET)

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class TokenUser:
    id: int
    username: str
    role: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int, username: str, role: str) -> str:
    expire = int(time.time()) + JWT_EXPIRE_MINUTES * 60
    payload = {"sub": str(user_id), "username": username, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> TokenUser:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        username = payload["username"]
        role = payload["role"]
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenUser(id=user_id, username=username, role=role)


def _code_for_minute(minute_bucket: int) -> str:
    digest = hmac.new(
        REGISTRATION_SECRET.encode(),
        str(minute_bucket).encode(),
        hashlib.sha256,
    ).digest()
    return str(int.from_bytes(digest[:4], "big") % 10_000_000).zfill(7)


def generate_registration_code() -> tuple[str, int]:
    now = int(time.time())
    minute_bucket = now // 60
    expires_in = 60 - (now % 60)
    return _code_for_minute(minute_bucket), expires_in


def verify_registration_code(code: str) -> bool:
    minute_bucket = int(time.time()) // 60
    return code == _code_for_minute(minute_bucket) or code == _code_for_minute(
        minute_bucket - 1
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TokenUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)


async def require_admin(user: TokenUser = Depends(get_current_user)) -> TokenUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
