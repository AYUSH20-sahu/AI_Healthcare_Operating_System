'use client';

import React, { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { Card, CardContent } from '@/components/ui';

// ─── Types ───────────────────────────────────────────────────────────────────

interface AssignedPatient {
    patientId: string;
    patientName: string;
    age: number;
    gender: string;
    bedNumber: string;
    ward: string;
    admittedFor: string;
    attendingPhysician: string;
    admitDate: string;
    day: number;
    status: 'stable' | 'attention' | 'critical';
    lastVitals?: { bp: string; pulse: number; spo2: number; temp: number };
    pendingMeds: number;
    pendingRounds: number;
    diet: string;
    allergies: string[];
    codeStatus: 'Full Code' | 'DNR' | 'DNI';
    isolationPrecautions?: string;
}

// ─── Mock data ────────────────────────────────────────────────────────────────

const ASSIGNED_PATIENTS: AssignedPatient[] = [
    {
        patientId: 'UHID-88219', patientName: 'Rajesh Sharma', age: 62, gender: 'M',
        bedNumber: 'ICU-04', ward: 'Intensive Care Unit', admittedFor: 'Post-CABG Recovery',
        attendingPhysician: 'Dr. Sarah Jenkins (Cardiology)', admitDate: '2025-09-18', day: 3,
        status: 'stable', lastVitals: { bp: '138/88', pulse: 94, spo2: 95, temp: 98.6 },
        pendingMeds: 1, pendingRounds: 0, diet: 'Cardiac Diet (Low Sodium)',
        allergies: ['Penicillin', 'Aspirin'], codeStatus: 'Full Code',
    },
    {
        patientId: 'UHID-90412', patientName: 'Anita Desai', age: 54, gender: 'F',
        bedNumber: 'ICU-06', ward: 'Intensive Care Unit', admittedFor: 'Acute Pulmonary Edema',
        attendingPhysician: 'Dr. Michael Chen (Pulmonology)', admitDate: '2025-09-21', day: 1,
        status: 'critical', lastVitals: { bp: '165/102', pulse: 118, spo2: 89, temp: 99.4 },
        pendingMeds: 2, pendingRounds: 1, diet: 'Fluid Restricted (1L/day)',
        allergies: ['Sulfa'], codeStatus: 'Full Code', isolationPrecautions: 'Contact',
    },
    {
        patientId: 'UHID-71029', patientName: 'Vikram Patel', age: 41, gender: 'M',
        bedNumber: 'GW-201', ward: 'General Ward B', admittedFor: 'Post-Appendectomy (Day 1)',
        attendingPhysician: 'Dr. Arvind Swaminathan (Surgery)', admitDate: '2025-09-20', day: 2,
        status: 'attention', lastVitals: { bp: '122/78', pulse: 88, spo2: 97, temp: 99.2 },
        pendingMeds: 1, pendingRounds: 1, diet: 'Clear Liquids progressing to soft',
        allergies: [], codeStatus: 'Full Code',
    },
    {
        patientId: 'UHID-65311', patientName: 'Meena Krishnan', age: 33, gender: 'F',
        bedNumber: 'GW-204', ward: 'General Ward B', admittedFor: 'Type 1 DM Ketoacidosis',
        attendingPhysician: 'Dr. Priya Rao (Endocrinology)', admitDate: '2025-09-19', day: 3,
        status: 'stable', lastVitals: { bp: '118/74', pulse: 76, spo2: 98, temp: 98.4 },
        pendingMeds: 1, pendingRounds: 0, diet: 'ADA Diabetic Diet',
        allergies: ['Ibuprofen'], codeStatus: 'Full Code',
    },
    {
        patientId: 'UHID-80027', patientName: 'Sunita Nair', age: 28, gender: 'F',
        bedNumber: 'OBS-01', ward: 'Obs & Gynae Ward', admittedFor: 'Antepartum Hypertension (34 weeks)',
        attendingPhysician: 'Dr. Lakshmi Venkatesh (Obs & Gyn)', admitDate: '2025-09-20', day: 2,
        status: 'attention', lastVitals: { bp: '152/96', pulse: 82, spo2: 98, temp: 98.6 },
        pendingMeds: 1, pendingRounds: 1, diet: 'Low Salt Maternity Diet',
        allergies: [], codeStatus: 'Full Code',
    },
    {
        patientId: 'UHID-81104', patientName: 'Pooja Gupta', age: 26, gender: 'F',
        bedNumber: 'OBS-03', ward: 'Obs & Gynae Ward', admittedFor: 'Post-Caesarean Section (Day 2)',
        attendingPhysician: 'Dr. Lakshmi Venkatesh (Obs & Gyn)', admitDate: '2025-09-19', day: 3,
        status: 'stable', lastVitals: { bp: '115/70', pulse: 74, spo2: 99, temp: 98.2 },
        pendingMeds: 0, pendingRounds: 1, diet: 'Soft Diet — Lactation Support',
        allergies: [], codeStatus: 'Full Code',
    },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function statusRing(status: string) {
    if (status === 'critical') return 'ring-2 ring-rose-400 dark:ring-rose-600';
    if (status === 'attention') return 'ring-2 ring-amber-400 dark:ring-amber-600';
    return 'ring-1 ring-slate-200 dark:ring-slate-700';
}

function statusBadge(status: string) {
    if (status === 'critical') return 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300';
    if (status === 'attention') return 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300';
    return 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300';
}

function spo2Color(v: number) {
    if (v < 90) return 'text-rose-600 dark:text-rose-400 font-bold';
    if (v < 94) return 'text-amber-600 dark:text-amber-400 font-semibold';
    return 'text-slate-700 dark:text-slate-300';
}

// ─── Patient Card ─────────────────────────────────────────────────────────────

function PatientCard({ patient }: { patient: AssignedPatient }) {
    const [expanded, setExpanded] = useState(false);
    const v = patient.lastVitals;

    return (
        <div className={`rounded-2xl bg-white dark:bg-slate-900/50 p-4 space-y-3 transition-all ${statusRing(patient.status)}`}>
            {/* Header row */}
            <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${
                    patient.status === 'critical' ? 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300' :
                    patient.status === 'attention' ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300' :
                    'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                }`}>
                    {patient.patientName.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{patient.patientName}</p>
                        <span className="text-xs text-slate-400">{patient.age}y {patient.gender}</span>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${statusBadge(patient.status)}`}>{patient.status}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <span className="text-xs font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">Bed {patient.bedNumber}</span>
                        <span className="text-xs text-slate-500">{patient.ward}</span>
                        <span className="text-xs text-slate-400">Day {patient.day}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5 truncate">{patient.admittedFor}</p>
                </div>
                <button
                    id={`patient-expand-${patient.patientId}`}
                    type="button"
                    onClick={() => setExpanded(e => !e)}
                    className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                    <svg className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </button>
            </div>

            {/* Vitals strip */}
            {v && (
                <div className="flex gap-2 flex-wrap">
                    {[
                        { label: 'BP', value: v.bp },
                        { label: 'HR', value: `${v.pulse}` },
                        { label: 'SpO₂', value: `${v.spo2}%`, colorClass: spo2Color(v.spo2) },
                        { label: 'Temp', value: `${v.temp}°F` },
                    ].map(({ label, value, colorClass }) => (
                        <div key={label} className="flex items-center gap-1 bg-slate-50 dark:bg-slate-800/60 rounded-lg px-2 py-1">
                            <span className="text-[10px] text-slate-400 font-semibold">{label}</span>
                            <span className={`text-xs font-bold ${colorClass || 'text-slate-700 dark:text-slate-300'}`}>{value}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Pending tasks indicator */}
            <div className="flex gap-2">
                {patient.pendingMeds > 0 && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800">
                        <svg className="w-3 h-3 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="text-[10px] font-bold text-amber-700 dark:text-amber-300">{patient.pendingMeds} Med{patient.pendingMeds > 1 ? 's' : ''} Due</span>
                    </div>
                )}
                {patient.pendingRounds > 0 && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800">
                        <svg className="w-3 h-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        <span className="text-[10px] font-bold text-blue-700 dark:text-blue-300">{patient.pendingRounds} Round Task{patient.pendingRounds > 1 ? 's' : ''}</span>
                    </div>
                )}
                {patient.pendingMeds === 0 && patient.pendingRounds === 0 && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800">
                        <svg className="w-3 h-3 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-300">All Tasks Clear</span>
                    </div>
                )}
                {patient.isolationPrecautions && (
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-50 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-800">
                        <span className="text-[10px] font-bold text-purple-700 dark:text-purple-300">⚠ {patient.isolationPrecautions} Isolation</span>
                    </div>
                )}
            </div>

            {/* Expanded details */}
            {expanded && (
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                        {[
                            { label: 'Attending Physician', value: patient.attendingPhysician },
                            { label: 'Admit Date', value: new Date(patient.admitDate).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) },
                            { label: 'Diet Order', value: patient.diet },
                            { label: 'Code Status', value: patient.codeStatus },
                        ].map(({ label, value }) => (
                            <div key={label}>
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-0.5">{label}</p>
                                <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">{value}</p>
                            </div>
                        ))}
                    </div>
                    {patient.allergies.length > 0 && (
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Known Allergies</p>
                            <div className="flex flex-wrap gap-1.5">
                                {patient.allergies.map(a => (
                                    <span key={a} className="text-xs px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 font-medium border border-rose-200 dark:border-rose-800">
                                        ⚠ {a}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function NursePatientsPage() {
    const { user } = useAuth();
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<'all' | 'critical' | 'attention' | 'stable'>('all');
    const [wardFilter, setWardFilter] = useState<string>('all');

    const wards = ['all', ...Array.from(new Set(ASSIGNED_PATIENTS.map(p => p.ward)))];

    const filtered = ASSIGNED_PATIENTS.filter(p => {
        const matchSearch = !search || p.patientName.toLowerCase().includes(search.toLowerCase()) || p.bedNumber.toLowerCase().includes(search.toLowerCase()) || p.admittedFor.toLowerCase().includes(search.toLowerCase());
        const matchStatus = statusFilter === 'all' || p.status === statusFilter;
        const matchWard = wardFilter === 'all' || p.ward === wardFilter;
        return matchSearch && matchStatus && matchWard;
    });

    const counts = {
        critical: ASSIGNED_PATIENTS.filter(p => p.status === 'critical').length,
        attention: ASSIGNED_PATIENTS.filter(p => p.status === 'attention').length,
        stable: ASSIGNED_PATIENTS.filter(p => p.status === 'stable').length,
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">My Assigned Patients</h1>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                    {ASSIGNED_PATIENTS.length} patients across {wards.length - 1} ward{wards.length - 1 > 1 ? 's' : ''} assigned to your shift
                </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-3">
                {[
                    { label: 'Critical', value: counts.critical, color: 'rose', filter: 'critical' as const },
                    { label: 'Attention', value: counts.attention, color: 'amber', filter: 'attention' as const },
                    { label: 'Stable', value: counts.stable, color: 'emerald', filter: 'stable' as const },
                ].map(({ label, value, color, filter }) => (
                    <button
                        key={filter}
                        id={`patient-filter-${filter}`}
                        type="button"
                        onClick={() => setStatusFilter(prev => prev === filter ? 'all' : filter)}
                        className={`${statusFilter === filter ? `ring-2 ring-${color}-500` : ''} bg-${color}-50 dark:bg-${color}-900/20 border border-${color}-100 dark:border-${color}-800/40 rounded-xl p-4 text-left transition-all hover:scale-[1.02]`}
                    >
                        <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
                        <p className={`text-xs font-medium text-${color}-700 dark:text-${color}-300 mt-0.5`}>{label}</p>
                    </button>
                ))}
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                    <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <input
                        id="patient-search"
                        type="search"
                        placeholder="Search patient name, bed, or condition…"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-sm dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div className="flex gap-2">
                    {wards.map(w => (
                        <button
                            key={w}
                            type="button"
                            onClick={() => setWardFilter(w)}
                            className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors whitespace-nowrap ${
                                wardFilter === w
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                            }`}
                        >
                            {w === 'all' ? 'All Wards' : w.replace('Intensive Care Unit', 'ICU').replace('General Ward B', 'Gen. Ward').replace('Obs & Gynae Ward', 'OBS')}
                        </button>
                    ))}
                </div>
            </div>

            {/* Patient grid */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {filtered
                    .sort((a, b) => {
                        const o = { critical: 0, attention: 1, stable: 2 };
                        return o[a.status] - o[b.status];
                    })
                    .map(p => <PatientCard key={p.patientId} patient={p} />)
                }
            </div>

            {filtered.length === 0 && (
                <div className="text-center py-12">
                    <p className="text-sm text-slate-400">No patients match your filters.</p>
                </div>
            )}
        </div>
    );
}
