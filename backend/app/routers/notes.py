"""Saisie et validation des notes.

- Enseignant : saisit les 3 interros + 2 devoirs pour les classes/matières
  qui lui sont affectées. Ne peut pas toucher une note validée.
- Administration : saisit toutes les notes de son école, saisit la note de
  conduite (matière « note directe »), et valide / dévalide les notes.

Toute modification du contenu d'une note remet sa validation à zéro : il
faut la revalider explicitement.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calcul import arrondi_affichage, evaluer_matiere
from app.core.deps import CurrentUser, DbSession, require_roles
from app.models import (
    AnneeScolaire,
    Classe,
    Eleve,
    EnseignantAffectation,
    Matiere,
    Note,
    Trimestre,
    Utilisateur,
)
from app.schemas import NoteEcrire, NoteOut, NoteValidation

router = APIRouter(prefix="/notes", tags=["notes"])

AdminOnly = Depends(require_roles("admin"))
CHAMPS_EVAL = ("interro1", "interro2", "interro3", "devoir1", "devoir2")


def _eleve_de_lecole(db: Session, eleve_id: int, ecole_id: int) -> Eleve:
    e = db.get(Eleve, eleve_id)
    if e is None or e.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élève introuvable.")
    return e


def _matiere_de_lecole(db: Session, matiere_id: int, ecole_id: int) -> Matiere:
    m = db.get(Matiere, matiere_id)
    if m is None or m.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matière introuvable.")
    return m


def _trimestre_de_lecole(db: Session, trimestre_id: int, ecole_id: int) -> Trimestre:
    tri = db.get(Trimestre, trimestre_id)
    annee = db.get(AnneeScolaire, tri.annee_scolaire_id) if tri else None
    if tri is None or annee is None or annee.ecole_id != ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trimestre introuvable.")
    return tri


def _a_une_affectation(db: Session, enseignant_id: int, classe_id: int | None, matiere_id: int) -> bool:
    if classe_id is None:
        return False
    return db.scalar(
        select(EnseignantAffectation).where(
            EnseignantAffectation.enseignant_id == enseignant_id,
            EnseignantAffectation.classe_id == classe_id,
            EnseignantAffectation.matiere_id == matiere_id,
        )
    ) is not None


def _peut_saisir(db: Session, user: Utilisateur, eleve: Eleve, matiere: Matiere) -> bool:
    if user.role == "admin":
        return True
    if matiere.note_directe:
        return False   # la conduite est saisie par l'administration
    if user.role != "enseignant":
        return False
    return _a_une_affectation(db, user.id, eleve.classe_id, matiere.id)


def _vers_out(note: Note, matiere: Matiere) -> NoteOut:
    moyenne: float | None = None
    if matiere.note_directe:
        statut = "directe" if note.note_directe is not None else "sans_note"
        if note.note_directe is not None:
            moyenne = float(arrondi_affichage(note.note_directe))
    else:
        r = evaluer_matiere(
            note.matiere_id, 1,
            note.interro1, note.interro2, note.interro3, note.devoir1, note.devoir2,
        )
        if r.sans_note:
            statut = "sans_note"
        elif r.incomplete:
            statut = "incomplete"
        else:
            statut = "calculee"
            moyenne = float(arrondi_affichage(r.moyenne))

    return NoteOut(
        id=note.id,
        eleve_id=note.eleve_id,
        matiere_id=note.matiere_id,
        trimestre_id=note.trimestre_id,
        interro1=_f(note.interro1),
        interro2=_f(note.interro2),
        interro3=_f(note.interro3),
        devoir1=_f(note.devoir1),
        devoir2=_f(note.devoir2),
        note_directe=_f(note.note_directe),
        appreciation=note.appreciation,
        saisi_par=note.saisi_par,
        valide=note.valide,
        valide_par=note.valide_par,
        moyenne=moyenne,
        statut=statut,
    )


def _f(x) -> float | None:
    return float(x) if x is not None else None


@router.get("", response_model=list[NoteOut])
def lister_notes(
    user: CurrentUser,
    db: DbSession,
    classe_id: Annotated[int, Query()],
    trimestre_id: Annotated[int, Query()],
    matiere_id: int | None = None,
):
    classe = db.get(Classe, classe_id)
    if classe is None or classe.ecole_id != user.ecole_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classe introuvable.")
    _trimestre_de_lecole(db, trimestre_id, user.ecole_id)

    stmt = (
        select(Note)
        .join(Eleve, Eleve.id == Note.eleve_id)
        .where(Eleve.classe_id == classe_id, Note.trimestre_id == trimestre_id)
    )
    if matiere_id is not None:
        stmt = stmt.where(Note.matiere_id == matiere_id)

    if user.role != "admin":
        affectees = set(
            db.scalars(
                select(EnseignantAffectation.matiere_id).where(
                    EnseignantAffectation.enseignant_id == user.id,
                    EnseignantAffectation.classe_id == classe_id,
                )
            )
        )
        if matiere_id is not None and matiere_id not in affectees:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Matière non affectée.")
        stmt = stmt.where(Note.matiere_id.in_(affectees or {-1}))

    notes = list(db.scalars(stmt.order_by(Note.eleve_id, Note.matiere_id)))
    cache: dict[int, Matiere] = {}
    for n in notes:
        cache.setdefault(n.matiere_id, db.get(Matiere, n.matiere_id))
    return [_vers_out(n, cache[n.matiere_id]) for n in notes]


@router.get("/{note_id}", response_model=NoteOut)
def consulter_note(note_id: int, user: CurrentUser, db: DbSession):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note introuvable.")
    eleve = _eleve_de_lecole(db, note.eleve_id, user.ecole_id)
    matiere = db.get(Matiere, note.matiere_id)
    if user.role != "admin" and not _a_une_affectation(db, user.id, eleve.classe_id, note.matiere_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé.")
    return _vers_out(note, matiere)


@router.put("", response_model=NoteOut)
def enregistrer_note(data: NoteEcrire, user: CurrentUser, db: DbSession):
    eleve = _eleve_de_lecole(db, data.eleve_id, user.ecole_id)
    matiere = _matiere_de_lecole(db, data.matiere_id, user.ecole_id)
    _trimestre_de_lecole(db, data.trimestre_id, user.ecole_id)

    eval_fournis = {c: getattr(data, c) for c in CHAMPS_EVAL if getattr(data, c) is not None}
    if matiere.note_directe:
        if eval_fournis:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Matière à note directe : renseignez « note_directe », pas les interros/devoirs.",
            )
    elif data.note_directe is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cette matière se note par 3 interros + 2 devoirs, pas par une note directe.",
        )

    if not _peut_saisir(db, user, eleve, matiere):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas autorisé à saisir cette note.",
        )

    note = db.scalar(
        select(Note).where(
            Note.eleve_id == data.eleve_id,
            Note.matiere_id == data.matiere_id,
            Note.trimestre_id == data.trimestre_id,
        )
    )
    if note is not None and note.valide and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette note est validée et verrouillée. Demandez à l'administration.",
        )

    if note is None:
        note = Note(
            eleve_id=data.eleve_id, matiere_id=data.matiere_id, trimestre_id=data.trimestre_id
        )
        db.add(note)

    for champ in (*CHAMPS_EVAL, "note_directe", "appreciation"):
        setattr(note, champ, getattr(data, champ))
    note.saisi_par = user.id
    # toute modification du contenu invalide la validation précédente
    note.valide = False
    note.valide_par = None
    note.valide_le = None

    db.commit()
    db.refresh(note)
    return _vers_out(note, matiere)


@router.post("/{note_id}/validation", response_model=NoteOut, dependencies=[AdminOnly])
def valider_note(note_id: int, data: NoteValidation, user: CurrentUser, db: DbSession):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note introuvable.")
    _eleve_de_lecole(db, note.eleve_id, user.ecole_id)
    matiere = db.get(Matiere, note.matiere_id)

    if data.valide:
        note.valide = True
        note.valide_par = user.id
        note.valide_le = datetime.now(timezone.utc)
    else:
        note.valide = False
        note.valide_par = None
        note.valide_le = None
    db.commit()
    db.refresh(note)
    return _vers_out(note, matiere)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def supprimer_note(note_id: int, user: CurrentUser, db: DbSession):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note introuvable.")
    eleve = _eleve_de_lecole(db, note.eleve_id, user.ecole_id)

    if user.role != "admin":
        if note.valide or not _a_une_affectation(db, user.id, eleve.classe_id, note.matiere_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Suppression non autorisée.")
    db.delete(note)
    db.commit()
