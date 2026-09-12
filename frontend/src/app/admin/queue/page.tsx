'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { adminOperationsApi, QueueItem, QueueListResponse } from '@/lib/api';
import { Button, Card, CardContent, Badge } from '@/components/ui';

const STATUS_FILTERS = [
    { key: 'all', label: 'All Consultations' },
    { key: 'scheduled', label: 'Waiting / Scheduled' },
    { key: 'in_progress', label: 'In Consultation' },
    { key: 'completed', label: 'Completed' },
    { key: 'cancelled', label: 'Cancelled' },
];

export default function AdminQueuePage() {
    const [queueData, setQueueData] = useState<QueueListResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0]);
    const [statusFilter, setStatusFilter] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [updatingId, setUpdatingId] = useState<string | null>(null);
    const [actionMessage, setActionMessage] = useState<string | null>(null);

    useEffect(() => {
        loadQueue();
    }, [selectedDate, statusFilter]);

    const loadQueue = async () => {
        setIsLoading(true);
        try {
            const res = await adminOperationsApi.getQueue({
                date_str: selectedDate,
                status_filter: statusFilter,
                search: searchTerm.trim() || undefined,
            });
            setQueueData(res);
        } catch (err: any) {
            console.error('Failed to load clinic queue:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        loadQueue();
    };

    const handleUpdateStatus = async (appointmentId: string, newStatus: string) => {
        setUpdatingId(appointmentId);
        setActionMessage(null);
        try {
            await adminOperationsApi.updateQueueStatus(appointmentId, newStatus);
            setActionMessage(`Appointment status updated to '${newStatus}'.`);
            await loadQueue();
        } catch (err: any) {
            alert(err.message || 'Failed to update queue status');
        } finally {
            setUpdatingId(null);
        }
    };

    const formatTime = (isoString: string) => {
        const d = new Date(isoString);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const getStatusBadgeVariant = (st: string) => {
        switch (st.toLowerCase()) {
            case 'scheduled':
                return 'primary';
            case 'in_progress':
                return 'purple';
            case 'completed':
                return 'success';
            case 'cancelled':
                return 'danger';
            default:
                return 'neutral';
        }
    };

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <Link href="/admin" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs">
                            ← Admin Console
                        </Link>
                        <span className="text-slate-300 dark:text-slate-700">•</span>
                        <Badge variant="primary" className="text-[10px] uppercase font-bold">
                            Live Triage
                        </Badge>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-1 flex items-center gap-2">
                        <span>⏱️ Real-Time Clinic Patient Queue</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Track patient waiting times, manage consultation states, and oversee provider encounter flows.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <input
                        type="date"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                    />
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadQueue}
                        disabled={isLoading}
                        className="text-xs"
                    >
                        ↻ Refresh
                    </Button>
                </div>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Total in Queue
                            </span>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                                {queueData?.total_in_queue ?? 0}
                            </h3>
                        </div>
                        <span className="text-2xl">📋</span>
                    </CardContent>
                </Card>

                <Card className="border border-purple-200 dark:border-purple-900/50 bg-purple-50/20 dark:bg-purple-950/20 shadow-sm">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-purple-700 dark:text-purple-300">
                                In Active Consultation
                            </span>
                            <h3 className="text-2xl font-bold text-purple-900 dark:text-purple-100 mt-1">
                                {queueData?.active_consultations_count ?? 0}
                            </h3>
                        </div>
                        <span className="text-2xl">🩺</span>
                    </CardContent>
                </Card>

                <Card className="border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/20 dark:bg-emerald-950/20 shadow-sm">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                                Completed Today
                            </span>
                            <h3 className="text-2xl font-bold text-emerald-900 dark:text-emerald-100 mt-1">
                                {queueData?.completed_today_count ?? 0}
                            </h3>
                        </div>
                        <span className="text-2xl">✓</span>
                    </CardContent>
                </Card>
            </div>

            {/* Filter & Search Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                    {STATUS_FILTERS.map((f) => (
                        <button
                            key={f.key}
                            onClick={() => setStatusFilter(f.key)}
                            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
                                statusFilter === f.key
                                    ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
                                    : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50'
                            }`}
                        >
                            {f.label}
                        </button>
                    ))}
                </div>

                <form onSubmit={handleSearch} className="flex gap-2">
                    <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Search patient, ABHA..."
                        className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white w-48 sm:w-64"
                    />
                    <Button type="submit" variant="secondary" size="sm" className="text-xs">
                        Search
                    </Button>
                </form>
            </div>

            {actionMessage && (
                <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs flex items-center justify-between">
                    <span>✓ {actionMessage}</span>
                    <button onClick={() => setActionMessage(null)} className="font-bold">✕</button>
                </div>
            )}

            {/* Queue Table */}
            {isLoading ? (
                <div className="space-y-3">
                    {[1, 2, 3, 4].map((i) => (
                        <Card key={i} className="p-5 animate-pulse border border-slate-200 dark:border-slate-800">
                            <div className="h-4 w-1/4 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                            <div className="h-3 w-1/2 bg-slate-200 dark:bg-slate-700 rounded" />
                        </Card>
                    ))}
                </div>
            ) : !queueData || queueData.queue.length === 0 ? (
                <Card className="border border-dashed border-slate-300 dark:border-slate-800 p-12 text-center bg-white dark:bg-slate-900">
                    <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center text-xl mb-3">
                        ⏱️
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                        No appointments in queue
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        No consultations match the selected date and filter criteria.
                    </p>
                </Card>
            ) : (
                <div className="space-y-3">
                    {queueData.queue.map((item) => (
                        <Card
                            key={item.appointment_id}
                            className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm hover:border-slate-300 transition-all"
                        >
                            <CardContent className="p-4 sm:p-5">
                                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                                    {/* Left: Patient & Time Details */}
                                    <div className="flex items-start gap-3.5">
                                        <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-sm shrink-0">
                                            {formatTime(item.scheduled_at)}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                                                    {item.patient_name}
                                                </h4>
                                                <Badge
                                                    variant={getStatusBadgeVariant(item.status) as any}
                                                    className="text-[10px] uppercase font-bold tracking-wider"
                                                >
                                                    {item.status.replace('_', ' ')}
                                                </Badge>
                                                {item.wait_time_minutes > 0 && (
                                                    <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded-full border border-amber-200 dark:border-amber-800">
                                                        ⏳ Waiting {item.wait_time_minutes}m
                                                    </span>
                                                )}
                                            </div>

                                            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400 mt-1">
                                                <span>Doctor: <strong className="text-slate-700 dark:text-slate-200">{item.doctor_name}</strong> ({item.doctor_specialty})</span>
                                                <span>•</span>
                                                <span>Duration: {item.duration_minutes} mins</span>
                                                {item.patient_phone && (
                                                    <>
                                                        <span>•</span>
                                                        <span>Phone: {item.patient_phone}</span>
                                                    </>
                                                )}
                                            </div>

                                            {/* Reason or Intake Summary */}
                                            {(item.reason || item.intake_chief_complaint) && (
                                                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2 p-2 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                                                    <strong className="text-slate-700 dark:text-slate-200">Clinical Purpose: </strong>
                                                    {item.intake_chief_complaint || item.reason}
                                                </p>
                                            )}
                                        </div>
                                    </div>

                                    {/* Right: Quick Action Controls */}
                                    <div className="flex items-center gap-2 self-end lg:self-center shrink-0">
                                        {item.status === 'scheduled' && (
                                            <Button
                                                variant="primary"
                                                size="sm"
                                                disabled={updatingId === item.appointment_id}
                                                onClick={() => handleUpdateStatus(item.appointment_id, 'in_progress')}
                                                className="text-xs"
                                            >
                                                ▶ Start Consultation
                                            </Button>
                                        )}

                                        {item.status === 'in_progress' && (
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                disabled={updatingId === item.appointment_id}
                                                onClick={() => handleUpdateStatus(item.appointment_id, 'completed')}
                                                className="text-xs text-emerald-600 dark:text-emerald-400 border-emerald-300"
                                            >
                                                ✓ Mark Completed
                                            </Button>
                                        )}

                                        {item.status !== 'cancelled' && item.status !== 'completed' && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                disabled={updatingId === item.appointment_id}
                                                onClick={() => handleUpdateStatus(item.appointment_id, 'cancelled')}
                                                className="text-xs text-red-600 dark:text-red-400 hover:bg-red-50"
                                            >
                                                Cancel
                                            </Button>
                                        )}

                                        {item.meeting_link && (
                                            <a
                                                href={item.meeting_link}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline px-2 py-1"
                                            >
                                                <span>Telehealth Room</span>
                                                <span>↗</span>
                                            </a>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
