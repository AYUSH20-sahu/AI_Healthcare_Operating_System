'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { patientsApi, appointmentsApi, medicalRecordsApi, prescriptionsApi } from '@/lib/api';
import { PatientSummary } from '@/components/PatientSummary';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export default function DoctorPatientDetailPage() {
    const params = useParams();
    const router = useRouter();
    const patientId = params?.id as string;

    const [patient, setPatient] = useState<any | null>(null);
    const [records, setRecords] = useState<any[]>([]);
    const [prescriptions, setPrescriptions] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!patientId) return;

        async function fetchPatientDetail() {
            try {
                setLoading(true);
                const [pRes, rRes, prRes] = await Promise.allSettled([
                    patientsApi.get(patientId),
                    medicalRecordsApi.list({ patient_id: patientId }),
                    prescriptionsApi.list({ patient_id: patientId }),
                ]);

                if (pRes.status === 'fulfilled') {
                    setPatient(pRes.value);
                }
                if (rRes.status === 'fulfilled' && rRes.value.records) {
                    setRecords(rRes.value.records);
                }
                if (prRes.status === 'fulfilled' && prRes.value.prescriptions) {
                    setPrescriptions(prRes.value.prescriptions);
                }
            } catch (err) {
                console.error('Failed to load patient detail:', err);
            } finally {
                setLoading(false);
            }
        }

        fetchPatientDetail();
    }, [patientId]);

    if (loading) {
        return (
            <div className="p-12 text-center text-xs text-slate-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500 mx-auto mb-2" />
                Loading comprehensive electronic health record...
            </div>
        );
    }

    if (!patient) {
        return (
            <div className="p-8 text-center space-y-3">
                <p className="text-sm text-slate-500">Patient not found or inaccessible.</p>
                <Link href="/doctor/appointments">
                    <Button variant="secondary" size="sm">Back to Appointments</Button>
                </Link>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            {/* Nav Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Link href="/doctor/appointments" className="text-xs text-teal-600 dark:text-teal-400 hover:underline">
                            ← Outpatient Schedule
                        </Link>
                        <span className="text-slate-400 text-xs">•</span>
                        <Link href="/doctor" className="text-xs text-slate-500 hover:underline">
                            Doctor Workspace
                        </Link>
                    </div>
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                            {patient.full_name}
                        </h1>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20 font-medium">
                            {patient.gender || 'Patient'} • Age: {patient.age || 'Adult'}
                        </span>
                    </div>
                    <p className="text-xs text-slate-500">
                        ABHA: {patient.abha_address || 'Not Linked'} • Contact: {patient.phone || 'Protected'}
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Link href={`/doctor?selected=${patientId}`}>
                        <Button variant="primary" size="sm">
                            Open Copilot Consultation 🎙️
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Grid Layout: Summary on Left, Clinical Records on Right */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-4">
                    <PatientSummary patientId={patientId} />
                </div>

                <div className="lg:col-span-8 space-y-6">
                    {/* Clinical History & Consultations */}
                    <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
                        <CardHeader className="p-4 border-b border-slate-200 dark:border-slate-800">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-semibold">Consultation & SOAP Encounters</CardTitle>
                                <Badge variant="primary">{records.length} Records</Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-4 space-y-3">
                            {records.length === 0 ? (
                                <p className="text-xs text-slate-400 py-4 text-center">No past clinical encounter notes on record.</p>
                            ) : (
                                records.map((rec) => (
                                    <div key={rec.record_id} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5 text-xs">
                                        <div className="flex items-center justify-between">
                                            <span className="font-semibold text-slate-900 dark:text-slate-100">
                                                Encounter: {new Date(rec.created_at).toLocaleDateString()}
                                            </span>
                                            <Badge variant={rec.status === 'FINALIZED' ? 'success' : 'warning'}>
                                                {rec.status}
                                            </Badge>
                                        </div>
                                        <p className="text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
                                            {typeof rec.content === 'object' ? JSON.stringify(rec.content, null, 2) : rec.content}
                                        </p>
                                    </div>
                                ))
                            )}
                        </CardContent>
                    </Card>

                    {/* Prescriptions & Medications */}
                    <Card className="border-slate-200 dark:border-slate-800 shadow-sm">
                        <CardHeader className="p-4 border-b border-slate-200 dark:border-slate-800">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-sm font-semibold">Active & Historical Prescriptions</CardTitle>
                                <Badge variant="primary">{prescriptions.length} Orders</Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-4 space-y-3">
                            {prescriptions.length === 0 ? (
                                <p className="text-xs text-slate-400 py-4 text-center">No medications prescribed yet.</p>
                            ) : (
                                prescriptions.map((rx) => (
                                    <div key={rx.prescription_id} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5 text-xs">
                                        <div className="flex items-center justify-between">
                                            <span className="font-semibold text-teal-600 dark:text-teal-400">
                                                Order ID: {rx.prescription_id.substring(0, 8)}...
                                            </span>
                                            <Badge variant={rx.status === 'FINALIZED' ? 'success' : 'warning'}>
                                                {rx.status}
                                            </Badge>
                                        </div>
                                        <div className="text-slate-600 dark:text-slate-300">
                                            {Array.isArray(rx.medications) ? (
                                                <ul className="list-disc pl-4 space-y-0.5">
                                                    {rx.medications.map((m: any, idx: number) => (
                                                        <li key={idx}>
                                                            <strong>{m.name || m.drug}</strong> — {m.dosage} ({m.frequency || 'Daily'})
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p>{JSON.stringify(rx.medications)}</p>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
