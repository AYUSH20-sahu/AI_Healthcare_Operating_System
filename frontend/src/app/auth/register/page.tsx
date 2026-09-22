'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import {
    Card,
    CardContent,
    Button,
    Input,
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

const FACILITY_TYPES = [
    'Multi-Specialty Hospital',
    'General Hospital',
    'Emergency & Trauma Center',
    'Clinic / Polyclinic',
    'Diagnostic & Imaging Center',
    'Specialty Surgical Center',
];

const AVAILABLE_DEPARTMENTS = [
    'Cardiology',
    'Neurology',
    'Emergency / Trauma',
    'Pediatrics',
    'Oncology',
    'Orthopedics',
    'General Surgery',
    'Radiology & Imaging',
    'Nephrology',
    'Obstetrics & Gynecology',
    'Critical Care / ICU',
    'Pathology & Lab',
];

export default function RegisterOrganizationPage() {
    const router = useRouter();
    const { registerOrg } = useAuth();

    // Wizard Step State (1 - 4)
    const [step, setStep] = useState<1 | 2 | 3 | 4>(1);

    // Step 1: Admin & Basic Facility Details
    const [orgName, setOrgName] = useState('');
    const [orgCode, setOrgCode] = useState('');
    const [orgAddress, setOrgAddress] = useState('');
    const [adminName, setAdminName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');

    // Step 2: Clinical Facility & Departments
    const [facilityType, setFacilityType] = useState('Multi-Specialty Hospital');
    const [departments, setDepartments] = useState<string[]>([
        'Emergency / Trauma',
        'Cardiology',
        'General Surgery',
        'Critical Care / ICU',
    ]);
    const [totalBeds, setTotalBeds] = useState<number>(150);
    const [icuBeds, setIcuBeds] = useState<number>(24);
    const [hasEmergency, setHasEmergency] = useState<boolean>(true);
    const [hasAmbulance, setHasAmbulance] = useState<boolean>(true);

    // Step 3: Regulatory & Licensing
    const [licenseNumber, setLicenseNumber] = useState('');
    const [abdmFacilityId, setAbdmFacilityId] = useState('');
    const [insuranceNetworkCode, setInsuranceNetworkCode] = useState('');

    // Step 4: Operational Settings & Safety Governance
    const [emergencyHotline, setEmergencyHotline] = useState('');
    const [operatingHours, setOperatingHours] = useState('24/7 Inpatient & Trauma | OPD: 08:00 - 20:00');
    const [clinicalReviewPolicy, setClinicalReviewPolicy] = useState<boolean>(true);
    const [termsAccepted, setTermsAccepted] = useState(false);

    // Status
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const toggleDepartment = (dept: string) => {
        if (departments.includes(dept)) {
            setDepartments(departments.filter((d) => d !== dept));
        } else {
            setDepartments([...departments, dept]);
        }
    };

    const validateStep1 = () => {
        if (!orgName.trim()) {
            setError('Please provide the Healthcare Organization / Facility name.');
            return false;
        }
        if (!adminName.trim()) {
            setError('Please provide the Lead Administrator legal name.');
            return false;
        }
        if (!email.trim() || !email.includes('@')) {
            setError('Please enter a valid institutional work email address.');
            return false;
        }
        if (!phone.trim()) {
            setError('Please enter an official contact phone number.');
            return false;
        }
        if (password.length < 8) {
            setError('Administrator password must be at least 8 characters long.');
            return false;
        }
        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return false;
        }
        setError(null);
        return true;
    };

    const validateStep2 = () => {
        if (departments.length === 0) {
            setError('Please select at least one clinical department.');
            return false;
        }
        if (totalBeds < 1 || totalBeds > 10000) {
            setError('Total bed capacity must be between 1 and 10,000 (largest hospital complex capacity limit).');
            return false;
        }
        if (icuBeds < 0 || icuBeds > 2500) {
            setError('Dedicated ICU / Critical bed capacity cannot exceed 2,500.');
            return false;
        }
        if (icuBeds > totalBeds) {
            setError(`Dedicated ICU beds (${icuBeds}) cannot exceed total inpatient bed capacity (${totalBeds}).`);
            return false;
        }
        setError(null);
        return true;
    };

    const validateStep3 = () => {
        setError(null);
        return true;
    };

    const handleNext = () => {
        if (step === 1 && validateStep1()) {
            setStep(2);
        } else if (step === 2 && validateStep2()) {
            setStep(3);
        } else if (step === 3 && validateStep3()) {
            setStep(4);
        }
    };

    const handleBack = () => {
        setError(null);
        if (step > 1) {
            setStep((s) => (s - 1) as 1 | 2 | 3 | 4);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!termsAccepted) {
            setError('You must confirm administrative governance authority to initialize this medical facility.');
            return;
        }

        try {
            setSubmitting(true);
            await registerOrg({
                organization_name: orgName.trim(),
                organization_code: orgCode.trim() ? orgCode.trim().toUpperCase() : undefined,
                organization_address: orgAddress.trim() || undefined,
                admin_name: adminName.trim(),
                email: email.trim().toLowerCase(),
                phone: phone.trim() || undefined,
                password,
                // Step 2
                facility_type: facilityType,
                departments: departments,
                total_beds: totalBeds,
                icu_beds: icuBeds,
                has_emergency: hasEmergency,
                has_ambulance: hasAmbulance,
                // Step 3
                license_number: licenseNumber.trim() || undefined,
                abdm_facility_id: abdmFacilityId.trim() || undefined,
                insurance_network_code: insuranceNetworkCode.trim() || undefined,
                // Step 4
                emergency_hotline: emergencyHotline.trim() || undefined,
                operating_hours: operatingHours.trim() || undefined,
                clinical_review_policy: clinicalReviewPolicy
                    ? 'Strict Doctor Sign-Off Required'
                    : 'Standard Governance',
            });

            router.push('/admin');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Organization registration failed. Please try again.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 bg-slate-50 dark:bg-[#070A13] text-slate-900 dark:text-slate-100 transition-colors relative overflow-hidden">
            {/* Ambient Lights */}
            <div className="absolute -top-32 -left-32 w-96 h-96 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-cyan-500/15 rounded-full blur-3xl pointer-events-none" />

            {/* Top Bar */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            <div className="w-full max-w-2xl space-y-6 relative z-10 my-8">
                {/* Brand Header */}
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center gap-2.5">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/25">
                            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                        </div>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                        Setup Healthcare Organization
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
                        4-Step Clinical Onboarding & Facility Provisioning Wizard
                    </p>
                </div>

                {/* 4-Step Progress Stepper */}
                <div className="grid grid-cols-4 gap-2 pt-2">
                    {[
                        { num: 1, title: 'Identity', desc: 'Admin & Facility' },
                        { num: 2, title: 'Clinical', desc: 'Depts & Beds' },
                        { num: 3, title: 'Regulatory', desc: 'ABDM & License' },
                        { num: 4, title: 'Operations', desc: 'Safety & Launch' },
                    ].map((s) => {
                        const isActive = step === s.num;
                        const isDone = step > s.num;
                        return (
                            <button
                                key={s.num}
                                type="button"
                                onClick={() => {
                                    if (s.num < step) setStep(s.num as 1 | 2 | 3 | 4);
                                }}
                                className={`flex flex-col items-center text-center p-2 rounded-xl border transition-all ${
                                    isActive
                                        ? 'border-blue-500 bg-blue-500/10 shadow-sm'
                                        : isDone
                                        ? 'border-emerald-500/40 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400 cursor-pointer'
                                        : 'border-slate-200 dark:border-slate-800 opacity-60'
                                }`}
                            >
                                <div
                                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mb-1 ${
                                        isActive
                                            ? 'bg-blue-600 text-white shadow-sm'
                                            : isDone
                                            ? 'bg-emerald-500 text-white'
                                            : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                                    }`}
                                >
                                    {isDone ? '✓' : s.num}
                                </div>
                                <span className="text-xs font-bold">{s.title}</span>
                                <span className="text-[10px] hidden sm:inline text-slate-500 dark:text-slate-400">{s.desc}</span>
                            </button>
                        );
                    })}
                </div>

                {error && (
                    <Alert
                        variant="error"
                        title="Configuration Notice"
                        onClose={() => setError(null)}
                    >
                        <div className="space-y-1.5">
                            <p>{error}</p>
                            {error.toLowerCase().includes('already exists') && (
                                <div className="pt-1">
                                    <Link
                                        href="/auth/login"
                                        className="inline-flex items-center gap-1 font-bold underline text-blue-700 dark:text-blue-300 hover:text-blue-900"
                                    >
                                        Log in with your existing credentials →
                                    </Link>
                                </div>
                            )}
                        </div>
                    </Alert>
                )}

                <Card className="glass-panel border-slate-200/80 dark:border-slate-800/80 shadow-2xl backdrop-blur-xl">
                    <CardContent className="pt-6">
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {/* ========================================================================= */}
                            {/* STEP 1: Admin & Basic Facility Details */}
                            {/* ========================================================================= */}
                            {step === 1 && (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
                                        <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                                                Step 1: Facility Identity & Lead Administrator
                                            </h3>
                                            <p className="text-xs text-slate-500">Provide legal entity details and designated institutional admin.</p>
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                            <div className="sm:col-span-2">
                                                <Input
                                                    id="orgName"
                                                    label="Organization / Hospital Legal Name"
                                                    required
                                                    placeholder="e.g. Metro Specialty Hospital & Research Center"
                                                    value={orgName}
                                                    onChange={(e) => setOrgName(e.target.value)}
                                                    disabled={submitting}
                                                />
                                            </div>
                                            <div>
                                                <Input
                                                    id="orgCode"
                                                    label="Facility Identifier Code"
                                                    placeholder="e.g. MSH-01"
                                                    value={orgCode}
                                                    onChange={(e) => setOrgCode(e.target.value)}
                                                    disabled={submitting}
                                                />
                                            </div>
                                        </div>

                                        <Input
                                            id="orgAddress"
                                            label="Campus Address & Postal Location"
                                            placeholder="e.g. 450 Medical Enclave, Tech Park Sector 4, New Delhi"
                                            value={orgAddress}
                                            onChange={(e) => setOrgAddress(e.target.value)}
                                            disabled={submitting}
                                        />

                                        <Input
                                            id="adminName"
                                            label="Administrator Full Legal Name"
                                            required
                                            allowedChars="alpha"
                                            placeholder="e.g. Dr Arthur Pendelton"
                                            value={adminName}
                                            onChange={(e) => setAdminName(e.target.value)}
                                            disabled={submitting}
                                        />

                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            <Input
                                                id="email"
                                                label="Institutional Work Email"
                                                type="email"
                                                required
                                                placeholder="admin@metrohospital.org"
                                                value={email}
                                                onChange={(e) => setEmail(e.target.value)}
                                                disabled={submitting}
                                            />

                                            <Input
                                                id="phone"
                                                label="Administrator Mobile Number"
                                                type="tel"
                                                allowedChars="numeric"
                                                maxLength={15}
                                                required
                                                placeholder="9876543210"
                                                value={phone}
                                                onChange={(e) => setPhone(e.target.value)}
                                                disabled={submitting}
                                            />
                                        </div>

                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            <Input
                                                id="password"
                                                label="Password (Min 8 chars)"
                                                type="password"
                                                required
                                                placeholder="••••••••••••"
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                disabled={submitting}
                                            />

                                            <Input
                                                id="confirmPassword"
                                                label="Confirm Password"
                                                type="password"
                                                required
                                                placeholder="••••••••••••"
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                disabled={submitting}
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ========================================================================= */}
                            {/* STEP 2: Clinical Facility & Departments */}
                            {/* ========================================================================= */}
                            {step === 2 && (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
                                        <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" />
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                                                Step 2: Clinical Facility & Departments
                                            </h3>
                                            <p className="text-xs text-slate-500">Configure bed capacities and activated medical clinical divisions.</p>
                                        </div>
                                    </div>

                                    {/* Facility Type */}
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            Facility Classification / Care Tier
                                        </label>
                                        <select
                                            value={facilityType}
                                            onChange={(e) => setFacilityType(e.target.value)}
                                            className="w-full h-10 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        >
                                            {FACILITY_TYPES.map((type) => (
                                                <option key={type} value={type}>
                                                    {type}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Clinical Departments Selection */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            Active Clinical Specialties & Departments ({departments.length} selected)
                                        </label>
                                        <div className="flex flex-wrap gap-2 pt-1">
                                            {AVAILABLE_DEPARTMENTS.map((dept) => {
                                                const selected = departments.includes(dept);
                                                return (
                                                    <button
                                                        key={dept}
                                                        type="button"
                                                        onClick={() => toggleDepartment(dept)}
                                                        className={`text-xs px-3 py-1.5 rounded-lg font-medium border transition-all ${
                                                            selected
                                                                ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                                                                : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-blue-400'
                                                        }`}
                                                    >
                                                        {selected ? '✓ ' : '+ '}
                                                        {dept}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* Bed Capacities */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                                        <Input
                                            id="totalBeds"
                                            label="Total Inpatient Beds (Max 10,000)"
                                            type="text"
                                            inputMode="numeric"
                                            allowedChars="numeric"
                                            maxLength={5}
                                            helperText="Standard hospital capacity: 1 – 10,000 beds"
                                            value={totalBeds === 0 ? '' : totalBeds.toString()}
                                            onChange={(e) => {
                                                const raw = e.target.value.replace(/\D/g, '');
                                                if (!raw) {
                                                    setTotalBeds(0);
                                                    return;
                                                }
                                                const val = parseInt(raw, 10);
                                                setTotalBeds(Math.min(val, 10000));
                                            }}
                                            disabled={submitting}
                                        />

                                        <Input
                                            id="icuBeds"
                                            label="Dedicated ICU / Critical Beds (Max 2,500)"
                                            type="text"
                                            inputMode="numeric"
                                            allowedChars="numeric"
                                            maxLength={4}
                                            helperText="Critical care beds (0 – 2,500, cannot exceed total beds)"
                                            value={icuBeds === 0 ? '' : icuBeds.toString()}
                                            onChange={(e) => {
                                                const raw = e.target.value.replace(/\D/g, '');
                                                if (!raw) {
                                                    setIcuBeds(0);
                                                    return;
                                                }
                                                const val = parseInt(raw, 10);
                                                setIcuBeds(Math.min(val, 2500));
                                            }}
                                            disabled={submitting}
                                        />
                                    </div>

                                    {/* Emergency & Ambulance Capabilities */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
                                        <Checkbox
                                            id="hasEmergency"
                                            label="24/7 Level-1 Emergency & Trauma Bay Available"
                                            checked={hasEmergency}
                                            onChange={(e) => setHasEmergency(e.target.checked)}
                                        />
                                        <Checkbox
                                            id="hasAmbulance"
                                            label="Active Critical Care Ambulance & Fleet Service"
                                            checked={hasAmbulance}
                                            onChange={(e) => setHasAmbulance(e.target.checked)}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* ========================================================================= */}
                            {/* STEP 3: Regulatory & Licensing */}
                            {/* ========================================================================= */}
                            {step === 3 && (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
                                        <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                                                Step 3: Regulatory & Health System Licenses
                                            </h3>
                                            <p className="text-xs text-slate-500">National health registry and insurance network credentials.</p>
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        <Input
                                            id="licenseNumber"
                                            label="Clinical Establishment License / State Reg #"
                                            placeholder="e.g. DL-CEA-2024-00918"
                                            value={licenseNumber}
                                            onChange={(e) => setLicenseNumber(e.target.value)}
                                            disabled={submitting}
                                        />

                                        <Input
                                            id="abdmFacilityId"
                                            label="ABDM Health Facility Registry (HFR) ID"
                                            placeholder="e.g. IN-MH-102941"
                                            value={abdmFacilityId}
                                            onChange={(e) => setAbdmFacilityId(e.target.value)}
                                            disabled={submitting}
                                        />

                                        <Input
                                            id="insuranceNetworkCode"
                                            label="ROHINI / Insurance Registry Code"
                                            placeholder="e.g. 890001239841"
                                            value={insuranceNetworkCode}
                                            onChange={(e) => setInsuranceNetworkCode(e.target.value)}
                                            disabled={submitting}
                                        />

                                        <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs text-blue-700 dark:text-blue-300">
                                            <strong>Note on ABDM & HIPAA compliance:</strong> Digital health registry credentials can be verified automatically via Ayushman Bharat Digital Mission sandbox APIs upon provisioning.
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ========================================================================= */}
                            {/* STEP 4: Operations & Clinical Safety Review Gate */}
                            {/* ========================================================================= */}
                            {step === 4 && (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
                                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                                        <div>
                                            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 uppercase tracking-wide">
                                                Step 4: Operational Settings & Safety Gate Review
                                            </h3>
                                            <p className="text-xs text-slate-500">Confirm triage hotlines, operational parameters, and safety policies.</p>
                                        </div>
                                    </div>

                                    <div className="space-y-3">
                                        <Input
                                            id="emergencyHotline"
                                            label="24/7 Facility Triage / Hotline Number"
                                            type="tel"
                                            placeholder="e.g. 1800-419-9999 or +91 11 2658 8500"
                                            value={emergencyHotline}
                                            onChange={(e) => setEmergencyHotline(e.target.value)}
                                            disabled={submitting}
                                        />

                                        <Input
                                            id="operatingHours"
                                            label="Operating Hours Specification"
                                            placeholder="e.g. 24/7 Inpatient & Trauma | OPD: 08:00 - 20:00"
                                            value={operatingHours}
                                            onChange={(e) => setOperatingHours(e.target.value)}
                                            disabled={submitting}
                                        />

                                        {/* Facility Summary Review Pill Box */}
                                        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
                                            <h4 className="font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-[11px]">
                                                Facility Configuration Summary
                                            </h4>
                                            <div className="grid grid-cols-2 gap-2 text-slate-600 dark:text-slate-400">
                                                <div><span className="font-semibold text-slate-900 dark:text-white">Facility:</span> {orgName || 'N/A'} ({orgCode || 'AUTO'})</div>
                                                <div><span className="font-semibold text-slate-900 dark:text-white">Classification:</span> {facilityType}</div>
                                                <div><span className="font-semibold text-slate-900 dark:text-white">Admin:</span> {adminName}</div>
                                                <div><span className="font-semibold text-slate-900 dark:text-white">Email:</span> {email}</div>
                                                <div><span className="font-semibold text-slate-900 dark:text-white">Capacities:</span> {totalBeds} Beds ({icuBeds} ICU)</div>
                                                <div><span className="font-semibold text-slate-900 dark:text-white">Emergency:</span> {hasEmergency ? 'Yes' : 'No'} | Ambulance: {hasAmbulance ? 'Yes' : 'No'}</div>
                                            </div>
                                        </div>

                                        <div className="space-y-2 pt-2">
                                            <Checkbox
                                                id="reviewPolicy"
                                                label="Enforce Physician Sign-off Policy: All AI-generated triage scores, preliminary radiological impressions, and diagnostic drafts require explicit clinician review prior to chart finalization."
                                                checked={clinicalReviewPolicy}
                                                onChange={(e) => setClinicalReviewPolicy(e.target.checked)}
                                            />

                                            <Checkbox
                                                id="terms"
                                                label="I certify that I am legally authorized to represent this healthcare organization and adhere to ABDM, HIPAA, and DPDP clinical data governance protocols."
                                                checked={termsAccepted}
                                                onChange={(e) => setTermsAccepted(e.target.checked)}
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Wizard Navigation Actions */}
                            <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800">
                                {step > 1 ? (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        onClick={handleBack}
                                        disabled={submitting}
                                    >
                                        ← Previous Step
                                    </Button>
                                ) : (
                                    <div />
                                )}

                                {step < 4 ? (
                                    <Button
                                        type="button"
                                        variant="primary"
                                        onClick={handleNext}
                                    >
                                        Continue to Step {step + 1} →
                                    </Button>
                                ) : (
                                    <Button
                                        type="submit"
                                        variant="primary"
                                        className="shadow-lg shadow-blue-500/25"
                                        isLoading={submitting}
                                    >
                                        Complete Setup & Launch Facility
                                    </Button>
                                )}
                            </div>
                        </form>
                    </CardContent>
                </Card>

                {/* Return to Institutional Sign In */}
                <div className="text-center text-xs text-slate-500 dark:text-slate-400 space-y-1">
                    <p>
                        Already have an administrator or clinical credential?{' '}
                        <Link href="/auth/login" className="font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                            Sign in to Portal
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
