function toggleAdminPassword() {
    const passwordField = document.getElementById("admin_password");
    passwordField.type = passwordField.type === "password" ? "text" : "password";
}

function handleToggleKeyDown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleAdminPassword();
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("toggle-admin-password");
    if (toggle) {
        toggle.addEventListener("click", toggleAdminPassword);
        toggle.addEventListener("keydown", handleToggleKeyDown);
    }
});