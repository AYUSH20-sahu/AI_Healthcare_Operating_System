/**
 * Post-login redirect validation utility.
 * Enforces strict internal-only relative paths and role authorization boundaries (SEC-03).
 */

export function getDefaultRouteForRole(role: string): string {
    switch (role.toLowerCase()) {
        case 'doctor':
            return '/doctor';
        case 'patient':
            return '/patient';
        case 'admin':
            return '/admin';
        default:
            return '/';
    }
}

/**
 * Validates the post-login destination URL.
 * - Rejects non-strings and empty strings.
 * - Enforces single leading slash (rejects protocol-relative `//` and external URLs `https://`, `javascript:`).
 * - Rejects backslashes `\` to prevent Windows path / browser normalization confusion.
 * - Confirms the user's role is authorized for role-gated routes (`/doctor`, `/patient`, `/admin`).
 */
export function validatePostLoginRedirect(redirectUrl: string | null | undefined, userRole: string): string {
    const fallback = getDefaultRouteForRole(userRole);
    if (!redirectUrl) {
        return fallback;
    }

    const trimmed = redirectUrl.trim();

    // Must be a relative path, reject protocol-relative (//) and backslashes (\)
    if (!trimmed.startsWith('/') || trimmed.startsWith('//') || trimmed.includes('\\')) {
        return fallback;
    }

    // Role boundary validation:
    // Only doctors (and admins) can route to /doctor
    if (trimmed.startsWith('/doctor') && userRole !== 'doctor' && userRole !== 'admin') {
        return fallback;
    }

    // Only patients (and admins) can route to /patient
    if (trimmed.startsWith('/patient') && userRole !== 'patient' && userRole !== 'admin') {
        return fallback;
    }

    // Only admins can route to /admin
    if (trimmed.startsWith('/admin') && userRole !== 'admin') {
        return fallback;
    }

    return trimmed;
}
