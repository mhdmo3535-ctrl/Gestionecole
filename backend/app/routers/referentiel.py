"""Données de référence : niveaux, séries, années scolaires."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import AnneeScolaire, Ecole, Niveau, Serie, Trimestre
from app.schemas import (
    AnneeScolaireCreate,
    AnneeScolaireOut,
    AnneeScolaireUpdate,
    EcoleOut,
    NiveauOut,
    SerieOut,
    TrimestreOut,
    TrimestreUpdate,
)

router = APIRouter(tags=["référentiel"])

AdminOnly = Depends(require_roles("admin"))


@router.get("/ecole", response_model=EcoleOut)
def mon_ecole(user: CurrentUser, db: DbSession):
    """L'école de l'utilisateur connecté."""
    ecole = db.get(Ecole, user.ecole_id)
    if ecole is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="École introuvable.")
    return ecole


@router.get("/niveaux", response_model=list[NiveauOut])
def lister_niveaux(user: CurrentUser, db: DbSession):
    return list(db.scalars(select(Niveau).order_by(Niveau.id)))


@router.get("/series", response_model=list[SerieOut])
def lister_series(user: CurrentUser, db: DbSession):
    return list(db.scalars(select(Serie).order_by(Serie.nom)))


@router.get("/annees-scolaires", response_model=list[AnneeScolaireOut])
def lister_annees(user: CurrentUser, db: DbSession):
    stmt = (
        select(AnneeScolaire)
        .where(AnneeScolaire.ecole_id == user.ecole_id)
        .order_by(AnneeScolaire.date_debut.desc())
    )
    return list(db.scalars(stmt))


@router.post(
    "/annees-scolaires",
    response_model=AnneeScolaireOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[AdminOnly],
)
def creer_annee(data: AnneeScolaireCreate, user: CurrentUser, db: DbSession):
    if data.date_fin <= data.date_debut:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La date de fin doit être postérieure à la date de début.",
        )
    existe = db.scalar(
        select(AnneeScolaire).where(
            AnneeScolaire.ecole_id == user.ecole_id,
            AnneeScolaire.libelle == data.libelle,
        )
    )
    if existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'année scolaire « {data.libelle} » existe déjà.",
        )

    annee = AnneeScolaire(ecole_id=user.ecole_id, **data.model_dump())
    if annee.active:
        _desactiver_autres_annees(db, user.ecole_id, sauf_id=None)
    db.add(annee)
    db.flush()
    # chaque année a ses 3 trimestres (dates à renseigner ensuite)
    db.add_all([Trimestre(annee_scolaire_id=annee.id, numero=n) for n in (1, 2, 3)])
    db.commit()
    db.refresh(annee)
    return annee


@router.patch("/annees-scolaires/{annee_id}", response_model=AnneeScolaireOut, dependencies=[AdminOnly])
def modifier_annee(annee_id: int, data: AnneeScolaireUpdate, user: CurrentUser, db: DbSession):
    annee = db.get(AnneeScolaire, annee_id)
    if annee is None or annee.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Année scolaire introuvable.")

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(annee, field, value)

    if annee.date_fin <= annee.date_debut:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La date de fin doit être postérieure à la date de début.",
        )
    if changes.get("active") is True:
        _desactiver_autres_annees(db, user.ecole_id, sauf_id=annee.id)

    db.commit()
    db.refresh(annee)
    return annee


@router.get("/trimestres", response_model=list[TrimestreOut])
def lister_trimestres(user: CurrentUser, db: DbSession, annee_scolaire_id: int | None = None):
    if annee_scolaire_id is None:
        annee = db.scalar(
            select(AnneeScolaire).where(
                AnneeScolaire.ecole_id == user.ecole_id, AnneeScolaire.active.is_(True)
            )
        )
        if annee is None:
            return []
        annee_scolaire_id = annee.id
    else:
        annee = db.get(AnneeScolaire, annee_scolaire_id)
        if annee is None or annee.ecole_id != user.ecole_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Année scolaire introuvable.")

    stmt = (
        select(Trimestre)
        .where(Trimestre.annee_scolaire_id == annee_scolaire_id)
        .order_by(Trimestre.numero)
    )
    return list(db.scalars(stmt))


@router.patch("/trimestres/{trimestre_id}", response_model=TrimestreOut, dependencies=[AdminOnly])
def modifier_trimestre(trimestre_id: int, data: TrimestreUpdate, user: CurrentUser, db: DbSession):
    tri = db.get(Trimestre, trimestre_id)
    if tri is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trimestre introuvable.")
    annee = db.get(AnneeScolaire, tri.annee_scolaire_id)
    if annee is None or annee.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trimestre introuvable.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tri, field, value)
    if tri.date_debut and tri.date_fin and tri.date_fin <= tri.date_debut:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La date de fin doit être postérieure à la date de début.",
        )
    db.commit()
    db.refresh(tri)
    return tri


def _desactiver_autres_annees(db: DbSession, ecole_id: int, sauf_id: int | None) -> None:
    """Une seule année active par école."""
    stmt = select(AnneeScolaire).where(
        AnneeScolaire.ecole_id == ecole_id, AnneeScolaire.active.is_(True)
    )
    for autre in db.scalars(stmt):
        if autre.id != sauf_id:
            autre.active = False
