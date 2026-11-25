"""Paiements / frais de scolarité.

- Les tranches (nombre, montant, date limite) sont configurables par école et
  par année scolaire. Une tranche s'applique à tous les élèves de l'école.
- Un paiement est rattaché à une tranche ; plusieurs paiements partiels sont
  possibles tant que le total ne dépasse pas le montant de la tranche.
- Chaque paiement reçoit un numéro de reçu unique (REC-000123).
- Accès strictement réservé à l'administration.
"""

import datetime as _dt
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ecriture, lecture
from app.core.permissions import Domaine
from app.models import (
    AnneeScolaire,
    Classe,
    Ecole,
    Eleve,
    Paiement,
    TranchePaiement,
    Utilisateur,
)
from app.schemas import (
    PaiementCreate,
    PaiementOut,
    RecuOut,
    SituationEleve,
    SituationTranche,
    SuiviLigne,
    SuiviPaiements,
    TrancheCreate,
    TrancheOut,
    TrancheUpdate,
)

router = APIRouter(tags=["paiements"])

LireFinances = lecture(Domaine.FINANCES)
GererFinances = ecriture(Domaine.FINANCES)
LireEncaissements = lecture(Domaine.ENCAISSEMENTS)
Encaisser = ecriture(Domaine.ENCAISSEMENTS)


# ---------- Utilitaires ----------

def _libelle_defaut(numero: int) -> str:
    return f"{numero}{'re' if numero == 1 else 'e'} tranche"


def _libelle(t: TranchePaiement) -> str:
    return t.libelle or _libelle_defaut(t.numero)


def statut_tranche(montant: Decimal, paye: Decimal, date_limite: _dt.date | None, aujourd_hui: _dt.date) -> str:
    if paye >= montant:
        return "solde"
    if date_limite is not None and aujourd_hui > date_limite:
        return "en_retard"
    return "partiel" if paye > 0 else "non_paye"


def statut_global(statuts: list[str], total_paye: Decimal) -> str:
    if not statuts:
        return "aucune_tranche"
    if all(s == "solde" for s in statuts):
        return "solde"
    if "en_retard" in statuts:
        return "en_retard"
    return "partiel" if total_paye > 0 else "non_paye"


def _annee(db: Session, ecole_id: int, annee_id: int | None) -> AnneeScolaire | None:
    if annee_id is not None:
        annee = db.get(AnneeScolaire, annee_id)
        if annee is None or annee.ecole_id != ecole_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Année scolaire inconnue.")
        return annee
    return db.scalar(
        select(AnneeScolaire).where(AnneeScolaire.ecole_id == ecole_id, AnneeScolaire.active.is_(True))
    )


def _annee_requise(db: Session, ecole_id: int, annee_id: int | None) -> AnneeScolaire:
    annee = _annee(db, ecole_id, annee_id)
    if annee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune année scolaire active. Précisez annee_scolaire_id ou activez une année.",
        )
    return annee


def _tranches(db: Session, ecole_id: int, annee_id: int) -> list[TranchePaiement]:
    stmt = (
        select(TranchePaiement)
        .where(TranchePaiement.ecole_id == ecole_id, TranchePaiement.annee_scolaire_id == annee_id)
        .order_by(TranchePaiement.numero)
    )
    return list(db.scalars(stmt))


def _tranche(db: Session, tranche_id: int, ecole_id: int) -> TranchePaiement:
    t = db.get(TranchePaiement, tranche_id)
    if t is None or t.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tranche introuvable.")
    return t


def _eleve(db: Session, eleve_id: int, ecole_id: int) -> Eleve:
    e = db.get(Eleve, eleve_id)
    if e is None or e.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    return e


def _annee_de_leleve(db: Session, eleve: Eleve) -> AnneeScolaire | None:
    """Année de la classe de l'élève, sinon l'année active de l'école."""
    if eleve.classe is not None:
        return db.get(AnneeScolaire, eleve.classe.annee_scolaire_id)
    return _annee(db, eleve.ecole_id, None)


def _paye_par_tranche(db: Session, eleve_id: int, tranche_ids: list[int]) -> dict[int, Decimal]:
    if not tranche_ids:
        return {}
    stmt = (
        select(Paiement.tranche_id, func.sum(Paiement.montant_paye))
        .where(Paiement.eleve_id == eleve_id, Paiement.tranche_id.in_(tranche_ids))
        .group_by(Paiement.tranche_id)
    )
    return {tid: total for tid, total in db.execute(stmt)}


