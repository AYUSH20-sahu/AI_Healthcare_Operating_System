/**
 * Base HTTP API client for AI-HOS frontend.
 * Provides resilient fetch wrappers, automatic token refreshing,
 * retry mechanisms, and structured error handling.
 */

export const API_BASE = '/api/v1';

export class ApiError extends Error {
    public status: number;
    public code: string;
    public requestId?: string;
    public details?: any;
    public isTimeout: boolean;
    public isNetworkError: boolean;
    public canRetry: boolean;

    constructor(params: {
        message: string;
        status?: number;
        code?: string;
        requestId?: string;
        details?: any;
        isTimeout?: boolean;
        isNetworkError?: boolean;
        canRetry?: boolean;
    }) {
        super(params.message);
        this.name = 'ApiError';
        this.status = params.status || 500;
        this.code = params.code || 'UNKNOWN_ERROR';
        this.requestId = params.requestId;
        this.details = params.details;
        this.isTimeout = !!params.isTimeout;
        this.isNetworkError = !!params.isNetworkError;
        this.canRetry = params.canRetry !== undefined ? params.canRetry : (this.status >= 500 || this.isNetworkError || this.isTimeout);
    }
}

export interface RequestOptions extends RequestInit {
    params?: Record<string, any>;
    _retry?: boolean;
    timeoutMs?: number;
}

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
    refreshSubscribers.push(cb);
}

function onTokenRefreshed(token: string) {
    refreshSubscribers.forEach((cb) => cb(token));
    refreshSubscribers = [];
}

