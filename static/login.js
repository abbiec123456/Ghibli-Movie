function togglePassword() {
    const password =
        document.getElementById("password");

    password.type =
        password.type === "password"
            ? "text"
            : "password";
}

function handleToggleKeyDown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        togglePassword();
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("toggle-password");
    if (toggle) {
        toggle.addEventListener("click", togglePassword);
        toggle.addEventListener("keydown", handleToggleKeyDown);
    }
});