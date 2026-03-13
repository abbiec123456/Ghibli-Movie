function toggleAdminPassword() {
    const passwordField = document.getElementById("admin_password");
    passwordField.type = passwordField.type === "password" ? "text" : "password";
}