"""Emploi du temps.

Établi par le censeur (domaine « pédagogie », écriture). Un créneau place un
professeur dans une classe pour une matière, un jour (lundi à samedi) et un
horaire libre (ex. 7h30-9h30).

Règles :
- le professeur doit être affecté à cette classe pour cette matière (ou
  l'affectation est créée avec le cours si « creer_affectation » est demandé) ;
- les matières « note directe » (conduite) ne sont pas des cours ;
- une classe ne peut pas avoir deux cours en même temps, ni un professeur
  être dans deux classes en même temps (chevauchement refusé, 409).

Consultation : quiconque voit la pédagogie ; un enseignant voit son propre
emploi du temps.
"""

import datetime as _dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ecriture, lecture
from app.core.permissions import Domaine, peut
from app.models import Classe, Creneau, EnseignantAffectation, Matiere, Utilisateur
from app.schemas import AffectationClasseOut, CreneauEcrire, CreneauModifier, CreneauOut

router = APIRouter(tags=["emploi du temps"])

GererPedagogie = ecriture(Domaine.PEDAGOGIE)
LirePedagogie = lecture(Domaine.PEDAGOGIE)

JOURS = {1: "lundi", 2: "mardi", 3: "mercredi", 4: "jeudi", 5: "vendredi", 6: "samedi"}


def _hm(t: _dt.time) -> str:
    return f"{t.hour}h{t.minute:02d}" if t.minute else f"{t.hour}h"


def _minutes(debut: _dt.time, fin: _dt.time) -> int:
    return (fin.hour * 60 + fin.minute) - (debut.hour * 60 + debut.minute)


def _vers_out(c: Creneau) -> CreneauOut:
    return CreneauOut(
        id=c.id,
        classe_id=c.classe_id,
        classe_nom=c.classe.nom,
        matiere_id=c.matiere_id,
        matiere_nom=c.matiere.nom,
        enseignant_id=c.enseignant_id,
        enseignant_nom=f"{c.enseignant.prenom} {c.enseignant.nom}",
        jour=c.jour,
        heure_debut=c.heure_debut,
        heure_fin=c.heure_fin,
        duree_minutes=_minutes(c.heure_debut, c.heure_fin),
    )


def _classe(db: Session, classe_id: int, ecole_id: int) -> Classe:
    c = db.get(Classe, classe_id)
    if c is None or c.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")
    return c


def _verifier(db: Session, ecole_id: int, classe_id: int, matiere_id: int, enseignant_id: int,
              jour: int, debut: _dt.time, fin: _dt.time, ignorer_id: int | None = None,
              creer_affectation: bool = False) -> None:
    if fin <= debut:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L'heure de fin doit être après l'heure de début.",
        )
    matiere = db.get(Matiere, matiere_id)
    if matiere is None or matiere.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Matière inconnue.")
    if matiere.note_directe:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"« {matiere.nom} » est une note, pas un cours : elle ne figure pas à l'emploi du temps.",
        )
    prof = db.get(Utilisateur, enseignant_id)
    if prof is None or prof.ecole_id != ecole_id or not prof.est_enseignant or not prof.actif:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Professeur inconnu.")
    affecte = db.scalar(
        select(EnseignantAffectation.id).where(
            EnseignantAffectation.enseignant_id == enseignant_id,
            EnseignantAffectation.classe_id == classe_id,
            EnseignantAffectation.matiere_id == matiere_id,
        )
    )
    if affecte is None and not creer_affectation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{prof.prenom} {prof.nom} n'est pas affecté(e) à cette classe pour « {matiere.nom} ».",
        )

    # chevauchement : même jour, [debut, fin) qui se croisent, même classe ou même professeur
    stmt = select(Creneau).where(
        Creneau.ecole_id == ecole_id,
        Creneau.jour == jour,
        Creneau.heure_debut < fin,
        Creneau.heure_fin > debut,
        (Creneau.classe_id == classe_id) | (Creneau.enseignant_id == enseignant_id),
    )
    if ignorer_id is not None:
        stmt = stmt.where(Creneau.id != ignorer_id)
    for c in db.scalars(stmt):
        horaire = f"le {JOURS[c.jour]} de {_hm(c.heure_debut)} à {_hm(c.heure_fin)}"
        if c.classe_id == classe_id:
            detail = f"La classe {c.classe.nom} a déjà {c.matiere.nom} {horaire}."
        else:
            detail = (f"{c.enseignant.prenom} {c.enseignant.nom} a déjà cours en {c.classe.nom} "
                      f"({c.matiere.nom}) {horaire}.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    # aucun conflit : on crée l'affectation demandée avec le cours
    if affecte is None:
        db.add(EnseignantAffectation(enseignant_id=enseignant_id, classe_id=classe_id, matiere_id=matiere_id))


@router.get("/emploi-du-temps", response_model=list[CreneauOut])
def lire_emploi_du_temps(
    user: CurrentUser,
    db: DbSession,
    classe_id: int | None = None,
    enseignant_id: int | None = None,
):
    if classe_id is None and enseignant_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Précisez une classe ou un professeur.",
        )
    son_propre = enseignant_id is not None and enseignant_id == user.id and classe_id is None
    if not (peut(user.roles, Domaine.PEDAGOGIE) or son_propre):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")

    stmt = select(Creneau).where(Creneau.ecole_id == user.ecole_id)
    if classe_id is not None:
        _classe(db, classe_id, user.ecole_id)
        stmt = stmt.where(Creneau.classe_id == classe_id)
    if enseignant_id is not None:
        stmt = stmt.where(Creneau.enseignant_id == enseignant_id)
    stmt = stmt.order_by(Creneau.jour, Creneau.heure_debut)
    return [_vers_out(c) for c in db.scalars(stmt)]


