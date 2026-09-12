'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    telehealthApi,
    DoctorScheduleResponse,
    DoctorScheduleItem,
} from '@/lib/api';

export default function DoctorConsultationsSchedulePage() {
    const [scheduleData, setScheduleData] = useState<DoctorScheduleResponse | null>(null);
    const [selectedDate, setSelectedDate] = useState<string>(
        new Date().toISOString().split('T')[0]
    );
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadSchedule(selectedDate);
    }, [selectedDate]);

    const loadSchedule = async (dateStr: string) => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await telehealthApi.getDoctorSchedule(dateStr);
            setScheduleData(data);
        } catch (err: any) {
            console.error('Failed to load doctor schedule:', err);
            setError(err?.message || 'Failed to load schedule for this date.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDateChange = (offsetDays: number) => {
        const curr = new Date(selectedDate);
        curr.setDate(curr.getDate() + offsetDays);
        setSelectedDate(curr.toISOString().split('T')[0]);
    };

    const isToday = selectedDate === new Date().toISOString().split('T')[0];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200 dark:border-blue-800/60">
                            Milestone U-14
                        </span>
                        <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300">
                            Telehealth Workstation
                        </span>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                        Doctor Schedule & Clinical Consultations
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Daily patient appointments, intake symptoms review, and integrated telehealth video rooms.
                    </p>
                </div>

                {/* Date Navigator */}
                <div className="flex items-center gap-2 bg-white dark:bg-slate-900 p-1.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
                    <button
                        onClick={() => handleDateChange(-1)}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                        title="Previous Day"
                    >
                        ◀
                    </button>
                    <input
                        type="date"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        className="text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200 bg-transparent px-2 py-1 focus:outline-none"
                    />
                    <button
                        onClick={() => handleDateChange(1)}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                        title="Next Day"
                    >
                        ▶
                    </button>
                    {!isToday && (
                        <button
                            onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
                            className="text-xs px-2.5 py-1 rounded-md bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-medium hover:bg-blue-100 transition"
                        >
                            Today
                        </button>
                    )}
                </div>
            </div>

            {/* Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                        Total Appointments
                    </span>
                    <span className="text-2xl font-bold text-slate-900 dark:text-white mt-1 block">
                        {isLoading ? '...' : scheduleData?.total_appointments ?? 0}
                    </span>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <span className="text-xs font-semibold text-amber-500 uppercase tracking-wider block">
                        Scheduled
                    </span>
                    <span className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1 block">
                        {isLoading ? '...' : scheduleData?.scheduled_count ?? 0}
                    </span>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <span className="text-xs font-semibold text-cyan-500 uppercase tracking-wider block">
                        In Consultation
                    </span>
                    <span className="text-2xl font-bold text-cyan-600 dark:text-cyan-400 mt-1 block">
                        {isLoading ? '...' : scheduleData?.in_consultation_count ?? 0}
                    </span>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
                    <span className="text-xs font-semibold text-emerald-500 uppercase tracking-wider block">
                        Completed
                    </span>
                    <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1 block">
                        {isLoading ? '...' : scheduleData?.completed_count ?? 0}
                    </span>
                </div>
            </div>

            {error && (
                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs sm:text-sm text-rose-700 dark:text-rose-300">
                    {error}
                </div>
            )}

            {/* Appointment Schedule List */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                        Consultation Schedule for {new Date(selectedDate + 'T00:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                    </h2>
                    <span className="text-xs text-slate-400">
                        {scheduleData?.appointments.length ?? 0} patient(s) queued
                    </span>
                </div>

                {isLoading ? (
                    <div className="p-12 text-center text-slate-400 text-sm bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 flex items-center justify-center gap-2">
                        <svg className="animate-spin w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Loading doctor schedule...
                    </div>
                ) : scheduleData?.appointments.length === 0 ? (
                    <div className="p-12 text-center text-slate-400 text-sm bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
                        No appointments scheduled for this date.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4">
                        {scheduleData?.appointments.map((appt: DoctorScheduleItem) => {
                            const isLive = appt.status === 'in_progress';
                            const isDone = appt.status === 'completed';
                            const hasRedFlags = appt.intake_summary?.has_red_flags;

                            return (
                                <div
                                    key={appt.appointment_id}
                                    className={`p-5 rounded-2xl border transition-all shadow-sm ${
                                        hasRedFlags
                                            ? 'border-rose-300 dark:border-rose-900/60 bg-rose-50/20 dark:bg-rose-950/10'
                                            : isLive
                                            ? 'border-cyan-400 dark:border-cyan-800 bg-cyan-50/30 dark:bg-cyan-950/10 ring-2 ring-cyan-500/20'
                                            : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                                    }`}
                                >
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                        {/* Left: Time & Patient Identity */}
                                        <div className="flex items-start gap-4">
                                            <div className="w-16 h-16 rounded-xl bg-slate-100 dark:bg-slate-800 flex flex-col items-center justify-center text-slate-700 dark:text-slate-200 flex-shrink-0">
                                                <span className="text-xs font-bold uppercase">
                                                    {new Date(appt.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                                <span className="text-[10px] text-slate-400">
                                                    {appt.duration_minutes}m
                                                </span>
                                            </div>

                                            <div className="space-y-1">
                                                <div className="flex items-center gap-2.5 flex-wrap">
                                                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                                                        {appt.patient_name}
                                                    </h3>
                                                    {appt.patient_age && (
                                                        <span className="text-xs text-slate-500 dark:text-slate-400">
                                                            • {appt.patient_age} yrs, {appt.patient_gender || 'Not specified'}
                                                        </span>
                                                    )}
                                                    {appt.patient_abha && (
                                                        <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-slate-600 dark:text-slate-300">
                                                            {appt.patient_abha}
                                                        </span>
                                                    )}
                                                    {hasRedFlags && (
                                                        <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-200 border border-rose-200 animate-pulse">
                                                            🚨 Red-Flag Detected
                                                        </span>
                                                    )}
                                                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-full uppercase tracking-wider ${
                                                        isDone
                                                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                                                            : isLive
                                                            ? 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300'
                                                            : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                                                    }`}>
                                                        {appt.status.replace('_', ' ')}
                                                    </span>
                                                </div>

                                                {/* Patient Intake Highlights from U-13 */}
                                                {appt.intake_summary ? (
                                                    <div className="text-xs text-slate-600 dark:text-slate-300 flex items-center gap-2 flex-wrap pt-0.5">
                                                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                                                            Intake Chief Complaint:
                                                        </span>
                                                        <span>{appt.intake_summary.chief_complaint || 'Reported symptoms'}</span>
                                                        {appt.intake_summary.severity && (
                                                            <span className={`px-1.5 py-0.2 rounded font-bold text-[11px] ${
                                                                appt.intake_summary.severity >= 7
                                                                    ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
                                                                    : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                                                            }`}>
                                                                Severity {appt.intake_summary.severity}/10
                                                            </span>
                                                        )}
                                                        {appt.intake_summary.duration && (
                                                            <span className="text-slate-400">
                                                                ({appt.intake_summary.duration})
                                                            </span>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <div className="text-xs text-slate-400 italic">
                                                        No pre-visit AI intake submitted yet.
                                                    </div>
                                                )}

                                                {hasRedFlags && appt.intake_summary?.red_flag_warnings && (
                                                    <div className="text-xs font-medium text-rose-700 dark:text-rose-300 flex items-center gap-1.5 pt-0.5">
                                                        <span>⚠️ Alerts:</span>
                                                        <span>{appt.intake_summary.red_flag_warnings.join(' • ')}</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Right: Actions */}
                                        <div className="flex items-center gap-2.5 flex-shrink-0">
                                            <Link
                                                href={`/doctor/consultations/${appt.appointment_id}`}
                                                className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition shadow-sm ${
                                                    isLive
                                                        ? 'bg-cyan-600 hover:bg-cyan-700 text-white animate-pulse'
                                                        : isDone
                                                        ? 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200'
                                                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                                                }`}
                                            >
                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                                </svg>
                                                {isLive ? 'Resume Telehealth Room' : isDone ? 'View Consultation Chart' : 'Enter Telehealth Room'}
                                            </Link>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