def _vers_paiement_out(db: Session, p: Paiement) -> PaiementOut:
    auteur = db.get(Utilisateur, p.enregistre_par) if p.enregistre_par else None
    return PaiementOut(
        id=p.id,
        eleve_id=p.eleve_id,
        tranche_id=p.tranche_id,
        tranche_libelle=_libelle(p.tranche),
        montant_paye=float(p.montant_paye),
        date_paiement=p.date_paiement,
        mode_paiement=p.mode_paiement,
        numero_recu=p.numero_recu,
        enregistre_par_nom=f"{auteur.prenom} {auteur.nom}" if auteur else None,
        created_at=p.created_at,
    )


def _vers_tranche_out(db: Session, t: TranchePaiement) -> TrancheOut:
    nb = db.scalar(select(func.count()).select_from(Paiement).where(Paiement.tranche_id == t.id))
    return TrancheOut(
        id=t.id,
        annee_scolaire_id=t.annee_scolaire_id,
        numero=t.numero,
        libelle=_libelle(t),
        montant=float(t.montant),
        date_limite=t.date_limite,
        nb_paiements=nb or 0,
    )


# ---------- Tranches ----------

@router.get("/paiements/tranches", response_model=list[TrancheOut], dependencies=[LireFinances])
def lister_tranches(user: CurrentUser, db: DbSession, annee_scolaire_id: int | None = None):
    annee = _annee(db, user.ecole_id, annee_scolaire_id)
    if annee is None:
        return []
    return [_vers_tranche_out(db, t) for t in _tranches(db, user.ecole_id, annee.id)]


@router.post("/paiements/tranches", response_model=TrancheOut, status_code=status.HTTP_201_CREATED, dependencies=[GererFinances])
def creer_tranche(data: TrancheCreate, user: CurrentUser, db: DbSession):
    annee = _annee_requise(db, user.ecole_id, data.annee_scolaire_id)
    dernier = db.scalar(
        select(func.max(TranchePaiement.numero)).where(
            TranchePaiement.ecole_id == user.ecole_id, TranchePaiement.annee_scolaire_id == annee.id
        )
    )
    numero = (dernier or 0) + 1
    t = TranchePaiement(
        ecole_id=user.ecole_id,
        annee_scolaire_id=annee.id,
        numero=numero,
        libelle=data.libelle or _libelle_defaut(numero),
        montant=Decimal(str(data.montant)),
        date_limite=data.date_limite,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _vers_tranche_out(db, t)


@router.patch("/paiements/tranches/{tranche_id}", response_model=TrancheOut, dependencies=[GererFinances])
def modifier_tranche(tranche_id: int, data: TrancheUpdate, user: CurrentUser, db: DbSession):
    t = _tranche(db, tranche_id, user.ecole_id)
    champs = data.model_dump(exclude_unset=True)
    if champs.get("montant") is not None:
        nouveau = Decimal(str(champs["montant"]))
        # le nouveau montant doit rester ≥ au plus gros total déjà versé par un élève
        deja = db.execute(
            select(func.sum(Paiement.montant_paye))
            .where(Paiement.tranche_id == t.id)
            .group_by(Paiement.eleve_id)
        ).scalars().all()
        plus_gros_versement = max(deja, default=Decimal(0))
        if nouveau < plus_gros_versement:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Un élève a déjà versé {plus_gros_versement:,.0f} FCFA sur cette tranche : "
                    "le montant ne peut pas être inférieur."
                ).replace(",", " "),
            )
        t.montant = nouveau
    if "libelle" in champs:
        t.libelle = champs["libelle"] or _libelle_defaut(t.numero)
    if "date_limite" in champs:
        t.date_limite = champs["date_limite"]
    db.commit()
    db.refresh(t)
    return _vers_tranche_out(db, t)


