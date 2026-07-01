-- Création de la base de données
CREATE DATABASE IF NOT EXISTS gestion_ecole;
USE gestion_ecole;

-- Table des classes
CREATE TABLE classes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(50) NOT NULL,
    avec_coefficients BOOLEAN DEFAULT 0
);

-- Table des élèves
CREATE TABLE eleves (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    classe_id INT,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE SET NULL
);

-- Table des matières
CREATE TABLE matieres (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(100) NOT NULL,
    classe_id INT,
    coefficient DECIMAL(3,1) DEFAULT 1,
    FOREIGN KEY (classe_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- Table des notes
CREATE TABLE notes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    eleve_id INT NOT NULL,
    matiere_id INT NOT NULL,
    periode INT NOT NULL,
    interro1 DECIMAL(4,2),
    interro2 DECIMAL(4,2),
    interro3 DECIMAL(4,2),
    devoir1 DECIMAL(4,2),
    devoir2 DECIMAL(4,2),
    FOREIGN KEY (eleve_id) REFERENCES eleves(id) ON DELETE CASCADE,
    FOREIGN KEY (matiere_id) REFERENCES matieres(id) ON DELETE CASCADE
);

-- Table des utilisateurs (Authentification)
CREATE TABLE utilisateurs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nom VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    mot_de_passe VARCHAR(255) NOT NULL,
    role ENUM('admin') DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertion des classes par défaut
INSERT INTO classes (nom, avec_coefficients) VALUES
('6e', 0),
('5e', 0),
('4e', 1),
('3e', 1),
('Seconde', 1),
('Première', 1),
('Terminale', 1);

-- AUCUN ADMIN PAR DÉFAUT (sécurité)