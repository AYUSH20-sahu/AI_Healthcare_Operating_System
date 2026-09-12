'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
    intakeApi,
    IntakeSession,
    IntakeMessageItem,
    StructuredSymptoms,
} from '@/lib/api';

const QUICK_PROMPTS = [
    "Severe throbbing headache for the past 2 days",
    "Persistent dry cough with mild fatigue",
    "Sharp lower back pain worsening when bending",
    "Upset stomach and nausea since yesterday evening",
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

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isSending]);

    // Load active session or create initial one
    useEffect(() => {
        loadSession();
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
                // Initialize a new session
                await handleStartNewSession();
            }
        } catch (err: any) {
            // If 404, create a fresh session
            if (err?.status === 404 || err?.message?.includes('404')) {
                await handleStartNewSession();
            } else {
                console.error('Failed to load active intake session:', err);
                setError('Unable to load intake session. Starting a new session...');
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

    const isSessionComplete = session?.status === 'completed';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/60">
                            Milestone U-13
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
                        AI Patient Intake & Symptom Clarifier
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Empathetic, non-diagnostic symptom structuring prior to clinical consultation.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => handleStartNewSession()}
                        disabled={isLoading}
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
                            disabled={isCompleting || messages.length < 2}
                            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-medium rounded-lg text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 transition shadow-sm"
                        >
                            {isCompleting ? 'Finalizing...' : 'Complete & Structure'}
                        </button>
                    )}
                </div>
            </div>

            {/* AI Safety / Non-Diagnostic Warning Banner */}
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

            {error && (
                <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs sm:text-sm text-rose-700 dark:text-rose-300 flex items-center justify-between">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-700 font-bold ml-2">✕</button>
                </div>
            )}

            {/* Split Screen Layout: Chat on Left, Structured Symptoms on Right */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                
                {/* Left Column: Conversational Chat Interface (7 cols) */}
                <div className="lg:col-span-7 flex flex-col bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden h-[640px]">
                    {/* Chat Header */}
                    <div className="px-5 py-3.5 border-b border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-full bg-cyan-600 text-white flex items-center justify-center font-bold text-xs shadow-inner">
                                AI
                            </div>
                            <div>
                                <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                                    Intake Assistant
                                </h2>
                                <p className="text-xs text-slate-400">
                                    Provider-orchestrated symptom collector
                                </p>
                            </div>
                        </div>

                        {aiConfidence !== null && (
                            <span className="text-xs px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono">
                                AI Confidence: {aiConfidence}%
                            </span>
                        )}
                    </div>

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
                                No messages yet. Say hello or select a prompt below.
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
                                            <div
                                                className={`text-[10px] mt-1 text-right ${
                                                    isUser ? 'text-indigo-200' : 'text-slate-400'
                                                }`}
                                            >
                                                {new Date(msg.timestamp).toLocaleTimeString([], {
                                                    hour: '2-digit',
                                                    minute: '2-digit',
                                                })}
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
                                    <span>Analyzing & structuring symptoms...</span>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Quick suggestion chips */}
                    {!isSessionComplete && (
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

                    {/* Input Controls */}
                    <div className="p-3.5 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                        {isSessionComplete ? (
                            <div className="p-3 text-center rounded-xl bg-slate-50 dark:bg-slate-800/50 text-xs text-slate-600 dark:text-slate-400">
                                This intake session has been finalized. You can review your structured symptoms on the right or book a visit with your doctor.
                            </div>
                        ) : (
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    handleSendMessage();
                                }}
                                className="flex items-center gap-2"
                            >
                                <textarea
                                    ref={textareaRef}
                                    rows={1}
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    disabled={isSending}
                                    placeholder="Describe how you are feeling, pain location, or onset..."
                                    className="flex-1 resize-none rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition"
                                />
                                <button
                                    type="submit"
                                    disabled={!inputText.trim() || isSending}
                                    className="p-2.5 rounded-xl bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-40 disabled:cursor-not-allowed transition shadow-sm flex-shrink-0"
                                    title="Send message"
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
                                <div>
                                    <span className="text-slate-400 text-xs uppercase tracking-wider font-semibold">
                                        Chief Complaint
                                    </span>
                                    <p className="mt-0.5 font-medium text-slate-800 dark:text-slate-200">
                                        {structuredSymptoms.chief_complaint || 'Pending clarification'}
                                    </p>
                                </div>

                                {/* Duration & Severity */}
                                <div className="grid grid-cols-2 gap-3 pt-1">
                                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                                        <span className="text-slate-400 text-[11px] block font-medium">
                                            Duration / Onset
                                        </span>
                                        <span className="font-semibold text-slate-700 dark:text-slate-200">
                                            {structuredSymptoms.duration || 'Not reported yet'}
                                        </span>
                                    </div>

                                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                                        <span className="text-slate-400 text-[11px] block font-medium">
                                            Reported Severity
                                        </span>
                                        <div className="flex items-center gap-1.5 mt-0.5">
                                            {structuredSymptoms.severity !== null && structuredSymptoms.severity !== undefined ? (
                                                <>
                                                    <span className={`font-bold text-sm ${
                                                        structuredSymptoms.severity >= 7
                                                            ? 'text-rose-600'
                                                            : structuredSymptoms.severity >= 4
                                                            ? 'text-amber-600'
                                                            : 'text-emerald-600'
                                                    }`}>
                                                        {structuredSymptoms.severity}/10
                                                    </span>
                                                    <div className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full rounded-full ${
                                                                structuredSymptoms.severity >= 7
                                                                    ? 'bg-rose-500'
                                                                    : structuredSymptoms.severity >= 4
                                                                    ? 'bg-amber-500'
                                                                    : 'bg-emerald-500'
                                                            }`}
                                                            style={{ width: `${structuredSymptoms.severity * 10}%` }}
                                                        />
                                                    </div>
                                                </>
                                            ) : (
                                                <span className="text-slate-400 italic text-xs">Unspecified</span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Associated Symptoms */}
                                {structuredSymptoms.associated_symptoms && structuredSymptoms.associated_symptoms.length > 0 && (
                                    <div>
                                        <span className="text-slate-400 text-xs uppercase tracking-wider font-semibold">
                                            Associated Symptoms
                                        </span>
                                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                                            {structuredSymptoms.associated_symptoms.map((sym, i) => (
                                                <span
                                                    key={i}
                                                    className="px-2.5 py-0.5 rounded-md text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                                                >
                                                    {sym}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Aggravating / Relieving Factors */}
                                {((structuredSymptoms.aggravating_factors?.length || 0) > 0 || (structuredSymptoms.relieving_factors?.length || 0) > 0) && (
                                    <div className="space-y-2 pt-1">
                                        {structuredSymptoms.aggravating_factors && structuredSymptoms.aggravating_factors.length > 0 && (
                                            <div>
                                                <span className="text-slate-400 text-[11px] font-medium block">
                                                    Aggravating Factors:
                                                </span>
                                                <p className="text-xs text-slate-600 dark:text-slate-300">
                                                    {structuredSymptoms.aggravating_factors.join(', ')}
                                                </p>
                                            </div>
                                        )}
                                        {structuredSymptoms.relieving_factors && structuredSymptoms.relieving_factors.length > 0 && (
                                            <div>
                                                <span className="text-slate-400 text-[11px] font-medium block">
                                                    Relieving Factors:
                                                </span>
                                                <p className="text-xs text-slate-600 dark:text-slate-300">
                                                    {structuredSymptoms.relieving_factors.join(', ')}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Clinical Summary */}
                                {structuredSymptoms.summary && (
                                    <div className="p-3.5 rounded-xl bg-cyan-50/60 dark:bg-cyan-950/20 border border-cyan-200/60 dark:border-cyan-800/40">
                                        <span className="text-[11px] font-semibold uppercase tracking-wider text-cyan-800 dark:text-cyan-300 block mb-1">
                                            Physician Brief Summary
                                        </span>
                                        <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                                            {structuredSymptoms.summary}
                                        </p>
                                    </div>
                                )}

                                {basis && (
                                    <div className="text-[11px] text-slate-400 border-t border-slate-100 dark:border-slate-800 pt-2">
                                        <span className="font-semibold">Clinical Basis:</span> {basis}
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="text-center py-8 text-slate-400 text-xs">
                                Symptoms will automatically structure here as you converse with the assistant.
                            </div>
                        )}
                    </div>

                    {/* Action Navigation Card */}
                    <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-50 to-cyan-50 dark:from-indigo-950/30 dark:to-cyan-950/30 border border-indigo-100 dark:border-indigo-900/40 space-y-3">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-900 dark:text-indigo-300">
                            Next Steps
                        </h4>
                        <p className="text-xs text-slate-600 dark:text-slate-300">
                            Once symptoms are organized, proceed to book an appointment with your doctor so they can review this intake brief.
                        </p>
                        <Link
                            href="/patient/appointments"
                            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-xs sm:text-sm font-semibold hover:bg-indigo-700 transition shadow-sm"
                        >
                            Schedule Doctor Consultation
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </Link>
                    </div>
                </div>

            </div>
        </div>
    );
}
