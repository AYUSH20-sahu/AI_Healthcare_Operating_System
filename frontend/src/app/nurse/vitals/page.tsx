'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { Button, Card, CardContent, Badge, Input, Modal } from '@/components/ui';

// ─── Types ───────────────────────────────────────────────────────────────────

interface VitalReading {
    id: string;
    patientName: string;
    patientId: string;
    bedNumber: string;
    ward: string;
    age: number;
    gender: string;
    admittedFor: string;
    systolic: number;
    diastolic: number;
    pulse: number;
    spo2: number;
    temperature: number;
    respiratoryRate: number;
    painScore: number;
    recordedAt: string;
    recordedBy?: string;
    notes?: string;
    status: 'stable' | 'attention' | 'critical';
}

interface PatientBed {
    bedNumber: string;
    ward: string;
    patientName: string;
    patientId: string;
    age: number;
    gender: string;
    admittedFor: string;
    attendingPhysician: string;
    latestVitals?: VitalReading;
    status: 'stable' | 'attention' | 'critical';
}

// ─── Mock patient beds ────────────────────────────────────────────────────────

const PATIENT_BEDS: PatientBed[] = [
    { bedNumber: 'ICU-04', ward: 'Intensive Care Unit', patientName: 'Rajesh Sharma', patientId: 'UHID-88219', age: 62, gender: 'M', admittedFor: 'Post-CABG Recovery', attendingPhysician: 'Dr. Sarah Jenkins', status: 'stable' },
    { bedNumber: 'ICU-06', ward: 'Intensive Care Unit', patientName: 'Anita Desai', patientId: 'UHID-90412', age: 54, gender: 'F', admittedFor: 'Acute Pulmonary Edema', attendingPhysician: 'Dr. Michael Chen', status: 'critical' },
    { bedNumber: 'GW-201', ward: 'General Ward B', patientName: 'Vikram Patel', patientId: 'UHID-71029', age: 41, gender: 'M', admittedFor: 'Post-Appendectomy (Day 1)', attendingPhysician: 'Dr. Arvind Swaminathan', status: 'attention' },
    { bedNumber: 'GW-204', ward: 'General Ward B', patientName: 'Meena Krishnan', patientId: 'UHID-65311', age: 33, gender: 'F', admittedFor: 'Type 1 DM Crisis', attendingPhysician: 'Dr. Priya Rao', status: 'stable' },
    { bedNumber: 'OBS-01', ward: 'Obs & Gynae Ward', patientName: 'Sunita Nair', patientId: 'UHID-80027', age: 28, gender: 'F', admittedFor: 'Antepartum Hypertension', attendingPhysician: 'Dr. Lakshmi Venkatesh', status: 'attention' },
    { bedNumber: 'OBS-03', ward: 'Obs & Gynae Ward', patientName: 'Pooja Gupta', patientId: 'UHID-81104', age: 26, gender: 'F', admittedFor: 'Post-CS Day 2', attendingPhysician: 'Dr. Lakshmi Venkatesh', status: 'stable' },
];

// ─── Helper functions ─────────────────────────────────────────────────────────

function computeStatus(s: number, d: number, pulse: number, spo2: number, temp: number): 'stable' | 'attention' | 'critical' {
    if (spo2 < 90 || s > 180 || pulse > 130 || temp > 39.5) return 'critical';
    if (spo2 < 94 || s > 160 || pulse > 110 || temp > 38.5 || d > 100) return 'attention';
    return 'stable';
}

function statusBadge(status: string) {
    if (status === 'critical') return 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800';
    if (status === 'attention') return 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800';
    return 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800';
}

