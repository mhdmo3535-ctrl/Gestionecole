"""Gestion des classes (ex : « 3e A », « Terminale D »).

Une classe appartient à une école, une année scolaire, un niveau, et
éventuellement une série (lycée uniquement). Les élèves y sont rattachés
via ``eleves.classe_id``.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import AnneeScolaire, Classe, Eleve, Matiere, Niveau, Serie
from app.schemas import ClasseCreate, ClasseMatiereOut, ClasseOut, ClasseUpdate, EleveOut
from app.services.coefficients import matieres_de_la_classe

router = APIRouter(prefix="/classes", tags=["classes"])

AdminOnly = Depends(require_roles("admin"))


def _annee_active_id(db: DbSession, ecole_id: int) -> int:
    annee = db.scalar(
        select(AnneeScolaire).where(
            AnneeScolaire.ecole_id == ecole_id, AnneeScolaire.active.is_(True)
        )
    )
    if annee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune année scolaire active. Précisez annee_scolaire_id ou activez une année.",
        )
    return annee.id


def _valider_niveau_serie(db: DbSession, niveau_id: int, serie_id: int | None) -> None:
    niveau = db.get(Niveau, niveau_id)
    if niveau is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Niveau inconnu.")
    if serie_id is not None:
        if db.get(Serie, serie_id) is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Série inconnue.")
        if niveau.cycle == "college":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le collège (6e–3e) n'a pas de série.",
            )


def _valider_annee(db: DbSession, annee_id: int, ecole_id: int) -> None:
    annee = db.get(AnneeScolaire, annee_id)
    if annee is None or annee.ecole_id != ecole_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Année scolaire inconnue."
        )


def _vers_out(db: DbSession, classe: Classe) -> ClasseOut:
    effectif = db.scalar(select(func.count()).select_from(Eleve).where(Eleve.classe_id == classe.id))
    return ClasseOut(
        id=classe.id,
        ecole_id=classe.ecole_id,
        nom=classe.nom,
        niveau_id=classe.niveau_id,
        niveau_nom=classe.niveau.nom,
        cycle=classe.niveau.cycle,
        serie_id=classe.serie_id,
        serie_nom=classe.serie.nom if classe.serie else None,
        annee_scolaire_id=classe.annee_scolaire_id,
        annee_libelle=classe.annee_scolaire.libelle,
        effectif=effectif or 0,
    )


@router.get("", response_model=list[ClasseOut])
def lister_classes(
    user: CurrentUser,
    db: DbSession,
    annee_scolaire_id: int | None = None,
    niveau_id: int | None = None,
    serie_id: int | None = None,
):
    stmt = select(Classe).where(Classe.ecole_id == user.ecole_id)
    if annee_scolaire_id is not None:
        stmt = stmt.where(Classe.annee_scolaire_id == annee_scolaire_id)
    if niveau_id is not None:
        stmt = stmt.where(Classe.niveau_id == niveau_id)
    if serie_id is not None:
        stmt = stmt.where(Classe.serie_id == serie_id)
    stmt = stmt.order_by(Classe.nom)
    return [_vers_out(db, c) for c in db.scalars(stmt)]


@router.get("/{classe_id}", response_model=ClasseOut)
def consulter_classe(classe_id: int, user: CurrentUser, db: DbSession):
    classe = db.get(Classe, classe_id)
    if classe is None or classe.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")
    return _vers_out(db, classe)


@router.get("/{classe_id}/eleves", response_model=list[EleveOut])
def lister_eleves_de_la_classe(classe_id: int, user: CurrentUser, db: DbSession):
    classe = db.get(Classe, classe_id)
    if classe is None or classe.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")
    stmt = select(Eleve).where(Eleve.classe_id == classe_id).order_by(Eleve.nom, Eleve.prenom)
    return list(db.scalars(stmt))


@router.get("/{classe_id}/matieres", response_model=list[ClasseMatiereOut])
def lister_matieres_de_la_classe(classe_id: int, user: CurrentUser, db: DbSession):
    """Matières déclarées pour cette classe (via ``coefficients``) + coefficient."""
    classe = db.get(Classe, classe_id)
    if classe is None or classe.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")

    paires = matieres_de_la_classe(
        db, ecole_id=user.ecole_id, niveau_id=classe.niveau_id, serie_id=classe.serie_id
    )
    if not paires:
        return []
    matieres = {m.id: m for m in db.scalars(select(Matiere).where(Matiere.id.in_([p[0] for p in paires])))}
    return [
        ClasseMatiereOut(
            matiere_id=mid,
            nom=matieres[mid].nom,
            note_directe=matieres[mid].note_directe,
            coefficient=float(coef),
        )
        for mid, coef in paires
        if mid in matieres
    ]


@router.post("", response_model=ClasseOut, status_code=status.HTTP_201_CREATED, dependencies=[AdminOnly])
def creer_classe(data: ClasseCreate, user: CurrentUser, db: DbSession):
    annee_id = data.annee_scolaire_id or _annee_active_id(db, user.ecole_id)
    _valider_annee(db, annee_id, user.ecole_id)
    _valider_niveau_serie(db, data.niveau_id, data.serie_id)

    existe = db.scalar(
        select(Classe).where(
            Classe.ecole_id == user.ecole_id,
            Classe.annee_scolaire_id == annee_id,
            Classe.nom == data.nom,
        )
    )
    if existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Une classe « {data.nom} » existe déjà pour cette année scolaire.",
        )

    classe = Classe(
        ecole_id=user.ecole_id,
        annee_scolaire_id=annee_id,
        niveau_id=data.niveau_id,
        serie_id=data.serie_id,
        nom=data.nom,
    )
    db.add(classe)
    db.commit()
    db.refresh(classe)
    return _vers_out(db, classe)


@router.patch("/{classe_id}", response_model=ClasseOut, dependencies=[AdminOnly])
def modifier_classe(classe_id: int, data: ClasseUpdate, user: CurrentUser, db: DbSession):
    classe = db.get(Classe, classe_id)
    if classe is None or classe.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")

    changes = data.model_dump(exclude_unset=True)
    niveau_id = changes.get("niveau_id", classe.niveau_id)
    serie_id = changes.get("serie_id", classe.serie_id)
    _valider_niveau_serie(db, niveau_id, serie_id)

    if "annee_scolaire_id" in changes:
        _valider_annee(db, changes["annee_scolaire_id"], user.ecole_id)

    nouveau_nom = changes.get("nom", classe.nom)
    nouvelle_annee = changes.get("annee_scolaire_id", classe.annee_scolaire_id)
    if (nouveau_nom, nouvelle_annee) != (classe.nom, classe.annee_scolaire_id):
        conflit = db.scalar(
            select(Classe).where(
                Classe.ecole_id == user.ecole_id,
                Classe.annee_scolaire_id == nouvelle_annee,
                Classe.nom == nouveau_nom,
                Classe.id != classe.id,
            )
        )
        if conflit is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Une classe « {nouveau_nom} » existe déjà pour cette année scolaire.",
            )

    for field, value in changes.items():
        setattr(classe, field, value)
    db.commit()
    db.refresh(classe)
    return _vers_out(db, classe)


@router.delete("/{classe_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[AdminOnly])
def supprimer_classe(classe_id: int, user: CurrentUser, db: DbSession):
    classe = db.get(Classe, classe_id)
    if classe is None or classe.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")

    effectif = db.scalar(select(func.count()).select_from(Eleve).where(Eleve.classe_id == classe_id))
    if effectif:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossible de supprimer : {effectif} élève(s) sont encore dans cette classe.",
        )
    db.delete(classe)
    db.commit()
