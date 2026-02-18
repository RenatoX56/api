<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);
include 'db.php';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $user = $_POST['user'];
    $pass = md5($_POST['pass']); // Uso débil de MD5

    // VULNERABILIDAD: SQL Injection en Login (Auth Bypass)
    // Permite entrar con: admin' -- -
    $sql = "SELECT id, username FROM users WHERE username = '$user' AND password = '$pass'";
    $res = mysqli_query($conn, $sql);

    if ($res && mysqli_num_rows($res) > 0) {
        $row = mysqli_fetch_assoc($res);
        
        // ESTAS LÍNEAS SON VITALES:
        $_SESSION['user_id'] = $row['id'];
        $_SESSION['username'] = $row['username'];
        $_SESSION['role'] = $row['role']; // Guardamos el rol para mostrarlo

        // Redirigir al nuevo dashboard en lugar del index
        header('Location: dashboard.php'); 
        exit;
    } else {
        $error = 'Usuario o clave incorrectos.';
    }
}
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Login Lab</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #0b0e14; color: #e0e0e0; display: flex; align-items: center; justify-content: center; height: 100vh; }
        .card { background-color: #161b22; border: 1px solid #e94560; width: 100%; max-width: 400px; }
        .btn-primary { background-color: #e94560; border: none; width: 100%; }
        .btn-primary:hover { background-color: #ff2e63; }
        .form-control { background-color: #0d1117; border: 1px solid #30363d; color: white; }
        .form-control:focus { background-color: #0d1117; color: white; border-color: #e94560; box-shadow: 0 0 5px rgba(233, 69, 96, 0.5); }
    </style>
</head>
<body>
    <div class="card p-4 shadow text-white">
        <h3 class="text-center mb-4 text-danger fw-bold">ACCESO SOC</h3>
        <?php if ($error): ?>
            <div class="alert alert-danger text-center p-2"><?php echo $error; ?></div>
        <?php endif; ?>
        <form method="POST" autocomplete="off">
            <div class="mb-3">
                <label class="form-label">Usuario</label>
                <input type="text" name="user" class="form-control" placeholder="admin">
            </div>
            <div class="mb-3">
                <label class="form-label">Contraseña</label>
                <input type="password" name="pass" class="form-control" placeholder="••••••">
            </div>
            <button class="btn btn-primary fw-bold" type="submit">ENTRAR</button>
            <div class="text-center mt-3">
                <a href="index.php" class="text-secondary small text-decoration-none">Volver al foro</a>
            </div>
        </form>
    </div>
</body>
</html>