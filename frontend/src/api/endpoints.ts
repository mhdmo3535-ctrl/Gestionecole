import { api } from "./client";
import type {
  Affectation,
  AnneeScolaire,
  BulletinClasse,
  BulletinEleve,
  Classe,
  ClasseMatiere,
  Eleve,
  Matiere,
  Niveau,
  Note,
  Serie,
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
}

export const getClasses = (params?: { annee_scolaire_id?: number; niveau_id?: number }) =>
  api.get<Classe[]>("/classes", { params }).then((r) => r.data);
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
export const creerMatiere = (payload: {
  nom: string;
  note_directe?: boolean;
  est_choix_langue?: boolean;
}) => api.post<Matiere>("/matieres", payload).then((r) => r.data);
export const modifierMatiere = (id: number, payload: Partial<{ nom: string }>) =>
  api.patch<Matiere>(`/matieres/${id}`, payload).then((r) => r.data);
export const supprimerMatiere = (id: number) => api.delete(`/matieres/${id}`);

// ---------- Utilisateurs & affectations ----------

export interface UtilisateurPayload {
  nom: string;
  prenom: string;
  email: string;
  mot_de_passe: string;
  role: "admin" | "enseignant";
  telephone?: string | null;
}

export const getUtilisateurs = (params?: { role?: string; actif?: boolean }) =>
  api.get<Utilisateur[]>("/utilisateurs", { params }).then((r) => r.data);
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
export const validerNote = (noteId: number, valide: boolean) =>
  api.post<Note>(`/notes/${noteId}/validation`, { valide }).then((r) => r.data);
export const supprimerNote = (noteId: number) => api.delete(`/notes/${noteId}`);

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
