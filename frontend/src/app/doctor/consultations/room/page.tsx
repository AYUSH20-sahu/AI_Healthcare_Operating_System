'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { api, API_BASE, telehealthApi, voiceNotesApi } from '@/lib/api';
import type { IceServerItem, RecordingMetadata } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────────────────

type CallState = 'idle' | 'connecting' | 'waiting' | 'negotiating' | 'active' | 'ended' | 'error';

interface RoomTokenResponse {
    room_id: string;
    appointment_id: string;
    peer_role: 'doctor' | 'patient';
    ws_url: string;
    ice_servers?: IceServerItem[];
}

interface TranscriptEntry {
    time: string;
    text: string;
}

// ─── Fallback ICE Configuration ───────────────────────────────────────────────

const DEFAULT_STUN_SERVERS = [
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
    const remoteStreamRef = useRef<MediaStream | null>(null);

    // WebRTC
    const peerRef = useRef<RTCPeerConnection | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const isInitiatorRef = useRef(false);

    // Horizon C: AudioContext & Ambient Scribe Pipe
    const audioContextRef = useRef<AudioContext | null>(null);
    const mixedAudioDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);
    const scribeRecorderRef = useRef<MediaRecorder | null>(null);
    const streamSequenceRef = useRef<number>(0);
    const activeVoiceNoteIdRef = useRef<string | null>(null);

    // Horizon C: Encrypted Call Recording
    const callRecorderRef = useRef<MediaRecorder | null>(null);
    const recordedBlobsRef = useRef<Blob[]>([]);
    const durationRef = useRef<number>(0);

    // UI State
    const [callState, setCallState] = useState<CallState>('idle');
    const [error, setError] = useState<string | null>(null);
    const [isMuted, setIsMuted] = useState(false);
    const [isCamOff, setIsCamOff] = useState(false);
    const [isPipMode, setIsPipMode] = useState(false);
    const [duration, setDuration] = useState(0);
    const [peerRole, setPeerRole] = useState<'doctor' | 'patient'>('patient');
    const [roomInfo, setRoomInfo] = useState<RoomTokenResponse | null>(null);
    const [iceServersUsed, setIceServersUsed] = useState<IceServerItem[]>(DEFAULT_STUN_SERVERS);

    // Horizon C UI State
    const [isScribeDrawerOpen, setIsScribeDrawerOpen] = useState(true);
    const [isScribeStreaming, setIsScribeStreaming] = useState(false);
    const [transcriptEntries, setTranscriptEntries] = useState<TranscriptEntry[]>([]);
    const [fullTranscription, setFullTranscription] = useState('');
    const [isGeneratingSOAP, setIsGeneratingSOAP] = useState(false);
    const [soapNoteDraft, setSoapNoteDraft] = useState<any | null>(null);

    // Encrypted recording UI state
    const [isRecordingEncrypted, setIsRecordingEncrypted] = useState(false);
    const [isSavingRecording, setIsSavingRecording] = useState(false);
    const [recordingMetadata, setRecordingMetadata] = useState<RecordingMetadata | null>(null);

    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const transcriptEndRef = useRef<HTMLDivElement>(null);

    // ── Start call timer ──────────────────────────────────────────────────────
    const startTimer = useCallback(() => {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => {
            setDuration(d => {
                durationRef.current = d + 1;
                return d + 1;
            });
        }, 1000);
    }, []);

    const stopTimer = useCallback(() => {
        if (timerRef.current) clearInterval(timerRef.current);
    }, []);

    // Scroll transcript down automatically
    useEffect(() => {
        transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [transcriptEntries]);

    // ── Horizon C: Institutional Mixed Audio Pipe -> Ambient Scribe ───────────
    const startAudioScribePipeline = useCallback((localStream: MediaStream, remoteStream: MediaStream) => {
        try {
            if (scribeRecorderRef.current && scribeRecorderRef.current.state !== 'inactive') {
                return;
            }

            const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
            if (!AudioCtx) {
                console.warn('AudioContext not supported on this platform');
                return;
            }

            const audioCtx = new AudioCtx();
            audioContextRef.current = audioCtx;

            const destNode = audioCtx.createMediaStreamDestination();
            mixedAudioDestRef.current = destNode;

            // Connect local doctor mic track
            if (localStream.getAudioTracks().length > 0) {
                const localSource = audioCtx.createMediaStreamSource(localStream);
                localSource.connect(destNode);
            }

            // Connect incoming remote patient audio track
            if (remoteStream.getAudioTracks().length > 0) {
                const remoteSource = audioCtx.createMediaStreamSource(remoteStream);
                remoteSource.connect(destNode);
            }

            const streamToRecord = destNode.stream.getAudioTracks().length > 0 ? destNode.stream : localStream;

            const preferredMime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : 'audio/webm';

            const scribeRecorder = new MediaRecorder(streamToRecord, { mimeType: preferredMime });
            scribeRecorderRef.current = scribeRecorder;

            scribeRecorder.ondataavailable = async (ev: BlobEvent) => {
                if (ev.data && ev.data.size > 0 && appointmentId) {
                    const currentSeq = streamSequenceRef.current++;
                    const formData = new FormData();
                    formData.append('chunk', ev.data, `chunk_${currentSeq}.webm`);
                    formData.append('sequence_number', String(currentSeq));
                    formData.append('is_final', 'false');

                    setIsScribeStreaming(true);
                    try {
                        const res = await voiceNotesApi.streamAppointmentChunk(appointmentId, formData);
                        if (res?.voice_note_id) {
                            activeVoiceNoteIdRef.current = res.voice_note_id;
                        }
                        if (res?.incremental_text && res.incremental_text.trim()) {
                            setTranscriptEntries(prev => [
                                ...prev,
                                {
                                    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                                    text: res.incremental_text.trim(),
                                }
                            ]);
                        }
                        if (res?.full_transcription) {
                            setFullTranscription(res.full_transcription);
                        }
                    } catch (err) {
                        console.warn('Scribe audio chunk streaming warning:', err);
                    } finally {
                        setIsScribeStreaming(false);
                    }
                }
            };

            // Stream chunked segments every 5000ms (5 seconds) as specified by Horizon C
            scribeRecorder.start(5000);
        } catch (err) {
            console.error('Failed to initialize Horizon C live audio scribe pipe:', err);
        }
    }, [appointmentId]);

    // ── Horizon C: Encrypted Consultation Call Recording ──────────────────────
    const startEncryptedRecording = useCallback((stream: MediaStream) => {
        try {
            if (callRecorderRef.current && callRecorderRef.current.state !== 'inactive') return;

            const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
                ? 'video/webm;codecs=vp9,opus'
                : MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
                ? 'video/webm;codecs=vp8,opus'
                : 'video/webm';

            const recorder = new MediaRecorder(stream, { mimeType: mime });
            callRecorderRef.current = recorder;
            recordedBlobsRef.current = [];

            recorder.ondataavailable = (e: BlobEvent) => {
                if (e.data && e.data.size > 0) {
                    recordedBlobsRef.current.push(e.data);
                }
            };

            recorder.onstop = async () => {
                if (recordedBlobsRef.current.length > 0 && appointmentId) {
                    setIsSavingRecording(true);
                    try {
                        const blob = new Blob(recordedBlobsRef.current, { type: 'video/webm' });
                        const formData = new FormData();
                        formData.append('file', blob, `consultation_${appointmentId}.webm`);
                        formData.append('duration_seconds', String(durationRef.current));

                        const uploadRes = await telehealthApi.uploadRecording(appointmentId, formData);
                        if (uploadRes?.metadata) {
                            setRecordingMetadata(uploadRes.metadata);
                        }
                    } catch (err) {
                        console.error('Failed to upload AES-256 encrypted recording:', err);
                    } finally {
                        setIsSavingRecording(false);
                    }
                }
            };

            recorder.start(1000);
            setIsRecordingEncrypted(true);
        } catch (err) {
            console.warn('Could not start encrypted recording:', err);
        }
    }, [appointmentId]);

    // ── Create Peer Connection with dynamic Coturn ICE Servers ────────────────
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
            const incomingStream = event.streams[0];
            remoteStreamRef.current = incomingStream;
            if (remoteVideoRef.current) {
                remoteVideoRef.current.srcObject = incomingStream;
            }
            setCallState('active');
            startTimer();

            // Horizon C: Hook incoming audio into the institutional mixed audio pipeline
            if (localStreamRef.current) {
                startAudioScribePipeline(localStreamRef.current, incomingStream);
                startEncryptedRecording(incomingStream);
            }
        };

        pc.onconnectionstatechange = () => {
            if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
                setCallState('ended');
                stopTimer();
            }
        };

        return pc;
    }, [startTimer, stopTimer, startAudioScribePipeline, startEncryptedRecording]);

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

    // ── Initialize call with dynamic Coturn ICE Servers ───────────────────────
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

            // 2. Fetch room token and Coturn ICE servers
            const tokenData = await telehealthApi.getRoomToken(appointmentId);
            setRoomInfo(tokenData);
            setPeerRole(tokenData.peer_role);

            let configuredIceServers = tokenData.ice_servers;
            if (!configuredIceServers || configuredIceServers.length === 0) {
                try {
                    const iceRes = await telehealthApi.getIceServers();
                    configuredIceServers = iceRes.ice_servers;
                } catch {
                    configuredIceServers = DEFAULT_STUN_SERVERS;
                }
            }
            setIceServersUsed(configuredIceServers);

            // 3. Create peer connection with authenticated Coturn credentials
            const pc = createPeer(configuredIceServers);
            peerRef.current = pc;
            stream.getTracks().forEach(track => pc.addTrack(track, stream));

            // 4. Connect to signalling WebSocket
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

    // ── End call & finalize media pipes ───────────────────────────────────────
    const endCall = useCallback(() => {
        // Send final signal
        sendSignal('bye', {});
        wsRef.current?.close();
        peerRef.current?.close();

        // Stop Scribe Audio Pipe
        if (scribeRecorderRef.current && scribeRecorderRef.current.state !== 'inactive') {
            scribeRecorderRef.current.stop();
        }
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => {});
        }

        // Stop Encrypted Recording and trigger save
        if (callRecorderRef.current && callRecorderRef.current.state !== 'inactive') {
            callRecorderRef.current.stop();
        }

        localStreamRef.current?.getTracks().forEach(t => t.stop());
        setCallState('ended');
        stopTimer();
    }, [sendSignal, stopTimer]);

    // ── Generate SOAP Draft from live transcription ───────────────────────────
    const handleGenerateSOAP = async () => {
        const vId = activeVoiceNoteIdRef.current;
        if (!vId) {
            alert('No active ambient scribe voice note detected yet. Please ensure consultation audio has streamed.');
            return;
        }

        setIsGeneratingSOAP(true);
        try {
            const draftRes = await voiceNotesApi.processScribe(vId, {
                chief_complaint: 'Telehealth clinical encounter',
            });
            setSoapNoteDraft(draftRes);
        } catch (err) {
            console.error('Failed to generate SOAP note draft:', err);
            alert('Failed to generate SOAP draft. STT pipeline processing in progress.');
        } finally {
            setIsGeneratingSOAP(false);
        }
    };

    // ── Media controls ────────────────────────────────────────────────────────
    const toggleMic = () => {
        localStreamRef.current?.getAudioTracks().forEach(t => { t.enabled = isMuted; });
        setIsMuted(m => !m);
    };

    const toggleCam = () => {
        localStreamRef.current?.getVideoTracks().forEach(t => { t.enabled = isCamOff; });
        setIsCamOff(c => !c);
    };

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
            if (scribeRecorderRef.current && scribeRecorderRef.current.state !== 'inactive') {
                scribeRecorderRef.current.stop();
            }
            if (callRecorderRef.current && callRecorderRef.current.state !== 'inactive') {
                callRecorderRef.current.stop();
            }
            if (audioContextRef.current) {
                audioContextRef.current.close().catch(() => {});
            }
            stopTimer();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Status labels
    const stateLabel: Record<CallState, string> = {
        idle: 'Initializing…',
        connecting: 'Connecting…',
        waiting: 'Waiting for patient to join…',
        negotiating: 'Establishing Coturn WebRTC session…',
        active: `Connected · ${formatDuration(duration)}`,
        ended: 'Call ended',
        error: 'Connection failed',
    };

    const hasCoturnRelay = iceServersUsed.some(s => {
        const u = Array.isArray(s.urls) ? s.urls.join(',') : s.urls;
        return u.includes('turn:') || u.includes('turns:');
    });

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col select-none text-slate-100">
            {/* Top Navigation & Status Bar */}
            <div className="flex items-center justify-between px-5 py-3 bg-black/60 backdrop-blur-md border-b border-slate-800/80 z-20">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <p className="text-sm font-bold text-white tracking-wide">AI-HOS Telehealth Suite</p>
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-900/60 text-blue-300 border border-blue-700/50">
                                Horizon C
                            </span>
                            {hasCoturnRelay && (
                                <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/70 text-emerald-300 border border-emerald-700/40">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                    Coturn ICE Traversal Active
                                </span>
                            )}
                            {isRecordingEncrypted && (
                                <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-950/70 text-purple-300 border border-purple-700/40">
                                    🛡️ AES-256 Vault Active
                                </span>
                            )}
                        </div>
                        <p className="text-[11px] text-slate-400">
                            {roomInfo ? `Role: ${peerRole === 'doctor' ? 'Attending Physician (Host)' : 'Patient (Guest)'} · Session ID: ${roomInfo.room_id.slice(-8)}` : 'Resolving consultation token…'}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Toggle Scribe Drawer Button */}
                    <button
                        type="button"
                        onClick={() => setIsScribeDrawerOpen(v => !v)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
                            isScribeDrawerOpen
                                ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/30'
                                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
                        }`}
                    >
                        <span>🎙️</span>
                        <span>Ambient Scribe</span>
                        {isScribeStreaming && <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />}
                    </button>

                    {/* Status pill */}
                    <div className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold ${
                        callState === 'active' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                        callState === 'ended' ? 'bg-slate-800 text-slate-400 border border-slate-700' :
                        callState === 'error' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                        'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}>
                        {callState === 'active' && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />}
                        {stateLabel[callState]}
                    </div>
                </div>
            </div>

            {/* Main Interactive Work Area */}
            <div className="flex-1 flex overflow-hidden relative">
                {/* Left/Center: Video Stage */}
                <div className="flex-1 relative bg-slate-950 overflow-hidden flex flex-col">
                    {/* Remote video (full frame) */}
                    <video
                        id="remote-video"
                        ref={remoteVideoRef}
                        autoPlay
                        playsInline
                        className={`w-full h-full object-cover transition-opacity duration-300 ${callState === 'active' ? 'opacity-100' : 'opacity-0'}`}
                    />

                    {/* Non-Active State Overlay */}
                    {callState !== 'active' && (
                        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-slate-950/90 z-10 px-4">
                            {callState === 'ended' ? (
                                <div className="text-center space-y-4 max-w-md p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl">
                                    <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-emerald-400">
                                        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                    <h2 className="text-xl font-bold text-white">Consultation Completed</h2>
                                    <p className="text-slate-400 text-xs">
                                        Total Clinical Encounter Duration: <span className="text-white font-mono">{formatDuration(duration)}</span>
                                    </p>
                                    {isSavingRecording && (
                                        <div className="p-3 rounded-xl bg-purple-950/40 border border-purple-800/40 text-xs text-purple-300 flex items-center justify-center gap-2">
                                            <div className="w-3.5 h-3.5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
                                            <span>Encrypting & persisting session recording to AES-256 vault…</span>
                                        </div>
                                    )}
                                    {recordingMetadata && (
                                        <div className="p-3 rounded-xl bg-emerald-950/50 border border-emerald-800/50 text-left text-xs text-emerald-300 space-y-1">
                                            <p className="font-semibold flex items-center gap-1.5">
                                                <span>🛡️ AES-256-GCM Vault Integrity Verified</span>
                                            </p>
                                            <p className="text-[11px] text-slate-300">File: {recordingMetadata.original_filename}</p>
                                            <p className="text-[10px] text-slate-400 font-mono break-all">SHA-256: {recordingMetadata.plaintext_sha256.slice(0, 24)}…</p>
                                        </div>
                                    )}
                                    <div className="flex items-center justify-center gap-3 pt-2">
                                        <button
                                            id="call-ended-return-btn"
                                            onClick={() => router.push('/doctor/consultations')}
                                            className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors shadow-lg shadow-blue-600/30"
                                        >
                                            Return to Consultations
                                        </button>
                                    </div>
                                </div>
                            ) : callState === 'error' ? (
                                <div className="text-center space-y-3 max-w-sm px-4 p-6 rounded-2xl bg-rose-950/40 border border-rose-800/50">
                                    <div className="w-14 h-14 rounded-full bg-rose-900/60 flex items-center justify-center mx-auto text-rose-300">
                                        <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    </div>
                                    <p className="text-white font-semibold text-sm">{error || 'Connection error'}</p>
                                    <button
                                        id="call-retry-btn"
                                        onClick={() => { setCallState('idle'); initCall(); }}
                                        className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors"
                                    >
                                        Retry Connection
                                    </button>
                                </div>
                            ) : (
                                <div className="text-center space-y-4">
                                    <div className="w-20 h-20 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto shadow-2xl">
                                        {callState === 'waiting' ? (
                                            <svg className="w-10 h-10 text-blue-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                            </svg>
                                        ) : (
                                            <div className="w-9 h-9 rounded-full border-3 border-blue-500 border-t-transparent animate-spin" />
                                        )}
                                    </div>
                                    <div>
                                        <p className="text-white font-bold text-lg">{stateLabel[callState]}</p>
                                        {callState === 'waiting' && (
                                            <p className="text-slate-400 text-xs mt-1">Waiting for remote patient peer connection rendezvous…</p>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Local Video Overlay (Doctor Self-View PiP) */}
                    <div className="absolute bottom-20 right-4 w-40 h-28 sm:w-48 sm:h-32 rounded-2xl overflow-hidden shadow-2xl border-2 border-slate-700/80 bg-slate-900 z-10">
                        <video
                            id="local-video"
                            ref={localVideoRef}
                            autoPlay
                            playsInline
                            muted
                            className={`w-full h-full object-cover ${isCamOff ? 'opacity-0' : 'opacity-100'}`}
                        />
                        {isCamOff && (
                            <div className="absolute inset-0 flex items-center justify-center bg-slate-800 text-slate-400">
                                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2zM3 3l18 18" />
                                </svg>
                            </div>
                        )}
                        <div className="absolute bottom-1.5 left-1.5 text-[10px] font-semibold bg-black/70 backdrop-blur-sm text-white px-2 py-0.5 rounded-md flex items-center gap-1">
                            <span>You (Doctor)</span>
                            {isMuted && <span className="text-rose-400 font-bold">[Muted]</span>}
                        </div>
                    </div>
                </div>

                {/* Right: Ambient Scribe Live Transcript & SOAP Copilot Panel (Horizon C) */}
                {isScribeDrawerOpen && (
                    <div className="w-80 sm:w-96 bg-slate-900/95 border-l border-slate-800 flex flex-col z-20 backdrop-blur-md">
                        {/* Drawer Header */}
                        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900">
                            <div className="flex items-center gap-2">
                                <span className="text-base">🎙️</span>
                                <div>
                                    <p className="text-xs font-bold text-white">Ambient Scribe Feed</p>
                                    <p className="text-[10px] text-slate-400">Real-Time 5s WebM Audio Ingestion</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-1.5">
                                {isScribeStreaming ? (
                                    <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">
                                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                                        Streaming
                                    </span>
                                ) : (
                                    <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                                        ● Listening
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Live Transcription Scrollable Body */}
                        <div className="flex-1 p-3 overflow-y-auto space-y-2 text-xs">
                            {transcriptEntries.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-2">
                                    <span className="text-2xl">🎧</span>
                                    <p className="font-semibold text-slate-400">Audio Pipe Initialized</p>
                                    <p className="text-[11px] leading-relaxed">
                                        Doctor and patient audio tracks are mixed into an AudioContext destination and continuously streamed to the STT scribe engine.
                                    </p>
                                </div>
                            ) : (
                                transcriptEntries.map((entry, idx) => (
                                    <div key={idx} className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/50 space-y-1">
                                        <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                                            <span>Encounter Chunk #{idx + 1}</span>
                                            <span>{entry.time}</span>
                                        </div>
                                        <p className="text-slate-200 text-xs leading-relaxed">{entry.text}</p>
                                    </div>
                                ))
                            )}
                            <div ref={transcriptEndRef} />
                        </div>

                        {/* SOAP Note Draft Preview Modal/Drawer Drawer Action */}
                        {soapNoteDraft && (
                            <div className="p-3 bg-indigo-950/40 border-t border-indigo-800/50 max-h-48 overflow-y-auto text-xs space-y-1.5">
                                <p className="font-bold text-indigo-300 flex items-center justify-between text-[11px]">
                                    <span>📋 Draft SOAP Note Generated</span>
                                    <span className="text-[10px] font-mono text-emerald-400">Confidence: {Math.round((soapNoteDraft.confidence || 0.9) * 100)}%</span>
                                </p>
                                <div className="text-[11px] text-slate-300 space-y-1 bg-slate-900/60 p-2 rounded-lg">
                                    <p><strong className="text-indigo-200">S:</strong> {soapNoteDraft.soap_note?.subjective || 'N/A'}</p>
                                    <p><strong className="text-indigo-200">O:</strong> {soapNoteDraft.soap_note?.objective || 'N/A'}</p>
                                    <p><strong className="text-indigo-200">A:</strong> {soapNoteDraft.soap_note?.assessment || 'N/A'}</p>
                                    <p><strong className="text-indigo-200">P:</strong> {soapNoteDraft.soap_note?.plan || 'N/A'}</p>
                                </div>
                            </div>
                        )}

                        {/* Footer Quick Action */}
                        <div className="p-3 border-t border-slate-800 bg-slate-900/90 space-y-2">
                            <button
                                type="button"
                                onClick={handleGenerateSOAP}
                                disabled={isGeneratingSOAP || (!activeVoiceNoteIdRef.current && transcriptEntries.length === 0)}
                                className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 disabled:text-slate-500 text-white font-semibold text-xs transition-all flex items-center justify-center gap-2 shadow-md shadow-indigo-600/30"
                            >
                                {isGeneratingSOAP ? (
                                    <>
                                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        <span>Drafting SOAP Note…</span>
                                    </>
                                ) : (
                                    <>
                                        <span>✨</span>
                                        <span>Generate Clinical SOAP Draft</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Bottom Controls Bar */}
            <div className="bg-black/80 backdrop-blur-md px-4 py-3.5 flex items-center justify-center gap-4 border-t border-slate-800/80 z-20">
                {/* Mute mic */}
                <button
                    id="call-toggle-mic"
                    type="button"
                    onClick={toggleMic}
                    disabled={callState === 'ended' || callState === 'error'}
                    title={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
                    className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
                        isMuted ? 'bg-rose-600 text-white hover:bg-rose-700' : 'bg-slate-800 text-slate-200 hover:bg-slate-700'
                    } disabled:opacity-30`}
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
                    className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
                        isCamOff ? 'bg-rose-600 text-white hover:bg-rose-700' : 'bg-slate-800 text-slate-200 hover:bg-slate-700'
                    } disabled:opacity-30`}
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        {isCamOff
                            ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2zM3 3l18 18" />
                            : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        }
                    </svg>
                </button>

                {/* Picture in Picture */}
                <button
                    id="call-pip"
                    type="button"
                    onClick={togglePip}
                    disabled={callState !== 'active'}
                    title="Picture-in-Picture"
                    className="w-11 h-11 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 flex items-center justify-center transition-colors disabled:opacity-30"
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                </button>

                {/* End call / Return button */}
                <button
                    id="call-end-btn"
                    type="button"
                    onClick={callState === 'ended' ? () => router.push('/doctor/consultations') : endCall}
                    className="px-5 h-11 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs flex items-center gap-2 transition-all shadow-lg shadow-rose-900/50"
                    title={callState === 'ended' ? 'Return to Consultations' : 'End Call & Finalize Notes'}
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
                    </svg>
                    <span>{callState === 'ended' ? 'Exit Room' : 'End Call'}</span>
                </button>
            </div>
        </div>
    );
}
