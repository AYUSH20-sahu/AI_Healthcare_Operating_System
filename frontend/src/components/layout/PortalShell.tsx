'use client';

import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';
import { EmergencyBanner } from './EmergencyBanner';

interface PortalShellProps {
    children: React.ReactNode;
}

export function PortalShell({ children }: PortalShellProps) {
    const [collapsed, setCollapsed] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('aihos_sidebar_collapsed');
            if (saved === 'true') {
                setCollapsed(true);
            }
        }
    }, []);

    const handleSetCollapsed = (val: boolean) => {
        setCollapsed(val);
        if (typeof window !== 'undefined') {
            localStorage.setItem('aihos_sidebar_collapsed', String(val));
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 transition-colors">
            {/* Top Emergency Clinical Banner */}
            <EmergencyBanner />

            {/* Sidebar */}
            <Sidebar
                collapsed={collapsed}
                setCollapsed={handleSetCollapsed}
                mobileOpen={mobileOpen}
                setMobileOpen={setMobileOpen}
            />

            {/* Top Nav Header */}
            <TopNav
                collapsed={collapsed}
                onMenuClick={() => setMobileOpen(true)}
            />

            {/* Main Content Area */}
            <main
                className={`transition-all duration-200 ease-in-out p-4 sm:p-6 lg:p-8 ${
                    collapsed ? 'lg:pl-24' : 'lg:pl-72'
                }`}
            >
                <div className="max-w-7xl mx-auto space-y-6">
                    {children}
                </div>
            </main>
        </div>
    );
}
