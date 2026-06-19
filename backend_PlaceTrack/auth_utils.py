import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import database
from models.user import User

# ── Config ──────────────────────────────────────────────────────────────────
SECRET_KEY = "CHANGE_THIS_TO_A_STRONG_RANDOM_SECRET"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

# Use argon2 instead of bcrypt for better Python 3.13 compatibility
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


# ── Password helpers ─────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Current-user dependency ───────────────────────────────────────────────────
def get_current_user(
    request: Request,
    db: Session = Depends(database.get_db),
) -> Optional[User]:
    """
    Reads JWT from cookie (web UI) or Authorization header (API).
    Returns None if unauthenticated (routes handle the redirect themselves).
    """
    token = request.cookies.get("access_token")
    if not token:
        # Try Bearer header for API clients
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    user_id: int = payload.get("sub")
    if user_id is None:
        return None

    return db.query(User).filter(User.id == int(user_id)).first()


def require_login(
    request: Request,
    db: Session = Depends(database.get_db),
) -> User:
    """Use as a dependency on routes that require authentication."""
    user = get_current_user(request, db)
    if not user:
        # Raise HTTPException which FastAPI will handle
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated. Please log in.",
        )
    return user


def require_role(*roles: str):
    """Factory: dependency that enforces one of the given roles."""
    def _checker(current_user: User = Depends(require_login)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}",
            )
        return current_user
    return _checker
