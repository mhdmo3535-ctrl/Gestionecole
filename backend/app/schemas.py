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
    telephone: str | None = None
    actif: bool = True


ROLES_GERABLES = "^(admin|enseignant)$"   # parents/élèves : cycle de vie à part


class UtilisateurCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=150)
    mot_de_passe: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern=ROLES_GERABLES)
    telephone: str | None = Field(default=None, max_length=30)


class UtilisateurUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    prenom: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, pattern=ROLES_GERABLES)
    telephone: str | None = Field(default=None, max_length=30)
    actif: bool | None = None


class MotDePasseUpdate(BaseModel):
    nouveau_mot_de_passe: str = Field(min_length=8, max_length=128)


# ---------- Matières ----------

class MatiereOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ecole_id: int
    nom: str
    code: str | None
    est_choix_langue: bool
    note_directe: bool


# ---------- Affectations enseignant ----------

class AffectationCreate(BaseModel):
    classe_id: int
    matiere_id: int


class AffectationOut(BaseModel):
    id: int
    enseignant_id: int
    classe_id: int
    classe_nom: str
    matiere_id: int
    matiere_nom: str


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
