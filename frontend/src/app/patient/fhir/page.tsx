'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import {
    fhirApi,
    FhirBundle,
    FhirPatient,
    FhirAppointment,
    FhirDiagnosticReport,
    FhirMedicationRequest,
    patientPortalApi,
    PatientProfile,
} from '@/lib/api';
import { Button, Card, CardContent, Badge, Spinner } from '@/components/ui';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(s?: string) {
    if (!s) return '—';
    return new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function fmtDateTime(s?: string) {
    if (!s) return '—';
    return new Date(s).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function statusColor(status?: string) {
    const s = (status || '').toLowerCase();
    if (['finalized', 'completed', 'active', 'booked'].includes(s)) return 'text-emerald-600 dark:text-emerald-400';
    if (['draft', 'in_progress', 'pending', 'proposed'].includes(s)) return 'text-amber-600 dark:text-amber-400';
    if (['cancelled', 'cancelled', 'revoked', 'no_show'].includes(s)) return 'text-rose-600 dark:text-rose-400';
    return 'text-slate-500 dark:text-slate-400';
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function SectionHeader({ icon, title, count }: { icon: React.ReactNode; title: string; count?: number }) {
    return (
        <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 dark:text-blue-400">
                {icon}
            </div>
            <div>
                <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
                {count !== undefined && (
                    <p className="text-xs text-slate-400">{count} record{count !== 1 ? 's' : ''}</p>
                )}
            </div>
        </div>
    );
}

function PatientCard({ patient }: { patient: FhirPatient }) {
    const name = patient.name?.[0]?.text || patient.name?.[0]?.given?.join(' ') || '—';
    const phone = patient.telecom?.find(t => t.system === 'phone')?.value;
    const email = patient.telecom?.find(t => t.system === 'email')?.value;
    const abha = patient.identifier?.find(i => i.system?.includes('abha'))?.value;
    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
                { label: 'Full Name', value: name },
                { label: 'Date of Birth', value: fmtDate(patient.birthDate) },
                { label: 'Gender', value: patient.gender ? patient.gender.charAt(0).toUpperCase() + patient.gender.slice(1) : '—' },
                { label: 'Status', value: patient.active !== false ? 'Active' : 'Inactive' },
                { label: 'Phone', value: phone || '—' },
                { label: 'Email', value: email || '—' },
                { label: 'ABHA ID', value: abha || 'Not linked' },
                { label: 'Last Updated', value: fmtDate(patient.meta?.lastUpdated) },
            ].map(({ label, value }) => (
                <div key={label} className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">{label}</p>
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100 break-all">{value}</p>
                </div>
            ))}
        </div>
    );
}

function AppointmentRow({ appt }: { appt: FhirAppointment }) {
    const patient = appt.participant?.find(p => p.actor?.reference?.startsWith('Patient'))?.actor?.display;
    const doctor = appt.participant?.find(p => p.actor?.reference?.startsWith('Practitioner'))?.actor?.display;
    const type = appt.appointmentType?.text || appt.serviceType?.[0]?.text || 'General';
    return (
        <div className="flex items-center justify-between py-3 border-b border-slate-100 dark:border-slate-800 last:border-0 gap-4">
            <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{type}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {doctor ? `Dr. ${doctor}` : '—'} · {fmtDateTime(appt.start)}
                    {appt.minutesDuration && ` (${appt.minutesDuration} min)`}
                </p>
            </div>
            <span className={`text-xs font-semibold uppercase shrink-0 ${statusColor(appt.status)}`}>
                {appt.status}
            </span>
        </div>
    );
}

