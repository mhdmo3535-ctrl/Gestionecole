import { api } from "./client";
import type {
  Absence,
  Affectation,
  AffectationClasse,
  AnneeScolaire,
  BulletinClasse,
  BulletinEleve,
  Classe,
  ClasseMatiere,
  Coefficient,
  Creneau,
  CreneauPayload,
  Discipline,
  Ecole,
  Eleve,
  InfosMedicales,
  LienParent,
  MatriceDroits,
  Matiere,
  ModePaiement,
  Paiement,
  Recu,
  SituationPaiements,
  SuiviPaiements,
  TableauDeBord,
  Tranche,
  Niveau,
  ParentTuteur,
  Note,
  NoteHistorique,
  Permission,
  PermissionEcole,
  ProgressionEleve,
  Role,
  Serie,
  StatutPermission,
  Trimestre,
  Utilisateur,
} from "./types";

// ---------- Authentification ----------

export async function login(email: string, motDePasse: string): Promise<string> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", motDePasse);
  const { data } = await api.post<{ access_token: string }>("/auth/login", form);
  return data.access_token;
}

export async function getMoi(): Promise<Utilisateur> {
  const { data } = await api.get<Utilisateur>("/auth/me");
  return data;
}

// ---------- Référentiel ----------

export const getMonEcole = () => api.get<Ecole>("/ecole").then((r) => r.data);
export const getNiveaux = () => api.get<Niveau[]>("/niveaux").then((r) => r.data);
export const getSeries = () => api.get<Serie[]>("/series").then((r) => r.data);
export const getAnneesScolaires = () =>
  api.get<AnneeScolaire[]>("/annees-scolaires").then((r) => r.data);
export const getTrimestres = (anneeScolaireId?: number) =>
  api
    .get<Trimestre[]>("/trimestres", { params: { annee_scolaire_id: anneeScolaireId } })
    .then((r) => r.data);

// ---------- Élèves ----------

export interface ElevePayload {
  matricule: string;
  nom: string;
  prenom: string;
  date_naissance?: string | null;
  sexe?: "M" | "F" | null;
  classe_id?: number | null;
}

export const getEleves = (params?: { q?: string; classe_id?: number }) =>
  api.get<Eleve[]>("/eleves", { params }).then((r) => r.data);
export const getEleve = (id: number) => api.get<Eleve>(`/eleves/${id}`).then((r) => r.data);

export const getInfosMedicales = (eleveId: number) =>
  api.get<InfosMedicales>(`/eleves/${eleveId}/infos-medicales`).then((r) => r.data);
export const enregistrerInfosMedicales = (
  eleveId: number,
  payload: Partial<Pick<InfosMedicales, "groupe_sanguin" | "allergies" | "contacts_urgence" | "remarques">>,
) => api.put<InfosMedicales>(`/eleves/${eleveId}/infos-medicales`, payload).then((r) => r.data);

export interface ParentPayload {
  nom: string;
  prenom: string;
  telephone?: string | null;
  email?: string | null;
  lien?: LienParent | null;
}
export const getParents = (eleveId: number) =>
  api.get<ParentTuteur[]>(`/eleves/${eleveId}/parents`).then((r) => r.data);
export const ajouterParent = (eleveId: number, payload: ParentPayload) =>
  api.post<ParentTuteur>(`/eleves/${eleveId}/parents`, payload).then((r) => r.data);
export const modifierParent = (eleveId: number, parentId: number, payload: Partial<ParentPayload>) =>
  api.patch<ParentTuteur>(`/eleves/${eleveId}/parents/${parentId}`, payload).then((r) => r.data);
export const retirerParent = (eleveId: number, parentId: number) =>
  api.delete(`/eleves/${eleveId}/parents/${parentId}`);

// ---------- Vie scolaire ----------

export const getAbsences = (eleveId: number) =>
  api.get<Absence[]>(`/eleves/${eleveId}/absences`).then((r) => r.data);
export const ajouterAbsence = (
  eleveId: number,
  payload: { date: string; type: "absence" | "retard"; matiere_id?: number | null; justifiee?: boolean },
) => api.post<Absence>(`/eleves/${eleveId}/absences`, payload).then((r) => r.data);
export const retirerAbsence = (eleveId: number, id: number) =>
  api.delete(`/eleves/${eleveId}/absences/${id}`);

export const getDiscipline = (eleveId: number) =>
  api.get<Discipline[]>(`/eleves/${eleveId}/discipline`).then((r) => r.data);
export const ajouterDiscipline = (
  eleveId: number,
  payload: {
    date?: string | null;
    description: string;
    gravite: "mineure" | "moyenne" | "grave";
    sanction?: string | null;
  },
) => api.post<Discipline>(`/eleves/${eleveId}/discipline`, payload).then((r) => r.data);
export const retirerDiscipline = (eleveId: number, id: number) =>
  api.delete(`/eleves/${eleveId}/discipline/${id}`);

export const getPermissions = (eleveId: number) =>
  api.get<Permission[]>(`/eleves/${eleveId}/permissions`).then((r) => r.data);
