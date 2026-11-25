"""Rôles et droits d'accès de l'administration.

L'administration n'est pas un profil unique : chaque compte porte un ou
plusieurs rôles (cumul possible), et ses droits sont la réunion des droits
de ses rôles. Les droits sont définis par **domaine** : qui peut le lire,
qui peut le modifier (modifier implique lire).

Les enseignants n'ont aucun domaine administratif : leurs accès (notes de
leurs classes, leurs affectations) sont contrôlés au cas par cas dans les
routes concernées.

Règle anti-fraude : aucun rôle, directeur compris, n'a le droit de
modifier une note ; le domaine « notes » est en lecture seule.
"""

from enum import Enum


class Role(str, Enum):
    DIRECTEUR = "directeur"
    CENSEUR = "censeur"            # directeur des études
    SURVEILLANT = "surveillant"    # surveillant général
    COMPTABLE = "comptable"        # directeur des affaires financières (DAF)
    SECRETAIRE = "secretaire"
    ENSEIGNANT = "enseignant"


ROLES_ADMINISTRATIFS = frozenset(
    {Role.DIRECTEUR, Role.CENSEUR, Role.SURVEILLANT, Role.COMPTABLE, Role.SECRETAIRE}
)
ROLES_PERSONNEL = ROLES_ADMINISTRATIFS | {Role.ENSEIGNANT}   # gérables via /utilisateurs

D, C, S, F, SEC = Role.DIRECTEUR, Role.CENSEUR, Role.SURVEILLANT, Role.COMPTABLE, Role.SECRETAIRE


class Domaine(str, Enum):
    PERSONNEL = "personnel"            # tout le personnel, comptes, attribution des rôles
    PARAMETRAGE = "parametrage"        # années, trimestres, mode de calcul, tarifs
    PEDAGOGIE = "pedagogie"            # classes, matières, coefficients, affectations, prof. principal
    NOTES = "notes"                    # consultation des notes et de leur historique
    BULLETINS = "bulletins"
    ELEVES = "eleves"                  # inscriptions, dossiers élèves, parents/tuteurs
    MEDICAL = "medical"
    VIE_SCOLAIRE = "vie_scolaire"      # présences, permissions, discipline
    ENCAISSEMENTS = "encaissements"    # encaisser les frais, reçus
    FINANCES = "finances"              # tranches, annulation de paiement, impayés
    BILANS = "bilans"                  # bilan financier (recouvrement, encaissements du mois)


# domaine -> (rôles qui lisent, rôles qui modifient)
_DROITS: dict[Domaine, tuple[frozenset, frozenset]] = {
    Domaine.PERSONNEL:     (frozenset(),                  frozenset({D})),
    Domaine.PARAMETRAGE:   (frozenset(),                  frozenset({D})),
    Domaine.PEDAGOGIE:     (frozenset({S, SEC}),          frozenset({D, C})),
    Domaine.NOTES:         (frozenset({D, C}),            frozenset()),
    Domaine.BULLETINS:     (frozenset(),                  frozenset({D, C})),
    Domaine.ELEVES:        (frozenset({C, S}),            frozenset({D, SEC})),
    Domaine.MEDICAL:       (frozenset({S}),               frozenset({D, SEC})),
    Domaine.VIE_SCOLAIRE:  (frozenset({C}),               frozenset({D, S})),
    Domaine.ENCAISSEMENTS: (frozenset(),                  frozenset({D, F, SEC})),
    Domaine.FINANCES:      (frozenset({SEC}),             frozenset({D, F})),
    Domaine.BILANS:        (frozenset({D, F}),            frozenset()),
}


def roles_qui_peuvent(domaine: Domaine, ecrire: bool = False) -> frozenset:
    lecture, ecriture = _DROITS[domaine]
    return ecriture if ecrire else lecture | ecriture


def peut(roles, domaine: Domaine, ecrire: bool = False) -> bool:
    """`roles` : liste des rôles du compte (chaînes ou Role)."""
    autorises = roles_qui_peuvent(domaine, ecrire)
    return any(Role(r) in autorises for r in roles if r in Role._value2member_map_)


def est_administratif(roles) -> bool:
    return any(r in {x.value for x in ROLES_ADMINISTRATIFS} for r in roles)


def matrice() -> dict[str, dict[str, list[str]]]:
    """Exposée au frontend pour qu'il affiche les mêmes droits que l'API."""
    return {
        d.value: {
            "lire": sorted(r.value for r in roles_qui_peuvent(d)),
            "ecrire": sorted(r.value for r in roles_qui_peuvent(d, ecrire=True)),
        }
        for d in Domaine
    }