function DiagnosticRow({ report }: { report: FhirDiagnosticReport }) {
    const [expanded, setExpanded] = useState(false);
    const code = report.code?.text || report.code?.coding?.[0]?.display || 'Clinical Note';
    const conclusion = report.conclusion || report.section?.[0]?.text?.div?.replace(/<[^>]*>/g, ' ') || '';
    return (
        <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
            <button
                type="button"
                onClick={() => setExpanded(e => !e)}
                className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-700/60 transition-colors text-left"
            >
                <div>
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{code}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{fmtDateTime(report.effectiveDateTime || report.issued)}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs font-semibold uppercase ${statusColor(report.status)}`}>{report.status}</span>
                    <svg className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </button>
            {expanded && conclusion && (
                <div className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 whitespace-pre-wrap leading-relaxed">
                    {conclusion}
                </div>
            )}
        </div>
    );
}

function MedRow({ med }: { med: FhirMedicationRequest }) {
    const name = med.medicationCodeableConcept?.text || med.medicationCodeableConcept?.coding?.[0]?.display || 'Medication';
    const dosage = med.dosageInstruction?.[0]?.text || '—';
    return (
        <div className="flex items-start gap-3 py-3 border-b border-slate-100 dark:border-slate-800 last:border-0">
            <div className="mt-1 w-6 h-6 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center shrink-0">
                <svg className="w-3.5 h-3.5 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
            </div>
            <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{name}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{dosage}</p>
            </div>
            <span className={`text-xs font-semibold uppercase shrink-0 mt-1 ${statusColor(med.status)}`}>{med.status}</span>
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function PatientFhirViewerPage() {
    const { user } = useAuth();
    const [bundle, setBundle] = useState<FhirBundle | null>(null);
    const [patientProfile, setPatientProfile] = useState<PatientProfile | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'appointments' | 'diagnoses' | 'medications' | 'raw'>('overview');
    const [exporting, setExporting] = useState(false);

    const loadData = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const profile = await patientPortalApi.getProfile();
            setPatientProfile(profile);
            const b = await fhirApi.getPatientBundle(profile.patient_id);
            setBundle(b);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to load FHIR health records.';
            setError(msg);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => { loadData(); }, [loadData]);

    // Partition bundle entries
    const patients: FhirPatient[] = [];
    const appointments: FhirAppointment[] = [];
    const reports: FhirDiagnosticReport[] = [];
    const medications: FhirMedicationRequest[] = [];

    (bundle?.entry || []).forEach(e => {
        if (!e.resource) return;
        switch (e.resource.resourceType) {
            case 'Patient': patients.push(e.resource as FhirPatient); break;
            case 'Appointment': appointments.push(e.resource as FhirAppointment); break;
            case 'DiagnosticReport': reports.push(e.resource as FhirDiagnosticReport); break;
            case 'MedicationRequest': medications.push(e.resource as FhirMedicationRequest); break;
        }
    });

    const handleExport = () => {
        if (!bundle) return;
        setExporting(true);
        try {
            const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `fhir-bundle-${patientProfile?.patient_id || 'patient'}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } finally {
            setExporting(false);
        }
    };

    const tabs = [
        { id: 'overview', label: 'Patient', count: patients.length },
        { id: 'appointments', label: 'Appointments', count: appointments.length },
        { id: 'diagnoses', label: 'Diagnoses', count: reports.length },
        { id: 'medications', label: 'Medications', count: medications.length },
        { id: 'raw', label: 'Raw JSON', count: null },
    ] as const;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 uppercase tracking-wider">
                            HL7 FHIR R4
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400">Interoperability Standard</span>
                    </div>
                    <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">My FHIR Health Records</h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                        Structured electronic health data in the international FHIR R4 standard
                    </p>
                </div>
                <Button
                    id="fhir-export-btn"
                    onClick={handleExport}
                    disabled={!bundle || exporting || isLoading}
                    variant="outline"
                    className="shrink-0 flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Export Bundle (JSON)
                </Button>
            </div>

            {/* Stats strip */}
            {bundle && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                        { label: 'Appointments', value: appointments.length, color: 'blue' },
                        { label: 'Clinical Notes', value: reports.length, color: 'indigo' },
                        { label: 'Medications', value: medications.length, color: 'green' },
                        { label: 'Total Resources', value: bundle.total || (bundle.entry?.length ?? 0), color: 'purple' },
                    ].map(({ label, value, color }) => (
                        <div key={label} className={`bg-${color}-50 dark:bg-${color}-900/20 border border-${color}-100 dark:border-${color}-800/40 rounded-xl p-4`}>
                            <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
                            <p className={`text-xs font-medium text-${color}-700 dark:text-${color}-300 mt-0.5`}>{label}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Loading */}
            {isLoading && (
                <div className="flex flex-col items-center justify-center py-16 gap-3">
                    <Spinner size="lg" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">Loading FHIR health records…</p>
                </div>
            )}

            {/* Error */}
            {error && !isLoading && (
                <Card>
                    <CardContent className="py-12 text-center">
                        <div className="w-14 h-14 rounded-2xl bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center mx-auto mb-4">
                            <svg className="w-7 h-7 text-rose-600 dark:text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{error}</p>
                        <Button id="fhir-retry-btn" onClick={loadData} className="mt-4" variant="outline">Retry</Button>
                    </CardContent>
                </Card>
            )}

            {/* Content */}
            {bundle && !isLoading && (
                <Card>
                    {/* Tabs */}
                    <div className="border-b border-slate-200 dark:border-slate-700 px-4 overflow-x-auto">
                        <div className="flex gap-0 min-w-max">
                            {tabs.map(tab => (
                                <button
                                    key={tab.id}
                                    id={`fhir-tab-${tab.id}`}
                                    type="button"
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`flex items-center gap-1.5 px-4 py-3 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
                                        activeTab === tab.id
                                            ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                                            : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    }`}
                                >
                                    {tab.label}
                                    {tab.count !== null && (
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                                            activeTab === tab.id ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                                        }`}>{tab.count}</span>
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>

                    <CardContent className="p-5">
                        {/* Overview / Patient tab */}
                        {activeTab === 'overview' && (
                            <div className="space-y-4">
                                <SectionHeader
                                    icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>}
                                    title="Patient Demographics (FHIR R4 Patient)"
                                    count={patients.length}
                                />
                                {patients.length > 0 ? (
                                    patients.map(p => <PatientCard key={p.id} patient={p} />)
                                ) : (
                                    <p className="text-sm text-slate-400 italic">No Patient resource found.</p>
                                )}

                                {/* Bundle metadata */}
                                <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800">
                                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">Bundle Metadata</p>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                        {[
                                            { label: 'Bundle Type', value: bundle.type },
                                            { label: 'Bundle ID', value: bundle.id || 'N/A' },
                                            { label: 'Last Updated', value: fmtDateTime(bundle.meta?.lastUpdated) },
                                            { label: 'Standard', value: 'HL7 FHIR R4' },
                                            { label: 'Entries', value: String(bundle.entry?.length ?? 0) },
                                            { label: 'Export Format', value: 'application/fhir+json' },
                                        ].map(({ label, value }) => (
                                            <div key={label} className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
                                                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">{label}</p>
                                                <p className="text-xs font-medium text-slate-700 dark:text-slate-300 break-all">{value}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Appointments */}
                        {activeTab === 'appointments' && (
                            <div>
                                <SectionHeader
                                    icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>}
                                    title="Appointment Timeline (FHIR R4 Appointment)"
                                    count={appointments.length}
                                />
                                {appointments.length > 0 ? (
                                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {appointments.sort((a, b) => new Date(b.start || '').getTime() - new Date(a.start || '').getTime())
                                            .map(a => <AppointmentRow key={a.id} appt={a} />)}
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-400 italic">No FHIR Appointment resources found.</p>
                                )}
                            </div>
                        )}

                        {/* Diagnoses */}
                        {activeTab === 'diagnoses' && (
                            <div>
                                <SectionHeader
                                    icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
                                    title="Clinical Notes & Diagnostic Reports (FHIR R4 DiagnosticReport)"
                                    count={reports.length}
                                />
                                {reports.length > 0 ? (
                                    <div className="space-y-2">
                                        {reports.sort((a, b) => new Date(b.effectiveDateTime || b.issued || '').getTime() - new Date(a.effectiveDateTime || a.issued || '').getTime())
                                            .map(r => <DiagnosticRow key={r.id} report={r} />)}
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-400 italic">No FHIR DiagnosticReport resources found.</p>
                                )}
                            </div>
                        )}

                        {/* Medications */}
                        {activeTab === 'medications' && (
                            <div>
                                <SectionHeader
                                    icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>}
                                    title="Medication Requests (FHIR R4 MedicationRequest)"
                                    count={medications.length}
                                />
                                {medications.length > 0 ? (
                                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {medications.sort((a, b) => new Date(b.authoredOn || '').getTime() - new Date(a.authoredOn || '').getTime())
                                            .map(m => <MedRow key={m.id} med={m} />)}
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-400 italic">No FHIR MedicationRequest resources found.</p>
                                )}
                            </div>
                        )}

                        {/* Raw JSON */}
                        {activeTab === 'raw' && (
                            <div>
                                <div className="flex items-center justify-between mb-4">
                                    <SectionHeader
                                        icon={<svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>}
                                        title="Raw FHIR R4 Bundle (JSON)"
                                    />
                                    <Button id="fhir-raw-export-btn" onClick={handleExport} variant="outline" className="text-xs py-1.5">
                                        Download
                                    </Button>
                                </div>
                                <pre className="bg-slate-950 dark:bg-slate-900 text-green-400 text-xs rounded-xl p-4 overflow-x-auto max-h-[500px] overflow-y-auto leading-relaxed">
                                    {JSON.stringify(bundle, null, 2)}
                                </pre>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