export const ajouterPermission = (
  eleveId: number,
  payload: { date_debut: string; date_fin: string; motif: string },
) => api.post<Permission>(`/eleves/${eleveId}/permissions`, payload).then((r) => r.data);
export const getAutorisationsEcole = () =>
  api.get<PermissionEcole[]>("/autorisations-absence").then((r) => r.data);
export const traiterPermission = (
  eleveId: number,
  id: number,
  payload: { statut: StatutPermission; commentaire_traitement?: string | null },
) => api.patch<Permission>(`/eleves/${eleveId}/permissions/${id}`, payload).then((r) => r.data);
export const retirerPermission = (eleveId: number, id: number) =>
  api.delete(`/eleves/${eleveId}/permissions/${id}`);
export const creerEleve = (payload: ElevePayload) =>
  api.post<Eleve>("/eleves", payload).then((r) => r.data);
export const modifierEleve = (id: number, payload: Partial<ElevePayload> & { statut?: string }) =>
  api.patch<Eleve>(`/eleves/${id}`, payload).then((r) => r.data);

// ---------- Classes ----------

export interface ClassePayload {
  nom: string;
  niveau_id: number;
  serie_id?: number | null;
  annee_scolaire_id?: number | null;
  professeur_principal_id?: number | null;
}

export const getClasses = (params?: { annee_scolaire_id?: number; niveau_id?: number }) =>
  api.get<Classe[]>("/classes", { params }).then((r) => r.data);
export const getClasse = (id: number) => api.get<Classe>(`/classes/${id}`).then((r) => r.data);
export const creerClasse = (payload: ClassePayload) =>
  api.post<Classe>("/classes", payload).then((r) => r.data);
export const modifierClasse = (id: number, payload: Partial<ClassePayload>) =>
  api.patch<Classe>(`/classes/${id}`, payload).then((r) => r.data);
export const supprimerClasse = (id: number) => api.delete(`/classes/${id}`);
export const getElevesDeLaClasse = (id: number) =>
  api.get<Eleve[]>(`/classes/${id}/eleves`).then((r) => r.data);
export const getMatieresDeLaClasse = (id: number) =>
  api.get<ClasseMatiere[]>(`/classes/${id}/matieres`).then((r) => r.data);

// ---------- Matières ----------

export const getMatieres = () => api.get<Matiere[]>("/matieres").then((r) => r.data);
export const getMatiere = (id: number) => api.get<Matiere>(`/matieres/${id}`).then((r) => r.data);
export const creerMatiere = (payload: {
  nom: string;
  code?: string | null;
  note_directe?: boolean;
  est_choix_langue?: boolean;
  evaluee?: boolean;
}) => api.post<Matiere>("/matieres", payload).then((r) => r.data);
export const modifierMatiere = (
  id: number,
  payload: Partial<{
    nom: string;
    code: string | null;
    note_directe: boolean;
    est_choix_langue: boolean;
    evaluee: boolean;
  }>,
) => api.patch<Matiere>(`/matieres/${id}`, payload).then((r) => r.data);
export const supprimerMatiere = (id: number) => api.delete(`/matieres/${id}`);

export const getCoefficients = (matiereId: number) =>
  api.get<Coefficient[]>(`/matieres/${matiereId}/coefficients`).then((r) => r.data);
export const declarerCoefficient = (
  matiereId: number,
  payload: { niveau_id?: number | null; serie_id?: number | null; coefficient: number },
) => api.put<Coefficient>(`/matieres/${matiereId}/coefficients`, payload).then((r) => r.data);
export const retirerCoefficient = (matiereId: number, coefficientId: number) =>
  api.delete(`/matieres/${matiereId}/coefficients/${coefficientId}`);

export const getDroits = () => api.get<MatriceDroits>("/auth/droits").then((r) => r.data);

// ---------- Utilisateurs & affectations ----------

export interface UtilisateurPayload {
  nom: string;
  prenom: string;
  email: string;
  mot_de_passe: string;
  roles: Role[];
  telephone?: string | null;
}

export const getUtilisateurs = (params?: { role?: string; actif?: boolean }) =>
  api.get<Utilisateur[]>("/utilisateurs", { params }).then((r) => r.data);
export const getUtilisateur = (id: number) =>
  api.get<Utilisateur>(`/utilisateurs/${id}`).then((r) => r.data);
export const creerUtilisateur = (payload: UtilisateurPayload) =>
  api.post<Utilisateur>("/utilisateurs", payload).then((r) => r.data);
export const modifierUtilisateur = (
  id: number,
  payload: Partial<Omit<UtilisateurPayload, "mot_de_passe" | "email">> & { actif?: boolean },
) => api.patch<Utilisateur>(`/utilisateurs/${id}`, payload).then((r) => r.data);
export const reinitialiserMotDePasse = (id: number, nouveau: string) =>
  api.put(`/utilisateurs/${id}/mot-de-passe`, { nouveau_mot_de_passe: nouveau });

