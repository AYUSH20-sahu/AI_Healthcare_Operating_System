'use client';

import React, { useState, useEffect, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { validatePostLoginRedirect } from '@/lib/redirect-validator';
import {
    Card,
    CardContent,
    Button,
    Input,
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

// ─── Institutional Doctor & Fee Knowledge Base ───────────────────────────────

interface DoctorInfo {
    id: string;
    name: string;
    specialty: string;
    qualification: string;
    slots: string[];
    room: string;
    fee: number;
    followUpFee: string;
    status: 'Available Today' | 'OPD Active' | '24/7 Emergency';
    phone: string;
}

const HOSPITAL_DOCTORS: DoctorInfo[] = [
    {
        id: 'doc-1',
        name: 'Dr. Rajesh Sharma',
        specialty: 'Interventional Cardiology',
        qualification: 'MD, DM (Cardiology), FACC',
        slots: ['Mon - Fri: 09:00 AM - 01:00 PM', 'Mon - Thu: 04:00 PM - 06:00 PM'],
        room: 'Room 302 (Cardiology Wing, 3rd Floor)',
        fee: 800,
        followUpFee: 'Free within 7 days',
        status: 'Available Today',
        phone: '+91-98765-43210',
    },
    {
        id: 'doc-2',
        name: 'Dr. Priya Patel',
        specialty: 'Neurology & Stroke Care',
        qualification: 'MD, DM (Neurology)',
        slots: ['Mon, Wed, Fri: 10:00 AM - 02:00 PM'],
        room: 'Room 205 (Neurosciences Block, 2nd Floor)',
        fee: 900,
        followUpFee: 'Free within 7 days',
        status: 'Available Today',
        phone: '+91-98765-43211',
    },
    {
        id: 'doc-3',
        name: 'Dr. Arjun Kumar',
        specialty: 'Pediatrics & Neonatal Care',
        qualification: 'MD, DCH (Pediatrics)',
        slots: ['Mon - Sat: 09:30 AM - 03:30 PM'],
        room: 'Room 104 (Child Health Pavilion, 1st Floor)',
        fee: 600,
        followUpFee: 'Free within 7 days',
        status: 'OPD Active',
        phone: '+91-98765-43212',
    },
    {
        id: 'doc-4',
        name: 'Dr. Kavya Singh',
        specialty: 'Orthopedics & Joint Surgery',
        qualification: 'MS, MCh (Ortho)',
        slots: ['Tue, Thu, Sat: 11:00 AM - 04:00 PM'],
        room: 'Room 218 (Surgical Block, 2nd Floor)',
        fee: 750,
        followUpFee: 'Free within 7 days',
        status: 'Available Today',
        phone: '+91-98765-43213',
    },
    {
        id: 'doc-5',
        name: 'Dr. Vikram Reddy',
        specialty: 'Dermatology & Skin Allergy',
        qualification: 'MD (Dermatology)',
        slots: ['Mon, Wed, Sat: 02:00 PM - 06:00 PM'],
        room: 'Room 112 (Outpatient Complex, 1st Floor)',
        fee: 650,
        followUpFee: 'Free within 7 days',
        status: 'OPD Active',
        phone: '+91-98765-43214',
    },
    {
        id: 'doc-6',
        name: 'Dr. Sunita Rao',
        specialty: 'Internal Medicine & Diabetology',
        qualification: 'MD (Internal Medicine)',
        slots: ['Mon - Sat: 08:30 AM - 02:30 PM'],
        room: 'Room 101 (Main OPD Complex, Ground Floor)',
        fee: 500,
        followUpFee: 'Free within 7 days',
        status: 'Available Today',
        phone: '+91-98765-43215',
    },
    {
        id: 'doc-7',
        name: 'Dr. Priya Nair',
        specialty: 'Emergency Medicine & Critical Trauma',
        qualification: 'MD, FACEM (Emergency Care)',
        slots: ['24/7 Rotational Emergency Coverage'],
        room: 'Trauma Bay 1 (Ground Floor Emergency Dept)',
        fee: 1000,
        followUpFee: 'Triage assessment included',
        status: '24/7 Emergency',
        phone: '+91-98765-43216',
    },
];

interface ChatMessage {
    id: string;
    sender: 'assistant' | 'user' | 'system-alert';
    text: string;
    timestamp: string;
    quickActions?: { label: string; action: () => void }[];
    doctorCard?: DoctorInfo;
    showEmergencyActions?: boolean;
}

type LoginMethod = 'email' | 'phone';
type LeftPanelTab = 'chat' | 'emergency' | 'doctors';

// ─── Security / Privacy Guardrail Engine ─────────────────────────────────────
// Strictly forbids exposing internal software, project details, code, architecture,
// rules, jailbreaks, or reverse psychology "what not to do" queries.

function isRestrictedProjectQuery(rawQuery: string): boolean {
    const q = rawQuery.toLowerCase().trim();

    // 1. Direct project, codebase, technology, or system meta inquiries
    const projectKeywords = [
        'this project',
        'about project',
        'about the project',
        'project details',
        'who made this',
        'who built this',
        'who created this',
        'codebase',
        'source code',
        'github',
        'repository',
        'tech stack',
        'technology stack',
        'fastapi',
        'nextjs',
        'next.js',
        'react',
        'python',
        'backend',
        'frontend',
        'database schema',
        'postgres',
        'system architecture',
        'ai healthcare operating system',
        'ai-hos',
        'system prompt',
        'developer mode',
        'jailbreak',
        'prompt injection',
        'what are your instructions',
        'what are your rules',
        'internal rules',
        'reveal prompt',
        'vulnerability',
        'security flaw',
        'weakness of this project',
        'negative points',
        'negative aspects',
        'criticize this project',
        'positive points',
        'positive aspects',
        'praise this project',
        'pros and cons of this project',
        'rate this project',
        'review this project',
        'hackathon',
        'assignment',
        'who is your creator',
        'who is your developer',
        'what model is this',
        'api key',
    ];

    for (const kw of projectKeywords) {
        if (q.includes(kw)) {
            return true;
        }
    }

    // 2. Reverse psychology patterns & "what not to do" / extraction queries
    const trickPatterns = [
        /what\s+(should\s+i\s+not|not\s+to)\s+do/i,
        /what\s+not\s+to\s+ask/i,
        /how\s+(can|do)\s+i\s+(get|extract|find)\s+info.*(project|system|code|backend|internal|app)/i,
        /what\s+(is\s+secret|are\s+the\s+secrets|is\s+hidden|is\s+forbidden)/i,
        /what\s+(can't|cannot)\s+you\s+(tell|reveal|say|disclose)/i,
        /tell\s+me\s+what\s+(not\s+to\s+ask|you\s+can't\s+say)/i,
        /bypass|override|ignore\s+previous|system\s+override/i,
        /what\s+is\s+this\s+(system|software|app|platform)/i,
        /is\s+this\s+project\s+(good|bad|flawed|safe|secure)/i,
    ];

    for (const pattern of trickPatterns) {
        if (pattern.test(q)) {
            return true;
        }
    }

    return false;
}

// ─── Main Unified Component ──────────────────────────────────────────────────

function PatientLoginForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const rawRedirect = searchParams.get('redirect');

    const { patientLogin, isLoading, isAuthenticated, isPatient } = useAuth();
    const [loginMethod, setLoginMethod] = useState<LoginMethod>('email');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    // Left Panel State
    const [activeLeftTab, setActiveLeftTab] = useState<LeftPanelTab>('chat');
    const [chatInput, setChatInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

    // Emergency Triage Dispatch State
    const [emergencyType, setEmergencyType] = useState('Acute Chest Pain / Cardiac Event');
    const [emergencyLocation, setEmergencyLocation] = useState('');
    const [emergencyTicket, setEmergencyTicket] = useState<string | null>(null);
    const [dispatchingSOS, setDispatchingSOS] = useState(false);

    // Initial Chat State
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: 'm1',
            sender: 'assistant',
            text: '👋 Welcome to CarePulse Patient Services! I am your hospital outpatient concierge assistant. How may I help you today? You can inquire about doctor time slots, outpatient consultation fees, clinic timings, or emergency assistance.',
            timestamp: 'Just now',
            quickActions: [
                { label: '📅 Doctor Time Slots', action: () => handleSendPrompt('Which doctors are available and what are their time slots?') },
                { label: '💰 Consultation Fees', action: () => handleSendPrompt('What are the doctor consultation fees and charges?') },
                { label: '⏰ OPD Clinic Hours', action: () => handleSendPrompt('What are the hospital OPD timings?') },
                { label: '🚨 Emergency Hotline', action: () => handleSendPrompt('What is the emergency helpline number?') },
            ],
        },
    ]);

    useEffect(() => {
        if (!isLoading && isAuthenticated && isPatient) {
            const destination = validatePostLoginRedirect(rawRedirect, 'patient');
            router.replace(destination);
        }
    }, [isLoading, isAuthenticated, isPatient, rawRedirect, router]);

    // Live backend connectivity heartbeat probe
    useEffect(() => {
        let isMounted = true;
        const checkBackend = async () => {
            try {
                const res = await fetch('/api/v1/observability/health', { method: 'GET' });
                if (isMounted) {
                    setBackendConnected(res.ok);
                }
            } catch {
                if (isMounted) {
                    setBackendConnected(false);
                }
            }
        };
        checkBackend();
        return () => {
            isMounted = false;
        };
    }, []);

    useEffect(() => {
        if (activeLeftTab === 'chat') {
            chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isTyping, activeLeftTab]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        const identifier = loginMethod === 'email' ? email.trim() : phone.trim();

        if (!identifier) {
            setError(
                loginMethod === 'email'
                    ? 'Please enter your registered email address.'
                    : 'Please enter your registered mobile phone number.'
            );
            return;
        }

        if (!password) {
            setError('Please enter your password.');
            return;
        }

        try {
            setSubmitting(true);
            await patientLogin(identifier, password);
            const destination = validatePostLoginRedirect(rawRedirect, 'patient');
            router.push(destination);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Invalid credentials. Please verify your details.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    // Quick demo autofill helper
    const handleAutofill = (type: 'amit' | 'sarah' | 'mobile') => {
        setError(null);
        if (type === 'amit') {
            setLoginMethod('email');
            setEmail('patient@test.com');
            setPassword('patientpassword123');
        } else if (type === 'sarah') {
            setLoginMethod('email');
            setEmail('freshpatient@test.com');
            setPassword('patientpassword123');
        } else if (type === 'mobile') {
            setLoginMethod('phone');
            setPhone('9876511111');
            setPassword('patientpassword123');
        }
    };

    // ─── Chatbot Logic ──────────────────────────────────────────────────────────

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
            processChatbotReply(query);
            setIsTyping(false);
        }, 500);
    };

    const handleSendPrompt = (prompt: string) => {
        handleSendMessage(prompt);
    };

    const processChatbotReply = (userQuery: string) => {
        const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const q = userQuery.toLowerCase();

        // 1. STRICT PRIVACY / PROJECT BOUNDARY GUARDRAIL
        if (isRestrictedProjectQuery(userQuery)) {
            const restrictedMsg: ChatMessage = {
                id: 'bot-' + Date.now(),
                sender: 'assistant',
                text: '🔒 **Hospital Outpatient Helpdesk Notice:**\n\nI am exclusively a hospital outpatient concierge assistant. My role is strictly limited to helping patients with clinical inquiries, doctor appointment time slots, consultation fees, and emergency assistance.\n\nI cannot disclose, discuss, or evaluate software architecture, system internals, source code, project specifications, or developmental details—neither positively nor negatively. Questions regarding system internals or restricted inquiries cannot be answered.\n\nFor patient care, you may ask about our on-duty doctors, consultation fees, or emergency triage.',
                timestamp: timeStr,
                quickActions: [
                    { label: '👨‍⚕️ View Doctor Time Slots', action: () => handleSendPrompt('Show me doctor time slots') },
                    { label: '💰 Check Consultation Fees', action: () => handleSendPrompt('What are the doctor consultation fees?') },
                    { label: '🚨 Emergency Triage Desk', action: () => handleSendPrompt('Emergency helpline') },
                ],
            };
            setMessages((prev) => [...prev, restrictedMsg]);
            return;
        }

        // 2. Emergency Symptoms / Acute Distress
        const isEmergency =
            q.includes('heart attack') ||
            q.includes('chest pain') ||
            q.includes('breath') ||
            q.includes('stroke') ||
            q.includes('unconscious') ||
            q.includes('bleeding') ||
            q.includes('dying') ||
            q.includes('severe pain') ||
            q.includes('accident') ||
            q.includes('emergency') ||
            q.includes('ambulance') ||
            q.includes('trauma');

        if (isEmergency) {
            const alertMsg: ChatMessage = {
                id: 'sys-' + Date.now(),
                sender: 'system-alert',
                text: '🚨 **CRITICAL MEDICAL EMERGENCY PROTOCOL:**\n\nIf you or someone nearby is experiencing acute symptoms (severe chest pain, sudden breathlessness, facial drooping, or heavy bleeding), do not delay. Immediately dial **108** (Ambulance) or our direct hospital trauma desk at **+91-011-2345-6789**.',
                timestamp: timeStr,
                showEmergencyActions: true,
                quickActions: [
                    { label: '🚨 Open Emergency SOS Console', action: () => setActiveLeftTab('emergency') },
                    { label: '📞 Call Ambulance: 108', action: () => { window.location.href = 'tel:108'; } },
                ],
            };
            setMessages((prev) => [...prev, alertMsg]);
            return;
        }

        // 3. Fees & Charges Inquiry
        if (
            q.includes('fee') ||
            q.includes('cost') ||
            q.includes('charge') ||
            q.includes('price') ||
            q.includes('rate') ||
            q.includes('how much')
        ) {
            const feeSummary =
                `💰 **Hospital Consultation & OPD Fee Schedule:**\n\n` +
                `• **General Medicine OPD (Dr. Sunita Rao):** ₹500\n` +
                `• **Pediatrics & Child Health (Dr. Arjun Kumar):** ₹600\n` +
                `• **Dermatology & Skin (Dr. Vikram Reddy):** ₹650\n` +
                `• **Orthopedics & Joint Care (Dr. Kavya Singh):** ₹750\n` +
                `• **Interventional Cardiology (Dr. Rajesh Sharma):** ₹800\n` +
                `• **Neurology & Stroke Care (Dr. Priya Patel):** ₹900\n` +
                `• **Emergency Triage Assessment (Trauma Bay):** ₹1,000\n\n` +
                `✨ **Patient Benefits:**\n` +
                `• All follow-up consultations within 7 days are **100% Free**\n` +
                `• New digital patient registration card: ₹50 (one-time)\n\n` +
                `*To book a confirmed consultation slot, please sign in or register using the panel on the right.*`;

            const replyMsg: ChatMessage = {
                id: 'bot-' + Date.now(),
                sender: 'assistant',
                text: feeSummary,
                timestamp: timeStr,
                quickActions: [
                    { label: '📅 View Specific Doctor Slots', action: () => setActiveLeftTab('doctors') },
                    { label: '⏰ OPD Clinic Hours', action: () => handleSendPrompt('What are the hospital OPD timings?') },
                ],
            };
            setMessages((prev) => [...prev, replyMsg]);
            return;
        }

        // 4. Doctor Inquiry or Specific Specialist Search
        if (
            q.includes('doctor') ||
            q.includes('slot') ||
            q.includes('timing') ||
            q.includes('schedule') ||
            q.includes('appointment') ||
            q.includes('specialist') ||
            q.includes('cardio') ||
            q.includes('neuro') ||
            q.includes('pediatric') ||
            q.includes('ortho') ||
            q.includes('skin') ||
            q.includes('derma') ||
            q.includes('sharma') ||
            q.includes('patel') ||
            q.includes('kumar') ||
            q.includes('singh') ||
            q.includes('reddy') ||
            q.includes('rao')
        ) {
            let matchedDoc: DoctorInfo | undefined;

            if (q.includes('cardio') || q.includes('heart') || q.includes('sharma')) {
                matchedDoc = HOSPITAL_DOCTORS[0];
            } else if (q.includes('neuro') || q.includes('brain') || q.includes('stroke') || q.includes('patel')) {
                matchedDoc = HOSPITAL_DOCTORS[1];
            } else if (q.includes('pediatric') || q.includes('child') || q.includes('baby') || q.includes('kumar')) {
                matchedDoc = HOSPITAL_DOCTORS[2];
            } else if (q.includes('ortho') || q.includes('bone') || q.includes('joint') || q.includes('singh')) {
                matchedDoc = HOSPITAL_DOCTORS[3];
            } else if (q.includes('derma') || q.includes('skin') || q.includes('reddy')) {
                matchedDoc = HOSPITAL_DOCTORS[4];
            } else if (q.includes('general') || q.includes('medicine') || q.includes('fever') || q.includes('rao')) {
                matchedDoc = HOSPITAL_DOCTORS[5];
            }

            if (matchedDoc) {
                const replyMsg: ChatMessage = {
                    id: 'bot-' + Date.now(),
                    sender: 'assistant',
                    text: `Here are the consultation slots and details for **${matchedDoc.name}** (${matchedDoc.specialty}):\n\n• **Qualifications:** ${matchedDoc.qualification}\n• **Consulting Hours:** ${matchedDoc.slots.join(' | ')}\n• **Clinic Location:** ${matchedDoc.room}\n• **Consultation Fee:** ₹${matchedDoc.fee} (${matchedDoc.followUpFee})\n• **Current Status:** ${matchedDoc.status}`,
                    timestamp: timeStr,
                    doctorCard: matchedDoc,
                    quickActions: [
                        { label: '📋 View All 7 Doctors', action: () => setActiveLeftTab('doctors') },
                        { label: '💰 Check All Doctor Fees', action: () => handleSendPrompt('What are all doctor fees?') },
                    ],
                };
                setMessages((prev) => [...prev, replyMsg]);
                return;
            }

            // General Doctor Roster summary
            const docListText =
                `👨‍⚕️ **Hospital Specialist Roster & Available Time Slots:**\n\n` +
                `1. **Dr. Rajesh Sharma** (Cardiology): Mon-Fri 09:00 AM - 01:00 PM (Fee: ₹800)\n` +
                `2. **Dr. Priya Patel** (Neurology): Mon, Wed, Fri 10:00 AM - 02:00 PM (Fee: ₹900)\n` +
                `3. **Dr. Arjun Kumar** (Pediatrics): Mon-Sat 09:30 AM - 03:30 PM (Fee: ₹600)\n` +
                `4. **Dr. Kavya Singh** (Orthopedics): Tue, Thu, Sat 11:00 AM - 04:00 PM (Fee: ₹750)\n` +
                `5. **Dr. Vikram Reddy** (Dermatology): Mon, Wed, Sat 02:00 PM - 06:00 PM (Fee: ₹650)\n` +
                `6. **Dr. Sunita Rao** (Internal Medicine): Mon-Sat 08:30 AM - 02:30 PM (Fee: ₹500)\n` +
                `7. **Dr. Priya Nair** (Emergency Medicine): 24/7 Rotational Coverage\n\n` +
                `*Sign in on the right to reserve your appointment.*`;

            const replyMsg: ChatMessage = {
                id: 'bot-' + Date.now(),
                sender: 'assistant',
                text: docListText,
                timestamp: timeStr,
                quickActions: [
                    { label: '📋 Open Doctor Directory Tab', action: () => setActiveLeftTab('doctors') },
                    { label: '💰 View Fee Details', action: () => handleSendPrompt('Consultation fees') },
                ],
            };
            setMessages((prev) => [...prev, replyMsg]);
            return;
        }

        // 5. Hospital OPD Hours & Timings
        if (q.includes('hour') || q.includes('time') || q.includes('open') || q.includes('opd') || q.includes('visit')) {
            const replyMsg: ChatMessage = {
                id: 'bot-' + Date.now(),
                sender: 'assistant',
                text: `⏰ **Hospital Operating & Visiting Hours:**\n\n• **General Outpatient (OPD):** Monday to Saturday, 08:00 AM - 05:00 PM\n• **Emergency & Trauma Center:** Open 24 Hours, 365 Days a Year\n• **Diagnostic Pathology & Imaging (CT/MRI/X-Ray):** 24/7 Operations\n• **Inpatient Visiting Hours:** Daily 04:00 PM - 07:00 PM\n• **Central Pharmacy (Ground Floor):** Open 24/7`,
                timestamp: timeStr,
                quickActions: [
                    { label: '👨‍⚕️ Available Doctor Slots', action: () => handleSendPrompt('Which doctors are available?') },
                    { label: '🚨 Emergency Assistance', action: () => setActiveLeftTab('emergency') },
                ],
            };
            setMessages((prev) => [...prev, replyMsg]);
            return;
        }

        // 6. Default Fallback
        const defaultMsg: ChatMessage = {
            id: 'bot-' + Date.now(),
            sender: 'assistant',
            text: `I can assist you with your hospital outpatient visit. What would you like to know?\n\n• **Doctor Time Slots:** Inquire about specific specialties or on-duty doctors.\n• **Consultation Fees:** Transparent fee breakdown for general OPD and super-specialists.\n• **Clinic Timings:** OPD consulting and visiting schedules.\n• **Emergency Assistance:** Direct contact with our 24/7 Trauma Bay & Ambulance.`,
            timestamp: timeStr,
            quickActions: [
                { label: '📅 Doctor Time Slots', action: () => handleSendPrompt('Show doctor time slots') },
                { label: '💰 Consultation Fees', action: () => handleSendPrompt('Show consultation fees') },
                { label: '🚨 Emergency Help', action: () => setActiveLeftTab('emergency') },
            ],
        };
        setMessages((prev) => [...prev, defaultMsg]);
    };

    // ─── Emergency Triage Dispatch Trigger ────────────────────────────────────

    const handleTriggerEmergencySOS = () => {
        setDispatchingSOS(true);
        setTimeout(() => {
            const ticketId = 'SOS-' + Math.floor(1000 + Math.random() * 9000);
            setEmergencyTicket(ticketId);
            setDispatchingSOS(false);
        }, 1000);
    };

    return (
        <div className="min-h-screen w-full bg-[#080B14] text-slate-100 flex flex-col lg:grid lg:grid-cols-12 overflow-x-hidden selection:bg-teal-500 selection:text-white">
            {/* ═══════════════════════════════════════════════════════════════════════
                LEFT SIDE: Welcome, Chatbot & Emergency Gateway
                ═══════════════════════════════════════════════════════════════════════ */}
            <div className="lg:col-span-7 xl:col-span-7 flex flex-col justify-between p-6 sm:p-8 lg:p-10 border-b lg:border-b-0 lg:border-r border-slate-800/80 bg-gradient-to-br from-[#0c1222] via-[#090d18] to-[#070912] relative overflow-hidden">
                {/* Background Ambient Glows */}
                <div className="absolute -top-32 -left-32 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute top-1/2 -right-24 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute -bottom-32 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

                <div className="relative z-10 flex flex-col h-full space-y-6">
                    {/* Brand Bar */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-500 to-emerald-400 flex items-center justify-center text-white shadow-lg shadow-teal-500/20">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.3} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                                </svg>
                            </div>
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="text-lg font-extrabold tracking-tight text-white">CarePulse</span>
                                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-500/15 text-teal-400 border border-teal-500/30">
                                        v4.0 Patient Portal
                                    </span>
                                </div>
                                <p className="text-[11px] text-slate-400">Institutional Clinical Care Gateway</p>
                            </div>
                        </div>

                        {/* Emergency Quick Dial Pill */}
                        <a
                            href="tel:108"
                            className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-semibold transition-all shadow-sm group"
                        >
                            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                            <span>Emergency SOS: <strong>108</strong></span>
                        </a>
                    </div>

                    {/* Hero Title & Pill */}
                    <div className="space-y-2">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-slate-800/80 text-teal-300 border border-slate-700/60 shadow-inner">
                            <span className="text-teal-400">✦</span>
                            <span>24/7 Patient Guidance & Instant Triage</span>
                        </div>
                        <h1 className="text-2xl sm:text-3xl xl:text-4xl font-extrabold tracking-tight text-white leading-tight">
                            Intelligent clinical care & instantaneous assistance for every patient.
                        </h1>
                        <p className="text-xs sm:text-sm text-slate-400 max-w-xl">
                            Resolve doctor time slots and consultation fees with our digital concierge, or trigger 24/7 emergency response before signing in.
                        </p>
                    </div>

                    {/* Interactive Feature Tabs */}
                    <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                        <button
                            type="button"
                            onClick={() => setActiveLeftTab('chat')}
                            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                activeLeftTab === 'chat'
                                    ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40 shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                            }`}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                            </svg>
                            <span>💬 Patient Concierge Bot</span>
                        </button>

                        <button
                            type="button"
                            onClick={() => setActiveLeftTab('emergency')}
                            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                activeLeftTab === 'emergency'
                                    ? 'bg-red-500/20 text-red-300 border border-red-500/40 shadow-sm'
                                    : 'text-slate-400 hover:text-red-300 hover:bg-red-500/10'
                            }`}
                        >
                            <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            <span className="font-semibold text-red-400">🚨 Emergency & Trauma SOS</span>
                        </button>

                        <button
                            type="button"
                            onClick={() => setActiveLeftTab('doctors')}
                            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                                activeLeftTab === 'doctors'
                                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm'
                                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                            }`}
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                            </svg>
                            <span>👨‍⚕️ Doctors & Fee Schedule</span>
                        </button>
                    </div>

                    {/* Tab 1: AI Patient Concierge Chatbot */}
                    {activeLeftTab === 'chat' && (
                        <div className="flex-1 flex flex-col min-h-[380px] max-h-[460px] rounded-2xl bg-slate-900/70 border border-slate-800/80 shadow-2xl backdrop-blur-md overflow-hidden">
                            {/* Chat Header */}
                            <div className="px-4 py-3 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between">
                                <div className="flex items-center gap-2.5">
                                    <div className="w-7 h-7 rounded-lg bg-teal-500/20 border border-teal-500/30 flex items-center justify-center text-teal-400">
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                        </svg>
                                    </div>
                                    <div>
                                        <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                                            Hospital Patient Concierge
                                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                        </div>
                                        <div className="text-[10px] text-slate-400">Instant Doctor Slots, Fees & OPD Guidance</div>
                                    </div>
                                </div>
                                <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                                    Safe & Restricted Helpdesk
                                </span>
                            </div>

                            {/* Chat Message Scrollable Container */}
                            <div className="flex-1 p-4 overflow-y-auto space-y-3 text-xs">
                                {messages.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={`flex flex-col ${
                                            msg.sender === 'user' ? 'items-end' : 'items-start'
                                        }`}
                                    >
                                        <div
                                            className={`max-w-[85%] rounded-2xl p-3 sm:p-3.5 space-y-2 leading-relaxed ${
                                                msg.sender === 'user'
                                                    ? 'bg-teal-600 text-white rounded-br-none shadow-md'
                                                    : msg.sender === 'system-alert'
                                                    ? 'bg-red-950/80 text-red-200 border border-red-500/40 rounded-bl-none shadow-lg'
                                                    : 'bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-bl-none shadow-sm'
                                            }`}
                                        >
                                            <div className="whitespace-pre-wrap">{msg.text}</div>

                                            {/* Doctor Card Attachment if present */}
                                            {msg.doctorCard && (
                                                <div className="mt-2 p-2.5 rounded-xl bg-slate-900/90 border border-teal-500/30 text-slate-300 space-y-1">
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-bold text-teal-300">{msg.doctorCard.name}</span>
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                                                            {msg.doctorCard.status}
                                                        </span>
                                                    </div>
                                                    <div className="text-[11px] text-slate-400">{msg.doctorCard.specialty} • {msg.doctorCard.qualification}</div>
                                                    <div className="text-[11px] text-slate-300">📍 {msg.doctorCard.room}</div>
                                                    <div className="text-[11px] font-semibold text-emerald-400">
                                                        Fee: ₹{msg.doctorCard.fee} ({msg.doctorCard.followUpFee})
                                                    </div>
                                                </div>
                                            )}

                                            {/* Quick Actions Buttons */}
                                            {msg.quickActions && (
                                                <div className="flex flex-wrap gap-1.5 pt-1.5 border-t border-slate-700/40">
                                                    {msg.quickActions.map((action, idx) => (
                                                        <button
                                                            key={idx}
                                                            type="button"
                                                            onClick={action.action}
                                                            className="text-[11px] px-2.5 py-1 rounded-md bg-slate-700/60 hover:bg-teal-600 hover:text-white text-slate-300 transition-colors border border-slate-600/50"
                                                        >
                                                            {action.label}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <span className="text-[10px] text-slate-500 mt-1 px-1">
                                            {msg.timestamp}
                                        </span>
                                    </div>
                                ))}

                                {isTyping && (
                                    <div className="flex items-center gap-1.5 text-xs text-slate-400 p-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-bounce" />
                                        <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-bounce [animation-delay:0.2s]" />
                                        <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-bounce [animation-delay:0.4s]" />
                                        <span className="text-[11px] ml-1">Consulting hospital directory...</span>
                                    </div>
                                )}
                                <div ref={chatEndRef} />
                            </div>

                            {/* Chat Input Bar */}
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault();
                                    handleSendMessage();
                                }}
                                className="p-2.5 bg-slate-900 border-t border-slate-800 flex items-center gap-2"
                            >
                                <input
                                    type="text"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    placeholder="Ask doctor slots, fees, timings, or emergency..."
                                    className="flex-1 bg-slate-800/80 border border-slate-700/70 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-500 transition-all"
                                />
                                <button
                                    type="submit"
                                    disabled={!chatInput.trim()}
                                    className="px-3.5 py-2 rounded-xl bg-teal-600 hover:bg-teal-500 disabled:opacity-40 disabled:hover:bg-teal-600 text-white text-xs font-semibold transition-all flex items-center gap-1 shadow-sm"
                                >
                                    <span>Send</span>
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                    </svg>
                                </button>
                            </form>
                        </div>
                    )}

                    {/* Tab 2: Dedicated Emergency & Trauma SOS Center */}
                    {activeLeftTab === 'emergency' && (
                        <div className="flex-1 flex flex-col rounded-2xl bg-slate-900/80 border border-red-500/30 p-5 space-y-4 shadow-2xl backdrop-blur-md overflow-y-auto max-h-[460px]">
                            {/* Emergency Header */}
                            <div className="flex items-center justify-between pb-3 border-b border-red-500/20">
                                <div className="flex items-center gap-2.5">
                                    <div className="w-9 h-9 rounded-xl bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-400">
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-bold text-red-300">24/7 Hospital Emergency & Trauma Desk</h3>
                                        <p className="text-[11px] text-slate-400">Immediate Ambulance, Triage, and Critical Care Dispatch</p>
                                    </div>
                                </div>
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                                    TRAUMA BAY ACTIVE
                                </span>
                            </div>

                            {/* Direct Emergency Call Cards */}
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                                <a
                                    href="tel:108"
                                    className="p-3 rounded-xl bg-red-950/60 border border-red-500/40 hover:bg-red-900/60 transition-all flex flex-col justify-between group"
                                >
                                    <div className="flex items-center justify-between text-xs text-red-300 font-semibold">
                                        <span>Ambulance Direct</span>
                                        <span className="text-xs">🚑</span>
                                    </div>
                                    <div className="text-lg font-black text-white mt-1 group-hover:text-red-300 transition-colors">
                                        108
                                    </div>
                                    <div className="text-[10px] text-slate-400">Toll-free 24/7 Dispatch</div>
                                </a>

                                <a
                                    href="tel:01123456789"
                                    className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:bg-slate-700/80 transition-all flex flex-col justify-between group"
                                >
                                    <div className="flex items-center justify-between text-xs text-teal-300 font-semibold">
                                        <span>Trauma Bay 1</span>
                                        <span className="text-xs">🏥</span>
                                    </div>
                                    <div className="text-sm font-bold text-white mt-1 group-hover:text-teal-300 transition-colors">
                                        +91 011-2345-6789
                                    </div>
                                    <div className="text-[10px] text-slate-400">On-Duty Medical Officer</div>
                                </a>

                                <a
                                    href="tel:112"
                                    className="p-3 rounded-xl bg-slate-800/80 border border-slate-700/80 hover:bg-slate-700/80 transition-all flex flex-col justify-between group"
                                >
                                    <div className="flex items-center justify-between text-xs text-amber-300 font-semibold">
                                        <span>National SOS</span>
                                        <span className="text-xs">🆘</span>
                                    </div>
                                    <div className="text-lg font-black text-white mt-1 group-hover:text-amber-300 transition-colors">
                                        112
                                    </div>
                                    <div className="text-[10px] text-slate-400">Unified Emergency Helpline</div>
                                </a>
                            </div>

                            {/* Emergency Dispatch Ticket Simulator */}
                            <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                                <div className="text-xs font-semibold text-slate-200 flex items-center justify-between">
                                    <span>Trigger Urgent Triage Beacon</span>
                                    <span className="text-[10px] text-slate-400">Instant Hospital Trauma Alert</span>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                                    <div>
                                        <label className="text-[10px] text-slate-400 block mb-1">Select Emergency Type</label>
                                        <select
                                            value={emergencyType}
                                            onChange={(e) => setEmergencyType(e.target.value)}
                                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-red-500"
                                        >
                                            <option>Acute Chest Pain / Cardiac Event</option>
                                            <option>Acute Respiratory Distress / Asthma</option>
                                            <option>Accident / Uncontrolled Bleeding</option>
                                            <option>Stroke (Facial Droop / Paralysis)</option>
                                            <option>Loss of Consciousness / Seizure</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="text-[10px] text-slate-400 block mb-1">Patient Location / Landmark</label>
                                        <input
                                            type="text"
                                            value={emergencyLocation}
                                            onChange={(e) => setEmergencyLocation(e.target.value)}
                                            placeholder="e.g. Ground Floor Gate 2, or Street Address"
                                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                                        >
                                        </input>
                                    </div>
                                </div>

                                {emergencyTicket ? (
                                    <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-xs text-emerald-200 space-y-1">
                                        <div className="font-bold flex items-center gap-1.5 text-emerald-300">
                                            <span>✓ Emergency Alert Dispatched</span>
                                            <span className="font-mono text-[11px] bg-emerald-900/80 px-2 py-0.5 rounded border border-emerald-700">
                                                Ticket #{emergencyTicket}
                                            </span>
                                        </div>
                                        <div className="text-[11px] text-slate-300">
                                            Ambulance unit & trauma nursing team notified for <strong>{emergencyType}</strong>.
                                            {emergencyLocation && <span> Location: <em>{emergencyLocation}</em>.</span>}
                                            {' '}Estimated response: 3-5 mins.
                                        </div>
                                    </div>
                                ) : (
                                    <button
                                        type="button"
                                        onClick={handleTriggerEmergencySOS}
                                        disabled={dispatchingSOS}
                                        className="w-full py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-xs font-bold shadow-lg shadow-red-600/30 transition-all flex items-center justify-center gap-2"
                                    >
                                        {dispatchingSOS ? (
                                            <span>Dispatching Emergency Beacon...</span>
                                        ) : (
                                            <>
                                                <span>🚨 TRIGGER EMERGENCY SOS DISPATCH</span>
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                                </svg>
                                            </>
                                        )}
                                    </button>
                                )}
                            </div>

                            {/* Emergency Action Protocol */}
                            <div className="text-[11px] text-slate-400 space-y-1.5 pt-1">
                                <div className="font-semibold text-slate-300 text-xs">Immediate First-Aid Guidelines:</div>
                                <p>• <strong>Heart Attack:</strong> Sit resting, loosen tight collar, chew Aspirin 300mg if not allergic.</p>
                                <p>• <strong>Stroke (F.A.S.T):</strong> Face drooping, Arm weakness, Speech difficulty → Call 108 instantly.</p>
                                <p>• <strong>Bleeding:</strong> Apply continuous direct pressure with clean cloth. Elevate injured limb.</p>
                            </div>
                        </div>
                    )}

                    {/* Tab 3: Doctors Directory & Fees */}
                    {activeLeftTab === 'doctors' && (
                        <div className="flex-1 flex flex-col rounded-2xl bg-slate-900/80 border border-slate-800 p-4 space-y-3 shadow-2xl backdrop-blur-md overflow-y-auto max-h-[460px]">
                            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                                <div>
                                    <h3 className="text-xs font-bold text-white">Hospital Specialist Directory & Outpatient Slots</h3>
                                    <p className="text-[10px] text-slate-400">Consultation fees include 7-day free follow-up review</p>
                                </div>
                                <span className="text-[10px] px-2 py-0.5 rounded bg-teal-500/10 text-teal-400 border border-teal-500/20">
                                    7 Specialists On Duty
                                </span>
                            </div>

                            <div className="space-y-2.5">
                                {HOSPITAL_DOCTORS.map((doc) => (
                                    <div
                                        key={doc.id}
                                        className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 hover:border-teal-500/40 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                                    >
                                        <div className="space-y-0.5">
                                            <div className="flex items-center gap-2">
                                                <span className="font-bold text-xs text-white">{doc.name}</span>
                                                <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-700 text-slate-300">
                                                    {doc.specialty}
                                                </span>
                                            </div>
                                            <div className="text-[11px] text-slate-400">{doc.qualification} • {doc.room}</div>
                                            <div className="text-[11px] text-teal-300">🕒 {doc.slots.join(' | ')}</div>
                                        </div>
                                        <div className="flex items-center sm:flex-col sm:items-end justify-between sm:justify-center border-t sm:border-t-0 border-slate-700/50 pt-2 sm:pt-0">
                                            <div className="text-xs font-bold text-emerald-400">
                                                ₹{doc.fee}
                                            </div>
                                            <div className="text-[10px] text-slate-400">{doc.followUpFee}</div>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setActiveLeftTab('chat');
                                                    handleSendMessage(`Tell me about ${doc.name} and fees`);
                                                }}
                                                className="text-[10px] text-teal-400 hover:underline mt-1"
                                            >
                                                Ask Bot About Doctor →
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Bottom Testimonial / Trust Seal (Matches the design in the image) */}
                    <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-slate-400">
                        <div className="space-y-0.5">
                            <p className="italic text-slate-300 text-[11px]">
                                &ldquo;CarePulse provides immediate emergency triage access and secure ABDM-compliant health record management for all patients.&rdquo;
                            </p>
                            <p className="text-[10px] text-slate-500 font-medium">
                                Dr. Rajesh Sharma — Chief Medical Officer & Head of Cardiology
                            </p>
                        </div>
                        <div className="flex items-center gap-3 shrink-0 text-[10px] text-slate-500">
                            <span className="flex items-center gap-1">
                                <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                                ABDM Compliant
                            </span>
                            <span>•</span>
                            <span>DPDP Protected</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════════════
                RIGHT SIDE: Patient Login Form (Matches the reference image)
                ═══════════════════════════════════════════════════════════════════════ */}
            <div className="lg:col-span-5 xl:col-span-5 flex flex-col justify-between p-6 sm:p-10 lg:p-12 bg-[#06080F] relative">
                {/* Top Nav: Sign Up Link & Theme Toggle */}
                <div className="flex items-center justify-between sm:justify-end gap-4 w-full">
                    <div className="text-xs text-slate-400">
                        Don&apos;t have an account?{' '}
                        <Link
                            href="/patient/register"
                            className="font-semibold text-teal-400 hover:text-teal-300 hover:underline transition-colors"
                        >
                            Sign Up
                        </Link>
                    </div>
                    <ThemeToggle />
                </div>

                {/* Centered Login Card */}
                <div className="w-full max-w-sm mx-auto my-auto py-8 space-y-6">
                    <div className="space-y-1.5 text-left">
                        <div className="flex items-center justify-between">
                            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                                Welcome back
                            </h2>
                            {backendConnected !== null && (
                                <span
                                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                                        backendConnected
                                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                            : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                                    }`}
                                >
                                    <span
                                        className={`w-1.5 h-1.5 rounded-full ${
                                            backendConnected ? 'bg-emerald-400' : 'bg-amber-400'
                                        }`}
                                    />
                                    {backendConnected ? 'API Online' : 'Connecting API'}
                                </span>
                            )}
                        </div>
                        <p className="text-xs text-slate-400">
                            Enter your credentials to sign in to your patient portal
                        </p>
                    </div>

                    {/* Google / ABDM ABHA Sign-In Button */}
                    <button
                        type="button"
                        onClick={() => handleAutofill('amit')}
                        className="w-full py-2.5 px-4 rounded-xl border border-slate-700/80 bg-slate-900/80 hover:bg-slate-800 text-slate-200 text-xs font-semibold flex items-center justify-center gap-2.5 transition-all shadow-sm"
                    >
                        <svg className="w-4 h-4" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                        </svg>
                        <span>Continue with Google / ABHA</span>
                    </button>

                    <div className="relative flex items-center justify-center">
                        <div className="border-t border-slate-800 w-full" />
                        <span className="bg-[#06080F] px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-widest shrink-0">
                            or continue with credentials
                        </span>
                        <div className="border-t border-slate-800 w-full" />
                    </div>

                    {error && (
                        <Alert
                            variant="error"
                            title="Sign-In Error"
                            onClose={() => setError(null)}
                        >
                            {error}
                        </Alert>
                    )}

                    <Card className="bg-slate-900/60 border-slate-800 shadow-xl backdrop-blur-xl">
                        <CardContent className="p-4 sm:p-5 space-y-4">
                            {/* Credential Switcher: Email vs Mobile Phone */}
                            <div className="grid grid-cols-2 p-1 bg-slate-950 rounded-xl border border-slate-800">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setLoginMethod('email');
                                        setError(null);
                                    }}
                                    className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
                                        loginMethod === 'email'
                                            ? 'bg-slate-800 text-teal-300 shadow-sm'
                                            : 'text-slate-400 hover:text-white'
                                    }`}
                                >
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                    </svg>
                                    <span>Email Address</span>
                                </button>

                                <button
                                    type="button"
                                    onClick={() => {
                                        setLoginMethod('phone');
                                        setError(null);
                                    }}
                                    className={`flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
                                        loginMethod === 'phone'
                                            ? 'bg-slate-800 text-teal-300 shadow-sm'
                                            : 'text-slate-400 hover:text-white'
                                    }`}
                                >
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                                    </svg>
                                    <span>Mobile Phone</span>
                                </button>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-3.5">
                                {loginMethod === 'email' ? (
                                    <Input
                                        id="patientEmail"
                                        label="Email address"
                                        type="email"
                                        required
                                        placeholder="name@example.com"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        disabled={submitting || isLoading}
                                        leadingIcon={
                                            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                            </svg>
                                        }
                                    />
                                ) : (
                                    <Input
                                        id="patientPhone"
                                        label="Registered Mobile Phone"
                                        type="tel"
                                        allowedChars="numeric"
                                        maxLength={15}
                                        required
                                        placeholder="9876543210"
                                        value={phone}
                                        onChange={(e) => setPhone(e.target.value)}
                                        disabled={submitting || isLoading}
                                        leadingIcon={
                                            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                            </svg>
                                        }
                                    />
                                )}

                                <div>
                                    <div className="flex items-center justify-between mb-1">
                                        <label htmlFor="patientPassword" className="text-xs font-medium text-slate-300">
                                            Password
                                        </label>
                                        <button
                                            type="button"
                                            onClick={() => setError('Password reset instructions will be sent to your registered contact.')}
                                            className="text-[11px] text-teal-400 hover:text-teal-300 hover:underline"
                                        >
                                            Forgot password?
                                        </button>
                                    </div>
                                    <Input
                                        id="patientPassword"
                                        type={showPassword ? 'text' : 'password'}
                                        required
                                        placeholder="••••••••••••"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        disabled={submitting || isLoading}
                                        leadingIcon={
                                            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                            </svg>
                                        }
                                        trailingIcon={
                                            showPassword ? (
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                                                </svg>
                                            ) : (
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                                        id="rememberMe"
                                        label="Remember me for 30 days"
                                        checked={rememberMe}
                                        onChange={(e) => setRememberMe(e.target.checked)}
                                    />
                                </div>

                                <Button
                                    type="submit"
                                    variant="primary"
                                    size="lg"
                                    className="w-full justify-center shadow-lg shadow-teal-500/25 bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 text-white font-semibold border-0 mt-2 py-2.5 text-xs sm:text-sm"
                                    isLoading={submitting || isLoading}
                                >
                                    Sign In with Email / Phone
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Quick Demo Logins (Click to autofill) - Exactly as in the reference image */}
                    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                        <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                            <span className="text-teal-400">⚡</span>
                            <span>Quick Demo Logins (Click to autofill)</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                            <button
                                type="button"
                                onClick={() => handleAutofill('amit')}
                                className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 transition-all"
                            >
                                Patient (Amit)
                            </button>
                            <button
                                type="button"
                                onClick={() => handleAutofill('sarah')}
                                className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/30 transition-all"
                            >
                                Patient (Sarah)
                            </button>
                            <button
                                type="button"
                                onClick={() => handleAutofill('mobile')}
                                className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-all"
                            >
                                Mobile (9876511111)
                            </button>
                        </div>
                    </div>
                </div>

                {/* Footer Terms & Legal Disclaimer */}
                <div className="text-center text-[11px] text-slate-500 space-y-1">
                    <p>
                        By clicking continue, you agree to our{' '}
                        <span className="underline hover:text-slate-400 cursor-pointer">Terms of Service</span> and{' '}
                        <span className="underline hover:text-slate-400 cursor-pointer">Privacy Policy</span>.
                    </p>
                    <p className="text-[10px] text-slate-600">
                        256-bit Encrypted Session • Compliant with Indian DPDP Act 2023
                    </p>
                </div>
            </div>
        </div>
    );
}

export default function PatientLoginPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center bg-[#080B14]">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500" />
                </div>
            }
        >
            <PatientLoginForm />
        </Suspense>
    );
}
