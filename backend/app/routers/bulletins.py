"""Bulletins : moyennes, rang et décision, calculés à la volée."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.calcul import arrondi_affichage, format_note
from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import AnneeScolaire, Classe, Ecole, Eleve, Trimestre
from app.schemas import (
    BulletinClasse,
    BulletinClasseLigne,
    BulletinEleve,
    BulletinLigne,
    ProgressionEleve,
    ProgressionPoint,
)
from app.services.bulletins import (
    BulletinClasseCalc,
    BulletinEleveCalc,
    construire_bulletins_classe,
    progression_eleve,
)

# Génération des bulletins : directeur et censeur.
router = APIRouter(tags=["bulletins"], dependencies=[Depends(require_roles("admin"))])


def _f(x: Decimal | None) -> float | None:
    return float(arrondi_affichage(x)) if x is not None else None


def _aff(x: Decimal | None) -> str | None:
    return format_note(x) if x is not None else None


def _classe_de_lecole(db: Session, classe_id: int, ecole_id: int) -> Classe:
    c = db.get(Classe, classe_id)
    if c is None or c.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")
    return c


def _trimestre_de_lecole(db: Session, trimestre_id: int, ecole_id: int) -> Trimestre:
    tri = db.get(Trimestre, trimestre_id)
    annee = db.get(AnneeScolaire, tri.annee_scolaire_id) if tri else None
    if tri is None or annee is None or annee.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trimestre introuvable.")
    return tri


def _verifier_coherence(classe: Classe, trimestre: Trimestre) -> None:
    if trimestre.annee_scolaire_id != classe.annee_scolaire_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ce trimestre n'appartient pas à l'année scolaire de la classe.",
        )


def _lignes_out(bulletin: BulletinClasseCalc, calc: BulletinEleveCalc) -> list[BulletinLigne]:
    lignes: list[BulletinLigne] = []
    for mid, coef in bulletin.coefficients.items():
        lc = calc.lignes[mid]
        r = lc.resultat
        moy = r.moyenne
        if moy is not None:
            statut = "directe" if bulletin.matieres[mid].note_directe else "calculee"
        else:
            statut = "incomplete" if r.incomplete else "sans_note"
        lignes.append(
            BulletinLigne(
                matiere_id=mid,
                matiere_nom=bulletin.matieres[mid].nom,
                coefficient=float(coef),
                note_directe=bulletin.matieres[mid].note_directe,
                moyenne=_f(moy),
                moyenne_affichee=_aff(moy),
                moyenne_coefficientee=_f(moy * coef) if moy is not None else None,
                rang=calc.rang_par_matiere.get(mid),
                statut=statut,
                appreciation=lc.appreciation,
            )
        )
    return lignes


def _bulletin_eleve_out(
    bulletin: BulletinClasseCalc, calc: BulletinEleveCalc, mode_annuel: str
) -> BulletinEleve:
    return BulletinEleve(
        eleve_id=calc.eleve.id,
        matricule=calc.eleve.matricule,
        nom=calc.eleve.nom,
        prenom=calc.eleve.prenom,
        classe_id=bulletin.classe.id,
        classe_nom=bulletin.classe.nom,
        trimestre_id=bulletin.trimestre.id,
        trimestre_numero=bulletin.trimestre.numero,
        lignes=_lignes_out(bulletin, calc),
        moyenne_generale=_f(calc.moyenne_generale),
        moyenne_generale_affichee=_aff(calc.moyenne_generale),
        rang=calc.rang,
        effectif_classe=bulletin.effectif,
        mode_calcul_annuel=mode_annuel,
        moyenne_annuelle=_f(calc.moyenne_annuelle),
        moyenne_annuelle_affichee=_aff(calc.moyenne_annuelle),
        decision=calc.decision.value if calc.decision is not None else None,
    )


@router.get("/classes/{classe_id}/bulletins", response_model=BulletinClasse)
def bulletins_de_la_classe(
    classe_id: int,
    user: CurrentUser,
    db: DbSession,
    trimestre_id: Annotated[int, Query()],
):
    classe = _classe_de_lecole(db, classe_id, user.ecole_id)
    trimestre = _trimestre_de_lecole(db, trimestre_id, user.ecole_id)
    _verifier_coherence(classe, trimestre)
    ecole = db.get(Ecole, user.ecole_id)
    bulletin = construire_bulletins_classe(
        db, classe=classe, trimestre=trimestre, mode_annuel=ecole.mode_calcul_moyenne_annuelle
    )
    return BulletinClasse(
        classe_id=classe.id,
        classe_nom=classe.nom,
        trimestre_id=trimestre.id,
        trimestre_numero=trimestre.numero,
        effectif_classe=bulletin.effectif,
        eleves=[
            BulletinClasseLigne(
                eleve_id=c.eleve.id,
                matricule=c.eleve.matricule,
                nom=c.eleve.nom,
                prenom=c.eleve.prenom,
                moyenne_generale=_f(c.moyenne_generale),
                moyenne_generale_affichee=_aff(c.moyenne_generale),
                rang=c.rang,
                moyenne_annuelle=_f(c.moyenne_annuelle),
                decision=c.decision.value if c.decision is not None else None,
            )
            for c in bulletin.eleves
        ],
    )


@router.get("/eleves/{eleve_id}/bulletin", response_model=BulletinEleve)
def bulletin_d_un_eleve(
    eleve_id: int,
    user: CurrentUser,
    db: DbSession,
    trimestre_id: Annotated[int, Query()],
):
    eleve = db.get(Eleve, eleve_id)
    if eleve is None or eleve.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    if eleve.classe_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cet élève n'est rattaché à aucune classe.",
        )
    classe = _classe_de_lecole(db, eleve.classe_id, user.ecole_id)
    trimestre = _trimestre_de_lecole(db, trimestre_id, user.ecole_id)
    _verifier_coherence(classe, trimestre)
    ecole = db.get(Ecole, user.ecole_id)
    bulletin = construire_bulletins_classe(
        db, classe=classe, trimestre=trimestre, mode_annuel=ecole.mode_calcul_moyenne_annuelle
    )
    calc = next((c for c in bulletin.eleves if c.eleve.id == eleve_id), None)
    if calc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bulletin indisponible (élève archivé ?)."
        )
    return _bulletin_eleve_out(bulletin, calc, ecole.mode_calcul_moyenne_annuelle)


@router.get("/eleves/{eleve_id}/progression", response_model=ProgressionEleve)
def progression_d_un_eleve(eleve_id: int, user: CurrentUser, db: DbSession):
    """Courbe de progression : moyenne générale par trimestre."""
    eleve = db.get(Eleve, eleve_id)
    if eleve is None or eleve.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    if eleve.classe_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cet élève n'est rattaché à aucune classe.",
        )
    classe = _classe_de_lecole(db, eleve.classe_id, user.ecole_id)

    points = [
        ProgressionPoint(
            trimestre_id=t.id,
            trimestre_numero=t.numero,
            moyenne_generale=_f(m),
            moyenne_generale_affichee=_aff(m),
        )
        for t, m in progression_eleve(db, eleve=eleve)
    ]
    return ProgressionEleve(
        eleve_id=eleve.id, classe_id=classe.id, classe_nom=classe.nom, points=points
    )
