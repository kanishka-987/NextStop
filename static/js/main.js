// static/js/main.js
// NextStop User Authentication UI helper scripts

document.addEventListener("DOMContentLoaded", () => {
    // 1. Password Visibility Toggle
    const togglePasswordBtn = document.getElementById("togglePassword");
    const passwordInput = document.getElementById("password");
    
    if (togglePasswordBtn && passwordInput) {
        togglePasswordBtn.addEventListener("click", () => {
            const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
            passwordInput.setAttribute("type", type);
            
            // Toggle eye icon class if using Bootstrap Icons
            const icon = togglePasswordBtn.querySelector("i");
            if (icon) {
                if (type === "text") {
                    icon.classList.remove("bi-eye");
                    icon.classList.add("bi-eye-slash");
                } else {
                    icon.classList.remove("bi-eye-slash");
                    icon.classList.add("bi-eye");
                }
            }
        });
    }

    // 2. Interactive Role Selection Cards/Tabs (Modern UI)
    const roleSelectors = document.querySelectorAll(".role-select-card");
    const roleHiddenInput = document.getElementById("roleHiddenInput");

    if (roleSelectors.length > 0 && roleHiddenInput) {
        roleSelectors.forEach(selector => {
            selector.addEventListener("click", () => {
                // Clear active class from all
                roleSelectors.forEach(s => s.classList.remove("active"));
                
                // Add active to current
                selector.classList.add("active");
                
                // Set the hidden input value
                const selectedRole = selector.getAttribute("data-role");
                roleHiddenInput.value = selectedRole;
            });
        });
    }

    // 3. Client-Side Form Validation (NextStop Form validation styling)
    const authForm = document.getElementById("authLoginForm");
    if (authForm) {
        authForm.addEventListener("submit", (event) => {
            let isValid = true;
            const email = document.getElementById("email");
            const password = document.getElementById("password");
            const role = document.getElementById("roleHiddenInput");
            
            // Basic inputs check
            if (email && email.value.trim() === "") {
                showValidationError(email, "Email address is required.");
                isValid = false;
            } else if (email) {
                clearValidationError(email);
            }
            
            if (password && password.value === "") {
                showValidationError(password, "Password is required.");
                isValid = false;
            } else if (password) {
                clearValidationError(password);
            }

            if (!isValid) {
                event.preventDefault(); // Stop form submission
            }
        });
    }
});

/**
 * Utility to display validation error class & feedback text
 */
function showValidationError(inputElement, message) {
    inputElement.classList.add("is-invalid");
    let feedback = inputElement.parentElement.querySelector(".invalid-feedback");
    if (!feedback) {
        feedback = document.createElement("div");
        feedback.className = "invalid-feedback";
        inputElement.parentElement.appendChild(feedback);
    }
    feedback.innerText = message;
}

/**
 * Utility to remove validation error indicators
 */
function clearValidationError(inputElement) {
    inputElement.classList.remove("is-invalid");
    const feedback = inputElement.parentElement.querySelector(".invalid-feedback");
    if (feedback) {
        feedback.remove();
    }
}
