'use client';

import React, { useState, useEffect } from 'react';
import { patientPortalApi, Patient, PatientSelfUpdate } from '@/lib/api';
import { Card, CardContent, Button, Input, Alert, Badge } from '@/components/ui';

export default function PatientProfilePage() {
    const [patient, setPatient] = useState<Patient | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [statusBanner, setStatusBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    // Form fields
    const [fullName, setFullName] = useState('');
    const [phone, setPhone] = useState('');
    const [address, setAddress] = useState('');
    const [emergencyName, setEmergencyName] = useState('');
    const [emergencyPhone, setEmergencyPhone] = useState('');
    const [abhaAddress, setAbhaAddress] = useState('');

    useEffect(() => {
        loadProfile();
    }, []);

    const loadProfile = async () => {
        setIsLoading(true);
        try {
            const data = await patientPortalApi.getProfile();
            setPatient(data);
            setFullName(data.full_name || '');
            setPhone(data.phone || '');
            setAddress(data.address || '');
            setEmergencyName(data.emergency_contact_name || '');
            setEmergencyPhone(data.emergency_contact_phone || '');
            setAbhaAddress(data.abha_address || '');
        } catch (err) {
            console.error('Failed to load profile:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        setStatusBanner(null);

        const updatePayload: PatientSelfUpdate = {
            full_name: fullName,
            phone: phone || undefined,
            address: address || undefined,
            emergency_contact_name: emergencyName || undefined,
            emergency_contact_phone: emergencyPhone || undefined,
            abha_address: abhaAddress || undefined,
        };

        try {
            const updated = await patientPortalApi.updateProfile(updatePayload);
            setPatient(updated);
            setStatusBanner({
                type: 'success',
                message: 'Your health profile and emergency contacts were successfully saved.',
            });
        } catch (err: any) {
            console.error('Failed to update profile:', err);
            setStatusBanner({
                type: 'error',
                message: err.message || 'Failed to update profile. Please try again.',
            });
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="space-y-6 pb-12 max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                        <span>👤 My Health Profile & Settings</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Manage your demographics, emergency contacts, address, and digital health identifiers.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Badge variant="success">Verified Patient Record</Badge>
                </div>
            </div>

            {/* Notification Alert */}
            {statusBanner && (
                <Alert
                    variant={statusBanner.type === 'success' ? 'success' : 'error'}
                    title={statusBanner.type === 'success' ? 'Profile Updated' : 'Update Error'}
                    onClose={() => setStatusBanner(null)}
                >
                    {statusBanner.message}
                </Alert>
            )}

            {isLoading ? (
                <Card className="p-8 animate-pulse border border-slate-200 dark:border-slate-800">
                    <div className="h-6 w-1/4 bg-slate-200 dark:bg-slate-700 rounded mb-4" />
                    <div className="h-4 w-1/2 bg-slate-200 dark:bg-slate-700 rounded" />
                </Card>
            ) : (
                <form onSubmit={handleSave} className="space-y-6">
                    {/* Read-Only Identity Card */}
                    <Card className="border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40">
                        <CardContent className="p-5 space-y-3">
                            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Permanent Health Identification
                            </h3>
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                                <div>
                                    <span className="text-slate-400 block text-[11px]">Registered Email</span>
                                    <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">
                                        {patient?.email || 'N/A'}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-slate-400 block text-[11px]">Date of Birth</span>
                                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                                        {patient?.date_of_birth ? new Date(patient.date_of_birth).toLocaleDateString() : 'N/A'}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-slate-400 block text-[11px]">Biological Gender</span>
                                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                                        {patient?.gender || 'Not Specified'}
                                    </span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Editable Demographics & Contact */}
                    <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-6 space-y-4">
                            <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2">
                                Contact & Residential Information
                            </h3>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                        Full Name
                                    </label>
                                    <Input
                                        value={fullName}
                                        onChange={(e) => setFullName(e.target.value)}
                                        placeholder="John Doe"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                        Phone Number
                                    </label>
                                    <Input
                                        value={phone}
                                        onChange={(e) => setPhone(e.target.value)}
                                        placeholder="+91 98765 43210"
                                    />
                                </div>

                                <div className="sm:col-span-2">
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                        Residential Address
                                    </label>
                                    <Input
                                        value={address}
                                        onChange={(e) => setAddress(e.target.value)}
                                        placeholder="Flat 402, Green Valley Apartments, Mumbai"
                                    />
                                </div>

                                <div className="sm:col-span-2">
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                        ABHA Address / ABDM ID (Optional)
                                    </label>
                                    <Input
                                        value={abhaAddress}
                                        onChange={(e) => setAbhaAddress(e.target.value)}
                                        placeholder="patient@abdm"
                                    />
                                    <span className="text-[11px] text-slate-400 mt-0.5 block">
                                        Links your national Ayushman Bharat Digital Mission health records.
                                    </span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Emergency Contacts */}
                    <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-6 space-y-4">
                            <h3 className="text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-1.5">
                                <span>🚨</span> Emergency Contact Details
                            </h3>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                        Contact Person Name
                                    </label>
                                    <Input
                                        value={emergencyName}
                                        onChange={(e) => setEmergencyName(e.target.value)}
                                        placeholder="Spouse / Parent / Next of Kin"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                        Emergency Phone Number
                                    </label>
                                    <Input
                                        value={emergencyPhone}
                                        onChange={(e) => setEmergencyPhone(e.target.value)}
                                        placeholder="+91 98765 00000"
                                    />
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Save Button */}
                    <div className="flex items-center justify-end gap-3 pt-2">
                        <Button
                            type="submit"
                            variant="primary"
                            size="md"
                            disabled={isSaving}
                        >
                            {isSaving ? 'Saving Changes...' : '💾 Save Profile & Settings'}
                        </Button>
                    </div>
                </form>
            )}
        </div>
    );
}
