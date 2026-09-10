'use client';

import React from 'react';
import { ProtectedRoute } from '@/components/auth';
import { PortalShell } from '@/components/layout';

export default function PatientLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedRoles={['patient', 'admin']}>
            <PortalShell>{children}</PortalShell>
        </ProtectedRoute>
    );
}

