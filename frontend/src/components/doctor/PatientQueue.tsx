'use client';

import React, { useState, useMemo } from 'react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export type TriagePriority = 'urgent' | 'priority' | 'routine' | 'followup';

export interface QueuePatientItem {
    appointment_id: string;
    patient_id: string;
    full_name: string;
    age: number;
    gender: string;
    blood_group: string;
    abha_address?: string;
    phone?: string;
    scheduled_at: string;
    duration_minutes: number;
    status: 'waiting' | 'in_progress' | 'scheduled' | 'completed' | 'no_show';
    triage_priority: TriagePriority;
    chief_complaint: string;
    vitals: {
        bp: string;
        hr: number;
        spo2: number;
        temp: number;
        glucose?: number;
    };
    allergies: {
        substance: string;
        severity: 'critical' | 'moderate' | 'mild';
        reaction: string;
    }[];
    risk_flags: string[];
}

interface PatientQueueProps {
    appointments: QueuePatientItem[];
    activePatientId?: string;
    onSelectPatient: (patient: QueuePatientItem) => void;
    onStartConsultation?: (patient: QueuePatientItem) => void;
    onRefresh?: () => void;
}

export function PatientQueue({
    appointments,
    activePatientId,
    onSelectPatient,
    onStartConsultation,
    onRefresh,
}: PatientQueueProps) {
    const [filterStatus, setFilterStatus] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState<string>('');

    // Filter appointments
    const filteredAppointments = useMemo(() => {
        return appointments.filter((item) => {
            const matchesStatus = filterStatus === 'all' || item.status === filterStatus;
            const q = searchQuery.toLowerCase().trim();
            const matchesSearch =
                !q ||
                item.full_name.toLowerCase().includes(q) ||
                (item.abha_address && item.abha_address.toLowerCase().includes(q)) ||
                item.chief_complaint.toLowerCase().includes(q);
            return matchesStatus && matchesSearch;
        });
    }, [appointments, filterStatus, searchQuery]);

    // Counts for tabs
    const counts = useMemo(() => {
        return {
            all: appointments.length,
            waiting: appointments.filter(a => a.status === 'waiting').length,
            in_progress: appointments.filter(a => a.status === 'in_progress').length,
            scheduled: appointments.filter(a => a.status === 'scheduled').length,
            completed: appointments.filter(a => a.status === 'completed').length,
        };
    }, [appointments]);

    const renderTriageBadge = (priority: TriagePriority) => {
        switch (priority) {
            case 'urgent':
                return (
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-md bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-900/60 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-600 animate-ping" />
                        Urgent
                    </span>
                );
            case 'priority':
                return (
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-md bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-900/60">
                        Priority
                    </span>
                );
            case 'routine':
                return (
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-md bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-900/60">
                        Routine
                    </span>
                );
            case 'followup':
                return (
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-md bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-900/60">
                        Follow-Up
                    </span>
                );
        }
    };

    const formatTime = (dateStr: string) => {
        try {
            return new Date(dateStr).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 shadow-sm overflow-hidden backdrop-blur-md">
            {/* Header with Search & Controls */}
            <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3.5">
                <div>
                    <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-slate-900 dark:text-white">
                            Today&apos;s Clinical Queue
                        </h3>
                        <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 dark:bg-blue-950/70 text-blue-700 dark:text-blue-300">
                            {appointments.length} Total
                        </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Triage priority, wait times, and direct consultation handoffs.
                    </p>
                </div>

                <div className="flex items-center gap-2.5 w-full md:w-auto">
                        <Input
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search patient, ABHA, symptom..."
                            className="py-1.5 text-xs"
                            leadingIcon={
                                <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            }
                        />
                    {onRefresh && (
                        <Button size="sm" variant="outline" onClick={onRefresh} title="Refresh Queue">
                            🔄
                        </Button>
                    )}
                </div>
            </div>

            {/* Filter Tabs */}
            <div className="px-4 sm:px-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 flex items-center gap-1.5 overflow-x-auto py-2 text-xs">
                {[
                    { key: 'all', label: 'All Patients', count: counts.all },
                    { key: 'waiting', label: 'Waiting in Triage', count: counts.waiting },
                    { key: 'in_progress', label: 'In Consultation', count: counts.in_progress },
                    { key: 'scheduled', label: 'Scheduled', count: counts.scheduled },
                    { key: 'completed', label: 'Completed', count: counts.completed },
                ].map((tab) => (
                    <button
                        key={tab.key}
                        type="button"
                        onClick={() => setFilterStatus(tab.key)}
                        className={`px-3 py-1.5 rounded-xl font-medium transition-all whitespace-nowrap flex items-center gap-1.5 ${
                            filterStatus === tab.key
                                ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200 dark:border-slate-700'
                                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                        }`}
                    >
                        <span>{tab.label}</span>
                        <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                            filterStatus === tab.key
                                ? 'bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300'
                                : 'bg-slate-200/80 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                        }`}>
                            {tab.count}
                        </span>
                    </button>
                ))}
            </div>

            {/* Appointment Queue List */}
            <div className="divide-y divide-slate-200 dark:divide-slate-800/80">
                {filteredAppointments.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 dark:text-slate-400 text-xs">
                        <span className="text-2xl block mb-1">📋</span>
                        No patients matching &ldquo;{filterStatus}&rdquo; queue.
                    </div>
                ) : (
                    filteredAppointments.map((appt) => {
                        const isSelected = activePatientId === appt.patient_id;
                        return (
                            <div
                                key={appt.appointment_id}
                                onClick={() => onSelectPatient(appt)}
                                className={`p-4 sm:p-4.5 hover:bg-slate-50/80 dark:hover:bg-slate-800/40 cursor-pointer transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 ${
                                    isSelected
                                        ? 'bg-blue-50/50 dark:bg-blue-950/20 border-l-4 border-blue-600 dark:border-blue-500'
                                        : ''
                                }`}
                            >
                                {/* Patient Demographic & Chief Complaint */}
                                <div className="flex items-start gap-3.5">
                                    <div className="relative mt-0.5">
                                        <div className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-sm shadow-sm ${
                                            isSelected
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200'
                                        }`}>
                                            {appt.full_name.charAt(0).toUpperCase()}
                                        </div>
                                    </div>

                                    <div>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="font-bold text-slate-900 dark:text-white text-sm">
                                                {appt.full_name}
                                            </span>
                                            <span className="text-xs text-slate-500 dark:text-slate-400">
                                                {appt.age}y • {appt.gender}
                                            </span>
                                            {renderTriageBadge(appt.triage_priority)}
                                            <StatusBadge status={appt.status} />
                                        </div>

                                        <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 font-medium">
                                            Chief Complaint: &ldquo;{appt.chief_complaint}&rdquo;
                                        </p>

                                        {/* Meta & Allergy pills */}
                                        <div className="flex flex-wrap items-center gap-2 mt-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                                            <span className="flex items-center gap-1 font-mono">
                                                ⏰ {formatTime(appt.scheduled_at)} ({appt.duration_minutes}m)
                                            </span>
                                            {appt.allergies.length > 0 && (
                                                <span className="px-1.5 py-0.2 rounded bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 font-medium">
                                                    ⚠️ {appt.allergies.map(a => a.substance).join(', ')}
                                                </span>
                                            )}
                                            {appt.risk_flags.length > 0 && (
                                                <span className="px-1.5 py-0.2 rounded bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-medium">
                                                    🛡️ {appt.risk_flags[0]}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Row Actions */}
                                <div className="flex items-center gap-2 sm:self-center self-end" onClick={(e) => e.stopPropagation()}>
                                    {appt.status !== 'completed' && (
                                        <Button
                                            size="sm"
                                            variant={isSelected ? 'primary' : 'outline'}
                                            onClick={() => {
                                                onSelectPatient(appt);
                                                if (onStartConsultation) onStartConsultation(appt);
                                            }}
                                        >
                                            {appt.status === 'in_progress' ? 'Resume Visit' : 'Start Visit'}
                                        </Button>
                                    )}
                                    {appt.status === 'completed' && (
                                        <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                                            ✓ Completed
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
