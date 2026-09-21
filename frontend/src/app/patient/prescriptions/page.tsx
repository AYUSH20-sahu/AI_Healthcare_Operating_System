'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { patientPortalApi, PatientPortalPrescriptionItem } from '@/lib/api';
import { Card, CardContent, Button, Badge } from '@/components/ui';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export default function PatientPrescriptionsPage() {
    const [prescriptions, setPrescriptions] = useState<PatientPortalPrescriptionItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [downloadingId, setDownloadingId] = useState<string | null>(null);

    useEffect(() => {
        loadPrescriptions();
    }, []);

    const loadPrescriptions = async () => {
        setIsLoading(true);
        try {
            const data = await patientPortalApi.getPrescriptions();
            setPrescriptions(data);
        } catch (err) {
            console.error('Failed to load prescriptions:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const downloadPdf = async (prescriptionId: string, doctorName: string) => {
        setDownloadingId(prescriptionId);
        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${API_BASE}/prescriptions/${prescriptionId}/pdf`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Prescription_${prescriptionId.slice(0, 8).toUpperCase()}_Dr_${doctorName.replace(/\s+/g, '_')}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('PDF download failed:', err);
            alert('Could not generate PDF. Please try again.');
        } finally {
            setDownloadingId(null);
        }
    };

    return (
        <div className="space-y-6 pb-12 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                        <span>💊 Digital Prescriptions & Pharmacy Orders</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Doctor-signed medication orders with dosage instructions, refill counts, and dispensary guidance.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => window.print()}
                        className="text-xs"
                    >
                        🖨️ Print Active Prescriptions
                    </Button>
                </div>
            </div>

            {/* Prescriptions List */}
            {isLoading ? (
                <div className="space-y-4">
                    {[1, 2].map((i) => (
                        <Card key={i} className="p-6 animate-pulse border border-slate-200 dark:border-slate-800">
                            <div className="h-5 w-1/3 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                            <div className="h-4 w-1/2 bg-slate-200 dark:bg-slate-700 rounded" />
                        </Card>
                    ))}
                </div>
            ) : prescriptions.length > 0 ? (
                <div className="space-y-6">
                    {prescriptions.map((rx) => (
                        <Card
                            key={rx.prescription_id}
                            className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm"
                        >
                            <CardContent className="p-6 space-y-5">
                                {/* Prescription Header */}
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
                                    <div>
                                        <span className="text-[11px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 block mb-0.5">
                                            Authorized e-Prescription
                                        </span>
                                        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                            Prescribed by {rx.doctor_name}
                                        </h3>
                                        <p className="text-xs text-slate-500 mt-0.5">
                                            Prescription ID: <span className="font-mono">{rx.prescription_id}</span>
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <Badge variant="success" className="mb-1 uppercase font-bold text-[10px]">
                                            {rx.status}
                                        </Badge>
                                        <span className="text-[11px] text-slate-400 block">
                                            Signed: {rx.finalized_at ? new Date(rx.finalized_at).toLocaleDateString() : new Date(rx.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                </div>

                                {/* Medications Table / Cards */}
                                <div>
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                                        Prescribed Medications ({rx.medications.length})
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {rx.medications.map((med, idx) => (
                                            <div
                                                key={idx}
                                                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 space-y-2"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <h5 className="text-sm font-bold text-slate-900 dark:text-white">
                                                        {med.name}
                                                    </h5>
                                                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300">
                                                        {med.dosage}
                                                    </span>
                                                </div>

                                                <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-300">
                                                    <div>
                                                        <span className="text-slate-400 block text-[11px]">Frequency</span>
                                                        <span className="font-semibold">{med.frequency}</span>
                                                    </div>
                                                    <div>
                                                        <span className="text-slate-400 block text-[11px]">Duration</span>
                                                        <span className="font-semibold">{med.duration}</span>
                                                    </div>
                                                    <div>
                                                        <span className="text-slate-400 block text-[11px]">Route</span>
                                                        <span className="font-semibold">{med.route || 'Oral'}</span>
                                                    </div>
                                                    <div>
                                                        <span className="text-slate-400 block text-[11px]">Refills Remaining</span>
                                                        <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                                                            {med.refills ?? 0}
                                                        </span>
                                                    </div>
                                                </div>

                                                {med.instructions && (
                                                    <p className="text-[11px] text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-200 dark:border-slate-800">
                                                        <strong>Instructions:</strong> {med.instructions}
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {rx.notes && (
                                    <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl text-xs text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                                        <strong>Physician Notes:</strong> {rx.notes}
                                    </div>
                                )}

                                {/* Dispensing Guidance Footer */}
                                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                    <span className="text-xs text-slate-400">Present this digital order or QR at any participating hospital dispensary or pharmacy.</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                                            Physician Electronic Sign-off Stamped ✅
                                        </span>
                                        {rx.status === 'finalized' && (
                                            <Button
                                                id={`download-pdf-${rx.prescription_id}`}
                                                variant="secondary"
                                                size="sm"
                                                onClick={() => downloadPdf(rx.prescription_id, rx.doctor_name)}
                                                disabled={downloadingId === rx.prescription_id}
                                                className="text-xs flex items-center gap-1.5"
                                            >
                                                {downloadingId === rx.prescription_id ? (
                                                    <><span className="animate-spin">⏳</span> Generating...</>
                                                ) : (
                                                    <><span>📄</span> Download PDF</>
                                                )}
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            ) : (
                <Card className="p-12 text-center border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 rounded-2xl">
                    <span className="text-3xl block mb-2">💊</span>
                    <h3 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                        No active prescriptions found
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                        When your attending doctor prescribes medications during your consultation, they will be listed here with dosage and refill instructions.
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
