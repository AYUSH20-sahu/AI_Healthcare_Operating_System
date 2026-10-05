'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { api, API_BASE, telehealthApi, TelehealthRoomData } from '@/lib/api';
import type { IceServerItem } from '@/lib/api';

type CallState = 'idle' | 'connecting' | 'waiting' | 'negotiating' | 'active' | 'ended' | 'error';

const DEFAULT_STUN_SERVERS: IceServerItem[] = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
];

export default function PatientConsultationRoomPage() {
    const params = useParams();
    const router = useRouter();
    const appointmentId = params?.appointmentId as string;

    const [roomData, setRoomData] = useState<TelehealthRoomData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Media refs
    const localVideoRef = useRef<HTMLVideoElement>(null);
    const remoteVideoRef = useRef<HTMLVideoElement>(null);
    const localStreamRef = useRef<MediaStream | null>(null);
    const peerRef = useRef<RTCPeerConnection | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    // Call state controls
    const [callState, setCallState] = useState<CallState>('idle');
    const [isMuted, setIsMuted] = useState(false);
    const [isVideoOff, setIsVideoOff] = useState(false);
    const [callSeconds, setCallSeconds] = useState(0);
    const [iceServersUsed, setIceServersUsed] = useState<IceServerItem[]>(DEFAULT_STUN_SERVERS);

    const timerRef = useRef<NodeJS.Timeout | null>(null);

    const startTimer = useCallback(() => {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => {
            setCallSeconds(prev => prev + 1);
        }, 1000);
    }, []);

    const stopTimer = useCallback(() => {
        if (timerRef.current) clearInterval(timerRef.current);
    }, []);

    // ── Signalling & WebRTC ───────────────────────────────────────────────────
    const sendSignal = useCallback((type: string, payload: unknown) => {
        wsRef.current?.send(JSON.stringify({ type, payload }));
    }, []);

    const createPeer = useCallback((servers: IceServerItem[]) => {
        const pc = new RTCPeerConnection({ iceServers: servers });

        pc.onicecandidate = (event) => {
            if (event.candidate && wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                    type: 'ice-candidate',
                    payload: event.candidate,
                }));
            }
        };

        pc.ontrack = (event) => {
            if (remoteVideoRef.current && event.streams[0]) {
                remoteVideoRef.current.srcObject = event.streams[0];
            }
            setCallState('active');
            startTimer();
        };

        pc.onconnectionstatechange = () => {
            if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
                setCallState('ended');
                stopTimer();
            }
        };

        return pc;
    }, [startTimer, stopTimer]);

    const handleSignal = useCallback(async (message: { type: string; payload: unknown }) => {
        const pc = peerRef.current;
        if (!pc) return;

        switch (message.type) {
            case 'offer':
                setCallState('negotiating');
                await pc.setRemoteDescription(new RTCSessionDescription(message.payload as RTCSessionDescriptionInit));
                const answer = await pc.createAnswer();
                await pc.setLocalDescription(answer);
                sendSignal('answer', answer);
                break;

            case 'ice-candidate':
                try {
                    await pc.addIceCandidate(new RTCIceCandidate(message.payload as RTCIceCandidateInit));
                } catch { /* ignore stale candidates */ }
                break;

            case 'bye':
            case 'peer_left':
                setCallState('ended');
                stopTimer();
                break;
        }
    }, [sendSignal, stopTimer]);

    // ── Initialize Media & Call ───────────────────────────────────────────────
    const initCall = useCallback(async () => {
        if (!appointmentId) return;
        setIsLoading(true);
        setError(null);
        setCallState('connecting');

        try {
            // 1. Fetch room details
            const data = await telehealthApi.getRoom(appointmentId);
            setRoomData(data);

            // 2. Acquire local media
            let stream: MediaStream | null = null;
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                localStreamRef.current = stream;
                if (localVideoRef.current) {
                    localVideoRef.current.srcObject = stream;
                }
            } catch (mediaErr) {
                console.warn('Could not acquire camera/mic:', mediaErr);
            }

            // 3. Get room token and Coturn ICE servers
            const tokenData = await telehealthApi.getRoomToken(appointmentId);
            let iceServers = tokenData.ice_servers;
            if (!iceServers || iceServers.length === 0) {
                try {
                    const iceRes = await telehealthApi.getIceServers();
                    iceServers = iceRes.ice_servers;
                } catch {
                    iceServers = DEFAULT_STUN_SERVERS;
                }
            }
            setIceServersUsed(iceServers);

            // 4. Create RTCPeerConnection and attach tracks
            const pc = createPeer(iceServers);
            peerRef.current = pc;
            if (stream) {
                stream.getTracks().forEach(track => pc.addTrack(track, stream!));
            }

            // 5. Connect WebSocket signalling relay
            const wsBase = API_BASE.replace(/^http/, 'ws').replace('/api/v1', '');
            const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
            const wsUrl = `${wsBase}/api/v1${tokenData.ws_url}${token ? `?token=${token}` : ''}`;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => setCallState('waiting');
            ws.onmessage = (ev) => {
                try {
                    const msg = JSON.parse(ev.data);
                    handleSignal(msg);
                } catch { /* ignore malformed */ }
            };
            ws.onerror = () => {
                setError('Signalling connection error. Please verify network.');
                setCallState('error');
            };
            ws.onclose = () => {
                if (callState !== 'ended' && callState !== 'error') {
                    setCallState('ended');
                    stopTimer();
                }
            };
        } catch (err: unknown) {
            console.error('Failed to initialize patient telehealth room:', err);
            setError(err instanceof Error ? err.message : 'Unable to join consultation room.');
            setCallState('error');
        } finally {
            setIsLoading(false);
        }
    }, [appointmentId, createPeer, handleSignal, callState, stopTimer]);

    useEffect(() => {
        initCall();
        return () => {
            localStreamRef.current?.getTracks().forEach(t => t.stop());
            wsRef.current?.close();
            peerRef.current?.close();
            stopTimer();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [appointmentId]);

    const formatTimer = (totalSec: number) => {
        const mins = Math.floor(totalSec / 60);
        const secs = totalSec % 60;
        return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    };

    const toggleMic = () => {
        localStreamRef.current?.getAudioTracks().forEach(t => { t.enabled = isMuted; });
        setIsMuted(m => !m);
    };

    const toggleCam = () => {
        localStreamRef.current?.getVideoTracks().forEach(t => { t.enabled = isVideoOff; });
        setIsVideoOff(v => !v);
    };

    const hasCoturnRelay = iceServersUsed.some(s => {
        const u = Array.isArray(s.urls) ? s.urls.join(',') : s.urls;
        return u.includes('turn:') || u.includes('turns:');
    });

    if (isLoading) {
        return (
            <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3 text-slate-400">
                <div className="w-10 h-10 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm font-medium">Connecting to your doctor's secure room (Horizon C Coturn WebRTC)…</p>
            </div>
        );
    }

    if (error && !roomData) {
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
                        className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition"
                    >
                        ←
                    </Link>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                                callState === 'active'
                                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                    : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                            }`}>
                                <span className={`w-2 h-2 rounded-full ${callState === 'active' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                                {callState === 'active' ? 'CONNECTED' : callState.toUpperCase()}
                            </span>
                            <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                                ⏱️ {formatTimer(callSeconds)}
                            </span>
                            {hasCoturnRelay && (
                                <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-900/40 text-blue-300 border border-blue-700/40">
                                    🛡️ Coturn NAT Protected
                                </span>
                            )}
                        </div>
                        <h1 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white mt-0.5">
                            Consultation with {roomData?.doctor_name || 'Attending Physician'}
                        </h1>
                        <p className="text-xs text-slate-500">
                            {roomData?.doctor_specialty || 'General Medicine'} • {roomData?.doctor_hospital || 'AI-HOS Apex Clinical Center'}
                        </p>
                    </div>
                </div>

                <Link
                    href="/patient/appointments"
                    onClick={() => {
                        sendSignal('bye', {});
                        wsRef.current?.close();
                        peerRef.current?.close();
                    }}
                    className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition"
                >
                    Leave Room
                </Link>
            </div>

            {/* Video Viewport Stage */}
            <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-xl h-[560px] relative flex flex-col justify-between">
                {/* Doctor Video Area */}
                <div className="flex-1 relative bg-slate-900 flex items-center justify-center overflow-hidden">
                    <video
                        id="patient-remote-video"
                        ref={remoteVideoRef}
                        autoPlay
                        playsInline
                        className={`w-full h-full object-cover transition-opacity duration-300 ${callState === 'active' ? 'opacity-100' : 'opacity-0'}`}
                    />

                    {callState !== 'active' && (
                        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-950">
                            <div className="text-center space-y-3 z-10 p-6">
                                <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 p-1 mx-auto shadow-2xl shadow-indigo-500/20">
                                    <div className="w-full h-full rounded-full bg-slate-900 flex items-center justify-center text-3xl font-bold text-white shadow-inner">
                                        {roomData?.doctor_name?.replace('Dr. ', '').charAt(0) || 'D'}
                                    </div>
                                </div>
                                <div>
                                    <h3 className="text-white font-bold text-base">
                                        {roomData?.doctor_name || 'Attending Physician'}
                                    </h3>
                                    <p className="text-indigo-400 text-xs font-mono">
                                        {callState === 'waiting' ? 'Waiting for doctor to join session…' : 'Connecting Coturn WebRTC…'}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Patient Self Preview PIP */}
                    <div className="absolute bottom-4 right-4 w-40 h-28 bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden z-20">
                        <video
                            id="patient-local-video"
                            ref={localVideoRef}
                            autoPlay
                            playsInline
                            muted
                            className={`w-full h-full object-cover ${isVideoOff ? 'opacity-0' : 'opacity-100'}`}
                        />
                        {isVideoOff && (
                            <div className="absolute inset-0 flex items-center justify-center bg-slate-800 text-slate-400 text-xs">
                                Camera Off
                            </div>
                        )}
                        <div className="absolute bottom-1 left-1 text-[9px] bg-black/60 text-white px-1.5 py-0.5 rounded">
                            You {isMuted && '(Muted)'}
                        </div>
                    </div>
                </div>

                {/* Media Controls Bar */}
                <div className="p-3.5 bg-slate-900/95 border-t border-slate-800 flex items-center justify-center gap-4">
                    <button
                        type="button"
                        onClick={toggleMic}
                        className={`p-3 rounded-full text-white transition shadow-md ${
                            isMuted ? 'bg-rose-600 hover:bg-rose-700' : 'bg-slate-800 hover:bg-slate-700'
                        }`}
                        title={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
                    >
                        {isMuted ? '🔇' : '🎙️'}
                    </button>

                    <button
                        type="button"
                        onClick={toggleCam}
                        className={`p-3 rounded-full text-white transition shadow-md ${
                            isVideoOff ? 'bg-rose-600 hover:bg-rose-700' : 'bg-slate-800 hover:bg-slate-700'
                        }`}
                        title={isVideoOff ? 'Turn Camera On' : 'Turn Camera Off'}
                    >
                        {isVideoOff ? '🚫' : '📹'}
                    </button>

                    <Link
                        href="/patient/appointments"
                        onClick={() => {
                            sendSignal('bye', {});
                            wsRef.current?.close();
                            peerRef.current?.close();
                        }}
                        className="px-5 py-2.5 rounded-full bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition shadow-md"
                    >
                        Disconnect Call
                    </Link>
                </div>
            </div>
        </div>
    );
}
