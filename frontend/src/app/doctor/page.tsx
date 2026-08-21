'use client';

import { useState, useEffect } from 'react';
import { doctorsApi, patientsApi, appointmentsApi, Doctor, Patient, Appointment } from '@/lib/api';
import { PatientSummary } from '@/components/PatientSummary';

export default function DoctorPage() {
    const [doctor, setDoctor] = useState<Doctor | null>(null);
    const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
    const [patients, setPatients] = useState<Patient[]>([]);
    const [todayAppointments, setTodayAppointments] = useState<Appointment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchDashboardData() {
            try {
                setLoading(true);

                // Get current doctor from auth token
                const token = localStorage.getItem('access_token');
                if (!token) {
                    throw new Error('Not authenticated');
                }

                // Parse token to get user ID (in real app, use proper JWT parsing)
                const payload = JSON.parse(atob(token.split('.')[1]));
                const userId = payload.sub;

                // Fetch doctor profile
                const doctors = await doctorsApi.list();
                const currentDoctor = doctors.doctors.find(d => d.user_id === userId);
                if (currentDoctor) {
                    setDoctor(currentDoctor);

                    // Fetch today's appointments for this doctor
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);
                    const tomorrow = new Date(today);
                    tomorrow.setDate(tomorrow.getDate() + 1);

                    const appointments = await appointmentsApi.list({
                        doctor_id: currentDoctor.doctor_id,
                        date_from: today.toISOString(),
                        date_to: tomorrow.toISOString(),
                        page_size: 20,
                    });
                    setTodayAppointments(appointments.appointments);
                }

                // Fetch all patients for the selector
                const patientsList = await patientsApi.list({ page_size: 100 });
                setPatients(patientsList.patients);

                // Auto-select first patient if available
                if (patientsList.patients.length > 0 && !selectedPatientId) {
                    setSelectedPatientId(patientsList.patients[0].patient_id);
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load dashboard');
            } finally {
                setLoading(false);
            }
        }

        fetchDashboardData();
    }, [selectedPatientId]);

    const formatTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'scheduled': return 'bg-blue-100 text-blue-700';
            case 'completed': return 'bg-green-100 text-green-700';
            case 'cancelled': return 'bg-red-100 text-red-700';
            case 'no_show': return 'bg-yellow-100 text-yellow-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    };

    if (loading) {
        return (
            <main className="min-h-screen bg-gray-50">
                <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
                    <div className="h-8 bg-gray-200 rounded animate-pulse w-1/4"></div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-40 bg-gray-200 rounded-xl animate-pulse"></div>
                        ))}
                    </div>
                    <div className="h-96 bg-gray-200 rounded-xl animate-pulse"></div>
                </div>
            </main>
        );
    }

    if (error) {
        return (
            <main className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="p-8 bg-white rounded-xl shadow-lg text-center">
                    <p className="text-red-600 mb-4">{error}</p>
                    <a href="/auth/login" className="text-primary-600 hover:underline">Login</a>
                </div>
            </main>
        );
    }

    return (
        <main className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <h1 className="text-2xl font-bold text-gray-900">Doctor Dashboard</h1>
                            {doctor && (
                                <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium">
                                    Dr. {doctor.full_name} • {doctor.specialty}
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-4">
                            <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                </svg>
                            </button>
                            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-medium">
                                {doctor?.full_name?.charAt(0) || 'D'}
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            <div className="max-w-7xl mx-auto px-4 py-6">
                {/* Patient Selector & Today's Appointments */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                    {/* Patient Selector */}
                    <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-gray-200">
                        <div className="p-4 border-b border-gray-200">
                            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                                <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                                </svg>
                                Select Patient
                            </h2>
                        </div>
                        <div className="p-4 max-h-64 overflow-y-auto">
                            {patients.length === 0 ? (
                                <p className="text-gray-500 text-sm text-center py-4">No patients found</p>
                            ) : (
                                <ul className="space-y-2">
                                    {patients.map((patient) => (
                                        <li key={patient.patient_id}>
                                            <button
                                                onClick={() => setSelectedPatientId(patient.patient_id)}
                                                className={`w-full text-left p-3 rounded-lg transition-colors ${selectedPatientId === patient.patient_id
                                                        ? 'bg-primary-50 border border-primary-200'
                                                        : 'hover:bg-gray-50'
                                                    }`}
                                            >
                                                <p className="font-medium text-gray-900">{patient.full_name}</p>
                                                <p className="text-sm text-gray-500">
                                                    DOB: {new Date(patient.date_of_birth).toLocaleDateString()} • {patient.gender}
                                                </p>
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>

                    {/* Today's Appointments */}
                    <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200">
                        <div className="p-4 border-b border-gray-200">
                            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                                <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                Today's Appointments
                                <span className="px-2 py-0.5 text-xs bg-primary-100 text-primary-700 rounded-full">
                                    {todayAppointments.length}
                                </span>
                            </h2>
                        </div>
                        <div className="divide-y divide-gray-200">
                            {todayAppointments.length === 0 ? (
                                <div className="p-8 text-center text-gray-500">
                                    <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    <p>No appointments scheduled for today</p>
                                </div>
                            ) : (
                                todayAppointments.map((appt) => (
                                    <div key={appt.appointment_id} className="p-4 hover:bg-gray-50">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                                                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                                    </svg>
                                                </div>
                                                <div>
                                                    <p className="font-medium text-gray-900">{appt.patient?.full_name || 'Unknown Patient'}</p>
                                                    <p className="text-sm text-gray-500">
                                                        {appt.notes || 'General consultation'}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className="font-medium text-gray-900">{formatTime(appt.scheduled_at)}</p>
                                                <p className="text-sm text-gray-500">{appt.duration_minutes} min</p>
                                                <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full capitalize ${getStatusColor(appt.status)}`}>
                                                    {appt.status.replace('_', ' ')}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                {/* Patient Summary */}
                {selectedPatientId && (
                    <PatientSummary patientId={selectedPatientId} />
                )}

                {/* Empty state when no patient selected */}
                {!selectedPatientId && patients.length > 0 && (
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
                        <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                        <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Patient</h3>
                        <p className="text-gray-500">Choose a patient from the sidebar to view their summary</p>
                    </div>
                )}
            </div>
        </main>
    );
}