@router.delete("/paiements/tranches/{tranche_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[GererFinances])
def supprimer_tranche(tranche_id: int, user: CurrentUser, db: DbSession):
    t = _tranche(db, tranche_id, user.ecole_id)
    if db.scalar(select(func.count()).select_from(Paiement).where(Paiement.tranche_id == t.id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Des paiements sont enregistrés sur cette tranche : impossible de la supprimer.",
        )
    db.delete(t)
    db.commit()


# ---------- Situation et paiements d'un élève ----------

def _situation(db: Session, eleve: Eleve, aujourd_hui: _dt.date) -> SituationEleve:
    annee = _annee_de_leleve(db, eleve)
    tranches = _tranches(db, eleve.ecole_id, annee.id) if annee else []
    payes = _paye_par_tranche(db, eleve.id, [t.id for t in tranches])

    lignes: list[SituationTranche] = []
    for t in tranches:
        paye = payes.get(t.id, Decimal(0))
        lignes.append(
            SituationTranche(
                tranche_id=t.id,
                numero=t.numero,
                libelle=_libelle(t),
                montant=float(t.montant),
                date_limite=t.date_limite,
                paye=float(paye),
                reste=float(max(t.montant - paye, Decimal(0))),
                statut=statut_tranche(t.montant, paye, t.date_limite, aujourd_hui),
            )
        )
    total_du = sum((t.montant for t in tranches), Decimal(0))
    total_paye = sum(payes.values(), Decimal(0))

    paiements = db.scalars(
        select(Paiement)
        .where(Paiement.eleve_id == eleve.id)
        .order_by(Paiement.date_paiement.desc(), Paiement.id.desc())
    )
    return SituationEleve(
        eleve_id=eleve.id,
        annee_scolaire_id=annee.id if annee else None,
        annee_libelle=annee.libelle if annee else None,
        total_du=float(total_du),
        total_paye=float(total_paye),
        reste=float(max(total_du - total_paye, Decimal(0))),
        statut=statut_global([l.statut for l in lignes], total_paye),
        tranches=lignes,
        paiements=[_vers_paiement_out(db, p) for p in paiements],
    )


@router.get("/eleves/{eleve_id}/paiements", response_model=SituationEleve, dependencies=[LireEncaissements])
def situation_eleve(eleve_id: int, user: CurrentUser, db: DbSession):
    eleve = _eleve(db, eleve_id, user.ecole_id)
    return _situation(db, eleve, _dt.date.today())


@router.post(
    "/eleves/{eleve_id}/paiements",
    response_model=PaiementOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Encaisser],
)
def enregistrer_paiement(eleve_id: int, data: PaiementCreate, user: CurrentUser, db: DbSession):
    eleve = _eleve(db, eleve_id, user.ecole_id)
    tranche = _tranche(db, data.tranche_id, user.ecole_id)

    date_paiement = data.date_paiement or _dt.date.today()
    if date_paiement > _dt.date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La date du paiement ne peut pas être dans le futur.",
        )

    montant = Decimal(str(data.montant_paye))
    deja = _paye_par_tranche(db, eleve.id, [tranche.id]).get(tranche.id, Decimal(0))
    reste = tranche.montant - deja
    if reste <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette tranche est déjà soldée.")
    if montant > reste:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le montant dépasse le reste à payer sur cette tranche ({reste:,.0f} FCFA).".replace(",", " "),
        )

    p = Paiement(
        eleve_id=eleve.id,
        tranche_id=tranche.id,
        montant_paye=montant,
        date_paiement=date_paiement,
        mode_paiement=data.mode_paiement,
        enregistre_par=user.id,
    )
    db.add(p)
    db.flush()
    p.numero_recu = f"REC-{p.id:06d}"
    db.commit()
    db.refresh(p)
    return _vers_paiement_out(db, p)


