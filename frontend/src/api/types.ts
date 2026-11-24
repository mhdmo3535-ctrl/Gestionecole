export type Role = "admin" | "enseignant" | "parent" | "eleve";

export interface Utilisateur {
  id: number;
  ecole_id: number;
  nom: string;
  prenom: string;
  email: string;
  role: Role;
  telephone: string | null;
  actif: boolean;
}

export interface Ecole {
  id: number;
  nom: string;
  sigle: string | null;
  adresse: string | null;
  telephone: string | null;
  email: string | null;
  mode_calcul_moyenne_annuelle: string;
  est_pilote: boolean;
}

export interface Niveau {
  id: number;
  nom: string;
  cycle: "college" | "lycee";
}

export interface Serie {
  id: number;
  nom: string;
}

export interface AnneeScolaire {
  id: number;
  ecole_id: number;
  libelle: string;
  date_debut: string;
  date_fin: string;
  active: boolean;
}

export interface Trimestre {
  id: number;
  annee_scolaire_id: number;
  numero: number;
  date_debut: string | null;
  date_fin: string | null;
}

export interface Classe {
  id: number;
  ecole_id: number;
  nom: string;
  niveau_id: number;
  niveau_nom: string;
  cycle: "college" | "lycee";
  serie_id: number | null;
  serie_nom: string | null;
  annee_scolaire_id: number;
  annee_libelle: string;
  effectif: number;
  professeur_principal_id: number | null;
  professeur_principal_nom: string | null;
}

export interface ClasseMatiere {
  matiere_id: number;
  nom: string;
  note_directe: boolean;
  coefficient: number;
}

export interface Eleve {
  id: number;
  ecole_id: number;
  matricule: string;
  nom: string;
  prenom: string;
  date_naissance: string | null;
  sexe: "M" | "F" | null;
  classe_id: number | null;
  statut: "actif" | "archive" | "redoublant";
}

export interface InfosMedicales {
  eleve_id: number;
  groupe_sanguin: string | null;
  allergies: string | null;
  contacts_urgence: string | null;
  remarques: string | null;
  updated_at: string | null;
  updated_par: number | null;
}

export interface Absence {
  id: number;
  eleve_id: number;
  date: string;
  type: "absence" | "retard";
  matiere_id: number | null;
  justifiee: boolean;
  permission_id: number | null;
}

export interface Discipline {
  id: number;
  eleve_id: number;
  date: string;
  description: string;
  gravite: "mineure" | "moyenne" | "grave";
  sanction: string | null;
}

export type StatutPermission = "en_attente" | "approuve" | "rejete";

export interface Permission {
  id: number;
  eleve_id: number;
  date_debut: string;
  date_fin: string;
  motif: string;
  statut: StatutPermission;
  commentaire_traitement: string | null;
  traite_le: string | null;
}

export type LienParent = "pere" | "mere" | "tuteur";

export interface ParentTuteur {
  parent_id: number;
  nom: string;
  prenom: string;
  telephone: string | null;
  email: string | null;
  lien: LienParent | null;
  a_un_compte: boolean;
}

export interface Matiere {
  id: number;
  ecole_id: number;
  nom: string;
  code: string | null;
  est_choix_langue: boolean;
  note_directe: boolean;
}

export interface Coefficient {
  id: number;
  matiere_id: number;
  niveau_id: number | null;
  serie_id: number | null;
  coefficient: number;
}

export interface Affectation {
  id: number;
  enseignant_id: number;
  classe_id: number;
  classe_nom: string;
  matiere_id: number;
  matiere_nom: string;
}

export type NoteStatut = "sans_note" | "incomplete" | "calculee" | "directe";

export interface Note {
  id: number;
  eleve_id: number;
  matiere_id: number;
  trimestre_id: number;
  interro1: number | null;
  interro2: number | null;
  interro3: number | null;
  devoir1: number | null;
  devoir2: number | null;
  note_directe: number | null;
  appreciation: string | null;
  saisi_par: number | null;
  moyenne: number | null;
  statut: NoteStatut;
}

export interface BulletinLigne {
  matiere_id: number;
  matiere_nom: string;
  coefficient: number;
  note_directe: boolean;
  moyenne: number | null;
  moyenne_affichee: string | null;
  moyenne_coefficientee: number | null;
  rang: number | null;
  statut: NoteStatut;
  appreciation: string | null;
}

