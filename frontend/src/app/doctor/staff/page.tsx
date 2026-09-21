'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { headPhysicianApi, JuniorPhysicianProvisionRequest, DepartmentTeamResponse } from '@/lib/api';
import { Button, Card, CardContent, Badge, Input, Alert } from '@/components/ui';

const RESIDENT_DESIGNATIONS = [
    'Junior Resident (PGY-1 / PGY-2)',
    'Senior Resident (PGY-3+)',
    'Fellow / Clinical Fellow',
    'Junior Medical Officer (JMO)',
    'Attending / Assistant Physician',
];

const SHIFTS = [
    'Morning (08:00 - 16:00)',
    'Evening (16:00 - 00:00)',
    'Night (00:00 - 08:00)',
    'Rotational Emergency Roster',
];

export default function DoctorStaffManagementPage() {
    const { user } = useAuth();
    const [teamData, setTeamData] = useState<DepartmentTeamResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Modal state
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [modalError, setModalError] = useState<string | null>(null);

    const initialForm: JuniorPhysicianProvisionRequest = {
        full_name: '',
        email: '',
        phone: '',
        password: '',
        license_number: '',
        qualifications: '',
        designation: 'Junior Resident (PGY-1 / PGY-2)',
        specialty: '',
        experience_years: 1,
        room_number: '',
        shift: 'Morning (08:00 - 16:00)',
    };

    const [formData, setFormData] = useState<JuniorPhysicianProvisionRequest>(initialForm);

    const isHeadPhysician = user?.role === 'head_physician' || user?.role === 'super_admin';

    const loadTeam = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await headPhysicianApi.getTeam();
            setTeamData(data);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to load department team';
            setError(msg);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadTeam();
    }, [loadTeam]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setModalError(null);

        if (!formData.full_name || !formData.email || !formData.password || !formData.license_number) {
            setModalError('Please complete all required fields (Name, Email, Password, and Medical License).');
            return;
        }

        if (formData.password.length < 8) {
            setModalError('Temporary password must be at least 8 characters long.');
            return;
        }

        try {
            setSubmitting(true);
            const res = await headPhysicianApi.provisionJunior(formData);
            setSuccessMessage(res.message || `Successfully onboarded ${formData.full_name}`);
            setIsModalOpen(false);
            setFormData(initialForm);
            loadTeam();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to provision junior physician';
            setModalError(msg);
        } finally {
            setSubmitting(false);
        }
    };

    const isConflictError = modalError && (
        modalError.toLowerCase().includes('already') ||
        modalError.toLowerCase().includes('exist') ||
        modalError.toLowerCase().includes('in use')
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Departmental Clinical Team & Staffing
                        </h1>
                        <Badge variant="primary" className="bg-amber-500/10 text-amber-600 border-amber-500/20">
                            Department Leadership
                        </Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Head Physician supervisory console for onboarding junior physicians, residents, and managing department postings.
                    </p>
                </div>

                {isHeadPhysician && (
                    <Button
                        variant="primary"
                        onClick={() => {
                            setFormData({
                                ...initialForm,
                                specialty: teamData?.department || 'General Medicine',
                            });
                            setModalError(null);
                            setIsModalOpen(true);
                        }}
                    >
                        <span className="flex items-center gap-1.5">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                            </svg>
                            <span>Onboard Junior Physician</span>
                        </span>
                    </Button>
                )}
            </div>

            {/* Notifications */}
            {error && (
                <Alert variant="error" title="Notice" onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {successMessage && (
                <Alert variant="success" title="Success" onClose={() => setSuccessMessage(null)}>
                    {successMessage}
                </Alert>
            )}

            {/* Department Lead Overview Card */}
            <Card className="glass-panel border-amber-500/20 bg-gradient-to-r from-amber-500/5 via-blue-500/5 to-transparent">
                <CardContent className="p-5">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-2xl">
                                🩺
                            </div>
                            <div>
                                <div className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
                                    Assigned Department
                                </div>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                                    Department of {teamData?.department || 'General Medicine'}
                                </h2>
                                <p className="text-xs text-slate-500 mt-0.5">
                                    Head Physician Incharge: <span className="font-semibold text-slate-700 dark:text-slate-300">{teamData?.head_physician?.name || user?.full_name || 'Dr. Chief Medical Officer'}</span>
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <div className="text-right">
                                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                                    {teamData?.total_members || 0}
                                </div>
                                <div className="text-xs text-slate-400">Total Department Clinicians</div>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Team Personnel Table */}
            <Card className="glass-panel overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-slate-50/80 dark:bg-slate-800/60 text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                            <tr>
                                <th className="px-5 py-3.5">Doctor & Contact</th>
                                <th className="px-5 py-3.5">Designation</th>
                                <th className="px-5 py-3.5">Council Registration</th>
                                <th className="px-5 py-3.5">Qualifications & Exp</th>
                                <th className="px-5 py-3.5">Posting / Shift</th>
                                <th className="px-5 py-3.5">Leadership</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        <div className="inline-flex items-center gap-2">
                                            <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                                            <span>Loading departmental roster...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : !teamData || teamData.team.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        No clinicians currently rostered in this department. Click &apos;Onboard Junior Physician&apos; to add staff.
                                    </td>
                                </tr>
                            ) : (
                                teamData.team.map((doc) => (
                                    <tr key={doc.doctor_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                        <td className="px-5 py-3.5">
                                            <div className="font-semibold text-slate-900 dark:text-white">
                                                {doc.full_name}
                                            </div>
                                            <div className="text-xs text-slate-400 font-mono">
                                                {doc.email}
                                            </div>
                                            {doc.phone && (
                                                <div className="text-[11px] text-slate-500 mt-0.5">
                                                    📱 {doc.phone}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className="font-medium text-slate-800 dark:text-slate-200 text-xs">
                                                {doc.designation || 'Physician'}
                                            </span>
                                            <span className="block text-[11px] text-blue-600 dark:text-blue-400">
                                                {doc.specialty}
                                            </span>
                                        </td>
                                        <td className="px-5 py-3.5 text-xs font-mono text-slate-600 dark:text-slate-300">
                                            {doc.license_number}
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                                            <div>{doc.qualifications || 'MBBS / Specialist'}</div>
                                            {doc.experience_years ? (
                                                <span className="text-[11px] text-slate-400">{doc.experience_years} Years Experience</span>
                                            ) : null}
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                                            <div>Cabin: {doc.room_number || 'General OPD'}</div>
                                            <div className="text-[11px] text-slate-400 font-mono">{doc.shift || 'Morning Shift'}</div>
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {doc.is_head_physician ? (
                                                <Badge variant="primary" className="bg-amber-500/10 text-amber-600 border-amber-500/20 font-bold text-[10px]">
                                                    Head of Dept
                                                </Badge>
                                            ) : (
                                                <Badge variant="outline" className="text-[10px]">
                                                    Staff Clinician
                                                </Badge>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </Card>

            {/* Modal: Onboard Junior Staff */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full shadow-2xl p-6 space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <div>
                                <h3 className="font-bold text-lg text-slate-900 dark:text-white">
                                    Onboard Junior Physician / Resident
                                </h3>
                                <p className="text-xs text-slate-500 mt-0.5">
                                    Scoped strictly to Department of <span className="font-bold text-blue-600">{teamData?.department || 'General Medicine'}</span>
                                </p>
                            </div>
                            <button
                                onClick={() => setIsModalOpen(false)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg"
                            >
                                ✕
                            </button>
                        </div>

                        {modalError && (
                            <Alert variant="error" title="Notice">
                                <div className="space-y-2 text-xs">
                                    <p>{modalError}</p>
                                    {isConflictError && (
                                        <div className="pt-2 border-t border-red-200 dark:border-red-900/50 flex items-center gap-2">
                                            <span className="font-semibold">Existing user account found:</span>
                                            <Link
                                                href="/auth/login"
                                                className="underline font-bold hover:text-red-800 dark:hover:text-red-200"
                                                onClick={() => setIsModalOpen(false)}
                                            >
                                                Login with Existing Credentials →
                                            </Link>
                                        </div>
                                    )}
                                </div>
                            </Alert>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-3">
                            <Input
                                id="junior-name"
                                label="Full Legal Name *"
                                required
                                placeholder="e.g. Dr. Aryan Khan, MD"
                                value={formData.full_name}
                                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                            />

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <Input
                                    id="junior-email"
                                    label="Institutional Email *"
                                    type="email"
                                    required
                                    placeholder="resident@hospital.org"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                />

                                <Input
                                    id="junior-phone"
                                    label="Mobile Phone *"
                                    required
                                    placeholder="+919876543210"
                                    value={formData.phone || ''}
                                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                                />
                            </div>

                            <Input
                                id="junior-pass"
                                label="Initial Temporary Password (8+ chars) *"
                                type="password"
                                required
                                placeholder="••••••••••••"
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            />

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <Input
                                    id="junior-lic"
                                    label="Medical Council Reg Number *"
                                    required
                                    placeholder="e.g. SMC-2023-4412"
                                    value={formData.license_number}
                                    onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
                                />

                                <Input
                                    id="junior-qual"
                                    label="Degrees / Qualifications *"
                                    required
                                    placeholder="e.g. MBBS, MD Resident"
                                    value={formData.qualifications}
                                    onChange={(e) => setFormData({ ...formData, qualifications: e.target.value })}
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                                    Clinical Designation *
                                </label>
                                <select
                                    className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    value={formData.designation}
                                    onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                                >
                                    {RESIDENT_DESIGNATIONS.map((des) => (
                                        <option key={des} value={des}>{des}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <Input
                                    id="junior-room"
                                    label="OPD Cabin / Ward Station"
                                    placeholder="Cabin 102 - Wing C"
                                    value={formData.room_number || ''}
                                    onChange={(e) => setFormData({ ...formData, room_number: e.target.value })}
                                />

                                <div>
                                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                                        Assigned Shift
                                    </label>
                                    <select
                                        className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        value={formData.shift}
                                        onChange={(e) => setFormData({ ...formData, shift: e.target.value })}
                                    >
                                        {SHIFTS.map((sh) => (
                                            <option key={sh} value={sh}>{sh}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setIsModalOpen(false)}
                                    disabled={submitting}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    size="sm"
                                    isLoading={submitting}
                                >
                                    Onboard Staff Clinician
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
