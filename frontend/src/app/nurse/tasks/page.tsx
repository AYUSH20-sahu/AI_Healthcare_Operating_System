'use client';

import React, { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { Card, CardContent, Badge, Modal, Button } from '@/components/ui';

// ─── Types ───────────────────────────────────────────────────────────────────

type TaskStatus = 'pending' | 'administered' | 'delayed' | 'refused';
type WardRoundStatus = 'pending' | 'done';
type Priority = 'urgent' | 'routine' | 'stat';

interface MedTask {
    id: string;
    patientName: string;
    patientId: string;
    bedNumber: string;
    ward: string;
    medication: string;
    dose: string;
    route: string;
    dueTime: string;
    overdue: boolean;
    priority: Priority;
    status: TaskStatus;
    notes?: string;
    prescribedBy: string;
}

interface RoundTask {
    id: string;
    patientName: string;
    bedNumber: string;
    task: string;
    category: 'positioning' | 'wound' | 'iv' | 'catheter' | 'nutrition' | 'assessment';
    status: WardRoundStatus;
    dueBy: string;
}

// ─── Shift Task Rosters ───────────────────────────────────────────────────────

const INITIAL_MED_TASKS: MedTask[] = [];

const INITIAL_ROUND_TASKS: RoundTask[] = [];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function priorityColor(p: Priority) {
    if (p === 'stat') return 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-700';
    if (p === 'urgent') return 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-700';
    return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
}

function categoryIcon(cat: RoundTask['category']) {
    const classes = 'w-4 h-4';
    switch (cat) {
        case 'positioning': return <svg className={classes} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>;
        case 'wound': return <svg className={classes} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>;
        case 'iv': return <svg className={classes} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>;
        default: return <svg className={classes} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>;
    }
}

// ─── Confirm Modal ────────────────────────────────────────────────────────────

function ActionModal({ task, onClose, onAction }: { task: MedTask; onClose: () => void; onAction: (id: string, status: TaskStatus, notes?: string) => void }) {
    const [action, setAction] = useState<TaskStatus>('administered');
    const [notes, setNotes] = useState('');

    return (
        <Modal isOpen onClose={onClose} title={`Update Medication Task`}>
            <div className="space-y-4">
                <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-3">
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{task.medication} — {task.dose} {task.route}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{task.patientName} · Bed {task.bedNumber} · Due {task.dueTime}</p>
                    {task.notes && <p className="text-xs text-amber-600 dark:text-amber-400 mt-1 font-medium">⚠ {task.notes}</p>}
                </div>
                <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-2">Action</label>
                    <div className="flex flex-col gap-2">
                        {[
                            { value: 'administered', label: '✅ Administered', color: 'emerald' },
                            { value: 'delayed', label: '⏳ Delayed / Rescheduled', color: 'amber' },
                            { value: 'refused', label: '❌ Refused by Patient', color: 'rose' },
                        ].map(opt => (
                            <label key={opt.value} className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${action === opt.value ? `border-${opt.color}-400 bg-${opt.color}-50 dark:bg-${opt.color}-900/20` : 'border-slate-200 dark:border-slate-700'}`}>
                                <input type="radio" name="action" value={opt.value} checked={action === opt.value} onChange={() => setAction(opt.value as TaskStatus)} className="accent-blue-600" />
                                <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{opt.label}</span>
                            </label>
                        ))}
                    </div>
                </div>
                <div>
                    <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5">Notes (optional)</label>
                    <textarea rows={2} value={notes} onChange={e => setNotes(e.target.value)} placeholder="e.g. Patient was fasting, delayed to 14:30..." className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm dark:bg-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
                </div>
                <div className="flex gap-2 justify-end">
                    <Button variant="ghost" onClick={onClose}>Cancel</Button>
                    <Button id="task-confirm-btn" onClick={() => { onAction(task.id, action, notes); onClose(); }}>Confirm</Button>
                </div>
            </div>
        </Modal>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function NurseTasksPage() {
    const [medTasks, setMedTasks] = useState<MedTask[]>(INITIAL_MED_TASKS);
    const [roundTasks, setRoundTasks] = useState<RoundTask[]>(INITIAL_ROUND_TASKS);
    const [activeTaskModal, setActiveTaskModal] = useState<MedTask | null>(null);
    const [activeTab, setActiveTab] = useState<'meds' | 'rounds'>('meds');

    const pendingMeds = medTasks.filter(t => t.status === 'pending');
    const overdueMeds = pendingMeds.filter(t => t.overdue);
    const completedMeds = medTasks.filter(t => t.status === 'administered');
    const pendingRounds = roundTasks.filter(t => t.status === 'pending');
    const completedRounds = roundTasks.filter(t => t.status === 'done');

    const handleMedAction = (id: string, status: TaskStatus, notes?: string) => {
        setMedTasks(prev => prev.map(t => t.id === id ? { ...t, status, notes: notes || t.notes } : t));
    };

    const toggleRound = (id: string) => {
        setRoundTasks(prev => prev.map(t => t.id === id ? { ...t, status: t.status === 'done' ? 'pending' : 'done' } : t));
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Medication Tasks & Ward Rounds</h1>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Shift task board — track administered medications and ward round checklists</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                    { label: 'Overdue Meds', value: overdueMeds.length, color: 'rose', urgent: overdueMeds.length > 0 },
                    { label: 'Meds Pending', value: pendingMeds.length, color: 'amber', urgent: false },
                    { label: 'Meds Done', value: completedMeds.length, color: 'green', urgent: false },
                    { label: 'Round Tasks Pending', value: pendingRounds.length, color: 'blue', urgent: false },
                ].map(({ label, value, color, urgent }) => (
                    <div key={label} className={`bg-${color}-50 dark:bg-${color}-900/20 border border-${color}-100 dark:border-${color}-800/40 rounded-xl p-4 ${urgent ? 'animate-pulse' : ''}`}>
                        <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
                        <p className={`text-xs font-medium text-${color}-700 dark:text-${color}-300 mt-0.5`}>{label}</p>
                    </div>
                ))}
            </div>

            {/* Overdue alert */}
            {overdueMeds.length > 0 && (
                <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl p-3 flex items-center gap-2">
                    <svg className="w-5 h-5 text-rose-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">
                        {overdueMeds.length} medication task{overdueMeds.length > 1 ? 's are' : ' is'} overdue — action required immediately.
                    </p>
                </div>
            )}

            {/* Tabs */}
            <div className="border-b border-slate-200 dark:border-slate-700">
                <div className="flex">
                    {[
                        { id: 'meds', label: `Medication Administration (${pendingMeds.length} pending)` },
                        { id: 'rounds', label: `Ward Round Checklist (${pendingRounds.length} pending)` },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            id={`task-tab-${tab.id}`}
                            type="button"
                            onClick={() => setActiveTab(tab.id as 'meds' | 'rounds')}
                            className={`px-4 py-3 text-xs font-semibold border-b-2 transition-colors ${
                                activeTab === tab.id
                                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Medication Tasks */}
            {activeTab === 'meds' && (
                <div className="space-y-3">
                    {medTasks.length === 0 ? (
                        <div className="p-12 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl bg-white/50 dark:bg-slate-900/20">
                            <div className="w-12 h-12 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-3 text-2xl">
                                💊
                            </div>
                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">No Medication Administration Tasks Pending</p>
                            <p className="text-xs text-slate-500 mt-1">There are no scheduled medication doses due for active inpatients during this shift.</p>
                        </div>
                    ) : (
                        medTasks
                            .sort((a, b) => {
                                const order: Record<Priority, number> = { stat: 0, urgent: 1, routine: 2 };
                                if (a.overdue && !b.overdue) return -1;
                                if (!a.overdue && b.overdue) return 1;
                                return order[a.priority] - order[b.priority];
                            })
                            .map(task => (
                                <div
                                    key={task.id}
                                    className={`rounded-xl border p-4 transition-all ${
                                        task.status !== 'pending'
                                            ? 'opacity-50 border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20'
                                            : task.overdue
                                            ? 'border-rose-200 dark:border-rose-800 bg-rose-50/30 dark:bg-rose-900/10'
                                            : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/40'
                                    }`}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0 flex-1">
                                            <div className="flex items-center gap-2 flex-wrap mb-1">
                                                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${priorityColor(task.priority)}`}>
                                                    {task.priority === 'stat' ? '⚡ STAT' : task.priority}
                                                </span>
                                                {task.overdue && task.status === 'pending' && (
                                                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-700 animate-pulse">
                                                        OVERDUE
                                                    </span>
                                                )}
                                                {task.status !== 'pending' && (
                                                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                                                        task.status === 'administered' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                                                    }`}>
                                                        {task.status}
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{task.medication} — {task.dose} {task.route}</p>
                                            <p className="text-xs text-slate-500 mt-0.5">
                                                {task.patientName} · Bed {task.bedNumber} · Due: <span className={task.overdue && task.status === 'pending' ? 'text-rose-600 font-semibold' : ''}>{task.dueTime}</span>
                                            </p>
                                            <p className="text-xs text-slate-400 mt-0.5">Prescribed by {task.prescribedBy}</p>
                                            {task.notes && <p className="text-xs text-amber-600 dark:text-amber-400 mt-1 font-medium">⚠ {task.notes}</p>}
                                        </div>
                                        {task.status === 'pending' && (
                                            <button
                                                id={`med-action-${task.id}`}
                                                type="button"
                                                onClick={() => setActiveTaskModal(task)}
                                                className="shrink-0 px-3 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors"
                                            >
                                                Action
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))
                    )}
                </div>
            )}

            {/* Ward Round Tasks */}
            {activeTab === 'rounds' && (
                <div className="space-y-3">
                    {roundTasks.length === 0 ? (
                        <div className="p-12 text-center border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl bg-white/50 dark:bg-slate-900/20">
                            <div className="w-12 h-12 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-3 text-2xl">
                                📋
                            </div>
                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">No Ward Round Checklists Pending</p>
                            <p className="text-xs text-slate-500 mt-1">Routine turn, IV check, and dressing rounds will be populated upon patient admission.</p>
                        </div>
                    ) : (
                        <>
                            <p className="text-xs text-slate-400 italic">Tap the checkbox to mark round tasks complete.</p>
                            {roundTasks.map(task => (
                                <div
                                    key={task.id}
                                    className={`rounded-xl border p-4 flex items-start gap-3 transition-all ${
                                        task.status === 'done'
                                            ? 'opacity-50 border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20'
                                            : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/40'
                                    }`}
                                >
                                    <button
                                        id={`round-toggle-${task.id}`}
                                        type="button"
                                        onClick={() => toggleRound(task.id)}
                                        className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                                            task.status === 'done'
                                                ? 'bg-emerald-500 border-emerald-500'
                                                : 'border-slate-300 dark:border-slate-600 hover:border-blue-500'
                                        }`}
                                    >
                                        {task.status === 'done' && (
                                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                            </svg>
                                        )}
                                    </button>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <div className="w-5 h-5 text-slate-400 dark:text-slate-500 shrink-0">
                                                {categoryIcon(task.category)}
                                            </div>
                                            <span className="text-[10px] font-semibold uppercase text-slate-400 tracking-wider">{task.category}</span>
                                        </div>
                                        <p className={`text-sm font-medium ${task.status === 'done' ? 'line-through text-slate-400' : 'text-slate-900 dark:text-slate-100'}`}>
                                            {task.task}
                                        </p>
                                        <p className="text-xs text-slate-500 mt-0.5">{task.patientName} · Bed {task.bedNumber} · Due by {task.dueBy}</p>
                                    </div>
                                </div>
                            ))}
                            {roundTasks.length > 0 && roundTasks.every(t => t.status === 'done') && (
                                <div className="text-center py-8">
                                    <div className="w-14 h-14 rounded-2xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-3">
                                        <svg className="w-7 h-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    </div>
                                    <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">All ward round tasks complete!</p>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* Action modal */}
            {activeTaskModal && (
                <ActionModal task={activeTaskModal} onClose={() => setActiveTaskModal(null)} onAction={handleMedAction} />
            )}
        </div>
    );
}
