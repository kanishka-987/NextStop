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
    const roleTabs = document.querySelectorAll(".role-tab-btn, .role-select-card");
    const roleHiddenInput = document.getElementById("roleHiddenInput");
    const submitBtn = document.getElementById("submitBtn");

    function setRole(role) {
        if (!roleHiddenInput) return;
        roleHiddenInput.value = role;
        
        roleTabs.forEach(tab => {
            if (tab.getAttribute("data-role") === role) {
                tab.classList.add("active");
            } else {
                tab.classList.remove("active");
            }
        });

        if (submitBtn) {
            const capitalizedRole = role.charAt(0).toUpperCase() + role.slice(1);
            submitBtn.innerHTML = `<i class="bi bi-box-arrow-in-right me-2"></i> Login as ${capitalizedRole}`;
        }
    }

    if (roleTabs.length > 0 && roleHiddenInput) {
        // Initialize based on hidden input value
        setRole(roleHiddenInput.value);

        roleTabs.forEach(tab => {
            tab.addEventListener("click", () => {
                const selectedRole = tab.getAttribute("data-role");
                setRole(selectedRole);
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
