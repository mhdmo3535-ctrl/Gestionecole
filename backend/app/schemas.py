"""Schémas Pydantic : formes des données en entrée et en sortie de l'API."""

import datetime as _dt
from datetime import date, datetime
from typing import Annotated, Literal

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
    roles: list[str]
    telephone: str | None = None
    actif: bool = True


# rôles attribuables via /utilisateurs (parents/élèves : cycle de vie à part)
RolePersonnel = Literal["directeur", "censeur", "surveillant", "comptable", "secretaire", "enseignant"]
ListeRoles = Annotated[list[RolePersonnel], Field(min_length=1, max_length=6)]


class UtilisateurCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=150)
    mot_de_passe: str = Field(min_length=8, max_length=128)
    roles: ListeRoles
    telephone: str | None = Field(default=None, max_length=30)


class UtilisateurUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    prenom: str | None = Field(default=None, min_length=1, max_length=100)
    roles: ListeRoles | None = None
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
    evaluee: bool = True


class MatiereCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    code: str | None = Field(default=None, max_length=20)
    est_choix_langue: bool = False
    note_directe: bool = False
    evaluee: bool = True


class MatiereUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, max_length=20)
    est_choix_langue: bool | None = None
    note_directe: bool | None = None
    evaluee: bool | None = None


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


class PermissionEcoleOut(PermissionOut):
    """Une demande vue depuis la liste de toute l'école."""

    model_config = ConfigDict(from_attributes=False)

    eleve_nom: str
    matricule: str
    classe_nom: str | None
    traite_par_nom: str | None
    demande_le: datetime


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
    professeur_principal_id: int | None = None


class ClasseUpdate(BaseModel):
    nom: str | None = Field(default=None, min_length=1, max_length=50)
    niveau_id: int | None = None
    serie_id: int | None = None
    annee_scolaire_id: int | None = None
    professeur_principal_id: int | None = None


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
    professeur_principal_id: int | None = None
    professeur_principal_nom: str | None = None


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
    # calculé, non stocké :
    moyenne: float | None = None      # moyenne de la matière si exploitable
    statut: str = "sans_note"         # sans_note | incomplete | calculee | directe


class NoteHistoriqueOut(BaseModel):
    id: int
    note_id: int | None
    eleve_id: int
    eleve_nom: str
    matiere_id: int
    matiere_nom: str
    trimestre_id: int
    action: str                       # creation | modification | suppression
    anciennes_valeurs: dict | None
    nouvelles_valeurs: dict | None
    auteur_id: int | None
    auteur_nom: str | None
    le: datetime


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


# ---------- Paiements ----------

MODES_PAIEMENT = "^(especes|mobile_money|virement|cheque)$"
Montant = Annotated[float, Field(gt=0, le=99_999_999)]


class TrancheCreate(BaseModel):
    libelle: str | None = Field(default=None, max_length=50)
    montant: Montant
    date_limite: date | None = None
    annee_scolaire_id: int | None = None   # défaut : année scolaire active


class TrancheUpdate(BaseModel):
    libelle: str | None = Field(default=None, max_length=50)
    montant: Montant | None = None
    date_limite: date | None = None


class TrancheOut(BaseModel):
    id: int
    annee_scolaire_id: int
    numero: int
    libelle: str
    montant: float
    date_limite: date | None
    nb_paiements: int = 0


class PaiementCreate(BaseModel):
    tranche_id: int
    montant_paye: Montant
    date_paiement: date | None = None       # défaut : aujourd'hui
    mode_paiement: str = Field(default="especes", pattern=MODES_PAIEMENT)


class PaiementOut(BaseModel):
    id: int
    eleve_id: int
    tranche_id: int
    tranche_libelle: str
    montant_paye: float
    date_paiement: date
    mode_paiement: str | None
    numero_recu: str | None
    enregistre_par_nom: str | None
    created_at: datetime


class SituationTranche(BaseModel):
    tranche_id: int
    numero: int
    libelle: str
    montant: float
    date_limite: date | None
    paye: float
    reste: float
    statut: str          # solde | partiel | non_paye | en_retard


class SituationEleve(BaseModel):
    eleve_id: int
    annee_scolaire_id: int | None
    annee_libelle: str | None
    total_du: float
    total_paye: float
    reste: float
    statut: str          # solde | partiel | non_paye | en_retard | aucune_tranche
    tranches: list[SituationTranche]
    paiements: list[PaiementOut]


