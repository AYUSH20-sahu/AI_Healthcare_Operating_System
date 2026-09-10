'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
    CardHeader,
    Badge,
    Input,
    Select,
    Alert,
} from '@/components/ui';

export default function AdminUserManagementPage() {
    const { user: currentAdmin } = useAuth();

    const [users, setUsers] = useState<AdminUser[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedRole, setSelectedRole] = useState<string>('all');
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Modal state for Provisioning
    const [isProvisionModalOpen, setIsProvisionModalOpen] = useState(false);
    const [provisioning, setProvisioning] = useState(false);
    const [provisionForm, setProvisionForm] = useState<ProvisionUserRequest>({
        full_name: '',
        email: '',
        password: '',
        role: 'doctor',
        specialty: 'Internal Medicine',
        license_number: '',
        hospital_affiliation: 'AI-HOS Central Medical Center',
        phone: '',
    });

    // Modal state for Password Reset
    const [resetTargetUser, setResetTargetUser] = useState<AdminUser | null>(null);
    const [newPassword, setNewPassword] = useState('');
    const [resetting, setResetting] = useState(false);

    const loadUsers = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const params: { role?: string; search?: string } = {};
            if (selectedRole !== 'all') params.role = selectedRole;
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
    }, [selectedRole, searchTerm]);

    useEffect(() => {
        loadUsers();
    }, [loadUsers]);

    const handleToggleStatus = async (targetUser: AdminUser) => {
        try {
            setError(null);
            const newStatus = !targetUser.is_active;
            await adminUsersApi.toggleStatus(targetUser.user_id, newStatus);
            setSuccessMessage(
                `User ${targetUser.email} has been ${newStatus ? 'activated' : 'deactivated'}.`
            );
            loadUsers();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Status toggle failed';
            setError(msg);
        }
    };

    const handleProvisionSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!provisionForm.full_name || !provisionForm.email || !provisionForm.password) {
            setError('Please fill in all required credentials.');
            return;
        }

        if (provisionForm.password.length < 8) {
            setError('Temporary password must be at least 8 characters long.');
            return;
        }

        if (provisionForm.role === 'doctor') {
            if (!provisionForm.license_number || !provisionForm.specialty) {
                setError('Medical license number and specialty are required for physician provisioning.');
                return;
            }
        }

        try {
            setProvisioning(true);
            await adminUsersApi.provision(provisionForm);
            setSuccessMessage(`Account successfully provisioned for ${provisionForm.email} (${provisionForm.role.toUpperCase()})`);
            setIsProvisionModalOpen(false);
            setProvisionForm({
                full_name: '',
                email: '',
                password: '',
                role: 'doctor',
                specialty: 'Internal Medicine',
                license_number: '',
                hospital_affiliation: 'AI-HOS Central Medical Center',
                phone: '',
            });
            loadUsers();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Provisioning failed';
            setError(msg);
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

    const getRoleBadge = (role: string) => {
        switch (role.toLowerCase()) {
            case 'admin':
                return <Badge variant="danger">ADMIN</Badge>;
            case 'doctor':
                return <Badge variant="info">DOCTOR</Badge>;
            case 'nurse':
                return <Badge variant="success">NURSE</Badge>;
            case 'receptionist':
                return <Badge variant="warning">STAFF</Badge>;
            case 'patient':
                return <Badge variant="default">PATIENT</Badge>;
            default:
                return <Badge variant="outline">{role.toUpperCase()}</Badge>;
        }
    };

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                            User Management & Controlled Provisioning
                        </h1>
                        <Badge variant="danger">Level 4 Clearance</Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Authoritative clinician provisioning, staff onboarding, RBAC permissions, and account status controls.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="primary"
                        onClick={() => setIsProvisionModalOpen(true)}
                    >
                        <span className="flex items-center gap-1.5">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                            </svg>
                            <span>Provision Clinician / Staff</span>
                        </span>
                    </Button>
                </div>
            </div>

            {/* Notification Messages */}
            {error && (
                <Alert variant="error" title="Action Error" onClose={() => setError(null)}>
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
                    <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                        {/* Search */}
                        <div className="w-full md:w-80">
                            <Input
                                id="user-search"
                                placeholder="Search by name or email..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                leadingIcon={
                                    <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                }
                            />
                        </div>

                        {/* Role Filter Tabs */}
                        <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
                            {['all', 'doctor', 'patient', 'nurse', 'receptionist', 'admin'].map((r) => (
                                <button
                                    key={r}
                                    onClick={() => setSelectedRole(r)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                        selectedRole === r
                                            ? 'bg-blue-600 text-white shadow-sm'
                                            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                                    }`}
                                >
                                    {r.charAt(0).toUpperCase() + r.slice(1)}
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
                                <th className="px-5 py-3.5">User / Credentials</th>
                                <th className="px-5 py-3.5">Assigned Role</th>
                                <th className="px-5 py-3.5">Clinical / Org Clearance</th>
                                <th className="px-5 py-3.5">Account Status</th>
                                <th className="px-5 py-3.5">Registered</th>
                                <th className="px-5 py-3.5 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        <div className="inline-flex items-center gap-2">
                                            <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                                            <span>Loading user accounts...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : users.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-5 py-12 text-center text-slate-400">
                                        No users match the search criteria.
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
                                        </td>
                                        <td className="px-5 py-3.5">
                                            {getRoleBadge(u.role)}
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-600 dark:text-slate-300">
                                            {u.doctor_profile ? (
                                                <div>
                                                    <span className="font-semibold text-blue-600 dark:text-blue-400">{u.doctor_profile.specialty}</span>
                                                    <span className="block text-slate-400">Lic: {u.doctor_profile.license_number}</span>
                                                    <span className="text-[11px] text-slate-400">{u.doctor_profile.hospital_affiliation}</span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-400 italic">Standard Access</span>
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
                                                    Deactivated
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-5 py-3.5 text-xs text-slate-400">
                                            {new Date(u.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="px-5 py-3.5 text-right space-x-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => {
                                                    setResetTargetUser(u);
                                                    setNewPassword('');
                                                }}
                                            >
                                                Reset Password
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
                    <span>Showing {users.length} of {total} registered users</span>
                    <span className="text-[11px] text-slate-400">All modifications are written to immutable audit_logs</span>
                </div>
            </Card>

            {/* Modal: Provision User */}
            {isProvisionModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <div>
                                <h3 className="font-bold text-lg text-slate-900 dark:text-white">
                                    Provision Clinician or Staff Account
                                </h3>
                                <p className="text-xs text-slate-500">
                                    Public registration is patient-only. All privileged accounts must be created here.
                                </p>
                            </div>
                            <button
                                onClick={() => setIsProvisionModalOpen(false)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleProvisionSubmit} className="space-y-4">
                            <Select
                                id="role-select"
                                label="Clearance Role"
                                value={provisionForm.role}
                                onChange={(e) => setProvisionForm({ ...provisionForm, role: e.target.value as any })}
                                options={[
                                    { value: 'doctor', label: 'Doctor / Physician (Clinical Approval Clearance)' },
                                    { value: 'nurse', label: 'Nurse (Care Coordination & Triage Clearance)' },
                                    { value: 'receptionist', label: 'Staff / Receptionist (Scheduling & Intake)' },
                                    { value: 'admin', label: 'Administrator (Level 4 System Operations)' },
                                ]}
                            />

                            <Input
                                id="prov-name"
                                label="Full Legal Name"
                                required
                                placeholder="e.g. Dr. Priya Patel, MD"
                                value={provisionForm.full_name}
                                onChange={(e) => setProvisionForm({ ...provisionForm, full_name: e.target.value })}
                            />

                            <Input
                                id="prov-email"
                                label="Institutional Email"
                                type="email"
                                required
                                placeholder="doctor@hospital.org"
                                value={provisionForm.email}
                                onChange={(e) => setProvisionForm({ ...provisionForm, email: e.target.value })}
                            />

                            <Input
                                id="prov-pass"
                                label="Initial Temporary Password (8+ chars)"
                                type="password"
                                required
                                placeholder="••••••••••••"
                                value={provisionForm.password}
                                onChange={(e) => setProvisionForm({ ...provisionForm, password: e.target.value })}
                            />

                            {/* Doctor Specific Fields */}
                            {provisionForm.role === 'doctor' && (
                                <div className="p-3 bg-blue-50/50 dark:bg-blue-950/30 rounded-xl border border-blue-200 dark:border-blue-900/50 space-y-3">
                                    <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
                                        Physician Credential Verification
                                    </div>

                                    <Input
                                        id="prov-specialty"
                                        label="Clinical Specialty"
                                        required
                                        placeholder="e.g. Cardiology, Neurology, Pediatrics"
                                        value={provisionForm.specialty || ''}
                                        onChange={(e) => setProvisionForm({ ...provisionForm, specialty: e.target.value })}
                                    />

                                    <Input
                                        id="prov-license"
                                        label="Medical License Number"
                                        required
                                        placeholder="e.g. MED-IND-948271"
                                        value={provisionForm.license_number || ''}
                                        onChange={(e) => setProvisionForm({ ...provisionForm, license_number: e.target.value })}
                                    />

                                    <Input
                                        id="prov-hospital"
                                        label="Hospital Affiliation / Tenant"
                                        placeholder="AI-HOS Central Health"
                                        value={provisionForm.hospital_affiliation || ''}
                                        onChange={(e) => setProvisionForm({ ...provisionForm, hospital_affiliation: e.target.value })}
                                    />
                                </div>
                            )}

                            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => setIsProvisionModalOpen(false)}
                                    disabled={provisioning}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    isLoading={provisioning}
                                >
                                    Issue & Provision Account
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal: Password Reset */}
            {resetTargetUser && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <div>
                                <h3 className="font-bold text-base text-slate-900 dark:text-white">
                                    Reset User Credentials
                                </h3>
                                <p className="text-xs text-slate-500">
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
                                label="New Secure Password (8+ chars)"
                                type="password"
                                required
                                placeholder="••••••••••••"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                            />

                            <div className="flex items-center justify-end gap-3 pt-2">
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
                                    Apply Password Reset
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