export async function request<T>(
    endpoint: string,
    options: RequestOptions = {}
): Promise<T> {
    const { params, headers, _retry, timeoutMs = 15000, ...fetchOptions } = options;

    const baseOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';
    const configuredApiUrl = (typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_API_URL) ? process.env.NEXT_PUBLIC_API_URL : null;
    
    // Build URL with query parameters
    let url: URL;
    if (configuredApiUrl && (configuredApiUrl.startsWith('http://') || configuredApiUrl.startsWith('https://'))) {
        const cleanBase = configuredApiUrl.replace(/\/$/, '');
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        url = new URL(`${cleanBase}${cleanEndpoint}`);
    } else {
        url = new URL(`${API_BASE}${endpoint}`, baseOrigin);
    }
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, String(value));
            }
        });
    }

    // Get auth token from localStorage safely
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData;
    const defaultHeaders: HeadersInit = {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    let response: Response;
    try {
        response = await fetch(url.toString(), {
            ...fetchOptions,
            headers: defaultHeaders,
            signal: fetchOptions.signal || controller.signal,
        });
    } catch (err: any) {
        clearTimeout(timer);
        const isOffline = typeof navigator !== 'undefined' && !navigator.onLine;
        const isAbort = err.name === 'AbortError';

        if (isAbort) {
            throw new ApiError({
                message: `Request timed out after ${Math.round(timeoutMs / 1000)}s. Please retry.`,
                status: 408,
                code: 'REQUEST_TIMEOUT',
                isTimeout: true,
                canRetry: true,
            });
        }

        throw new ApiError({
            message: isOffline
                ? 'You appear to be offline. Please verify your internet connection.'
                : 'Network connection failure. Unable to reach AI-HOS backend server.',
            status: 0,
            code: isOffline ? 'OFFLINE_ERROR' : 'NETWORK_ERROR',
            isNetworkError: true,
            canRetry: true,
        });
    } finally {
        clearTimeout(timer);
    }

    // Handle 401 Unauthorized with token refresh if possible
    if (response.status === 401 && !_retry && typeof window !== 'undefined') {
        const refreshToken = localStorage.getItem('refresh_token');
        const isAuthEndpoint = endpoint.includes('/auth/login') || endpoint.includes('/auth/refresh') || endpoint.includes('/auth/signup');

        if (refreshToken && !isAuthEndpoint) {
            if (!isRefreshing) {
                isRefreshing = true;
                try {
                    let refreshUrl: URL;
                    if (configuredApiUrl && (configuredApiUrl.startsWith('http://') || configuredApiUrl.startsWith('https://'))) {
                        refreshUrl = new URL(`${configuredApiUrl.replace(/\/$/, '')}/auth/refresh`);
                    } else {
                        refreshUrl = new URL(`${API_BASE}/auth/refresh`, baseOrigin);
                    }
                    refreshUrl.searchParams.append('refresh_token', refreshToken);

                    const refreshRes = await fetch(refreshUrl.toString(), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                    });

                    if (refreshRes.ok) {
                        const newTokens = await refreshRes.json();
                        localStorage.setItem('access_token', newTokens.access_token);
                        localStorage.setItem('refresh_token', newTokens.refresh_token);
                        isRefreshing = false;
                        onTokenRefreshed(newTokens.access_token);
                        // Retry original request
                        return request<T>(endpoint, { ...options, _retry: true });
                    } else {
                        throw new Error('Refresh failed');
                    }
                } catch {
                    isRefreshing = false;
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    localStorage.removeItem('auth_user');
                    window.dispatchEvent(new CustomEvent('aihos:auth_expired'));
                }
            } else {
                // Wait for refreshing process
                return new Promise<T>((resolve, reject) => {
                    subscribeTokenRefresh(() => {
                        request<T>(endpoint, { ...options, _retry: true })
                            .then(resolve)
                            .catch(reject);
                    });
                });
            }
        }
    }

    if (!response.ok) {
        let requestId = response.headers.get('X-Request-ID') || undefined;
        const error = await response.json().catch(() => ({}));
        let message = `HTTP ${response.status}`;
        let code = `HTTP_${response.status}`;
        let details = null;

        if (error.error) {
            code = error.error.code || code;
            message = error.error.message || message;
            details = error.error.details || null;
            if (!requestId && error.error.request_id) {
                requestId = error.error.request_id;
            }
        } else if (typeof error.detail === 'string') {
            message = error.detail;
        } else if (Array.isArray(error.detail)) {
            message = error.detail.map((d: { msg?: string }) => d.msg || 'Validation error').join(', ');
            details = error.detail;
            code = 'VALIDATION_ERROR';
        }

        throw new ApiError({
            message,
            status: response.status,
            code,
            requestId,
            details,
            canRetry: response.status >= 500 || response.status === 429,
        });
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

export const api = {
    get: <T>(
        endpoint: string,
        paramsOrOptions?: Record<string, any>,
        options?: Partial<RequestOptions>
    ) => {
        let params = paramsOrOptions;
        let opts = options;
        if (paramsOrOptions && 'params' in paramsOrOptions && typeof paramsOrOptions.params === 'object') {
            params = paramsOrOptions.params;
            const { params: _, ...rest } = paramsOrOptions;
            opts = { ...rest, ...options };
        }
        return request<T>(endpoint, { method: 'GET', params, ...opts });
    },

    post: <T>(
        endpoint: string,
        data?: unknown,
        paramsOrOptions?: Record<string, any>,
        options?: Partial<RequestOptions>
    ) => {
        let params = paramsOrOptions;
        let opts = options;
        if (paramsOrOptions && 'params' in paramsOrOptions && typeof paramsOrOptions.params === 'object') {
            params = paramsOrOptions.params;
            const { params: _, ...rest } = paramsOrOptions;
            opts = { ...rest, ...options };
        }
        const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
        return request<T>(endpoint, {
            method: 'POST',
            body: isFormData ? (data as FormData) : data !== undefined ? JSON.stringify(data) : undefined,
            params,
            ...opts,
        });
    },

    put: <T>(endpoint: string, data: unknown, options?: Partial<RequestOptions>) =>
        request<T>(endpoint, { method: 'PUT', body: JSON.stringify(data), ...options }),

    patch: <T>(endpoint: string, data?: unknown, options?: Partial<RequestOptions>) =>
        request<T>(endpoint, { method: 'PATCH', body: data !== undefined ? JSON.stringify(data) : undefined, ...options }),

    delete: <T>(endpoint: string, options?: Partial<RequestOptions>) =>
        request<T>(endpoint, { method: 'DELETE', ...options }),

    retry: async <T>(fn: () => Promise<T>, maxRetries = 2, delayMs = 800): Promise<T> => {
        let lastErr: any;
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await fn();
            } catch (err: any) {
                lastErr = err;
                if (attempt < maxRetries && (err?.canRetry || err?.status >= 500 || err?.isNetworkError)) {
                    await new Promise((r) => setTimeout(r, delayMs * Math.pow(2, attempt)));
                    continue;
                }
                throw err;
            }
        }
        throw lastErr;
    },
};

export default api;
