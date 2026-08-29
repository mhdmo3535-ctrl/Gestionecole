"""Résolveur de coefficient.

Donne le coefficient d'une matière pour une classe donnée (son niveau et,
au lycée, sa série). Cherche d'abord une ligne explicite dans
``coefficients``, puis se rabat sur ``coefficients_defaut``. À chaque
étape, la ligne la plus spécifique gagne (niveau + série > série seule >
niveau seul > sans critère).
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Coefficient, CoefficientDefaut


class CoefficientIntrouvable(Exception):
    """Aucun coefficient ni valeur par défaut pour cette matière / ce niveau."""

    def __init__(self, matiere_id: int):
        super().__init__(f"Aucun coefficient défini pour la matière {matiere_id}.")
        self.matiere_id = matiere_id


def _meilleure(rows, niveau_id: int | None, serie_id: int | None):
    meilleure = None
    meilleur_score = -1
    for r in rows:
        if r.niveau_id is not None and r.niveau_id != niveau_id:
            continue
        if r.serie_id is not None and r.serie_id != serie_id:
            continue
        score = (2 if r.niveau_id == niveau_id else 0) + (2 if r.serie_id == serie_id else 0)
        if score > meilleur_score:
            meilleure, meilleur_score = r, score
    return meilleure


def resoudre_coefficient(
    db: Session,
    *,
    ecole_id: int,
    matiere_id: int,
    niveau_id: int,
    serie_id: int | None,
) -> Decimal:
    explicites = db.scalars(
        select(Coefficient).where(
            Coefficient.ecole_id == ecole_id, Coefficient.matiere_id == matiere_id
        )
    ).all()
    trouve = _meilleure(explicites, niveau_id, serie_id)
    if trouve is not None:
        return trouve.coefficient

    defauts = db.scalars(
        select(CoefficientDefaut).where(CoefficientDefaut.ecole_id == ecole_id)
    ).all()
    trouve = _meilleure(defauts, niveau_id, serie_id)
    if trouve is not None:
        return trouve.coefficient

    raise CoefficientIntrouvable(matiere_id)


def matieres_de_la_classe(db: Session, *, ecole_id: int, niveau_id: int, serie_id: int | None):
    """Matières explicitement déclarées pour ce niveau / cette série.

    Renvoie une liste de tuples (matiere_id, coefficient), triée par
    matiere_id. « Déclarée » = il existe une ligne dans ``coefficients``
    qui correspond (la valeur par défaut ne suffit pas à faire exister
    une matière dans une classe).
    """
    rows = db.scalars(select(Coefficient).where(Coefficient.ecole_id == ecole_id)).all()
    par_matiere: dict[int, object] = {}
    for r in rows:
        if r.niveau_id is not None and r.niveau_id != niveau_id:
            continue
        if r.serie_id is not None and r.serie_id != serie_id:
            continue
        score = (2 if r.niveau_id == niveau_id else 0) + (2 if r.serie_id == serie_id else 0)
        ancienne = par_matiere.get(r.matiere_id)
        if ancienne is None or score > ancienne[0]:
            par_matiere[r.matiere_id] = (score, r.coefficient)
    return sorted((mid, coef) for mid, (_, coef) in par_matiere.items())
