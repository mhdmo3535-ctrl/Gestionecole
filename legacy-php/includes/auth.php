<?php
// includes/auth.php - Fonctions d'authentification
session_start();

function estConnecte() {
    return isset($_SESSION['user_id']);
}

function estSuperAdmin() {
    return isset($_SESSION['role']) && $_SESSION['role'] === 'super_admin';
}

function estAdmin() {
    return isset($_SESSION['role']) && ($_SESSION['role'] === 'admin' || $_SESSION['role'] === 'super_admin');
}

function verifierAcces() {
    if (!estConnecte()) {
        header('Location: login.php');
        exit();
    }
}

function verifierSuperAdmin() {
    verifierAcces();
    if (!estSuperAdmin()) {
        header('Location: index.php');
        exit();
    }
}
?>