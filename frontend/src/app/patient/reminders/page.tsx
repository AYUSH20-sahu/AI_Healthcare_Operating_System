'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { patientRemindersApi, MedicineReminderItem } from '@/lib/api';
import { Card, CardContent, Button, Badge } from '@/components/ui';

const TIME_PRESETS = [
    { label: 'Morning (08:00)', value: '08:00', icon: '🌅' },
    { label: 'Noon (13:00)', value: '13:00', icon: '☀️' },
    { label: 'Evening (18:00)', value: '18:00', icon: '🌆' },
    { label: 'Night (21:00)', value: '21:00', icon: '🌙' },
];

export default function PatientMedicineRemindersPage() {
    const [reminders, setReminders] = useState<MedicineReminderItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [filterActiveOnly, setFilterActiveOnly] = useState<boolean | undefined>(undefined);

    // Form states
    const [medicationName, setMedicationName] = useState('');
    const [dosage, setDosage] = useState('');
    const [frequency, setFrequency] = useState('Once daily');
    const [selectedTimes, setSelectedTimes] = useState<string[]>(['08:00']);
    const [customTime, setCustomTime] = useState('');
    const [instructions, setInstructions] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [formError, setFormError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Action states
    const [togglingId, setTogglingId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    useEffect(() => {
        loadReminders();
    }, [filterActiveOnly]);

    const loadReminders = async () => {
        setIsLoading(true);
        try {
            const data = await patientRemindersApi.list(filterActiveOnly);
            setReminders(data.reminders);
        } catch (err) {
            console.error('Failed to load reminders:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleToggleTimePreset = (timeStr: string) => {
        if (selectedTimes.includes(timeStr)) {
            setSelectedTimes(selectedTimes.filter((t) => t !== timeStr));
        } else {
            setSelectedTimes([...selectedTimes, timeStr].sort());
        }
    };

    const handleAddCustomTime = () => {
        if (!customTime) return;
        if (!selectedTimes.includes(customTime)) {
            setSelectedTimes([...selectedTimes, customTime].sort());
        }
        setCustomTime('');
    };

    const handleCreateReminder = async (e: React.FormEvent) => {
        e.preventDefault();
        setFormError(null);

        if (!medicationName.trim()) {
            setFormError('Medication name is required.');
            return;
        }
        if (!dosage.trim()) {
            setFormError('Dosage is required (e.g. 500mg, 1 tablet).');
            return;
        }
        if (selectedTimes.length === 0) {
            setFormError('Please select at least one daily reminder time.');
            return;
        }

        setIsSubmitting(true);
        try {
            await patientRemindersApi.create({
                medication_name: medicationName.trim(),
                dosage: dosage.trim(),
                frequency,
                times_of_day: selectedTimes,
                instructions: instructions.trim() || undefined,
                start_date: startDate || undefined,
                end_date: endDate || undefined,
                is_active: true,
            });

            // Reset form
            setMedicationName('');
            setDosage('');
            setFrequency('Once daily');
            setSelectedTimes(['08:00']);
            setInstructions('');
            setStartDate('');
            setEndDate('');
            setShowCreateModal(false);

            await loadReminders();
        } catch (err: any) {
            setFormError(err.message || 'Failed to schedule reminder.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleToggleActive = async (reminder: MedicineReminderItem) => {
        setTogglingId(reminder.reminder_id);
        try {
            const updated = await patientRemindersApi.toggleActive(reminder.reminder_id, !reminder.is_active);
            setReminders((prev) =>
                prev.map((r) => (r.reminder_id === reminder.reminder_id ? updated : r))
            );
        } catch (err: any) {
            alert(err.message || 'Failed to toggle status.');
        } finally {
            setTogglingId(null);
        }
    };

    const handleDelete = async (reminderId: string) => {
        if (!confirm('Are you sure you want to remove this medication reminder schedule?')) {
            return;
        }
        setDeletingId(reminderId);
        try {
            await patientRemindersApi.delete(reminderId);
            setReminders((prev) => prev.filter((r) => r.reminder_id !== reminderId));
        } catch (err: any) {
            alert(err.message || 'Failed to delete reminder.');
        } finally {
            setDeletingId(null);
        }
    };

    const activeCount = reminders.filter((r) => r.is_active).length;

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                        <span>⏰ Medicine Reminders & Dosage Schedule</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Track prescribed medications, schedule daily dosage times, and maintain clinical adherence.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <Button
                        variant="primary"
                        onClick={() => setShowCreateModal(true)}
                        className="text-xs font-semibold px-4 py-2 flex items-center gap-1.5"
                    >
                        <span>+ Add Medication Reminder</span>
                    </Button>
                </div>
            </div>

            {/* Strict Rule Disclosure Banner */}
            <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-gradient-to-r from-amber-50 to-orange-50/50 dark:from-amber-950/20 dark:to-orange-950/10 flex items-start gap-3">
                <span className="text-xl shrink-0">ℹ️</span>
                <div className="text-xs space-y-1 text-amber-900 dark:text-amber-200">
                    <p className="font-bold">
                        Medication Reminder Scheduling Engine:
                    </p>
                    <p className="text-amber-800/90 dark:text-amber-300/80 leading-relaxed">
                        Schedules configured here are actively recorded and simulated by the AI-HOS clinical scheduler engine. External SMS/Push notification delivery channels are currently in scheduled rollout. Daily dosage times are displayed below for patient adherence tracking.
                    </p>
                </div>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                Active Regimens
                            </p>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">
                                {activeCount}
                            </h3>
                        </div>
                        <div className="w-10 h-10 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
                            💊
                        </div>
                    </CardContent>
                </Card>

                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                Total Schedules
                            </p>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">
                                {reminders.length}
                            </h3>
                        </div>
                        <div className="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">
                            📋
                        </div>
                    </CardContent>
                </Card>

                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                                Related Prescriptions
                            </p>
                            <Link
                                href="/patient/prescriptions"
                                className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline mt-1 inline-block"
                            >
                                View Doctor Prescriptions →
                            </Link>
                        </div>
                        <div className="w-10 h-10 rounded-full bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold">
                            🩺
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Filter Toggle */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setFilterActiveOnly(undefined)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                            filterActiveOnly === undefined
                                ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                        }`}
                    >
                        All ({reminders.length})
                    </button>
                    <button
                        onClick={() => setFilterActiveOnly(true)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                            filterActiveOnly === true
                                ? 'bg-emerald-600 text-white'
                                : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                        }`}
                    >
                        Active Only ({activeCount})
                    </button>
                </div>

                <span className="text-xs text-slate-500 dark:text-slate-400">
                    Showing {reminders.length} reminder {reminders.length === 1 ? 'entry' : 'entries'}
                </span>
            </div>

            {/* Reminder Cards Grid */}
            {isLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="p-5 animate-pulse border border-slate-200 dark:border-slate-800">
                            <div className="h-5 w-1/2 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                            <div className="h-4 w-1/3 bg-slate-200 dark:bg-slate-700 rounded mb-4" />
                            <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded" />
                        </Card>
                    ))}
                </div>
            ) : reminders.length === 0 ? (
                <Card className="border border-dashed border-slate-300 dark:border-slate-800 p-12 text-center bg-white dark:bg-slate-900">
                    <div className="w-12 h-12 mx-auto rounded-full bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center text-xl mb-3">
                        ⏰
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                        No medication reminders configured
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                        Add your active medicines to schedule daily reminder alerts and ensure on-time doses.
                    </p>
                    <div className="mt-4">
                        <Button
                            variant="primary"
                            onClick={() => setShowCreateModal(true)}
                            className="text-xs font-semibold px-4 py-2"
                        >
                            + Add Your First Reminder
                        </Button>
                    </div>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {reminders.map((rem) => (
                        <Card
                            key={rem.reminder_id}
                            className={`border transition-all bg-white dark:bg-slate-900 flex flex-col justify-between ${
                                rem.is_active
                                    ? 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm'
                                    : 'border-slate-200 dark:border-slate-800 opacity-60 bg-slate-50/50 dark:bg-slate-900/50'
                            }`}
                        >
                            <CardContent className="p-5 space-y-4">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="min-w-0">
                                        <h4 className="text-base font-bold text-slate-900 dark:text-white truncate">
                                            {rem.medication_name}
                                        </h4>
                                        <div className="flex items-center gap-2 mt-0.5">
                                            <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
                                                {rem.dosage}
                                            </span>
                                            <span className="text-slate-300 dark:text-slate-700">•</span>
                                            <span className="text-xs text-slate-500 dark:text-slate-400">
                                                {rem.frequency}
                                            </span>
                                        </div>
                                    </div>

                                    <Badge
                                        variant={rem.is_active ? 'success' : 'neutral'}
                                        className="text-[10px] uppercase font-bold tracking-wider shrink-0"
                                    >
                                        {rem.is_active ? 'Active' : 'Paused'}
                                    </Badge>
                                </div>

                                {/* Scheduled Times Chips */}
                                <div>
                                    <p className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                                        Daily Doses
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {rem.times_of_day && rem.times_of_day.length > 0 ? (
                                            rem.times_of_day.map((t, idx) => (
                                                <span
                                                    key={idx}
                                                    className="px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900 flex items-center gap-1"
                                                >
                                                    <span>🔔</span>
                                                    <span>{t}</span>
                                                </span>
                                            ))
                                        ) : (
                                            <span className="text-xs text-slate-400">No times set</span>
                                        )}
                                    </div>
                                </div>

                                {rem.instructions && (
                                    <div className="text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/60 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800">
                                        <span className="font-semibold text-slate-700 dark:text-slate-200">Instructions: </span>
                                        {rem.instructions}
                                    </div>
                                )}

                                {(rem.start_date || rem.end_date) && (
                                    <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100 dark:border-slate-800">
                                        <span>Course:</span>
                                        <span>
                                            {rem.start_date || 'Ongoing'} → {rem.end_date || 'Indefinite'}
                                        </span>
                                    </div>
                                )}

                                {/* Action Buttons */}
                                <div className="pt-2 flex items-center gap-2 border-t border-slate-100 dark:border-slate-800">
                                    <Button
                                        variant={rem.is_active ? 'secondary' : 'primary'}
                                        size="sm"
                                        disabled={togglingId === rem.reminder_id}
                                        onClick={() => handleToggleActive(rem)}
                                        className="flex-1 text-xs font-semibold flex items-center justify-center gap-1.5"
                                    >
                                        {togglingId === rem.reminder_id ? (
                                            <span className="w-3 h-3 border-2 border-slate-500 border-t-transparent rounded-full animate-spin" />
                                        ) : rem.is_active ? (
                                            <>
                                                <span>⏸</span>
                                                <span>Pause Schedule</span>
                                            </>
                                        ) : (
                                            <>
                                                <span>▶</span>
                                                <span>Resume Schedule</span>
                                            </>
                                        )}
                                    </Button>

                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        disabled={deletingId === rem.reminder_id}
                                        onClick={() => handleDelete(rem.reminder_id)}
                                        className="text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 px-2.5"
                                        title="Delete reminder"
                                    >
                                        {deletingId === rem.reminder_id ? (
                                            <span className="w-3 h-3 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                                        ) : (
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        )}
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            {/* Create Reminder Modal */}
            {showCreateModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <span>💊 Schedule Medication Reminder</span>
                            </h3>
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg leading-none"
                            >
                                ✕
                            </button>
                        </div>

                        <form onSubmit={handleCreateReminder} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
                            {/* Medication Name */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                    Medication Name *
                                </label>
                                <input
                                    type="text"
                                    value={medicationName}
                                    onChange={(e) => setMedicationName(e.target.value)}
                                    placeholder="e.g. Metformin Hydrochloride"
                                    className="w-full text-sm px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    required
                                />
                            </div>

                            {/* Dosage & Frequency */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                        Dosage *
                                    </label>
                                    <input
                                        type="text"
                                        value={dosage}
                                        onChange={(e) => setDosage(e.target.value)}
                                        placeholder="e.g. 500 mg, 1 tablet"
                                        className="w-full text-sm px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                        Frequency *
                                    </label>
                                    <select
                                        value={frequency}
                                        onChange={(e) => setFrequency(e.target.value)}
                                        className="w-full text-sm px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    >
                                        <option value="Once daily">Once daily</option>
                                        <option value="Twice daily">Twice daily</option>
                                        <option value="Three times daily">Three times daily</option>
                                        <option value="Four times daily">Four times daily</option>
                                        <option value="Every alternate day">Every alternate day</option>
                                        <option value="As needed (PRN)">As needed (PRN)</option>
                                    </select>
                                </div>
                            </div>

                            {/* Times of Day */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                    Reminder Times (Select one or more) *
                                </label>
                                <div className="grid grid-cols-2 gap-2 mb-2">
                                    {TIME_PRESETS.map((p) => {
                                        const isSelected = selectedTimes.includes(p.value);
                                        return (
                                            <button
                                                type="button"
                                                key={p.value}
                                                onClick={() => handleToggleTimePreset(p.value)}
                                                className={`p-2 rounded-lg text-xs font-medium border flex items-center justify-between transition-all ${
                                                    isSelected
                                                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300'
                                                        : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50'
                                                }`}
                                            >
                                                <span>{p.icon} {p.label}</span>
                                                <span>{isSelected ? '✓' : '+'}</span>
                                            </button>
                                        );
                                    })}
                                </div>

                                {/* Custom time input */}
                                <div className="flex gap-2">
                                    <input
                                        type="time"
                                        value={customTime}
                                        onChange={(e) => setCustomTime(e.target.value)}
                                        className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                                    />
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        size="sm"
                                        onClick={handleAddCustomTime}
                                        className="text-xs"
                                    >
                                        + Add Time
                                    </Button>
                                </div>

                                <div className="flex flex-wrap gap-1 mt-2">
                                    {selectedTimes.map((t) => (
                                        <span
                                            key={t}
                                            className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 text-xs font-mono flex items-center gap-1"
                                        >
                                            <span>{t}</span>
                                            <button
                                                type="button"
                                                onClick={() => handleToggleTimePreset(t)}
                                                className="text-blue-500 hover:text-blue-700 font-bold"
                                            >
                                                ×
                                            </button>
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Instructions */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                    Intake Instructions (Optional)
                                </label>
                                <textarea
                                    value={instructions}
                                    onChange={(e) => setInstructions(e.target.value)}
                                    rows={2}
                                    placeholder="e.g. Take immediately after food. Avoid consuming alcohol."
                                    className="w-full text-sm px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                />
                            </div>

                            {/* Start and End Dates */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                        Start Date
                                    </label>
                                    <input
                                        type="date"
                                        value={startDate}
                                        onChange={(e) => setStartDate(e.target.value)}
                                        className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                        End Date (Optional)
                                    </label>
                                    <input
                                        type="date"
                                        value={endDate}
                                        onChange={(e) => setEndDate(e.target.value)}
                                        className="w-full text-sm px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    />
                                </div>
                            </div>

                            {formError && (
                                <div className="p-3 text-xs rounded-lg bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                                    ⚠️ {formError}
                                </div>
                            )}

                            <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    onClick={() => setShowCreateModal(false)}
                                    className="text-xs"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    variant="primary"
                                    disabled={isSubmitting}
                                    className="text-xs font-semibold px-4 py-2"
                                >
                                    {isSubmitting ? 'Scheduling...' : 'Save Reminder Schedule'}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
