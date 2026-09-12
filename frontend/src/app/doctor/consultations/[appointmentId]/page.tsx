'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
    telehealthApi,
    TelehealthRoomData,
} from '@/lib/api';

export default function DoctorTelehealthRoomPage() {
    const params = useParams();
    const router = useRouter();
    const appointmentId = params?.appointmentId as string;

    const [roomData, setRoomData] = useState<TelehealthRoomData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Call state controls
    const [isMuted, setIsMuted] = useState(false);
    const [isVideoOff, setIsVideoOff] = useState(false);
    const [isScreenSharing, setIsScreenSharing] = useState(false);
    const [activeTab, setActiveTab] = useState<'intake' | 'scribe' | 'copilot'>('intake');
    const [callSeconds, setCallSeconds] = useState(0);
    const [isEnding, setIsEnding] = useState(false);

    // Simulated Scribe state in room
    const [isScribeRecording, setIsScribeRecording] = useState(false);
    const [transcriptLines, setTranscriptLines] = useState<string[]>([
        "Doctor: Hello, I can see you clearly. How are you feeling right now?",
        "Patient: Good morning doctor. I've had this persistent discomfort for a few days.",
    ]);

    // Timer
    useEffect(() => {
        const interval = setInterval(() => {
            setCallSeconds((prev) => prev + 1);
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    // Load room
    useEffect(() => {
        if (!appointmentId) return;
        loadRoom();
    }, [appointmentId]);

    const loadRoom = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await telehealthApi.getRoom(appointmentId);
            setRoomData(data);

            // Automatically start session if scheduled
            if (data.status === 'scheduled') {
                await telehealthApi.startRoom(appointmentId);
                setRoomData((prev) => prev ? { ...prev, status: 'in_progress' } : null);
            }
        } catch (err: any) {
            console.error('Failed to load consultation room:', err);
            setError(err?.message || 'Failed to connect to consultation room.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleEndConsultation = async () => {
        if (!confirm('Are you sure you want to conclude this telehealth consultation?')) {
            return;
        }
        setIsEnding(true);
        try {
            await telehealthApi.endRoom(appointmentId);
            router.push('/doctor/consultations');
        } catch (err: any) {
            console.error('Failed to end consultation:', err);
            setError(err?.message || 'Failed to conclude consultation.');
            setIsEnding(false);
        }
    };

    const formatTimer = (totalSec: number) => {
        const mins = Math.floor(totalSec / 60);
        const secs = totalSec % 60;
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    };

    const intake = roomData?.intake_summary;
    const hasRedFlags = intake?.has_red_flags;

    if (isLoading) {
        return (
            <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3 text-slate-400">
                <svg className="animate-spin w-8 h-8 text-cyan-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <p className="text-sm font-medium">Connecting to secure encrypted telehealth room...</p>
            </div>
        );
    }

    if (error || !roomData) {
        return (
            <div className="max-w-xl mx-auto p-8 rounded-2xl bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-900/60 shadow-lg text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400 mx-auto flex items-center justify-center text-xl font-bold">
                    ✕
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                    Consultation Room Unavailable
                </h2>
                <p className="text-xs text-rose-600 dark:text-rose-300">
                    {error || 'Unable to access room data.'}
                </p>
                <Link
                    href="/doctor/consultations"
                    className="inline-block px-4 py-2 rounded-xl bg-slate-800 text-white text-xs font-semibold hover:bg-slate-700 transition"
                >
                    Back to Schedule
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Top Consultation Workstation Bar */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                    <Link
                        href="/doctor/consultations"
                        className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition"
                        title="Back to Schedule"
                    >
                        ←
                    </Link>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                                LIVE TELEHEALTH
                            </span>
                            <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                                ⏱️ {formatTimer(callSeconds)}
                            </span>
                            {hasRedFlags && (
                                <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-200 border border-rose-300 animate-pulse">
                                    🚨 Red Flag Warning
                                </span>
                            )}
                        </div>
                        <h1 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white mt-0.5">
                            {roomData.patient_name}
                            {roomData.patient_age && (
                                <span className="text-xs font-normal text-slate-400 ml-2">
                                    ({roomData.patient_age} yrs, {roomData.patient_gender || 'Not specified'})
                                </span>
                            )}
                        </h1>
                    </div>
                </div>

                {/* Right actions */}
                <div className="flex items-center gap-2">
                    <Link
                        href={`/doctor/scribe`}
                        className="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                    >
                        🎙️ Full Ambient Scribe
                    </Link>
                    <button
                        onClick={handleEndConsultation}
                        disabled={isEnding}
                        className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs sm:text-sm font-semibold transition shadow-sm disabled:opacity-50"
                    >
                        {isEnding ? 'Finalizing...' : 'End Consultation & Save'}
                    </button>
                </div>
            </div>

            {/* Split Screen Video & Clinical Workstation */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                
                {/* Left: Video Streams (7 cols) */}
                <div className="lg:col-span-7 flex flex-col bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-lg h-[640px] relative">
                    {/* Patient Video Stream Viewport */}
                    <div className="flex-1 relative flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-950 overflow-hidden">
                        {/* Simulated Remote Video Feed with animated aura */}
                        <div className="text-center space-y-3 z-10">
                            <div className="relative mx-auto w-32 h-32 rounded-full bg-gradient-to-tr from-indigo-600 to-cyan-500 p-1 shadow-2xl shadow-cyan-500/20">
                                <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center text-4xl font-bold text-white shadow-inner">
                                    {roomData.patient_name.charAt(0)}
                                </div>
                                <span className="absolute bottom-1 right-1 w-6 h-6 rounded-full bg-emerald-500 border-2 border-slate-950 flex items-center justify-center text-[10px] text-white">
                                    ✓
                                </span>
                            </div>

                            <div>
                                <h3 className="text-white font-bold text-base">
                                    {roomData.patient_name}
                                </h3>
                                <p className="text-cyan-400 text-xs font-mono">
                                    HD 1080p • 48 kHz Audio • Encrypted WebRTC
                                </p>
                            </div>

                            {/* Voice Activity Waveform */}
                            <div className="flex items-center justify-center gap-1 h-5 pt-1">
                                <span className="w-1 h-3 bg-cyan-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                <span className="w-1 h-5 bg-cyan-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                <span className="w-1 h-4 bg-cyan-400 rounded-full animate-bounce" />
                                <span className="w-1 h-2 bg-cyan-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
                            </div>
                        </div>

                        {/* Connection Badge in Corner */}
                        <div className="absolute top-4 left-4 z-20 flex items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-1 rounded-lg border border-slate-800 text-[11px] text-slate-300">
                            <span className="w-2 h-2 rounded-full bg-emerald-400" />
                            <span>Encrypted Telehealth Session</span>
                        </div>

                        {/* Local Doctor PIP Feed */}
                        <div className="absolute bottom-4 right-4 w-40 h-28 bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden flex flex-col items-center justify-center text-center p-2 z-20">
                            <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs mb-1">
                                Dr
                            </div>
                            <span className="text-[10px] text-slate-300 font-semibold truncate w-full">
                                {roomData.doctor_name}
                            </span>
                            <span className="text-[9px] text-slate-400">
                                {isVideoOff ? 'Camera Off' : isMuted ? 'Muted' : 'Speaking'}
                            </span>
                        </div>
                    </div>

                    {/* Floating Media Control Bar */}
                    <div className="p-3.5 bg-slate-900/95 border-t border-slate-800 flex items-center justify-center gap-4">
                        <button
                            onClick={() => setIsMuted(!isMuted)}
                            className={`p-3 rounded-full text-white transition shadow-md ${
                                isMuted ? 'bg-rose-600 hover:bg-rose-700' : 'bg-slate-800 hover:bg-slate-700'
                            }`}
                            title={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
                        >
                            {isMuted ? '🔇' : '🎙️'}
                        </button>

                        <button
                            onClick={() => setIsVideoOff(!isVideoOff)}
                            className={`p-3 rounded-full text-white transition shadow-md ${
                                isVideoOff ? 'bg-rose-600 hover:bg-rose-700' : 'bg-slate-800 hover:bg-slate-700'
                            }`}
                            title={isVideoOff ? 'Turn Camera On' : 'Turn Camera Off'}
                        >
                            {isVideoOff ? '🚫' : '📹'}
                        </button>

                        <button
                            onClick={() => setIsScreenSharing(!isScreenSharing)}
                            className={`p-3 rounded-full text-white transition shadow-md ${
                                isScreenSharing ? 'bg-cyan-600 hover:bg-cyan-700' : 'bg-slate-800 hover:bg-slate-700'
                            }`}
                            title={isScreenSharing ? 'Stop Screen Share' : 'Share Screen'}
                        >
                            💻
                        </button>

                        <button
                            onClick={() => setIsScribeRecording(!isScribeRecording)}
                            className={`px-4 py-2.5 rounded-full text-xs font-bold text-white transition shadow-md flex items-center gap-2 ${
                                isScribeRecording
                                    ? 'bg-purple-600 hover:bg-purple-700 animate-pulse'
                                    : 'bg-slate-800 hover:bg-slate-700'
                            }`}
                            title="Toggle Ambient Scribe"
                        >
                            <span className="w-2 h-2 rounded-full bg-red-400" />
                            {isScribeRecording ? 'Scribe Recording...' : 'Record Scribe'}
                        </button>
                    </div>
                </div>

                {/* Right: Integrated Clinical Assistant Panel (5 cols) */}
                <div className="lg:col-span-5 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm flex flex-col h-[640px]">
                    {/* Panel Tabs */}
                    <div className="flex border-b border-slate-200 dark:border-slate-800 pb-2 gap-2">
                        <button
                            onClick={() => setActiveTab('intake')}
                            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition ${
                                activeTab === 'intake'
                                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300'
                                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                            }`}
                        >
                            AI Intake & Triage
                        </button>

                        <button
                            onClick={() => setActiveTab('scribe')}
                            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition ${
                                activeTab === 'scribe'
                                    ? 'bg-purple-50 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300'
                                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                            }`}
                        >
                            Ambient Scribe
                        </button>

                        <button
                            onClick={() => setActiveTab('copilot')}
                            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition ${
                                activeTab === 'copilot'
                                    ? 'bg-cyan-50 text-cyan-700 dark:bg-cyan-950/60 dark:text-cyan-300'
                                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                            }`}
                        >
                            Copilot Assist
                        </button>
                    </div>

                    {/* Tab 1: AI Intake & Red Flags */}
                    {activeTab === 'intake' && (
                        <div className="flex-1 overflow-y-auto pt-3 space-y-4 text-xs sm:text-sm">
                            {hasRedFlags && (
                                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-900/60 text-rose-900 dark:text-rose-200 space-y-2">
                                    <div className="flex items-center gap-2 font-bold text-xs">
                                        <span>🚨 EMERGENCY RED-FLAGS DETECTED</span>
                                    </div>
                                    <ul className="list-disc list-inside text-xs space-y-1">
                                        {intake?.red_flag_warnings.map((w, idx) => (
                                            <li key={idx}>{w}</li>
                                        ))}
                                    </ul>
                                    <p className="text-[11px] text-rose-700 dark:text-rose-300 font-semibold pt-1">
                                        Recommendation: Confirm immediate vital stability, rule out acute coronary or neurological deficit.
                                    </p>
                                </div>
                            )}

                            {intake ? (
                                <div className="space-y-3.5">
                                    <div>
                                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                            Chief Complaint
                                        </span>
                                        <p className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                                            {intake.chief_complaint || 'No complaint specified'}
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-800">
                                            <span className="text-[10px] text-slate-400 font-medium block">Duration</span>
                                            <span className="text-xs font-semibold text-slate-700 dark:text-slate-200">
                                                {intake.duration || 'Not specified'}
                                            </span>
                                        </div>

                                        <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-800">
                                            <span className="text-[10px] text-slate-400 font-medium block">Reported Pain/Severity</span>
                                            <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                                                {intake.severity ? `${intake.severity}/10` : 'Unrated'}
                                            </span>
                                        </div>
                                    </div>

                                    {intake.associated_symptoms && intake.associated_symptoms.length > 0 && (
                                        <div>
                                            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                                                Associated Symptoms
                                            </span>
                                            <div className="flex flex-wrap gap-1.5 mt-1">
                                                {intake.associated_symptoms.map((s, idx) => (
                                                    <span key={idx} className="px-2 py-0.5 text-xs rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                                                        {s}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {intake.summary && (
                                        <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700">
                                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                                                Physician Brief Summary
                                            </span>
                                            <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                                                {intake.summary}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="p-8 text-center text-slate-400 text-xs">
                                    No pre-consultation intake recorded for this patient.
                                </div>
                            )}
                        </div>
                    )}

                    {/* Tab 2: Ambient Scribe */}
                    {activeTab === 'scribe' && (
                        <div className="flex-1 overflow-y-auto pt-3 space-y-3">
                            <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-900/60 text-xs text-purple-900 dark:text-purple-200 flex items-center justify-between">
                                <span>Ambient Voice Processing Active</span>
                                <span className="px-2 py-0.5 rounded bg-purple-200 dark:bg-purple-800 font-bold text-[10px]">
                                    Groq Whisper STT
                                </span>
                            </div>

                            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-800 space-y-2 h-[340px] overflow-y-auto font-mono text-xs">
                                {transcriptLines.map((line, i) => (
                                    <div key={i} className="text-slate-700 dark:text-slate-300">
                                        {line}
                                    </div>
                                ))}
                                {isScribeRecording && (
                                    <div className="text-purple-500 animate-pulse text-xs italic">
                                        [Listening & transcribing consultation audio...]
                                    </div>
                                )}
                            </div>

                            <Link
                                href="/doctor/scribe"
                                className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-xl bg-purple-600 text-white text-xs font-semibold hover:bg-purple-700 transition"
                            >
                                Open Full Note Generator →
                            </Link>
                        </div>
                    )}

                    {/* Tab 3: Copilot Diagnostics */}
                    {activeTab === 'copilot' && (
                        <div className="flex-1 overflow-y-auto pt-3 space-y-3 text-xs">
                            <div className="p-3 rounded-xl bg-cyan-50 dark:bg-cyan-950/40 border border-cyan-200 dark:border-cyan-800 text-cyan-900 dark:text-cyan-200">
                                <span className="font-bold block mb-1">Proposed Primary Diagnosis</span>
                                <span className="text-sm font-semibold">Tension-type Headache / Acute Migraine</span>
                                <span className="text-[10px] block font-mono text-cyan-700 dark:text-cyan-300 mt-0.5">ICD-10: G43.909</span>
                            </div>

                            <div className="space-y-1.5">
                                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                                    Differential Diagnoses
                                </span>
                                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                                    1. Cluster Headache (G44.009)
                                </div>
                                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                                    2. Cervicogenic Headache (G44.841)
                                </div>
                            </div>

                            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                                <Link
                                    href="/doctor/prescriptions"
                                    className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition shadow-sm"
                                >
                                    Draft Digital Prescription (M22) →
                                </Link>
                            </div>
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
}
