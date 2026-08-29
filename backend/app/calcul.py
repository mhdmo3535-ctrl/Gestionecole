"""Calcul des moyennes, du rang et de la décision de fin d'année.

C'est la SEULE implémentation de ces règles dans tout le projet.
Fonctions pures, sans accès base : elles
prennent des nombres, elles rendent des nombres. Tout est en ``Decimal``
pour éviter les erreurs de virgule flottante.

Règles (validées avec le porteur du projet le 2026-08-28) :

* Moyenne interro   = (I1 + I2 + I3) / 3
* Moyenne matière   = (Moyenne interro + Devoir1 + Devoir2) / 3
                      -> les 3 interros pèsent ensemble autant qu'UN devoir
* Moyenne coeff.    = Moyenne matière x coefficient
* Moyenne générale  = somme(moyennes coeff.) / somme(coefficients)
                      -> une matière "note directe" (ex : Conduite) y entre
                         exactement comme les autres : sa note x son coefficient.
                         La formule ne change pas, c'est juste un terme de plus
                         dans la somme pondérée (aucun résultat faussé).
* Moyenne annuelle  = (T1 + T2 + T3) / 3            [mode "poids_egal"]
                      (T1 + T2 + 2*T3) / 4          [mode "t3_renforce"]
* Aucun arrondi des moyennes : calcul en pleine précision, affichage à
  2 décimales. Le seuil de passage et les ex aequo se jugent sur la
  valeur ARRONDIE à 2 décimales (celle qui figure sur le bulletin).
* Matière sans note : exclue du numérateur ET du dénominateur.
* Matière incomplète (1 à 4 notes sur 5) : exclue aussi, mais signalée.
* Décision : moyenne annuelle >= 10,00 -> admis ; < 10,00 -> redouble.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

Nombre = Decimal | int | float
CENT = Decimal("0.01")
SEUIL_PASSAGE = Decimal("10")


class ModeCalculAnnuel(str, Enum):
    POIDS_EGAL = "poids_egal"
    T3_RENFORCE = "t3_renforce"


class Decision(str, Enum):
    ADMIS = "admis"
    REDOUBLE = "redouble"


def _d(x: Nombre) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def arrondi_affichage(valeur: Nombre) -> Decimal:
    """Arrondi à 2 décimales, mode « arrondi commercial » (0,005 -> 0,01)."""
    return _d(valeur).quantize(CENT, rounding=ROUND_HALF_UP)


def format_note(valeur: Nombre) -> str:
    """Rend la note telle qu'affichée : 2 décimales, virgule. Ex : ``12,47``."""
    return f"{arrondi_affichage(valeur):.2f}".replace(".", ",")


def moyenne_interrogations(i1: Nombre, i2: Nombre, i3: Nombre) -> Decimal:
    return (_d(i1) + _d(i2) + _d(i3)) / 3


def moyenne_matiere(i1: Nombre, i2: Nombre, i3: Nombre, d1: Nombre, d2: Nombre) -> Decimal:
    """Moyenne d'une matière sur un trimestre, en pleine précision."""
    return (moyenne_interrogations(i1, i2, i3) + _d(d1) + _d(d2)) / 3


@dataclass(frozen=True)
class ResultatMatiere:
    """Une matière évaluée pour un élève sur un trimestre."""

    matiere_id: int
    coefficient: Decimal
    moyenne: Decimal | None          # None = pas de moyenne exploitable
    incomplete: bool = False         # des notes manquent (1 à 4 sur 5)
    sans_note: bool = False          # aucune note saisie


def evaluer_matiere(
    matiere_id: int,
    coefficient: Nombre,
    i1: Nombre | None,
    i2: Nombre | None,
    i3: Nombre | None,
    d1: Nombre | None,
    d2: Nombre | None,
) -> ResultatMatiere:
    notes = [i1, i2, i3, d1, d2]
    presentes = [n for n in notes if n is not None]
    coef = _d(coefficient)

    if not presentes:
        return ResultatMatiere(matiere_id, coef, None, sans_note=True)
    if len(presentes) < 5:
        return ResultatMatiere(matiere_id, coef, None, incomplete=True)

    return ResultatMatiere(matiere_id, coef, moyenne_matiere(i1, i2, i3, d1, d2))


def evaluer_note_directe(
    matiere_id: int,
    coefficient: Nombre,
    note: Nombre | None,
) -> ResultatMatiere:
    """Matière notée par une seule valeur (ex : Conduite).

    Le résultat s'ajoute tel quel à la liste passée à ``moyenne_generale`` :
    il compte comme une matière ordinaire, avec son coefficient.
    """
    coef = _d(coefficient)
    if note is None:
        return ResultatMatiere(matiere_id, coef, None, sans_note=True)
    return ResultatMatiere(matiere_id, coef, _d(note))


def moyenne_generale(resultats: list[ResultatMatiere]) -> Decimal | None:
    """Moyenne générale d'un trimestre. ``None`` si aucune matière exploitable."""
    retenues = [r for r in resultats if r.moyenne is not None]
    somme_coef = sum((r.coefficient for r in retenues), Decimal(0))
    if somme_coef == 0:
        return None
    somme_pond = sum((r.moyenne * r.coefficient for r in retenues), Decimal(0))
    return somme_pond / somme_coef


def moyenne_annuelle(
    t1: Nombre | None,
    t2: Nombre | None,
    t3: Nombre | None,
    mode: ModeCalculAnnuel | str,
) -> Decimal | None:
    """Moyenne annuelle générale. ``None`` s'il manque un trimestre."""
    if t1 is None or t2 is None or t3 is None:
        return None
    mode = ModeCalculAnnuel(mode)
    t1, t2, t3 = _d(t1), _d(t2), _d(t3)
    if mode is ModeCalculAnnuel.POIDS_EGAL:
        return (t1 + t2 + t3) / 3
    return (t1 + t2 + 2 * t3) / 4


def decision_annuelle(moyenne_annuelle_generale: Nombre | None) -> Decision | None:
    """>= 10,00 (valeur affichée) -> admis ; < 10,00 -> redouble."""
    if moyenne_annuelle_generale is None:
        return None
    if arrondi_affichage(moyenne_annuelle_generale) >= SEUIL_PASSAGE:
        return Decision.ADMIS
    return Decision.REDOUBLE


def calculer_rangs(valeurs: dict[int, Nombre | None]) -> dict[int, int | None]:
    """Rang de chacun dans son groupe (une classe), d'après une moyenne.

    - tri décroissant ; meilleure moyenne = rang 1 ;
    - ex aequo (même valeur à 2 décimales) : même rang, le rang suivant
      saute d'autant -> 1, 2, 2, 4 ... ;
    - valeur ``None`` (aucune moyenne) : non classé -> ``None``.

    Comparaison faite sur la valeur ARRONDIE à 2 décimales, cohérente
    avec ce qui est imprimé sur le bulletin.
    """
    arrondies = {
        eid: (arrondi_affichage(v) if v is not None else None) for eid, v in valeurs.items()
    }
    classables = [v for v in arrondies.values() if v is not None]
    return {
        eid: (1 + sum(1 for autre in classables if autre > v) if v is not None else None)
        for eid, v in arrondies.items()
    }


def effectif_classe(valeurs: dict[int, Nombre | None]) -> int:
    """Nombre d'élèves effectivement classés (ceux qui ont une moyenne)."""
    return sum(1 for v in valeurs.values() if v is not None)
