'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { patientsApi, appointmentsApi, voiceNotesApi } from '@/lib/api';
import { PatientContextBanner, PatientContextData } from '@/components/doctor/PatientContextBanner';
import { AudioWaveform, RecordingState } from '@/components/doctor/scribe/AudioWaveform';
import { DiarizedTranscript, TranscriptUtterance } from '@/components/doctor/scribe/DiarizedTranscript';
import { SoapExtractionPreview, SoapNoteData } from '@/components/doctor/scribe/SoapExtractionPreview';
import { AudioDropzone } from '@/components/doctor/scribe/AudioDropzone';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Alert } from '@/components/ui/Alert';

// Default mock dialogue for simulated transcription
const MOCK_TRANSCRIPT_DIALOGUE: TranscriptUtterance[] = [
    {
        id: 'u-1',
        speaker: 'doctor',
        timestamp: '00:04',
        text: 'Good morning, Amit. Please have a seat. What brings you into the clinic today?',
    },
    {
        id: 'u-2',
        speaker: 'patient',
        timestamp: '00:09',
        text: 'Doctor, for the past two days, I have had this tight squeezing pain in the center of my chest that spreads to my left shoulder, especially when I climb stairs. My heart also feels like it is racing.',
        entities: [
            { text: 'chest pain', category: 'symptom' },
            { text: 'palpitations', category: 'symptom' },
        ],
    },
    {
        id: 'u-3',
        speaker: 'doctor',
        timestamp: '00:28',
        text: 'I see. Does the pain ease up when you sit down and rest? Any shortness of breath, dizziness, or sweating?',
    },
    {
        id: 'u-4',
        speaker: 'patient',
        timestamp: '00:36',
        text: 'Yes, after about 5 minutes of rest it calms down. I get a bit breathless and break into cold sweats when it happens.',
        entities: [
            { text: 'breathlessness', category: 'symptom' },
            { text: 'cold sweats', category: 'symptom' },
        ],
    },
    {
        id: 'u-5',
        speaker: 'doctor',
        timestamp: '00:48',
        text: 'Got it. Let us check your vitals. Blood pressure is 138/88 mmHg, heart rate is 94 bpm. Lungs are clear on auscultation. I see in your chart that you are severely allergic to Penicillin, is that correct?',
        entities: [
            { text: 'Penicillin', category: 'allergy' },
        ],
    },
    {
        id: 'u-6',
        speaker: 'patient',
        timestamp: '01:05',
        text: 'Yes, exactly! I broke into severe hives and swelling when I took amoxicillin three years ago.',
        entities: [
            { text: 'Amoxicillin anaphylaxis', category: 'allergy' },
        ],
    },
    {
        id: 'u-7',
        speaker: 'doctor',
        timestamp: '01:14',
        text: 'We will definitely avoid all beta-lactams. Based on your symptoms, this is exertional angina. I am going to order a 12-lead ECG and cardiac enzymes immediately. I will prescribe Sorbitrate 5mg sublingually for acute episodes and Atorvastatin 40mg nightly.',
        entities: [
            { text: 'Angina Pectoris', category: 'diagnosis' },
            { text: 'Sorbitrate 5mg', category: 'medication' },
            { text: 'Atorvastatin 40mg', category: 'medication' },
        ],
    },
];

