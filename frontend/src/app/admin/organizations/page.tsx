'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import {
    adminOrganizationsApi,
    Organization,
    OrganizationCreateRequest,
} from '@/lib/api';
import {
    Card,
    CardHeader,
    CardTitle,
    CardContent,
    Button,
    Badge,
    Input,
    Alert,
    ErrorAlert,
    Modal,
} from '@/components/ui';

export default function AdminOrganizationsPage() {
    const { user, isSuperAdmin } = useAuth();
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<any>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // Modal state for Create Organization
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [createLoading, setCreateLoading] = useState(false);
    const [createForm, setCreateForm] = useState<OrganizationCreateRequest>({
        name: '',
        code: '',
        description: '',
        address: '',
        contact_email: '',
        contact_phone: '',
        admin_name: '',
        admin_email: '',
        admin_password: '',
        admin_phone: '',
    });

    // Modal state for Delete Organization
    const [deletingOrg, setDeletingOrg] = useState<Organization | null>(null);
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Search & Filter
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        loadOrganizations();
    }, []);

    const loadOrganizations = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await adminOrganizationsApi.list();
            setOrganizations(data);
        } catch (err: any) {
            console.error('Failed to load organizations:', err);
            setError(err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setCreateLoading(true);
        setError(null);
        try {
            await adminOrganizationsApi.create({
                ...createForm,
                code: createForm.code.toUpperCase().trim(),
                name: createForm.name.trim(),
                admin_name: createForm.admin_name.trim(),
                admin_email: createForm.admin_email.trim(),
            });

            setSuccessMessage(`Organization '${createForm.name}' and its administrator were successfully created.`);
            setIsCreateOpen(false);
            setCreateForm({
                name: '',
                code: '',
                description: '',
                address: '',
                contact_email: '',
                contact_phone: '',
                admin_name: '',
                admin_email: '',
                admin_password: '',
                admin_phone: '',
            });
            await loadOrganizations();
        } catch (err: any) {
            const msg = err?.message || 'Failed to create organization.';
            setError(msg);
        } finally {
            setCreateLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!deletingOrg) return;
        setDeleteLoading(true);
        setError(null);
        try {
            await adminOrganizationsApi.delete(deletingOrg.organization_id);
            setSuccessMessage(`Organization '${deletingOrg.name}' and its administrator were successfully deleted.`);
            setDeletingOrg(null);
            await loadOrganizations();
        } catch (err: any) {
            const msg = err?.message || 'Failed to delete organization.';
            setError(msg);
        } finally {
            setDeleteLoading(false);
        }
    };

    const filteredOrgs = organizations.filter(
        (org) =>
            org.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            org.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
            org.admin?.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            org.admin?.email?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
            {/* Executive Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <Link href="/admin" className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                            ← Admin Operations
                        </Link>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>🏛️ Multi-Tenant Organizations</span>
                        </h1>
                        {isSuperAdmin ? (
                            <Badge variant="primary" className="text-xs uppercase font-bold tracking-wider">
                                Super Administrator
                            </Badge>
                        ) : (
                            <Badge variant="outline" className="text-xs">
                                Facility Scope
                            </Badge>
                        )}
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        {isSuperAdmin
                            ? 'Complete authority to provision, govern, and delete healthcare facilities and their respective administrators.'
                            : 'View details for your assigned healthcare organization.'}
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadOrganizations}
                        disabled={isLoading}
                        className="text-xs flex items-center gap-1.5"
                    >
                        <span>🔄</span>
                        <span>{isLoading ? 'Refreshing...' : 'Refresh'}</span>
                    </Button>

                    {isSuperAdmin && (
                        <Button
                            variant="primary"
                            size="sm"
                            onClick={() => {
                                setIsCreateOpen(true);
                                setError(null);
                            }}
                            className="text-xs flex items-center gap-1.5 shadow-md shadow-blue-500/20"
                        >
                            <span>➕</span>
                            <span>Create New Organization</span>
                        </Button>
                    )}
                </div>
            </div>

            {/* Notification Alerts */}
            {successMessage && (
                <Alert
                    variant="success"
                    title="Action Completed"
                    onClose={() => setSuccessMessage(null)}
                >
                    {successMessage}
                </Alert>
            )}

            {error && (
                <ErrorAlert
                    error={error}
                    title="Organization Operation Warning"
                    onRetry={loadOrganizations}
                    isRetrying={isLoading}
                />
            )}

            {/* Metrics Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="glass-panel border-slate-200 dark:border-slate-800">
                    <CardContent className="p-5 flex items-center justify-between">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Total Organizations
                            </p>
                            <p className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
                                {organizations.length}
                            </p>
                        </div>
                        <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xl font-bold">
                            🏥
                        </div>
                    </CardContent>
                </Card>

                <Card className="glass-panel border-slate-200 dark:border-slate-800">
                    <CardContent className="p-5 flex items-center justify-between">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Active Facilities
                            </p>
                            <p className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
                                {organizations.filter((o) => o.is_active).length}
                            </p>
                        </div>
                        <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-xl font-bold">
                            ✓
                        </div>
                    </CardContent>
                </Card>

                <Card className="glass-panel border-slate-200 dark:border-slate-800">
                    <CardContent className="p-5 flex items-center justify-between">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Super Admin Clearance
                            </p>
                            <p className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-1">
                                {isSuperAdmin ? 'Full Cross-Tenant Authority' : 'Restricted to Org Scope'}
                            </p>
                            <p className="text-[11px] text-slate-400 mt-0.5">
                                {user?.email}
                            </p>
                        </div>
                        <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center text-xl font-bold">
                            🛡️
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Search Bar */}
            <div className="flex items-center gap-3">
                <div className="flex-1 max-w-md">
                    <Input
                        id="orgSearch"
                        label=""
                        placeholder="Search by facility name, code, or administrator..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                    Showing {filteredOrgs.length} of {organizations.length} facility(ies)
                </div>
            </div>

            {/* Organizations Grid */}
            {isLoading ? (
                <div className="py-16 text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-3" />
                    <p className="text-xs text-slate-500">Loading healthcare organizations...</p>
                </div>
            ) : filteredOrgs.length === 0 ? (
                <Card className="glass-panel border-slate-200 dark:border-slate-800 text-center py-12">
                    <CardContent>
                        <p className="text-base font-semibold text-slate-700 dark:text-slate-300">
                            No organizations found
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            {searchQuery ? 'Try adjusting your search query.' : 'Click "Create New Organization" to establish your first healthcare facility.'}
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {filteredOrgs.map((org) => (
                        <Card
                            key={org.organization_id}
                            className="glass-panel border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between"
                        >
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <CardTitle className="text-lg font-bold text-slate-900 dark:text-white">
                                                {org.name}
                                            </CardTitle>
                                            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                                                {org.code}
                                            </span>
                                        </div>
                                        {org.description && (
                                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                                                {org.description}
                                            </p>
                                        )}
                                    </div>
                                    <Badge variant={org.is_active ? 'success' : 'outline'}>
                                        {org.is_active ? 'Active' : 'Inactive'}
                                    </Badge>
                                </div>
                            </CardHeader>

                            <CardContent className="space-y-4 pt-0">
                                {/* Administrator Info Box */}
                                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-xs space-y-1.5">
                                    <div className="flex items-center justify-between text-slate-400 uppercase font-semibold text-[10px] tracking-wider">
                                        <span>Designated Administrator</span>
                                        <span className="text-blue-500">Org Admin</span>
                                    </div>
                                    {org.admin ? (
                                        <div>
                                            <p className="font-semibold text-slate-800 dark:text-slate-200 text-sm">
                                                {org.admin.full_name}
                                            </p>
                                            <p className="text-slate-500 dark:text-slate-400">
                                                📧 {org.admin.email}
                                            </p>
                                            {org.admin.phone && (
                                                <p className="text-slate-500 dark:text-slate-400">
                                                    📱 {org.admin.phone}
                                                </p>
                                            )}
                                        </div>
                                    ) : (
                                        <p className="text-slate-400 italic">No assigned administrator</p>
                                    )}
                                </div>

                                {/* Quick Details & Stats */}
                                <div className="grid grid-cols-3 gap-2 text-center text-xs py-1 border-t border-b border-slate-100 dark:border-slate-800/80">
                                    <div>
                                        <p className="text-[10px] text-slate-400 uppercase">Doctors</p>
                                        <p className="font-bold text-slate-800 dark:text-slate-200">
                                            {org.stats?.total_doctors ?? 0}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-slate-400 uppercase">Patients</p>
                                        <p className="font-bold text-slate-800 dark:text-slate-200">
                                            {org.stats?.total_patients ?? 0}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-slate-400 uppercase">Total Users</p>
                                        <p className="font-bold text-slate-800 dark:text-slate-200">
                                            {org.stats?.total_users ?? 0}
                                        </p>
                                    </div>
                                </div>

                                {org.address && (
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                                        📍 {org.address}
                                    </p>
                                )}

                                {/* Action Bar */}
                                <div className="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-800">
                                    <span className="text-[10px] text-slate-400">
                                        Created: {new Date(org.created_at).toLocaleDateString()}
                                    </span>

                                    {isSuperAdmin && (
                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="danger"
                                                size="sm"
                                                onClick={() => setDeletingOrg(org)}
                                                className="text-xs px-2.5 py-1"
                                            >
                                                Delete Org & Admin
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Create Organization Modal */}
            {isCreateOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
                    <div className="w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden my-8">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                    Create Healthcare Organization & Admin
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                    Provision a new hospital tenant and configure its primary administrator.
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setIsCreateOpen(false)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleCreateSubmit} className="p-6 space-y-4">
                            <div className="space-y-3 pb-3 border-b border-slate-100 dark:border-slate-800">
                                <h4 className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wider">
                                    1. Facility Information
                                </h4>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    <div className="sm:col-span-2">
                                        <Input
                                            id="newOrgName"
                                            label="Facility Name"
                                            required
                                            placeholder="e.g. St. Jude Specialty Hospital"
                                            value={createForm.name}
                                            onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                                            disabled={createLoading}
                                        />
                                    </div>
                                    <div>
                                        <Input
                                            id="newOrgCode"
                                            label="Code"
                                            required
                                            placeholder="e.g. SJS-01"
                                            value={createForm.code}
                                            onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })}
                                            disabled={createLoading}
                                        />
                                    </div>
                                </div>

                                <Input
                                    id="newOrgDesc"
                                    label="Description / Specialization (Optional)"
                                    placeholder="e.g. Cardiology and Neurological Tertiary Center"
                                    value={createForm.description || ''}
                                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                                    disabled={createLoading}
                                />

                                <Input
                                    id="newOrgAddress"
                                    label="Campus Address (Optional)"
                                    placeholder="e.g. 100 Health Blvd, North Wing"
                                    value={createForm.address || ''}
                                    onChange={(e) => setCreateForm({ ...createForm, address: e.target.value })}
                                    disabled={createLoading}
                                />
                            </div>

                            <div className="space-y-3">
                                <h4 className="text-xs font-semibold text-cyan-600 dark:text-cyan-400 uppercase tracking-wider">
                                    2. Administrator Provisioning
                                </h4>
                                <Input
                                    id="newAdminName"
                                    label="Administrator Full Name"
                                    required
                                    placeholder="e.g. Dr. Sarah Connor"
                                    value={createForm.admin_name}
                                    onChange={(e) => setCreateForm({ ...createForm, admin_name: e.target.value })}
                                    disabled={createLoading}
                                />

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <Input
                                        id="newAdminEmail"
                                        label="Admin Email"
                                        type="email"
                                        required
                                        placeholder="sarah.connor@stjude.org"
                                        value={createForm.admin_email}
                                        onChange={(e) => setCreateForm({ ...createForm, admin_email: e.target.value })}
                                        disabled={createLoading}
                                    />

                                    <Input
                                        id="newAdminPhone"
                                        label="Admin Mobile Phone"
                                        type="tel"
                                        placeholder="+91 98765 43210"
                                        value={createForm.admin_phone || ''}
                                        onChange={(e) => setCreateForm({ ...createForm, admin_phone: e.target.value })}
                                        disabled={createLoading}
                                    />
                                </div>

                                <Input
                                    id="newAdminPassword"
                                    label="Initial Admin Password (8+ chars)"
                                    type="password"
                                    required
                                    placeholder="••••••••••••"
                                    value={createForm.admin_password}
                                    onChange={(e) => setCreateForm({ ...createForm, admin_password: e.target.value })}
                                    disabled={createLoading}
                                />
                            </div>

                            <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                                <Button
                                    type="button"
                                    variant="secondary"
                                    onClick={() => setIsCreateOpen(false)}
                                    disabled={createLoading}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    isLoading={createLoading}
                                    className="shadow-md shadow-blue-500/20"
                                >
                                    Provision Organization & Admin
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {deletingOrg && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
                    <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl border border-red-200 dark:border-red-900/50 shadow-2xl p-6 space-y-4">
                        <div className="flex items-center gap-3 text-red-600">
                            <span className="text-2xl">⚠️</span>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                Delete Organization & Admin?
                            </h3>
                        </div>

                        <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                            Are you sure you want to delete <strong className="text-red-600 dark:text-red-400">{deletingOrg.name} ({deletingOrg.code})</strong>?
                        </p>

                        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800/40 text-xs text-red-700 dark:text-red-300 space-y-1">
                            <p className="font-semibold">This action cannot be undone:</p>
                            <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                                <li>The organization will be permanently deleted.</li>
                                <li>The organization administrator ({deletingOrg.admin?.email || 'admin'}) will be removed.</li>
                                <li>All staff access associated with this tenant will be revoked.</li>
                            </ul>
                        </div>

                        <div className="flex items-center justify-end gap-3 pt-2">
                            <Button
                                variant="secondary"
                                onClick={() => setDeletingOrg(null)}
                                disabled={deleteLoading}
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="danger"
                                onClick={handleDelete}
                                isLoading={deleteLoading}
                            >
                                Confirm Permanent Deletion
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
