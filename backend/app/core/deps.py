"""Dépendances FastAPI : session, utilisateur courant, contrôle des droits."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.permissions import Domaine, peut
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


def exige(domaine: Domaine, ecrire: bool = False):
    """Dépendance : l'utilisateur doit avoir le droit de lire (ou modifier) ce domaine."""

    def verifier(user: CurrentUser) -> Utilisateur:
        if not peut(user.roles, domaine, ecrire):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les droits pour cette action.",
            )
        return user

    return Depends(verifier)


def lecture(domaine: Domaine):
    return exige(domaine)


def ecriture(domaine: Domaine):
    return exige(domaine, ecrire=True)
