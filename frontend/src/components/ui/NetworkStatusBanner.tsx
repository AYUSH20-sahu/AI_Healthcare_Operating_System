'use client';

import React, { useState, useEffect } from 'react';

export const NetworkStatusBanner: React.FC = () => {
    const [isOnline, setIsOnline] = useState(true);
    const [showRestored, setShowRestored] = useState(false);

    useEffect(() => {
        if (typeof window === 'undefined') return;

        setIsOnline(navigator.onLine);

        const handleOnline = () => {
            setIsOnline(true);
            setShowRestored(true);
            const timer = setTimeout(() => setShowRestored(false), 3500);
            return () => clearTimeout(timer);
        };

        const handleOffline = () => {
            setIsOnline(false);
            setShowRestored(false);
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    if (isOnline && !showRestored) {
        return null;
    }

    if (!isOnline) {
        return (
            <div
                role="status"
                aria-live="assertive"
                className="bg-amber-600 text-white px-4 py-2 text-xs font-medium text-center sticky top-0 z-50 shadow-md flex items-center justify-center gap-2"
            >
                <span className="animate-pulse">📡</span>
                <span>
                    <strong>Offline Mode:</strong> Network connection lost. Data sync and cloud AI models will automatically resume once reconnected.
                </span>
            </div>
        );
    }

    if (showRestored) {
        return (
            <div
                role="status"
                aria-live="polite"
                className="bg-emerald-600 text-white px-4 py-1.5 text-xs font-medium text-center sticky top-0 z-50 shadow-md flex items-center justify-center gap-2 transition-opacity"
            >
                <span>✅</span>
                <span>Connection restored. Online services synced.</span>
            </div>
        );
    }

    return null;
};
