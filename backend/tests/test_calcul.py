"""Tests de la fonction unique de calcul (app/calcul.py)."""

from decimal import Decimal

import pytest

from app.calcul import (
    Decision,
    ModeCalculAnnuel,
    ResultatMatiere,
    arrondi_affichage,
    calculer_rangs,
    decision_annuelle,
    effectif_classe,
    evaluer_matiere,
    evaluer_note_directe,
    format_note,
    moyenne_annuelle,
    moyenne_generale,
    moyenne_interrogations,
    moyenne_matiere,
)

D = Decimal


# ---------- Moyenne d'une matière ----------

def test_moyenne_interrogations():
    assert moyenne_interrogations(12, 14, 16) == D(14)


def test_moyenne_matiere_exemple_simple():
    # interros -> 12 ; (12 + 15 + 9) / 3 = 12
    assert moyenne_matiere(12, 12, 12, 15, 9) == D(12)


def test_les_trois_interros_pesent_comme_un_devoir():
    # 3 interros à 0, 2 devoirs à 18 -> (0 + 18 + 18) / 3 = 12
    assert moyenne_matiere(0, 0, 0, 18, 18) == D(12)
    # ce n'est donc PAS (0+0+0+18+18)/5 = 7,2
    assert moyenne_matiere(0, 0, 0, 18, 18) != D("7.2")


def test_moyenne_matiere_pleine_precision():
    # (10/3 + 5 + 5) / 3 = (3,333... + 10) / 3 = 4,444...
    v = moyenne_matiere(0, 0, 10, 5, 5)
    assert v > D("4.444") and v < D("4.445")


# ---------- evaluer_matiere : cases manquantes ----------

def test_evaluer_matiere_complete():
    r = evaluer_matiere(1, 2, 10, 10, 10, 10, 10)
    assert r.moyenne == D(10)
    assert not r.incomplete and not r.sans_note


def test_evaluer_matiere_sans_aucune_note():
    r = evaluer_matiere(1, 2, None, None, None, None, None)
    assert r.moyenne is None and r.sans_note and not r.incomplete


def test_evaluer_matiere_incomplete():
    r = evaluer_matiere(1, 2, 10, 12, None, 8, 14)
    assert r.moyenne is None and r.incomplete and not r.sans_note


# ---------- Moyenne générale du trimestre ----------

def test_moyenne_generale_ponderee():
    resultats = [
        ResultatMatiere(1, D(3), D(10)),   # 30
        ResultatMatiere(2, D(1), D(18)),   # 18
    ]
    # (30 + 18) / 4 = 12
    assert moyenne_generale(resultats) == D(12)


def test_moyenne_generale_college_coef_1_est_moyenne_simple():
    resultats = [
        ResultatMatiere(1, D(1), D(8)),
        ResultatMatiere(2, D(1), D(12)),
        ResultatMatiere(3, D(1), D(16)),
    ]
    assert moyenne_generale(resultats) == D(12)


def test_moyenne_generale_exclut_matiere_sans_moyenne():
    resultats = [
        ResultatMatiere(1, D(2), D(10)),
        ResultatMatiere(2, D(5), None, incomplete=True),   # ignorée, num. ET dénom.
    ]
    assert moyenne_generale(resultats) == D(10)


def test_moyenne_generale_aucune_matiere():
    assert moyenne_generale([]) is None
    assert moyenne_generale([ResultatMatiere(1, D(2), None, sans_note=True)]) is None


# ---------- Conduite (matière "note directe") ----------

def test_note_directe_slot_dans_resultat_matiere():
    r = evaluer_note_directe(99, D(1), D("15"))
    assert r.moyenne == D(15)
    assert not r.incomplete and not r.sans_note


def test_note_directe_absente():
    r = evaluer_note_directe(99, D(1), None)
    assert r.moyenne is None and r.sans_note


def test_conduite_entre_dans_la_moyenne_du_trimestre():
    # 2 matières scolaires + la conduite, la formule pondérée les traite pareil
    resultats = [
        ResultatMatiere(1, D(3), D(10)),                  # 30
        ResultatMatiere(2, D(2), D(15)),                  # 30
        evaluer_note_directe(3, D(1), D("6")),            # conduite : 6
    ]
    # (30 + 30 + 6) / (3 + 2 + 1) = 66 / 6 = 11
    assert moyenne_generale(resultats) == D(11)


def test_sans_conduite_le_resultat_differe():
    sans = [ResultatMatiere(1, D(3), D(10)), ResultatMatiere(2, D(2), D(15))]
    avec = sans + [evaluer_note_directe(3, D(1), D("6"))]
    assert moyenne_generale(sans) == D(12)   # 60 / 5
    assert moyenne_generale(avec) == D(11)   # 66 / 6  -> la conduite pèse, sans fausser la formule


