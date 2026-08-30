"""Vie scolaire d'un élève : absences, discipline, permissions d'absence.

Réservé à l'administration pour l'instant (le Surveillant Général aura ces
accès lors du découpage des rôles).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import Absence, Discipline, Eleve, PermissionAbsence
from app.schemas import (
    AbsenceCreate,
    AbsenceOut,
    DisciplineCreate,
    DisciplineOut,
    PermissionCreate,
    PermissionOut,
    PermissionTraitement,
)

router = APIRouter(prefix="/eleves", tags=["vie scolaire"], dependencies=[Depends(require_roles("admin"))])


def _eleve(db: Session, eleve_id: int, ecole_id: int) -> Eleve:
    e = db.get(Eleve, eleve_id)
    if e is None or e.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    return e


# ---------- Absences ----------

@router.get("/{eleve_id}/absences", response_model=list[AbsenceOut])
def lister_absences(eleve_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    stmt = select(Absence).where(Absence.eleve_id == eleve_id).order_by(Absence.date.desc())
    return list(db.scalars(stmt))


@router.post(
    "/{eleve_id}/absences",
    response_model=AbsenceOut,
    status_code=status.HTTP_201_CREATED,
)
def ajouter_absence(eleve_id: int, data: AbsenceCreate, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    absence = Absence(eleve_id=eleve_id, saisi_par=user.id, **data.model_dump())
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return absence


@router.delete("/{eleve_id}/absences/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_absence(eleve_id: int, absence_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    absence = db.get(Absence, absence_id)
    if absence is None or absence.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Absence introuvable.")
    db.delete(absence)
    db.commit()


# ---------- Discipline ----------

@router.get("/{eleve_id}/discipline", response_model=list[DisciplineOut])
def lister_discipline(eleve_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    stmt = select(Discipline).where(Discipline.eleve_id == eleve_id).order_by(Discipline.date.desc())
    return list(db.scalars(stmt))


@router.post(
    "/{eleve_id}/discipline",
    response_model=DisciplineOut,
    status_code=status.HTTP_201_CREATED,
)
def ajouter_discipline(eleve_id: int, data: DisciplineCreate, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    payload = data.model_dump(exclude_none=True)
    fait = Discipline(eleve_id=eleve_id, signale_par=user.id, **payload)
    db.add(fait)
    db.commit()
    db.refresh(fait)
    return fait


@router.delete("/{eleve_id}/discipline/{fait_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_discipline(eleve_id: int, fait_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    fait = db.get(Discipline, fait_id)
    if fait is None or fait.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fait introuvable.")
    db.delete(fait)
    db.commit()


# ---------- Permissions d'absence ----------

@router.get("/{eleve_id}/permissions", response_model=list[PermissionOut])
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


@router.patch("/{eleve_id}/permissions/{permission_id}", response_model=PermissionOut)
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


@router.delete("/{eleve_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_permission(eleve_id: int, permission_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    perm = db.get(PermissionAbsence, permission_id)
    if perm is None or perm.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission introuvable.")
    db.delete(perm)
    db.commit()
