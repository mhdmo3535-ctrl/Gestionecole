"""Gestion des matières d'une école et de leurs coefficients.

L'admin déclare les matières de son école, puis, pour chaque niveau
(collège) ou série (lycée), le coefficient de la matière. Une matière
sans ligne de coefficient pour un niveau/série n'y « existe » pas
(elle n'apparaît ni dans la classe ni au bulletin).

Une matière « non évaluée » (evaluee = false, ex : Travaux dirigés) est un
cours sans note : elle va à l'emploi du temps mais n'a jamais de coefficient.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ecriture, lecture
from app.core.permissions import Domaine
from app.models import Coefficient, Matiere, Niveau, Note, Serie
from app.schemas import (
    CoefficientDeclare,
    CoefficientOut,
    MatiereCreate,
    MatiereOut,
    MatiereUpdate,
)

router = APIRouter(prefix="/matieres", tags=["matières"])

GererPedagogie = ecriture(Domaine.PEDAGOGIE)


def _verifier_type(evaluee: bool, note_directe: bool) -> None:
    if not evaluee and note_directe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Une matière sans note ne peut pas être à « note directe ».",
        )


def _matiere(db: Session, matiere_id: int, ecole_id: int) -> Matiere:
    m = db.get(Matiere, matiere_id)
    if m is None or m.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable.")
    return m


@router.get("", response_model=list[MatiereOut])
def lister_matieres(user: CurrentUser, db: DbSession):
    stmt = select(Matiere).where(Matiere.ecole_id == user.ecole_id).order_by(Matiere.nom)
    return list(db.scalars(stmt))


@router.post("", response_model=MatiereOut, status_code=status.HTTP_201_CREATED, dependencies=[GererPedagogie])
def creer_matiere(data: MatiereCreate, user: CurrentUser, db: DbSession):
    nom = data.nom.strip()
    _verifier_type(data.evaluee, data.note_directe)
    if db.scalar(select(Matiere).where(Matiere.ecole_id == user.ecole_id, func.lower(Matiere.nom) == nom.lower())):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La matière « {nom} » existe déjà dans cette école.",
        )
    matiere = Matiere(
        ecole_id=user.ecole_id,
        nom=nom,
        code=data.code,
        est_choix_langue=data.est_choix_langue,
        note_directe=data.note_directe,
        evaluee=data.evaluee,
    )
    db.add(matiere)
    db.commit()
    db.refresh(matiere)
    return matiere


@router.get("/{matiere_id}", response_model=MatiereOut)
def consulter_matiere(matiere_id: int, user: CurrentUser, db: DbSession):
    return _matiere(db, matiere_id, user.ecole_id)


@router.patch("/{matiere_id}", response_model=MatiereOut, dependencies=[GererPedagogie])
def modifier_matiere(matiere_id: int, data: MatiereUpdate, user: CurrentUser, db: DbSession):
    matiere = _matiere(db, matiere_id, user.ecole_id)
    changes = data.model_dump(exclude_unset=True)
    if "nom" in changes:
        nom = changes["nom"].strip()
        conflit = db.scalar(
            select(Matiere).where(
                Matiere.ecole_id == user.ecole_id,
                func.lower(Matiere.nom) == nom.lower(),
                Matiere.id != matiere.id,
            )
        )
        if conflit is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"La matière « {nom} » existe déjà.")
        changes["nom"] = nom
    evaluee = changes.get("evaluee", matiere.evaluee)
    _verifier_type(evaluee, changes.get("note_directe", matiere.note_directe))
    if matiere.evaluee and evaluee is False:
        nb_notes = db.scalar(select(func.count()).select_from(Note).where(Note.matiere_id == matiere.id))
        if nb_notes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Impossible : {nb_notes} note(s) sont déjà enregistrée(s) pour cette matière.",
            )
        # une matière sans note n'a plus de coefficient
        for c in db.scalars(select(Coefficient).where(Coefficient.matiere_id == matiere.id)):
            db.delete(c)
    for field, value in changes.items():
        setattr(matiere, field, value)
    db.commit()
    db.refresh(matiere)
    return matiere


@router.delete("/{matiere_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[GererPedagogie])
def supprimer_matiere(matiere_id: int, user: CurrentUser, db: DbSession):
    matiere = _matiere(db, matiere_id, user.ecole_id)
    nb_notes = db.scalar(select(func.count()).select_from(Note).where(Note.matiere_id == matiere.id))
    if nb_notes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossible de supprimer : {nb_notes} note(s) enregistrée(s) pour cette matière.",
        )
    db.delete(matiere)   # les lignes de coefficients sont supprimées en cascade
    db.commit()


# ---------------------------------------------------------------------
# Coefficients déclarés pour une matière
# ---------------------------------------------------------------------

@router.get("/{matiere_id}/coefficients", response_model=list[CoefficientOut])
def lister_coefficients(matiere_id: int, user: CurrentUser, db: DbSession):
    _matiere(db, matiere_id, user.ecole_id)
    stmt = select(Coefficient).where(
        Coefficient.ecole_id == user.ecole_id, Coefficient.matiere_id == matiere_id
    )
    return list(db.scalars(stmt))


@router.put("/{matiere_id}/coefficients", response_model=CoefficientOut, dependencies=[GererPedagogie])
def declarer_coefficient(matiere_id: int, data: CoefficientDeclare, user: CurrentUser, db: DbSession):
    matiere = _matiere(db, matiere_id, user.ecole_id)
    if not matiere.evaluee:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"« {matiere.nom} » n'est pas notée : elle n'a pas de coefficient.",
        )
    if data.niveau_id is None and data.serie_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Précisez un niveau (collège) ou une série (lycée).",
        )
    niveau = None
    if data.niveau_id is not None:
        niveau = db.get(Niveau, data.niveau_id)
        if niveau is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Niveau inconnu.")
    if data.serie_id is not None:
        if db.get(Serie, data.serie_id) is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Série inconnue.")
        if niveau is not None and niveau.cycle == "college":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le collège n'a pas de série.",
            )

    existante = None
    for c in db.scalars(
        select(Coefficient).where(
            Coefficient.ecole_id == user.ecole_id, Coefficient.matiere_id == matiere_id
        )
    ):
        if c.niveau_id == data.niveau_id and c.serie_id == data.serie_id:
            existante = c
            break

    if existante is not None:
        existante.coefficient = data.coefficient
        db.commit()
        db.refresh(existante)
        return existante

    coef = Coefficient(
        ecole_id=user.ecole_id,
        matiere_id=matiere_id,
        niveau_id=data.niveau_id,
        serie_id=data.serie_id,
        coefficient=data.coefficient,
    )
    db.add(coef)
    db.commit()
    db.refresh(coef)
    return coef


@router.delete(
    "/{matiere_id}/coefficients/{coefficient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[GererPedagogie],
)
def retirer_coefficient(matiere_id: int, coefficient_id: int, user: CurrentUser, db: DbSession):
    _matiere(db, matiere_id, user.ecole_id)
    coef = db.get(Coefficient, coefficient_id)
    if coef is None or coef.matiere_id != matiere_id or coef.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coefficient introuvable.")
    db.delete(coef)
    db.commit()
