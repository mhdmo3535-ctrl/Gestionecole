"""Schémas Pydantic : formes des données en entrée et en sortie de l'API."""

import datetime as _dt
from datetime import date, datetime
from typing import Annotated

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


class MatiereCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    code: str | None = Field(default=None, max_length=20)
    est_choix_langue: bool = False
    note_directe: bool = False


class MatiereUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, max_length=20)
    est_choix_langue: bool | None = None
    note_directe: bool | None = None


class CoefficientDeclare(BaseModel):
    niveau_id: int | None = None
    serie_id: int | None = None
    coefficient: float = Field(gt=0, le=99)


class CoefficientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matiere_id: int
    niveau_id: int | None
    serie_id: int | None
    coefficient: float


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


class InfosMedicalesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    eleve_id: int
    groupe_sanguin: str | None = None
    allergies: str | None = None
    contacts_urgence: str | None = None
    remarques: str | None = None
    updated_at: datetime | None = None
    updated_par: int | None = None


class InfosMedicalesUpdate(BaseModel):
    groupe_sanguin: str | None = Field(default=None, max_length=5)
    allergies: str | None = None
    contacts_urgence: str | None = None
    remarques: str | None = None


LIEN_PARENT = "^(pere|mere|tuteur)$"


class ParentOut(BaseModel):
    parent_id: int
    nom: str
    prenom: str
    telephone: str | None
    email: str | None
    lien: str | None
    a_un_compte: bool


class ParentCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    telephone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=150)
    lien: str | None = Field(default=None, pattern=LIEN_PARENT)


class ParentUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    prenom: str | None = Field(default=None, min_length=1, max_length=100)
    telephone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=150)
    lien: str | None = Field(default=None, pattern=LIEN_PARENT)


# ---------- Vie scolaire : absences, discipline, permissions ----------

class AbsenceCreate(BaseModel):
    date: _dt.date
    type: str = Field(default="absence", pattern="^(absence|retard)$")
    matiere_id: int | None = None
    justifiee: bool = False


class AbsenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eleve_id: int
    date: _dt.date
    type: str
    matiere_id: int | None
    justifiee: bool
    permission_id: int | None


class DisciplineCreate(BaseModel):
    date: _dt.date | None = None
    description: str = Field(min_length=1)
    gravite: str = Field(default="mineure", pattern="^(mineure|moyenne|grave)$")
    sanction: str | None = None


class DisciplineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eleve_id: int
    date: _dt.date
    description: str
    gravite: str
    sanction: str | None


class PermissionCreate(BaseModel):
    date_debut: date
    date_fin: date
    motif: str = Field(min_length=1)


class PermissionTraitement(BaseModel):
    statut: str = Field(pattern="^(approuve|rejete|en_attente)$")
    commentaire_traitement: str | None = None


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eleve_id: int
    date_debut: date
    date_fin: date
    motif: str
    statut: str
    commentaire_traitement: str | None
    traite_le: datetime | None


# ---------- Référentiel ----------

class EcoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    sigle: str | None
    adresse: str | None
    telephone: str | None
    email: str | None
    mode_calcul_moyenne_annuelle: str
    est_pilote: bool


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


class TrimestreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    annee_scolaire_id: int
    numero: int
    date_debut: date | None
    date_fin: date | None


class TrimestreUpdate(BaseModel):
    date_debut: date | None = None
    date_fin: date | None = None


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


class ClasseMatiereOut(BaseModel):
    """Une matière déclarée pour la classe, avec son coefficient résolu."""

    matiere_id: int
    nom: str
    note_directe: bool
    coefficient: float


# ---------- Notes ----------

Note20 = Annotated[float, Field(ge=0, le=20)]


class NoteEcrire(BaseModel):
    eleve_id: int
    matiere_id: int
    trimestre_id: int
    interro1: Note20 | None = None
    interro2: Note20 | None = None
    interro3: Note20 | None = None
    devoir1: Note20 | None = None
    devoir2: Note20 | None = None
    note_directe: Note20 | None = None
    appreciation: str | None = None


class NoteValidation(BaseModel):
    valide: bool


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eleve_id: int
    matiere_id: int
    trimestre_id: int
    interro1: float | None
    interro2: float | None
    interro3: float | None
    devoir1: float | None
    devoir2: float | None
    note_directe: float | None
    appreciation: str | None
    saisi_par: int | None
    valide: bool
    valide_par: int | None
    # calculé, non stocké :
    moyenne: float | None = None      # moyenne de la matière si exploitable
    statut: str = "sans_note"         # sans_note | incomplete | calculee | directe


# ---------- Bulletins ----------

class BulletinLigne(BaseModel):
    matiere_id: int
    matiere_nom: str
    coefficient: float
    note_directe: bool
    moyenne: float | None
    moyenne_affichee: str | None
    moyenne_coefficientee: float | None
    rang: int | None
    statut: str                       # sans_note | incomplete | calculee | directe
    appreciation: str | None = None


class BulletinEleve(BaseModel):
    eleve_id: int
    matricule: str
    nom: str
    prenom: str
    classe_id: int
    classe_nom: str
    trimestre_id: int
    trimestre_numero: int
    lignes: list[BulletinLigne]
    moyenne_generale: float | None
    moyenne_generale_affichee: str | None
    rang: int | None
    effectif_classe: int
    mode_calcul_annuel: str
    moyenne_annuelle: float | None = None
    moyenne_annuelle_affichee: str | None = None
    decision: str | None = None       # admis | redouble (si l'année est complète)


class BulletinClasseLigne(BaseModel):
    eleve_id: int
    matricule: str
    nom: str
    prenom: str
    moyenne_generale: float | None
    moyenne_generale_affichee: str | None
    rang: int | None
    moyenne_annuelle: float | None = None
    decision: str | None = None


class BulletinClasse(BaseModel):
    classe_id: int
    classe_nom: str
    trimestre_id: int
    trimestre_numero: int
    effectif_classe: int
    eleves: list[BulletinClasseLigne]


class ProgressionPoint(BaseModel):
    trimestre_id: int
    trimestre_numero: int
    moyenne_generale: float | None
    moyenne_generale_affichee: str | None


class ProgressionEleve(BaseModel):
    eleve_id: int
    classe_id: int
    classe_nom: str
    points: list[ProgressionPoint]