# ---------- Moyenne annuelle ----------

def test_moyenne_annuelle_poids_egal():
    assert moyenne_annuelle(9, 12, 12, ModeCalculAnnuel.POIDS_EGAL) == D(11)


def test_moyenne_annuelle_t3_renforce():
    # (10 + 10 + 2*14) / 4 = 12
    assert moyenne_annuelle(10, 10, 14, "t3_renforce") == D(12)


def test_moyenne_annuelle_trimestre_manquant():
    assert moyenne_annuelle(10, None, 12, ModeCalculAnnuel.POIDS_EGAL) is None


# ---------- Arrondi / affichage ----------

def test_arrondi_affichage_deux_decimales():
    assert arrondi_affichage(D("12.476")) == D("12.48")
    assert arrondi_affichage(D("12.474")) == D("12.47")
    assert arrondi_affichage(D("12.005")) == D("12.01")   # arrondi commercial


def test_format_note_virgule():
    assert format_note(D("12.4")) == "12,40"
    assert format_note(10) == "10,00"
    assert format_note(D("7.126")) == "7,13"


# ---------- Décision de fin d'année ----------

def test_decision_admis_et_redouble():
    assert decision_annuelle(D("10")) is Decision.ADMIS
    assert decision_annuelle(D("13.5")) is Decision.ADMIS
    assert decision_annuelle(D("9.99")) is Decision.REDOUBLE
    assert decision_annuelle(None) is None


def test_decision_jugee_sur_la_valeur_affichee():
    # 9,997 s'affiche "10,00" sur le bulletin -> l'élève passe
    assert format_note(D("9.997")) == "10,00"
    assert decision_annuelle(D("9.997")) is Decision.ADMIS


# ---------- Rang dans la classe ----------

def test_rang_ordre_simple():
    rangs = calculer_rangs({1: D(15), 2: D(12), 3: D(9)})
    assert rangs == {1: 1, 2: 2, 3: 3}


def test_rang_ex_aequo_groupes_avec_saut():
    # deux 2es -> pas de 3e, le suivant est 4e
    rangs = calculer_rangs({1: D(16), 2: D(12), 3: D(12), 4: D(8)})
    assert rangs == {1: 1, 2: 2, 3: 2, 4: 4}


def test_rang_ex_aequo_juge_sur_deux_decimales():
    # 12,531 et 12,529 s'affichent tous deux "12,53" -> ex aequo
    rangs = calculer_rangs({1: D("12.531"), 2: D("12.529"), 3: D("10")})
    assert rangs == {1: 1, 2: 1, 3: 3}


def test_rang_eleve_sans_moyenne_non_classe():
    rangs = calculer_rangs({1: D(14), 2: None, 3: D(11)})
    assert rangs == {1: 1, 2: None, 3: 2}
    assert effectif_classe({1: D(14), 2: None, 3: D(11)}) == 2


def test_rang_classe_vide():
    assert calculer_rangs({}) == {}


# ---------- Enchaînement complet (bout en bout, sans base) ----------

def test_scenario_complet_un_eleve_terminale_D():
    """Un élève de Tle D, un trimestre, coefficients officiels."""
    # (matiere_id, coef, i1, i2, i3, d1, d2)
    saisies = [
        (1, 5, 12, 14, 13, 11, 15),   # SVT
        (2, 4, 8, 10, 9, 12, 11),     # Maths
        (3, 4, 14, 13, 15, 16, 12),   # Sciences physiques/PCT
        (4, 2, 10, 11, 9, 13, 12),    # Français
        (5, 1, 15, 16, 17, 14, 18),   # EPS
    ]
    resultats = [evaluer_matiere(mid, coef, i1, i2, i3, d1, d2)
                 for (mid, coef, i1, i2, i3, d1, d2) in saisies]
    assert all(r.moyenne is not None for r in resultats)

    moy_t = moyenne_generale(resultats)
    assert moy_t is not None
    # Vérif indépendante : somme pondérée / somme des coefficients (= 16)
    somme = sum(r.moyenne * r.coefficient for r in resultats)
    assert moy_t == somme / Decimal(16)
    assert D(10) <= arrondi_affichage(moy_t) <= D(20)

    annuelle = moyenne_annuelle(moy_t, moy_t, moy_t, ModeCalculAnnuel.POIDS_EGAL)
    assert annuelle == moy_t
    assert decision_annuelle(annuelle) in (Decision.ADMIS, Decision.REDOUBLE)