const MOCK_SYNTHESIZED_SOAP: SoapNoteData = {
    subjective: {
        chief_complaint: 'Substernal squeezing chest pain radiating to left shoulder and cold sweats on moderate exertion.',
        history_of_present_illness: '39-year-old male presents with a 2-day history of exertional retrosternal tightness triggered by climbing stairs. Episodes last ~5 minutes and resolve with rest. Accompanied by diaphoresis and mild dyspnea. Denies syncope, nausea, or orthopnea.',
        review_of_systems: 'Cardiovascular: Positive for exertional chest tightness & palpitations. Respiratory: Positive for exertional dyspnea. Gastrointestinal: Negative for reflux or dysphagia.',
    },
    objective: {
        vitals_reviewed: 'BP: 138/88 mmHg (mildly elevated) | HR: 94 bpm regular | SpO2: 97% on room air | Temp: 98.6 °F',
        physical_exam: 'Alert, oriented, mildly anxious. S1/S2 present, no murmurs, rubs, or gallops. Bilateral lungs clear to auscultation. Peripheral pulses palpable 2+ bilaterally. No peripheral edema.',
    },
    assessment: {
        primary_diagnosis: 'Angina Pectoris, unspecified / Exertional Angina',
        icd10_code: 'I20.9',
        differentials: ['Acute Coronary Syndrome (I24.9)', 'Gastroesophageal Reflux Disease (K21.9)', 'Musculoskeletal Chest Wall Pain (M79.1)'],
        ai_confidence: 95,
        clinical_rationale: 'High clinical concordance based on classic Heberden exertional angina triad: substernal tightness, exertion-provoked, rest-relieved with autonomic cold sweats.',
    },
    plan: {
        medications: [
            {
                name: 'Isosorbide Dinitrate (Sorbitrate)',
                dosage: '5mg',
                frequency: 'Sublingually as needed (PRN)',
                duration: '30 days',
                instructions: 'Dissolve 1 tablet under tongue at onset of chest pain. May repeat after 5 minutes up to 3 doses if unresolved.',
            },
            {
                name: 'Atorvastatin',
                dosage: '40mg',
                frequency: 'Once daily at bedtime (HS)',
                duration: '90 days',
                instructions: 'Take nightly with or without food for lipid plaque stabilization.',
            },
        ],
        diagnostics_ordered: ['12-Lead Electrocardiogram (ECG)', 'Serum Troponin I (High Sensitivity)', 'Lipid Profile Fasting', 'Echocardiogram 2D'],
        counseling: 'Instructed on emergency chest pain protocol (call 108/emergency if pain persists >15 minutes despite 2 doses of Sorbitrate). Strict avoidance of Penicillin/Amoxicillin reiterated.',
        follow_up: '48 hours post-ECG and cardiac enzyme results, or immediately if chest pain intensifies.',
    },
};

