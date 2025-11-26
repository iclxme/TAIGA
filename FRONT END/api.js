// Configuración de la API
const API_BASE_URL = "http://localhost:8000/api";

// ==================== GESTIÓN DE SESIONES ====================
let inactivityTimer = null;
const INACTIVITY_TIMEOUT = 10 * 60 * 1000; // 10 minutos

// Inicializar monitoreo de inactividad
function initializeSessionMonitoring() {
    // Solo inicializar si NO hay "recordar sesion"
    if (!localStorage.getItem('rememberDevice')) {
        setupInactivityMonitoring();
    }
}

function setupInactivityMonitoring() {
    // Limpiar timer anterior si existe
    if (inactivityTimer) {
        clearTimeout(inactivityTimer);
    }

    // Configurar nuevo timer
    inactivityTimer = setTimeout(() => {
        // Auto-logout después de 10 min de inactividad
        logout();
    }, INACTIVITY_TIMEOUT);
}

function resetInactivityTimer() {
    // Solo resetear si el usuario está logueado y NO tiene "recordar sesion"
    if (isUserLoggedIn() && !localStorage.getItem('rememberDevice')) {
        setupInactivityMonitoring();
    }
}

// Monitorear eventos de actividad del usuario
document.addEventListener('click', resetInactivityTimer);
document.addEventListener('keypress', resetInactivityTimer);
document.addEventListener('mousemove', resetInactivityTimer);
document.addEventListener('scroll', resetInactivityTimer);
document.addEventListener('touchstart', resetInactivityTimer);

// Inicializar al cargar la página
document.addEventListener('DOMContentLoaded', initializeSessionMonitoring);

// ==================== UTILIDADES ====================
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        "Content-Type": "application/json",
        ...options.headers
    };

    // Agregar token si existe
    const token = localStorage.getItem("access_token");
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        const data = await response.json();

        if (!response.ok) {
            // Lanzar error con el mensaje del servidor
            const errorMessage = data.detail || data.message || "Error en la solicitud";
            throw new Error(errorMessage);
        }

        // Si el token expiró
        if (response.status === 401 && !endpoint.includes("login") && !endpoint.includes("register")) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("currentUser");
            window.location.href = "inicio_sesion.html";
        }

        return data;
    } catch (error) {
        console.error("Error:", error);
        throw error;
    }
}

// ==================== AUTENTICACIÓN ====================
async function register(email, username, password, fullName = "") {
    try {
        const response = await fetchAPI("/auth/register", {
            method: "POST",
            body: JSON.stringify({
                email,
                username,
                password,
                full_name: fullName
            })
        });
        return response;
    } catch (error) {
        throw error;
    }
}

async function login(email, password) {
    try {
        const response = await fetchAPI("/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email,
                password
            })
        });

        // Guardar token y usuario
        localStorage.setItem("access_token", response.access_token);
        localStorage.setItem("currentUser", JSON.stringify(response.user));

        return response;
    } catch (error) {
        throw error;
    }
}

async function getCurrentUser() {
    try {
        return await fetchAPI("/auth/me");
    } catch (error) {
        throw error;
    }
}

async function updateProfile(fullName) {
    try {
        return await fetchAPI("/auth/update-profile", {
            method: "PUT",
            body: JSON.stringify({
                full_name: fullName
            })
        });
    } catch (error) {
        throw error;
    }
}

async function changePassword(oldPassword, newPassword) {
    try {
        return await fetchAPI("/auth/change-password", {
            method: "POST",
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword
            })
        });
    } catch (error) {
        throw error;
    }
}

async function deleteAccount(password) {
    try {
        return await fetchAPI("/auth/delete-account", {
            method: "DELETE",
            body: JSON.stringify({
                password: password
            })
        });
    } catch (error) {
        throw error;
    }
}

function logout() {
    // Limpiar timer de inactividad
    if (inactivityTimer) {
        clearTimeout(inactivityTimer);
    }
    
    localStorage.removeItem("access_token");
    localStorage.removeItem("currentUser");
    localStorage.removeItem("rememberDevice");
    window.location.href = "index.html";
}

function isUserLoggedIn() {
    return !!localStorage.getItem("access_token");
}

function getCurrentUserData() {
    const userData = localStorage.getItem("currentUser");
    return userData ? JSON.parse(userData) : null;
}

function isAdmin() {
    const user = getCurrentUserData();
    return user && user.role === "admin";
}

// ==================== PRODUCTOS ====================
async function getProducts() {
    return fetchAPI("/products");
}

async function getProduct(productId) {
    return fetchAPI(`/products/${productId}`);
}

async function createProduct(name, category, price, description, image = null) {
    return fetchAPI("/products", {
        method: "POST",
        body: JSON.stringify({
            name,
            category,
            price,
            description,
            image
        })
    });
}

async function updateProduct(productId, data) {
    return fetchAPI(`/products/${productId}`, {
        method: "PUT",
        body: JSON.stringify(data)
    });
}

async function deleteProduct(productId) {
    return fetchAPI(`/products/${productId}`, {
        method: "DELETE"
    });
}

// ==================== ADMIN ====================
async function getAllUsers() {
    return fetchAPI("/admin/users");
}

async function updateUserRole(userId, newRole) {
    return fetchAPI(`/admin/users/${userId}/role`, {
        method: "PUT",
        body: JSON.stringify({ new_role: newRole })
    });
}

async function toggleUserActive(userId) {
    return fetchAPI(`/admin/users/${userId}/toggle-active`, {
        method: "PUT"
    });
}

// ==================== VERIFICACIÓN DE AUTENTICACIÓN EN PÁGINAS ====================
function checkAuthAndRedirect(requireAdmin = false) {
    if (!isUserLoggedIn()) {
        window.location.href = "inicio_sesion.html";
        return false;
    }

    if (requireAdmin && !isAdmin()) {
        alert("Acceso denegado: se requieren permisos de administrador");
        window.location.href = "index.html";
        return false;
    }

    return true;
}
