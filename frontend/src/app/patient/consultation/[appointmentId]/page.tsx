'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { telehealthApi, TelehealthRoomData } from '@/lib/api';

export default function PatientConsultationRoomPage() {
    const params = useParams();
    const router = useRouter();
    const appointmentId = params?.appointmentId as string;

    const [roomData, setRoomData] = useState<TelehealthRoomData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [isMuted, setIsMuted] = useState(false);
    const [isVideoOff, setIsVideoOff] = useState(false);
    const [callSeconds, setCallSeconds] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setCallSeconds((prev) => prev + 1);
        }, 1000);
        return () => clearInterval(interval);
    }, []);

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
        } catch (err: any) {
            console.error('Failed to load patient telehealth room:', err);
            setError(err?.message || 'Unable to join consultation room.');
        } finally {
            setIsLoading(false);
        }
    };

    const formatTimer = (totalSec: number) => {
        const mins = Math.floor(totalSec / 60);
        const secs = totalSec % 60;
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    };

    if (isLoading) {
        return (
            <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3 text-slate-400">
                <svg className="animate-spin w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <p className="text-sm font-medium">Connecting to your doctor's secure room...</p>
            </div>
        );
    }

    if (error || !roomData) {
        return (
            <div className="max-w-md mx-auto p-8 rounded-2xl bg-white dark:bg-slate-900 border border-rose-200 dark:border-rose-800 text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 mx-auto flex items-center justify-center font-bold text-xl">
                    ✕
                </div>
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">Unable to Join Call</h2>
                <p className="text-xs text-rose-600 dark:text-rose-300">{error || 'Session not found.'}</p>
                <Link
                    href="/patient/appointments"
                    className="inline-block px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 transition"
                >
                    Back to Appointments
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-4 max-w-5xl mx-auto">
            {/* Header */}
            <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Link
                        href="/patient/appointments"
                        className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 transition"
                    >
                        ←
                    </Link>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                                CONNECTED
                            </span>
                            <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                                ⏱️ {formatTimer(callSeconds)}
                            </span>
                        </div>
                        <h1 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white mt-0.5">
                            Consultation with {roomData.doctor_name}
                        </h1>
                        <p className="text-xs text-slate-500">
                            {roomData.doctor_specialty} • {roomData.doctor_hospital || 'AI-HOS Medical Center'}
                        </p>
                    </div>
                </div>

                <Link
                    href="/patient/appointments"
                    className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition"
                >
                    Leave Room
                </Link>
            </div>

            {/* Video Viewport */}
            <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-xl h-[560px] relative flex flex-col justify-between">
                {/* Main Doctor Video Area */}
                <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-950 relative">
                    <div className="text-center space-y-3 z-10">
                        <div className="w-28 h-28 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 p-1 mx-auto shadow-2xl shadow-indigo-500/20">
                            <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center text-3xl font-bold text-white shadow-inner">
                                {roomData.doctor_name.replace('Dr. ', '').charAt(0)}
                            </div>
                        </div>

                        <div>
                            <h3 className="text-white font-bold text-base">
                                {roomData.doctor_name}
                            </h3>
                            <p className="text-indigo-400 text-xs font-mono">
                                Attending Physician • HD Audio & Video Active
                            </p>
                        </div>
                    </div>

                    {/* Patient Self Preview PIP */}
                    <div className="absolute bottom-4 right-4 w-36 h-24 bg-slate-900 rounded-xl border border-slate-700 shadow-2xl flex flex-col items-center justify-center p-2 z-20">
                        <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs mb-1">
                            You
                        </div>
                        <span className="text-[10px] text-slate-300 truncate w-full text-center">
                            {roomData.patient_name}
                        </span>
                        <span className="text-[9px] text-slate-400">
                            {isVideoOff ? 'Camera Off' : isMuted ? 'Muted' : 'Speaking'}
                        </span>
                    </div>
                </div>

                {/* Media Controls Bar */}
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

                    <Link
                        href="/patient/appointments"
                        className="px-5 py-2.5 rounded-full bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition shadow-md"
                    >
                        Disconnect Call
                    </Link>
                </div>
            </div>
        </div>
    );
}
