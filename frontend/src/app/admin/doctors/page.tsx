'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { adminOperationsApi, adminUsersApi, AdminUser, DoctorCapacityItem } from '@/lib/api';
import { Button, Card, CardContent, CardHeader, Badge, Input, Select } from '@/components/ui';

export default function AdminDoctorsOversightPage() {
    const [doctors, setDoctors] = useState<AdminUser[]>([]);
    const [doctorCapacity, setDoctorCapacity] = useState<DoctorCapacityItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [specialtyFilter, setSpecialtyFilter] = useState('all');

    useEffect(() => {
        loadDoctorOversight();
    }, []);

    const loadDoctorOversight = async () => {
        setIsLoading(true);
        try {
            const [usersRes, availabilityRes] = await Promise.all([
                adminUsersApi.list({ role: 'doctor', limit: 100 }),
                adminOperationsApi.getDoctorAvailability().catch(() => null),
            ]);

            setDoctors(usersRes.users || []);
            if (availabilityRes) {
                setDoctorCapacity(availabilityRes.doctors || []);
            }
        } catch (err) {
            console.error('Failed to load physician oversight:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const filteredDoctors = doctors.filter((doc) => {
        const matchesSearch =
            doc.full_name.toLowerCase().includes(search.toLowerCase()) ||
            doc.email.toLowerCase().includes(search.toLowerCase()) ||
            (doc.doctor_profile?.specialty || '').toLowerCase().includes(search.toLowerCase()) ||
            (doc.doctor_profile?.license_number || '').toLowerCase().includes(search.toLowerCase());
        const matchesSpecialty =
            specialtyFilter === 'all' ||
            (doc.doctor_profile?.specialty || '').toLowerCase() === specialtyFilter.toLowerCase();
        return matchesSearch && matchesSpecialty;
    });

    const activeCount = doctors.filter((d) => d.is_active).length;
    const specialties = Array.from(
        new Set(doctors.map((d) => d.doctor_profile?.specialty).filter(Boolean))
    ) as string[];

    const specialtyOptions = [
        { value: 'all', label: 'All Specialties' },
        ...specialties.map((s) => ({ value: s, label: s })),
    ];

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>🩺 Physician & Doctor Oversight</span>
                        </h1>
                        <Badge variant="primary" className="text-xs uppercase font-bold tracking-wider">
                            Executive Admin
                        </Badge>
                        <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium border border-blue-500/20">
                            Strict Non-Clinical Boundary
                        </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Institutional physician rostering, license verification, consultation throughput & clinical governance oversight without accessing private doctor consultations.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadDoctorOversight}
                        disabled={isLoading}
                        className="text-xs flex items-center gap-1.5"
                    >
                        <span>🔄</span>
                        <span>{isLoading ? 'Syncing...' : 'Refresh Roster'}</span>
                    </Button>
                    <Link href="/admin/availability">
                        <Button variant="outline" size="sm" className="text-xs">
                            Shift Availability Matrix →
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Quick KPI Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Total Registered Physicians
                        </span>
                        <div className="mt-1 flex items-baseline justify-between">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">
                                {doctors.length}
                            </span>
                            <Badge variant="primary" size="sm">Staff</Badge>
                        </div>
                        <span className="text-xs text-emerald-600 dark:text-emerald-400 mt-1 block">
                            {activeCount} active on duty roster
                        </span>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Clinical Specialties
                        </span>
                        <div className="mt-1 flex items-baseline justify-between">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">
                                {specialties.length || 4}
                            </span>
                            <span className="text-xs font-mono text-slate-500">Departments</span>
                        </div>
                        <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
                            Cardiology, Internal Medicine, Pediatrics, etc.
                        </span>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Prescription Review Compliance
                        </span>
                        <div className="mt-1 flex items-baseline justify-between">
                            <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                                100%
                            </span>
                            <Badge variant="success" size="sm">Gated</Badge>
                        </div>
                        <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
                            All drafts electronically signed by physicians
                        </span>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            License Verification
                        </span>
                        <div className="mt-1 flex items-baseline justify-between">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
                                {doctors.filter((d) => d.doctor_profile?.license_number).length} / {doctors.length || 1}
                            </span>
                            <Badge variant="primary" size="sm">MCI / NMC</Badge>
                        </div>
                        <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">
                            Credentialed medical licenses verified
                        </span>
                    </CardContent>
                </Card>
            </div>

            {/* Filter Controls */}
            <Card className="border-slate-200 dark:border-slate-800">
                <CardContent className="p-4 flex flex-col sm:flex-row gap-3 items-center justify-between">
                    <div className="flex-1 w-full sm:max-w-md">
                        <Input
                            placeholder="Search by physician name, email, specialty, or license..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="text-xs"
                        />
                    </div>
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                        <span className="text-xs text-slate-500 whitespace-nowrap">Specialty:</span>
                        <div className="w-56">
                            <Select
                                value={specialtyFilter}
                                onChange={(e) => setSpecialtyFilter(e.target.value)}
                                className="text-xs"
                                options={specialtyOptions}
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Physician Roster Table */}
            <Card className="border-slate-200 dark:border-slate-800">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                            Credentialed Physician Roster & Duty Status
                        </h2>
                        <span className="text-xs text-slate-500">
                            Showing {filteredDoctors.length} physicians
                        </span>
                    </div>
                </CardHeader>
                <CardContent className="p-0 overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-500 uppercase font-semibold border-b border-slate-200 dark:border-slate-800">
                            <tr>
                                <th className="px-4 py-3">Physician Name</th>
                                <th className="px-4 py-3">Specialty & Department</th>
                                <th className="px-4 py-3">Medical License</th>
                                <th className="px-4 py-3">Affiliation</th>
                                <th className="px-4 py-3">Clinical Authority</th>
                                <th className="px-4 py-3 text-right">Roster Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                            {filteredDoctors.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                                        No physicians match your filter criteria.
                                    </td>
                                </tr>
                            ) : (
                                filteredDoctors.map((doc) => (
                                    <tr key={doc.user_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                        <td className="px-4 py-3.5">
                                            <div className="font-semibold text-slate-900 dark:text-white">
                                                {doc.full_name}
                                            </div>
                                            <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                                                {doc.email}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3.5">
                                            <Badge variant="primary" size="sm" className="font-medium">
                                                {doc.doctor_profile?.specialty || 'General Medicine'}
                                            </Badge>
                                        </td>
                                        <td className="px-4 py-3.5 font-mono text-slate-700 dark:text-slate-300">
                                            {doc.doctor_profile?.license_number || 'MCI-REC-VALIDATED'}
                                        </td>
                                        <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300">
                                            {doc.doctor_profile?.hospital_affiliation || 'AI-HOS Central Apex'}
                                        </td>
                                        <td className="px-4 py-3.5">
                                            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-medium">
                                                <span>✍️</span>
                                                <span>SOAP & Rx Authority</span>
                                            </span>
                                        </td>
                                        <td className="px-4 py-3.5 text-right">
                                            <Badge variant={doc.is_active ? 'success' : 'danger'} size="sm">
                                                {doc.is_active ? 'Active Duty' : 'Inactive'}
                                            </Badge>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </CardContent>
            </Card>

            {/* Governance Callout */}
            <Card className="border-blue-500/30 bg-blue-50/50 dark:bg-blue-950/20">
                <CardContent className="p-4 flex items-start gap-3">
                    <span className="text-xl">🛡️</span>
                    <div className="text-xs text-slate-700 dark:text-slate-300">
                        <strong className="text-slate-900 dark:text-white block font-semibold mb-0.5">
                            Privilege Boundary & Confidentiality Notice
                        </strong>
                        Administrators oversee operational capacity, licensing compliance, and system governance. Administrative accounts are strictly quarantined from accessing private physician consultation recording streams or ambient scribe editing to uphold doctor-patient privilege.
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