@router.delete("/eleves/{eleve_id}/paiements/{paiement_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[GererFinances])
def annuler_paiement(eleve_id: int, paiement_id: int, user: CurrentUser, db: DbSession):
    _eleve(db, eleve_id, user.ecole_id)
    p = db.get(Paiement, paiement_id)
    if p is None or p.eleve_id != eleve_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable.")
    db.delete(p)
    db.commit()


# ---------- Reçu ----------

@router.get("/paiements/{paiement_id}/recu", response_model=RecuOut, dependencies=[LireEncaissements])
def recu(paiement_id: int, user: CurrentUser, db: DbSession):
    p = db.get(Paiement, paiement_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable.")
    eleve = _eleve(db, p.eleve_id, user.ecole_id)
    ecole = db.get(Ecole, user.ecole_id)
    tranche = p.tranche
    annee = db.get(AnneeScolaire, tranche.annee_scolaire_id)

    # Situation « à la date du reçu » : on ne compte que les paiements
    # enregistrés jusqu'à celui-ci inclus (un reçu réimprimé reste identique).
    anterieurs = select(Paiement).where(Paiement.eleve_id == eleve.id, Paiement.id <= p.id)
    payes: dict[int, Decimal] = {}
    for q in db.scalars(anterieurs):
        payes[q.tranche_id] = payes.get(q.tranche_id, Decimal(0)) + q.montant_paye
    tranches = _tranches(db, eleve.ecole_id, annee.id)
    total_du = sum((t.montant for t in tranches), Decimal(0))
    total_paye = sum((payes.get(t.id, Decimal(0)) for t in tranches), Decimal(0))

    return RecuOut(
        paiement=_vers_paiement_out(db, p),
        ecole_nom=ecole.nom,
        ecole_sigle=ecole.sigle,
        ecole_adresse=ecole.adresse,
        ecole_telephone=ecole.telephone,
        annee_libelle=annee.libelle,
        eleve_matricule=eleve.matricule,
        eleve_nom=eleve.nom,
        eleve_prenom=eleve.prenom,
        classe_nom=eleve.classe.nom if eleve.classe else None,
        tranche_montant=float(tranche.montant),
        tranche_reste_apres=float(max(tranche.montant - payes.get(tranche.id, Decimal(0)), Decimal(0))),
        total_du=float(total_du),
        total_paye_a_date=float(total_paye),
        reste_global=float(max(total_du - total_paye, Decimal(0))),
    )


# ---------- Suivi d'ensemble ----------

@router.get("/paiements/suivi", response_model=SuiviPaiements, dependencies=[LireFinances])
def suivi(
    user: CurrentUser,
    db: DbSession,
    annee_scolaire_id: int | None = None,
    classe_id: int | None = None,
):
    annee = _annee_requise(db, user.ecole_id, annee_scolaire_id)
    tranches = _tranches(db, user.ecole_id, annee.id)
    tranche_ids = [t.id for t in tranches]
    aujourd_hui = _dt.date.today()

    stmt = (
        select(Eleve, Classe)
        .join(Classe, Classe.id == Eleve.classe_id)
        .where(
            Eleve.ecole_id == user.ecole_id,
            Eleve.statut != "archive",
            Classe.annee_scolaire_id == annee.id,
        )
        .order_by(Classe.nom, Eleve.nom, Eleve.prenom)
    )
    if classe_id is not None:
        stmt = stmt.where(Classe.id == classe_id)
    eleves = db.execute(stmt).all()

    # Totaux payés (élève, tranche) et date du dernier paiement, en 2 requêtes.
    payes: dict[tuple[int, int], Decimal] = {}
    derniers: dict[int, _dt.date] = {}
    ids = [e.id for e, _ in eleves]
    if ids and tranche_ids:
        for eid, tid, total, dernier in db.execute(
            select(
                Paiement.eleve_id,
                Paiement.tranche_id,
                func.sum(Paiement.montant_paye),
                func.max(Paiement.date_paiement),
            )
            .where(Paiement.eleve_id.in_(ids), Paiement.tranche_id.in_(tranche_ids))
            .group_by(Paiement.eleve_id, Paiement.tranche_id)
        ):
            payes[(eid, tid)] = total
            derniers[eid] = max(dernier, derniers.get(eid, dernier))

    total_du = sum((t.montant for t in tranches), Decimal(0))
    lignes: list[SuiviLigne] = []
    for e, c in eleves:
        statuts = []
        paye = Decimal(0)
        for t in tranches:
            pt = payes.get((e.id, t.id), Decimal(0))
            paye += pt
            statuts.append(statut_tranche(t.montant, pt, t.date_limite, aujourd_hui))
        lignes.append(
            SuiviLigne(
                eleve_id=e.id,
                matricule=e.matricule,
                nom=e.nom,
                prenom=e.prenom,
                classe_id=c.id,
                classe_nom=c.nom,
                total_du=float(total_du),
                total_paye=float(paye),
                reste=float(max(total_du - paye, Decimal(0))),
                statut=statut_global(statuts, paye),
                dernier_paiement=derniers.get(e.id),
            )
        )

    encaisse = sum((Decimal(str(l.total_paye)) for l in lignes), Decimal(0))
    attendu = total_du * len(lignes)
    return SuiviPaiements(
        annee_scolaire_id=annee.id,
        annee_libelle=annee.libelle,
        nb_tranches=len(tranches),
        total_attendu=float(attendu),
        total_encaisse=float(encaisse),
        reste=float(max(attendu - encaisse, Decimal(0))),
        nb_eleves=len(lignes),
        nb_soldes=sum(1 for l in lignes if l.statut == "solde"),
        nb_en_retard=sum(1 for l in lignes if l.statut == "en_retard"),
        lignes=lignes,
    )
