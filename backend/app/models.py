"""Modèles SQLAlchemy.

Couvre les tables utilisées par l'API (auth, élèves, classes, référentiel,
coefficients, notes). Le schéma complet fait foi : backend/db/schema.sql.
Les modules restants seront ajoutés au
fur et à mesure.
"""

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Time,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ecole(Base):
    __tablename__ = "ecoles"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(150))
    sigle: Mapped[str | None] = mapped_column(String(20))
    adresse: Mapped[str | None] = mapped_column(String(255))
    telephone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    mode_calcul_moyenne_annuelle: Mapped[str] = mapped_column(String(20))
    est_pilote: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnneeScolaire(Base):
    __tablename__ = "annees_scolaires"

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    libelle: Mapped[str] = mapped_column(String(20))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Trimestre(Base):
    __tablename__ = "trimestres"
    __table_args__ = (UniqueConstraint("annee_scolaire_id", "numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    annee_scolaire_id: Mapped[int] = mapped_column(
        ForeignKey("annees_scolaires.id", ondelete="CASCADE")
    )
    numero: Mapped[int] = mapped_column(SmallInteger)
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)


class Niveau(Base):
    __tablename__ = "niveaux"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(20), unique=True)
    cycle: Mapped[str] = mapped_column(String(10))


class Serie(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(30), unique=True)


class Classe(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    annee_scolaire_id: Mapped[int] = mapped_column(ForeignKey("annees_scolaires.id", ondelete="CASCADE"))
    niveau_id: Mapped[int] = mapped_column(ForeignKey("niveaux.id"))
    serie_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"))
    nom: Mapped[str] = mapped_column(String(50))
    # enseignant qui saisit la note de conduite de la classe
    professeur_principal_id: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL")
    )

    niveau: Mapped[Niveau] = relationship(lazy="joined")
    serie: Mapped[Serie | None] = relationship(lazy="joined")
    annee_scolaire: Mapped[AnneeScolaire] = relationship(lazy="joined")


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    # un ou plusieurs rôles (cumul possible) : voir app/core/permissions.py
    roles: Mapped[list[str]] = mapped_column(ARRAY(String(20)))
    telephone: Mapped[str | None] = mapped_column(String(30))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def a_le_role(self, role: str) -> bool:
        return role in (self.roles or [])

    @property
    def est_enseignant(self) -> bool:
        return self.a_le_role("enseignant")

class Matiere(Base):
    __tablename__ = "matieres"
    __table_args__ = (UniqueConstraint("ecole_id", "nom"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    nom: Mapped[str] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(20))
    est_choix_langue: Mapped[bool] = mapped_column(Boolean, default=False)
    note_directe: Mapped[bool] = mapped_column(Boolean, default=False)
    # False : cours sans note (Travaux dirigés…) — emploi du temps oui, moyennes non
    evaluee: Mapped[bool] = mapped_column(Boolean, default=True)


class EnseignantAffectation(Base):
    __tablename__ = "enseignant_affectations"
    __table_args__ = (UniqueConstraint("enseignant_id", "classe_id", "matiere_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    enseignant_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"))
    classe_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(ForeignKey("matieres.id", ondelete="CASCADE"))

    classe: Mapped[Classe] = relationship(lazy="joined")
    matiere: Mapped[Matiere] = relationship(lazy="joined")


class Creneau(Base):
    """Un cours de l'emploi du temps : une classe, une matière, un professeur, un jour, un horaire."""

    __tablename__ = "creneaux"

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    classe_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(ForeignKey("matieres.id", ondelete="CASCADE"))
    enseignant_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"))
    jour: Mapped[int] = mapped_column(SmallInteger)          # 1 = lundi … 6 = samedi
    heure_debut: Mapped[time] = mapped_column(Time)
    heure_fin: Mapped[time] = mapped_column(Time)

    classe: Mapped[Classe] = relationship(lazy="joined")
    matiere: Mapped[Matiere] = relationship(lazy="joined")
    enseignant: Mapped["Utilisateur"] = relationship(lazy="joined")


class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    telephone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))


class EleveParent(Base):
    __tablename__ = "eleve_parents"

    eleve_id: Mapped[int] = mapped_column(
        ForeignKey("eleves.id", ondelete="CASCADE"), primary_key=True
    )
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), primary_key=True
    )
    lien: Mapped[str | None] = mapped_column(String(20))

    parent: Mapped[Parent] = relationship(lazy="joined")


