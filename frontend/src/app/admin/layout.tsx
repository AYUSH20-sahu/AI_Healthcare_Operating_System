'use client';

import React from 'react';
import { ProtectedRoute } from '@/components/auth';
import { PortalShell } from '@/components/layout';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    return (
        <ProtectedRoute allowedRoles={['admin']}>
            <PortalShell>{children}</PortalShell>
        </ProtectedRoute>
    );
}

