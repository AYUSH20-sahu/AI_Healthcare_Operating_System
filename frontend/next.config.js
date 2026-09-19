/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    async rewrites() {
        const rawBackendUrl =
            process.env.BACKEND_INTERNAL_URL ||
            process.env.NEXT_PUBLIC_API_URL ||
            'http://ai-hos-backend:8000';
        const backendBase = rawBackendUrl.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
        return [
            {
                source: '/api/v1/:path*',
                destination: `${backendBase}/api/v1/:path*`,
            },
        ];
    },
};

module.exports = nextConfig;