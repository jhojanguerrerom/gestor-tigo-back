from datetime import datetime, timedelta, timezone
import logging
from fastapi import HTTPException, Request, status
from jose import jwt, JWTError
from uuid import uuid4
from typing import Tuple, Optional
from app.core.config import settings

logger = logging.getLogger("jwt_manager")

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def create_jwt_token(subject: str, token_type: str = "access", expires_minutes: Optional[int] = None) -> Tuple[str, str, int]:
    """
    Crea un JWT con:
      - sub: subject (user id)
      - jti: id único de token
      - type: "access" o "refresh"
      - exp: timestamp (segundos desde epoch)

    Retorna: (token, jti, exp_timestamp)
    """
    if token_type not in ("access", "refresh"):
        raise ValueError("token_type must be 'access' or 'refresh'")

    if expires_minutes is None:
        expires_minutes = settings.JWT_EXPIRE_MINUTES if token_type == "access" else settings.JWT_REFRESH_EXPIRE_MINUTES

    expire_dt = _now_utc() + timedelta(minutes=expires_minutes)
    exp_ts = int(expire_dt.timestamp())
    jti = str(uuid4())

    payload = {
        "sub": str(subject),
        "jti": jti,
        "type": token_type,
        "exp": exp_ts,
        "iat": int(_now_utc().timestamp())
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti, exp_ts

def verify_jwt_token(token: str, expected_type: Optional[str] = None) -> Optional[dict]:
    """
    Decodifica y verifica un token JWT.
    Si expected_type se provee, valida que payload['type'] coincida.
    Retorna el payload dict o None si inválido.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if expected_type and payload.get("type") != expected_type:
            logger.warning("Token type mismatch: expected %s got %s", expected_type, payload.get("type"))
            return None
        return payload
    except JWTError as e:
        logger.debug("verify_jwt_token error: %s", e)
        return None

def get_token_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no proporcionado")
    token = auth_header.split(" ")[1]
    return token