@router.post("/emploi-du-temps", response_model=CreneauOut, status_code=status.HTTP_201_CREATED,
             dependencies=[GererPedagogie])
def ajouter_creneau(data: CreneauEcrire, user: CurrentUser, db: DbSession):
    _classe(db, data.classe_id, user.ecole_id)
    _verifier(db, user.ecole_id, data.classe_id, data.matiere_id, data.enseignant_id,
              data.jour, data.heure_debut, data.heure_fin, creer_affectation=data.creer_affectation)
    c = Creneau(ecole_id=user.ecole_id, **data.model_dump(exclude={"creer_affectation"}))
    db.add(c)
    db.commit()
    db.refresh(c)
    return _vers_out(c)


@router.patch("/emploi-du-temps/{creneau_id}", response_model=CreneauOut, dependencies=[GererPedagogie])
def modifier_creneau(creneau_id: int, data: CreneauModifier, user: CurrentUser, db: DbSession):
    c = db.get(Creneau, creneau_id)
    if c is None or c.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")
    v = {**{k: getattr(c, k) for k in ("matiere_id", "enseignant_id", "jour", "heure_debut", "heure_fin")},
         **data.model_dump(exclude_unset=True, exclude_none=True, exclude={"creer_affectation"})}
    _verifier(db, user.ecole_id, c.classe_id, v["matiere_id"], v["enseignant_id"],
              v["jour"], v["heure_debut"], v["heure_fin"], ignorer_id=c.id,
              creer_affectation=data.creer_affectation)
    for k, val in v.items():
        setattr(c, k, val)
    db.commit()
    db.refresh(c)
    return _vers_out(c)


@router.delete("/emploi-du-temps/{creneau_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[GererPedagogie])
def supprimer_creneau(creneau_id: int, user: CurrentUser, db: DbSession):
    c = db.get(Creneau, creneau_id)
    if c is None or c.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cours introuvable.")
    db.delete(c)
    db.commit()


@router.get("/classes/{classe_id}/affectations", response_model=list[AffectationClasseOut],
            dependencies=[LirePedagogie])
def affectations_de_la_classe(classe_id: int, user: CurrentUser, db: DbSession):
    """Professeurs affectés à la classe, par matière (hors matières « note directe »)."""
    _classe(db, classe_id, user.ecole_id)
    stmt = (
        select(EnseignantAffectation, Utilisateur)
        .join(Utilisateur, Utilisateur.id == EnseignantAffectation.enseignant_id)
        .where(EnseignantAffectation.classe_id == classe_id, Utilisateur.actif.is_(True))
    )
    lignes = [
        AffectationClasseOut(
            enseignant_id=u.id,
            enseignant_nom=f"{u.prenom} {u.nom}",
            matiere_id=a.matiere_id,
            matiere_nom=a.matiere.nom,
        )
        for a, u in db.execute(stmt)
        if not a.matiere.note_directe
    ]
    return sorted(lignes, key=lambda l: (l.matiere_nom, l.enseignant_nom))
