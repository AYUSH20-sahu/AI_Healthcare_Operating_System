'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { appointmentsApi, doctorsApi, Appointment, Doctor } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusBadge } from '@/components/ui/StatusBadge';

export default function DoctorAppointmentsPage() {
    const { user } = useAuth();
    const [appointments, setAppointments] = useState<Appointment[]>([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState<string>('ALL');

    useEffect(() => {
        async function loadAppointments() {
            try {
                setLoading(true);
                const res = await appointmentsApi.list({ page_size: 50 });
                if (res && res.appointments) {
                    setAppointments(res.appointments);
                }
            } catch (err) {
                console.error('Failed to load doctor appointments:', err);
            } finally {
                setLoading(false);
            }
        }
        loadAppointments();
    }, []);

    const filtered = appointments.filter(a => {
        if (statusFilter === 'ALL') return true;
        return a.status.toUpperCase() === statusFilter;
    });

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Link href="/doctor" className="text-xs text-teal-600 dark:text-teal-400 hover:underline">
                            ← Back to Copilot Workspace
                        </Link>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                        Specialist Outpatient Appointments & Queue
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                        View, filter, and manage scheduled patient encounters and outpatient time slots.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Filter Status:</span>
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="text-xs py-1.5 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    >
                        <option value="ALL">All Statuses ({appointments.length})</option>
                        <option value="SCHEDULED">Scheduled</option>
                        <option value="IN_PROGRESS">In Progress</option>
                        <option value="COMPLETED">Completed</option>
                        <option value="CANCELLED">Cancelled</option>
                    </select>
                </div>
            </div>

            {/* Content Table */}
            <Card className="border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                <CardHeader className="p-4 bg-slate-50/50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-800">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-semibold">Active Appointment Schedule</CardTitle>
                        <Badge variant="primary">{filtered.length} Appointments</Badge>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    {loading ? (
                        <div className="p-12 text-center text-xs text-slate-400">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-500 mx-auto mb-2" />
                            Loading outpatient appointments...
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="p-12 text-center text-xs text-slate-500">
                            No appointments found matching filter &quot;{statusFilter}&quot;.
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs">
                                <thead className="bg-slate-50 dark:bg-slate-900 text-slate-500 uppercase tracking-wider text-[10px] border-b border-slate-200 dark:border-slate-800">
                                    <tr>
                                        <th className="p-3.5">Scheduled Time</th>
                                        <th className="p-3.5">Patient Details</th>
                                        <th className="p-3.5">Reason / Specialty</th>
                                        <th className="p-3.5">Duration</th>
                                        <th className="p-3.5">Status</th>
                                        <th className="p-3.5 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                    {filtered.map((appt) => (
                                        <tr key={appt.appointment_id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                                            <td className="p-3.5 font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">
                                                {new Date(appt.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                <div className="text-[10px] text-slate-400">
                                                    {new Date(appt.scheduled_at).toLocaleDateString()}
                                                </div>
                                            </td>
                                            <td className="p-3.5">
                                                <Link
                                                    href={`/doctor/patients/${appt.patient_id}`}
                                                    className="font-bold text-teal-600 dark:text-teal-400 hover:underline"
                                                >
                                                    {appt.patient?.full_name || 'Patient Encounter'}
                                                </Link>
                                                <div className="text-[10px] text-slate-400">
                                                    {appt.patient?.abha_address || 'ABHA Registered'}
                                                </div>
                                            </td>
                                            <td className="p-3.5 text-slate-600 dark:text-slate-300">
                                                {appt.reason || appt.notes || 'General Outpatient Review'}
                                            </td>
                                            <td className="p-3.5 text-slate-500">
                                                {appt.duration_minutes || 30} mins
                                            </td>
                                            <td className="p-3.5">
                                                <StatusBadge status={appt.status.toUpperCase() as any} />
                                            </td>
                                            <td className="p-3.5 text-right whitespace-nowrap">
                                                <Link href={`/doctor?selected=${appt.patient_id}`}>
                                                    <Button size="sm" variant="secondary">
                                                        Open Copilot →
                                                    </Button>
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