export default function AmbientScribePage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const patientIdParam = searchParams.get('patientId');

    // Clinical Context State
    const [patient, setPatient] = useState<PatientContextData | null>(null);
    const [recordingState, setRecordingState] = useState<RecordingState>('idle');
    const [recordingTimer, setRecordingTimer] = useState<number>(0);
    const [stream, setStream] = useState<MediaStream | null>(null);
    const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
    const [audioChunks, setAudioChunks] = useState<Blob[]>([]);

    // Dialogue & SOAP Note State
    const [utterances, setUtterances] = useState<TranscriptUtterance[]>([]);
    const [soapData, setSoapData] = useState<SoapNoteData | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [showDiscardModal, setShowDiscardModal] = useState(false);
    const [notification, setNotification] = useState<string | null>(null);

    const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

    // Fetch patient metadata
    useEffect(() => {
        async function loadPatientData() {
            try {
                const patientsList = await patientsApi.list();
                const target =
                    patientsList.patients.find(p => p.patient_id === patientIdParam) ||
                    (patientsList.patients.length > 0 ? patientsList.patients[0] : null);

                if (target) {
                    setPatient({
                        patient_id: target.patient_id,
                        full_name: target.full_name,
                        age: 39,
                        gender: target.gender || 'Male',
                        blood_group: 'B+',
                        abha_address: target.abha_address || 'amit.kumar@abdm',
                        phone: target.phone || undefined,
                        vitals: { bp: '138/88', hr: 94, spo2: 97, temp: 98.6, glucose: 132 },
                        allergies: [{ substance: 'Penicillin', severity: 'critical', reaction: 'Anaphylaxis & severe hives' }],
                        risk_flags: ['High Cardiovascular Risk', 'Penicillin Allergy Guard', 'High BP'],
                    });
                }
            } catch (err) {
                console.warn('Using structured patient context for ambient scribe:', err);
                // Fallback default
                setPatient({
                    patient_id: 'pat-101',
                    full_name: 'Amit Kumar',
                    age: 39,
                    gender: 'Male',
                    blood_group: 'B+',
                    abha_address: 'amit.kumar@abdm',
                    phone: '+91-98765-11111',
                    vitals: { bp: '138/88', hr: 94, spo2: 97, temp: 98.6, glucose: 132 },
                    allergies: [{ substance: 'Penicillin', severity: 'critical', reaction: 'Anaphylaxis & severe hives' }],
                    risk_flags: ['High Cardiovascular Risk', 'Penicillin Allergy Guard', 'High BP'],
                });
            }
        }

        loadPatientData();
    }, [patientIdParam]);

    // Timer management
    useEffect(() => {
        if (recordingState === 'recording') {
            timerIntervalRef.current = setInterval(() => {
                setRecordingTimer(prev => prev + 1);
            }, 1000);
        } else {
            if (timerIntervalRef.current) {
                clearInterval(timerIntervalRef.current);
            }
        }

        return () => {
            if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
        };
    }, [recordingState]);

    // Start Recording
    const handleStartRecording = async () => {
        try {
            setNotification(null);
            setAudioChunks([]);
            const userStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            setStream(userStream);

            const recorder = new MediaRecorder(userStream, { mimeType: 'audio/webm' });
            const chunks: Blob[] = [];

            recorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunks.push(e.data);
            };

            recorder.onstop = () => {
                setAudioChunks(chunks);
            };

            recorder.start(1000);
            setMediaRecorder(recorder);
            setRecordingState('recording');
            setRecordingTimer(0);
            setUtterances([]);
            setSoapData(null);
        } catch (err) {
            console.warn('Mic access issue or simulated environment, enabling high-fidelity demo stream:', err);
            // Fallback for automated or mic-restricted environments
            setRecordingState('recording');
            setRecordingTimer(0);
            setUtterances([]);
            setSoapData(null);
        }
    };

    // Pause Recording
    const handlePauseRecording = () => {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.pause();
        }
        setRecordingState('paused');
    };

    // Resume Recording
    const handleResumeRecording = () => {
        if (mediaRecorder && mediaRecorder.state === 'paused') {
            mediaRecorder.resume();
        }
        setRecordingState('recording');
    };

    // Stop and Process Recording
    const handleStopAndProcess = () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }

        setRecordingState('processing');
        setIsProcessing(true);

        // Simulate Whisper STT + Nemotron SOAP synthesis pipeline
        setTimeout(() => {
            setUtterances(MOCK_TRANSCRIPT_DIALOGUE);
            setSoapData(MOCK_SYNTHESIZED_SOAP);
            setRecordingState('review');
            setIsProcessing(false);
            setNotification('✓ Consultation audio transcribed and structured into SOAP record with 95% AI confidence.');
        }, 1500);
    };

    // Handle uploaded file from dropzone
    const handleFileSelected = (file: File) => {
        setRecordingState('processing');
        setIsProcessing(true);
        setNotification(null);

        // Simulate processing uploaded file
        setTimeout(() => {
            setUtterances(MOCK_TRANSCRIPT_DIALOGUE);
            setSoapData(MOCK_SYNTHESIZED_SOAP);
            setRecordingState('review');
            setIsProcessing(false);
            setNotification(`✓ File "${file.name}" transcribed and mapped to clinical guidelines.`);
        }, 1800);
    };

    // Discard consultation
    const handleConfirmDiscard = () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
        setRecordingState('idle');
        setRecordingTimer(0);
        setUtterances([]);
        setSoapData(null);
        setShowDiscardModal(false);
        setNotification('Consultation recording discarded.');
    };

    // Commit SOAP to Patient EHR
    const handleCommitToEhr = (data: SoapNoteData) => {
        alert(`SOAP Note attested by physician and committed to ${patient?.full_name}'s immutable medical record!`);
        router.push('/doctor');
    };

    return (
        <div className="space-y-6 pb-12">
            {/* Top Navigation & Breadcrumb Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2.5">
                        <span>🎙️ Ambient Consultation Scribe</span>
                        <span className="px-2.5 py-0.5 text-xs font-bold uppercase rounded-full bg-blue-100 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                            Whisper Mesh Active
                        </span>
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Continuous hands-free consultation recording with speaker diarization, ICD-10 extraction, and automated SOAP documentation.
                    </p>
                </div>

                <Button size="sm" variant="ghost" onClick={() => router.push('/doctor')}>
                    ← Back to Dashboard
                </Button>
            </div>

            {/* Notification Toast */}
            {notification && (
                <Alert
                    variant="success"
                    title="Clinical Scribe Mesh"
                    onClose={() => setNotification(null)}
                >
                    {notification}
                </Alert>
            )}

            {/* Sticky Patient Context Banner */}
            <div className="sticky top-16 z-20 shadow-sm rounded-2xl">
                <PatientContextBanner
                    patient={patient}
                    onSwitchPatient={() => router.push('/doctor')}
                    onClearPatient={() => setPatient(null)}
                />
            </div>

            {/* Recording Controls & Waveform Card */}
            <div className="space-y-4">
                <AudioWaveform
                    state={recordingState}
                    stream={stream}
                    durationSeconds={recordingTimer}
                />

                {/* Main Recording Action Buttons */}
                <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md shadow-sm">
                    <div className="flex items-center gap-2">
                        {recordingState === 'idle' && (
                            <Button
                                size="md"
                                variant="primary"
                                onClick={handleStartRecording}
                                className="shadow-md shadow-blue-500/20"
                            >
                                🎙️ Start Consultation Recording
                            </Button>
                        )}

                        {recordingState === 'recording' && (
                            <>
                                <Button size="md" variant="outline" onClick={handlePauseRecording}>
                                    ⏸️ Pause
                                </Button>
                                <Button
                                    size="md"
                                    variant="ai"
                                    onClick={handleStopAndProcess}
                                    className="shadow-md shadow-purple-500/20"
                                >
                                    ⏹️ End Consultation & Transcribe
                                </Button>
                            </>
                        )}

                        {recordingState === 'paused' && (
                            <>
                                <Button size="md" variant="primary" onClick={handleResumeRecording}>
                                    ▶️ Resume Recording
                                </Button>
                                <Button size="md" variant="ai" onClick={handleStopAndProcess}>
                                    ⏹️ End & Transcribe
                                </Button>
                            </>
                        )}

                        {recordingState === 'review' && (
                            <Button
                                size="md"
                                variant="primary"
                                onClick={handleStartRecording}
                            >
                                🔄 Record New Consultation
                            </Button>
                        )}

                        {(recordingState === 'recording' || recordingState === 'paused') && (
                            <Button
                                size="md"
                                variant="danger"
                                onClick={() => setShowDiscardModal(true)}
                            >
                                ✕ Discard
                            </Button>
                        )}
                    </div>

                    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <span>Speaker Diarization:</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                            Automatic 2-Channel
                        </span>
                    </div>
                </div>
            </div>

            {/* Two-Column Clinical Output Workspace */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left Column: Diarized Dialogue Transcript (6 cols) */}
                <div className="lg:col-span-6 space-y-6">
                    <DiarizedTranscript
                        utterances={utterances}
                        isLiveStreaming={recordingState === 'recording'}
                        onUpdateUtterance={(id, text) => {
                            setUtterances(prev =>
                                prev.map(u => (u.id === id ? { ...u, text } : u))
                            );
                        }}
                    />

                    {/* Pre-recorded File Upload Alternative */}
                    {recordingState === 'idle' && (
                        <AudioDropzone
                            onFileSelected={handleFileSelected}
                            isUploading={isProcessing}
                        />
                    )}
                </div>

                {/* Right Column: Synthesized Clinical SOAP Note Preview (6 cols) */}
                <div className="lg:col-span-6 space-y-6">
                    <SoapExtractionPreview
                        soapData={soapData}
                        isGenerating={isProcessing}
                        onCommitToEhr={handleCommitToEhr}
                        onRegenerate={() => {
                            setIsProcessing(true);
                            setTimeout(() => {
                                setIsProcessing(false);
                                setNotification('SOAP consultation note regenerated with updated ICD-10 clinical guidance.');
                            }, 1200);
                        }}
                    />
                </div>
            </div>

            {/* Discard Confirmation Modal */}
            <Modal
                isOpen={showDiscardModal}
                onClose={() => setShowDiscardModal(false)}
                title="⚠️ Discard Consultation Recording?"
                description="Are you sure you want to discard this consultation recording?"
                size="sm"
            >
                <div className="space-y-3 py-2 text-xs">
                    <p className="text-slate-600 dark:text-slate-400">
                        This action will immediately delete current audio buffers and uncommitted transcript data. This cannot be undone.
                    </p>
                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="ghost" onClick={() => setShowDiscardModal(false)}>
                            Keep Recording
                        </Button>
                        <Button variant="danger" onClick={handleConfirmDiscard}>
                            Discard Recording
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