class RecuOut(BaseModel):
    paiement: PaiementOut
    ecole_nom: str
    ecole_sigle: str | None
    ecole_adresse: str | None
    ecole_telephone: str | None
    annee_libelle: str
    eleve_matricule: str
    eleve_nom: str
    eleve_prenom: str
    classe_nom: str | None
    tranche_montant: float
    tranche_reste_apres: float
    total_du: float
    total_paye_a_date: float
    reste_global: float


class SuiviLigne(BaseModel):
    eleve_id: int
    matricule: str
    nom: str
    prenom: str
    classe_id: int
    classe_nom: str
    total_du: float
    total_paye: float
    reste: float
    statut: str
    dernier_paiement: date | None


class SuiviPaiements(BaseModel):
    annee_scolaire_id: int
    annee_libelle: str
    nb_tranches: int
    total_attendu: float
    total_encaisse: float
    reste: float
    nb_eleves: int
    nb_soldes: int
    nb_en_retard: int
    lignes: list[SuiviLigne]


# ---------- Tableau de bord ----------

class TdbTrimestre(BaseModel):
    id: int
    numero: int
    annee_libelle: str


class TdbPeriode(BaseModel):
    debut: date
    fin: date
    jours_ouvres: int


class TdbEffectifs(BaseModel):
    eleves_actifs: int
    filles: int
    garcons: int
    classes: int
    enseignants_actifs: int


class TdbScolarite(BaseModel):
    moyenne_ecole: float | None
    taux_reussite: float | None      # part des élèves notés avec une moyenne >= 10
    eleves_notes: int


class TdbVieScolaire(BaseModel):
    taux_presence: float | None
    jours_absence: int
    retards: int
    permissions_en_attente: int


class TdbFinances(BaseModel):
    annee_libelle: str
    attendu: float
    encaisse: float
    reste: float
    taux_recouvrement: float | None
    encaisse_mois: float
    eleves_en_retard: int


class TdbAlerte(BaseModel):
    code: str
    niveau: str                      # attention | info
    libelle: str
    nombre: int
    lien: str | None = None


class TdbLigne(BaseModel):
    """Une classe (ou un niveau, classe_id = None) ; chaque indicateur est None si non visible."""

    classe_id: int | None = None
    libelle: str
    niveau_nom: str
    effectif: int
    moyenne: float | None = None
    taux_reussite: float | None = None
    taux_presence: float | None = None
    taux_recouvrement: float | None = None


class TableauDeBord(BaseModel):
    trimestre: TdbTrimestre | None
    periode_presence: TdbPeriode | None
    effectifs: TdbEffectifs
    scolarite: TdbScolarite | None
    vie_scolaire: TdbVieScolaire | None
    finances: TdbFinances | None
    alertes: list[TdbAlerte]
    classes: list[TdbLigne]
    niveaux: list[TdbLigne]


# ---------- Emploi du temps ----------

class CreneauEcrire(BaseModel):
    classe_id: int
    matiere_id: int
    enseignant_id: int
    jour: int = Field(ge=1, le=6)            # 1 = lundi … 6 = samedi
    heure_debut: _dt.time
    heure_fin: _dt.time
    # True : si le professeur n'est pas encore affecté à cette classe pour cette
    # matière, l'affectation est créée en même temps que le cours
    creer_affectation: bool = False


class CreneauModifier(BaseModel):
    matiere_id: int | None = None
    enseignant_id: int | None = None
    jour: int | None = Field(default=None, ge=1, le=6)
    heure_debut: _dt.time | None = None
    heure_fin: _dt.time | None = None
    creer_affectation: bool = False


class CreneauOut(BaseModel):
    id: int
    classe_id: int
    classe_nom: str
    matiere_id: int
    matiere_nom: str
    enseignant_id: int
    enseignant_nom: str
    jour: int
    heure_debut: _dt.time
    heure_fin: _dt.time
    duree_minutes: int


class AffectationClasseOut(BaseModel):
    """Qui enseigne quoi dans une classe (pour proposer le bon professeur)."""

    enseignant_id: int
    enseignant_nom: str
    matiere_id: int
    matiere_nom: str

