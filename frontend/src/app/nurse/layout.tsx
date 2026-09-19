'use client';

import React from 'react';
import { ProtectedRoute } from '@/components/auth';
import { PortalShell } from '@/components/layout';

export default function NurseLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedRoles={['nurse']}>
            <PortalShell>{children}</PortalShell>
        </ProtectedRoute>
    );
}
