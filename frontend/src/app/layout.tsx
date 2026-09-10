import type { Metadata } from 'next'
import { ThemeProvider } from '@/lib/theme'
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
            <body className="min-h-screen bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 selection:bg-blue-500 selection:text-white transition-colors duration-150 antialiased">
                <ThemeProvider>{children}</ThemeProvider>
            </body>
        </html>
    )
}