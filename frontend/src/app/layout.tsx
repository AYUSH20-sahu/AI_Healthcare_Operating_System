import type { Metadata } from 'next'
import { ThemeProvider } from '@/lib/theme'
import { AuthProvider } from '@/lib/auth'
import './globals.css'

export const metadata: Metadata = {
    title: 'AI-HOS — AI Healthcare Operating System',
    description: 'Next-Generation Clinical AI Operating System connecting Doctors, Patients, and Hospital Ops',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" suppressHydrationWarning>
            <head>
                <script
                    dangerouslySetInnerHTML={{
                        __html: `
                            (function() {
                                try {
                                    var stored = localStorage.getItem('ai_hos_theme');
                                    var mql = window.matchMedia('(prefers-color-scheme: dark)');
                                    var isDark = stored === 'dark' || ((!stored || stored === 'system') && mql.matches);
                                    var root = document.documentElement;
                                    if (isDark) {
                                        root.classList.add('dark');
                                        root.setAttribute('data-theme', 'dark');
                                        root.style.colorScheme = 'dark';
                                    } else {
                                        root.classList.remove('dark');
                                        root.setAttribute('data-theme', 'light');
                                        root.style.colorScheme = 'light';
                                    }
                                } catch (e) {}
                            })();
                        `,
                    }}
                />
            </head>
            <body className="min-h-screen bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 selection:bg-blue-500 selection:text-white transition-colors duration-150 antialiased">
                <ThemeProvider>
                    <AuthProvider>{children}</AuthProvider>
                </ThemeProvider>
            </body>
        </html>

    )
}