function vitalColor(label: string, value: number): string {
    const red = 'text-rose-600 dark:text-rose-400 font-bold';
    const amber = 'text-amber-600 dark:text-amber-400 font-semibold';
    const normal = 'text-slate-900 dark:text-slate-100';
    switch (label) {
        case 'SpO₂': return value < 90 ? red : value < 94 ? amber : normal;
        case 'Systolic BP': return value > 180 ? red : value > 160 ? amber : normal;
        case 'Pulse': return value > 130 ? red : value > 110 ? amber : normal;
        case 'Temp (°F)': return value > 39.5 ? red : value > 38.5 ? amber : normal;
        case 'Pain': return value >= 8 ? red : value >= 5 ? amber : normal;
        default: return normal;
    }
}

// ─── Vitals Entry Form ────────────────────────────────────────────────────────

function VitalsModal({ patient, onClose, onSave }: { patient: PatientBed; onClose: () => void; onSave: (v: VitalReading) => void }) {
    const { user } = useAuth();
    const [systolic, setSystolic] = useState(120);
    const [diastolic, setDiastolic] = useState(80);
    const [pulse, setPulse] = useState(72);
    const [spo2, setSpo2] = useState(98);
    const [temperature, setTemperature] = useState(98.6);
    const [respRate, setRespRate] = useState(16);
    const [painScore, setPainScore] = useState(0);
    const [notes, setNotes] = useState('');
    const [saving, setSaving] = useState(false);

    const status = computeStatus(systolic, diastolic, pulse, spo2, temperature);

    const handleSave = async () => {
        setSaving(true);
        // Simulate API call — in production: POST /nurses/vitals
        await new Promise(r => setTimeout(r, 600));
        const reading: VitalReading = {
            id: `vit-${Date.now()}`,
            patientName: patient.patientName,
            patientId: patient.patientId,
            bedNumber: patient.bedNumber,
            ward: patient.ward,
            age: patient.age,
            gender: patient.gender,
            admittedFor: patient.admittedFor,
            systolic, diastolic, pulse, spo2, temperature, respiratoryRate: respRate, painScore,
            recordedAt: new Date().toISOString(),
            recordedBy: user?.full_name || 'Nurse',
            notes,
            status,
        };
        onSave(reading);
        setSaving(false);
    };

    const criticalAlert = status === 'critical';

    return (
        <Modal isOpen onClose={onClose} title={`Record Vitals — ${patient.patientName}`} size="lg">
            <div className="space-y-5">
                {/* Patient context */}
                <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-3 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-blue-700 dark:text-blue-300 font-bold text-sm shrink-0">
                        {patient.patientName.charAt(0)}
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{patient.patientName} · {patient.age}y {patient.gender}</p>
                        <p className="text-xs text-slate-500">Bed {patient.bedNumber} · {patient.admittedFor}</p>
                    </div>
                </div>

                {/* Critical alert */}
                {criticalAlert && (
                    <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl p-3 flex items-center gap-2">
                        <svg className="w-5 h-5 text-rose-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">⚠️ Critical values detected — notify attending physician immediately.</p>
                    </div>
                )}

                {/* Vitals inputs */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">Systolic BP (mmHg)</label>
                        <input id="vital-systolic" type="number" min={60} max={250} value={systolic}
                            onChange={e => setSystolic(Number(e.target.value))}
                            className={`w-full px-3 py-2 rounded-lg border text-sm font-mono ${systolic > 180 ? 'border-rose-400 bg-rose-50 dark:bg-rose-900/20' : systolic > 160 ? 'border-amber-400' : 'border-slate-200 dark:border-slate-700'} dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">Diastolic BP (mmHg)</label>
                        <input id="vital-diastolic" type="number" min={40} max={160} value={diastolic}
                            onChange={e => setDiastolic(Number(e.target.value))}
                            className={`w-full px-3 py-2 rounded-lg border text-sm font-mono ${diastolic > 110 ? 'border-rose-400 bg-rose-50 dark:bg-rose-900/20' : 'border-slate-200 dark:border-slate-700'} dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">Pulse (bpm)</label>
                        <input id="vital-pulse" type="number" min={30} max={220} value={pulse}
                            onChange={e => setPulse(Number(e.target.value))}
                            className={`w-full px-3 py-2 rounded-lg border text-sm font-mono ${pulse > 130 ? 'border-rose-400 bg-rose-50 dark:bg-rose-900/20' : pulse > 110 ? 'border-amber-400' : 'border-slate-200 dark:border-slate-700'} dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">SpO₂ (%)</label>
                        <input id="vital-spo2" type="number" min={50} max={100} value={spo2}
                            onChange={e => setSpo2(Number(e.target.value))}
                            className={`w-full px-3 py-2 rounded-lg border text-sm font-mono ${spo2 < 90 ? 'border-rose-400 bg-rose-50 dark:bg-rose-900/20' : spo2 < 94 ? 'border-amber-400' : 'border-slate-200 dark:border-slate-700'} dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">Temperature (°F)</label>
                        <input id="vital-temp" type="number" min={92} max={108} step={0.1} value={temperature}
                            onChange={e => setTemperature(parseFloat(e.target.value))}
                            className={`w-full px-3 py-2 rounded-lg border text-sm font-mono ${temperature > 39.5 ? 'border-rose-400 bg-rose-50 dark:bg-rose-900/20' : temperature > 38.5 ? 'border-amber-400' : 'border-slate-200 dark:border-slate-700'} dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">Respiratory Rate (/min)</label>
                        <input id="vital-rr" type="number" min={8} max={60} value={respRate}
                            onChange={e => setRespRate(Number(e.target.value))}
                            className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-mono dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                </div>

                {/* Pain score slider */}
                <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">
                        Pain Score: <span className={`text-base font-bold ${painScore >= 8 ? 'text-rose-600' : painScore >= 5 ? 'text-amber-600' : 'text-emerald-600'}`}>{painScore}/10</span>
                    </label>
                    <input id="vital-pain" type="range" min={0} max={10} value={painScore}
                        onChange={e => setPainScore(Number(e.target.value))}
                        className="w-full h-2 rounded-lg accent-blue-600"
                    />
                    <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                        <span>No Pain (0)</span><span>Moderate (5)</span><span>Worst (10)</span>
                    </div>
                </div>

                {/* Notes */}
                <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">Clinical Notes (optional)</label>
                    <textarea id="vital-notes" rows={2} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Patient appears comfortable; IV site clean..." className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
                </div>

                {/* Status preview */}
                <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">Computed Status:</span>
                        <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${statusBadge(status)}`}>{status}</span>
                    </div>
                    <div className="flex gap-2">
                        <Button id="vital-cancel-btn" variant="ghost" onClick={onClose}>Cancel</Button>
                        <Button id="vital-save-btn" onClick={handleSave} disabled={saving}>
                            {saving ? 'Saving…' : 'Save Vitals'}
                        </Button>
                    </div>
                </div>
            </div>
        </Modal>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function NurseVitalsPage() {
    const { user } = useAuth();
    const [beds, setBeds] = useState<PatientBed[]>(PATIENT_BEDS);
    const [selectedBed, setSelectedBed] = useState<PatientBed | null>(null);
    const [selectedWard, setSelectedWard] = useState<string>('all');
    const [historyBed, setHistoryBed] = useState<PatientBed | null>(null);
    const [vitalHistory, setVitalHistory] = useState<Record<string, VitalReading[]>>({});

    const wards = ['all', ...Array.from(new Set(PATIENT_BEDS.map(b => b.ward)))];

    const filteredBeds = selectedWard === 'all' ? beds : beds.filter(b => b.ward === selectedWard);

    const criticalCount = beds.filter(b => b.status === 'critical').length;
    const attentionCount = beds.filter(b => b.status === 'attention').length;

    const handleSave = (reading: VitalReading) => {
        setBeds(prev => prev.map(b =>
            b.bedNumber === reading.bedNumber
                ? { ...b, latestVitals: reading, status: reading.status }
                : b
        ));
        setVitalHistory(prev => ({
            ...prev,
            [reading.bedNumber]: [reading, ...(prev[reading.bedNumber] || [])].slice(0, 10),
        }));
        setSelectedBed(null);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Vitals Charting</h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                        Record and monitor patient vitals across all assigned beds
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {criticalCount > 0 && (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-100 dark:bg-rose-900/40 border border-rose-200 dark:border-rose-800 animate-pulse">
                            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                            <span className="text-xs font-bold text-rose-700 dark:text-rose-300">{criticalCount} Critical</span>
                        </div>
                    )}
                    {attentionCount > 0 && (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-100 dark:bg-amber-900/40 border border-amber-200 dark:border-amber-800">
                            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                            <span className="text-xs font-bold text-amber-700 dark:text-amber-300">{attentionCount} Attention</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3">
                {[
                    { label: 'Total Patients', value: beds.length, color: 'blue' },
                    { label: 'Vitals Recorded', value: Object.values(vitalHistory).reduce((s, h) => s + h.length, 0), color: 'green' },
                    { label: 'Pending This Shift', value: beds.filter(b => !b.latestVitals).length, color: 'amber' },
                ].map(({ label, value, color }) => (
                    <div key={label} className={`bg-${color}-50 dark:bg-${color}-900/20 border border-${color}-100 dark:border-${color}-800/40 rounded-xl p-4`}>
                        <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
                        <p className={`text-xs font-medium text-${color}-700 dark:text-${color}-300 mt-0.5`}>{label}</p>
                    </div>
                ))}
            </div>

            {/* Ward filter */}
            <div className="flex flex-wrap gap-2">
                {wards.map(w => (
                    <button
                        key={w}
                        type="button"
                        id={`ward-filter-${w.replace(/\s+/g, '-').toLowerCase()}`}
                        onClick={() => setSelectedWard(w)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                            selectedWard === w
                                ? 'bg-blue-600 text-white'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                        }`}
                    >
                        {w === 'all' ? 'All Wards' : w}
                    </button>
                ))}
            </div>

            {/* Patient Bed Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                {filteredBeds.map(bed => {
                    const v = bed.latestVitals;
                    const history = vitalHistory[bed.bedNumber] || [];
                    return (
                        <div key={bed.bedNumber} className={`rounded-2xl border-2 p-4 space-y-3 transition-all ${
                            bed.status === 'critical'
                                ? 'border-rose-300 dark:border-rose-800 bg-rose-50/30 dark:bg-rose-900/10'
                                : bed.status === 'attention'
                                ? 'border-amber-300 dark:border-amber-800 bg-amber-50/30 dark:bg-amber-900/10'
                                : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/40'
                        }`}>
                            {/* Bed header */}
                            <div className="flex items-start justify-between gap-2">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-bold font-mono bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">{bed.bedNumber}</span>
                                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${statusBadge(bed.status)}`}>{bed.status}</span>
                                    </div>
                                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 mt-1.5">{bed.patientName}</p>
                                    <p className="text-xs text-slate-500">{bed.age}y {bed.gender} · {bed.admittedFor}</p>
                                </div>
                                {bed.status === 'critical' && (
                                    <div className="w-8 h-8 rounded-xl bg-rose-100 dark:bg-rose-900/40 flex items-center justify-center animate-pulse shrink-0">
                                        <svg className="w-4 h-4 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    </div>
                                )}
                            </div>

                            {/* Vitals grid */}
                            {v ? (
                                <div className="grid grid-cols-3 gap-2">
                                    {[
                                        { label: 'BP', value: `${v.systolic}/${v.diastolic}`, unit: 'mmHg', colorKey: 'Systolic BP', colorVal: v.systolic },
                                        { label: 'Pulse', value: String(v.pulse), unit: 'bpm', colorKey: 'Pulse', colorVal: v.pulse },
                                        { label: 'SpO₂', value: `${v.spo2}%`, unit: '', colorKey: 'SpO₂', colorVal: v.spo2 },
                                        { label: 'Temp', value: `${v.temperature}°F`, unit: '', colorKey: 'Temp (°F)', colorVal: v.temperature },
                                        { label: 'RR', value: `${v.respiratoryRate}/min`, unit: '', colorKey: '', colorVal: 0 },
                                        { label: 'Pain', value: `${v.painScore}/10`, unit: '', colorKey: 'Pain', colorVal: v.painScore },
                                    ].map(({ label, value, colorKey, colorVal }) => (
                                        <div key={label} className="bg-white dark:bg-slate-800/80 rounded-lg p-2 text-center">
                                            <p className="text-[10px] text-slate-400 uppercase font-semibold">{label}</p>
                                            <p className={`text-sm font-bold mt-0.5 ${colorKey ? vitalColor(colorKey, colorVal) : 'text-slate-900 dark:text-slate-100'}`}>{value}</p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="bg-slate-50 dark:bg-slate-800/40 rounded-xl p-3 text-center">
                                    <p className="text-xs text-slate-400 italic">No vitals recorded yet this shift</p>
                                </div>
                            )}

                            {v && (
                                <p className="text-[10px] text-slate-400 text-right">
                                    Last by {v.recordedBy} · {new Date(v.recordedAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                                </p>
                            )}

                            {/* Actions */}
                            <div className="flex gap-2 pt-1">
                                <button
                                    id={`record-vitals-${bed.bedNumber}`}
                                    type="button"
                                    onClick={() => setSelectedBed(bed)}
                                    className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
                                >
                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                    </svg>
                                    Record Vitals
                                </button>
                                {history.length > 0 && (
                                    <button
                                        id={`view-history-${bed.bedNumber}`}
                                        type="button"
                                        onClick={() => setHistoryBed(bed)}
                                        className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                                    >
                                        History ({history.length})
                                    </button>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Record Vitals Modal */}
            {selectedBed && (
                <VitalsModal patient={selectedBed} onClose={() => setSelectedBed(null)} onSave={handleSave} />
            )}

            {/* History Modal */}
            {historyBed && (
                <Modal isOpen onClose={() => setHistoryBed(null)} title={`Vitals History — ${historyBed.patientName}`} size="lg">
                    <div className="space-y-2 max-h-[500px] overflow-y-auto">
                        {(vitalHistory[historyBed.bedNumber] || []).map((v, i) => (
                            <div key={v.id} className="border border-slate-200 dark:border-slate-700 rounded-xl p-3">
                                <div className="flex items-center justify-between mb-2">
                                    <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                        {new Date(v.recordedAt).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                        {' · '}{v.recordedBy}
                                    </p>
                                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${statusBadge(v.status)}`}>{v.status}</span>
                                </div>
                                <div className="grid grid-cols-3 gap-2">
                                    {[
                                        { label: 'BP', value: `${v.systolic}/${v.diastolic}` },
                                        { label: 'Pulse', value: `${v.pulse} bpm` },
                                        { label: 'SpO₂', value: `${v.spo2}%` },
                                        { label: 'Temp', value: `${v.temperature}°F` },
                                        { label: 'RR', value: `${v.respiratoryRate}/min` },
                                        { label: 'Pain', value: `${v.painScore}/10` },
                                    ].map(({ label, value }) => (
                                        <div key={label} className="text-xs">
                                            <span className="text-slate-400">{label}: </span>
                                            <span className="text-slate-900 dark:text-slate-100 font-medium">{value}</span>
                                        </div>
                                    ))}
                                </div>
                                {v.notes && <p className="text-xs text-slate-500 mt-2 italic">"{v.notes}"</p>}
                            </div>
                        ))}
                    </div>
                </Modal>
            )}
        </div>
    );
}
