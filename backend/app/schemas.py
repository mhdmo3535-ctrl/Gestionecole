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


# ---------- Référentiel ----------

class NiveauOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    cycle: str


class SerieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str


class AnneeScolaireCreate(BaseModel):
    libelle: str = Field(min_length=1, max_length=20)
    date_debut: date
    date_fin: date
    active: bool = True


class AnneeScolaireUpdate(BaseModel):
    libelle: str | None = Field(default=None, min_length=1, max_length=20)
    date_debut: date | None = None
    date_fin: date | None = None
    active: bool | None = None


class AnneeScolaireOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ecole_id: int
    libelle: str
    date_debut: date
    date_fin: date
    active: bool


# ---------- Classes ----------

class ClasseCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=50)
    niveau_id: int
    serie_id: int | None = None
    annee_scolaire_id: int | None = None   # défaut : année scolaire active


class ClasseUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=50)
    niveau_id: int | None = None
    serie_id: int | None = None
    annee_scolaire_id: int | None = None


class ClasseOut(BaseModel):
    id: int
    ecole_id: int
    nom: str
    niveau_id: int
    niveau_nom: str
    cycle: str
    serie_id: int | None
    serie_nom: str | None
    annee_scolaire_id: int
    annee_libelle: str
    effectif: int
