'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import {
    adminUsersApi,
    AdminUser,
    ProvisionUserRequest,
} from '@/lib/api';
import {
    Button,
    Card,
    CardContent,
    Badge,
    Input,
    Select,
    Alert,
} from '@/components/ui';

const DEPARTMENTS = [
    'Cardiology',
    'Neurology',
    'Oncology',
    'Pediatrics',
    'Emergency Medicine',
    'General Surgery',
    'Orthopedics',
    'Critical Care & ICU',
    'Obstetrics & Gynecology',
    'General Medicine',
    'Pulmonology',
    'Nephrology',
    'Radiology',
    'Anesthesiology',
];

const SHIFTS = [
    'Morning (08:00 - 16:00)',
    'Evening (16:00 - 00:00)',
    'Night (00:00 - 08:00)',
    'Rotational (24/7 Roster)',
    'General OPD (09:00 - 17:00)',
];

export default function AdminUserManagementPage() {
    const { user: currentAdmin } = useAuth();

    const [users, setUsers] = useState<AdminUser[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedRole, setSelectedRole] = useState<string>('all');
    const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // 4-Step Provisioning Wizard State
    const [isProvisionModalOpen, setIsProvisionModalOpen] = useState(false);
    const [wizardStep, setWizardStep] = useState<1 | 2 | 3 | 4>(1);
    const [provisioning, setProvisioning] = useState(false);
    const [provisionError, setProvisionError] = useState<string | null>(null);
    const [backgroundVerified, setBackgroundVerified] = useState(true);
    const [privileges, setPrivileges] = useState<string[]>([
        'Inpatient Admitting',
        'Prescription Authority',
        'Telehealth Consultations',
    ]);

    const initialProvisionForm: ProvisionUserRequest = {
        full_name: '',
        email: '',
        phone: '',
        password: '',
        emergency_contact_phone: '',
        role: 'doctor',
        license_number: '',
        qualifications: '',
        experience_years: 3,
        specialty: 'General Medicine',
        department: 'General Medicine',
        designation: 'Consultant Physician',
        room_number: '',
        shift: 'Morning (08:00 - 16:00)',
        hospital_affiliation: '',
        abdm_hpr_id: '',
        background_verified: true,
    };

    const [provisionForm, setProvisionForm] = useState<ProvisionUserRequest>(initialProvisionForm);

    // Password Reset State
    const [resetTargetUser, setResetTargetUser] = useState<AdminUser | null>(null);
    const [newPassword, setNewPassword] = useState('');
    const [resetting, setResetting] = useState(false);

    // Role Change State
    const [roleTargetUser, setRoleTargetUser] = useState<AdminUser | null>(null);
    const [selectedNewRole, setSelectedNewRole] = useState<string>('doctor');
    const [roleSpecialty, setRoleSpecialty] = useState('General Medicine');
    const [roleLicenseNumber, setRoleLicenseNumber] = useState('');
    const [updatingRole, setUpdatingRole] = useState(false);

    const loadUsers = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const params: { role?: string; search?: string; department?: string } = {};
            if (selectedRole !== 'all') params.role = selectedRole;
            if (selectedDepartment !== 'all') params.department = selectedDepartment;
            if (searchTerm.trim()) params.search = searchTerm.trim();

            const res = await adminUsersApi.list(params);
            setUsers(res.users);
            setTotal(res.total);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to load users';
            setError(msg);
        } finally {
            setLoading(false);
        }
    }, [selectedRole, selectedDepartment, searchTerm]);

    useEffect(() => {
        loadUsers();
    }, [loadUsers]);

    const handleToggleStatus = async (targetUser: AdminUser) => {
        try {
            setError(null);
            const newStatus = !targetUser.is_active;
            await adminUsersApi.toggleStatus(targetUser.user_id, newStatus);
            setSuccessMessage(
                `User ${targetUser.email} has been ${newStatus ? 'activated' : 'suspended'}.`
            );
            loadUsers();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Status toggle failed';
            setError(msg);
        }
    };

    // Step Validation
    const validateStep = (step: number): boolean => {
        setProvisionError(null);
        if (step === 1) {
            if (!provisionForm.full_name.trim()) {
                setProvisionError('Full legal name is required.');
                return false;
            }
            if (!provisionForm.email.trim() || !provisionForm.email.includes('@')) {
                setProvisionError('A valid institutional email is required.');
                return false;
            }
            if (!provisionForm.phone?.trim() || provisionForm.phone.trim().length < 8) {
                setProvisionError('A valid mobile phone number is required (min 8 digits).');
                return false;
            }
            if (!provisionForm.password || provisionForm.password.length < 8) {
                setProvisionError('Temporary password must be at least 8 characters.');
                return false;
            }
            return true;
        }

        if (step === 2) {
            if (!provisionForm.license_number?.trim()) {
                setProvisionError('Medical / Nursing Council Registration Number is mandatory for hospital credentials.');
                return false;
            }
            if (!provisionForm.qualifications?.trim()) {
                setProvisionError('Educational qualifications & degrees are required.');
                return false;
            }
            return true;
        }

        if (step === 3) {
            if (!provisionForm.department?.trim()) {
                setProvisionError('Department assignment is required.');
                return false;
            }
            if (!provisionForm.designation?.trim()) {
                setProvisionError('Official institutional designation / title is required.');
                return false;
            }
            return true;
        }

        return true;
    };

    const handleNextStep = () => {
        if (validateStep(wizardStep)) {
            setWizardStep((prev) => (prev < 4 ? (prev + 1 as any) : prev));
        }
    };

    const handlePrevStep = () => {
        setProvisionError(null);
        setWizardStep((prev) => (prev > 1 ? (prev - 1 as any) : prev));
    };

    const handleProvisionSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setProvisionError(null);

        if (!validateStep(1) || !validateStep(2) || !validateStep(3)) {
            return;
        }

        if (!backgroundVerified) {
            setProvisionError('Please confirm the background verification and credentialing acknowledgment.');
            return;
        }

        try {
            setProvisioning(true);
            const payload: ProvisionUserRequest = {
                ...provisionForm,
                clinical_privileges: privileges,
                background_verified: backgroundVerified,
            };

            await adminUsersApi.provision(payload);
            setSuccessMessage(
                `Account successfully provisioned for ${provisionForm.full_name} (${provisionForm.role.toUpperCase()}) in Department of ${provisionForm.department}.`
            );
            setIsProvisionModalOpen(false);
            setProvisionForm(initialProvisionForm);
            setWizardStep(1);
            loadUsers();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Provisioning failed';
            setProvisionError(msg);
        } finally {
            setProvisioning(false);
        }
    };

    const handleResetPasswordSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!resetTargetUser) return;
        if (newPassword.length < 8) {
            setError('Password must be at least 8 characters long.');
            return;
        }

        try {
            setResetting(true);
            await adminUsersApi.resetPassword(resetTargetUser.user_id, newPassword);
            setSuccessMessage(`Credentials updated for ${resetTargetUser.email}`);
            setResetTargetUser(null);
            setNewPassword('');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to reset password';
            setError(msg);
        } finally {
            setResetting(false);
        }
    };

    const handleRoleChangeSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!roleTargetUser) return;
        setUpdatingRole(true);
        setError(null);
        try {
            await adminUsersApi.updateRole(
                roleTargetUser.user_id,
                selectedNewRole,
                selectedNewRole === 'doctor' || selectedNewRole === 'head_physician' ? roleSpecialty.trim() || undefined : undefined,
                selectedNewRole === 'doctor' || selectedNewRole === 'head_physician' ? roleLicenseNumber.trim() || undefined : undefined,
            );
            setSuccessMessage(`Role for ${roleTargetUser.email} updated to '${selectedNewRole}'.`);
            setRoleTargetUser(null);
            await loadUsers();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to update user role';
            setError(msg);
        } finally {
            setUpdatingRole(false);
        }
    };

    const getRoleBadge = (role: string) => {
        switch (role.toLowerCase()) {
            case 'super_admin':
                return <Badge variant="primary" className="bg-purple-500/10 text-purple-600 border-purple-500/20 font-semibold">Super Admin</Badge>;
            case 'admin':
                return <Badge variant="primary" className="bg-indigo-500/10 text-indigo-600 border-indigo-500/20 font-semibold">Hospital Admin</Badge>;
            case 'head_physician':
                return <Badge variant="primary" className="bg-amber-500/10 text-amber-600 border-amber-500/20 font-bold">Head Physician</Badge>;
            case 'head_nurse':
                return <Badge variant="primary" className="bg-rose-500/10 text-rose-600 border-rose-500/20 font-bold">Head Nurse</Badge>;
            case 'doctor':
                return <Badge variant="primary" className="bg-blue-500/10 text-blue-600 border-blue-500/20">Doctor / Clinician</Badge>;
            case 'nurse':
                return <Badge variant="info" className="bg-teal-500/10 text-teal-600 border-teal-500/20">Staff Nurse</Badge>;
            case 'patient':
                return <Badge variant="outline">Patient</Badge>;
            default:
                return <Badge variant="outline">{role}</Badge>;
        }
    };

    const isConflictError = provisionError && (
        provisionError.toLowerCase().includes('already') ||
        provisionError.toLowerCase().includes('exist') ||
        provisionError.toLowerCase().includes('in use')
    );

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Hospital Staffing & Controlled Provisioning
                        </h1>
                        <Badge variant="danger">Level 4 Clearance</Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Authoritative 4-step onboarding of Doctors, Head Physician, and Head Nurse. Junior staff are managed departmentally.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="primary"
                        onClick={() => {
                            setProvisionForm(initialProvisionForm);
                            setWizardStep(1);
                            setProvisionError(null);
                            setIsProvisionModalOpen(true);
                        }}
                    >
                        <span className="flex items-center gap-1.5">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                            </svg>
                            <span>4-Step Staff Provisioning</span>
                        </span>
                    </Button>
                </div>
            </div>

            {/* Notification Messages */}
            {error && (
                <Alert variant="error" title="Action Notice" onClose={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {successMessage && (
                <Alert variant="success" title="Success" onClose={() => setSuccessMessage(null)}>
                    {successMessage}
                </Alert>
            )}

            {/* Filters Bar */}
            <Card className="glass-panel">
                <CardContent className="pt-5 pb-5">
                    <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
                        {/* Search */}
                        <div className="w-full lg:w-72">
                            <Input
                                id="user-search"
                                placeholder="Search by name, email, or phone..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                leadingIcon={
                                    <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                }
                            />
                        </div>

                        {/* Department Filter */}
                        <div className="w-full lg:w-60">
                            <select
                                className="w-full text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                value={selectedDepartment}
                                onChange={(e) => setSelectedDepartment(e.target.value)}
                            >
                                <option value="all">All Departments</option>
                                {DEPARTMENTS.map((dept) => (
                                    <option key={dept} value={dept}>{dept}</option>
                                ))}
                            </select>
                        </div>

                        {/* Role Filter Tabs */}
                        <div className="flex flex-wrap items-center gap-1.5 w-full lg:w-auto">
                            {[
                                { id: 'all', label: 'All' },
                                { id: 'head_physician', label: 'Head Physician' },
                                { id: 'head_nurse', label: 'Head Nurse' },
                                { id: 'doctor', label: 'Doctors' },
                                { id: 'nurse', label: 'Nurses' },
                                { id: 'admin', label: 'Admins' },
                                { id: 'patient', label: 'Patients' },
                            ].map((r) => (
                                <button
                                    key={r.id}
                                    onClick={() => setSelectedRole(r.id)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                        selectedRole === r.id
                                            ? 'bg-blue-600 text-white shadow-sm'
                                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                    }`}
                                >
                                    {r.label}
                                </button>
                            ))}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Users Data Table */}
            <Card className="glass-panel overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-slate-50/80 dark:bg-slate-800/60 text-xs uppercase font-semibold text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                            <tr>
                                <th className="px-5 py-3.5">User & Contact</th>
                                <th className="px-5 py-3.5">Role</th>
                                <th className="px-5 py-3.5">Department & Posting</th>
                                <th className="px-5 py-3.5">Credentials & Licensure</th>
                                <th className="px-5 py-3.5">Status</th>
                                <th className="px-5 py-3.5 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        <div className="inline-flex items-center gap-2">
                                            <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                                            <span>Loading hospital personnel...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : users.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        No registered personnel match the search and filter criteria.
                                    </td>
                                </tr>
                            ) : (
                                users.map((u) => (
                                    <tr key={u.user_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                        <td className="px-5 py-3.5">
                                            <div className="font-medium text-slate-900 dark:text-white">
                                                {u.full_name}
                                            </div>
                                            <div className="text-xs text-slate-400 font-mono">
                                                {u.email}
                                            </div>
                                            {u.phone && (
                                                <div className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                                                    <span>📱</span> {u.phone}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {getRoleBadge(u.role)}
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                                            {u.department ? (
                                                <div>
                                                    <span className="font-semibold text-blue-600 dark:text-blue-400">
                                                        {u.department}
                                                    </span>
                                                    <span className="block text-slate-500 dark:text-slate-400">
                                                        {u.designation || 'Staff Member'}
                                                    </span>
                                                    {u.room_number && (
                                                        <span className="text-[11px] text-slate-400 block">
                                                            Station/Room: {u.room_number}
                                                        </span>
                                                    )}
                                                    {u.shift && (
                                                        <span className="text-[10px] text-slate-400 font-mono">
                                                            Shift: {u.shift}
                                                        </span>
                                                    )}
                                                </div>
                                            ) : (
                                                <span className="text-slate-400 italic">General Administration</span>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                                            {u.doctor_profile ? (
                                                <div>
                                                    <span className="font-semibold text-slate-700 dark:text-slate-200">
                                                        Lic: {u.doctor_profile.license_number}
                                                    </span>
                                                    <span className="block text-slate-500">
                                                        {u.qualifications || u.doctor_profile.qualifications || 'Certified Practitioner'}
                                                    </span>
                                                    {u.experience_years ? (
                                                        <span className="text-[11px] text-slate-400">
                                                            {u.experience_years} Years Experience
                                                        </span>
                                                    ) : null}
                                                </div>
                                            ) : u.qualifications ? (
                                                <div>
                                                    <span className="text-slate-700 dark:text-slate-200">{u.qualifications}</span>
                                                    {u.experience_years ? (
                                                        <span className="text-[11px] text-slate-400 block">{u.experience_years} Years Exp</span>
                                                    ) : null}
                                                </div>
                                            ) : (
                                                <span className="text-slate-400 italic">—</span>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {u.is_active ? (
                                                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                                    Active
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                                                    Suspended
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5 text-right space-x-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => {
                                                    setRoleTargetUser(u);
                                                    setSelectedNewRole(u.role.toLowerCase());
                                                    setRoleSpecialty(u.doctor_profile?.specialty || 'General Medicine');
                                                    setRoleLicenseNumber(u.doctor_profile?.license_number || '');
                                                }}
                                                disabled={u.user_id === currentAdmin?.user_id}
                                            >
                                                Role
                                            </Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => {
                                                    setResetTargetUser(u);
                                                    setNewPassword('');
                                                }}
                                            >
                                                Password
                                            </Button>

                                            <Button
                                                variant={u.is_active ? 'danger' : 'secondary'}
                                                size="sm"
                                                onClick={() => handleToggleStatus(u)}
                                                disabled={u.user_id === currentAdmin?.user_id}
                                            >
                                                {u.is_active ? 'Suspend' : 'Activate'}
                                            </Button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between">
                    <span>Showing {users.length} of {total} registered personnel</span>
                    <span className="text-[11px] text-slate-400">All modifications are written to immutable audit_logs</span>
                </div>
            </Card>

            {/* 4-Step Modal: Provision Clinician & Leadership Account */}
            {isProvisionModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                        {/* Modal Header & Step Indicator */}
                        <div className="p-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/40">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h3 className="font-bold text-lg text-slate-900 dark:text-white flex items-center gap-2">
                                        <span>Hospital Clinician & Leadership Provisioning</span>
                                        <Badge variant="primary" className="text-[10px]">Step {wizardStep} of 4</Badge>
                                    </h3>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                        Admin provisions all Doctors, only one Head Nurse, and only one Head Physician.
                                    </p>
                                </div>
                                <button
                                    onClick={() => setIsProvisionModalOpen(false)}
                                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg"
                                >
                                    ✕
                                </button>
                            </div>

                            {/* Wizard Progress Bar */}
                            <div className="grid grid-cols-4 gap-2 mt-4">
                                {[
                                    { step: 1, title: 'Identity & Auth' },
                                    { step: 2, title: 'Licensure & Quals' },
                                    { step: 3, title: 'Department & Duty' },
                                    { step: 4, title: 'Review & Confirm' },
                                ].map((s) => (
                                    <div
                                        key={s.step}
                                        className={`pb-1 border-b-2 transition-all ${
                                            wizardStep >= s.step
                                                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                                                : 'border-slate-200 dark:border-slate-800 text-slate-400'
                                        }`}
                                    >
                                        <div className="text-[10px] font-bold uppercase tracking-wider">Step {s.step}</div>
                                        <div className="text-xs font-medium truncate">{s.title}</div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6 overflow-y-auto space-y-4 flex-1">
                            {provisionError && (
                                <Alert variant="error" title="Provisioning Notice">
                                    <div className="space-y-2">
                                        <p>{provisionError}</p>
                                        {isConflictError && (
                                            <div className="pt-2 border-t border-red-200 dark:border-red-900/50 flex items-center gap-2">
                                                <span className="text-xs font-semibold">Existing user account found:</span>
                                                <Link
                                                    href="/auth/login"
                                                    className="text-xs underline font-bold hover:text-red-800 dark:hover:text-red-200"
                                                    onClick={() => setIsProvisionModalOpen(false)}
                                                >
                                                    Login with Existing Credentials →
                                                </Link>
                                            </div>
                                        )}
                                    </div>
                                </Alert>
                            )}

                            {/* STEP 1: Personal & Demographics */}
                            {wizardStep === 1 && (
                                <div className="space-y-4">
                                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                        1. Institutional Role & Identity Information
                                    </div>

                                    <div>
                                        <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                                            Institutional Role *
                                        </label>
                                        <select
                                            className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2.5 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            value={provisionForm.role}
                                            onChange={(e) => {
                                                const newRole = e.target.value as any;
                                                setProvisionForm({
                                                    ...provisionForm,
                                                    role: newRole,
                                                    designation:
                                                        newRole === 'head_physician'
                                                            ? 'Chief Medical Officer / Lead Physician'
                                                            : newRole === 'head_nurse'
                                                            ? 'Nursing Superintendent / Head Nurse'
                                                            : 'Senior Consultant Physician',
                                                });
                                            }}
                                        >
                                            <option value="doctor">Doctor / Specialist Physician</option>
                                            <option value="head_physician">Head Physician (Chief Medical Officer - Single Hospital Head)</option>
                                            <option value="head_nurse">Head Nurse (Nursing Superintendent - Single Hospital Head)</option>
                                            {currentAdmin?.role === 'super_admin' && (
                                                <option value="admin">Hospital Administrator</option>
                                            )}
                                        </select>
                                        <p className="text-[11px] text-slate-400 mt-1">
                                            {provisionForm.role === 'head_physician'
                                                ? 'Designates the primary clinical leader with authority to provision junior residents and physicians.'
                                                : provisionForm.role === 'head_nurse'
                                                ? 'Designates the nursing director with authority to provision departmental staff nurses.'
                                                : 'Standard clinician account with EHR access and prescription signing privileges.'}
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <Input
                                            id="prov-name"
                                            label="Full Legal Name *"
                                            required
                                            allowedChars="alpha"
                                            placeholder="e.g. Dr. Rajesh Verma, MD"
                                            value={provisionForm.full_name}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, full_name: e.target.value })}
                                        />

                                        <Input
                                            id="prov-email"
                                            label="Institutional Email *"
                                            type="email"
                                            required
                                            placeholder="clinician@hospital.org"
                                            value={provisionForm.email}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, email: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <Input
                                            id="prov-phone"
                                            label="Mobile Phone Number *"
                                            type="tel"
                                            allowedChars="numeric"
                                            maxLength={15}
                                            required
                                            placeholder="9876543210"
                                            value={provisionForm.phone || ''}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, phone: e.target.value })}
                                        />

                                        <Input
                                            id="prov-emergency"
                                            label="Emergency Contact Phone"
                                            type="tel"
                                            allowedChars="numeric"
                                            maxLength={15}
                                            placeholder="9876500000"
                                            value={provisionForm.emergency_contact_phone || ''}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, emergency_contact_phone: e.target.value })}
                                        />
                                    </div>

                                    <Input
                                        id="prov-pass"
                                        label="Initial Temporary Password (8+ chars) *"
                                        type="password"
                                        required
                                        placeholder="••••••••••••"
                                        value={provisionForm.password}
                                        onChange={(e) => setProvisionForm({ ...provisionForm, password: e.target.value })}
                                    />
                                </div>
                            )}

                            {/* STEP 2: Professional Licensure & Credentials */}
                            {wizardStep === 2 && (
                                <div className="space-y-4">
                                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                        2. Medical / Nursing Council Licensure & Degrees
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <Input
                                            id="prov-license"
                                            label={
                                                provisionForm.role === 'head_nurse'
                                                    ? 'State Nursing Council Reg Number *'
                                                    : 'State Medical Council / MCI Reg Number *'
                                            }
                                            required
                                            placeholder={provisionForm.role === 'head_nurse' ? 'SNC-2024-8849' : 'MCI-DEL-2018-9921'}
                                            value={provisionForm.license_number || ''}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, license_number: e.target.value })}
                                        />

                                        <Input
                                            id="prov-specialty"
                                            label="Specialty / Clinical Focus *"
                                            required
                                            allowedChars="alpha"
                                            placeholder="e.g. Cardiology, Critical Care, Pediatrics"
                                            value={provisionForm.specialty || ''}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, specialty: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <Input
                                            id="prov-qual"
                                            label="Highest Degrees & Qualifications *"
                                            required
                                            placeholder="e.g. MBBS, MD (Medicine), DM (Cardio), B.Sc Nursing"
                                            value={provisionForm.qualifications || ''}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, qualifications: e.target.value })}
                                        />

                                        <Input
                                            id="prov-exp"
                                            label="Clinical Experience (Years)"
                                            type="number"
                                            min={0}
                                            value={String(provisionForm.experience_years || 0)}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, experience_years: parseInt(e.target.value) || 0 })}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* STEP 3: Departmental Assignment & Clinical Setup */}
                            {wizardStep === 3 && (
                                <div className="space-y-4">
                                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                        3. Departmental Assignment & Station Posting
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                                                Assigned Department *
                                            </label>
                                            <select
                                                className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2.5 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                value={provisionForm.department}
                                                onChange={(e) => setProvisionForm({ ...provisionForm, department: e.target.value })}
                                            >
                                                {DEPARTMENTS.map((dept) => (
                                                    <option key={dept} value={dept}>{dept}</option>
                                                ))}
                                            </select>
                                        </div>

                                        <Input
                                            id="prov-designation"
                                            label="Official Designation / Title *"
                                            required
                                            placeholder="e.g. Senior Consultant, Lead Intensivist"
                                            value={provisionForm.designation || ''}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, designation: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <Input
                                            id="prov-room"
                                            label="OPD Cabin / Station / Ward Number"
                                            placeholder="e.g. Cabin 304 - Tower A, ICU Unit 1"
                                            value={provisionForm.room_number || ''}
                                            onChange={(e) => setProvisionForm({ ...provisionForm, room_number: e.target.value })}
                                        />

                                        <div>
                                            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                                                Primary Shift
                                            </label>
                                            <select
                                                className="w-full text-sm rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-3 py-2.5 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                value={provisionForm.shift}
                                                onChange={(e) => setProvisionForm({ ...provisionForm, shift: e.target.value })}
                                            >
                                                {SHIFTS.map((sh) => (
                                                    <option key={sh} value={sh}>{sh}</option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <Input
                                        id="prov-hospital-affil"
                                        label="Hospital Affiliation / Campus"
                                        value={provisionForm.hospital_affiliation || ''}
                                        onChange={(e) => setProvisionForm({ ...provisionForm, hospital_affiliation: e.target.value })}
                                    />
                                </div>
                            )}

                            {/* STEP 4: Governance, ABDM & Final Review */}
                            {wizardStep === 4 && (
                                <div className="space-y-4">
                                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                        4. Regulatory Compliance & Final Review
                                    </div>

                                    <Input
                                        id="prov-hpr"
                                        label="Healthcare Professional Registry ID (ABDM HPR ID)"
                                        placeholder="e.g. 91-8839-2910-1122 or dr.name@hpr.abdm"
                                        value={provisionForm.abdm_hpr_id || ''}
                                        onChange={(e) => setProvisionForm({ ...provisionForm, abdm_hpr_id: e.target.value })}
                                    />

                                    <div>
                                        <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                                            Granted Clinical Privileges
                                        </label>
                                        <div className="grid grid-cols-2 gap-2 text-xs">
                                            {[
                                                'Inpatient Admitting',
                                                'Prescription Authority',
                                                'Telehealth Consultations',
                                                'Departmental Staff Oversight',
                                                'ICU Emergency Overrides',
                                                'Surgical Clearances',
                                            ].map((priv) => (
                                                <label key={priv} className="flex items-center gap-2 p-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 cursor-pointer">
                                                    <input
                                                        type="checkbox"
                                                        checked={privileges.includes(priv)}
                                                        onChange={(e) => {
                                                            if (e.target.checked) {
                                                                setPrivileges([...privileges, priv]);
                                                            } else {
                                                                setPrivileges(privileges.filter((p) => p !== priv));
                                                            }
                                                        }}
                                                        className="rounded text-blue-600 focus:ring-blue-500"
                                                    />
                                                    <span className="text-slate-700 dark:text-slate-300">{priv}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Verification Summary Card */}
                                    <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50/40 dark:bg-blue-950/20 space-y-2 text-xs">
                                        <div className="font-bold text-blue-900 dark:text-blue-300 uppercase tracking-wider text-[10px]">
                                            Provisioning Summary Card
                                        </div>
                                        <div className="grid grid-cols-2 gap-2 text-slate-700 dark:text-slate-300">
                                            <div><span className="text-slate-400">Name:</span> {provisionForm.full_name}</div>
                                            <div><span className="text-slate-400">Role:</span> {provisionForm.role.toUpperCase()}</div>
                                            <div><span className="text-slate-400">Email:</span> {provisionForm.email}</div>
                                            <div><span className="text-slate-400">Phone:</span> {provisionForm.phone}</div>
                                            <div><span className="text-slate-400">Department:</span> {provisionForm.department}</div>
                                            <div><span className="text-slate-400">Designation:</span> {provisionForm.designation}</div>
                                            <div><span className="text-slate-400">Council Lic:</span> {provisionForm.license_number}</div>
                                            <div><span className="text-slate-400">Degrees:</span> {provisionForm.qualifications}</div>
                                            <div><span className="text-slate-400">Room/Shift:</span> {provisionForm.room_number || 'N/A'} ({provisionForm.shift})</div>
                                            <div><span className="text-slate-400">Experience:</span> {provisionForm.experience_years} Years</div>
                                        </div>
                                    </div>

                                    <label className="flex items-start gap-2 pt-2 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={backgroundVerified}
                                            onChange={(e) => setBackgroundVerified(e.target.checked)}
                                            className="mt-0.5 rounded text-blue-600 focus:ring-blue-500"
                                        />
                                        <span className="text-xs text-slate-600 dark:text-slate-400">
                                            I confirm that the candidate&apos;s medical/nursing qualifications, State Council registration, and institutional background check have been verified in compliance with hospital governance.
                                        </span>
                                    </label>
                                </div>
                            )}
                        </div>

                        {/* Modal Footer Controls */}
                        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/30 flex items-center justify-between">
                            <div>
                                {wizardStep > 1 && (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={handlePrevStep}
                                        disabled={provisioning}
                                    >
                                        ← Back
                                    </Button>
                                )}
                            </div>

                            <div className="flex items-center gap-2">
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setIsProvisionModalOpen(false)}
                                    disabled={provisioning}
                                >
                                    Cancel
                                </Button>

                                {wizardStep < 4 ? (
                                    <Button
                                        type="button"
                                        variant="primary"
                                        size="sm"
                                        onClick={handleNextStep}
                                    >
                                        Next Step →
                                    </Button>
                                ) : (
                                    <Button
                                        type="button"
                                        variant="primary"
                                        size="sm"
                                        onClick={handleProvisionSubmit}
                                        isLoading={provisioning}
                                    >
                                        Confirm & Provision Account
                                    </Button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal: Password Reset */}
            {resetTargetUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <div>
                                <h3 className="font-bold text-lg text-slate-900 dark:text-white">
                                    Administrative Password Reset
                                </h3>
                                <p className="text-xs text-slate-500 font-mono mt-0.5">
                                    Target: {resetTargetUser.email}
                                </p>
                            </div>
                            <button
                                onClick={() => setResetTargetUser(null)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
                            <Input
                                id="new-password"
                                label="New Password (min 8 chars)"
                                type="password"
                                required
                                placeholder="••••••••••••"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                            />

                            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => setResetTargetUser(null)}
                                    disabled={resetting}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    isLoading={resetting}
                                >
                                    Update Password
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal: Role Change */}
            {roleTargetUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <div>
                                <h3 className="font-bold text-lg text-slate-900 dark:text-white">
                                    Change User Role
                                </h3>
                                <p className="text-xs text-slate-500 font-mono mt-0.5">
                                    User: {roleTargetUser.email}
                                </p>
                            </div>
                            <button
                                onClick={() => setRoleTargetUser(null)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleRoleChangeSubmit} className="space-y-4">
                            <Select
                                id="change-role-select"
                                label="New Role Assignment"
                                value={selectedNewRole}
                                onChange={(e) => setSelectedNewRole(e.target.value)}
                                options={[
                                    { value: 'doctor', label: 'Doctor / Physician' },
                                    { value: 'head_physician', label: 'Head Physician (Lead)' },
                                    { value: 'head_nurse', label: 'Head Nurse (Lead)' },
                                    { value: 'nurse', label: 'Staff Nurse' },
                                    { value: 'admin', label: 'Hospital Administrator' },
                                    { value: 'patient', label: 'Patient' },
                                ]}
                            />

                            {(selectedNewRole === 'doctor' || selectedNewRole === 'head_physician') && (
                                <div className="space-y-3 p-3 bg-blue-50/50 dark:bg-blue-950/30 rounded-xl border border-blue-200 dark:border-blue-900/50">
                                    <Input
                                        id="role-specialty"
                                        label="Clinical Specialty"
                                        allowedChars="alpha"
                                        placeholder="e.g. Cardiology"
                                        value={roleSpecialty}
                                        onChange={(e) => setRoleSpecialty(e.target.value)}
                                    />
                                    <Input
                                        id="role-license"
                                        label="Medical License Number"
                                        placeholder="e.g. MED-IND-12345"
                                        value={roleLicenseNumber}
                                        onChange={(e) => setRoleLicenseNumber(e.target.value)}
                                    />
                                </div>
                            )}

                            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => setRoleTargetUser(null)}
                                    disabled={updatingRole}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    isLoading={updatingRole}
                                >
                                    Confirm Role Update
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
