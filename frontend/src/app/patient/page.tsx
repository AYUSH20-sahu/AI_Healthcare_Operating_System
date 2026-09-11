'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { patientPortalApi, PatientPortalDashboardResponse } from '@/lib/api';
import { Card, CardContent, Button, Badge } from '@/components/ui';

export default function PatientDashboardPage() {
    const { user } = useAuth();
    const [dashboardData, setDashboardData] = useState<PatientPortalDashboardResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadDashboard();
    }, []);

    const loadDashboard = async () => {
        setIsLoading(true);
        try {
            const data = await patientPortalApi.getDashboard();
            setDashboardData(data);
        } catch (err) {
            console.error('Failed to load patient dashboard:', err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6 pb-12">
            {/* Top Welcome Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Patient Health Portal
                        </h1>
                        <Badge variant="success">ABHA Connected</Badge>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Welcome back, <span className="font-semibold text-slate-800 dark:text-slate-200">{dashboardData?.patient.full_name || user?.full_name || 'Patient'}</span> • Centralized health records, appointments, and AI triage.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <Link href="/patient/intake">
                        <Button
                            variant="primary"
                            size="md"
                            className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 shadow-md shadow-purple-500/20 text-white font-medium"
                        >
                            <span className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                                <span>🎙️ Start Voice Triage</span>
                            </span>
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Quick Metrics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Link href="/patient/appointments" className="block group">
                    <Card className="hover:border-blue-500/40 transition-all border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-sm shadow-sm group-hover:shadow-md">
                        <CardContent className="p-5 flex items-center justify-between">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                    Upcoming Consultations
                                </p>
                                <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                                    {isLoading ? '...' : dashboardData?.upcoming_appointments_count ?? 0}
                                </h3>
                                <p className="text-[11px] text-blue-600 dark:text-blue-400 font-medium mt-1">
                                    View schedule & details →
                                </p>
                            </div>
                            <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xl font-bold shadow-inner">
                                📅
                            </div>
                        </CardContent>
                    </Card>
                </Link>

                <Link href="/patient/records" className="block group">
                    <Card className="hover:border-emerald-500/40 transition-all border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-sm shadow-sm group-hover:shadow-md">
                        <CardContent className="p-5 flex items-center justify-between">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                    Finalized Medical Records
                                </p>
                                <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                                    {isLoading ? '...' : dashboardData?.finalized_records_count ?? 0}
                                </h3>
                                <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-1">
                                    Doctor-signed clinical summaries →
                                </p>
                            </div>
                            <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-xl font-bold shadow-inner">
                                📋
                            </div>
                        </CardContent>
                    </Card>
                </Link>

                <Link href="/patient/prescriptions" className="block group">
                    <Card className="hover:border-purple-500/40 transition-all border border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-sm shadow-sm group-hover:shadow-md">
                        <CardContent className="p-5 flex items-center justify-between">
                            <div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                    Active Prescriptions
                                </p>
                                <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                                    {isLoading ? '...' : dashboardData?.active_prescriptions_count ?? 0}
                                </h3>
                                <p className="text-[11px] text-purple-600 dark:text-purple-400 font-medium mt-1">
                                    Digital prescriptions & refills →
                                </p>
                            </div>
                            <div className="w-12 h-12 rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center text-xl font-bold shadow-inner">
                                💊
                            </div>
                        </CardContent>
                    </Card>
                </Link>
            </div>

            {/* Next Appointment Spotlight & Active Medication Timeline */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Next Appointment Spotlight (7 Cols) */}
                <div className="lg:col-span-7 space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <span>🩺 Next Consultation Spotlight</span>
                        </h2>
                        <Link href="/patient/appointments" className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                            All Appointments ({dashboardData?.upcoming_appointments_count ?? 0})
                        </Link>
                    </div>

                    {isLoading ? (
                        <Card className="p-8 text-center border border-slate-200 dark:border-slate-800 animate-pulse">
                            <div className="h-6 w-1/3 bg-slate-200 dark:bg-slate-700 rounded mx-auto mb-3" />
                            <div className="h-4 w-1/2 bg-slate-200 dark:bg-slate-700 rounded mx-auto" />
                        </Card>
                    ) : dashboardData?.next_appointment ? (
                        <Card className="border border-blue-200 dark:border-blue-900/60 bg-gradient-to-br from-blue-50/50 via-white to-slate-50/40 dark:from-blue-950/20 dark:via-slate-900 dark:to-slate-900/80 shadow-sm">
                            <CardContent className="p-6 space-y-4">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-blue-100 dark:border-blue-900/40 pb-3">
                                    <div>
                                        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                            {dashboardData.next_appointment.doctor_name}
                                        </h3>
                                        <p className="text-xs text-blue-700 dark:text-blue-300 font-medium">
                                            {dashboardData.next_appointment.doctor_specialty || 'General Physician'} • {dashboardData.next_appointment.hospital_affiliation || 'AI-HOS Medical Center'}
                                        </p>
                                    </div>
                                    <Badge variant="primary" className="uppercase font-bold text-[10px]">
                                        Confirmed
                                    </Badge>
                                </div>

                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                                    <div className="p-3 bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
                                        <span className="text-slate-400 block mb-0.5">Date & Time</span>
                                        <span className="font-bold text-slate-900 dark:text-white">
                                            {new Date(dashboardData.next_appointment.scheduled_at).toLocaleDateString()}
                                        </span>
                                        <span className="text-slate-500 block text-[11px]">
                                            {new Date(dashboardData.next_appointment.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>

                                    <div className="p-3 bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
                                        <span className="text-slate-400 block mb-0.5">Duration</span>
                                        <span className="font-bold text-slate-900 dark:text-white">
                                            {dashboardData.next_appointment.duration_minutes} Minutes
                                        </span>
                                        <span className="text-emerald-600 dark:text-emerald-400 block text-[11px] font-semibold">
                                            Direct Consultation
                                        </span>
                                    </div>

                                    <div className="p-3 bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 col-span-2 sm:col-span-1">
                                        <span className="text-slate-400 block mb-0.5">Format</span>
                                        <span className="font-bold text-slate-900 dark:text-white">
                                            {dashboardData.next_appointment.meeting_link ? 'Telehealth Video' : 'In-Person Hospital'}
                                        </span>
                                        <span className="text-slate-500 block text-[11px]">
                                            Main Clinic Block
                                        </span>
                                    </div>
                                </div>

                                {dashboardData.next_appointment.reason && (
                                    <p className="text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700">
                                        <strong>Consultation Reason:</strong> {dashboardData.next_appointment.reason}
                                    </p>
                                )}

                                <div className="flex items-center justify-end gap-3 pt-2">
                                    <Link href="/patient/appointments">
                                        <Button variant="outline" size="sm">
                                            Manage Schedule
                                        </Button>
                                    </Link>
                                </div>
                            </CardContent>
                        </Card>
                    ) : (
                        <Card className="p-8 text-center border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 rounded-2xl">
                            <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 mx-auto flex items-center justify-center text-xl mb-3">
                                📅
                            </div>
                            <h3 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                                No upcoming appointments scheduled
                            </h3>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                                Need to consult a doctor? Start an AI voice triage session or schedule a direct consultation.
                            </p>
                            <div className="mt-4">
                                <Link href="/patient/intake">
                                    <Button variant="primary" size="sm">
                                        Start Triage & Book
                                    </Button>
                                </Link>
                            </div>
                        </Card>
                    )}

                    {/* Emergency Red-Flag Protocol Reminder */}
                    <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/60 dark:bg-rose-950/20 flex items-start gap-3">
                        <span className="text-xl">🚨</span>
                        <div>
                            <h4 className="text-xs font-bold text-rose-800 dark:text-rose-300 uppercase tracking-wider">
                                Emergency Medical Notice
                            </h4>
                            <p className="text-xs text-rose-700 dark:text-rose-400 mt-0.5 leading-relaxed">
                                If you are experiencing severe chest pain, sudden numbness, difficulty breathing, or severe trauma, bypass online booking and call emergency services immediately or visit the nearest emergency room.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Recent Prescriptions & ABHA Summary (5 Cols) */}
                <div className="lg:col-span-5 space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <span>💊 Active Medications</span>
                        </h2>
                        <Link href="/patient/prescriptions" className="text-xs font-semibold text-purple-600 dark:text-purple-400 hover:underline">
                            View All ({dashboardData?.active_prescriptions_count ?? 0})
                        </Link>
                    </div>

                    {isLoading ? (
                        <Card className="p-6 text-center border border-slate-200 dark:border-slate-800 animate-pulse">
                            <div className="h-4 w-3/4 bg-slate-200 dark:bg-slate-700 rounded mx-auto" />
                        </Card>
                    ) : dashboardData?.recent_prescriptions && dashboardData.recent_prescriptions.length > 0 ? (
                        <div className="space-y-3">
                            {dashboardData.recent_prescriptions.map((rx) => (
                                <Card key={rx.prescription_id} className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                                    <CardContent className="p-4 space-y-2">
                                        <div className="flex items-center justify-between">
                                            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                                                Prescribed by {rx.doctor_name}
                                            </span>
                                            <Badge variant="success" className="text-[10px]">
                                                Finalized
                                            </Badge>
                                        </div>
                                        <div className="space-y-1.5 pt-1">
                                            {rx.medications.slice(0, 2).map((med, idx) => (
                                                <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-xs">
                                                    <div>
                                                        <span className="font-bold text-slate-900 dark:text-white block">
                                                            {med.name} {med.dosage}
                                                        </span>
                                                        <span className="text-slate-500 text-[11px]">
                                                            {med.frequency} • {med.duration}
                                                        </span>
                                                    </div>
                                                    <span className="text-[11px] font-semibold text-purple-600 dark:text-purple-400">
                                                        {med.route || 'Oral'}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    ) : (
                        <Card className="p-6 text-center border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                            <span className="text-2xl block mb-1">💊</span>
                            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                No active prescriptions on file
                            </p>
                            <p className="text-[11px] text-slate-500 mt-1">
                                Prescriptions signed by your physician will appear here automatically.
                            </p>
                        </Card>
                    )}

                    {/* ABHA / Profile Information Card */}
                    <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-4 space-y-3">
                            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
                                <span className="text-xs font-bold text-slate-900 dark:text-white">
                                    Digital Health Identity
                                </span>
                                <Badge variant="success">Active</Badge>
                            </div>
                            <div className="text-xs space-y-1">
                                <div className="flex justify-between">
                                    <span className="text-slate-400">ABHA Address:</span>
                                    <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                                        {dashboardData?.patient.abha_address || 'Not Registered'}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Phone:</span>
                                    <span className="text-slate-800 dark:text-slate-200">
                                        {dashboardData?.patient.phone || 'Not Provided'}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-400">Emergency Contact:</span>
                                    <span className="text-slate-800 dark:text-slate-200">
                                        {dashboardData?.patient.emergency_contact_name ? `${dashboardData.patient.emergency_contact_name} (${dashboardData.patient.emergency_contact_phone || ''})` : 'None Added'}
                                    </span>
                                </div>
                            </div>
                            <div className="pt-2">
                                <Link href="/patient/profile">
                                    <Button variant="secondary" size="sm" className="w-full text-xs">
                                        ✏️ Edit Profile & Emergency Contacts
                                    </Button>
                                </Link>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}