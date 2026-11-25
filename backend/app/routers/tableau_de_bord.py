"""Tableau de bord de l'administration.

Vue d'ensemble par classe et par niveau : effectifs, moyennes générales,
taux de présence, recouvrement des frais de scolarité, et une liste de
points à traiter.

Chaque bloc n'est calculé que si le rôle connecté y a droit :
- moyennes            -> bulletins (directeur, censeur)
- présences           -> vie scolaire (directeur, censeur, surveillant)
- finances            -> bilans (directeur, DAF)
Les enseignants n'ont pas de tableau de bord administratif.
"""

import datetime as _dt
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.calcul import arrondi_affichage
from app.core.deps import CurrentUser, DbSession
from app.core.permissions import Domaine, est_administratif, peut
from app.models import (
    Absence,
    AnneeScolaire,
    Classe,
    Ecole,
    Eleve,
    Note,
    NoteHistorique,
    Paiement,
    PermissionAbsence,
    Trimestre,
    Utilisateur,
)
from app.routers.paiements import suivi
from app.schemas import (
    TableauDeBord,
    TdbAlerte,
    TdbEffectifs,
    TdbFinances,
    TdbLigne,
    TdbPeriode,
    TdbScolarite,
    TdbTrimestre,
    TdbVieScolaire,
)
from app.services.bulletins import construire_bulletins_classe

router = APIRouter(tags=["tableau de bord"])

# Jours de classe pris en compte pour le taux de présence : lundi au samedi
# (cours le samedi matin).
JOURS_DE_CLASSE = {0, 1, 2, 3, 4, 5}
# Fenêtre utilisée si le trimestre n'a pas de dates.
FENETRE_PAR_DEFAUT = 30


def _jours_ouvres(debut: _dt.date, fin: _dt.date) -> int:
    if fin < debut:
        return 0
    n = (fin - debut).days + 1
    return sum(1 for i in range(n) if (debut + _dt.timedelta(days=i)).weekday() in JOURS_DE_CLASSE)


def _trimestre_courant(db: Session, annee: AnneeScolaire, aujourd_hui: _dt.date) -> Trimestre | None:
    """Le trimestre en cours ; sinon le dernier commencé qui a des notes ; sinon le dernier commencé."""
    trimestres = list(
        db.scalars(
            select(Trimestre)
            .where(Trimestre.annee_scolaire_id == annee.id)
            .order_by(Trimestre.numero.desc())
        )
    )
    for t in trimestres:
        if t.date_debut and t.date_fin and t.date_debut <= aujourd_hui <= t.date_fin:
            return t
    commences = [t for t in trimestres if t.date_debut is None or t.date_debut <= aujourd_hui]
    for t in commences:
        if db.scalar(select(Note.id).where(Note.trimestre_id == t.id).limit(1)) is not None:
            return t
    if commences:
        return commences[0]
    return trimestres[-1] if trimestres else None


def _periode(trimestre: Trimestre | None, aujourd_hui: _dt.date) -> TdbPeriode | None:
    if trimestre is not None and trimestre.date_debut is not None:
        debut = trimestre.date_debut
        fin = min(trimestre.date_fin or aujourd_hui, aujourd_hui)
    else:
        debut, fin = aujourd_hui - _dt.timedelta(days=FENETRE_PAR_DEFAUT - 1), aujourd_hui
    if fin < debut:
        return None   # trimestre pas encore commencé
    return TdbPeriode(debut=debut, fin=fin, jours_ouvres=_jours_ouvres(debut, fin))


