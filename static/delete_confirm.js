document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".delete-form").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            const message = form.dataset.confirm || "Are you sure you want to delete this?";
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});