export interface BulletinEleve {
  eleve_id: number;
  matricule: string;
  nom: string;
  prenom: string;
  classe_id: number;
  classe_nom: string;
  trimestre_id: number;
  trimestre_numero: number;
  lignes: BulletinLigne[];
  moyenne_generale: number | null;
  moyenne_generale_affichee: string | null;
  rang: number | null;
  effectif_classe: number;
  mode_calcul_annuel: string;
  moyenne_annuelle: number | null;
  moyenne_annuelle_affichee: string | null;
  decision: "admis" | "redouble" | null;
}

export interface BulletinClasseLigne {
  eleve_id: number;
  matricule: string;
  nom: string;
  prenom: string;
  moyenne_generale: number | null;
  moyenne_generale_affichee: string | null;
  rang: number | null;
  moyenne_annuelle: number | null;
  decision: "admis" | "redouble" | null;
}

export interface BulletinClasse {
  classe_id: number;
  classe_nom: string;
  trimestre_id: number;
  trimestre_numero: number;
  effectif_classe: number;
  eleves: BulletinClasseLigne[];
}

export interface ProgressionPoint {
  trimestre_id: number;
  trimestre_numero: number;
  moyenne_generale: number | null;
  moyenne_generale_affichee: string | null;
}

export interface ProgressionEleve {
  eleve_id: number;
  classe_id: number;
  classe_nom: string;
  points: ProgressionPoint[];
}

// ---------- Paiements ----------

export type ModePaiement = "especes" | "mobile_money" | "virement" | "cheque";
export type StatutTranche = "solde" | "partiel" | "non_paye" | "en_retard";
export type StatutPaiementEleve = StatutTranche | "aucune_tranche";

export interface Tranche {
  id: number;
  annee_scolaire_id: number;
  numero: number;
  libelle: string;
  montant: number;
  date_limite: string | null;
  nb_paiements: number;
}

export interface Paiement {
  id: number;
  eleve_id: number;
  tranche_id: number;
  tranche_libelle: string;
  montant_paye: number;
  date_paiement: string;
  mode_paiement: ModePaiement | null;
  numero_recu: string | null;
  enregistre_par_nom: string | null;
  created_at: string;
}

export interface SituationTranche {
  tranche_id: number;
  numero: number;
  libelle: string;
  montant: number;
  date_limite: string | null;
  paye: number;
  reste: number;
  statut: StatutTranche;
}

export interface SituationPaiements {
  eleve_id: number;
  annee_scolaire_id: number | null;
  annee_libelle: string | null;
  total_du: number;
  total_paye: number;
  reste: number;
  statut: StatutPaiementEleve;
  tranches: SituationTranche[];
  paiements: Paiement[];
}

export interface Recu {
  paiement: Paiement;
  ecole_nom: string;
  ecole_sigle: string | null;
  ecole_adresse: string | null;
  ecole_telephone: string | null;
  annee_libelle: string;
  eleve_matricule: string;
  eleve_nom: string;
  eleve_prenom: string;
  classe_nom: string | null;
  tranche_montant: number;
  tranche_reste_apres: number;
  total_du: number;
  total_paye_a_date: number;
  reste_global: number;
}

export interface SuiviLigne {
  eleve_id: number;
  matricule: string;
  nom: string;
  prenom: string;
  classe_id: number;
  classe_nom: string;
  total_du: number;
  total_paye: number;
  reste: number;
  statut: StatutPaiementEleve;
  dernier_paiement: string | null;
}

export interface SuiviPaiements {
  annee_scolaire_id: number;
  annee_libelle: string;
  nb_tranches: number;
  total_attendu: number;
  total_encaisse: number;
  reste: number;
  nb_eleves: number;
  nb_soldes: number;
  nb_en_retard: number;
  lignes: SuiviLigne[];
}

export type ValeursNote = Partial<
  Record<"interro1" | "interro2" | "interro3" | "devoir1" | "devoir2" | "note_directe", number | null>
> & { appreciation?: string | null };

export interface NoteHistorique {
  id: number;
  note_id: number | null;
  eleve_id: number;
  eleve_nom: string;
  matiere_id: number;
  matiere_nom: string;
  trimestre_id: number;
  action: "creation" | "modification" | "suppression";
  anciennes_valeurs: ValeursNote | null;
  nouvelles_valeurs: ValeursNote | null;
  auteur_id: number | null;
  auteur_nom: string | null;
  le: string;
}
