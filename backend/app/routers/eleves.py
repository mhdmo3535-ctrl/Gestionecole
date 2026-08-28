"""Gestion des élèves : créer, lister, consulter, modifier.

Toutes les routes sont limitées à l'école de l'utilisateur connecté
(multi-école : on ne voit jamais les élèves d'une autre école).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import Eleve
from app.schemas import EleveCreate, EleveOut, EleveUpdate

router = APIRouter(prefix="/eleves", tags=["eleves"])

# admin : accès complet. enseignant : lecture seule (consultation de ses classes).
AdminOnly = Depends(require_roles("admin"))


@router.get("", response_model=list[EleveOut])
def lister_eleves(
    user: CurrentUser,
    db: DbSession,
    q: Annotated[str | None, Query(description="Recherche sur nom, prénom ou matricule")] = None,
    classe_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    stmt = select(Eleve).where(Eleve.ecole_id == user.ecole_id)
    if classe_id is not None:
        stmt = stmt.where(Eleve.classe_id == classe_id)
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Eleve.nom).like(pattern)
            | func.lower(Eleve.prenom).like(pattern)
            | func.lower(Eleve.matricule).like(pattern)
        )
    stmt = stmt.order_by(Eleve.nom, Eleve.prenom).limit(limit).offset(offset)
    return list(db.scalars(stmt))


@router.get("/{eleve_id}", response_model=EleveOut)
def consulter_eleve(eleve_id: int, user: CurrentUser, db: DbSession):
    eleve = db.get(Eleve, eleve_id)
    if eleve is None or eleve.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    return eleve


@router.post("", response_model=EleveOut, status_code=status.HTTP_201_CREATED, dependencies=[AdminOnly])
def creer_eleve(data: EleveCreate, user: CurrentUser, db: DbSession):
    existe = db.scalar(
        select(Eleve).where(
            Eleve.ecole_id == user.ecole_id,
            Eleve.matricule == data.matricule,
        )
    )
    if existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Le matricule {data.matricule} est déjà utilisé dans cette école.",
        )
    eleve = Eleve(ecole_id=user.ecole_id, **data.model_dump())
    db.add(eleve)
    db.commit()
    db.refresh(eleve)
    return eleve


@router.patch("/{eleve_id}", response_model=EleveOut, dependencies=[AdminOnly])
def modifier_eleve(eleve_id: int, data: EleveUpdate, user: CurrentUser, db: DbSession):
    eleve = db.get(Eleve, eleve_id)
    if eleve is None or eleve.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")

    changes = data.model_dump(exclude_unset=True)
    if "matricule" in changes and changes["matricule"] != eleve.matricule:
        conflit = db.scalar(
            select(Eleve).where(
                Eleve.ecole_id == user.ecole_id,
                Eleve.matricule == changes["matricule"],
            )
        )
        if conflit is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Le matricule {changes['matricule']} est déjà utilisé.",
            )

    for field, value in changes.items():
        setattr(eleve, field, value)
    db.commit()
    db.refresh(eleve)
    return eleve
