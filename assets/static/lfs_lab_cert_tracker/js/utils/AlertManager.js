const validTypes = ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"];

// This Alert Manager is similar to the one from the inventory site
// Adapted for Bootstrap 4

export default class AlertManager {
    static stopEvent(message, event, element, alertContainer) {
        event.preventDefault();
        element.focus();
        AlertManager.showAlert(message, alertContainer);
    }

    // Shows a dismissible alert message in the specified container
    static showAlert(message, alertContainer, type = "danger") {
        if (!type || !validTypes.includes(type)) {
            type = "danger";
        }

        const className = `alert alert-${type} alert-dismissible fade show`;
        const existingAlert = document.querySelector(".alert");
        if (existingAlert) {
            existingAlert.remove();
        }
        const alertDiv = document.createElement("div");
        alertDiv.className = className;
        alertDiv.role = "alert";
        alertDiv.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>
    `;
        alertContainer.prepend(alertDiv);

        alertDiv.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}
