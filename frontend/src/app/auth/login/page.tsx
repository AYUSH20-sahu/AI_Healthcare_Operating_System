'use client';

import React, { useState, useRef, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { validatePostLoginRedirect, getDefaultRouteForRole } from '@/lib/redirect-validator';
import {
    Card,
    CardContent,
    Button,
    Input,
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

// ─── Institutional Clinical & Medication Knowledge Base ───────────────────────

interface DoctorInfo {
    id: string;
    name: string;
    specialty: string;
    experience: string;
    room: string;
    hours: string;
    status: 'Available Today' | 'In Emergency Triage' | 'OPD Active';
    phone: string;
}

const CLINICAL_DOCTORS: DoctorInfo[] = [
    {
        id: 'doc-1',
        name: 'Dr. Rajesh Sharma, MD, DM',
        specialty: 'Interventional Cardiology',
        experience: '16+ Years Experience',
        room: 'Room 302 (Cardiology Wing)',
        hours: 'Mon - Fri: 09:00 AM - 02:00 PM',
        status: 'Available Today',
        phone: '+91-98765-43211',
    },
    {
        id: 'doc-2',
        name: 'Dr. Sunita Rao, MD, DCH',
        specialty: 'Pediatrics & Neonatology',
        experience: '12+ Years Experience',
        room: 'Room 204 (Maternal & Child Block)',
        hours: 'Mon - Sat: 10:00 AM - 04:00 PM',
        status: 'OPD Active',
        phone: '+91-98765-43212',
    },
    {
        id: 'doc-3',
        name: 'Dr. Vikram Sen, MD',
        specialty: 'Internal Medicine & Diabetology',
        experience: '14+ Years Experience',
        room: 'Room 108 (Main Outpatient Complex)',
        hours: 'Mon - Sat: 08:30 AM - 03:30 PM',
        status: 'Available Today',
        phone: '+91-98765-43213',
    },
    {
        id: 'doc-4',
        name: 'Dr. Priya Nair, MD, FACEM',
        specialty: 'Emergency Medicine & Critical Trauma',
        experience: '11+ Years Experience',
        room: 'Trauma Bay 1 (Emergency Department)',
        hours: '24/7 Rotational Emergency Coverage',
        status: 'In Emergency Triage',
        phone: '+91-98765-43214',
    },
    {
        id: 'doc-5',
        name: 'Dr. Arvind Mehra, MS, MCh',
        specialty: 'Orthopedics & Joint Replacement',
        experience: '18+ Years Experience',
        room: 'Room 215 (Surgical Block)',
        hours: 'Tue, Thu, Sat: 09:30 AM - 01:30 PM',
        status: 'Available Today',
        phone: '+91-98765-43215',
    },
];

interface MedicationInfo {
    name: string;
    genericName: string;
    category: string;
    commonUse: string;
    dosageAdvice: string;
    precautions: string;
    warning?: string;
}

const CLINICAL_MEDICATIONS: MedicationInfo[] = [
    {
        name: 'Atorvastatin',
        genericName: 'Atorvastatin Calcium',
        category: 'Lipid-lowering / Statin',
        commonUse: 'Hypercholesterolemia, cardiovascular risk reduction, post-infarction care.',
        dosageAdvice: '10mg to 40mg once daily, recommended in the evening or at bedtime.',
        precautions: 'Avoid grapefruit juice. Monitor liver transaminases and report persistent muscle pain.',
    },
    {
        name: 'Metformin',
        genericName: 'Metformin Hydrochloride',
        category: 'Antidiabetic / Biguanide',
        commonUse: 'Type 2 Diabetes Mellitus glycemic management and insulin sensitivity.',
        dosageAdvice: '500mg to 1000mg twice daily with meals to mitigate gastrointestinal side effects.',
        precautions: 'Temporarily pause 48 hours prior to iodinated radiologic contrast procedures.',
    },
    {
        name: 'Paracetamol',
        genericName: 'Acetaminophen',
        category: 'Analgesic & Antipyretic',
        commonUse: 'Fever reduction, mild-to-moderate headache, musculo-skeletal pain.',
        dosageAdvice: '500mg to 650mg every 4 to 6 hours as needed. Do not exceed 4000mg (4g) within 24 hours.',
        precautions: 'Caution with underlying hepatic impairment or concurrent acetaminophen-containing cold remedies.',
    },
    {
        name: 'Amoxicillin + Clavulanate',
        genericName: 'Amoxicillin / Clavulanic Acid',
        category: 'Broad-Spectrum Antibiotic',
        commonUse: 'Respiratory tract infections, acute bacterial sinusitis, otitis media, skin infections.',
        dosageAdvice: '625mg twice daily or 1g twice daily for 5-7 days depending on clinical severity.',
        precautions: 'Contraindicated in known penicillin anaphylaxis. Must complete full prescribed antibiotic course.',
        warning: 'Penicillin allergy alert: Inform your attending physician if you ever experienced rash or swelling with penicillins.',
    },
    {
        name: 'Aspirin (Cardio)',
        genericName: 'Acetylsalicylic Acid (Dispersible / Chewable)',
        category: 'Antiplatelet Agent',
        commonUse: 'Secondary prevention of acute coronary syndrome, ischemic stroke, and emergency cardiac triage.',
        dosageAdvice: '75mg - 150mg maintenance daily. Acute emergency cardiac suspicion: 300mg - 325mg chewed immediately.',
        precautions: 'Take with food to minimize gastric irritation. Avoid if active peptic ulceration or bleeding diathesis.',
    },
    {
        name: 'Amlodipine',
        genericName: 'Amlodipine Besylate',
        category: 'Antihypertensive (Calcium Channel Blocker)',
        commonUse: 'Essential hypertension and chronic stable angina pectoris.',
        dosageAdvice: '5mg once daily, may be titrated to 10mg once daily under medical supervision.',
        precautions: 'Monitor for peripheral pedal edema and orthostatic dizziness upon standing.',
    },
];

interface ChatMessage {
    id: string;
    sender: 'assistant' | 'user' | 'system-alert';
    text: string;
    timestamp: string;
    quickActions?: { label: string; action: () => void }[];
    doctorCard?: DoctorInfo;
    medicationCard?: MedicationInfo;
    emergencyTrigger?: boolean;
}

// ─── Main Unified Login & Patient Care Gateway Component ─────────────────────

function LoginForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirectUrl = searchParams.get('redirect');

    const { login, isLoading, user } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    // Left Panel Interactive Dashboard State
    const [activeTab, setActiveTab] = useState<'chat' | 'emergency' | 'doctors' | 'medications'>('chat');
    const [chatInput, setChatInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // Emergency SOS State
    const [emergencyDispatched, setEmergencyDispatched] = useState(false);
    const [selectedEmergencyCondition, setSelectedEmergencyCondition] = useState<string>('Chest Pain / Suspected Heart Attack');
    const [emergencyPatientLocation, setEmergencyPatientLocation] = useState<string>('');
    const [emergencyDispatchTicket, setEmergencyDispatchTicket] = useState<string>('');
    const [dispatchTimestamp, setDispatchTimestamp] = useState<string>('');

    // Initial Chat Messages
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: 'm1',
            sender: 'assistant',
            text: '👋 Welcome to AI-HOS Health Care Portal! I am your AI Patient Care Concierge. How can I assist you today? You can ask about our on-duty doctors, available appointment slots, medication guides, clinic timings, or trigger an emergency response.',
            timestamp: 'Just now',
            quickActions: [
                { label: '👨‍⚕️ Available Doctors', action: () => handleQuickPrompt('Which doctors are available today?') },
                { label: '💊 Medication Guide', action: () => handleQuickPrompt('Tell me about common hospital medications') },
                { label: '❤️ Chest Pain / Emergency Help', action: () => handleQuickPrompt('What should I do if experiencing severe chest pain?') },
                { label: '⏰ OPD Consulting Hours', action: () => handleQuickPrompt('What are the hospital OPD timings?') },
            ],
        },
    ]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isTyping]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!email.trim() || !password) {
            setError('Please enter both your institutional email and password.');
            return;
        }

        try {
            setSubmitting(true);
            const user = await login(email.trim(), password);
            const destination = validatePostLoginRedirect(redirectUrl, user.role);
            router.push(destination);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Invalid credentials. Please try again.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    // ─── Intelligent AI Chatbot Engine ────────────────────────────────────────

    const handleSendMessage = (textToSend?: string) => {
        const query = (textToSend || chatInput).trim();
        if (!query) return;

        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const userMsg: ChatMessage = {
            id: 'u-' + Date.now(),
            sender: 'user',
            text: query,
            timestamp: timeStr,
        };

        setMessages((prev) => [...prev, userMsg]);
        setChatInput('');
        setIsTyping(true);

        setTimeout(() => {
            generateAIResponse(query);
            setIsTyping(false);
        }, 650);
    };

    const handleQuickPrompt = (prompt: string) => {
        handleSendMessage(prompt);
    };

    const generateAIResponse = (userQuery: string) => {
        const q = userQuery.toLowerCase();
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Emergency detection
        const isEmergency = q.includes('heart attack') || q.includes('chest pain') ||
            q.includes('breath') || q.includes('stroke') || q.includes('unconscious') ||
            q.includes('bleeding') || q.includes('dying') || q.includes('severe pain') ||
            q.includes('emergency') || q.includes('faint');

        if (isEmergency) {
            const alertMsg: ChatMessage = {
                id: 'sys-' + Date.now(),
                sender: 'system-alert',
                text: '🚨 CRITICAL CLINICAL ALERT DETECTED: Your symptoms may signify an acute life-threatening medical emergency (such as Acute Coronary Syndrome or Respiratory Distress). Please do not exert yourself. Trigger the instant Emergency SOS button below to alert our on-duty emergency physicians and nursing staff immediately, or dial 108 / Emergency Center.',
                timestamp: timeStr,
                emergencyTrigger: true,
                quickActions: [
                    {
                        label: '🚨 ACTIVATE EMERGENCY SOS DISPATCH',
                        action: () => triggerEmergencyFlow('Acute Chest Pain / Suspected Cardiac Event'),
                    },
                    {
                        label: '📞 Call Emergency Room: 108',
                        action: () => { window.location.href = 'tel:108'; },
                    },
                ],
            };
            setMessages((prev) => [...prev, alertMsg]);
            return;
        }

        // Doctor inquiries
        if (q.includes('doctor') || q.includes('cardiologist') || q.includes('pediatrician') ||
            q.includes('physician') || q.includes('appointment') || q.includes('sharma') ||
            q.includes('sunita') || q.includes('vikram') || q.includes('specialist')) {

            let matchedDoc: DoctorInfo | undefined;
            if (q.includes('cardio') || q.includes('heart') || q.includes('sharma')) {
                matchedDoc = CLINICAL_DOCTORS[0];
            } else if (q.includes('pediatric') || q.includes('child') || q.includes('sunita')) {
                matchedDoc = CLINICAL_DOCTORS[1];
            } else if (q.includes('diabet') || q.includes('internal') || q.includes('vikram')) {
                matchedDoc = CLINICAL_DOCTORS[2];
            }

            const responseMsg: ChatMessage = {
                id: 'bot-' + Date.now(),
                sender: 'assistant',
                text: matchedDoc
                    ? `Here are the details for ${matchedDoc.name}, currently on duty in our hospital:`
                    : `We have 5 distinguished specialists currently available in the outpatient and emergency departments. Here is our primary attending roster:`,
                timestamp: timeStr,
                doctorCard: matchedDoc || CLINICAL_DOCTORS[0],
                quickActions: [
                    { label: '📅 View All 5 Doctors', action: () => setActiveTab('doctors') },
                    { label: '🩺 Book Consultation (Sign In Required)', action: () => setError('Please sign in on the right to reserve an appointment slot.') },
                ],
            };
            setMessages((prev) => [...prev, responseMsg]);
            return;
        }

        // Medication inquiries
        if (q.includes('medication') || q.includes('medicine') || q.includes('drug') ||
            q.includes('paracetamol') || q.includes('atorvastatin') || q.includes('metformin') ||
            q.includes('amoxicillin') || q.includes('aspirin') || q.includes('dosage') ||
            q.includes('prescription')) {

            let matchedMed: MedicationInfo | undefined;
            if (q.includes('paracetamol') || q.includes('fever') || q.includes('pain') || q.includes('crocin')) {
                matchedMed = CLINICAL_MEDICATIONS[2];
            } else if (q.includes('atorvastatin') || q.includes('cholesterol') || q.includes('statin')) {
                matchedMed = CLINICAL_MEDICATIONS[0];
            } else if (q.includes('metformin') || q.includes('sugar') || q.includes('diabetes')) {
                matchedMed = CLINICAL_MEDICATIONS[1];
            } else if (q.includes('amoxicillin') || q.includes('antibiotic') || q.includes('augmentin')) {
                matchedMed = CLINICAL_MEDICATIONS[3];
            } else if (q.includes('aspirin')) {
                matchedMed = CLINICAL_MEDICATIONS[4];
            }

            const responseMsg: ChatMessage = {
                id: 'bot-' + Date.now(),
                sender: 'assistant',
                text: matchedMed
                    ? `Clinical pharmacopeia details for ${matchedMed.name} (${matchedMed.genericName}):`
                    : `Our hospital clinical formulary includes safety-screened medications with real-time automated drug-drug interaction validation. Here is an essential summary:`,
                timestamp: timeStr,
                medicationCard: matchedMed || CLINICAL_MEDICATIONS[0],
                quickActions: [
                    { label: '💊 Browse Full Pharmacy Formulary', action: () => setActiveTab('medications') },
                    { label: '⚠️ Drug Allergy Safeguards', action: () => handleQuickPrompt('What happens if I have a penicillin allergy?') },
                ],
            };
            setMessages((prev) => [...prev, responseMsg]);
            return;
        }

        // OPD Hours
        if (q.includes('hour') || q.includes('timing') || q.includes('open') || q.includes('opd') || q.includes('time')) {
            const responseMsg: ChatMessage = {
                id: 'bot-' + Date.now(),
                sender: 'assistant',
                text: `⏰ Hospital Operating & Consultation Hours:\n\n• General Outpatient (OPD): Monday to Saturday, 08:00 AM - 05:00 PM\n• Diagnostic Labs & Imaging (CT/MRI/X-Ray): 24/7 Service\n• Inpatient Pharmacy: 24/7 Ground Floor Counter\n• Emergency & Trauma Center: 24 Hours, 365 Days Continuous Triage`,
                timestamp: timeStr,
                quickActions: [
                    { label: '👨‍⚕️ Check Doctor Shift Times', action: () => setActiveTab('doctors') },
                    { label: '🚨 Emergency Triage Protocol', action: () => setActiveTab('emergency') },
                ],
            };
            setMessages((prev) => [...prev, responseMsg]);
            return;
        }

        // Fallback friendly guidance
        const defaultMsg: ChatMessage = {
            id: 'bot-' + Date.now(),
            sender: 'assistant',
            text: `I understand you are asking about: "${userQuery}".\n\nAs your AI Clinical Concierge, I can provide direct details on:\n1. 👨‍⚕️ Available doctors & outpatient schedules\n2. 💊 Medication usages, recommended dosages & precautions\n3. 🚨 Instant Emergency SOS alert dispatch to on-duty nurses & physicians\n4. 🏥 Hospital departments & facility guidelines\n\nPlease select a quick topic below or type your inquiry:`,
            timestamp: timeStr,
            quickActions: [
                { label: '👨‍⚕️ See Available Doctors', action: () => setActiveTab('doctors') },
                { label: '💊 View Medications', action: () => setActiveTab('medications') },
                { label: '🚨 Emergency SOS Help', action: () => setActiveTab('emergency') },
            ],
        };
        setMessages((prev) => [...prev, defaultMsg]);
    };

    // ─── Emergency SOS Dispatch Flow ──────────────────────────────────────────

    const triggerEmergencyFlow = (condition?: string) => {
        if (condition) setSelectedEmergencyCondition(condition);
        setActiveTab('emergency');
    };

    const handleConfirmEmergencyDispatch = () => {
        const ticket = 'EMG-SOS-' + Math.floor(100000 + Math.random() * 900000);
        const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        setEmergencyDispatchTicket(ticket);
        setDispatchTimestamp(nowStr);
        setEmergencyDispatched(true);

        // Add confirmation message to chat
        const emergencyBotMsg: ChatMessage = {
            id: 'sos-alert-' + Date.now(),
            sender: 'system-alert',
            text: `🚨 [CODE RED DISPATCHED #${ticket}]: Emergency alert broadcast sent at ${nowStr} to all on-duty emergency physicians (Dr. Priya Nair, Dr. Rajesh Sharma) and inpatient ICU/Ward nursing stations. Medical response team mobilized.`,
            timestamp: nowStr,
            quickActions: [
                { label: '📞 Call Emergency Room: 108', action: () => { window.location.href = 'tel:108'; } },
                { label: '🏥 View Triage Status', action: () => setActiveTab('emergency') },
            ],
        };
        setMessages((prev) => [...prev, emergencyBotMsg]);
    };

    const handleCancelEmergencyAlert = () => {
        setEmergencyDispatched(false);
        const cancelMsg: ChatMessage = {
            id: 'cancel-' + Date.now(),
            sender: 'assistant',
            text: `ℹ️ Emergency Alert #${emergencyDispatchTicket} has been marked as resolved/stand-down. On-duty clinical staff have been notified. Stay safe, and let me know if you need any other medical information.`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, cancelMsg]);
    };

    return (
        <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 transition-colors">
            {/* Top Bar for Theme Toggle */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            {/* ═══════════════════════════════════════════════════════════════════
                LEFT COLUMN: Interactive Patient Home & Health Care Dashboard
                ═══════════════════════════════════════════════════════════════════ */}
            <div className="lg:w-7/12 relative flex flex-col justify-between p-6 sm:p-8 lg:p-10 bg-slate-900 dark:bg-[#070A13] text-white border-b lg:border-b-0 lg:border-r border-slate-800 overflow-hidden">
                {/* Background Ambient Glows */}
                <div className="absolute top-0 -left-20 w-96 h-96 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute bottom-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute top-1/2 left-1/3 w-80 h-80 bg-rose-600/10 rounded-full blur-3xl pointer-events-none" />

                {/* 1. Header & Emergency Headline Beacon */}
                <div className="relative z-10 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <Link href={getDefaultRouteForRole(user?.role)} className="inline-flex items-center gap-3 group">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/25 group-hover:scale-105 transition-transform">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <div>
                                <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
                                    AI-HOS <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium border border-blue-500/30">Patient & Clinical Care</span>
                                </span>
                                <p className="text-xs text-slate-400">Next-Gen Intelligent Healthcare Operating System</p>
                            </div>
                        </Link>

                        {/* Top Direct Emergency SOS Trigger Button */}
                        <button
                            type="button"
                            onClick={() => triggerEmergencyFlow('Acute Chest Pain / Heart Attack')}
                            className="relative group inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-rose-600/90 hover:bg-rose-600 text-white font-bold text-xs tracking-wide shadow-lg shadow-rose-600/30 hover:shadow-rose-600/50 transition-all border border-rose-400/40 animate-pulse hover:animate-none"
                        >
                            <span className="w-2.5 h-2.5 rounded-full bg-white animate-ping" />
                            <span>🚨 EMERGENCY SOS</span>
                        </button>
                    </div>

                    {/* Operational Status Ticker */}
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 font-medium">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            24/7 ER Trauma Active
                        </div>
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/25 text-blue-300 font-medium">
                            <span className="w-2 h-2 rounded-full bg-blue-400" />
                            On-Duty Physicians: 5 Specialists
                        </div>
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/25 text-purple-300 font-medium">
                            <span>🤖 Clinical AI Concierge Online</span>
                        </div>
                    </div>
                </div>

                {/* 2. Interactive Navigation Tabs */}
                <div className="relative z-10 mt-6 mb-4 flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
                    <button
                        type="button"
                        onClick={() => setActiveTab('chat')}
                        className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                            activeTab === 'chat'
                                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
                                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white'
                        }`}
                    >
                        <span>💬 Patient AI Chatbot</span>
                    </button>

                    <button
                        type="button"
                        onClick={() => setActiveTab('emergency')}
                        className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                            activeTab === 'emergency'
                                ? 'bg-rose-600 text-white shadow-md shadow-rose-600/40 ring-2 ring-rose-400/50'
                                : 'bg-rose-950/40 text-rose-300 border border-rose-800/50 hover:bg-rose-900/50'
                        }`}
                    >
                        <span>🚨 Emergency SOS Alert</span>
                        {emergencyDispatched && (
                            <span className="w-2 h-2 rounded-full bg-rose-400 animate-ping" />
                        )}
                    </button>

                    <button
                        type="button"
                        onClick={() => setActiveTab('doctors')}
                        className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                            activeTab === 'doctors'
                                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
                                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white'
                        }`}
                    >
                        <span>👨‍⚕️ Available Doctors ({CLINICAL_DOCTORS.length})</span>
                    </button>

                    <button
                        type="button"
                        onClick={() => setActiveTab('medications')}
                        className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                            activeTab === 'medications'
                                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
                                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-800 hover:text-white'
                        }`}
                    >
                        <span>💊 Medications Guide</span>
                    </button>
                </div>

                {/* 3. Dynamic Center Panel Body */}
                <div className="relative z-10 flex-1 flex flex-col min-h-[460px] max-h-[560px]">
                    {/* ──── TAB 1: AI PATIENT CHATBOT ──── */}
                    {activeTab === 'chat' && (
                        <div className="flex-1 flex flex-col rounded-2xl bg-slate-800/70 border border-slate-700/70 backdrop-blur-md overflow-hidden shadow-2xl">
                            {/* Chat Header */}
                            <div className="px-4 py-3 bg-slate-800/90 border-b border-slate-700/80 flex items-center justify-between">
                                <div className="flex items-center gap-2.5">
                                    <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-blue-500/20">
                                        🤖
                                    </div>
                                    <div>
                                        <h3 className="text-xs font-bold text-white tracking-tight">AI Patient Care Concierge</h3>
                                        <p className="text-[10px] text-emerald-400 font-medium flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                            Active • Doctor Schedules, Medications & Triage
                                        </p>
                                    </div>
                                </div>
                                <span className="text-[11px] text-slate-400 font-mono">HIPAA Guarded</span>
                            </div>

                            {/* Chat Message Scrollable Area */}
                            <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs text-slate-200">
                                {messages.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                                    >
                                        <div
                                            className={`max-w-[90%] sm:max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed shadow-sm ${
                                                msg.sender === 'user'
                                                    ? 'bg-blue-600 text-white rounded-br-none'
                                                    : msg.sender === 'system-alert'
                                                    ? 'bg-rose-950/80 border border-rose-500/50 text-rose-100 rounded-bl-none ring-1 ring-rose-500/30'
                                                    : 'bg-slate-900/90 border border-slate-700/60 text-slate-100 rounded-bl-none'
                                            }`}
                                        >
                                            <p className="whitespace-pre-line">{msg.text}</p>

                                            {/* Render Embedded Doctor Card if present */}
                                            {msg.doctorCard && (
                                                <div className="mt-3 p-3 rounded-xl bg-slate-800/90 border border-slate-700/80 space-y-1.5 text-slate-200">
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-bold text-blue-300 text-xs">{msg.doctorCard.name}</span>
                                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold">
                                                            {msg.doctorCard.status}
                                                        </span>
                                                    </div>
                                                    <p className="text-[11px] text-cyan-300 font-medium">{msg.doctorCard.specialty} • {msg.doctorCard.experience}</p>
                                                    <div className="text-[10px] text-slate-400 space-y-0.5 pt-1">
                                                        <p>📍 {msg.doctorCard.room}</p>
                                                        <p>⏰ {msg.doctorCard.hours}</p>
                                                        <p>📞 Emergency Desk Ext: {msg.doctorCard.phone}</p>
                                                    </div>
                                                </div>
                                            )}

                                            {/* Render Embedded Medication Card if present */}
                                            {msg.medicationCard && (
                                                <div className="mt-3 p-3 rounded-xl bg-slate-800/90 border border-slate-700/80 space-y-1.5 text-slate-200">
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-bold text-emerald-300 text-xs">{msg.medicationCard.name}</span>
                                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium">
                                                            {msg.medicationCard.category}
                                                        </span>
                                                    </div>
                                                    <p className="text-[11px] text-slate-300"><strong>Generic:</strong> {msg.medicationCard.genericName}</p>
                                                    <p className="text-[11px] text-slate-300"><strong>Primary Use:</strong> {msg.medicationCard.commonUse}</p>
                                                    <p className="text-[11px] text-slate-300"><strong>Standard Dose:</strong> {msg.medicationCard.dosageAdvice}</p>
                                                    <p className="text-[10px] text-amber-300/90"><strong>Safety Notes:</strong> {msg.medicationCard.precautions}</p>
                                                    {msg.medicationCard.warning && (
                                                        <div className="p-2 rounded-lg bg-rose-950/60 border border-rose-700/50 text-rose-200 text-[10px] font-semibold mt-1">
                                                            ⚠️ {msg.medicationCard.warning}
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Quick Action Buttons */}
                                            {msg.quickActions && msg.quickActions.length > 0 && (
                                                <div className="mt-2.5 pt-2 border-t border-slate-700/40 flex flex-wrap gap-1.5">
                                                    {msg.quickActions.map((qa, idx) => (
                                                        <button
                                                            key={idx}
                                                            type="button"
                                                            onClick={qa.action}
                                                            className="text-[10px] px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 font-medium border border-slate-600/50 hover:border-blue-400 transition-all shadow-sm"
                                                        >
                                                            {qa.label}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <span className="text-[9px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
                                    </div>
                                ))}

                                {isTyping && (
                                    <div className="flex items-center gap-1.5 p-2 rounded-xl bg-slate-900/80 max-w-[120px] text-slate-400 text-xs">
                                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" />
                                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce [animation-delay:0.2s]" />
                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.4s]" />
                                        <span className="text-[10px] font-medium ml-1">Analyzing...</span>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>

                            {/* Chat Quick Prompt Chips */}
                            <div className="px-3 py-2 bg-slate-800/60 border-t border-slate-700/50 flex items-center gap-1.5 overflow-x-auto text-[11px] scrollbar-thin">
                                <button
                                    type="button"
                                    onClick={() => handleQuickPrompt('Which doctors are available today?')}
                                    className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-700/60 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-600/40 transition-colors"
                                >
                                    👨‍⚕️ Available Doctors
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleQuickPrompt('What medications are used for blood pressure and heart care?')}
                                    className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-700/60 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-600/40 transition-colors"
                                >
                                    💊 Cardiac & BP Meds
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleQuickPrompt('I am feeling severe chest tightness and sweating')}
                                    className="whitespace-nowrap px-2.5 py-1 rounded-full bg-rose-900/40 hover:bg-rose-900/70 text-rose-300 border border-rose-700/40 transition-colors"
                                >
                                    🚨 Report Chest Pain
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleQuickPrompt('What are your OPD consulting hours?')}
                                    className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-700/60 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-600/40 transition-colors"
                                >
                                    ⏰ OPD Timings
                                </button>
                            </div>

                            {/* Chat Input Bar */}
                            <div className="p-3 bg-slate-800/90 border-t border-slate-700/70 flex items-center gap-2">
                                <input
                                    type="text"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            e.preventDefault();
                                            handleSendMessage();
                                        }
                                    }}
                                    placeholder="Ask about doctors, medications, clinic timings, or symptoms..."
                                    className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                                />
                                <button
                                    type="button"
                                    onClick={() => handleSendMessage()}
                                    disabled={!chatInput.trim()}
                                    className="p-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 transition-all shadow-md shadow-blue-500/20"
                                    title="Send message"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ──── TAB 2: EMERGENCY SOS DISPATCH ──── */}
                    {activeTab === 'emergency' && (
                        <div className="flex-1 flex flex-col rounded-2xl bg-gradient-to-b from-rose-950/60 via-slate-900/90 to-slate-900 border border-rose-700/50 p-5 overflow-y-auto space-y-4 shadow-2xl backdrop-blur-md">
                            {/* Emergency Header */}
                            <div className="flex items-center justify-between pb-3 border-b border-rose-800/50">
                                <div className="flex items-center gap-2.5">
                                    <div className="w-8 h-8 rounded-xl bg-rose-600 flex items-center justify-center text-white font-bold text-base shadow-lg shadow-rose-600/50 animate-bounce">
                                        🚨
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-extrabold text-white tracking-wide uppercase flex items-center gap-2">
                                            Code Red Emergency Dispatch
                                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/30 text-rose-300 font-mono">CRITICAL CARE</span>
                                        </h3>
                                        <p className="text-[11px] text-rose-300">Directly alerts all on-duty emergency physicians & ICU nurses</p>
                                    </div>
                                </div>
                                <span className="text-xs font-bold text-rose-400 font-mono">PRIORITY 1</span>
                            </div>

                            {!emergencyDispatched ? (
                                <div className="space-y-4">
                                    <div className="p-3.5 rounded-xl bg-rose-950/70 border border-rose-700/60 text-xs text-rose-200 leading-relaxed">
                                        <strong>⚠️ Immediate Life-Threatening Crisis Protocol:</strong>
                                        <p className="mt-1 text-[11px] text-rose-300">
                                            Use this alert for acute conditions such as <strong>Heart Attack (severe squeezing chest pain radiating to left arm/jaw)</strong>, sudden speech slurring/stroke, acute severe breathlessness, or massive trauma.
                                        </p>
                                    </div>

                                    {/* Select Condition */}
                                    <div>
                                        <label className="block text-xs font-semibold text-slate-200 mb-2">
                                            Select Presenting Critical Condition:
                                        </label>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                                            {[
                                                'Chest Pain / Suspected Heart Attack',
                                                'Severe Respiratory Distress / Choking',
                                                'Stroke Symptoms / Facial Droop / Slurred Speech',
                                                'Unconscious / Syncope / Collapse',
                                                'Acute Anaphylaxis / Severe Allergic Reaction',
                                                'Massive Hemorrhage / Acute Trauma',
                                            ].map((cond) => (
                                                <button
                                                    key={cond}
                                                    type="button"
                                                    onClick={() => setSelectedEmergencyCondition(cond)}
                                                    className={`p-2.5 rounded-xl text-left font-medium transition-all border ${
                                                        selectedEmergencyCondition === cond
                                                            ? 'bg-rose-600 text-white border-rose-400 shadow-md shadow-rose-600/30 font-bold'
                                                            : 'bg-slate-800/80 text-slate-300 border-slate-700/80 hover:bg-slate-800 hover:text-white'
                                                    }`}
                                                >
                                                    • {cond}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Patient Location or Contact */}
                                    <div>
                                        <label className="block text-xs font-medium text-slate-300 mb-1">
                                            Your Current Location or Contact Phone (Optional):
                                        </label>
                                        <input
                                            type="text"
                                            value={emergencyPatientLocation}
                                            onChange={(e) => setEmergencyPatientLocation(e.target.value)}
                                            placeholder="e.g. Ground Floor Reception, Inpatient Room 204, or Phone Number"
                                            className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500"
                                        />
                                    </div>

                                    {/* Dispatch Button */}
                                    <div className="pt-2">
                                        <button
                                            type="button"
                                            onClick={handleConfirmEmergencyDispatch}
                                            className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-rose-600 via-red-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white font-black text-sm tracking-wider uppercase shadow-xl shadow-rose-600/40 hover:shadow-rose-600/60 transition-all flex items-center justify-center gap-3 border border-rose-400/50"
                                        >
                                            <span className="w-3 h-3 rounded-full bg-white animate-ping" />
                                            <span>🚨 DISPATCH CODE RED EMERGENCY TEAM NOW</span>
                                        </button>
                                    </div>

                                    {/* Direct Phone Backup */}
                                    <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800">
                                        <span>Direct Ambulance / ER Hotline:</span>
                                        <a href="tel:108" className="font-bold text-rose-400 hover:underline">
                                            📞 Dial 108 / +91-800-AIHOS-911
                                        </a>
                                    </div>
                                </div>
                            ) : (
                                /* Emergency Active Broadcast Screen */
                                <div className="space-y-4 animate-in fade-in duration-300">
                                    <div className="p-4 rounded-xl bg-rose-600/20 border-2 border-rose-500 text-center space-y-2">
                                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-600 text-white text-xs font-black tracking-widest uppercase animate-pulse">
                                            🔴 CODE RED ACTIVE • MEDICAL TEAM MOBILIZED
                                        </div>
                                        <h4 className="text-base font-extrabold text-white mt-1">
                                            Emergency Alert Dispatched: {selectedEmergencyCondition}
                                        </h4>
                                        <p className="text-xs text-rose-200">
                                            Broadcasted via High-Priority Clinical Mesh to <strong>Trauma ICU</strong>, <strong>Duty Cardiologist</strong>, and <strong>Ward Nursing Stations</strong>.
                                        </p>
                                    </div>

                                    <div className="p-3.5 rounded-xl bg-slate-800/90 border border-slate-700/80 space-y-2 text-xs text-slate-300">
                                        <div className="flex justify-between border-b border-slate-700/60 pb-1.5">
                                            <span className="text-slate-400">Incident Ticket:</span>
                                            <span className="font-mono font-bold text-cyan-300">{emergencyDispatchTicket}</span>
                                        </div>
                                        <div className="flex justify-between border-b border-slate-700/60 pb-1.5">
                                            <span className="text-slate-400">Dispatch Time:</span>
                                            <span className="font-mono text-white">{dispatchTimestamp} UTC</span>
                                        </div>
                                        <div className="flex justify-between border-b border-slate-700/60 pb-1.5">
                                            <span className="text-slate-400">Notified Clinicians:</span>
                                            <span className="text-emerald-300 font-semibold">Dr. Priya Nair (ER), Dr. Rajesh Sharma (Cardio)</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-slate-400">Assigned Nursing Station:</span>
                                            <span className="text-blue-300 font-semibold">Telemetry Ward 1 & Rapid Response Team</span>
                                        </div>
                                    </div>

                                    {/* Action Guidance */}
                                    <div className="p-3 rounded-xl bg-blue-950/50 border border-blue-800/50 text-xs text-blue-200 space-y-1">
                                        <p className="font-bold text-white">Immediate Instructions While Team Arrives:</p>
                                        <ul className="list-disc list-inside text-[11px] space-y-0.5 text-blue-200">
                                            <li>Sit down comfortably in an upright position; do not walk or exert yourself.</li>
                                            <li>Loosen any tight collars, belts, or clothing around chest and neck.</li>
                                            <li>If cardiac chest pain is suspected and patient is conscious with no allergy, chew 1 adult aspirin (300-325mg).</li>
                                        </ul>
                                    </div>

                                    <div className="flex items-center gap-3 pt-2">
                                        <a
                                            href="tel:108"
                                            className="flex-1 py-2.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs text-center transition-colors flex items-center justify-center gap-1.5"
                                        >
                                            📞 Call ER Desk (108)
                                        </a>
                                        <button
                                            type="button"
                                            onClick={handleCancelEmergencyAlert}
                                            className="py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
                                        >
                                            Stand Down / Cancel
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ──── TAB 3: AVAILABLE DOCTORS DIRECTORY ──── */}
                    {activeTab === 'doctors' && (
                        <div className="flex-1 flex flex-col rounded-2xl bg-slate-800/70 border border-slate-700/70 p-4 overflow-y-auto space-y-3 backdrop-blur-md shadow-2xl">
                            <div className="flex items-center justify-between pb-2 border-b border-slate-700/70">
                                <div>
                                    <h3 className="text-xs font-bold text-white tracking-wide uppercase">On-Duty Doctors & Specialists</h3>
                                    <p className="text-[11px] text-slate-400">Consulting schedules and departmental room locations</p>
                                </div>
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-mono">Real-Time OPD</span>
                            </div>

                            <div className="space-y-2.5">
                                {CLINICAL_DOCTORS.map((doc) => (
                                    <div key={doc.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-700/60 hover:border-blue-500/50 transition-all text-xs space-y-1">
                                        <div className="flex items-center justify-between">
                                            <h4 className="font-bold text-white text-xs">{doc.name}</h4>
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                                                doc.status === 'Available Today' ? 'bg-emerald-500/20 text-emerald-300' :
                                                doc.status === 'In Emergency Triage' ? 'bg-rose-500/20 text-rose-300 animate-pulse' :
                                                'bg-blue-500/20 text-blue-300'
                                            }`}>
                                                {doc.status}
                                            </span>
                                        </div>
                                        <p className="text-[11px] text-cyan-300 font-medium">{doc.specialty} • {doc.experience}</p>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-[10px] text-slate-400 pt-1">
                                            <p>📍 {doc.room}</p>
                                            <p>⏰ {doc.hours}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* ──── TAB 4: MEDICATIONS DIRECTORY ──── */}
                    {activeTab === 'medications' && (
                        <div className="flex-1 flex flex-col rounded-2xl bg-slate-800/70 border border-slate-700/70 p-4 overflow-y-auto space-y-3 backdrop-blur-md shadow-2xl">
                            <div className="flex items-center justify-between pb-2 border-b border-slate-700/70">
                                <div>
                                    <h3 className="text-xs font-bold text-white tracking-wide uppercase">Hospital Medication Formulary</h3>
                                    <p className="text-[11px] text-slate-400">Clinical usage, standard dosage and safety precautions</p>
                                </div>
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono">Pharmacopeia</span>
                            </div>

                            <div className="space-y-2.5">
                                {CLINICAL_MEDICATIONS.map((med, idx) => (
                                    <div key={idx} className="p-3 rounded-xl bg-slate-900/80 border border-slate-700/60 text-xs space-y-1.5">
                                        <div className="flex items-center justify-between">
                                            <h4 className="font-bold text-emerald-300 text-xs">{med.name}</h4>
                                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium">
                                                {med.category}
                                            </span>
                                        </div>
                                        <p className="text-[11px] text-slate-300"><strong>Generic:</strong> {med.genericName}</p>
                                        <p className="text-[11px] text-slate-300"><strong>Indication:</strong> {med.commonUse}</p>
                                        <p className="text-[11px] text-slate-300"><strong>Standard Dose:</strong> {med.dosageAdvice}</p>
                                        <p className="text-[10px] text-amber-300/90"><strong>Precaution:</strong> {med.precautions}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* 4. Footer Security & System Node Badge */}
                <div className="relative z-10 pt-4 mt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        AES-256 GCM • ABHA & DPDP Compliant
                    </span>
                    <span className="font-mono text-slate-500">SYSTEM ID: AIHOS-PORTAL-NODE-01</span>
                </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════════
                RIGHT COLUMN: Institutional & Patient Portal Sign In Form
                ═══════════════════════════════════════════════════════════════════ */}
            <div className="lg:w-5/12 flex items-center justify-center p-6 sm:p-10 lg:p-12">
                <div className="w-full max-w-md space-y-6">
                    <div>
                        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Institutional Login
                        </h2>
                        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                            Sign in to access your designated clinical workspace, patient health records, or nursing dashboard.
                        </p>
                    </div>

                    {error && (
                        <Alert
                            variant="error"
                            title="Authentication Failed"
                            onClose={() => setError(null)}
                        >
                            {error}
                        </Alert>
                    )}

                    {/* Login Card */}
                    <Card className="glass-panel border-slate-200 dark:border-slate-800 shadow-xl">
                        <CardContent className="pt-6">
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <Input
                                    id="email"
                                    label="Institutional Email or Mobile Number"
                                    type="text"
                                    required
                                    placeholder="patient@test.com, doctor@hospital.org"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    disabled={submitting || isLoading}
                                    leadingIcon={
                                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                        </svg>
                                    }
                                />

                                <div>
                                    <div className="flex items-center justify-between mb-1.5">
                                        <label htmlFor="password" className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                                            Password <span className="text-rose-500">*</span>
                                        </label>
                                        <a
                                            href="#forgot"
                                            onClick={(e) => {
                                                e.preventDefault();
                                                alert('Please contact your hospital system administrator or click register to create a new patient account.');
                                            }}
                                            className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                                        >
                                            Forgot password?
                                        </a>
                                    </div>
                                    <Input
                                        id="password"
                                        type={showPassword ? 'text' : 'password'}
                                        autoComplete="current-password"
                                        required
                                        placeholder="••••••••••••"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        disabled={submitting || isLoading}
                                        leadingIcon={
                                            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                            </svg>
                                        }
                                        trailingIcon={
                                            showPassword ? (
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                                                </svg>
                                            ) : (
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                                </svg>
                                            )
                                        }
                                        onTrailingIconClick={() => setShowPassword(!showPassword)}
                                    />
                                </div>

                                <div className="flex items-center justify-between pt-1">
                                    <Checkbox
                                        id="remember"
                                        label="Remember this workstation"
                                        checked={rememberMe}
                                        onChange={(e) => setRememberMe(e.target.checked)}
                                    />
                                </div>

                                <Button
                                    type="submit"
                                    variant="primary"
                                    size="lg"
                                    className="w-full justify-center shadow-lg shadow-blue-500/25 mt-2 font-bold"
                                    isLoading={submitting || isLoading}
                                >
                                    Authenticate & Access Portal
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Secondary Navigation */}
                    <div className="text-center text-xs text-slate-500 dark:text-slate-400 space-y-2">
                        <p>
                            New patient or registering a healthcare facility?{' '}
                            <Link href="/auth/register" className="font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                                Register Organization or Account
                            </Link>
                        </p>
                        <p>
                            <Link
                                href={getDefaultRouteForRole(user?.role)}
                                className="hover:underline text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                            >
                                {user ? '← Return to Dashboard' : '← Return to System Overview'}
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#0B0F19]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            </div>
        }>
            <LoginForm />
        </Suspense>
    );
}
