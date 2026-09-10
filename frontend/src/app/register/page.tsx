'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function RegisterPageRedirect() {
    const router = useRouter();

    useEffect(() => {
        router.replace('/auth/register');
    }, [router]);

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#0B0F19]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
    );
}
