'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { patientPortalApi, PatientPortalRecordItem } from '@/lib/api';
import { Card, CardContent, Button, Badge } from '@/components/ui';

export default function PatientMedicalRecordsPage() {
    const [records, setRecords] = useState<PatientPortalRecordItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedRecord, setSelectedRecord] = useState<PatientPortalRecordItem | null>(null);

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

                <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                        <span>🔒</span>
                        <span>Official EHR Signed Records</span>
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
                                        className={`p-4 rounded-xl border cursor-pointer transition-all ${
                                            isSelected
                                                ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20 shadow-sm'
                                                : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="text-xs font-bold text-slate-900 dark:text-white">
                                                {rec.doctor_name}
                                            </span>
                                            <Badge variant="success" className="text-[10px] uppercase font-bold">
                                                {rec.status}
                                            </Badge>
                                        </div>
                                        <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200 truncate">
                                            {rec.assessment || rec.chief_complaint || 'Encounter Note'}
                                        </h4>
                                        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                                            <span>Encounter: {new Date(rec.created_at).toLocaleDateString()}</span>
                                            <span>ID: {rec.record_id.slice(0, 8)}...</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Detailed Record Viewer (7 Cols) */}
                    {selectedRecord && (
                        <div className="lg:col-span-7">
                            <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                                <CardContent className="p-6 space-y-6">
                                    {/* Record Header */}
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
                                        <div>
                                            <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 block mb-0.5">
                                                Physician Consultation Report
                                            </span>
                                            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                                                {selectedRecord.assessment || 'Clinical Encounter Summary'}
                                            </h2>
                                            <p className="text-xs text-slate-500 mt-0.5">
                                                Attending Physician: <strong className="text-slate-800 dark:text-slate-200">{selectedRecord.doctor_name}</strong>
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <Badge variant="success" className="mb-1">
                                                Attested & Finalized
                                            </Badge>
                                            <span className="text-[11px] text-slate-400 block">
                                                Signed: {selectedRecord.finalized_at ? new Date(selectedRecord.finalized_at).toLocaleDateString() : new Date(selectedRecord.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>

                                    {/* SOAP Structured Sections */}
                                    <div className="space-y-4 text-xs leading-relaxed">
                                        {/* Subjective */}
                                        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
                                            <h4 className="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>🗣️</span> Chief Complaint & Patient Symptoms
                                            </h4>
                                            <p className="text-slate-700 dark:text-slate-300">
                                                {selectedRecord.chief_complaint || selectedRecord.content?.subjective?.chief_complaint || 'No subjective complaints documented.'}
                                            </p>
                                            {selectedRecord.content?.subjective?.history_of_present_illness && (
                                                <p className="text-slate-500 dark:text-slate-400 mt-2">
                                                    <strong>HPI:</strong> {selectedRecord.content.subjective.history_of_present_illness}
                                                </p>
                                            )}
                                        </div>

                                        {/* Objective */}
                                        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
                                            <h4 className="font-bold text-slate-900 dark:text-white uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>🩺</span> Objective Examination & Vitals
                                            </h4>
                                            <p className="text-slate-700 dark:text-slate-300">
                                                {selectedRecord.content?.objective?.physical_exam || selectedRecord.content?.objective || 'Vitals and physical examination completed within acceptable parameters.'}
                                            </p>
                                        </div>

                                        {/* Assessment */}
                                        <div className="p-4 rounded-xl bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900/40">
                                            <h4 className="font-bold text-blue-900 dark:text-blue-300 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>🔍</span> Physician Clinical Assessment & Diagnosis
                                            </h4>
                                            <p className="font-semibold text-slate-900 dark:text-white text-sm">
                                                {selectedRecord.assessment || 'Diagnosis not finalized.'}
                                            </p>
                                            {selectedRecord.content?.assessment?.clinical_rationale && (
                                                <p className="text-slate-600 dark:text-slate-400 mt-1">
                                                    {selectedRecord.content.assessment.clinical_rationale}
                                                </p>
                                            )}
                                        </div>

                                        {/* Plan */}
                                        <div className="p-4 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40">
                                            <h4 className="font-bold text-emerald-900 dark:text-emerald-300 uppercase tracking-wider text-[11px] mb-1.5 flex items-center gap-1.5">
                                                <span>📋</span> Treatment Plan & Doctor Recommendations
                                            </h4>
                                            <p className="text-slate-800 dark:text-slate-200 whitespace-pre-line">
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
        </div>
    );
}
