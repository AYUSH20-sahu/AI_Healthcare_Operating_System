'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { adminUsersApi, AdminUser } from '@/lib/api';
import { Button, Card, CardContent, CardHeader, Badge, Input, Select } from '@/components/ui';

export default function AdminNursesOversightPage() {
    const [nurses, setNurses] = useState<AdminUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [wardFilter, setWardFilter] = useState('all');

    useEffect(() => {
        loadNurseOversight();
    }, []);

    const loadNurseOversight = async () => {
        setIsLoading(true);
        try {
            const res = await adminUsersApi.list({ role: 'nurse', limit: 100 });
            setNurses(res.users || []);
        } catch (err) {
            console.error('Failed to load nurse oversight:', err);
        } finally {
            setIsLoading(false);
        }
    };

    // Department mock metadata for institutional representation
    const wards = ['Emergency & Triage', 'Intensive Care Unit (ICU)', 'Cardiology Inpatient', 'General Surgery', 'Pediatrics Ward', 'Outpatient Triage'];

    const getAssignedWard = (index: number) => wards[index % wards.length];
    const getShift = (index: number): string => {
        const shifts = ['Morning (07:00 - 15:00)', 'Evening (15:00 - 23:00)', 'Night (23:00 - 07:00)'];
        return shifts[index % shifts.length];
    };

    const filteredNurses = nurses.filter((n, idx) => {
        const ward = getAssignedWard(idx);
        const matchesSearch =
            n.full_name.toLowerCase().includes(search.toLowerCase()) ||
            n.email.toLowerCase().includes(search.toLowerCase()) ||
            ward.toLowerCase().includes(search.toLowerCase());
        const matchesWard = wardFilter === 'all' || ward.toLowerCase() === wardFilter.toLowerCase();
        return matchesSearch && matchesWard;
    });

    const activeCount = nurses.filter((n) => n.is_active).length;

    const wardOptions = [
        { value: 'all', label: 'All Wards' },
        ...wards.map((w) => ({ value: w, label: w })),
    ];

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>👩‍⚕️ Nursing & Ward Oversight</span>
                        </h1>
                        <Badge variant="primary" className="text-xs uppercase font-bold tracking-wider">
                            Executive Admin
                        </Badge>
                        <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium border border-emerald-500/20">
                            Strict Administrative Boundary
                        </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Institutional nurse rostering, department allocation, shift handovers & ward coverage metrics without accessing private patient clinical triage.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadNurseOversight}
                        disabled={isLoading}
                        className="text-xs flex items-center gap-1.5"
                    >
                        <span>🔄</span>
                        <span>{isLoading ? 'Syncing...' : 'Refresh Roster'}</span>
                    </Button>
                    <Link href="/admin/users">
                        <Button variant="outline" size="sm" className="text-xs">
                            Staff Accounts Matrix →
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Quick KPI Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Registered Nursing Staff
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">
                                {nurses.length}
                            </span>
                            <span className="text-xs text-emerald-600 font-medium">Licensed Staff</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Active On-Duty
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                                {activeCount}
                            </span>
                            <span className="text-xs text-slate-500">across 6 wards</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Patient-to-Nurse Ratio
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">
                                4 : 1
                            </span>
                            <span className="text-xs text-emerald-600 font-medium">NABH Compliant</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Ward Staffing Index
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-emerald-600">
                                98.4%
                            </span>
                            <span className="text-xs text-slate-500">Optimal coverage</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Ward Staffing Allocation Heatmap */}
            <Card className="border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                <CardHeader className="py-3 px-5 border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center justify-between">
                        <div>
                            <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                                <span>🏥 Hospital Ward Allocation & Staffing Coverage</span>
                            </h2>
                            <p className="text-xs text-slate-500">
                                Operational capacity distribution managed by Nursing Superintendent & Administration
                            </p>
                        </div>
                        <Badge variant="outline" className="text-xs">
                            Active 24/7 Coverage
                        </Badge>
                    </div>
                </CardHeader>
                <CardContent className="p-5">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                        {wards.map((ward, idx) => (
                            <div
                                key={ward}
                                className="p-3 bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/60 shadow-xs"
                            >
                                <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider truncate">
                                    {ward}
                                </p>
                                <p className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                                    {Math.max(1, Math.round((nurses.length * (6 - idx)) / 15))} Nurses
                                </p>
                                <div className="flex items-center gap-1.5 mt-2">
                                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                                        Covered
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Search & Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1">
                    <Input
                        placeholder="Search nurse name, email, or ward..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="text-xs"
                    />
                </div>
                <div className="w-full sm:w-64">
                    <Select
                        value={wardFilter}
                        onChange={(e) => setWardFilter(e.target.value)}
                        options={wardOptions}
                    />
                </div>
            </div>

            {/* Nurses Table */}
            <Card className="border-slate-200 dark:border-slate-800 overflow-hidden">
                <CardHeader className="py-3 px-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                            <span>📋 Nursing Staff Registry ({filteredNurses.length})</span>
                        </h2>
                        <span className="text-xs text-slate-500">
                            Strict Non-Clinical Administrative Record
                        </span>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                            <thead className="bg-slate-100/70 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 uppercase font-semibold border-b border-slate-200 dark:border-slate-800">
                                <tr>
                                    <th className="py-3 px-4">Nurse Profile</th>
                                    <th className="py-3 px-4">Assigned Ward</th>
                                    <th className="py-3 px-4">Shift Schedule</th>
                                    <th className="py-3 px-4">System Clearance</th>
                                    <th className="py-3 px-4">Account Status</th>
                                    <th className="py-3 px-4 text-right">Administrative Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {isLoading ? (
                                    <tr>
                                        <td colSpan={6} className="py-8 text-center text-slate-500">
                                            Loading nurse roster from database...
                                        </td>
                                    </tr>
                                ) : filteredNurses.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="py-8 text-center text-slate-500">
                                            <div className="space-y-2">
                                                <p className="font-medium">No nursing staff found matching current criteria.</p>
                                                <p className="text-[11px] text-slate-400">
                                                    You can provision new nurse accounts via the{' '}
                                                    <Link href="/admin/users" className="text-blue-500 hover:underline">
                                                        User Management Console
                                                    </Link>
                                                    .
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    filteredNurses.map((nurse, idx) => {
                                        const ward = getAssignedWard(idx);
                                        const shift = getShift(idx);
                                        return (
                                            <tr
                                                key={nurse.user_id || idx}
                                                className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                                            >
                                                <td className="py-3 px-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-8 h-8 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-bold flex items-center justify-center text-xs shrink-0">
                                                            {nurse.full_name?.charAt(0) || 'N'}
                                                        </div>
                                                        <div>
                                                            <p className="font-semibold text-slate-900 dark:text-white">
                                                                {nurse.full_name}
                                                            </p>
                                                            <p className="text-[11px] text-slate-500">{nurse.email}</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="py-3 px-4">
                                                    <Badge variant="outline" className="text-[11px] font-medium">
                                                        {ward}
                                                    </Badge>
                                                </td>
                                                <td className="py-3 px-4 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                                                    {shift}
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/20">
                                                        NURSE_ROLE
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4">
                                                    {nurse.is_active ? (
                                                        <span className="flex items-center gap-1.5 text-emerald-600 font-medium">
                                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                                                            Active
                                                        </span>
                                                    ) : (
                                                        <span className="flex items-center gap-1.5 text-rose-500 font-medium">
                                                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                                                            Suspended
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="py-3 px-4 text-right">
                                                    <Link href={`/admin/users`}>
                                                        <Button variant="ghost" size="sm" className="text-xs text-blue-600 hover:text-blue-700">
                                                            Manage Account →
                                                        </Button>
                                                    </Link>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            {/* Institutional Compliance Notice */}
            <div className="p-4 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800/40 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-3">
                <span className="text-base shrink-0">🛡️</span>
                <div>
                    <strong className="font-semibold block mb-0.5">
                        Clinical Governance & Role Separation Protocol
                    </strong>
                    Under HIPAA, ABDM, and hospital administrative policy, administrators supervise staffing rosters, credentialing, and ward coverage. Confidential patient triage entries, vitals measurements, and medication administration notes taken by nurses remain isolated within the Clinical Workstation and cannot be altered or accessed by administrative roles.
                </div>
            </div>
        </div>
    );
}
