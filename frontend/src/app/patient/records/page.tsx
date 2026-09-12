'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    patientPortalApi,
    PatientPortalRecordItem,
    fhirApi,
    FhirBundle,
    FhirResourceHeader,
} from '@/lib/api';
import { Card, CardContent, Button, Badge } from '@/components/ui';

export default function PatientMedicalRecordsPage() {
    const [records, setRecords] = useState<PatientPortalRecordItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedRecord, setSelectedRecord] = useState<PatientPortalRecordItem | null>(null);

    // FHIR Interoperability State (Milestone U-20)
    const [fhirModalOpen, setFhirModalOpen] = useState(false);
    const [fhirData, setFhirData] = useState<FhirBundle | FhirResourceHeader | null>(null);
    const [fhirLoading, setFhirLoading] = useState(false);
    const [fhirTitle, setFhirTitle] = useState('Standardized FHIR R4 Health Record');
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        loadRecords();
    }, []);

    const loadRecords = async () => {
        setIsLoading(true);
        try {
            const data = await patientPortalApi.getRecords();
            setRecords(data);
            if (data.length > 0) {
                setSelectedRecord(data[0]);
            }
        } catch (err) {
            console.error('Failed to load medical records:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleExportFhirBundle = async () => {
        setFhirLoading(true);
        setFhirTitle('Standardized Patient Health Record Bundle (HL7 FHIR R4)');
        setFhirModalOpen(true);
        try {
            const bundle = await fhirApi.getPatientBundle();
            setFhirData(bundle);
        } catch (err: any) {
            console.error('Failed to export FHIR Bundle:', err);
        } finally {
            setFhirLoading(false);
        }
    };

    const handleExportRecordFhir = async (recordId: string) => {
        setFhirLoading(true);
        setFhirTitle('Clinical DiagnosticReport (HL7 FHIR R4)');
        setFhirModalOpen(true);
        try {
            const fhirReport = await fhirApi.getRecordFhir(recordId);
            setFhirData(fhirReport);
        } catch (err: any) {
            console.error('Failed to export record FHIR:', err);
        } finally {
            setFhirLoading(false);
        }
    };

    const handleCopyJson = () => {
        if (!fhirData) return;
        navigator.clipboard.writeText(JSON.stringify(fhirData, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDownloadJson = () => {
        if (!fhirData) return;
        const blob = new Blob([JSON.stringify(fhirData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `fhir-export-${fhirData.resourceType.toLowerCase()}-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="space-y-6 pb-12 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                        <span>📋 Medical Records & Clinical Summaries</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Doctor-attested clinical visit notes, encounter summaries, and diagnosis plans.
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleExportFhirBundle}
                        className="text-xs flex items-center gap-1.5 border-indigo-200 dark:border-indigo-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-medium"
                    >
                        <span>🌐</span>
                        <span>Export FHIR R4 Bundle</span>
                    </Button>
                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 ml-1">
                        <span>🔒</span>
                        <span>Signed EHR Records</span>
                    </span>
                </div>
            </div>

            {/* Split Screen Layout: List on Left, Detail on Right */}
            {isLoading ? (
                <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="p-6 animate-pulse border border-slate-200 dark:border-slate-800">
                            <div className="h-5 w-1/3 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                            <div className="h-4 w-1/2 bg-slate-200 dark:bg-slate-700 rounded" />
                        </Card>
                    ))}
                </div>
            ) : records.length > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                    {/* Record Select Drawer (5 Cols) */}
                    <div className="lg:col-span-5 space-y-3">
                        <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 px-1">
                            Encounter History ({records.length})
                        </div>
                        <div className="space-y-2">
                            {records.map((rec) => {
                                const isSelected = selectedRecord?.record_id === rec.record_id;
                                return (
                                    <div
                                        key={rec.record_id}
                                        onClick={() => setSelectedRecord(rec)}
                                        className={`p-4 rounded-xl border transition cursor-pointer ${
                                            isSelected
                                                ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-700 shadow-sm'
                                                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between mb-1.5">
                                            <span className="text-xs font-bold text-slate-900 dark:text-white">
                                                {rec.doctor_name || 'Attending Physician'}
                                            </span>
                                            <Badge variant="success" className="text-[10px] uppercase font-bold">
                                                Finalized & Signed
                                            </Badge>
                                        </div>

                                        <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">
                                            {rec.doctor_specialty || 'General Medicine'} • {new Date(rec.created_at).toLocaleDateString(undefined, { dateStyle: 'medium' })}
                                        </div>

                                        <p className="text-xs text-slate-700 dark:text-slate-300 line-clamp-2 italic">
                                            "{rec.assessment || rec.content?.assessment?.clinical_summary || 'Clinical encounter progress notes recorded.'}"
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Detailed SOAP Clinical Viewer (7 Cols) */}
                    {selectedRecord && (
                        <div className="lg:col-span-7">
                            <Card className="border border-slate-200 dark:border-slate-800 shadow-sm">
                                <CardContent className="p-6 space-y-6">
                                    {/* Document Header & Doctor Seal */}
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800 gap-3">
                                        <div>
                                            <span className="text-[10px] font-mono uppercase tracking-widest text-indigo-600 dark:text-indigo-400 font-semibold block">
                                                Certified Clinical Progress Note
                                            </span>
                                            <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-0.5">
                                                {selectedRecord.doctor_name}
                                            </h3>
                                            <p className="text-xs text-slate-500">
                                                {selectedRecord.doctor_specialty} • {selectedRecord.doctor_hospital || 'AI-HOS Medical Network'}
                                            </p>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                onClick={() => handleExportRecordFhir(selectedRecord.record_id)}
                                                className="text-xs font-mono"
                                                title="Export this record as FHIR R4 DiagnosticReport"
                                            >
                                                FHIR R4 JSON
                                            </Button>
                                            <div className="text-right">
                                                <span className="text-[11px] font-mono text-slate-400 block">
                                                    Encounter Date
                                                </span>
                                                <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                                                    {new Date(selectedRecord.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* SOAP Narrative Sections */}
                                    <div className="space-y-4 text-xs sm:text-sm">
                                        {/* Subjective */}
                                        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800">
                                            <h4 className="font-bold text-indigo-900 dark:text-indigo-300 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>🗣️</span> Subjective Patient Complaint
                                            </h4>
                                            <p className="text-slate-800 dark:text-slate-200 whitespace-pre-line leading-relaxed">
                                                {selectedRecord.subjective || selectedRecord.content?.subjective?.history_of_present_illness || 'Patient presented with standard clinical inquiry.'}
                                            </p>
                                        </div>

                                        {/* Objective */}
                                        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800">
                                            <h4 className="font-bold text-indigo-900 dark:text-indigo-300 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>🩺</span> Objective Physician Observations
                                            </h4>
                                            <p className="text-slate-800 dark:text-slate-200 whitespace-pre-line leading-relaxed">
                                                {selectedRecord.objective || selectedRecord.content?.objective?.physical_exam || 'General clinical parameters observed within normal limits.'}
                                            </p>
                                        </div>

                                        {/* Assessment & Diagnosis */}
                                        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-800">
                                            <h4 className="font-bold text-indigo-900 dark:text-indigo-300 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>🔬</span> Clinical Assessment & Diagnosis
                                            </h4>
                                            <p className="text-slate-800 dark:text-slate-200 font-medium whitespace-pre-line leading-relaxed">
                                                {selectedRecord.assessment || selectedRecord.content?.assessment?.primary_diagnosis || 'Clinical evaluation concluded.'}
                                            </p>
                                            {selectedRecord.content?.assessment?.differential_diagnoses && (
                                                <p className="text-xs text-slate-500 mt-2">
                                                    <strong>Differential:</strong> {selectedRecord.content.assessment.differential_diagnoses.join(', ')}
                                                </p>
                                            )}
                                        </div>

                                        {/* Plan */}
                                        <div className="p-4 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40">
                                            <h4 className="font-bold text-emerald-900 dark:text-emerald-300 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>📋</span> Treatment Plan & Doctor Recommendations
                                            </h4>
                                            <p className="text-slate-800 dark:text-slate-200 whitespace-pre-line leading-relaxed">
                                                {selectedRecord.plan || selectedRecord.content?.plan?.counseling || 'Follow prescribed medications and schedule review if symptoms persist.'}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Footer Attestation Certificate */}
                                    <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-400">
                                        <div>
                                            <span>Certified Medical Record • Protected under EHR Privacy Standards</span>
                                        </div>
                                        <Button
                                            variant="secondary"
                                            size="sm"
                                            onClick={() => window.print()}
                                            className="text-xs"
                                        >
                                            🖨️ Print Clinical Summary
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </div>
            ) : (
                <Card className="p-12 text-center border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 rounded-2xl">
                    <span className="text-3xl block mb-2">📋</span>
                    <h3 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                        No medical records on file yet
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                        Once you complete a consultation and your physician signs off on the clinical encounter note, your records will appear here.
                    </p>
                    <div className="mt-4">
                        <Link href="/patient/appointments">
                            <Button variant="primary" size="sm">
                                View Consultations
                            </Button>
                        </Link>
                    </div>
                </Card>
            )}

            {/* FHIR Interoperability Export Modal (Milestone U-20) */}
            {fhirModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4 overflow-y-auto animate-fadeIn">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-3xl w-full border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden my-8">
                        {/* Modal Header */}
                        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/80 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2.5">
                                <div className="p-2 rounded-lg bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                                    </svg>
                                </div>
                                <div>
                                    <h3 className="font-bold text-base text-slate-900 dark:text-white">
                                        {fhirTitle}
                                    </h3>
                                    <p className="text-xs text-slate-400">
                                        HL7 FHIR Release 4 • Interoperability & ABDM Standard
                                    </p>
                                </div>
                            </div>

                            <button
                                onClick={() => {
                                    setFhirModalOpen(false);
                                    setFhirData(null);
                                }}
                                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="p-6 space-y-4">
                            {fhirLoading ? (
                                <div className="py-16 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
                                    <svg className="animate-spin w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                    </svg>
                                    Compiling FHIR R4 resources...
                                </div>
                            ) : fhirData ? (
                                <>
                                    {/* Resource Metadata Highlights */}
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                                        <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                            <span className="text-[10px] text-slate-400 block font-mono">Resource Type</span>
                                            <span className="font-bold text-slate-800 dark:text-slate-100">{fhirData.resourceType}</span>
                                        </div>
                                        <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                            <span className="text-[10px] text-slate-400 block font-mono">Standard</span>
                                            <span className="font-bold text-indigo-600 dark:text-indigo-400">HL7 FHIR R4</span>
                                        </div>
                                        {fhirData.total !== undefined && (
                                            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                                <span className="text-[10px] text-slate-400 block font-mono">Bundled Entries</span>
                                                <span className="font-bold text-emerald-600 dark:text-emerald-400">{fhirData.total}</span>
                                            </div>
                                        )}
                                        <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                                            <span className="text-[10px] text-slate-400 block font-mono">Export Schema</span>
                                            <span className="font-bold text-slate-700 dark:text-slate-300">Non-Mutating</span>
                                        </div>
                                    </div>

                                    {/* JSON Code Viewer */}
                                    <div className="relative">
                                        <pre className="p-4 rounded-xl bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto max-h-96 border border-slate-800 leading-relaxed">
                                            {JSON.stringify(fhirData, null, 2)}
                                        </pre>
                                    </div>
                                </>
                            ) : (
                                <div className="py-12 text-center text-slate-400 text-sm">
                                    Unable to compile FHIR resources. Please try again.
                                </div>
                            )}
                        </div>

                        {/* Modal Footer */}
                        <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 flex items-center justify-between">
                            <span className="text-xs text-slate-500 dark:text-slate-400">
                                Portability & Interoperability Compliant
                            </span>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={handleCopyJson}
                                    disabled={!fhirData || fhirLoading}
                                    className="text-xs"
                                >
                                    {copied ? '✓ Copied!' : 'Copy JSON'}
                                </Button>
                                <Button
                                    variant="primary"
                                    size="sm"
                                    onClick={handleDownloadJson}
                                    disabled={!fhirData || fhirLoading}
                                    className="text-xs flex items-center gap-1.5"
                                >
                                    <span>⬇️</span>
                                    <span>Download Bundle</span>
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
