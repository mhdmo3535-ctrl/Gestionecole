"""Modèles SQLAlchemy.

Couvre les tables utilisées par l'API (auth, élèves, classes, référentiel,
coefficients, notes). Le schéma complet fait foi : backend/db/schema.sql.
Les modules restants (absences, discipline, paiements...) seront ajoutés au
fur et à mesure.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
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
    role: Mapped[str] = mapped_column(String(20))
    telephone: Mapped[str | None] = mapped_column(String(30))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Matiere(Base):
    __tablename__ = "matieres"
    __table_args__ = (UniqueConstraint("ecole_id", "nom"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ecole_id: Mapped[int] = mapped_column(ForeignKey("ecoles.id", ondelete="CASCADE"))
    nom: Mapped[str] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(20))
    est_choix_langue: Mapped[bool] = mapped_column(Boolean, default=False)
    note_directe: Mapped[bool] = mapped_column(Boolean, default=False)


class EnseignantAffectation(Base):
    __tablename__ = "enseignant_affectations"
    __table_args__ = (UniqueConstraint("enseignant_id", "classe_id", "matiere_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    enseignant_id: Mapped[int] = mapped_column(ForeignKey("utilisateurs.id", ondelete="CASCADE"))
    classe_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    matiere_id: Mapped[int] = mapped_column(ForeignKey("matieres.id", ondelete="CASCADE"))

    classe: Mapped[Classe] = relationship(lazy="joined")
    matiere: Mapped[Matiere] = relationship(lazy="joined")


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
    valide: Mapped[bool] = mapped_column(Boolean, default=False)
    valide_par: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    valide_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
