/**
 * Post-login redirect validation utility.
 * Enforces strict internal-only relative paths and role authorization boundaries (SEC-03).
 */

export function getDefaultRouteForRole(role?: string | null): string {
    if (!role) return '/';
    switch (role.toLowerCase()) {
        case 'doctor':
        case 'physician':
            return '/doctor';
        case 'nurse':
            return '/nurse';
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
 * - Confirms the user's role is authorized for role-gated routes (`/doctor`, `/nurse`, `/patient`, `/admin`).
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
    // Only doctors / physicians can route to /doctor
    if (trimmed.startsWith('/doctor') && userRole !== 'doctor' && userRole !== 'physician') {
        return fallback;
    }

    // Only nurses can route to /nurse
    if (trimmed.startsWith('/nurse') && userRole !== 'nurse') {
        return fallback;
    }

    // Only patients can route to /patient
    if (trimmed.startsWith('/patient') && userRole !== 'patient') {
        return fallback;
    }

    // Only admins can route to /admin
    if (trimmed.startsWith('/admin') && userRole !== 'admin') {
        return fallback;
    }

    return trimmed;
}
