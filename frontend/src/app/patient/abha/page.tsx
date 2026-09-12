'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import {
    consentApi,
    ConsentItem,
    appointmentBookingApi,
    DoctorListResponse,
    Doctor,
    patientPortalApi,
    PatientProfile,
    abdmApi,
    AbdmStatusResponse,
} from '@/lib/api';
import { Button, Card, CardContent, Badge } from '@/components/ui';

export default function PatientAbhaConsentPage() {
    const { user } = useAuth();
    const [patientProfile, setPatientProfile] = useState<PatientProfile | null>(null);
    const [abdmStatus, setAbdmStatus] = useState<AbdmStatusResponse | null>(null);
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

    // ABHA Linking 2-Step OTP Modal State (Milestone U-21)
    const [isAbhaModalOpen, setIsAbhaModalOpen] = useState(false);
    const [abhaAddressInput, setAbhaAddressInput] = useState('');
    const [linkingStep, setLinkingStep] = useState<'address' | 'otp'>('address');
    const [linkingTxId, setLinkingTxId] = useState<string | null>(null);
    const [otpInput, setOtpInput] = useState('');
    const [isSubmittingAbha, setIsSubmittingAbha] = useState(false);
    const [abhaError, setAbhaError] = useState<string | null>(null);

    useEffect(() => {
        loadData();
    }, [filterActiveOnly]);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [consentsRes, profileRes, statusRes, docRes] = await Promise.allSettled([
                consentApi.getMyConsents(filterActiveOnly),
                patientPortalApi.getProfile(),
                abdmApi.getStatus(),
                appointmentBookingApi.getDoctors(),
            ]);

            if (consentsRes.status === 'fulfilled') setConsents(consentsRes.value);
            if (profileRes.status === 'fulfilled') {
                setPatientProfile(profileRes.value);
                if (profileRes.value.abha_address) {
                    setAbhaAddressInput(profileRes.value.abha_address);
                }
            }
            if (statusRes.status === 'fulfilled') setAbdmStatus(statusRes.value);
            if (docRes.status === 'fulfilled') {
                setDoctors(docRes.value.doctors);
                if (docRes.value.doctors.length > 0) {
                    setSelectedDoctorId(docRes.value.doctors[0].doctor_id);
                }
            }
        } catch (err: any) {
            console.error('Failed to load ABDM consent console data:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleOpenAbhaLinkModal = () => {
        setLinkingStep('address');
        setLinkingTxId(null);
        setOtpInput('');
        setAbhaError(null);
        setIsAbhaModalOpen(true);
    };

    const handleSendAbhaOtp = async (e: React.FormEvent) => {
        e.preventDefault();
        const address = abhaAddressInput.trim().toLowerCase();
        if (!address) {
            setAbhaError('Please enter a valid ABHA address (e.g. rahul@abdm)');
            return;
        }

        setIsSubmittingAbha(true);
        setAbhaError(null);
        try {
            const res = await abdmApi.initAbhaLinking(address);
            setLinkingTxId(res.transaction_id);
            setLinkingStep('otp');
            if (res.sandbox_test_otp) {
                setOtpInput(res.sandbox_test_otp); // Pre-fill test OTP for sandbox convenience
            }
        } catch (err: any) {
            setAbhaError(err?.message || 'Failed to dispatch verification OTP. Please verify address format.');
        } finally {
            setIsSubmittingAbha(false);
        }
    };

    const handleVerifyAbhaOtp = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!linkingTxId || !otpInput.trim()) {
            setAbhaError('Please enter the 6-digit verification code.');
            return;
        }

        setIsSubmittingAbha(true);
        setAbhaError(null);
        try {
            const res = await abdmApi.verifyAbhaOtp(linkingTxId, otpInput.trim());
            setActionSuccess(`ABHA Health Address (${res.abha_address}) linked successfully.`);
            setIsAbhaModalOpen(false);
            // Refresh patient profile
            const updatedProfile = await patientPortalApi.getProfile();
            setPatientProfile(updatedProfile);
        } catch (err: any) {
            setAbhaError(err?.message || 'Invalid or expired OTP. Please check the code and retry.');
        } finally {
            setIsSubmittingAbha(false);
        }
    };

    const handleUnlinkAbha = async () => {
        if (!confirm('Are you sure you want to unlink your ABHA address from this clinical account?')) {
            return;
        }
        try {
            await abdmApi.unlinkAbha();
            setActionSuccess('ABHA address unlinked successfully.');
            const updatedProfile = await patientPortalApi.getProfile();
            setPatientProfile(updatedProfile);
        } catch (err: any) {
            alert(err?.message || 'Failed to unlink ABHA');
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
            const res = await consentApi.getMyConsents(filterActiveOnly);
            setConsents(res);
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
            const res = await consentApi.getMyConsents(filterActiveOnly);
            setConsents(res);
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
        });
    };

    const isAbhaLinked = Boolean(patientProfile?.abha_address);
    const activeAbhaAddress = patientProfile?.abha_address || (user?.email ? `${user.email.split('@')[0]}@abdm` : 'unlinked@abdm');

    return (
        <div className="space-y-6 pb-12 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <Badge variant="primary" className="text-xs uppercase font-mono tracking-wider">
                            ABDM Milestone U-21
                        </Badge>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
                            Sandbox Isolation Active
                        </span>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-1 flex items-center gap-2">
                        <span>🛡️ ABHA Health Identity & ABDM Consent Console</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Manage Ayushman Bharat Digital Mission (ABDM) electronic health records, link your national health ID, and authorize provider access.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2.5">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleOpenAbhaLinkModal}
                        className="text-xs font-semibold"
                    >
                        <span>🔗</span>
                        <span>{isAbhaLinked ? 'Change ABHA ID' : 'Link ABHA ID'}</span>
                    </Button>
                    <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setIsGrantModalOpen(true)}
                        className="text-xs font-semibold px-4 flex items-center gap-1.5"
                    >
                        <span>+ Authorize Provider</span>
                    </Button>
                </div>
            </div>

            {actionSuccess && (
                <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs flex items-center justify-between animate-fadeIn">
                    <span>✓ {actionSuccess}</span>
                    <button onClick={() => setActionSuccess(null)} className="font-bold">✕</button>
                </div>
            )}

            {/* ABHA Digital Identity Card & Sovereign Rights Banner */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* ABHA ID Card (1 Col) */}
                <Card className="border border-blue-200 dark:border-blue-900/60 bg-gradient-to-br from-blue-600 via-indigo-600 to-indigo-800 text-white shadow-lg overflow-hidden relative">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl pointer-events-none" />
                    <CardContent className="p-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold tracking-wider uppercase bg-white/20 px-2.5 py-0.5 rounded-full">
                                ABDM Ayushman Bharat
                            </span>
                            <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                                isAbhaLinked
                                    ? 'bg-emerald-400/20 text-emerald-300'
                                    : 'bg-amber-400/20 text-amber-200'
                            }`}>
                                {isAbhaLinked ? '● Verified & Linked' : '○ Not Linked'}
                            </span>
                        </div>

                        <div className="pt-2">
                            <span className="text-[11px] text-blue-200 uppercase tracking-wider block">
                                Digital Health Address
                            </span>
                            <h3 className="text-lg font-bold font-mono tracking-wide mt-0.5 break-all">
                                {isAbhaLinked ? patientProfile?.abha_address : activeAbhaAddress}
                            </h3>
                        </div>

                        <div className="pt-2 border-t border-white/15 flex items-center justify-between text-xs">
                            <div>
                                <span className="text-[10px] text-blue-200 uppercase block">Holder</span>
                                <span className="font-semibold">{patientProfile?.full_name || user?.full_name || 'Authorized Patient'}</span>
                            </div>
                            <div className="text-right">
                                <span className="text-[10px] text-blue-200 uppercase block">Facility Node</span>
                                <span className="font-mono text-[11px] text-indigo-200">{abdmStatus?.hfr_facility_id || 'IN-DL-AIHOS-001'}</span>
                            </div>
                        </div>

                        {isAbhaLinked && (
                            <div className="pt-1">
                                <button
                                    type="button"
                                    onClick={handleUnlinkAbha}
                                    className="text-[11px] text-rose-200 hover:text-white underline transition"
                                >
                                    Unlink this ABHA address
                                </button>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* ABDM Ecosystem & Sovereign Rights Card (2 Cols) */}
                <Card className="lg:col-span-2 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-6 space-y-3.5 text-xs text-slate-600 dark:text-slate-300">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <span>🏛️ National Digital Health Network (HIP / HIU)</span>
                            </h3>
                            <span className="text-[11px] font-mono text-slate-400">
                                Sandbox: Online
                            </span>
                        </div>
                        <p className="leading-relaxed">
                            Under the Ayushman Bharat Digital Mission (ABDM) and national consent architecture, you have exclusive sovereign ownership of your clinical health data. Healthcare providers cannot inspect your diagnostic reports, prescriptions, or clinical notes without an active, explicit consent authorization.
                        </p>
                        
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
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
                                    Zero Credential Leak
                                </span>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                    Gateway secrets remain strictly isolated inside the security boundary.
                                </p>
                            </div>

                            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                                <span className="font-bold text-slate-900 dark:text-white block mb-0.5">
                                    HFR Registered Node
                                </span>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                    Facility {abdmStatus?.hfr_facility_id || 'IN-DL-AIHOS-001'} (AI-HOS Apex Center).
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Consents Filter Toolbar */}
            <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-slate-900 dark:text-white">
                        Authorized Provider Agreements
                    </h2>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono">
                        {consents.length}
                    </span>
                </div>

                <div className="flex items-center gap-2 text-xs">
                    <label className="flex items-center gap-1.5 cursor-pointer text-slate-600 dark:text-slate-300">
                        <input
                            type="checkbox"
                            checked={filterActiveOnly}
                            onChange={(e) => setFilterActiveOnly(e.target.checked)}
                            className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span>Active only</span>
                    </label>
                </div>
            </div>

            {/* Consents Table */}
            <Card className="border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                {isLoading ? (
                    <div className="p-12 text-center text-slate-400 text-sm">
                        Loading consent authorizations...
                    </div>
                ) : consents.length === 0 ? (
                    <div className="p-12 text-center text-slate-400 text-sm space-y-2">
                        <p>No consent agreements found.</p>
                        <p className="text-xs text-slate-500">
                            Click <strong>"+ Authorize Provider"</strong> to grant temporary access to your medical records.
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs border-collapse">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 font-semibold">
                                    <th className="p-3.5 pl-4">Healthcare Provider</th>
                                    <th className="p-3.5">Specialty & Hospital</th>
                                    <th className="p-3.5">Access Scope</th>
                                    <th className="p-3.5">Granted Date</th>
                                    <th className="p-3.5">Status</th>
                                    <th className="p-3.5 pr-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                                {consents.map((consent) => (
                                    <tr key={consent.consent_id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                                        <td className="p-3.5 pl-4 font-semibold text-slate-900 dark:text-white">
                                            {consent.provider_name || 'Attending Physician'}
                                        </td>
                                        <td className="p-3.5 text-slate-600 dark:text-slate-300">
                                            {consent.provider_specialty || 'General Medicine'}
                                            <span className="block text-[11px] text-slate-400">
                                                {consent.provider_hospital || 'AI-HOS Medical Network'}
                                            </span>
                                        </td>
                                        <td className="p-3.5">
                                            <span className="inline-block px-2.5 py-1 rounded-md text-[11px] font-mono bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-900/40">
                                                {consent.record_scope}
                                            </span>
                                        </td>
                                        <td className="p-3.5 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                                            {formatDate(consent.granted_at)}
                                        </td>
                                        <td className="p-3.5">
                                            {consent.is_active ? (
                                                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-full">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                                    Active
                                                </span>
                                            ) : (
                                                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-full">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                                                    Revoked
                                                </span>
                                            )}
                                        </td>
                                        <td className="p-3.5 pr-4 text-right">
                                            {consent.is_active ? (
                                                <Button
                                                    variant="secondary"
                                                    size="sm"
                                                    onClick={() => handleRevokeConsent(consent)}
                                                    disabled={revokingId === consent.consent_id}
                                                    className="text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border-rose-200 dark:border-rose-900"
                                                >
                                                    {revokingId === consent.consent_id ? 'Revoking...' : 'Revoke Access'}
                                                </Button>
                                            ) : (
                                                <span className="text-[11px] text-slate-400 italic">
                                                    {consent.revoked_at ? `Revoked ${formatDate(consent.revoked_at)}` : 'Inactive'}
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </Card>

            {/* ABHA Linking 2-Step OTP Modal (Milestone U-21) */}
            {isAbhaModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4 overflow-y-auto animate-fadeIn">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden my-8">
                        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/80 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2">
                                <span className="text-lg">🇮🇳</span>
                                <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                                    Link National ABHA Health ID
                                </h3>
                            </div>
                            <button
                                onClick={() => setIsAbhaModalOpen(false)}
                                className="text-slate-400 hover:text-slate-600 transition"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="p-6 space-y-4 text-xs">
                            {abhaError && (
                                <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300">
                                    {abhaError}
                                </div>
                            )}

                            {linkingStep === 'address' ? (
                                <form onSubmit={handleSendAbhaOtp} className="space-y-4">
                                    <div>
                                        <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                                            Enter your ABHA Address
                                        </label>
                                        <input
                                            type="text"
                                            value={abhaAddressInput}
                                            onChange={(e) => setAbhaAddressInput(e.target.value)}
                                            placeholder="e.g. rahul@abdm or 14-digit number"
                                            required
                                            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                                        />
                                        <p className="text-[11px] text-slate-400 mt-1">
                                            A 6-digit verification code will be sent to your registered mobile number.
                                        </p>
                                    </div>

                                    <div className="p-3 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/40 text-indigo-800 dark:text-indigo-300 text-[11px] leading-relaxed">
                                        💡 <strong>ABDM Sandbox Environment:</strong> Simulated OTP verification is active. You can enter any mock address like <code>patient@abdm</code>.
                                    </div>

                                    <div className="pt-2 flex justify-end gap-2">
                                        <Button
                                            type="button"
                                            variant="secondary"
                                            size="sm"
                                            onClick={() => setIsAbhaModalOpen(false)}
                                        >
                                            Cancel
                                        </Button>
                                        <Button
                                            type="submit"
                                            variant="primary"
                                            size="sm"
                                            disabled={isSubmittingAbha || !abhaAddressInput.trim()}
                                        >
                                            {isSubmittingAbha ? 'Dispatching OTP...' : 'Send Verification OTP →'}
                                        </Button>
                                    </div>
                                </form>
                            ) : (
                                <form onSubmit={handleVerifyAbhaOtp} className="space-y-4">
                                    <div>
                                        <div className="flex items-center justify-between mb-1.5">
                                            <label className="font-semibold text-slate-700 dark:text-slate-300">
                                                Enter 6-Digit Verification OTP
                                            </label>
                                            <button
                                                type="button"
                                                onClick={() => setLinkingStep('address')}
                                                className="text-[11px] text-indigo-600 hover:underline"
                                            >
                                                Change Address
                                            </button>
                                        </div>
                                        <input
                                            type="text"
                                            value={otpInput}
                                            onChange={(e) => setOtpInput(e.target.value)}
                                            maxLength={6}
                                            placeholder="123456"
                                            required
                                            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-base tracking-widest font-mono text-center focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                                        />
                                        <p className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1">
                                            Sandbox test OTP is <strong>123456</strong>.
                                        </p>
                                    </div>

                                    <div className="pt-2 flex justify-end gap-2">
                                        <Button
                                            type="button"
                                            variant="secondary"
                                            size="sm"
                                            onClick={() => setIsAbhaModalOpen(false)}
                                        >
                                            Cancel
                                        </Button>
                                        <Button
                                            type="submit"
                                            variant="primary"
                                            size="sm"
                                            disabled={isSubmittingAbha || !otpInput.trim()}
                                        >
                                            {isSubmittingAbha ? 'Verifying...' : 'Verify & Link ABHA'}
                                        </Button>
                                    </div>
                                </form>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Grant Provider Consent Modal */}
            {isGrantModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4 overflow-y-auto animate-fadeIn">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden my-8">
                        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/80 dark:bg-slate-800/50">
                            <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                                Authorize Provider Consent Agreement
                            </h3>
                            <button
                                onClick={() => setIsGrantModalOpen(false)}
                                className="text-slate-400 hover:text-slate-600 transition"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleGrantConsent} className="p-6 space-y-4 text-xs">
                            {grantError && (
                                <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300">
                                    {grantError}
                                </div>
                            )}

                            <div>
                                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                                    Select Healthcare Practitioner (Doctor)
                                </label>
                                <select
                                    value={selectedDoctorId}
                                    onChange={(e) => setSelectedDoctorId(e.target.value)}
                                    required
                                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                                >
                                    {doctors.map((doc) => (
                                        <option key={doc.doctor_id} value={doc.doctor_id}>
                                            {doc.full_name} — {doc.specialty} ({doc.hospital_affiliation || 'AI-HOS Node'})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                                    Data Access Scope
                                </label>
                                <select
                                    value={selectedScope}
                                    onChange={(e) => setSelectedScope(e.target.value)}
                                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                                >
                                    <option value="full_access">Full Access (Medical Records, Prescriptions, Appointments)</option>
                                    <option value="records_only">Clinical Progress Notes Only</option>
                                    <option value="appointments_only">Appointment Scheduling Only</option>
                                    <option value="notes_only">Encounter Notes Only</option>
                                </select>
                            </div>

                            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-[11px] leading-relaxed">
                                🔒 <strong>Legal Attestation:</strong> By authorizing this agreement, you grant the selected physician clinical access to review your health records under ABDM sovereign consent standards. You may revoke this permission at any time.
                            </div>

                            <div className="pt-2 flex justify-end gap-2">
                                <Button
                                    type="button"
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setIsGrantModalOpen(false)}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    size="sm"
                                    disabled={isGranting}
                                >
                                    {isGranting ? 'Recording Consent...' : 'Authorize & Sign Consent'}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
