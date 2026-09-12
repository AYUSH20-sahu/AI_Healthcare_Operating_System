'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
    intakeApi,
    IntakeSession,
    IntakeMessageItem,
    StructuredSymptoms,
    voiceApi,
    VoiceLanguageDetail,
} from '@/lib/api';

const QUICK_PROMPTS = [
    "Severe throbbing headache for the past 2 days",
    "Persistent dry cough with mild fatigue",
    "Sharp lower back pain worsening when bending",
    "Upset stomach and nausea since yesterday evening",
];

interface LanguageOption {
    code: string;
    name: string;
    nativeName: string;
    status: 'validated' | 'experimental';
    webSpeechLang: string;
}

const SUPPORTED_LANGUAGES: LanguageOption[] = [
    { code: 'en', name: 'English', nativeName: 'English', status: 'validated', webSpeechLang: 'en-US' },
    { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', status: 'validated', webSpeechLang: 'hi-IN' },
    { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', status: 'experimental', webSpeechLang: 'ta-IN' },
    { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', status: 'experimental', webSpeechLang: 'te-IN' },
    { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', status: 'experimental', webSpeechLang: 'bn-IN' },
    { code: 'es', name: 'Spanish', nativeName: 'Español', status: 'experimental', webSpeechLang: 'es-ES' },
];

export default function PatientIntakePage() {
    const [session, setSession] = useState<IntakeSession | null>(null);
    const [messages, setMessages] = useState<IntakeMessageItem[]>([]);
    const [structuredSymptoms, setStructuredSymptoms] = useState<StructuredSymptoms | null>(null);
    const [aiConfidence, setAiConfidence] = useState<number | null>(null);
    const [basis, setBasis] = useState<string | null>(null);
    const [inputText, setInputText] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isSending, setIsSending] = useState(false);
    const [isCompleting, setIsCompleting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Multilingual & Voice Intake State (Milestone U-19)
    const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [micDenied, setMicDenied] = useState(false);
    const [autoPlaySpeech, setAutoPlaySpeech] = useState(true);
    const [speechRate, setSpeechRate] = useState<number>(1.0);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [audioFallbackNotice, setAudioFallbackNotice] = useState<string | null>(null);
    const [currentAudioElement, setCurrentAudioElement] = useState<HTMLAudioElement | null>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isSending]);

    // Load active session or create initial one
    useEffect(() => {
        loadSession();
        return () => {
            stopSpeaking();
            if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
        };
    }, []);

    const loadSession = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const active = await intakeApi.getActiveSession();
            if (active && active.session_id) {
                setSession(active);
                setMessages(active.messages || []);
                setStructuredSymptoms(active.structured_symptoms || null);
                setAiConfidence(active.ai_confidence ?? null);
                setBasis(active.basis || null);
            } else {
                await handleStartNewSession();
            }
        } catch (err: any) {
            if (err?.status === 404 || err?.message?.includes('404')) {
                await handleStartNewSession();
            } else {
                console.error('Failed to load active intake session:', err);
                setError('Unable to load active intake session. Starting a new session...');
                await handleStartNewSession();
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleStartNewSession = async (initialMsg?: string) => {
        setIsLoading(true);
        setError(null);
        try {
            const newSession = await intakeApi.createSession(initialMsg);
            setSession(newSession);
            setMessages(newSession.messages || []);
            setStructuredSymptoms(newSession.structured_symptoms || null);
            setAiConfidence(newSession.ai_confidence ?? null);
            setBasis(newSession.basis || null);
        } catch (err: any) {
            console.error('Failed to create intake session:', err);
            setError(err?.message || 'Failed to start intake session. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    // Text Message Submission
    const handleSendMessage = async (textToSend?: string) => {
        const text = (textToSend || inputText).trim();
        if (!text || isSending) return;

        if (!session) {
            await handleStartNewSession(text);
            setInputText('');
            return;
        }

        if (session.status === 'completed') {
            setError('This session is completed. Please start a new intake session.');
            return;
        }

        const clientTimestamp = new Date().toISOString();
        const optimisticMsg: IntakeMessageItem = {
            role: 'patient',
            content: text,
            timestamp: clientTimestamp,
        };

        setMessages((prev) => [...prev, optimisticMsg]);
        setInputText('');
        setIsSending(true);
        setError(null);

        try {
            const res = await intakeApi.sendMessage(session.session_id, text);
            const assistantMsg: IntakeMessageItem = {
                role: 'assistant',
                content: res.reply,
                timestamp: new Date().toISOString(),
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStructuredSymptoms(res.structured_symptoms);
            setAiConfidence(res.ai_confidence);
            setBasis(res.basis || null);

            if (res.is_complete || res.status === 'completed') {
                setSession((prev) => prev ? { ...prev, status: 'completed' } : null);
            }

            if (autoPlaySpeech) {
                playSpokenResponse(res.reply);
            }
        } catch (err: any) {
            console.error('Failed to send message:', err);
            setError(err?.message || 'Failed to process message. Please retry.');
        } finally {
            setIsSending(false);
            if (textareaRef.current) {
                textareaRef.current.focus();
            }
        }
    };

    // Voice Message Recording & Submission (Milestone U-19)
    const startRecording = async () => {
        setMicDenied(false);
        setError(null);
        audioChunksRef.current = [];

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                stream.getTracks().forEach((track) => track.stop());
                if (audioBlob.size > 0) {
                    await handleSendVoiceMessage(audioBlob);
                }
            };

            mediaRecorder.start(250); // Collect in slices
            setIsRecording(true);
            setRecordingTime(0);

            recordingTimerRef.current = setInterval(() => {
                setRecordingTime((prev) => prev + 1);
            }, 1000);
        } catch (err: any) {
            console.warn('Microphone permission denied or unsupported:', err);
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                setMicDenied(true);
            } else {
                setError('Could not access microphone. Please check your browser audio settings.');
            }
            setIsRecording(false);
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
        if (recordingTimerRef.current) {
            clearInterval(recordingTimerRef.current);
            recordingTimerRef.current = null;
        }
    };

    const cancelRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.onstop = null; // Prevent dispatch
            mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
        if (recordingTimerRef.current) {
            clearInterval(recordingTimerRef.current);
            recordingTimerRef.current = null;
        }
        audioChunksRef.current = [];
        setRecordingTime(0);
    };

    const handleSendVoiceMessage = async (audioBlob: Blob) => {
        if (!session) return;
        setIsSending(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', audioBlob, 'intake_patient_speech.webm');
        formData.append('language', selectedLanguage);
        formData.append('synthesize_reply', 'true');

        try {
            const res = await intakeApi.sendVoiceMessage(session.session_id, formData);

            // Append patient transcribed voice turn
            const userVoiceMsg: IntakeMessageItem = {
                role: 'patient',
                content: res.transcription || '[Voice input]',
                timestamp: new Date().toISOString(),
            };

            // Append assistant turn
            const assistantMsg: IntakeMessageItem = {
                role: 'assistant',
                content: res.reply,
                timestamp: new Date().toISOString(),
            };

            setMessages((prev) => [...prev, userVoiceMsg, assistantMsg]);
            if (res.structured_symptoms) setStructuredSymptoms(res.structured_symptoms);
            if (res.ai_confidence !== null && res.ai_confidence !== undefined) {
                setAiConfidence(res.ai_confidence);
            }
            if (res.basis) setBasis(res.basis);

            if (res.is_complete) {
                setSession((prev) => prev ? { ...prev, status: 'completed' } : null);
            }

            // Speak assistant reply
            if (autoPlaySpeech && res.reply) {
                playSpokenResponse(res.reply, res.audio_base64, res.tts_provider);
            }
        } catch (err: any) {
            console.error('Voice intake processing error:', err);
            setError(err?.message || 'Speech-to-text processing failed. Please type your message below.');
        } finally {
            setIsSending(false);
            setRecordingTime(0);
        }
    };

    // Spoken Audio Output (ElevenLabs or Browser Web Speech API Fallback)
    const playSpokenResponse = (text: string, audioBase64?: string | null, providerName?: string) => {
        stopSpeaking();

        // 1. Try playing synthesized ElevenLabs audio buffer if available
        if (audioBase64) {
            try {
                const audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
                audio.playbackRate = speechRate;
                audio.onplay = () => setIsSpeaking(true);
                audio.onended = () => setIsSpeaking(false);
                audio.onerror = () => {
                    console.warn('Backend audio playback error, escalating to Web Speech API fallback.');
                    playWebSpeechFallback(text);
                };
                setCurrentAudioElement(audio);
                audio.play();
                setAudioFallbackNotice(null);
                return;
            } catch (err) {
                console.warn('Audio tag failed, falling back to Web Speech API:', err);
            }
        }

        // 2. Fallback to Browser Web Speech API
        playWebSpeechFallback(text);
    };

    const playWebSpeechFallback = (text: string) => {
        if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
            console.warn('Browser does not support Web Speech API.');
            return;
        }

        const langMeta = SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage);
        const langTag = langMeta?.webSpeechLang || 'en-US';

        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = langTag;
        utterance.rate = speechRate;

        utterance.onstart = () => {
            setIsSpeaking(true);
            setAudioFallbackNotice('Web Speech API fallback active');
        };
        utterance.onend = () => {
            setIsSpeaking(false);
            setAudioFallbackNotice(null);
        };
        utterance.onerror = (e) => {
            console.warn('Web Speech synthesis error:', e);
            setIsSpeaking(false);
        };

        window.speechSynthesis.speak(utterance);
    };

    const stopSpeaking = () => {
        if (currentAudioElement) {
            currentAudioElement.pause();
            currentAudioElement.currentTime = 0;
            setCurrentAudioElement(null);
        }
        if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
        setIsSpeaking(false);
        setAudioFallbackNotice(null);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    const handleCompleteSession = async () => {
        if (!session) return;
        setIsCompleting(true);
        try {
            const updated = await intakeApi.completeSession(session.session_id);
            setSession(updated);
            setStructuredSymptoms(updated.structured_symptoms || structuredSymptoms);
        } catch (err: any) {
            console.error('Failed to complete session:', err);
            setError(err?.message || 'Failed to finalize session.');
        } finally {
            setIsCompleting(false);
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const isSessionComplete = session?.status === 'completed';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/60">
                            Milestone U-19
                        </span>
                        <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300">
                            Multilingual Voice Intake
                        </span>
                        <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full ${
                            isSessionComplete
                                ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                                : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                        }`}>
                            {isSessionComplete ? 'Intake Finalized' : 'Active Symptom Collection'}
                        </span>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                        AI Patient Intake & Voice Clarifier
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Multilingual voice and text conversational triage powered by Whisper STT & ElevenLabs TTS.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => handleStartNewSession()}
                        disabled={isLoading || isRecording}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-medium rounded-lg text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 transition shadow-sm"
                    >
                        <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Start Fresh Intake
                    </button>
                    {!isSessionComplete && (
                        <button
                            onClick={handleCompleteSession}
                            disabled={isCompleting || messages.length < 2 || isRecording}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-medium rounded-lg text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition shadow-sm"
                        >
                            {isCompleting ? 'Finalizing...' : 'Complete & Structure'}
                        </button>
                    )}
                </div>
            </div>

            {/* AI Safety Banner */}
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 text-amber-900 dark:text-amber-200 flex items-start gap-3 shadow-sm">
                <div className="p-1 rounded-md bg-amber-200 dark:bg-amber-800/50 text-amber-800 dark:text-amber-100 flex-shrink-0 mt-0.5">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <div className="text-xs sm:text-sm leading-relaxed">
                    <span className="font-semibold">Safety & Non-Diagnostic Notice:</span> This AI assistant only gathers and clarifies symptoms for review by your doctor. It does <span className="underline font-semibold">not</span> provide a medical diagnosis or prescribe medications. If you are experiencing acute chest pain, shortness of breath, severe bleeding, or a medical emergency, please call <strong>911 / 112</strong> immediately.
                </div>
            </div>

            {/* Microphone Permission Blocked Banner */}
            {micDenied && (
                <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-900 dark:text-rose-200 flex items-start justify-between gap-3 shadow-sm animate-fadeIn">
                    <div className="flex items-start gap-3">
                        <div className="p-1 rounded-md bg-rose-200 dark:bg-rose-800/50 text-rose-800 dark:text-rose-100 flex-shrink-0 mt-0.5">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                            </svg>
                        </div>
                        <div className="text-xs sm:text-sm">
                            <span className="font-semibold">Microphone Access Denied:</span> Your browser blocked microphone permissions. To speak with the AI assistant, click the permissions lock icon in your browser address bar and choose <strong>"Allow Microphone"</strong>, or continue typing in the text box below.
                        </div>
                    </div>
                    <button
                        onClick={() => setMicDenied(false)}
                        className="text-xs font-medium px-2.5 py-1 rounded bg-rose-100 dark:bg-rose-900/60 text-rose-700 dark:text-rose-300 hover:bg-rose-200 transition flex-shrink-0"
                    >
                        Dismiss
                    </button>
                </div>
            )}

            {error && (
                <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs sm:text-sm text-rose-700 dark:text-rose-300 flex items-center justify-between">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700 font-bold ml-2">✕</button>
                </div>
            )}

            {/* Split Screen Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                
                {/* Left Column: Conversational Chat Interface (7 cols) */}
                <div className="lg:col-span-7 flex flex-col bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden h-[680px]">
                    
                    {/* Chat & Multilingual Control Bar */}
                    <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/40 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-cyan-600 text-white flex items-center justify-center font-bold text-xs shadow-inner">
                                AI
                            </div>
                            <div>
                                <div className="flex items-center gap-1.5">
                                    <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                                        Intake Assistant
                                    </h2>
                                    {isSpeaking && (
                                        <span className="flex items-center gap-1 text-[10px] text-cyan-600 dark:text-cyan-400 font-medium animate-pulse">
                                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM14.657 2.929a1 1 0 011.414 0A9.972 9.972 0 0119 10a9.972 9.972 0 01-2.929 7.071 1 1 0 01-1.414-1.414A7.971 7.971 0 0017 10c0-2.21-.894-4.208-2.343-5.657a1 1 0 010-1.414zm-2.829 2.828a1 1 0 011.415 0A5.983 5.983 0 0115 10a5.984 5.984 0 01-1.757 4.243 1 1 0 01-1.415-1.415A3.984 3.984 0 0013 10a3.983 3.983 0 00-1.172-2.828 1 1 0 010-1.415z" clipRule="evenodd" />
                                            </svg>
                                            Speaking...
                                        </span>
                                    )}
                                </div>
                                <p className="text-[11px] text-slate-400">
                                    Provider adapter: Groq Whisper STT + ElevenLabs TTS
                                </p>
                            </div>
                        </div>

                        {/* Controls Toolbar: Language & Audio Speed */}
                        <div className="flex items-center gap-2">
                            {/* Language Selector */}
                            <div className="flex items-center gap-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 shadow-sm">
                                <label htmlFor="language-select" className="text-[11px] font-medium text-slate-500">
                                    Lang:
                                </label>
                                <select
                                    id="language-select"
                                    value={selectedLanguage}
                                    onChange={(e) => setSelectedLanguage(e.target.value)}
                                    aria-label="Select Intake Language"
                                    className="bg-transparent text-xs font-semibold text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
                                >
                                    <optgroup label="Validated Languages">
                                        <option value="en">English (en)</option>
                                        <option value="hi">हिन्दी (hi)</option>
                                    </optgroup>
                                    <optgroup label="Experimental Languages">
                                        <option value="ta">தமிழ் (ta)</option>
                                        <option value="te">తెలుగు (te)</option>
                                        <option value="bn">বাংলা (bn)</option>
                                        <option value="es">Español (es)</option>
                                    </optgroup>
                                </select>
                                <span className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                    SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage)?.status === 'validated'
                                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300'
                                        : 'bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300'
                                }`}>
                                    {SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage)?.status}
                                </span>
                            </div>

                            {/* Auto-Play Speech Toggle */}
                            <button
                                type="button"
                                onClick={() => setAutoPlaySpeech(!autoPlaySpeech)}
                                title={autoPlaySpeech ? 'Auto-play speech enabled' : 'Auto-play speech disabled'}
                                aria-label="Toggle auto-play speech"
                                className={`p-1.5 rounded-lg border text-xs transition ${
                                    autoPlaySpeech
                                        ? 'bg-cyan-50 dark:bg-cyan-950/50 border-cyan-300 text-cyan-700 dark:text-cyan-300'
                                        : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-400'
                                }`}
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                                </svg>
                            </button>

                            {/* Speech Speed Selector */}
                            <select
                                value={speechRate}
                                onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                                aria-label="Speech rate"
                                className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-[11px] font-mono text-slate-600 dark:text-slate-300 focus:outline-none"
                            >
                                <option value={0.75}>0.75x</option>
                                <option value={1.0}>1.0x</option>
                                <option value={1.25}>1.25x</option>
                            </select>

                            {/* Stop Speech Button */}
                            {isSpeaking && (
                                <button
                                    onClick={stopSpeaking}
                                    className="px-2 py-1 rounded-lg bg-rose-100 dark:bg-rose-900/60 text-rose-700 dark:text-rose-300 text-[11px] font-semibold hover:bg-rose-200 transition"
                                >
                                    Stop Audio
                                </button>
                            )}
                        </div>
                    </div>

                    {audioFallbackNotice && (
                        <div className="px-4 py-1.5 bg-blue-50 dark:bg-blue-950/40 border-b border-blue-200 dark:border-blue-900 text-[11px] text-blue-700 dark:text-blue-300 flex items-center justify-between">
                            <span>Notice: {audioFallbackNotice}</span>
                            <button onClick={() => setAudioFallbackNotice(null)} className="text-xs">✕</button>
                        </div>
                    )}

                    {/* Messages Scroll Area */}
                    <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
                        {isLoading ? (
                            <div className="flex items-center justify-center h-full text-slate-400 text-sm gap-2">
                                <svg className="animate-spin w-5 h-5 text-cyan-600" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                                Loading intake session...
                            </div>
                        ) : messages.length === 0 ? (
                            <div className="text-center py-12 text-slate-400 text-sm">
                                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400">
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                                    </svg>
                                </div>
                                <p className="font-medium text-slate-600 dark:text-slate-300">Ready for your intake consultation.</p>
                                <p className="text-xs text-slate-400 mt-1">Tap the microphone below to speak or select a quick prompt.</p>
                            </div>
                        ) : (
                            messages.map((msg, index) => {
                                const isUser = msg.role === 'patient' || msg.role === 'user';
                                return (
                                    <div
                                        key={index}
                                        className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                                    >
                                        <div
                                            className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 shadow-sm ${
                                                isUser
                                                    ? 'bg-indigo-600 text-white'
                                                    : 'bg-cyan-600 text-white'
                                            }`}
                                        >
                                            {isUser ? 'You' : 'AI'}
                                        </div>

                                        <div
                                            className={`max-w-[82%] sm:max-w-[75%] rounded-2xl px-4 py-3 text-xs sm:text-sm leading-relaxed ${
                                                isUser
                                                    ? 'bg-indigo-600 text-white rounded-tr-none'
                                                    : 'bg-slate-100 dark:bg-slate-800/90 text-slate-800 dark:text-slate-100 rounded-tl-none border border-slate-200/60 dark:border-slate-700/60'
                                            }`}
                                        >
                                            <p className="whitespace-pre-wrap">{msg.content}</p>
                                            
                                            <div className="flex items-center justify-between mt-2 pt-1 border-t border-slate-200/30">
                                                {!isUser ? (
                                                    <button
                                                        type="button"
                                                        onClick={() => playSpokenResponse(msg.content)}
                                                        className="inline-flex items-center gap-1 text-[11px] text-cyan-600 dark:text-cyan-400 hover:underline"
                                                    >
                                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                        </svg>
                                                        Listen
                                                    </button>
                                                ) : (
                                                    <span className="text-[10px] text-indigo-200">Patient Response</span>
                                                )}

                                                <span
                                                    className={`text-[10px] ${
                                                        isUser ? 'text-indigo-200' : 'text-slate-400'
                                                    }`}
                                                >
                                                    {new Date(msg.timestamp).toLocaleTimeString([], {
                                                        hour: '2-digit',
                                                        minute: '2-digit',
                                                    })}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}

                        {isSending && (
                            <div className="flex items-start gap-3">
                                <div className="w-8 h-8 rounded-full bg-cyan-600 text-white flex items-center justify-center text-xs font-semibold flex-shrink-0 shadow-sm">
                                    AI
                                </div>
                                <div className="rounded-2xl rounded-tl-none px-4 py-3 bg-slate-100 dark:bg-slate-800 text-slate-500 text-xs flex items-center gap-2">
                                    <div className="flex space-x-1">
                                        <div className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                        <div className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                        <div className="w-2 h-2 bg-cyan-500 rounded-full animate-bounce"></div>
                                    </div>
                                    <span>Processing dialogue & structuring clinical symptoms...</span>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Quick suggestion chips */}
                    {!isSessionComplete && !isRecording && (
                        <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 overflow-x-auto flex gap-2 no-scrollbar">
                            <span className="text-[11px] font-medium text-slate-400 self-center whitespace-nowrap">
                                Suggestions:
                            </span>
                            {QUICK_PROMPTS.map((prompt, idx) => (
                                <button
                                    key={idx}
                                    type="button"
                                    onClick={() => handleSendMessage(prompt)}
                                    disabled={isSending}
                                    className="text-[11px] whitespace-nowrap px-2.5 py-1 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-cyan-500 hover:text-cyan-600 dark:hover:text-cyan-400 transition"
                                >
                                    {prompt}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Input & Voice Recording Controls */}
                    <div className="p-3.5 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                        {isSessionComplete ? (
                            <div className="p-3 text-center rounded-xl bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-600 dark:text-slate-400">
                                This intake session has been finalized. You can review your structured symptoms on the right or book a visit with your doctor.
                            </div>
                        ) : isRecording ? (
                            /* Live Audio Recording State */
                            <div className="flex items-center justify-between p-2 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 animate-fadeIn">
                                <div className="flex items-center gap-3">
                                    <div className="relative flex items-center justify-center">
                                        <div className="w-3 h-3 rounded-full bg-rose-600 animate-ping absolute"></div>
                                        <div className="w-3 h-3 rounded-full bg-rose-600 relative"></div>
                                    </div>
                                    <div>
                                        <div className="text-xs font-bold text-rose-700 dark:text-rose-300">
                                            Recording Patient Audio ({formatTime(recordingTime)})
                                        </div>
                                        <div className="text-[10px] text-rose-500">
                                            Speak clearly in {SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage)?.name}...
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={cancelRecording}
                                        className="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 transition"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="button"
                                        onClick={stopRecording}
                                        className="px-3.5 py-1.5 text-xs font-semibold rounded-lg text-white bg-rose-600 hover:bg-rose-700 transition shadow-sm flex items-center gap-1.5"
                                    >
                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
                                        </svg>
                                        Done & Send
                                    </button>
                                </div>
                            </div>
                        ) : (
                            /* Regular Text + Voice Mic Launch Controls */
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    handleSendMessage();
                                }}
                                className="flex items-center gap-2"
                            >
                                <button
                                    type="button"
                                    onClick={startRecording}
                                    disabled={isSending}
                                    title="Speak your symptoms (Whisper STT)"
                                    aria-label="Record voice symptom intake"
                                    className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-cyan-50 dark:hover:bg-cyan-950 hover:text-cyan-600 dark:hover:text-cyan-400 border border-slate-200 dark:border-slate-700 transition flex-shrink-0"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                                    </svg>
                                </button>

                                <textarea
                                    ref={textareaRef}
                                    rows={1}
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    disabled={isSending}
                                    placeholder={`Type symptoms or tap mic to speak in ${SUPPORTED_LANGUAGES.find((l) => l.code === selectedLanguage)?.name}...`}
                                    className="flex-1 resize-none rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition"
                                />

                                <button
                                    type="submit"
                                    disabled={!inputText.trim() || isSending}
                                    className="p-2.5 rounded-xl bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-40 disabled:cursor-not-allowed transition shadow-sm flex-shrink-0"
                                    title="Send message"
                                    aria-label="Send message"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                    </svg>
                                </button>
                            </form>
                        )}
                    </div>
                </div>

                {/* Right Column: Live Structured Symptom Card (5 cols) */}
                <div className="lg:col-span-5 space-y-5">
                    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
                        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                            <div className="flex items-center gap-2">
                                <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400">
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </div>
                                <h3 className="font-semibold text-sm sm:text-base text-slate-800 dark:text-slate-100">
                                    Structured Symptoms
                                </h3>
                            </div>
                            <span className="text-[11px] font-mono text-slate-400">
                                Real-time Extraction
                            </span>
                        </div>

                        {structuredSymptoms ? (
                            <div className="space-y-4 text-xs sm:text-sm">
                                {/* Chief Complaint */}
                                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60">
                                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                                        Chief Complaint
                                    </div>
                                    <div className="text-slate-800 dark:text-slate-200 font-medium">
                                        {structuredSymptoms.chief_complaint || 'Pending clarification...'}
                                    </div>
                                </div>

                                {/* Duration & Severity */}
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60">
                                        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                                            Duration
                                        </div>
                                        <div className="text-slate-800 dark:text-slate-200 font-medium">
                                            {structuredSymptoms.duration || 'Not specified'}
                                        </div>
                                    </div>
                                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60">
                                        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                                            Severity (1-10)
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-slate-800 dark:text-slate-200 font-bold">
                                                {structuredSymptoms.severity !== null && structuredSymptoms.severity !== undefined
                                                    ? `${structuredSymptoms.severity}/10`
                                                    : 'Not rated'}
                                            </span>
                                            {structuredSymptoms.severity && (
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                                    structuredSymptoms.severity >= 7
                                                        ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/60 dark:text-rose-300'
                                                        : structuredSymptoms.severity >= 4
                                                        ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300'
                                                        : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300'
                                                }`}>
                                                    {structuredSymptoms.severity >= 7 ? 'High' : structuredSymptoms.severity >= 4 ? 'Moderate' : 'Mild'}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Associated Symptoms */}
                                <div>
                                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                                        Associated Symptoms
                                    </div>
                                    {structuredSymptoms.associated_symptoms && structuredSymptoms.associated_symptoms.length > 0 ? (
                                        <div className="flex flex-wrap gap-1.5">
                                            {structuredSymptoms.associated_symptoms.map((sym, i) => (
                                                <span
                                                    key={i}
                                                    className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                                                >
                                                    {sym}
                                                </span>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-slate-400 text-xs italic">
                                            None identified yet.
                                        </div>
                                    )}
                                </div>

                                {/* Red Flags Banner */}
                                {structuredSymptoms.has_red_flags ? (
                                    <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 space-y-1.5">
                                        <div className="flex items-center gap-1.5 font-semibold text-xs">
                                            <svg className="w-4 h-4 text-rose-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                            </svg>
                                            Clinical Red Flag Identified
                                        </div>
                                        <ul className="list-disc list-inside text-xs space-y-0.5 text-rose-700 dark:text-rose-300">
                                            {structuredSymptoms.red_flag_warnings?.map((warning, i) => (
                                                <li key={i}>{warning}</li>
                                            ))}
                                        </ul>
                                    </div>
                                ) : (
                                    <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2">
                                        <svg className="w-4 h-4 text-emerald-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                        </svg>
                                        No acute red flags detected so far.
                                    </div>
                                )}

                                {/* Clinical Summary */}
                                {structuredSymptoms.summary && (
                                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/60 text-xs">
                                        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                                            Dialogue Summary
                                        </div>
                                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                                            {structuredSymptoms.summary}
                                        </p>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="py-12 text-center text-slate-400 text-xs sm:text-sm">
                                Describe your symptoms by voice or text to generate structured clinical observations.
                            </div>
                        )}
                    </div>

                    {/* Quick Link to Book Doctor Consultation */}
                    <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-600 text-white shadow-sm space-y-2">
                        <h4 className="font-semibold text-sm">Ready to see a doctor?</h4>
                        <p className="text-xs text-indigo-100 leading-relaxed">
                            Your structured symptoms will be automatically shared with your attending clinician during your appointment.
                        </p>
                        <Link
                            href="/patient/appointments/book"
                            className="inline-block mt-1 px-3.5 py-1.5 rounded-lg bg-white text-indigo-700 text-xs font-semibold hover:bg-indigo-50 transition shadow-sm"
                        >
                            Book Provider Consultation →
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