def _taux(numerateur: Decimal | float, denominateur: Decimal | float) -> float | None:
    return round(float(numerateur) / float(denominateur), 4) if denominateur else None


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def tableau_de_bord(user: CurrentUser, db: DbSession, trimestre_id: int | None = None):
    if not est_administratif(user.roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé à l'administration.")

    voit_moyennes = peut(user.roles, Domaine.BULLETINS)
    voit_presences = peut(user.roles, Domaine.VIE_SCOLAIRE)
    voit_finances = peut(user.roles, Domaine.BILANS)
    aujourd_hui = _dt.date.today()

    annee = db.scalar(
        select(AnneeScolaire).where(AnneeScolaire.ecole_id == user.ecole_id, AnneeScolaire.active.is_(True))
    )

    # ---------- trimestre et période ----------
    trimestre: Trimestre | None = None
    if trimestre_id is not None:
        trimestre = db.get(Trimestre, trimestre_id)
        if trimestre is None or annee is None or trimestre.annee_scolaire_id != annee.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trimestre introuvable.")
    elif annee is not None:
        trimestre = _trimestre_courant(db, annee, aujourd_hui)
    periode = _periode(trimestre, aujourd_hui) if voit_presences else None

    # ---------- classes et élèves actifs de l'année ----------
    classes: list[Classe] = []
    if annee is not None:
        classes = list(
            db.scalars(
                select(Classe)
                .where(Classe.ecole_id == user.ecole_id, Classe.annee_scolaire_id == annee.id)
                .order_by(Classe.niveau_id, Classe.nom)
            )
        )
    eleves = list(
        db.scalars(
            select(Eleve).where(Eleve.ecole_id == user.ecole_id, Eleve.statut != "archive")
        )
    )
    ids_classes = {c.id for c in classes}
    par_classe: dict[int, list[Eleve]] = defaultdict(list)
    for e in eleves:
        if e.classe_id in ids_classes:
            par_classe[e.classe_id].append(e)
    inscrits = [e for e in eleves if e.classe_id in ids_classes]

    effectifs = TdbEffectifs(
        eleves_actifs=len(inscrits),
        filles=sum(1 for e in inscrits if e.sexe == "F"),
        garcons=sum(1 for e in inscrits if e.sexe == "M"),
        classes=len(classes),
        enseignants_actifs=db.scalar(
            select(func.count()).select_from(Utilisateur).where(
                Utilisateur.ecole_id == user.ecole_id,
                Utilisateur.actif.is_(True),
                Utilisateur.roles.any("enseignant"),
            )
        )
        or 0,
    )

    # ---------- moyennes par classe ----------
    moyennes: dict[int, list[Decimal]] = {}
    if voit_moyennes and trimestre is not None:
        ecole = db.get(Ecole, user.ecole_id)
        for c in classes:
            calc = construire_bulletins_classe(
                db, classe=c, trimestre=trimestre, mode_annuel=ecole.mode_calcul_moyenne_annuelle
            )
            moyennes[c.id] = [b.moyenne_generale for b in calc.eleves if b.moyenne_generale is not None]

    def _stats_moyennes(valeurs: list[Decimal]) -> tuple[float | None, float | None]:
        if not valeurs:
            return None, None
        moyenne = sum(valeurs, Decimal(0)) / len(valeurs)
        reussite = sum(1 for v in valeurs if v >= 10) / len(valeurs)
        return float(arrondi_affichage(moyenne)), round(reussite, 4)

    # ---------- absences par classe ----------
    absences_par_classe: dict[int, int] = defaultdict(int)
    retards = 0
    if periode is not None and inscrits:
        ids_eleves = [e.id for e in inscrits]
        classe_de = {e.id: e.classe_id for e in inscrits}
        jours = db.execute(
            select(Absence.eleve_id, func.count(distinct(Absence.date)))
            .where(
                Absence.eleve_id.in_(ids_eleves),
                Absence.type == "absence",
                Absence.date.between(periode.debut, periode.fin),
            )
            .group_by(Absence.eleve_id)
        )
        for eid, n in jours:
            absences_par_classe[classe_de[eid]] += n
        retards = db.scalar(
            select(func.count()).select_from(Absence).where(
                Absence.eleve_id.in_(ids_eleves),
                Absence.type == "retard",
                Absence.date.between(periode.debut, periode.fin),
            )
        ) or 0

    def _taux_presence(effectif: int, jours_absence: int) -> float | None:
        if periode is None or not periode.jours_ouvres or not effectif:
            return None
        return round(1 - jours_absence / (effectif * periode.jours_ouvres), 4)

    # ---------- finances ----------
    finances: TdbFinances | None = None
    recouvrement: dict[int, tuple[Decimal, Decimal]] = {}
    if voit_finances and annee is not None:
        s = suivi(user=user, db=db, annee_scolaire_id=annee.id, classe_id=None)
        acc: dict[int, list[Decimal]] = defaultdict(lambda: [Decimal(0), Decimal(0)])
        for ligne in s.lignes:
            acc[ligne.classe_id][0] += Decimal(str(ligne.total_du))
            acc[ligne.classe_id][1] += Decimal(str(ligne.total_paye))
        recouvrement = {cid: (v[0], v[1]) for cid, v in acc.items()}
        debut_mois = aujourd_hui.replace(day=1)
        encaisse_mois = db.scalar(
            select(func.coalesce(func.sum(Paiement.montant_paye), 0))
            .join(Eleve, Eleve.id == Paiement.eleve_id)
            .where(Eleve.ecole_id == user.ecole_id, Paiement.date_paiement >= debut_mois,
                   Paiement.date_paiement <= aujourd_hui)
        )
        finances = TdbFinances(
            annee_libelle=s.annee_libelle,
            attendu=s.total_attendu,
            encaisse=s.total_encaisse,
            reste=s.reste,
            taux_recouvrement=_taux(s.total_encaisse, s.total_attendu),
            encaisse_mois=float(encaisse_mois or 0),
            eleves_en_retard=s.nb_en_retard,
        )

    # ---------- lignes par classe ----------
    lignes: list[TdbLigne] = []
    for c in classes:
        effectif = len(par_classe[c.id])
        moy, reussite = _stats_moyennes(moyennes.get(c.id, [])) if voit_moyennes else (None, None)
        du, paye = recouvrement.get(c.id, (Decimal(0), Decimal(0)))
        lignes.append(TdbLigne(
            classe_id=c.id,
            libelle=c.nom,
            niveau_nom=c.niveau.nom,
            effectif=effectif,
            moyenne=moy,
            taux_reussite=reussite,
            taux_presence=_taux_presence(effectif, absences_par_classe[c.id]) if voit_presences else None,
            taux_recouvrement=_taux(paye, du) if voit_finances else None,
        ))

    # ---------- lignes par niveau (agrégées sur les élèves, pas sur les classes) ----------
    niveaux: list[TdbLigne] = []
    groupes: dict[int, list[Classe]] = defaultdict(list)
    for c in classes:
        groupes[c.niveau_id].append(c)
    for _, cs in sorted(groupes.items()):
        effectif = sum(len(par_classe[c.id]) for c in cs)
        moy, reussite = (
            _stats_moyennes([v for c in cs for v in moyennes.get(c.id, [])]) if voit_moyennes else (None, None)
        )
        du = sum((recouvrement.get(c.id, (Decimal(0), Decimal(0)))[0] for c in cs), Decimal(0))
        paye = sum((recouvrement.get(c.id, (Decimal(0), Decimal(0)))[1] for c in cs), Decimal(0))
        niveaux.append(TdbLigne(
            libelle=cs[0].niveau.nom,
            niveau_nom=cs[0].niveau.nom,
            effectif=effectif,
            moyenne=moy,
            taux_reussite=reussite,
            taux_presence=(
                _taux_presence(effectif, sum(absences_par_classe[c.id] for c in cs)) if voit_presences else None
            ),
            taux_recouvrement=_taux(paye, du) if voit_finances else None,
        ))

    # ---------- blocs de synthèse ----------
    scolarite = None
    if voit_moyennes:
        toutes = [v for vs in moyennes.values() for v in vs]
        moy, reussite = _stats_moyennes(toutes)
        scolarite = TdbScolarite(moyenne_ecole=moy, taux_reussite=reussite, eleves_notes=len(toutes))

    permissions_en_attente = db.scalar(
        select(func.count()).select_from(PermissionAbsence)
        .join(Eleve, Eleve.id == PermissionAbsence.eleve_id)
        .where(Eleve.ecole_id == user.ecole_id, PermissionAbsence.statut == "en_attente")
    ) or 0

    vie_scolaire = None
    if voit_presences:
        total_absence = sum(absences_par_classe.values())
        vie_scolaire = TdbVieScolaire(
            taux_presence=_taux_presence(len(inscrits), total_absence),
            jours_absence=total_absence,
            retards=retards,
            permissions_en_attente=permissions_en_attente,
        )

    # ---------- points à traiter ----------
    alertes: list[TdbAlerte] = []
    # à traiter seulement par qui décide (surveillant, directeur) ; le censeur ne fait que consulter
    if peut(user.roles, Domaine.VIE_SCOLAIRE, ecrire=True) and permissions_en_attente:
        alertes.append(TdbAlerte(
            code="permissions", niveau="attention", nombre=permissions_en_attente,
            libelle="demande(s) d'autorisation d'absence en attente", lien="/autorisations",
        ))
    if voit_finances and finances and finances.eleves_en_retard:
        alertes.append(TdbAlerte(
            code="impayes", niveau="attention", nombre=finances.eleves_en_retard,
            libelle="élève(s) en retard de paiement", lien="/paiements",
        ))
    if peut(user.roles, Domaine.PEDAGOGIE):
        sans_pp = sum(1 for c in classes if c.professeur_principal_id is None)
        if sans_pp:
            alertes.append(TdbAlerte(
                code="sans_pp", niveau="attention", nombre=sans_pp,
                libelle="classe(s) sans professeur principal : la conduite ne peut pas être saisie",
                lien="/classes",
            ))
    if peut(user.roles, Domaine.ELEVES):
        sans_classe = sum(1 for e in eleves if e.classe_id not in ids_classes)
        if sans_classe:
            alertes.append(TdbAlerte(
                code="sans_classe", niveau="info", nombre=sans_classe,
                libelle="élève(s) actif(s) sans classe cette année", lien="/eleves",
            ))
    if peut(user.roles, Domaine.NOTES):
        depuis = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=7)
        modifs = db.scalar(
            select(func.count()).select_from(NoteHistorique)
            .join(Eleve, Eleve.id == NoteHistorique.eleve_id)
            .where(
                Eleve.ecole_id == user.ecole_id,
                NoteHistorique.action.in_(("modification", "suppression")),
                NoteHistorique.le >= depuis,
            )
        ) or 0
        if modifs:
            alertes.append(TdbAlerte(
                code="notes_modifiees", niveau="info", nombre=modifs,
                libelle="note(s) modifiée(s) ou supprimée(s) ces 7 derniers jours",
                lien="/classes",
            ))

    return TableauDeBord(
        trimestre=(
            TdbTrimestre(id=trimestre.id, numero=trimestre.numero, annee_libelle=annee.libelle)
            if trimestre is not None and annee is not None
            else None
        ),
        periode_presence=periode,
        effectifs=effectifs,
        scolarite=scolarite,
        vie_scolaire=vie_scolaire,
        finances=finances,
        alertes=alertes,
        classes=lignes,
        niveaux=niveaux,
    )
