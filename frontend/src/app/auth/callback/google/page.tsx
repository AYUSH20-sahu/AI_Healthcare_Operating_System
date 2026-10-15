'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { authApi } from '@/lib/api/auth';
import { validatePostLoginRedirect } from '@/lib/redirect-validator';

function GoogleCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { handleOAuthTokens } = useAuth();

    const [error, setError] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState('Verifying Google credentials with accounts.google.com...');

    useEffect(() => {
        let isMounted = true;

        const processOAuthCallback = async () => {
            const errorParam = searchParams.get('error') || searchParams.get('error_description');
            if (errorParam) {
                if (isMounted) setError(decodeURIComponent(errorParam));
                return;
            }

            const accessTokenParam = searchParams.get('access_token');
            const refreshTokenParam = searchParams.get('refresh_token');

            // 1. Direct tokens from backend redirect
            if (accessTokenParam && refreshTokenParam) {
                try {
                    setStatusMessage('Finalizing secure session...');
                    const loggedInUser = await handleOAuthTokens(accessTokenParam, refreshTokenParam);
                    const destination = validatePostLoginRedirect(null, loggedInUser.role);
                    router.replace(destination);
                } catch (err: unknown) {
                    if (isMounted) {
                        const msg = err instanceof Error ? err.message : 'Failed to finalize session with received tokens.';
                        setError(msg);
                    }
                }
                return;
            }

            // 2. Authorization code from accounts.google.com
            const codeParam = searchParams.get('code');
            if (codeParam) {
                try {
                    setStatusMessage('Exchanging authorization code with Google OAuth servers...');
                    const redirectUri = window.location.origin + '/auth/callback/google';
                    const tokenRes = await authApi.googleOAuthCallback(codeParam, redirectUri);

                    setStatusMessage('Creating patient profile and session...');
                    const loggedInUser = await handleOAuthTokens(tokenRes.access_token, tokenRes.refresh_token);
                    const destination = validatePostLoginRedirect(null, loggedInUser.role);
                    router.replace(destination);
                } catch (err: unknown) {
                    if (isMounted) {
                        const msg = err instanceof Error ? err.message : 'Google OAuth exchange failed. Please try again.';
                        setError(msg);
                    }
                }
                return;
            }

            // Neither code nor tokens found
            if (isMounted) {
                setError('No authorization code or tokens returned by Google Accounts.');
            }
        };

        processOAuthCallback();

        return () => {
            isMounted = false;
        };
    }, [searchParams, handleOAuthTokens, router]);

    if (error) {
        return (
            <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6 text-center">
                <div className="w-16 h-16 mx-auto rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center border border-rose-500/20">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>

                <div className="space-y-2">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                        Google Authentication Failed
                    </h2>
                    <p className="text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/40 rounded-xl p-3 text-left leading-relaxed">
                        {error}
                    </p>
                </div>

                <div className="space-y-2 pt-2">
                    <Link
                        href="/patient/login"
                        className="w-full inline-flex items-center justify-center py-2.5 px-4 rounded-xl text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 shadow-md shadow-teal-500/20 transition"
                    >
                        Return to Patient Sign In
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full max-w-md bg-[#1F1F1F] text-[#E3E3E3] border border-[#303030] rounded-[28px] overflow-hidden shadow-2xl">
            {/* Top Google Progress Loading Bar */}
            <div className="h-1 w-full bg-[#1F1F1F] overflow-hidden relative">
                <div className="absolute top-0 bottom-0 left-0 bg-[#8AB4F8] w-1/2 animate-pulse" />
            </div>

            <div className="p-8 space-y-6 text-center">
                <div className="flex items-center justify-center gap-2 text-xs font-medium text-[#C4C7C5]">
                    <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                    </svg>
                    <span>Sign in with Google</span>
                </div>

                <div className="py-6 flex flex-col items-center justify-center space-y-4">
                    <svg className="animate-spin w-10 h-10 text-[#8AB4F8]" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <div className="space-y-1">
                        <h3 className="text-lg font-medium text-white">One moment please...</h3>
                        <p className="text-xs text-[#8E918F]">{statusMessage}</p>
                    </div>
                </div>

                <div className="pt-2 border-t border-[#303030] text-[11px] text-[#8E918F]">
                    Connecting to CarePulse Healthcare Operating System
                </div>
            </div>
        </div>
    );
}

export default function GoogleCallbackPage() {
    return (
        <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
            <Suspense
                fallback={
                    <div className="w-full max-w-md bg-[#1F1F1F] rounded-[28px] p-8 text-center text-[#8E918F] text-xs">
                        Loading Google authorization callback...
                    </div>
                }
            >
                <GoogleCallbackContent />
            </Suspense>
        </div>
    );
}
