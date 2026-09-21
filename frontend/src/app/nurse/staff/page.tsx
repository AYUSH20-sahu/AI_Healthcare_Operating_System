'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { headNurseApi, JuniorNurseProvisionRequest, DepartmentTeamResponse } from '@/lib/api';
import { Button, Card, CardContent, Badge, Input, Alert } from '@/components/ui';

const NURSE_DESIGNATIONS = [
    'Staff Nurse / General Ward Nurse',
    'Junior Staff Nurse (Probationary)',
    'ICU / Critical Care Nurse',
    'Operating Theatre (OT) Nurse',
    'Emergency & Triage Nurse',
    'Pediatric Care Nurse',
    'Shift In-Charge / Senior Staff Nurse',
];

const SHIFTS = [
    'Morning (07:00 - 15:00)',
    'Evening (15:00 - 23:00)',
    'Night (23:00 - 07:00)',
    'Rotational Roster (24/7)',
];

export default function NurseStaffManagementPage() {
    const { user } = useAuth();
    const [teamData, setTeamData] = useState<DepartmentTeamResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Modal state
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [modalError, setModalError] = useState<string | null>(null);

    const initialForm: JuniorNurseProvisionRequest = {
        full_name: '',
        email: '',
        phone: '',
        password: '',
        license_number: '',
        qualifications: 'B.Sc Nursing',
        designation: 'Staff Nurse / General Ward Nurse',
        experience_years: 1,
        room_number: '',
        shift: 'Morning (07:00 - 15:00)',
    };

    const [formData, setFormData] = useState<JuniorNurseProvisionRequest>(initialForm);

    const isHeadNurse = user?.role === 'head_nurse' || user?.role === 'super_admin';

    const loadTeam = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await headNurseApi.getTeam();
            setTeamData(data);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to load nursing team';
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
            setModalError('Please complete all required fields (Name, Email, Password, and Nursing Council Reg No).');
            return;
        }

        if (formData.password.length < 8) {
            setModalError('Temporary password must be at least 8 characters long.');
            return;
        }

        try {
            setSubmitting(true);
            const res = await headNurseApi.provisionJunior(formData);
            setSuccessMessage(res.message || `Successfully onboarded ${formData.full_name}`);
            setIsModalOpen(false);
            setFormData(initialForm);
            loadTeam();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to provision junior nurse';
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
                            Nursing Department Roster & Staffing
                        </h1>
                        <Badge variant="primary" className="bg-rose-500/10 text-rose-600 border-rose-500/20">
                            Nursing Administration
                        </Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Head Nurse supervisory console for onboarding junior nurses, managing duty shifts, and ward station assignments.
                    </p>
                </div>

                {isHeadNurse && (
                    <Button
                        variant="primary"
                        onClick={() => {
                            setFormData(initialForm);
                            setModalError(null);
                            setIsModalOpen(true);
                        }}
                    >
                        <span className="flex items-center gap-1.5">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                            </svg>
                            <span>Onboard Staff Nurse</span>
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
            <Card className="glass-panel border-rose-500/20 bg-gradient-to-r from-rose-500/5 via-teal-500/5 to-transparent">
                <CardContent className="p-5">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-2xl">
                                👩‍⚕️
                            </div>
                            <div>
                                <div className="text-xs font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
                                    Assigned Ward / Department
                                </div>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                                    Department of {teamData?.department || 'General Ward'}
                                </h2>
                                <p className="text-xs text-slate-500 mt-0.5">
                                    Nursing Superintendent: <span className="font-semibold text-slate-700 dark:text-slate-300">{teamData?.head_nurse?.name || user?.full_name || 'Head Nurse'}</span>
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            <div className="text-right">
                                <div className="text-2xl font-bold text-teal-600 dark:text-teal-400">
                                    {teamData?.total_members || 0}
                                </div>
                                <div className="text-xs text-slate-400">Total Department Nurses</div>
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
                                <th className="px-5 py-3.5">Nurse & Contact</th>
                                <th className="px-5 py-3.5">Designation</th>
                                <th className="px-5 py-3.5">Qualifications & Exp</th>
                                <th className="px-5 py-3.5">Ward / Station Posting</th>
                                <th className="px-5 py-3.5">Duty Shift</th>
                                <th className="px-5 py-3.5">Leadership</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        <div className="inline-flex items-center gap-2">
                                            <div className="w-4 h-4 rounded-full border-2 border-rose-500 border-t-transparent animate-spin" />
                                            <span>Loading nursing roster...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : !teamData || teamData.team.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        No nursing staff currently rostered in this department. Click &apos;Onboard Staff Nurse&apos; to add nurses.
                                    </td>
                                </tr>
                            ) : (
                                teamData.team.map((nurse) => (
                                    <tr key={nurse.user_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                        <td className="px-5 py-3.5">
                                            <div className="font-semibold text-slate-900 dark:text-white">
                                                {nurse.full_name}
                                            </div>
                                            <div className="text-xs text-slate-400 font-mono">
                                                {nurse.email}
                                            </div>
                                            {nurse.phone && (
                                                <div className="text-[11px] text-slate-500 mt-0.5">
                                                    📱 {nurse.phone}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            <span className="font-medium text-slate-800 dark:text-slate-200 text-xs">
                                                {nurse.designation || 'Staff Nurse'}
                                            </span>
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                                            <div>{nurse.qualifications || 'B.Sc Nursing / GNM'}</div>
                                            {nurse.experience_years ? (
                                                <span className="text-[11px] text-slate-400">{nurse.experience_years} Years Experience</span>
                                            ) : null}
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                                            <div>Station: {nurse.room_number || 'General Ward Station'}</div>
                                            <div className="text-[11px] text-slate-400">{nurse.department}</div>
                                        </td>
                                        <td className="px-5 py-3.5 text-xs font-mono text-slate-600 dark:text-slate-300">
                                            {nurse.shift || 'Morning Shift'}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {nurse.role === 'head_nurse' ? (
                                                <Badge variant="primary" className="bg-rose-500/10 text-rose-600 border-rose-500/20 font-bold text-[10px]">
                                                    Head Nurse
                                                </Badge>
                                            ) : (
                                                <Badge variant="info" className="bg-teal-500/10 text-teal-600 border-teal-500/20 text-[10px]">
                                                    Staff Nurse
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

            {/* Modal: Onboard Staff Nurse */}
            {isModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full shadow-2xl p-6 space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <div>
                                <h3 className="font-bold text-lg text-slate-900 dark:text-white">
                                    Onboard Staff Nurse
                                </h3>
                                <p className="text-xs text-slate-500 mt-0.5">
                                    Scoped strictly to Department of <span className="font-bold text-rose-600">{teamData?.department || 'General Ward'}</span>
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
                                id="nurse-name"
                                label="Full Legal Name *"
                                required
                                placeholder="e.g. Sister Ananya Sharma"
                                value={formData.full_name}
                                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                            />

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <Input
                                    id="nurse-email"
                                    label="Institutional Email *"
                                    type="email"
                                    required
                                    placeholder="nurse@hospital.org"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                />

                                <Input
                                    id="nurse-phone"
                                    label="Mobile Phone *"
                                    required
                                    placeholder="+919876543210"
                                    value={formData.phone || ''}
                                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                                />
                            </div>

                            <Input
                                id="nurse-pass"
                                label="Initial Temporary Password (8+ chars) *"
                                type="password"
                                required
                                placeholder="••••••••••••"
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                            />

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <Input
                                    id="nurse-lic"
                                    label="Nursing Council Reg Number *"
                                    required
                                    placeholder="e.g. SNC-DEL-2022-8192"
                                    value={formData.license_number}
                                    onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
                                />

                                <Input
                                    id="nurse-qual"
                                    label="Qualifications & Certification *"
                                    required
                                    placeholder="e.g. B.Sc Nursing, GNM, Critical Care"
                                    value={formData.qualifications}
                                    onChange={(e) => setFormData({ ...formData, qualifications: e.target.value })}
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                                    Nursing Designation *
                                </label>
                                <select
                                    className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    value={formData.designation}
                                    onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                                >
                                    {NURSE_DESIGNATIONS.map((des) => (
                                        <option key={des} value={des}>{des}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <Input
                                    id="nurse-room"
                                    label="Assigned Station / Ward Number"
                                    placeholder="Ward 3A - Station 1"
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
                                    Onboard Staff Nurse
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