export const getAffectations = (enseignantId: number) =>
  api.get<Affectation[]>(`/utilisateurs/${enseignantId}/affectations`).then((r) => r.data);
export const ajouterAffectation = (
  enseignantId: number,
  payload: { classe_id: number; matiere_id: number },
) => api.post<Affectation>(`/utilisateurs/${enseignantId}/affectations`, payload).then((r) => r.data);
export const retirerAffectation = (enseignantId: number, affectationId: number) =>
  api.delete(`/utilisateurs/${enseignantId}/affectations/${affectationId}`);

// ---------- Notes ----------

export interface NotePayload {
  eleve_id: number;
  matiere_id: number;
  trimestre_id: number;
  interro1?: number | null;
  interro2?: number | null;
  interro3?: number | null;
  devoir1?: number | null;
  devoir2?: number | null;
  note_directe?: number | null;
  appreciation?: string | null;
}

export const getNotes = (params: {
  classe_id: number;
  trimestre_id: number;
  matiere_id?: number;
}) => api.get<Note[]>("/notes", { params }).then((r) => r.data);
export const enregistrerNote = (payload: NotePayload) =>
  api.put<Note>("/notes", payload).then((r) => r.data);
export const supprimerNote = (noteId: number) => api.delete(`/notes/${noteId}`);
export const getHistoriqueNotes = (params: {
  classe_id?: number;
  eleve_id?: number;
  trimestre_id?: number;
  matiere_id?: number;
}) => api.get<NoteHistorique[]>("/notes/historique", { params }).then((r) => r.data);

// ---------- Bulletins ----------

export const getBulletinsClasse = (classeId: number, trimestreId: number) =>
  api
    .get<BulletinClasse>(`/classes/${classeId}/bulletins`, {
      params: { trimestre_id: trimestreId },
    })
    .then((r) => r.data);
export const getBulletinEleve = (eleveId: number, trimestreId: number) =>
  api
    .get<BulletinEleve>(`/eleves/${eleveId}/bulletin`, { params: { trimestre_id: trimestreId } })
    .then((r) => r.data);
export const getProgressionEleve = (eleveId: number) =>
  api.get<ProgressionEleve>(`/eleves/${eleveId}/progression`).then((r) => r.data);

// ---------- Paiements ----------

export interface TranchePayload {
  libelle?: string | null;
  montant: number;
  date_limite?: string | null;
  annee_scolaire_id?: number;
}

export const getTranches = (anneeScolaireId?: number) =>
  api
    .get<Tranche[]>("/paiements/tranches", { params: { annee_scolaire_id: anneeScolaireId } })
    .then((r) => r.data);
export const creerTranche = (payload: TranchePayload) =>
  api.post<Tranche>("/paiements/tranches", payload).then((r) => r.data);
export const modifierTranche = (id: number, payload: Partial<TranchePayload>) =>
  api.patch<Tranche>(`/paiements/tranches/${id}`, payload).then((r) => r.data);
export const supprimerTranche = (id: number) => api.delete(`/paiements/tranches/${id}`);

export const getSituationPaiements = (eleveId: number) =>
  api.get<SituationPaiements>(`/eleves/${eleveId}/paiements`).then((r) => r.data);
export const enregistrerPaiement = (
  eleveId: number,
  payload: { tranche_id: number; montant_paye: number; date_paiement?: string; mode_paiement: ModePaiement },
) => api.post<Paiement>(`/eleves/${eleveId}/paiements`, payload).then((r) => r.data);
export const annulerPaiement = (eleveId: number, paiementId: number) =>
  api.delete(`/eleves/${eleveId}/paiements/${paiementId}`);
export const getRecu = (paiementId: number) =>
  api.get<Recu>(`/paiements/${paiementId}/recu`).then((r) => r.data);
export const getSuiviPaiements = (params: { annee_scolaire_id?: number; classe_id?: number }) =>
  api.get<SuiviPaiements>("/paiements/suivi", { params }).then((r) => r.data);

// ---------- Tableau de bord ----------

export const getTableauDeBord = (trimestreId?: number) =>
  api
    .get<TableauDeBord>("/tableau-de-bord", { params: { trimestre_id: trimestreId } })
    .then((r) => r.data);

// ---------- Emploi du temps ----------

export const getEmploiDuTemps = (params: { classe_id?: number; enseignant_id?: number }) =>
  api.get<Creneau[]>("/emploi-du-temps", { params }).then((r) => r.data);
export const ajouterCreneau = (payload: CreneauPayload) =>
  api.post<Creneau>("/emploi-du-temps", payload).then((r) => r.data);
export const modifierCreneau = (id: number, payload: Partial<Omit<CreneauPayload, "classe_id">>) =>
  api.patch<Creneau>(`/emploi-du-temps/${id}`, payload).then((r) => r.data);
export const supprimerCreneau = (id: number) => api.delete(`/emploi-du-temps/${id}`);
export const getAffectationsDeLaClasse = (classeId: number) =>
  api.get<AffectationClasse[]>(`/classes/${classeId}/affectations`).then((r) => r.data);

