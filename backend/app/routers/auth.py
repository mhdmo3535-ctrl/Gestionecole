"""Authentification : connexion et profil courant."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.permissions import matrice
from app.core.security import create_access_token, verify_password
from app.models import Utilisateur
from app.schemas import Token, UtilisateurOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
):
    """Connexion par email (champ ``username``) + mot de passe."""
    user = db.scalar(select(Utilisateur).where(Utilisateur.email == form.username))
    if user is None or not verify_password(form.password, user.mot_de_passe_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé.",
        )
    token = create_access_token(subject=str(user.id), extra={"roles": user.roles, "ecole_id": user.ecole_id})
    return Token(access_token=token)


@router.get("/me", response_model=UtilisateurOut)
def read_me(user: CurrentUser):
    return user


@router.get("/droits")
def lire_droits(_: CurrentUser) -> dict[str, dict[str, list[str]]]:
    """Matrice des droits (domaine -> rôles qui lisent / modifient), pour l'interface."""
    return matrice()
