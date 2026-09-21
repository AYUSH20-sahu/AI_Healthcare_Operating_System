'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { api, API_BASE } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

type CallState = 'idle' | 'connecting' | 'waiting' | 'negotiating' | 'active' | 'ended' | 'error';

interface RoomTokenResponse {
    room_id: string;
    appointment_id: string;
    peer_role: 'doctor' | 'patient';
    ws_url: string;
}

// ─── ICE Configuration ────────────────────────────────────────────────────────

const ICE_SERVERS = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDuration(secs: number) {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function TelehealthRoomPage() {
    const { user } = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const appointmentId = searchParams.get('appointment_id');

    // Media streams
    const localVideoRef = useRef<HTMLVideoElement>(null);
    const remoteVideoRef = useRef<HTMLVideoElement>(null);
    const localStreamRef = useRef<MediaStream | null>(null);

    // WebRTC
    const peerRef = useRef<RTCPeerConnection | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const isInitiatorRef = useRef(false);

    // UI State
    const [callState, setCallState] = useState<CallState>('idle');
    const [error, setError] = useState<string | null>(null);
    const [isMuted, setIsMuted] = useState(false);
    const [isCamOff, setIsCamOff] = useState(false);
    const [isPipMode, setIsPipMode] = useState(false);
    const [duration, setDuration] = useState(0);
    const [peerRole, setPeerRole] = useState<'doctor' | 'patient'>('patient');
    const [roomInfo, setRoomInfo] = useState<RoomTokenResponse | null>(null);

    const timerRef = useRef<NodeJS.Timeout | null>(null);

    // ── Start call timer ──────────────────────────────────────────────────────
    const startTimer = useCallback(() => {
        timerRef.current = setInterval(() => setDuration(d => d + 1), 1000);
    }, []);

    const stopTimer = useCallback(() => {
        if (timerRef.current) clearInterval(timerRef.current);
    }, []);

    // ── Create Peer Connection ────────────────────────────────────────────────
    const createPeer = useCallback(() => {
        const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });

        pc.onicecandidate = (event) => {
            if (event.candidate && wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                    type: 'ice-candidate',
                    payload: event.candidate,
                }));
            }
        };

        pc.ontrack = (event) => {
            if (remoteVideoRef.current) {
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

    // ── Send signalling message ───────────────────────────────────────────────
    const sendSignal = useCallback((type: string, payload: unknown) => {
        wsRef.current?.send(JSON.stringify({ type, payload }));
    }, []);

    // ── Start Offer (initiator = doctor) ──────────────────────────────────────
    const startOffer = useCallback(async () => {
        if (!peerRef.current || !localStreamRef.current) return;
        setCallState('negotiating');
        const offer = await peerRef.current.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: true });
        await peerRef.current.setLocalDescription(offer);
        sendSignal('offer', offer);
    }, [sendSignal]);

    // ── Handle incoming signalling message ────────────────────────────────────
    const handleSignal = useCallback(async (message: { type: string; payload: unknown }) => {
        const pc = peerRef.current;
        if (!pc) return;

        switch (message.type) {
            case 'room_joined':
                isInitiatorRef.current = (message.payload as { is_initiator: boolean }).is_initiator;
                break;

            case 'peer_joined':
                // Second peer joined; if I'm the initiator, create and send offer
                if (isInitiatorRef.current) {
                    await startOffer();
                }
                setCallState('negotiating');
                break;

            case 'offer':
                await pc.setRemoteDescription(new RTCSessionDescription(message.payload as RTCSessionDescriptionInit));
                const answer = await pc.createAnswer();
                await pc.setLocalDescription(answer);
                sendSignal('answer', answer);
                setCallState('negotiating');
                break;

            case 'answer':
                await pc.setRemoteDescription(new RTCSessionDescription(message.payload as RTCSessionDescriptionInit));
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
    }, [startOffer, sendSignal, stopTimer]);

    // ── Initialize call ───────────────────────────────────────────────────────
    const initCall = useCallback(async () => {
        if (!appointmentId) {
            setError('No appointment ID provided.');
            setCallState('error');
            return;
        }

        setCallState('connecting');
        setError(null);

        try {
            // 1. Get local media
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localStreamRef.current = stream;
            if (localVideoRef.current) {
                localVideoRef.current.srcObject = stream;
            }

            // 2. Fetch room token from backend
            const tokenData = await api.get<RoomTokenResponse>(`/telehealth/room/${appointmentId}/token`);
            setRoomInfo(tokenData);
            setPeerRole(tokenData.peer_role);

            // 3. Create peer connection and add local tracks
            const pc = createPeer();
            peerRef.current = pc;
            stream.getTracks().forEach(track => pc.addTrack(track, stream));

            // 4. Connect to signalling WebSocket
            const wsBase = API_BASE.replace(/^http/, 'ws').replace('/api/v1', '');
            const token = localStorage.getItem('access_token');
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
                setError('Signalling connection failed. Check your network.');
                setCallState('error');
            };
            ws.onclose = () => {
                if (callState !== 'ended' && callState !== 'error') {
                    setCallState('ended');
                    stopTimer();
                }
            };

        } catch (err: unknown) {
            if (err instanceof DOMException && err.name === 'NotAllowedError') {
                setError('Camera/microphone access was denied. Please allow permissions and try again.');
            } else {
                setError(err instanceof Error ? err.message : 'Failed to start call.');
            }
            setCallState('error');
        }
    }, [appointmentId, createPeer, handleSignal, callState, stopTimer]);

    // ── End call ──────────────────────────────────────────────────────────────
    const endCall = useCallback(() => {
        sendSignal('bye', {});
        wsRef.current?.close();
        peerRef.current?.close();
        localStreamRef.current?.getTracks().forEach(t => t.stop());
        setCallState('ended');
        stopTimer();
    }, [sendSignal, stopTimer]);

    // ── Toggle mic ────────────────────────────────────────────────────────────
    const toggleMic = () => {
        localStreamRef.current?.getAudioTracks().forEach(t => { t.enabled = isMuted; });
        setIsMuted(m => !m);
    };

    // ── Toggle camera ─────────────────────────────────────────────────────────
    const toggleCam = () => {
        localStreamRef.current?.getVideoTracks().forEach(t => { t.enabled = isCamOff; });
        setIsCamOff(c => !c);
    };

    // ── Picture-in-Picture ────────────────────────────────────────────────────
    const togglePip = async () => {
        if (!remoteVideoRef.current) return;
        try {
            if (document.pictureInPictureElement) {
                await document.exitPictureInPicture();
                setIsPipMode(false);
            } else {
                await remoteVideoRef.current.requestPictureInPicture();
                setIsPipMode(true);
            }
        } catch { /* PiP not supported */ }
    };

    // Auto-init on mount
    useEffect(() => {
        initCall();
        return () => {
            localStreamRef.current?.getTracks().forEach(t => t.stop());
            wsRef.current?.close();
            peerRef.current?.close();
            stopTimer();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Status labels ─────────────────────────────────────────────────────────
    const stateLabel: Record<CallState, string> = {
        idle: 'Initializing…',
        connecting: 'Connecting…',
        waiting: 'Waiting for other party to join…',
        negotiating: 'Establishing secure call…',
        active: `Connected · ${formatDuration(duration)}`,
        ended: 'Call ended',
        error: 'Connection failed',
    };

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col select-none">
            {/* Top bar */}
            <div className="flex items-center justify-between px-5 py-3 bg-black/40 backdrop-blur-sm z-10">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-white">AI-HOS Telehealth Room</p>
                        <p className="text-[10px] text-slate-400">
                            {roomInfo ? `As: ${peerRole === 'doctor' ? 'Doctor (Host)' : 'Patient (Guest)'} · Room: ${roomInfo.room_id.slice(-8)}` : '…'}
                        </p>
                    </div>
                </div>

                {/* Status pill */}
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${
                    callState === 'active' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                    callState === 'ended' ? 'bg-slate-700 text-slate-400' :
                    callState === 'error' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                    'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                }`}>
                    {callState === 'active' && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />}
                    {stateLabel[callState]}
                </div>
            </div>

            {/* Video area */}
            <div className="flex-1 relative bg-slate-900 overflow-hidden">
                {/* Remote video (full frame) */}
                <video
                    id="remote-video"
                    ref={remoteVideoRef}
                    autoPlay
                    playsInline
                    className={`w-full h-full object-cover transition-opacity duration-300 ${callState === 'active' ? 'opacity-100' : 'opacity-0'}`}
                />

                {/* Waiting / state overlay */}
                {callState !== 'active' && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                        {callState === 'ended' ? (
                            <div className="text-center space-y-3">
                                <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto">
                                    <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
                                    </svg>
                                </div>
                                <p className="text-white font-semibold text-lg">Call Ended</p>
                                <p className="text-slate-400 text-sm">Duration: {formatDuration(duration)}</p>
                                <button
                                    id="call-ended-return-btn"
                                    onClick={() => router.back()}
                                    className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors"
                                >
                                    Return to Consultations
                                </button>
                            </div>
                        ) : callState === 'error' ? (
                            <div className="text-center space-y-3 max-w-sm px-4">
                                <div className="w-16 h-16 rounded-full bg-rose-900/40 flex items-center justify-center mx-auto">
                                    <svg className="w-8 h-8 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </div>
                                <p className="text-white font-semibold">{error || 'Connection error'}</p>
                                <button
                                    id="call-retry-btn"
                                    onClick={() => { setCallState('idle'); initCall(); }}
                                    className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors"
                                >
                                    Retry
                                </button>
                            </div>
                        ) : (
                            <div className="text-center space-y-4">
                                <div className="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center mx-auto">
                                    {callState === 'waiting' ? (
                                        <svg className="w-10 h-10 text-slate-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                        </svg>
                                    ) : (
                                        <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
                                    )}
                                </div>
                                <div>
                                    <p className="text-white font-semibold text-lg">{stateLabel[callState]}</p>
                                    {callState === 'waiting' && (
                                        <p className="text-slate-400 text-sm mt-1">Share your appointment link or wait for the other party</p>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Local video (PiP overlay — bottom right) */}
                <div className="absolute bottom-20 right-4 w-36 h-24 sm:w-44 sm:h-28 rounded-xl overflow-hidden shadow-2xl border-2 border-slate-700 bg-slate-800 z-10">
                    <video
                        id="local-video"
                        ref={localVideoRef}
                        autoPlay
                        playsInline
                        muted
                        className={`w-full h-full object-cover ${isCamOff ? 'opacity-0' : 'opacity-100'}`}
                    />
                    {isCamOff && (
                        <div className="absolute inset-0 flex items-center justify-center bg-slate-700">
                            <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2zM3 3l18 18" />
                            </svg>
                        </div>
                    )}
                    <div className="absolute bottom-1 left-1 text-[9px] bg-black/60 text-white px-1 rounded">
                        You {isMuted && '(Muted)'}
                    </div>
                </div>
            </div>

            {/* Controls bar */}
            <div className="bg-black/70 backdrop-blur-md px-4 py-4 flex items-center justify-center gap-4">
                {/* Mute mic */}
                <button
                    id="call-toggle-mic"
                    type="button"
                    onClick={toggleMic}
                    disabled={callState === 'ended' || callState === 'error'}
                    title={isMuted ? 'Unmute' : 'Mute'}
                    className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
                        isMuted ? 'bg-rose-600 hover:bg-rose-700' : 'bg-slate-700 hover:bg-slate-600'
                    } disabled:opacity-30`}
                >
                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        {isMuted
                            ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15zM17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                            : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
                        }
                    </svg>
                </button>

                {/* Toggle camera */}
                <button
                    id="call-toggle-cam"
                    type="button"
                    onClick={toggleCam}
                    disabled={callState === 'ended' || callState === 'error'}
                    title={isCamOff ? 'Turn on camera' : 'Turn off camera'}
                    className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
                        isCamOff ? 'bg-rose-600 hover:bg-rose-700' : 'bg-slate-700 hover:bg-slate-600'
                    } disabled:opacity-30`}
                >
                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        {isCamOff
                            ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2zM3 3l18 18" />
                            : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        }
                    </svg>
                </button>

                {/* PiP */}
                <button
                    id="call-pip"
                    type="button"
                    onClick={togglePip}
                    disabled={callState !== 'active'}
                    title="Picture-in-Picture"
                    className="w-12 h-12 rounded-full bg-slate-700 hover:bg-slate-600 flex items-center justify-center transition-colors disabled:opacity-30"
                >
                    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                </button>

                {/* End call */}
                <button
                    id="call-end-btn"
                    type="button"
                    onClick={callState === 'ended' ? () => router.back() : endCall}
                    className="w-16 h-12 rounded-full bg-rose-600 hover:bg-rose-700 flex items-center justify-center transition-colors shadow-lg shadow-rose-900/50"
                    title={callState === 'ended' ? 'Return' : 'End call'}
                >
                    <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
