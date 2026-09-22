'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth';
import { PortalShell } from '@/components/layout';

const PUBLIC_PATIENT_ROUTES = ['/patient/login', '/patient/register'];

export default function PatientLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isPublicRoute = PUBLIC_PATIENT_ROUTES.some((route) => pathname?.startsWith(route));

    if (isPublicRoute) {
        return <>{children}</>;
    }

    return (
        <ProtectedRoute allowedRoles={['patient']}>
            <PortalShell>{children}</PortalShell>
        </ProtectedRoute>
    );
}

