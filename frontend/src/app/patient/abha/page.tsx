'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { consentApi, ConsentItem, appointmentBookingApi, DoctorListResponse, Doctor } from '@/lib/api';
import { Button, Card, CardContent, Badge } from '@/components/ui';

export default function PatientAbhaConsentPage() {
    const { user } = useAuth();
    const [consents, setConsents] = useState<ConsentItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [filterActiveOnly, setFilterActiveOnly] = useState(false);
    const [revokingId, setRevokingId] = useState<string | null>(null);

    // Grant Consent Modal State
    const [isGrantModalOpen, setIsGrantModalOpen] = useState(false);
    const [doctors, setDoctors] = useState<Doctor[]>([]);
    const [selectedDoctorId, setSelectedDoctorId] = useState('');
    const [selectedScope, setSelectedScope] = useState('full_access');
    const [isGranting, setIsGranting] = useState(false);
    const [grantError, setGrantError] = useState<string | null>(null);
    const [actionSuccess, setActionSuccess] = useState<string | null>(null);

    useEffect(() => {
        loadConsents();
        loadDoctors();
    }, [filterActiveOnly]);

    const loadConsents = async () => {
        setIsLoading(true);
        try {
            const res = await consentApi.getMyConsents(filterActiveOnly);
            setConsents(res);
        } catch (err: any) {
            console.error('Failed to load patient consents:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const loadDoctors = async () => {
        try {
            const res: DoctorListResponse = await appointmentBookingApi.getDoctors();
            setDoctors(res.doctors);
            if (res.doctors.length > 0) {
                setSelectedDoctorId(res.doctors[0].doctor_id);
            }
        } catch (err) {
            console.error('Failed to load doctors list:', err);
        }
    };

    const handleGrantConsent = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedDoctorId) {
            setGrantError('Please select a healthcare provider.');
            return;
        }

        setIsGranting(true);
        setGrantError(null);
        try {
            await consentApi.grantConsent({
                provider_id: selectedDoctorId,
                record_scope: selectedScope,
            });
            setActionSuccess('Consent agreement granted successfully and recorded in immutable audit log.');
            setIsGrantModalOpen(false);
            await loadConsents();
        } catch (err: any) {
            setGrantError(err.message || 'Failed to grant consent agreement');
        } finally {
            setIsGranting(false);
        }
    };

    const handleRevokeConsent = async (consent: ConsentItem) => {
        if (!confirm(`Are you sure you want to revoke consent for ${consent.provider_name || 'this provider'}? The doctor will immediately lose access to your medical records.`)) {
            return;
        }

        setRevokingId(consent.consent_id);
        setActionSuccess(null);
        try {
            await consentApi.revokeConsent(consent.consent_id);
            setActionSuccess(`Consent access for ${consent.provider_name || 'provider'} has been revoked.`);
            await loadConsents();
        } catch (err: any) {
            alert(err.message || 'Failed to revoke consent');
        } finally {
            setRevokingId(null);
        }
    };

    const formatDate = (isoString: string) => {
        const d = new Date(isoString);
        return d.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const activeCount = consents.filter((c) => c.is_active).length;

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <Link href="/patient" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs">
                            ← Patient Portal
                        </Link>
                        <span className="text-slate-300 dark:text-slate-700">•</span>
                        <Badge variant="primary" className="text-[10px] uppercase font-bold">
                            ABDM Milestone M2
                        </Badge>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-1 flex items-center gap-2">
                        <span>🛡️ ABHA Health Identity & Provider Consents</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Manage ABDM electronic health record consents, authorize physician record access, and enforce data sovereignty.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <Button
                        variant="primary"
                        onClick={() => setIsGrantModalOpen(true)}
                        className="text-xs font-semibold px-4 py-2 flex items-center gap-1.5"
                    >
                        <span>+ Grant Provider Consent</span>
                    </Button>
                </div>
            </div>

            {actionSuccess && (
                <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs flex items-center justify-between animate-fade-in">
                    <span>✓ {actionSuccess}</span>
                    <button onClick={() => setActionSuccess(null)} className="font-bold">✕</button>
                </div>
            )}

            {/* ABHA Digital Identity Card & Sovereign Rights Banner */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* ABHA ID Card (1 Col) */}
                <Card className="border border-blue-200 dark:border-blue-900/60 bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-lg overflow-hidden relative">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl pointer-events-none" />
                    <CardContent className="p-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold tracking-wider uppercase bg-white/20 px-2.5 py-0.5 rounded-full">
                                ABDM Ayushman Bharat
                            </span>
                            <span className="text-xs font-mono font-bold text-emerald-300">
                                Active & Linked
                            </span>
                        </div>

                        <div className="pt-2">
                            <span className="text-[11px] text-blue-200 uppercase tracking-wider block">
                                Digital Health Address
                            </span>
                            <h3 className="text-lg font-bold font-mono tracking-wide mt-0.5">
                                {user?.email ? `${user.email.split('@')[0]}@abdm` : 'patient.abha@abdm'}
                            </h3>
                        </div>

                        <div className="pt-2 border-t border-white/15 flex items-center justify-between text-xs">
                            <div>
                                <span className="text-[10px] text-blue-200 uppercase block">Holder</span>
                                <span className="font-semibold">{user?.full_name || 'Authorized Patient'}</span>
                            </div>
                            <div className="text-right">
                                <span className="text-[10px] text-blue-200 uppercase block">Health ID</span>
                                <span className="font-mono text-[11px]">91-8821-4412</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Patient Sovereign Rights Information (2 Cols) */}
                <Card className="lg:col-span-2 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-6 space-y-3 text-xs text-slate-600 dark:text-slate-300">
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <span>📜 Patient Data Sovereignty & Revocation Rights</span>
                        </h3>
                        <p className="leading-relaxed">
                            Under the Ayushman Bharat Digital Mission (ABDM) and HIPAA privacy frameworks, you have exclusive sovereign ownership of your clinical electronic health records. Healthcare providers cannot inspect your diagnostic reports, prescriptions, or clinical notes without an active, explicit consent authorization.
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                                <span className="font-bold text-slate-900 dark:text-white block mb-0.5">
                                    Instant Revocation
                                </span>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                    Revoke access at any moment. Provider access is terminated immediately.
                                </p>
                            </div>

                            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                                <span className="font-bold text-slate-900 dark:text-white block mb-0.5">
                                    Immutable Audit Trail
                                </span>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                    Every grant, revocation, and record read is recorded in an unalterable audit log.
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Consents Filter Toolbar */}
            <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setFilterActiveOnly(false)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                            !filterActiveOnly
                                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                        }`}
                    >
                        All Agreements ({consents.length})
                    </button>
                    <button
                        onClick={() => setFilterActiveOnly(true)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                            filterActiveOnly
                                ? 'bg-emerald-600 text-white'
                                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                        }`}
                    >
                        Active Only ({activeCount})
                    </button>
                </div>

                <span className="text-xs text-slate-500 dark:text-slate-400">
                    Showing {consents.length} consent {consents.length === 1 ? 'record' : 'records'}
                </span>
            </div>

            {/* Consents List */}
            {isLoading ? (
                <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="p-5 animate-pulse border border-slate-200 dark:border-slate-800">
                            <div className="h-4 w-1/3 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                            <div className="h-3 w-1/2 bg-slate-200 dark:bg-slate-700 rounded" />
                        </Card>
                    ))}
                </div>
            ) : consents.length === 0 ? (
                <Card className="border border-dashed border-slate-300 dark:border-slate-800 p-12 text-center bg-white dark:bg-slate-900">
                    <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center text-xl mb-3">
                        🛡️
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                        No consent authorizations found
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                        You have not granted medical record access to any healthcare providers yet. Click below to authorize a physician.
                    </p>
                    <div className="mt-4">
                        <Button
                            variant="primary"
                            onClick={() => setIsGrantModalOpen(true)}
                            className="text-xs font-semibold px-4 py-2"
                        >
                            + Grant Your First Consent
                        </Button>
                    </div>
                </Card>
            ) : (
                <div className="space-y-3">
                    {consents.map((consent) => (
                        <Card
                            key={consent.consent_id}
                            className={`border transition-all bg-white dark:bg-slate-900 shadow-sm ${
                                consent.is_active
                                    ? 'border-slate-200 dark:border-slate-800 hover:border-slate-300'
                                    : 'border-slate-200 dark:border-slate-800 opacity-60 bg-slate-50/50 dark:bg-slate-900/40'
                            }`}
                        >
                            <CardContent className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div className="flex items-start gap-3.5">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0 ${
                                        consent.is_active
                                            ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400'
                                            : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                                    }`}>
                                        {consent.is_active ? '🛡️' : '🔒'}
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                                                {consent.provider_name || 'Healthcare Provider'}
                                            </h4>
                                            <Badge
                                                variant={consent.is_active ? 'success' : 'neutral'}
                                                className="text-[10px] uppercase font-bold tracking-wider"
                                            >
                                                {consent.is_active ? 'Active' : 'Revoked'}
                                            </Badge>
                                        </div>

                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                            {consent.provider_specialty || 'General Practice'} • {consent.provider_hospital || 'AI-HOS Health Center'}
                                        </p>

                                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400 mt-2">
                                            <span>Scope: <strong className="text-slate-700 dark:text-slate-200 uppercase">{consent.record_scope.replace('_', ' ')}</strong></span>
                                            <span>•</span>
                                            <span>Granted: {formatDate(consent.granted_at)}</span>
                                            {consent.revoked_at && (
                                                <>
                                                    <span>•</span>
                                                    <span className="text-rose-600 dark:text-rose-400">Revoked on: {formatDate(consent.revoked_at)}</span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="self-end sm:self-center shrink-0">
                                    {consent.is_active ? (
                                        <Button
                                            variant="danger"
                                            size="sm"
                                            disabled={revokingId === consent.consent_id}
                                            onClick={() => handleRevokeConsent(consent)}
                                            className="text-xs"
                                        >
                                            {revokingId === consent.consent_id ? 'Revoking...' : 'Revoke Access'}
                                        </Button>
                                    ) : (
                                        <span className="text-xs text-slate-400 italic">
                                            Access Terminated
                                        </span>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Grant Consent Modal */}
            {isGrantModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <h3 className="font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
                                <span>🛡️ Authorize Provider Consent</span>
                            </h3>
                            <button
                                onClick={() => setIsGrantModalOpen(false)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleGrantConsent} className="space-y-4">
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                    Select Healthcare Provider *
                                </label>
                                <select
                                    value={selectedDoctorId}
                                    onChange={(e) => setSelectedDoctorId(e.target.value)}
                                    className="w-full text-sm px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    required
                                >
                                    {doctors.map((d) => (
                                        <option key={d.doctor_id} value={d.doctor_id}>
                                            {d.full_name} ({d.specialty}) - {d.hospital_affiliation || 'AI-HOS'}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                    Authorization Scope *
                                </label>
                                <select
                                    value={selectedScope}
                                    onChange={(e) => setSelectedScope(e.target.value)}
                                    className="w-full text-sm px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                >
                                    <option value="full_access">Full Access (EHR Records, Scans, Notes & Prescriptions)</option>
                                    <option value="records_only">Medical Records & Diagnostic Reports Only</option>
                                    <option value="appointments_only">Appointments & Consultation Logs Only</option>
                                    <option value="notes_only">Clinical Visit Notes Only</option>
                                </select>
                            </div>

                            <div className="p-3 bg-blue-50 dark:bg-blue-950/40 rounded-xl border border-blue-100 dark:border-blue-900/40 text-blue-900 dark:text-blue-200 text-xs leading-relaxed">
                                ℹ️ <strong>Legal Attestation:</strong> By granting this agreement, you authorize the physician to access your electronic health records according to the selected scope. You may revoke access at any time.
                            </div>

                            {grantError && (
                                <div className="p-3 text-xs rounded-lg bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                                    ⚠️ {grantError}
                                </div>
                            )}

                            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    onClick={() => setIsGrantModalOpen(false)}
                                    className="text-xs"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    disabled={isGranting}
                                    className="text-xs font-semibold px-4 py-2"
                                >
                                    {isGranting ? 'Granting...' : 'Authorize Consent'}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
