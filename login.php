<?php
// login.php - Page de connexion
session_start();
require_once 'config/db.php';

// Vérifier si un admin existe, sinon rediriger vers install
$stmt = $pdo->query("SELECT COUNT(*) FROM utilisateurs");
$adminExiste = $stmt->fetchColumn();

if ($adminExiste == 0) {
    header('Location: install.php');
    exit();
}

// Si déjà connecté, rediriger vers accueil
if (isset($_SESSION['user_id'])) {
    header('Location: index.php');
    exit();
}

$erreur = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email']);
    $password = $_POST['password'];
    
    $stmt = $pdo->prepare("SELECT * FROM utilisateurs WHERE email = ?");
    $stmt->execute([$email]);
    $user = $stmt->fetch();
    
    if ($user && password_verify($password, $user['mot_de_passe'])) {
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['nom'] = $user['nom'];
        $_SESSION['email'] = $user['email'];
        $_SESSION['role'] = $user['role'];
        header('Location: index.php');
        exit();
    } else {
        $erreur = "Email ou mot de passe incorrect.";
    }
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connexion - Gestion Ecole</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #FCD116 0%, #008751 50%, #E8112D 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .login-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 450px;
            width: 100%;
            padding: 40px;
            animation: fadeIn 0.5s ease-out;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        h1 {
            text-align: center;
            color: #E8112D;
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .sous-titre {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        h2 {
            color: #008751;
            margin-bottom: 25px;
            text-align: center;
            font-size: 20px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
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
            background: #008751;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #006442;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .erreur {
            background: #F8D7DA;
            color: #721C24;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #E8112D;
        }
        
        .footer {
            margin-top: 25px;
            text-align: center;
            font-size: 12px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🏫 GestionEcole</h1>
        <div class="sous-titre">Collège Privé d'Enseignement Général "Sainte Jeanne d'Arc"</div>
        
        <h2>🔐 Connexion</h2>
        
        <?php if ($erreur): ?>
            <div class="erreur">❌ <?= htmlspecialchars($erreur) ?></div>
        <?php endif; ?>
        
        <form method="POST">
            <div class="form-group">
                <label>📧 Email</label>
                <input type="email" name="email" required placeholder="admin@ecole.com">
            </div>
            
            <div class="form-group">
                <label>🔒 Mot de passe</label>
                <input type="password" name="password" required>
            </div>
            
            <button type="submit">Se connecter</button>
        </form>
        
        <div class="footer">
            🇧🇯 Système éducatif béninois
        </div>
    </div>
</body>
</html>