"""Schémas Pydantic : formes des données en entrée et en sortie de l'API."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# ---------- Authentification ----------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UtilisateurOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ecole_id: int
    nom: str
    prenom: str
    email: str
    role: str


# ---------- Élèves ----------

class EleveBase(BaseModel):
    matricule: str = Field(min_length=1, max_length=30)
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    date_naissance: date | None = None
    sexe: str | None = Field(default=None, pattern="^[MF]$")
    classe_id: int | None = None


class EleveCreate(EleveBase):
    pass


class EleveUpdate(BaseModel):
    matricule: str | None = Field(default=None, min_length=1, max_length=30)
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    prenom: str | None = Field(default=None, min_length=1, max_length=100)
    date_naissance: date | None = None
    sexe: str | None = Field(default=None, pattern="^[MF]$")
    classe_id: int | None = None
    statut: str | None = Field(default=None, pattern="^(actif|archive|redoublant)$")


class EleveOut(EleveBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ecole_id: int
    statut: str
