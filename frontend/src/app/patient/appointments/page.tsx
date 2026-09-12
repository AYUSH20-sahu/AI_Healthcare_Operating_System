'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { patientPortalApi, PatientPortalAppointmentItem } from '@/lib/api';
import { Card, CardContent, Button, Badge, Modal, Alert } from '@/components/ui';

export default function PatientAppointmentsPage() {
    const [appointments, setAppointments] = useState<PatientPortalAppointmentItem[]>([]);
    const [activeTab, setActiveTab] = useState<'all' | 'upcoming' | 'past'>('upcoming');
    const [isLoading, setIsLoading] = useState(true);
    const [selectedAppointment, setSelectedAppointment] = useState<PatientPortalAppointmentItem | null>(null);
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [isCancelling, setIsCancelling] = useState(false);
    const [statusBanner, setStatusBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    const loadAppointments = useCallback(async () => {
        setIsLoading(true);
        try {
            const data = await patientPortalApi.getAppointments();
            setAppointments(data);
        } catch (err) {
            console.error('Failed to load appointments:', err);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        loadAppointments();
    }, [loadAppointments]);

    const now = new Date();

    const filteredAppointments = appointments.filter((appt) => {
        const apptDate = new Date(appt.scheduled_at);
        if (activeTab === 'upcoming') {
            return apptDate >= now && appt.status.toUpperCase() !== 'CANCELLED';
        }
        if (activeTab === 'past') {
            return apptDate < now || appt.status.toUpperCase() === 'CANCELLED';
        }
        return true;
    });

    const handleConfirmCancel = async () => {
        if (!selectedAppointment) return;
        setIsCancelling(true);
        setStatusBanner(null);
        try {
            await patientPortalApi.cancelAppointment(selectedAppointment.appointment_id);
            setStatusBanner({
                type: 'success',
                message: `Consultation with ${selectedAppointment.doctor_name} was successfully cancelled.`,
            });
            setShowCancelModal(false);
            setSelectedAppointment(null);
            await loadAppointments();
        } catch (err: any) {
            console.error('Cancellation failed:', err);
            setStatusBanner({
                type: 'error',
                message: err.message || 'Failed to cancel appointment. Please try again.',
            });
        } finally {
            setIsCancelling(false);
        }
    };

    return (
        <div className="space-y-6 pb-12 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                        <span>📅 My Consultations & Appointments</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        View upcoming clinic visits, telehealth sessions, and consultation history.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <Link href="/patient/intake">
                        <Button variant="primary" size="sm">
                            + Book New Consultation
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Notification Banner */}
            {statusBanner && (
                <Alert
                    variant={statusBanner.type === 'success' ? 'success' : 'error'}
                    title={statusBanner.type === 'success' ? 'Appointment Updated' : 'Operation Error'}
                    onClose={() => setStatusBanner(null)}
                >
                    {statusBanner.message}
                </Alert>
            )}

            {/* Tab Filter */}
            <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
                <button
                    onClick={() => setActiveTab('upcoming')}
                    className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                        activeTab === 'upcoming'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                >
                    Upcoming Consultations ({appointments.filter(a => new Date(a.scheduled_at) >= now && a.status.toUpperCase() !== 'CANCELLED').length})
                </button>
                <button
                    onClick={() => setActiveTab('past')}
                    className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                        activeTab === 'past'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                >
                    Past & Cancelled ({appointments.filter(a => new Date(a.scheduled_at) < now || a.status.toUpperCase() === 'CANCELLED').length})
                </button>
                <button
                    onClick={() => setActiveTab('all')}
                    className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                        activeTab === 'all'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                >
                    All ({appointments.length})
                </button>
            </div>

            {/* Appointment List */}
            {isLoading ? (
                <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="p-6 animate-pulse border border-slate-200 dark:border-slate-800">
                            <div className="h-5 w-1/4 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                            <div className="h-4 w-1/2 bg-slate-200 dark:bg-slate-700 rounded" />
                        </Card>
                    ))}
                </div>
            ) : filteredAppointments.length > 0 ? (
                <div className="space-y-3">
                    {filteredAppointments.map((appt) => {
                        const isPast = new Date(appt.scheduled_at) < now;
                        const isCancelled = appt.status.toUpperCase() === 'CANCELLED';

                        return (
                            <Card
                                key={appt.appointment_id}
                                className={`border transition-all shadow-sm ${
                                    isCancelled
                                        ? 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 opacity-70'
                                        : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-blue-500/40'
                                }`}
                            >
                                <CardContent className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div className="space-y-1.5">
                                        <div className="flex items-center gap-2.5">
                                            <h3 className="font-bold text-base text-slate-900 dark:text-white">
                                                {appt.doctor_name}
                                            </h3>
                                            <Badge
                                                variant={
                                                    isCancelled
                                                        ? 'error'
                                                        : isPast
                                                        ? 'outline'
                                                        : 'primary'
                                                }
                                                className="text-[10px] uppercase font-bold"
                                            >
                                                {appt.status}
                                            </Badge>
                                            <span className="text-xs text-slate-400">
                                                {appt.doctor_specialty || 'Physician'} • {appt.hospital_affiliation || 'AI-HOS Medical Center'}
                                            </span>
                                        </div>

                                        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                                            <span className="flex items-center gap-1 font-semibold text-slate-800 dark:text-slate-200">
                                                <span>🗓️</span> {new Date(appt.scheduled_at).toLocaleDateString()} at {new Date(appt.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                            <span>⏱️ {appt.duration_minutes} Mins</span>
                                            <span>{appt.meeting_link ? '📹 Telehealth Video' : '🏥 Hospital Outpatient'}</span>
                                        </div>

                                        {appt.reason && (
                                            <p className="text-xs text-slate-600 dark:text-slate-300 pt-1">
                                                <strong>Reason:</strong> {appt.reason}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex items-center gap-2 self-end md:self-center">
                                        {!isPast && !isCancelled && (
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                className="text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-xs"
                                                onClick={() => {
                                                    setSelectedAppointment(appt);
                                                    setShowCancelModal(true);
                                                }}
                                            >
                                                Cancel
                                            </Button>
                                        )}
                                        {!isCancelled && (
                                            <Link href={`/patient/consultation/${appt.appointment_id}`}>
                                                <Button variant="primary" size="sm" className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white">
                                                    📹 Join Telehealth Video
                                                </Button>
                                            </Link>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            ) : (
                <Card className="p-12 text-center border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 rounded-2xl">
                    <span className="text-3xl block mb-2">🗓️</span>
                    <h3 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                        No {activeTab} appointments found
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                        You do not have any {activeTab === 'upcoming' ? 'scheduled upcoming' : activeTab} appointments on record.
                    </p>
                    <div className="mt-4">
                        <Link href="/patient/intake">
                            <Button variant="primary" size="sm">
                                Book a Consultation
                            </Button>
                        </Link>
                    </div>
                </Card>
            )}

            {/* Cancel Confirmation Modal */}
            <Modal
                isOpen={showCancelModal}
                onClose={() => setShowCancelModal(false)}
                title="Cancel Appointment Confirmation"
            >
                <div className="space-y-4">
                    <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                        Are you sure you want to cancel your consultation with <strong className="text-slate-900 dark:text-white">{selectedAppointment?.doctor_name}</strong> scheduled for {selectedAppointment ? new Date(selectedAppointment.scheduled_at).toLocaleDateString() : ''}?
                    </p>
                    <p className="text-xs text-slate-500">
                        This slot will be released back to the clinic schedule. You can reschedule anytime through AI triage or online booking.
                    </p>

                    <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                        <Button variant="secondary" onClick={() => setShowCancelModal(false)}>
                            Keep Appointment
                        </Button>
                        <Button
                            variant="danger"
                            onClick={handleConfirmCancel}
                            disabled={isCancelling}
                        >
                            {isCancelling ? 'Cancelling...' : 'Yes, Cancel Consultation'}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
