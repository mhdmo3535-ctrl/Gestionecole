<?php
// install.php - Création du premier administrateur (Super Admin)
require_once 'config/db.php';

// Vérifier si un utilisateur existe déjà
$stmt = $pdo->query("SELECT COUNT(*) FROM utilisateurs");
$userExiste = $stmt->fetchColumn();

if ($userExiste > 0) {
    header('Location: login.php');
    exit();
}

$erreur = '';
$succes = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $nom = trim($_POST['nom']);
    $email = trim($_POST['email']);
    $password = $_POST['password'];
    $confirm = $_POST['confirm_password'];
    
    if (empty($nom) || empty($email) || empty($password)) {
        $erreur = "Tous les champs sont obligatoires.";
    } elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $erreur = "Email invalide.";
    } elseif (strlen($password) < 6) {
        $erreur = "Le mot de passe doit contenir au moins 6 caractères.";
    } elseif ($password !== $confirm) {
        $erreur = "Les mots de passe ne correspondent pas.";
    } else {
        $hash = password_hash($password, PASSWORD_DEFAULT);
        $stmt = $pdo->prepare("INSERT INTO utilisateurs (nom, email, mot_de_passe, role) VALUES (?, ?, ?, 'super_admin')");
        
        if ($stmt->execute([$nom, $email, $hash])) {
            $succes = "Compte Super Administrateur créé avec succès ! Redirection...";
            header('refresh:3;url=login.php');
        } else {
            $erreur = "Erreur lors de la création.";
        }
    }
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Installation - Gestion Ecole</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-image: url('https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Flag_of_Benin.svg/1920px-Flag_of_Benin.svg.png');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            position: relative;
        }
        
        body::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            z-index: 0;
        }
        
        .install-container {
            position: relative;
            z-index: 1;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
            max-width: 550px;
            width: 100%;
            padding: 40px;
            animation: fadeIn 0.6s ease-out;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: scale(0.95);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }
        
        .flag-stripes {
            height: 5px;
            background: linear-gradient(90deg, #FCD116 0%, #FCD116 33%, #E8112D 33%, #E8112D 66%, #008751 66%, #008751 100%);
            border-radius: 5px;
            margin-bottom: 25px;
        }
        
        h1 {
            text-align: center;
            color: #E8112D;
            font-size: 28px;
            margin-bottom: 5px;
        }
        
        .sous-titre {
            text-align: center;
            color: #666;
            margin-bottom: 25px;
            font-size: 14px;
        }
        
        h2 {
            color: #008751;
            margin-bottom: 20px;
            font-size: 22px;
            text-align: center;
        }
        
        .warning {
            background: #FFF3CD;
            border-left: 4px solid #FCD116;
            padding: 15px;
            margin-bottom: 25px;
            font-size: 14px;
            color: #856404;
            border-radius: 8px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        
        input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #FCD116;
            box-shadow: 0 0 0 3px rgba(252, 209, 22, 0.2);
        }
        
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #008751, #006442);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0,135,81,0.4);
        }
        
        .erreur {
            background: #F8D7DA;
            color: #721C24;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #E8112D;
        }
        
        .succes {
            background: #D4EDDA;
            color: #155724;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #008751;
            text-align: center;
        }
        
        .footer {
            margin-top: 25px;
            text-align: center;
            font-size: 12px;
            color: #999;
        }
        
        .benin-icon {
            text-align: center;
            font-size: 40px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="install-container">
        <div class="flag-stripes"></div>
        <div class="benin-icon">🇧🇯</div>
        <h1>🏫 GestionEcole</h1>
        <div class="sous-titre">Collège Privé d'Enseignement Général "Sainte Jeanne d'Arc"</div>
        
        <h2>⚙️ Installation - Premier Administrateur</h2>
        
        <div class="warning">
            <strong>⚠️ Configuration initiale</strong><br>
            Vous allez créer le premier compte administrateur de l'application.<br>
            Cet utilisateur aura les droits <strong>Super Administrateur</strong> et pourra gérer d'autres administrateurs.
        </div>
        
        <?php if ($erreur): ?>
            <div class="erreur">❌ <?= htmlspecialchars($erreur) ?></div>
        <?php endif; ?>
        
        <?php if ($succes): ?>
            <div class="succes">✅ <?= htmlspecialchars($succes) ?></div>
        <?php endif; ?>
        
        <form method="POST">
            <div class="form-group">
                <label>👤 Nom complet</label>
                <input type="text" name="nom" required placeholder="Ex: Jean KPODA">
            </div>
            
            <div class="form-group">
                <label>📧 Email</label>
                <input type="email" name="email" required placeholder="admin@ecole-saintejeanne.bj">
            </div>
            
            <div class="form-group">
                <label>🔒 Mot de passe (minimum 6 caractères)</label>
                <input type="password" name="password" required minlength="6">
            </div>
            
            <div class="form-group">
                <label>🔒 Confirmer le mot de passe</label>
                <input type="password" name="confirm_password" required minlength="6">
            </div>
            
            <button type="submit">🚀 Créer le compte Super Administrateur</button>
        </form>
        
        <div class="footer">
            🇧🇯 République du Bénin - Ministère des Enseignements Secondaires
        </div>
    </div>
</body>
</html>