'use client';

import { useState, useEffect } from 'react';
import {
    patientsApi,
    appointmentsApi,
    medicalRecordsApi,
    prescriptionsApi,
    Patient,
    Appointment,
    MedicalRecord,
    Prescription
} from '@/lib/api';

interface PatientSummaryProps {
    patientId: string;
}

interface PatientSummaryData {
    patient: Patient | null;
    upcomingAppointments: Appointment[];
    recentMedicalRecords: MedicalRecord[];
    activePrescriptions: Prescription[];
    loading: boolean;
    error: string | null;
}

export function PatientSummary({ patientId }: PatientSummaryProps) {
    const [data, setData] = useState<PatientSummaryData>({
        patient: null,
        upcomingAppointments: [],
        recentMedicalRecords: [],
        activePrescriptions: [],
        loading: true,
        error: null,
    });

    useEffect(() => {
        async function fetchPatientSummary() {
            try {
                setData(prev => ({ ...prev, loading: true, error: null }));

                const [patient, appointments, records, prescriptions] = await Promise.all([
                    patientsApi.get(patientId),
                    appointmentsApi.list({ patient_id: patientId, status: 'scheduled', page_size: 5 }),
                    medicalRecordsApi.listByPatient(patientId, { page_size: 5 }),
                    prescriptionsApi.listByPatient(patientId, { status: 'FINALIZED', page_size: 5 }),
                ]);

                setData({
                    patient,
                    upcomingAppointments: appointments.appointments,
                    recentMedicalRecords: records.records,
                    activePrescriptions: prescriptions.prescriptions,
                    loading: false,
                    error: null,
                });
            } catch (err) {
                setData(prev => ({
                    ...prev,
                    loading: false,
                    error: err instanceof Error ? err.message : 'Failed to load patient summary',
                }));
            }
        }

        if (patientId) {
            fetchPatientSummary();
        }
    }, [patientId]);

    if (data.loading) {
        return (
            <div className="space-y-4">
                <div className="h-8 bg-gray-200 rounded animate-pulse w-1/4"></div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div>
            </div>
        );
    }

    if (data.error) {
        return (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                Error loading patient summary: {data.error}
            </div>
        );
    }

    if (!data.patient) {
        return (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700">
                Patient not found
            </div>
        );
    }

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });
    };

    const formatDateTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="space-y-6">
            {/* Patient Header */}
            <div className="bg-white dark:bg-slate-900/80 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                            <span className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                                {data.patient.full_name.charAt(0).toUpperCase()}
                            </span>
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-slate-900 dark:text-white">{data.patient.full_name}</h2>
                            <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400 mt-1">
                                <span>DOB: {formatDate(data.patient.date_of_birth)}</span>
                                <span>Gender: {data.patient.gender}</span>
                                <span>ABHA: {data.patient.abha_address || 'Not linked'}</span>
                            </div>
                        </div>
                    </div>
                    <div className="text-right">
                        <p className="text-sm text-slate-500 dark:text-slate-400">Patient ID</p>
                        <p className="font-mono text-sm text-slate-700 dark:text-slate-300">{data.patient.patient_id.slice(0, 8)}...</p>
                    </div>
                </div>
            </div>

            {/* Upcoming Appointments */}
            <div className="bg-white dark:bg-slate-900/80 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">
                    <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        Upcoming Appointments
                        {data.upcomingAppointments.length > 0 && (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded-full font-medium">
                                {data.upcomingAppointments.length}
                            </span>
                        )}
                    </h3>
                </div>
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                    {data.upcomingAppointments.length === 0 ? (
                        <div className="p-6 text-center text-slate-500 dark:text-slate-400">
                            No upcoming appointments scheduled
                        </div>
                    ) : (
                        data.upcomingAppointments.map((appt) => (
                            <div key={appt.appointment_id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                                            <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                            </svg>
                                        </div>
                                        <div>
                                            <p className="font-medium text-slate-900 dark:text-white">Dr. {appt.doctor?.full_name || 'Unknown'}</p>
                                            <p className="text-sm text-slate-500 dark:text-slate-400">{appt.doctor?.specialty || 'General'}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-medium text-slate-900 dark:text-white">{formatDateTime(appt.scheduled_at)}</p>
                                        <p className="text-sm text-slate-500 dark:text-slate-400">{appt.duration_minutes} min</p>
                                        <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 rounded-full capitalize">
                                            {appt.status.replace('_', ' ')}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Recent Medical Records */}
            <div className="bg-white dark:bg-slate-900/80 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">
                    <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Recent Medical Records
                        {data.recentMedicalRecords.length > 0 && (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded-full font-medium">
                                {data.recentMedicalRecords.length}
                            </span>
                        )}
                    </h3>
                </div>
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                    {data.recentMedicalRecords.length === 0 ? (
                        <div className="p-6 text-center text-slate-500 dark:text-slate-400">
                            No medical records found
                        </div>
                    ) : (
                        data.recentMedicalRecords.map((record) => (
                            <div key={record.record_id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center">
                                            <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                            </svg>
                                        </div>
                                        <div>
                                            <p className="font-medium text-slate-900 dark:text-white">
                                                {(record.content?.chief_complaint as string) || 'Clinical Note'}
                                            </p>
                                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                                Dr. {record.doctor?.full_name || 'Unknown'} • {formatDate(record.created_at)}
                                            </p>
                                        </div>
                                    </div>
                                    <span className={`px-2 py-0.5 text-xs rounded-full capitalize ${record.status === 'FINALIZED' ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400' :
                                            record.status === 'AMENDED' ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400' :
                                                'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                                        }`}>
                                        {record.status.toLowerCase()}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Active Prescriptions */}
            <div className="bg-white dark:bg-slate-900/80 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">
                    <h3 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                        <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Active Prescriptions
                        {data.activePrescriptions.length > 0 && (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded-full font-medium">
                                {data.activePrescriptions.length}
                            </span>
                        )}
                    </h3>
                </div>
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                    {data.activePrescriptions.length === 0 ? (
                        <div className="p-6 text-center text-slate-500 dark:text-slate-400">
                            No active prescriptions
                        </div>
                    ) : (
                        data.activePrescriptions.map((rx) => (
                            <div key={rx.prescription_id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1">
                                        <p className="font-medium text-slate-900 dark:text-white">
                                            {rx.medications.map(m => m.name).join(', ')}
                                        </p>
                                        <div className="flex flex-wrap gap-2 mt-1 text-sm text-slate-500 dark:text-slate-400">
                                            {rx.medications.map((m, i) => (
                                                <span key={i} className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-0.5 rounded">
                                                    {m.dosage} • {m.frequency} • {m.duration}
                                                </span>
                                            ))}
                                        </div>
                                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                            Prescribed by Dr. {rx.doctor?.full_name || 'Unknown'} • {formatDate(rx.created_at)}
                                        </p>
                                    </div>
                                    <span className="px-2 py-0.5 text-xs bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 rounded-full capitalize">
                                        {rx.status.toLowerCase()}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}