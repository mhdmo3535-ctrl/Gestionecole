"""Gestion des élèves : créer, lister, consulter, modifier.

Toutes les routes sont limitées à l'école de l'utilisateur connecté
(multi-école : on ne voit jamais les élèves d'une autre école).
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, ecriture, lecture
from app.core.permissions import Domaine
from app.models import Eleve, EleveInfosMedicales, EleveParent, Parent
from app.schemas import (
    EleveCreate,
    EleveOut,
    EleveUpdate,
    InfosMedicalesOut,
    InfosMedicalesUpdate,
    ParentCreate,
    ParentOut,
    ParentUpdate,
)

router = APIRouter(prefix="/eleves", tags=["eleves"])

# admin : accès complet. enseignant : lecture seule (consultation de ses classes).
LireEleves = lecture(Domaine.ELEVES)
GererEleves = ecriture(Domaine.ELEVES)
LireMedical = lecture(Domaine.MEDICAL)
GererMedical = ecriture(Domaine.MEDICAL)


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


@router.post("", response_model=EleveOut, status_code=status.HTTP_201_CREATED, dependencies=[GererEleves])
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


@router.patch("/{eleve_id}", response_model=EleveOut, dependencies=[GererEleves])
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


# ---------------------------------------------------------------------
# Informations médicales — accès strictement réservé à l'administration
# ---------------------------------------------------------------------

def _eleve_de_lecole(db: DbSession, eleve_id: int, ecole_id: int) -> Eleve:
    eleve = db.get(Eleve, eleve_id)
    if eleve is None or eleve.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    return eleve


@router.get("/{eleve_id}/infos-medicales", response_model=InfosMedicalesOut, dependencies=[LireMedical])
def lire_infos_medicales(eleve_id: int, user: CurrentUser, db: DbSession):
    _eleve_de_lecole(db, eleve_id, user.ecole_id)
    infos = db.get(EleveInfosMedicales, eleve_id)
    if infos is None:
        return InfosMedicalesOut(eleve_id=eleve_id)
    return infos


@router.put("/{eleve_id}/infos-medicales", response_model=InfosMedicalesOut, dependencies=[GererMedical])
def enregistrer_infos_medicales(
    eleve_id: int, data: InfosMedicalesUpdate, user: CurrentUser, db: DbSession
):
    _eleve_de_lecole(db, eleve_id, user.ecole_id)
    infos = db.get(EleveInfosMedicales, eleve_id)
    if infos is None:
        infos = EleveInfosMedicales(eleve_id=eleve_id)
        db.add(infos)
    for field, value in data.model_dump().items():
        setattr(infos, field, value)
    infos.updated_par = user.id
    db.commit()
    db.refresh(infos)
    return infos


# ---------------------------------------------------------------------
# Parents / tuteurs
# ---------------------------------------------------------------------

def _vers_parent_out(lien: EleveParent) -> ParentOut:
    p = lien.parent
    return ParentOut(
        parent_id=p.id,
        nom=p.nom,
        prenom=p.prenom,
        telephone=p.telephone,
        email=p.email,
        lien=lien.lien,
        a_un_compte=p.utilisateur_id is not None,
    )


@router.get("/{eleve_id}/parents", response_model=list[ParentOut], dependencies=[LireEleves])
def lister_parents(eleve_id: int, user: CurrentUser, db: DbSession):
    _eleve_de_lecole(db, eleve_id, user.ecole_id)
    liens = db.scalars(select(EleveParent).where(EleveParent.eleve_id == eleve_id))
    return [_vers_parent_out(li) for li in liens]


@router.post(
    "/{eleve_id}/parents",
    response_model=ParentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[GererEleves],
)
def ajouter_parent(eleve_id: int, data: ParentCreate, user: CurrentUser, db: DbSession):
    _eleve_de_lecole(db, eleve_id, user.ecole_id)
    parent = Parent(
        ecole_id=user.ecole_id,
        nom=data.nom,
        prenom=data.prenom,
        telephone=data.telephone,
        email=data.email,
    )
    db.add(parent)
    db.flush()
    lien = EleveParent(eleve_id=eleve_id, parent_id=parent.id, lien=data.lien)
    db.add(lien)
    db.commit()
    db.refresh(lien)
    return _vers_parent_out(lien)


def _lien_de_lecole(db: DbSession, eleve_id: int, parent_id: int, ecole_id: int) -> EleveParent:
    _eleve_de_lecole(db, eleve_id, ecole_id)
    lien = db.get(EleveParent, (eleve_id, parent_id))
    if lien is None or lien.parent.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent introuvable.")
    return lien


@router.patch("/{eleve_id}/parents/{parent_id}", response_model=ParentOut, dependencies=[GererEleves])
def modifier_parent(
    eleve_id: int, parent_id: int, data: ParentUpdate, user: CurrentUser, db: DbSession
):
    lien = _lien_de_lecole(db, eleve_id, parent_id, user.ecole_id)
    changes = data.model_dump(exclude_unset=True)
    if "lien" in changes:
        lien.lien = changes.pop("lien")
    for field, value in changes.items():
        setattr(lien.parent, field, value)
    db.commit()
    db.refresh(lien)
    return _vers_parent_out(lien)


@router.delete(
    "/{eleve_id}/parents/{parent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[GererEleves],
)
def retirer_parent(eleve_id: int, parent_id: int, user: CurrentUser, db: DbSession):
    lien = _lien_de_lecole(db, eleve_id, parent_id, user.ecole_id)
    parent = lien.parent
    db.delete(lien)
    db.flush()
    # supprimer la fiche parent si elle n'est plus rattachée à aucun élève
    autres = db.scalar(select(EleveParent).where(EleveParent.parent_id == parent.id))
    if autres is None and parent.utilisateur_id is None:
        db.delete(parent)
    db.commit()
