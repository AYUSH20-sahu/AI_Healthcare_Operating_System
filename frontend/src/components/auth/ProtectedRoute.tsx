'use client';

import React, { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { Spinner } from '@/components/ui';

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
    fallback?: React.ReactNode;
}

export function ProtectedRoute({
    children,
    allowedRoles,
    fallback,
}: ProtectedRouteProps) {
    const { user, isLoading, isAuthenticated } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (!isLoading) {
            if (!isAuthenticated) {
                const redirectParam = pathname ? `?redirect=${encodeURIComponent(pathname)}` : '';
                router.replace(`/auth/login${redirectParam}`);
            } else if (allowedRoles && user && !allowedRoles.includes(user.role)) {
                router.replace('/auth/unauthorized');
            }
        }
    }, [isLoading, isAuthenticated, user, allowedRoles, router, pathname]);

    if (isLoading) {
        if (fallback) return <>{fallback}</>;
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 dark:bg-[#0B0F19]">
                <div className="p-8 flex flex-col items-center gap-4 text-center">
                    <div className="relative flex items-center justify-center">
                        <div className="w-12 h-12 rounded-full border-2 border-blue-500/20 animate-ping absolute" />
                        <Spinner size="lg" className="text-blue-500" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-slate-800 dark:text-slate-200">Verifying Clinical Clearance</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Authenticating session & access permissions...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
        return null;
    }

    return <>{children}</>;
}
