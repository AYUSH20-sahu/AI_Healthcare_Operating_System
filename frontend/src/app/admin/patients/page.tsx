'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { adminUsersApi, AdminUser } from '@/lib/api';
import { Button, Card, CardContent, CardHeader, Badge, Input } from '@/components/ui';

export default function AdminPatientsOversightPage() {
    const [patients, setPatients] = useState<AdminUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');

    useEffect(() => {
        loadPatientRegistry();
    }, []);

    const loadPatientRegistry = async () => {
        setIsLoading(true);
        try {
            const res = await adminUsersApi.list({ role: 'patient', limit: 100 });
            setPatients(res.users || []);
        } catch (err) {
            console.error('Failed to load patient registry:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const filteredPatients = patients.filter((patient) => {
        const matchesSearch =
            patient.full_name.toLowerCase().includes(search.toLowerCase()) ||
            patient.email.toLowerCase().includes(search.toLowerCase()) ||
            (patient.phone || '').includes(search);
        const matchesStatus =
            statusFilter === 'all' ||
            (statusFilter === 'active' && patient.is_active) ||
            (statusFilter === 'inactive' && !patient.is_active);
        return matchesSearch && matchesStatus;
    });

    const activeCount = patients.filter((p) => p.is_active).length;
    const verifiedCount = patients.filter((p) => p.is_verified).length;

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>👥 Patient Census & Registry Oversight</span>
                        </h1>
                        <Badge variant="primary" className="text-xs uppercase font-bold tracking-wider">
                            Executive Admin
                        </Badge>
                        <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium border border-blue-500/20">
                            Strict PHI Isolation
                        </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Institutional patient registration volume, demographic census, insurance eligibility & account verification without accessing private medical records or consultations.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadPatientRegistry}
                        disabled={isLoading}
                        className="text-xs flex items-center gap-1.5"
                    >
                        <span>🔄</span>
                        <span>{isLoading ? 'Syncing...' : 'Refresh Census'}</span>
                    </Button>
                    <Link href="/admin/queue">
                        <Button variant="outline" size="sm" className="text-xs">
                            Live Clinic Queue →
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Quick KPI Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Registered Patients
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">
                                {patients.length}
                            </span>
                            <span className="text-xs text-blue-600 font-medium">EMR Identities</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Active Patient Portals
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                                {activeCount}
                            </span>
                            <span className="text-xs text-slate-500">
                                {patients.length > 0 ? Math.round((activeCount / patients.length) * 100) : 100}% Active
                            </span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            ABHA / ABDM Verified
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                                {verifiedCount}
                            </span>
                            <span className="text-xs text-purple-600 font-medium">Digital ID Linked</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Hospital Admission Status
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">
                                92% OPD
                            </span>
                            <span className="text-xs text-slate-500">8% Inpatient</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Privacy Architecture Notice */}
            <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/70 dark:bg-blue-950/20 dark:border-blue-900/40 text-blue-900 dark:text-blue-300 text-xs flex items-start gap-3">
                <span className="text-base shrink-0">🔒</span>
                <div>
                    <strong className="font-semibold block mb-0.5">
                        HIPAA & ABDM Protected Health Information (PHI) Safeguard
                    </strong>
                    Hospital Administrators have zero direct access to patient clinical notes, medical prescriptions, laboratory findings, or private physician chats. Administrative privileges are limited to account verification, demographic verification, billing status, and queue routing.
                </div>
            </div>

            {/* Search & Filter Controls */}
            <div className="flex flex-col sm:flex-row gap-3">
                <div className="flex-1">
                    <Input
                        placeholder="Search patient by name, email, or registered phone..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="text-xs"
                    />
                </div>
                <div className="flex gap-2">
                    <Button
                        variant={statusFilter === 'all' ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('all')}
                        className="text-xs"
                    >
                        All ({patients.length})
                    </Button>
                    <Button
                        variant={statusFilter === 'active' ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('active')}
                        className="text-xs"
                    >
                        Active ({activeCount})
                    </Button>
                    <Button
                        variant={statusFilter === 'inactive' ? 'primary' : 'outline'}
                        size="sm"
                        onClick={() => setStatusFilter('inactive')}
                        className="text-xs"
                    >
                        Suspended ({patients.length - activeCount})
                    </Button>
                </div>
            </div>

            {/* Patient Registry Table */}
            <Card className="border-slate-200 dark:border-slate-800 overflow-hidden">
                <CardHeader className="py-3 px-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                            <span>📋 Master Patient Index ({filteredPatients.length})</span>
                        </h2>
                        <span className="text-xs text-slate-500">
                            Demographic & Identity Records
                        </span>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                            <thead className="bg-slate-100/70 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 uppercase font-semibold border-b border-slate-200 dark:border-slate-800">
                                <tr>
                                    <th className="py-3 px-4">Patient Name & Contact</th>
                                    <th className="py-3 px-4">EMR Unique ID</th>
                                    <th className="py-3 px-4">ABDM Status</th>
                                    <th className="py-3 px-4">Account Status</th>
                                    <th className="py-3 px-4">Registration Date</th>
                                    <th className="py-3 px-4 text-right">Account Governance</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {isLoading ? (
                                    <tr>
                                        <td colSpan={6} className="py-8 text-center text-slate-500">
                                            Loading patient registry from database...
                                        </td>
                                    </tr>
                                ) : filteredPatients.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="py-8 text-center text-slate-500">
                                            No patients found matching the search criteria.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredPatients.map((patient) => (
                                        <tr
                                            key={patient.user_id}
                                            className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                                        >
                                            <td className="py-3 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-full bg-blue-500/15 text-blue-600 dark:text-blue-400 font-bold flex items-center justify-center text-xs shrink-0">
                                                        {patient.full_name?.charAt(0) || 'P'}
                                                    </div>
                                                    <div>
                                                        <p className="font-semibold text-slate-900 dark:text-white">
                                                            {patient.full_name}
                                                        </p>
                                                        <p className="text-[11px] text-slate-500">
                                                            {patient.email} {patient.phone ? `• ${patient.phone}` : ''}
                                                        </p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="py-3 px-4 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                                                AI-HOS-{patient.user_id?.slice(0, 8).toUpperCase() || 'PATIENT'}
                                            </td>
                                            <td className="py-3 px-4">
                                                {patient.is_verified ? (
                                                    <Badge variant="primary" size="sm">
                                                        ABHA Linked
                                                    </Badge>
                                                ) : (
                                                    <Badge variant="outline" size="sm">
                                                        Pending Consent
                                                    </Badge>
                                                )}
                                            </td>
                                            <td className="py-3 px-4">
                                                {patient.is_active ? (
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
                                            <td className="py-3 px-4 text-slate-500 text-[11px]">
                                                {patient.created_at ? new Date(patient.created_at).toLocaleDateString() : 'N/A'}
                                            </td>
                                            <td className="py-3 px-4 text-right">
                                                <Link href="/admin/users">
                                                    <Button variant="ghost" size="sm" className="text-xs text-blue-600 hover:text-blue-700">
                                                        Manage Clearance →
                                                    </Button>
                                                </Link>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
