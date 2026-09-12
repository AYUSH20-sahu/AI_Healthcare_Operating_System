'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { adminOperationsApi, DoctorAvailabilityMatrixResponse, appointmentBookingApi } from '@/lib/api';
import { Button, Card, CardContent, Badge } from '@/components/ui';

export default function AdminDoctorAvailabilityPage() {
    const [matrix, setMatrix] = useState<DoctorAvailabilityMatrixResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0]);
    const [specialties, setSpecialties] = useState<string[]>([]);
    const [selectedSpecialty, setSelectedSpecialty] = useState('all');

    useEffect(() => {
        loadSpecialties();
    }, []);

    useEffect(() => {
        loadAvailability();
    }, [selectedDate, selectedSpecialty]);

    const loadSpecialties = async () => {
        try {
            const list = await appointmentBookingApi.getSpecialties();
            setSpecialties(list);
        } catch (err) {
            console.error('Failed to load specialties:', err);
        }
    };

    const loadAvailability = async () => {
        setIsLoading(true);
        try {
            const res = await adminOperationsApi.getDoctorAvailability(selectedDate, selectedSpecialty);
            setMatrix(res);
        } catch (err: any) {
            console.error('Failed to load doctor availability matrix:', err);
        } finally {
            setIsLoading(false);
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
                        <Badge variant="purple" className="text-[10px] uppercase font-bold">
                            Capacity Matrix
                        </Badge>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-1 flex items-center gap-2">
                        <span>📊 Doctor Availability & Capacity Utilization</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Inspect daily 30-minute consultation slot allocations, provider workload distribution, and overall clinic utilization.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <input
                        type="date"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                    />
                    <select
                        value={selectedSpecialty}
                        onChange={(e) => setSelectedSpecialty(e.target.value)}
                        className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                    >
                        <option value="all">All Specialties</option>
                        {specialties.map((s) => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Clinic Capacity Summary Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Active Doctors on Schedule
                            </span>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
                                {matrix?.total_doctors ?? 0}
                            </h3>
                        </div>
                        <span className="text-2xl">🩺</span>
                    </CardContent>
                </Card>

                <Card className="border border-purple-200 dark:border-purple-900/50 bg-purple-50/20 dark:bg-purple-950/20 shadow-sm">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-purple-700 dark:text-purple-300">
                                Overall Slot Utilization
                            </span>
                            <h3 className="text-2xl font-bold text-purple-900 dark:text-purple-100 mt-1">
                                {matrix?.overall_clinic_utilization_pct ?? 0}%
                            </h3>
                        </div>
                        <span className="text-2xl">📈</span>
                    </CardContent>
                </Card>

                <Card className="border border-blue-200 dark:border-blue-900/50 bg-blue-50/20 dark:bg-blue-950/20 shadow-sm">
                    <CardContent className="p-4 flex items-center justify-between">
                        <div>
                            <span className="text-xs font-semibold uppercase tracking-wider text-blue-700 dark:text-blue-300">
                                Standard Daily Interval
                            </span>
                            <h3 className="text-base font-bold text-blue-900 dark:text-blue-100 mt-1">
                                09:00 - 17:00 (30m Slots)
                            </h3>
                        </div>
                        <span className="text-2xl">⏰</span>
                    </CardContent>
                </Card>
            </div>

            {/* Doctor Capacity Cards Grid */}
            {isLoading ? (
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="p-6 animate-pulse border border-slate-200 dark:border-slate-800">
                            <div className="h-5 w-1/3 bg-slate-200 dark:bg-slate-700 rounded mb-3" />
                            <div className="h-3 w-1/2 bg-slate-200 dark:bg-slate-700 rounded mb-4" />
                            <div className="h-10 bg-slate-100 dark:bg-slate-800 rounded" />
                        </Card>
                    ))}
                </div>
            ) : !matrix || matrix.doctors.length === 0 ? (
                <Card className="border border-dashed border-slate-300 dark:border-slate-800 p-12 text-center bg-white dark:bg-slate-900">
                    <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center text-xl mb-3">
                        📊
                    </div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                        No doctors found
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        No doctors match the selected specialty filter.
                    </p>
                </Card>
            ) : (
                <div className="space-y-5">
                    {matrix.doctors.map((doc) => (
                        <Card
                            key={doc.doctor_id}
                            className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm"
                        >
                            <CardContent className="p-6 space-y-4">
                                {/* Doctor Info & Utilization Bar */}
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-base font-bold text-slate-900 dark:text-white">
                                                {doc.doctor_name}
                                            </h3>
                                            <Badge variant="primary" className="text-[10px]">
                                                {doc.specialty}
                                            </Badge>
                                        </div>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                            {doc.hospital_affiliation || 'AI-HOS Health Center'} • {doc.email}
                                        </p>
                                    </div>

                                    {/* Utilization Stats */}
                                    <div className="text-right">
                                        <div className="text-xs font-bold text-slate-900 dark:text-white">
                                            {doc.booked_slots} / {doc.total_slots} slots booked
                                            <span className="text-purple-600 dark:text-purple-400 ml-1.5">
                                                ({doc.utilization_rate_pct}% utilization)
                                            </span>
                                        </div>
                                        {/* Capacity Progress Bar */}
                                        <div className="w-48 h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-1.5 ml-auto">
                                            <div
                                                className={`h-full rounded-full ${
                                                    doc.utilization_rate_pct > 75
                                                        ? 'bg-red-500'
                                                        : doc.utilization_rate_pct > 40
                                                        ? 'bg-amber-500'
                                                        : 'bg-emerald-500'
                                                }`}
                                                style={{ width: `${Math.min(doc.utilization_rate_pct, 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Slot Matrix Pills */}
                                <div>
                                    <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 block mb-2">
                                        Consultation Time Slots ({matrix.date})
                                    </span>
                                    <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
                                        {doc.slots.map((slot, idx) => (
                                            <div
                                                key={idx}
                                                className={`p-2 rounded-lg border text-center transition-all text-xs ${
                                                    slot.is_available
                                                        ? 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/50 dark:bg-emerald-950/20 text-emerald-800 dark:text-emerald-300'
                                                        : 'border-blue-200 dark:border-blue-900/60 bg-blue-50/50 dark:bg-blue-950/20 text-blue-800 dark:text-blue-300'
                                                }`}
                                            >
                                                <div className="font-bold text-xs">
                                                    {slot.slot_time}
                                                </div>
                                                <div className="text-[10px] truncate mt-0.5">
                                                    {slot.is_available ? (
                                                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">Open</span>
                                                    ) : (
                                                        <span className="font-semibold text-blue-700 dark:text-blue-300" title={slot.patient_name || 'Booked'}>
                                                            {slot.patient_name || 'Booked'}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
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