class Absence(Base):
    __tablename__ = "absences"

    id: Mapped[int] = mapped_column(primary_key=True)
    eleve_id: Mapped[int] = mapped_column(ForeignKey("eleves.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    matiere_id: Mapped[int | None] = mapped_column(ForeignKey("matieres.id"))
    type: Mapped[str] = mapped_column(String(20), default="absence")
    justifiee: Mapped[bool] = mapped_column(Boolean, default=False)
    permission_id: Mapped[int | None] = mapped_column(ForeignKey("permissions_absence.id"))
    saisi_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    matiere: Mapped["Matiere | None"] = relationship(lazy="joined")


class Discipline(Base):
    __tablename__ = "discipline"

    id: Mapped[int] = mapped_column(primary_key=True)
    eleve_id: Mapped[int] = mapped_column(ForeignKey("eleves.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    description: Mapped[str] = mapped_column(Text)
    gravite: Mapped[str] = mapped_column(String(10), default="mineure")
    sanction: Mapped[str | None] = mapped_column(Text)
    signale_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PermissionAbsence(Base):
    __tablename__ = "permissions_absence"

    id: Mapped[int] = mapped_column(primary_key=True)
    eleve_id: Mapped[int] = mapped_column(ForeignKey("eleves.id", ondelete="CASCADE"))
    date_debut: Mapped[date] = mapped_column(Date)
    date_fin: Mapped[date] = mapped_column(Date)
    motif: Mapped[str] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(String(20), default="en_attente")
    traite_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    commentaire_traitement: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    traite_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EleveInfosMedicales(Base):
    __tablename__ = "eleve_infos_medicales"

    eleve_id: Mapped[int] = mapped_column(
        ForeignKey("eleves.id", ondelete="CASCADE"), primary_key=True
    )
    groupe_sanguin: Mapped[str | None] = mapped_column(String(5))
    allergies: Mapped[str | None] = mapped_column(Text)
    contacts_urgence: Mapped[str | None] = mapped_column(Text)
    remarques: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))


class Coefficient(Base):
    __tablename__ = "coefficients"

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    niveau_id: Mapped[int | None] = mapped_column(ForeignKey("niveaux.id"))
    serie_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"))
    matiere_id: Mapped[int] = mapped_column(ForeignKey("matieres.id", ondelete="CASCADE"))
    coefficient: Mapped[Decimal] = mapped_column(Numeric(3, 1))


class CoefficientDefaut(Base):
    __tablename__ = "coefficients_defaut"

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    niveau_id: Mapped[int | None] = mapped_column(ForeignKey("niveaux.id"))
    serie_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"))
    coefficient: Mapped[Decimal] = mapped_column(Numeric(3, 1))


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (UniqueConstraint("eleve_id", "matiere_id", "trimestre_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    eleve_id: Mapped[int] = mapped_column(ForeignKey("eleves.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(ForeignKey("matieres.id", ondelete="CASCADE"))
    trimestre_id: Mapped[int] = mapped_column(ForeignKey("trimestres.id", ondelete="CASCADE"))
    interro1: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    interro2: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    interro3: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    devoir1: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    devoir2: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    note_directe: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    appreciation: Mapped[str | None] = mapped_column(String)
    saisi_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NoteHistorique(Base):
    """Journal des saisies de notes : création, modification, suppression.

    Une note n'est modifiable que par l'enseignant concerné ; chaque
    changement est tracé ici (anciennes et nouvelles valeurs, auteur, date)
    pour que la direction puisse repérer une modification suspecte.
    Les lignes survivent à la suppression de la note.
    """

    __tablename__ = "notes_historique"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int | None] = mapped_column(ForeignKey("notes.id", ondelete="SET NULL"))
    eleve_id: Mapped[int] = mapped_column(ForeignKey("eleves.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(ForeignKey("matieres.id", ondelete="CASCADE"))
    trimestre_id: Mapped[int] = mapped_column(ForeignKey("trimestres.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(20))   # creation | modification | suppression
    anciennes_valeurs: Mapped[dict | None] = mapped_column(JSONB)
    nouvelles_valeurs: Mapped[dict | None] = mapped_column(JSONB)
    auteur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id", ondelete="SET NULL"))
    le: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Eleve(Base):
    __tablename__ = "eleves"
    __table_args__ = (UniqueConstraint("ecole_id", "matricule"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    matricule: Mapped[str] = mapped_column(String(30))
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    date_naissance: Mapped[date | None] = mapped_column(Date)
    sexe: Mapped[str | None] = mapped_column(String(1))
    classe_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id"))
    statut: Mapped[str] = mapped_column(String(20), default="actif")
    photo_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    classe: Mapped[Classe | None] = relationship(lazy="joined")


class TranchePaiement(Base):
    __tablename__ = "tranches_paiement"
    __table_args__ = (UniqueConstraint("ecole_id", "annee_scolaire_id", "numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    annee_scolaire_id: Mapped[int] = mapped_column(
        ForeignKey("annees_scolaires.id", ondelete="CASCADE")
    )
    numero: Mapped[int] = mapped_column(SmallInteger)
    libelle: Mapped[str | None] = mapped_column(String(50))
    montant: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    date_limite: Mapped[date | None] = mapped_column(Date)


class Paiement(Base):
    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(primary_key=True)
    eleve_id: Mapped[int] = mapped_column(ForeignKey("eleves.id", ondelete="CASCADE"))
    tranche_id: Mapped[int] = mapped_column(ForeignKey("tranches_paiement.id"))
    montant_paye: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    date_paiement: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    mode_paiement: Mapped[str | None] = mapped_column(String(20))
    numero_recu: Mapped[str | None] = mapped_column(String(50))
    enregistre_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tranche: Mapped[TranchePaiement] = relationship(lazy="joined")
