"""Comptes utilisateurs (admins, enseignants) et affectations des enseignants.

Périmètre : profils Administration et Enseignants. Les comptes parents /
élèves ont un cycle de vie distinct (créés depuis la fiche élève, connexion
mobile) et ne passent pas par ces routes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.security import hash_password
from app.models import Classe, EnseignantAffectation, Matiere, Utilisateur
from app.schemas import (
    AffectationCreate,
    AffectationOut,
    MotDePasseUpdate,
    UtilisateurCreate,
    UtilisateurOut,
    UtilisateurUpdate,
)

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])

AdminOnly = Depends(require_roles("admin"))


def _get_de_mon_ecole(db: DbSession, user_id: int, ecole_id: int) -> Utilisateur:
    u = db.get(Utilisateur, user_id)
    if u is None or u.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    return u


@router.get("", response_model=list[UtilisateurOut], dependencies=[AdminOnly])
def lister_utilisateurs(
    user: CurrentUser,
    db: DbSession,
    role: Annotated[str | None, Query(pattern="^(admin|enseignant)$")] = None,
    actif: bool | None = None,
):
    stmt = select(Utilisateur).where(Utilisateur.ecole_id == user.ecole_id)
    if role is not None:
        stmt = stmt.where(Utilisateur.role == role)
    if actif is not None:
        stmt = stmt.where(Utilisateur.actif.is_(actif))
    stmt = stmt.order_by(Utilisateur.nom, Utilisateur.prenom)
    return list(db.scalars(stmt))


@router.post("", response_model=UtilisateurOut, status_code=status.HTTP_201_CREATED, dependencies=[AdminOnly])
def creer_utilisateur(data: UtilisateurCreate, user: CurrentUser, db: DbSession):
    email = data.email.strip().lower()
    if db.scalar(select(Utilisateur).where(Utilisateur.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'email {email} est déjà utilisé.",
        )
    nouvel = Utilisateur(
        ecole_id=user.ecole_id,
        nom=data.nom,
        prenom=data.prenom,
        email=email,
        mot_de_passe_hash=hash_password(data.mot_de_passe),
        role=data.role,
        telephone=data.telephone,
    )
    db.add(nouvel)
    db.commit()
    db.refresh(nouvel)
    return nouvel


@router.get("/{user_id}", response_model=UtilisateurOut, dependencies=[AdminOnly])
def consulter_utilisateur(user_id: int, user: CurrentUser, db: DbSession):
    return _get_de_mon_ecole(db, user_id, user.ecole_id)


@router.patch("/{user_id}", response_model=UtilisateurOut, dependencies=[AdminOnly])
def modifier_utilisateur(user_id: int, data: UtilisateurUpdate, user: CurrentUser, db: DbSession):
    cible = _get_de_mon_ecole(db, user_id, user.ecole_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("actif") is False and cible.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vous ne pouvez pas désactiver votre propre compte.",
        )
    for field, value in changes.items():
        setattr(cible, field, value)
    db.commit()
    db.refresh(cible)
    return cible


@router.put("/{user_id}/mot-de-passe", status_code=status.HTTP_204_NO_CONTENT, dependencies=[AdminOnly])
def reinitialiser_mot_de_passe(user_id: int, data: MotDePasseUpdate, user: CurrentUser, db: DbSession):
    cible = _get_de_mon_ecole(db, user_id, user.ecole_id)
    cible.mot_de_passe_hash = hash_password(data.nouveau_mot_de_passe)
    db.commit()


# ---------------------------------------------------------------------
# Affectations : quelles classes / matières un enseignant peut saisir
# ---------------------------------------------------------------------

def _vers_affectation_out(aff: EnseignantAffectation) -> AffectationOut:
    return AffectationOut(
        id=aff.id,
        enseignant_id=aff.enseignant_id,
        classe_id=aff.classe_id,
        classe_nom=aff.classe.nom,
        matiere_id=aff.matiere_id,
        matiere_nom=aff.matiere.nom,
    )


@router.get("/{user_id}/affectations", response_model=list[AffectationOut])
def lister_affectations(user_id: int, user: CurrentUser, db: DbSession):
    # un enseignant peut voir les siennes ; sinon réservé à l'admin
    if user.role != "admin" and user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    enseignant = _get_de_mon_ecole(db, user_id, user.ecole_id)
    stmt = select(EnseignantAffectation).where(
        EnseignantAffectation.enseignant_id == enseignant.id
    )
    return [_vers_affectation_out(a) for a in db.scalars(stmt)]


@router.post(
    "/{user_id}/affectations",
    response_model=AffectationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[AdminOnly],
)
def ajouter_affectation(user_id: int, data: AffectationCreate, user: CurrentUser, db: DbSession):
    enseignant = _get_de_mon_ecole(db, user_id, user.ecole_id)
    if enseignant.role != "enseignant":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Seul un compte de rôle « enseignant » peut recevoir une affectation.",
        )

    classe = db.get(Classe, data.classe_id)
    if classe is None or classe.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Classe inconnue.")
    matiere = db.get(Matiere, data.matiere_id)
    if matiere is None or matiere.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Matière inconnue.")

    existe = db.scalar(
        select(EnseignantAffectation).where(
            EnseignantAffectation.enseignant_id == enseignant.id,
            EnseignantAffectation.classe_id == data.classe_id,
            EnseignantAffectation.matiere_id == data.matiere_id,
        )
    )
    if existe is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet enseignant est déjà affecté à cette classe pour cette matière.",
        )

    aff = EnseignantAffectation(
        enseignant_id=enseignant.id, classe_id=data.classe_id, matiere_id=data.matiere_id
    )
    db.add(aff)
    db.commit()
    db.refresh(aff)
    return _vers_affectation_out(aff)


@router.delete(
    "/{user_id}/affectations/{affectation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[AdminOnly],
)
def retirer_affectation(user_id: int, affectation_id: int, user: CurrentUser, db: DbSession):
    enseignant = _get_de_mon_ecole(db, user_id, user.ecole_id)
    aff = db.get(EnseignantAffectation, affectation_id)
    if aff is None or aff.enseignant_id != enseignant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affectation introuvable.")
    db.delete(aff)
    db.commit()
