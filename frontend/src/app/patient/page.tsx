'use client';

import React from 'react';
import { useAuth } from '@/lib/auth';
import { Button, Card, CardContent, Badge } from '@/components/ui';

export default function PatientPage() {
    const { user } = useAuth();

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Patient Health Portal
                        </h1>
                        <Badge variant="success">ABHA / ABDM Linked</Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Welcome, {user?.full_name || 'Patient'} • Voice intake, appointments, and medical records
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <a href="/patient/intake">
                        <Button variant="ai" size="sm" icon={
                            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                        }>
                            Start Voice Triage
                        </Button>
                    </a>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="glass-panel hover:border-blue-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">AI Receptionist (Voice Intake)</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Speak your symptoms naturally. Real-time multilingual voice triage routes you to the appropriate specialist.
                        </p>
                    </CardContent>
                </Card>

                <Card className="glass-panel hover:border-cyan-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">Appointment Booking</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Schedule, reschedule, or cancel consultations with hospital physicians and outpatient clinics.
                        </p>
                    </CardContent>
                </Card>

                <Card className="glass-panel hover:border-emerald-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">Health Records & Prescriptions</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Access doctor-signed medical records, digital prescriptions, and visit summaries.
                        </p>
                    </CardContent>
                </Card>

                <Card className="glass-panel hover:border-purple-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">Multilingual AI Scribe Support</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Complete support for regional languages with automated translation to clinical English summaries.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}