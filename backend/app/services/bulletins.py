"""Construction des bulletins (à la volée, aucune table dédiée — cf décision 5).

Assemble, pour une classe et un trimestre :
- la moyenne de chaque matière (via app.calcul) et son rang dans la classe ;
- la moyenne générale du trimestre et le rang général ;
- si les 3 trimestres sont complets : la moyenne annuelle et la décision.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calcul import (
    Decision,
    ModeCalculAnnuel,
    ResultatMatiere,
    calculer_rangs,
    decision_annuelle,
    effectif_classe,
    evaluer_matiere,
    evaluer_note_directe,
    moyenne_annuelle,
    moyenne_generale,
)
from app.models import Classe, Eleve, Matiere, Note, Trimestre
from app.services.coefficients import matieres_de_la_classe

STATUTS_ELEVE_INCLUS = ("actif", "redoublant")


@dataclass
class _LigneCalc:
    resultat: ResultatMatiere
    appreciation: str | None = None


@dataclass
class BulletinEleveCalc:
    eleve: Eleve
    lignes: dict[int, _LigneCalc]                 # matiere_id -> ligne
    moyenne_generale: Decimal | None
    rang: int | None
    rang_par_matiere: dict[int, int | None] = field(default_factory=dict)
    moyenne_annuelle: Decimal | None = None
    decision: Decision | None = None


@dataclass
class BulletinClasseCalc:
    classe: Classe
    trimestre: Trimestre
    matieres: dict[int, Matiere]
    coefficients: dict[int, Decimal]              # matiere_id -> coefficient
    eleves: list[BulletinEleveCalc]
    effectif: int


def _resultats_du_trimestre(
    db: Session,
    *,
    eleve_ids: list[int],
    paires: list[tuple[int, Decimal]],
    matieres: dict[int, Matiere],
    trimestre_id: int,
) -> dict[int, list[_LigneCalc]]:
    matiere_ids = [mid for mid, _ in paires]
    notes = {
        (n.eleve_id, n.matiere_id): n
        for n in db.scalars(
            select(Note).where(
                Note.trimestre_id == trimestre_id,
                Note.eleve_id.in_(eleve_ids or [-1]),
                Note.matiere_id.in_(matiere_ids or [-1]),
            )
        )
    }
    par_eleve: dict[int, list[_LigneCalc]] = {}
    for eid in eleve_ids:
        lignes: list[_LigneCalc] = []
        for mid, coef in paires:
            m = matieres[mid]
            n = notes.get((eid, mid))
            if m.note_directe:
                r = evaluer_note_directe(mid, coef, n.note_directe if n else None)
            elif n is None:
                r = evaluer_matiere(mid, coef, None, None, None, None, None)
            else:
                r = evaluer_matiere(mid, coef, n.interro1, n.interro2, n.interro3, n.devoir1, n.devoir2)
            lignes.append(_LigneCalc(resultat=r, appreciation=(n.appreciation if n else None)))
        par_eleve[eid] = lignes
    return par_eleve


def _moyennes_generales(par_eleve: dict[int, list[_LigneCalc]]) -> dict[int, Decimal | None]:
    return {
        eid: moyenne_generale([lc.resultat for lc in lignes])
        for eid, lignes in par_eleve.items()
    }


def construire_bulletins_classe(
    db: Session, *, classe: Classe, trimestre: Trimestre, mode_annuel: str
) -> BulletinClasseCalc:
    paires = matieres_de_la_classe(
        db, ecole_id=classe.ecole_id, niveau_id=classe.niveau_id, serie_id=classe.serie_id
    )
    coefficients = {mid: coef for mid, coef in paires}
    matieres = {
        m.id: m
        for m in db.scalars(select(Matiere).where(Matiere.id.in_(list(coefficients) or [-1])))
    }
    eleves = list(
        db.scalars(
            select(Eleve)
            .where(Eleve.classe_id == classe.id, Eleve.statut.in_(STATUTS_ELEVE_INCLUS))
            .order_by(Eleve.nom, Eleve.prenom)
        )
    )
    eleve_ids = [e.id for e in eleves]

    par_eleve = _resultats_du_trimestre(
        db, eleve_ids=eleve_ids, paires=paires, matieres=matieres, trimestre_id=trimestre.id
    )
    moy_gen = _moyennes_generales(par_eleve)
    rangs_gen = calculer_rangs(moy_gen)
    effectif = effectif_classe(moy_gen)

    rang_par_matiere: dict[int, dict[int, int | None]] = {}
    for mid in coefficients:
        valeurs = {
            eid: next(lc.resultat.moyenne for lc in lignes if lc.resultat.matiere_id == mid)
            for eid, lignes in par_eleve.items()
        }
        rang_par_matiere[mid] = calculer_rangs(valeurs)

    # Moyenne annuelle : seulement si les 3 trimestres ont une moyenne générale.
    trimestres = list(
        db.scalars(
            select(Trimestre)
            .where(Trimestre.annee_scolaire_id == classe.annee_scolaire_id)
            .order_by(Trimestre.numero)
        )
    )
    moy_gen_par_trimestre: dict[int, dict[int, Decimal | None]] = {}
    for t in trimestres:
        if t.id == trimestre.id:
            moy_gen_par_trimestre[t.numero] = moy_gen
        else:
            pe = _resultats_du_trimestre(
                db, eleve_ids=eleve_ids, paires=paires, matieres=matieres, trimestre_id=t.id
            )
            moy_gen_par_trimestre[t.numero] = _moyennes_generales(pe)

    bulletins: list[BulletinEleveCalc] = []
    for e in eleves:
        annuelle = None
        decision = None
        if {1, 2, 3} <= set(moy_gen_par_trimestre):
            t1 = moy_gen_par_trimestre[1].get(e.id)
            t2 = moy_gen_par_trimestre[2].get(e.id)
            t3 = moy_gen_par_trimestre[3].get(e.id)
            annuelle = moyenne_annuelle(t1, t2, t3, mode_annuel)
            decision = decision_annuelle(annuelle)

        bulletins.append(
            BulletinEleveCalc(
                eleve=e,
                lignes={lc.resultat.matiere_id: lc for lc in par_eleve[e.id]},
                moyenne_generale=moy_gen[e.id],
                rang=rangs_gen[e.id],
                rang_par_matiere={mid: rang_par_matiere[mid][e.id] for mid in coefficients},
                moyenne_annuelle=annuelle,
                decision=decision,
            )
        )

    return BulletinClasseCalc(
        classe=classe,
        trimestre=trimestre,
        matieres=matieres,
        coefficients=coefficients,
        eleves=bulletins,
        effectif=effectif,
    )
