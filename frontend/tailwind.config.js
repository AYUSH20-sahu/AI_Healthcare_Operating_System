/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    50: '#eff6ff',
                    100: '#dbeafe',
                    200: '#bfdbfe',
                    300: '#93c5fd',
                    400: '#60a5fa',
                    500: '#3b82f6',
                    600: '#2563eb',
                    700: '#1d4ed8',
                    800: '#1e40af',
                    900: '#1e3a8a',
                    950: '#172554',
                },
                secondary: {
                    50: '#f8fafc',
                    100: '#f1f5f9',
                    200: '#e2e8f0',
                    300: '#cbd5e1',
                    400: '#94a3b8',
                    500: '#64748b',
                    600: '#475569',
                    700: '#334155',
                    800: '#1e293b',
                    900: '#0f172a',
                    950: '#020617',
                },
                surface: {
                    dark: '#0B0F19',
                    card: '#111827',
                    panel: '#1E293B',
                    light: '#F8FAFC',
                },
                copilot: {
                    50: '#f5f3ff',
                    100: '#ede9fe',
                    500: '#8b5cf6',
                    600: '#7c3aed',
                    700: '#6d28d9',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
                mono: ['JetBrains Mono', 'Menlo', 'monospace'],
            },
            boxShadow: {
                'glow-sm': '0 0 15px -3px rgba(59, 130, 246, 0.25)',
                'glow-md': '0 0 25px -5px rgba(59, 130, 246, 0.35)',
                'glow-ai': '0 0 20px -3px rgba(139, 92, 246, 0.3)',
                'inner-light': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
            },
        },
    },
    plugins: [],
}