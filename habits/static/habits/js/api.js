// Reads the csrftoken cookie Django sets on every response
function getCsrfToken() {
    return document.cookie
        .split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('csrftoken='))
        ?.split('=')[1] ?? '';
}
    
// Every fetch in the app goes through here
async function apiFetch(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const mutating = ['POST', 'PATCH', 'PUT', 'DELETE'].includes(method);

    const response = await fetch(path, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(mutating ? { 'X-CSRFToken': getCsrfToken() } : {}),
            ...options.headers,
        },
        credentials: 'same-origin',  // sends session cookie with every request
    });

    if (response.status === 401 || response.status === 403) {
        // Not on the login page already — redirect
        if (!window.location.pathname.startsWith('/login')) {
            window.location.href = '/login/';
        }
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Unauthorized');
    }

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed: ${response.status}`);
    }

    if (response.status === 204) return null;
    return response.json();
}

// Auth
const auth = {
    login: (username, password) =>
        apiFetch('/api/v1/auth/login/', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        }),

    logout: () =>
        apiFetch('/api/v1/auth/logout/', { method: 'POST' }),

    me: () =>
        apiFetch('/api/v1/auth/me/'),

    register: (username, email, password) =>
        apiFetch('/api/v1/auth/register/', {
            method: 'POST',
            body: JSON.stringify({ username, email, password }),
        }),
};

// Habits
const habits = {
    list: (params = {}) => {
        const query = new URLSearchParams(params).toString();
        return apiFetch(`/api/v1/habits/${query ? '?' + query : ''}`);
    },
    create: (task_specification, periodicity) =>
        apiFetch('/api/v1/habits/', {
            method: 'POST',
            body: JSON.stringify({ task_specification, periodicity }),
        }),

    retrieve: (id) =>
        apiFetch(`/api/v1/habits/${id}/`),

    update: (id, task_specification) =>
        apiFetch(`/api/v1/habits/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify({ task_specification }),
        }),

    archive: (id) =>
        apiFetch(`/api/v1/habits/${id}/archive/`, { method: 'PATCH' }),

    unarchive: (id) =>
        apiFetch(`/api/v1/habits/${id}/unarchive/`, { method: 'PATCH' }),

    delete: (id) =>
        apiFetch(`/api/v1/habits/${id}/`, { method: 'DELETE' }),

    analytics: (id, start = null, end = null) => {
        const params = new URLSearchParams();
        if (start) params.set('start', start);
        if (end) params.set('end', end);
        const query = params.toString() ? `?${params.toString()}` : '';
        return apiFetch(`/api/v1/habits/${id}/analytics/${query}`);
    },
};

// Completions
const completions = {
    create: (habitId, completedAt = null, note = null) => {
        const body = {};
        if (completedAt) body.completed_at = completedAt;
        if (note) body.note = note;
        return apiFetch(`/api/v1/habits/${habitId}/completions/`, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    delete: (habitId, completionId) =>
        apiFetch(`/api/v1/habits/${habitId}/completions/${completionId}/`, {
            method: 'DELETE',
        }),
};

// Analytics
const analytics = {
    summary: () =>
        apiFetch('/api/v1/analytics/summary/'),

    export: (format = 'csv') => {
        // Direct navigation — browser handles the download
        window.location.href = `/api/v1/analytics/export/?format=${format}`;
    },
};