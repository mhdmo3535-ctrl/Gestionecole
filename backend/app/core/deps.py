"""Dépendances FastAPI : session, utilisateur courant, contrôle de rôle."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import Utilisateur

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> Utilisateur:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Jeton invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", ""))
    except (jwt.PyJWTError, ValueError):
        raise credentials_error

    user = db.get(Utilisateur, user_id)
    if user is None or not user.actif:
        raise credentials_error
    return user


CurrentUser = Annotated[Utilisateur, Depends(get_current_user)]


def require_roles(*roles: str):
    """Renvoie une dépendance qui n'autorise que les rôles donnés."""

    def checker(user: CurrentUser) -> Utilisateur:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les droits pour cette action.",
            )
        return user

    return checker
