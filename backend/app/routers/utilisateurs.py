"""Comptes du personnel (administration, enseignants) et affectations des enseignants.

Chaque compte porte un ou plusieurs rôles (cumul possible).
Seul le directeur crée les comptes et attribue les
rôles ; l'école garde toujours au moins un directeur actif.

Les comptes parents / élèves ont un cycle de vie distinct (créés depuis la
fiche élève, connexion mobile) et ne passent pas par ces routes.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, ecriture
from app.core.permissions import Domaine, peut
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

GererPersonnel = ecriture(Domaine.PERSONNEL)
GererPedagogie = ecriture(Domaine.PEDAGOGIE)


def _get_de_mon_ecole(db: DbSession, user_id: int, ecole_id: int) -> Utilisateur:
    u = db.get(Utilisateur, user_id)
    if u is None or u.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    return u


def _roles_normalises(roles: list[str]) -> list[str]:
    return sorted(set(roles))


def _verifier_un_directeur_reste(db: DbSession, cible: Utilisateur, roles: list[str], actif: bool) -> None:
    """Refuse un changement qui laisserait l'école sans aucun directeur actif."""
    if "directeur" in roles and actif:
        return
    autres = db.scalar(
        select(Utilisateur.id).where(
            Utilisateur.ecole_id == cible.ecole_id,
            Utilisateur.id != cible.id,
            Utilisateur.actif.is_(True),
            Utilisateur.roles.any("directeur"),
        ).limit(1)
    )
    if cible.a_le_role("directeur") and cible.actif and autres is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L'école doit garder au moins un directeur actif.",
        )


def _voit_tout_le_personnel(user: Utilisateur) -> bool:
    return peut(user.roles, Domaine.PERSONNEL)


def _verifier_lecture(user: Utilisateur) -> None:
    """Le personnel complet : directeur. Les enseignants seuls : qui voit la pédagogie."""
    if not (_voit_tout_le_personnel(user) or peut(user.roles, Domaine.PEDAGOGIE)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")


@router.get("", response_model=list[UtilisateurOut])
def lister_utilisateurs(
    user: CurrentUser,
    db: DbSession,
    role: Annotated[
        str | None,
        Query(pattern="^(directeur|censeur|surveillant|comptable|secretaire|enseignant)$"),
    ] = None,
    actif: bool | None = None,
):
    _verifier_lecture(user)
    stmt = select(Utilisateur).where(Utilisateur.ecole_id == user.ecole_id)
    if not _voit_tout_le_personnel(user):
        # censeur, surveillant, secrétaire : uniquement les enseignants
        stmt = stmt.where(Utilisateur.roles.any("enseignant"))
    if role is not None:
        stmt = stmt.where(Utilisateur.roles.any(role))
    if actif is not None:
        stmt = stmt.where(Utilisateur.actif.is_(actif))
    stmt = stmt.order_by(Utilisateur.nom, Utilisateur.prenom)
    return list(db.scalars(stmt))


@router.post("", response_model=UtilisateurOut, status_code=status.HTTP_201_CREATED, dependencies=[GererPersonnel])
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
        roles=_roles_normalises(data.roles),
        telephone=data.telephone,
    )
    db.add(nouvel)
    db.commit()
    db.refresh(nouvel)
    return nouvel


@router.get("/{user_id}", response_model=UtilisateurOut)
def consulter_utilisateur(user_id: int, user: CurrentUser, db: DbSession):
    _verifier_lecture(user)
    cible = _get_de_mon_ecole(db, user_id, user.ecole_id)
    if not _voit_tout_le_personnel(user) and not cible.est_enseignant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    return cible


@router.patch("/{user_id}", response_model=UtilisateurOut, dependencies=[GererPersonnel])
def modifier_utilisateur(user_id: int, data: UtilisateurUpdate, user: CurrentUser, db: DbSession):
    cible = _get_de_mon_ecole(db, user_id, user.ecole_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("actif") is False and cible.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vous ne pouvez pas désactiver votre propre compte.",
        )
    if "roles" in changes:
        if changes["roles"] is None:
            del changes["roles"]
        else:
            changes["roles"] = _roles_normalises(changes["roles"])
    _verifier_un_directeur_reste(
        db, cible, changes.get("roles", cible.roles), changes.get("actif", cible.actif)
    )
    for field, value in changes.items():
        setattr(cible, field, value)
    db.commit()
    db.refresh(cible)
    return cible


@router.put("/{user_id}/mot-de-passe", status_code=status.HTTP_204_NO_CONTENT, dependencies=[GererPersonnel])
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
    # un enseignant peut voir les siennes ; sinon réservé à qui voit la pédagogie
    if user.id != user_id and not peut(user.roles, Domaine.PEDAGOGIE):
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
    dependencies=[GererPedagogie],
)
def ajouter_affectation(user_id: int, data: AffectationCreate, user: CurrentUser, db: DbSession):
    enseignant = _get_de_mon_ecole(db, user_id, user.ecole_id)
    if not enseignant.est_enseignant:
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
    dependencies=[GererPedagogie],
)
def retirer_affectation(user_id: int, affectation_id: int, user: CurrentUser, db: DbSession):
    enseignant = _get_de_mon_ecole(db, user_id, user.ecole_id)
    aff = db.get(EnseignantAffectation, affectation_id)
    if aff is None or aff.enseignant_id != enseignant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affectation introuvable.")
    db.delete(aff)
    db.commit()
