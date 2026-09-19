'use client';

import React from 'react';
import { ProtectedRoute } from '@/components/auth';
import { PortalShell } from '@/components/layout';

export default function DoctorLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedRoles={['doctor']}>
            <PortalShell>{children}</PortalShell>
        </ProtectedRoute>
    );
}

