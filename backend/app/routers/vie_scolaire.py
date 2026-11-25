"""Vie scolaire : absences, discipline, autorisations d'absence.

Gérée par le surveillant général (et le directeur) ; le censeur consulte.
Les routes /eleves/{id}/… concernent un élève ; /autorisations-absence
regroupe les demandes de toute l'école pour les traiter au même endroit.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ecriture, lecture
from app.core.permissions import Domaine
from app.models import Absence, Classe, Discipline, Eleve, PermissionAbsence, Utilisateur
from app.schemas import (
    AbsenceCreate,
    AbsenceOut,
    DisciplineCreate,
    DisciplineOut,
    PermissionCreate,
    PermissionEcoleOut,
    PermissionOut,
    PermissionTraitement,
)

router = APIRouter(prefix="/eleves", tags=["vie scolaire"])
router_ecole = APIRouter(tags=["vie scolaire"])

LireVieScolaire = lecture(Domaine.VIE_SCOLAIRE)
GererVieScolaire = ecriture(Domaine.VIE_SCOLAIRE)


def _eleve(db: Session, eleve_id: int, ecole_id: int) -> Eleve:
    e = db.get(Eleve, eleve_id)
    if e is None or e.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    return e


# ---------- Absences ----------

@router.get("/{eleve_id}/absences", response_model=list[AbsenceOut], dependencies=[LireVieScolaire])
def lister_absences(eleve_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    stmt = select(Absence).where(Absence.eleve_id == eleve_id).order_by(Absence.date.desc())
    return list(db.scalars(stmt))


@router.post(
    "/{eleve_id}/absences",
    response_model=AbsenceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GererVieScolaire],
)
def ajouter_absence(eleve_id: int, data: AbsenceCreate, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    absence = Absence(eleve_id=eleve_id, saisi_par=user.id, **data.model_dump())
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return absence


@router.delete("/{eleve_id}/absences/{absence_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[GererVieScolaire])
def supprimer_absence(eleve_id: int, absence_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    absence = db.get(Absence, absence_id)
    if absence is None or absence.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence introuvable.")
    db.delete(absence)
    db.commit()


# ---------- Discipline ----------

@router.get("/{eleve_id}/discipline", response_model=list[DisciplineOut], dependencies=[LireVieScolaire])
def lister_discipline(eleve_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    stmt = select(Discipline).where(Discipline.eleve_id == eleve_id).order_by(Discipline.date.desc())
    return list(db.scalars(stmt))


@router.post(
    "/{eleve_id}/discipline",
    response_model=DisciplineOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GererVieScolaire],
)
def ajouter_discipline(eleve_id: int, data: DisciplineCreate, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    payload = data.model_dump(exclude_none=True)
    fait = Discipline(eleve_id=eleve_id, signale_par=user.id, **payload)
    db.add(fait)
    db.commit()
    db.refresh(fait)
    return fait


@router.delete("/{eleve_id}/discipline/{fait_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[GererVieScolaire])
def supprimer_discipline(eleve_id: int, fait_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    fait = db.get(Discipline, fait_id)
    if fait is None or fait.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fait introuvable.")
    db.delete(fait)
    db.commit()


# ---------- Permissions d'absence ----------

@router.get("/{eleve_id}/permissions", response_model=list[PermissionOut], dependencies=[LireVieScolaire])
def lister_permissions(eleve_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    stmt = (
        select(PermissionAbsence)
        .where(PermissionAbsence.eleve_id == eleve_id)
        .order_by(PermissionAbsence.date_debut.desc())
    )
    return list(db.scalars(stmt))


@router.post(
    "/{eleve_id}/permissions",
    response_model=PermissionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GererVieScolaire],
)
def ajouter_permission(eleve_id: int, data: PermissionCreate, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    if data.date_fin < data.date_debut:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La date de fin doit être postérieure ou égale à la date de début.",
        )
    perm = PermissionAbsence(eleve_id=eleve_id, **data.model_dump())
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


@router.patch("/{eleve_id}/permissions/{permission_id}", response_model=PermissionOut, dependencies=[GererVieScolaire])
def traiter_permission(
    eleve_id: int, permission_id: int, data: PermissionTraitement, user: CurrentUser, db: DbSession
):
    _eleve(db, eleve_id, user.ecole_id)
    perm = db.get(PermissionAbsence, permission_id)
    if perm is None or perm.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission introuvable.")
    perm.statut = data.statut
    perm.commentaire_traitement = data.commentaire_traitement
    if data.statut == "en_attente":
        perm.traite_par = None
        perm.traite_le = None
    else:
        perm.traite_par = user.id
        perm.traite_le = datetime.now(timezone.utc)
    db.commit()
    db.refresh(perm)
    return perm


@router.delete("/{eleve_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[GererVieScolaire])
def supprimer_permission(eleve_id: int, permission_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    perm = db.get(PermissionAbsence, permission_id)
    if perm is None or perm.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission introuvable.")
    db.delete(perm)
    db.commit()


# ---------- Toutes les demandes de l'école ----------

@router_ecole.get("/autorisations-absence", response_model=list[PermissionEcoleOut], dependencies=[LireVieScolaire])
def autorisations_de_l_ecole(user: CurrentUser, db: DbSession, statut: str | None = None):
    """Les demandes en attente d'abord (les plus anciennes en tête), puis les traitées (récentes d'abord)."""
    stmt = (
        select(PermissionAbsence, Eleve, Classe, Utilisateur)
        .join(Eleve, Eleve.id == PermissionAbsence.eleve_id)
        .outerjoin(Classe, Classe.id == Eleve.classe_id)
        .outerjoin(Utilisateur, Utilisateur.id == PermissionAbsence.traite_par)
        .where(Eleve.ecole_id == user.ecole_id)
    )
    if statut is not None:
        if statut not in ("en_attente", "approuve", "rejete"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Statut inconnu.")
        stmt = stmt.where(PermissionAbsence.statut == statut)
    lignes = [
        PermissionEcoleOut(
            id=p.id,
            eleve_id=e.id,
            date_debut=p.date_debut,
            date_fin=p.date_fin,
            motif=p.motif,
            statut=p.statut,
            commentaire_traitement=p.commentaire_traitement,
            traite_le=p.traite_le,
            eleve_nom=f"{e.nom} {e.prenom}",
            matricule=e.matricule,
            classe_nom=c.nom if c else None,
            traite_par_nom=f"{u.prenom} {u.nom}" if u else None,
            demande_le=p.created_at,
        )
        for p, e, c, u in db.execute(stmt)
    ]
    attente = sorted((l for l in lignes if l.statut == "en_attente"), key=lambda l: (l.date_debut, l.id))
    traitees = sorted((l for l in lignes if l.statut != "en_attente"),
                      key=lambda l: (l.traite_le or l.demande_le), reverse=True)
    return attente + traitees

