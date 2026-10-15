'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { patientsApi, Patient } from '@/lib/api';
import { Card, CardHeader, CardContent, Button, Badge, Input } from '@/components/ui';

export default function DoctorPatientsDirectoryPage() {
    const [patients, setPatients] = useState<Patient[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize] = useState(15);
    const [search, setSearch] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [genderFilter, setGenderFilter] = useState<'all' | 'male' | 'female' | 'other'>('all');
    const [abhaFilter, setAbhaFilter] = useState<'all' | 'linked' | 'unlinked'>('all');

    const loadPatients = useCallback(async () => {
        setIsLoading(true);
        try {
            const res = await patientsApi.list({
                page,
                page_size: pageSize,
                search: search.trim() || undefined,
            });
            setPatients(res.patients || []);
            setTotal(res.total || 0);
        } catch (err) {
            console.error('Failed to load patient directory:', err);
        } finally {
            setIsLoading(false);
        }
    }, [page, pageSize, search]);

    useEffect(() => {
        loadPatients();
    }, [loadPatients]);

    const handleSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        loadPatients();
    };

    const calculateAge = (dobString?: string) => {
        if (!dobString) return '—';
        const dob = new Date(dobString);
        if (isNaN(dob.getTime())) return '—';
        const diffMs = Date.now() - dob.getTime();
        const ageDt = new Date(diffMs);
        return Math.abs(ageDt.getUTCFullYear() - 1970);
    };

    const filteredPatients = patients.filter((p) => {
        if (genderFilter !== 'all' && (p.gender || '').toLowerCase() !== genderFilter) {
            return false;
        }
        if (abhaFilter === 'linked' && !p.abha_address) return false;
        if (abhaFilter === 'unlinked' && p.abha_address) return false;
        return true;
    });

    const totalPages = Math.ceil(total / pageSize) || 1;

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Link href="/doctor" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                            ← Doctor Console
                        </Link>
                        <span className="text-slate-300 dark:text-slate-700">•</span>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                            Clinical Registry
                        </span>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                        <span>👥 Patient Directory & Longitudinal EHR</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Search and inspect patient clinical timelines, active prescriptions, ABHA identifiers, and diagnostic history.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Badge variant="primary" className="text-xs">
                        Total Registered: {total}
                    </Badge>
                </div>
            </div>

            {/* Filter and Search Bar */}
            <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
                <CardContent className="p-4">
                    <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row items-center gap-3">
                        <div className="relative flex-1 w-full">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search by patient name, phone, email, or ABHA address..."
                                className="w-full pl-9 pr-4 py-2 rounded-xl text-xs sm:text-sm border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>

                        <div className="flex items-center gap-2 w-full sm:w-auto">
                            <select
                                value={genderFilter}
                                onChange={(e) => setGenderFilter(e.target.value as any)}
                                className="px-3 py-2 rounded-xl text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            >
                                <option value="all">All Genders</option>
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                                <option value="other">Other</option>
                            </select>

                            <select
                                value={abhaFilter}
                                onChange={(e) => setAbhaFilter(e.target.value as any)}
                                className="px-3 py-2 rounded-xl text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            >
                                <option value="all">All ABHA Statuses</option>
                                <option value="linked">ABHA Linked Only</option>
                                <option value="unlinked">Unlinked Only</option>
                            </select>

                            <Button type="submit" variant="primary" size="sm" className="shrink-0 text-xs">
                                Search
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>

            {/* Patients Table */}
            <Card className="border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                <CardHeader className="py-3 px-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 flex flex-row items-center justify-between">
                    <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <span>📋 Patient Rosters ({filteredPatients.length} shown)</span>
                    </h2>
                    <span className="text-xs text-slate-400">
                        Page {page} of {totalPages}
                    </span>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs text-left">
                            <thead className="bg-slate-100/70 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 uppercase font-semibold border-b border-slate-200 dark:border-slate-800">
                                <tr>
                                    <th className="py-3 px-4">Patient Name & Demographics</th>
                                    <th className="py-3 px-4">Age / Gender</th>
                                    <th className="py-3 px-4">ABHA ID / National Address</th>
                                    <th className="py-3 px-4">Emergency Contact</th>
                                    <th className="py-3 px-4">Registered Date</th>
                                    <th className="py-3 px-4 text-right">EHR Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {isLoading ? (
                                    <tr>
                                        <td colSpan={6} className="py-12 text-center text-slate-500">
                                            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mb-2" />
                                            <p>Loading patient directory...</p>
                                        </td>
                                    </tr>
                                ) : filteredPatients.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="py-12 text-center text-slate-400">
                                            <span className="text-2xl block mb-1">🔍</span>
                                            No patients found matching the selected filters.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredPatients.map((patient) => {
                                        const age = calculateAge(patient.date_of_birth);
                                        return (
                                            <tr
                                                key={patient.patient_id}
                                                className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                                            >
                                                <td className="py-3 px-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-8 h-8 rounded-full bg-blue-500/15 text-blue-600 dark:text-blue-400 font-bold flex items-center justify-center text-xs shrink-0">
                                                            {patient.full_name?.charAt(0) || 'P'}
                                                        </div>
                                                        <div>
                                                            <Link
                                                                href={`/doctor/patients/${patient.patient_id}`}
                                                                className="font-semibold text-slate-900 dark:text-white hover:text-blue-600 transition-colors"
                                                            >
                                                                {patient.full_name}
                                                            </Link>
                                                            <p className="text-[11px] text-slate-500">
                                                                {patient.phone || 'No phone'} {patient.email ? `• ${patient.email}` : ''}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className="font-medium text-slate-800 dark:text-slate-200">
                                                        {age !== '—' ? `${age} yrs` : '—'}
                                                    </span>
                                                    <span className="text-slate-400 text-[11px] block capitalize">
                                                        {patient.gender || 'Unknown'} {patient.blood_group ? `(${patient.blood_group})` : ''}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4">
                                                    {patient.abha_address ? (
                                                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
                                                            <span>✓</span> {patient.abha_address}
                                                        </span>
                                                    ) : (
                                                        <span className="text-slate-400 text-[11px] italic">
                                                            Not Linked
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="py-3 px-4 text-slate-600 dark:text-slate-300 text-[11px]">
                                                    {patient.emergency_contact_name ? (
                                                        <div>
                                                            <p className="font-medium">{patient.emergency_contact_name}</p>
                                                            <p className="text-slate-400">{patient.emergency_contact_phone || '—'}</p>
                                                        </div>
                                                    ) : (
                                                        <span className="text-slate-400 italic">None listed</span>
                                                    )}
                                                </td>
                                                <td className="py-3 px-4 text-slate-500 text-[11px]">
                                                    {patient.created_at
                                                        ? new Date(patient.created_at).toLocaleDateString()
                                                        : '—'}
                                                </td>
                                                <td className="py-3 px-4 text-right">
                                                    <div className="flex items-center justify-end gap-2">
                                                        <Link
                                                            href={`/doctor/patients/${patient.patient_id}`}
                                                            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50 transition-colors"
                                                        >
                                                            View EHR →
                                                        </Link>
                                                        <Link
                                                            href={`/doctor/prescriptions?patient_id=${patient.patient_id}`}
                                                            className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 transition-colors"
                                                            title="Draft Prescription"
                                                        >
                                                            Rx
                                                        </Link>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination Bar */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between p-4 border-t border-slate-200 dark:border-slate-800 text-xs">
                            <span className="text-slate-500">
                                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} patients
                            </span>
                            <div className="flex items-center gap-1.5">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={page <= 1}
                                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                                >
                                    Previous
                                </Button>
                                <span className="px-2 font-medium text-slate-700 dark:text-slate-300">
                                    {page} / {totalPages}
                                </span>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={page >= totalPages}
                                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                >
                                    Next
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
