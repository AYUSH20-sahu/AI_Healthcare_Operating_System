/**
 * Clinical AI Workflows: Medical Records, Ambient Scribe, Copilot Analysis,
 * M23 Approval Gates, Patient Intake Sessions, and Voice Transcription.
 */

import { api, API_BASE } from './client';
import type { Patient } from './patients';
import type { Doctor } from './doctors';
import type { Appointment } from './appointments';
import type { Medication } from './prescriptions';

export interface AIMetadata {
    provider: string;
    model: string;
    fallback_used: boolean;
    latency_ms: number;
    confidence: number;
    tokens?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number } | null;
}

export interface MedicalRecordContent {
    chief_complaint?: string;
    history_present_illness?: string;
    physical_examination?: string;
    assessment?: string;
    plan?: string;
    diagnosis_codes?: string[];
    [key: string]: unknown;
}

export interface MedicalRecord {
    record_id: string;
    patient_id: string;
    doctor_id: string;
    appointment_id: string | null;
    content: MedicalRecordContent;
    status: 'DRAFT' | 'FINALIZED' | 'AMENDED';
    created_at: string;
    updated_at: string;
    finalized_at: string | null;
    patient?: Patient;
    doctor?: Doctor;
    appointment?: Appointment;
}

export interface MedicalRecordListResponse {
    records: MedicalRecord[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export const medicalRecordsApi = {
    list: (params?: {
        page?: number;
        page_size?: number;
        patient_id?: string;
        doctor_id?: string;
        status?: string;
    }) =>
        api.get<MedicalRecordListResponse>('/medical-records/', params),

    listByPatient: (patientId: string, params?: {
        page?: number;
        page_size?: number;
        status?: string;
    }) =>
        api.get<MedicalRecordListResponse>(`/medical-records/patient/${patientId}/`, params),

    get: (recordId: string) =>
        api.get<MedicalRecord>(`/medical-records/${recordId}/`),

    create: (data: {
        patient_id: string;
        doctor_id: string;
        appointment_id?: string;
        content: Record<string, unknown>;
    }) =>
        api.post<MedicalRecord>('/medical-records/', data),

    update: (recordId: string, data: {
        content?: Record<string, unknown>;
        status?: string;
    }) =>
        api.put<MedicalRecord>(`/medical-records/${recordId}/`, data),

    getAppointmentDraft: (appointmentId: string) =>
        api.get<MedicalRecord | null>(`/medical-records/appointment/${appointmentId}/draft`),
};

export interface CopilotAnalysisRequest {
    transcription?: string;
    patient_id?: string;
    patient_name?: string;
    appointment_id?: string;
    vitals?: Record<string, any>;
    allergies?: any[];
    chief_complaint?: string;
    language?: string;
}

export interface CopilotAnalysisData {
    soap: {
        subjective: {
            chief_complaint: string;
            history_of_present_illness: string;
            review_of_systems?: string;
        };
        objective: {
            vitals_reviewed: string;
            physical_exam: string;
        };
        assessment: {
            primary_diagnosis: string;
            icd10_code: string;
            differentials: string[];
            ai_confidence: number;
            clinical_rationale: string;
        };
        plan: {
            medications: Array<{
                name: string;
                dosage: string;
                frequency: string;
                duration: string;
                instructions?: string;
            }>;
            diagnostics_ordered: string[];
            counseling: string;
            follow_up: string;
        };
    };
    icd10_codes: string[];
    medications: Array<{
        name: string;
        dosage: string;
        frequency: string;
        duration: string;
        instructions?: string;
    }>;
    diagnostics_ordered: string[];
    confidence: number;
}

export interface CopilotAnalysisResponse {
    success: boolean;
    status: 'completed' | 'fallback_to_human' | 'failed' | string;
    task_id: string;
    data: CopilotAnalysisData | null;
    ai_metadata: AIMetadata;
    requires_human_fallback: boolean;
    fallback_reason: string | null;
}

export interface AIProviderHealthResponse {
    active_llm: string;
    active_stt: string;
    llm_providers: string[];
    stt_providers: string[];
    failover_ready: boolean;
}

export const copilotApi = {
    analyze: (data: CopilotAnalysisRequest) =>
        api.post<CopilotAnalysisResponse>('/copilot/analyze', data),

    getProviders: () =>
        api.get<AIProviderHealthResponse>('/copilot/providers'),
};

export interface MedicalRecordApprovalRequest {
    action: 'approve' | 'reject' | 'request_changes';
    reviewer_notes?: string;
    rejection_reason?: string;
    edited_content?: Record<string, any>;
}

export interface MedicalRecordApprovalResponse {
    record_id: string;
    status: string;
    action: string;
    reviewer_id: string;
    reviewed_at: string;
    finalized_at?: string | null;
    reviewer_notes?: string | null;
    rejection_reason?: string | null;
    message: string;
}

export interface PrescriptionApprovalRequest {
    action: 'approve' | 'reject' | 'request_changes';
    reviewer_notes?: string;
    rejection_reason?: string;
    edited_medications?: Medication[];
}

export interface PrescriptionApprovalResponse {
    prescription_id: string;
    status: string;
    action: string;
    reviewer_id: string;
    reviewed_at: string;
    finalized_at?: string | null;
    reviewer_notes?: string | null;
    rejection_reason?: string | null;
    message: string;
}

export interface DraftItem {
    record_id?: string;
    prescription_id?: string;
    patient_id: string;
    patient_name?: string;
    doctor_id: string;
    appointment_id?: string | null;
    medical_record_id?: string | null;
    chief_complaint?: string | null;
    assessment?: string | null;
    confidence?: number | null;
    basis?: string | null;
    medications?: Medication[];
    notes?: string | null;
    content?: Record<string, any>;
    created_at: string;
    updated_at: string;
}

export interface DraftListResponse {
    medical_records: DraftItem[];
    prescriptions: DraftItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export const approvalApi = {
    listDrafts: (params?: { page?: number; page_size?: number }) =>
        api.get<DraftListResponse>('/approval/drafts', params),

    reviewMedicalRecord: (recordId: string, data: MedicalRecordApprovalRequest) =>
        api.post<MedicalRecordApprovalResponse>(`/approval/medical-records/${recordId}/review`, data),

    reviewPrescription: (prescriptionId: string, data: PrescriptionApprovalRequest) =>
        api.post<PrescriptionApprovalResponse>(`/approval/prescriptions/${prescriptionId}/review`, data),

    getMedicalRecord: (recordId: string) =>
        api.get<MedicalRecord>(`/approval/medical-records/${recordId}`),

    getPrescription: (prescriptionId: string) =>
        api.get<any>(`/approval/prescriptions/${prescriptionId}`),
};

export interface VoiceNote {
    voice_note_id: string;
    appointment_id: string;
    doctor_id: string;
    patient_id: string;
    file_path: string;
    file_name: string;
    content_type: string;
    file_size: number;
    duration_seconds?: number;
    transcript?: string;
    transcription_status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
}

export interface VoiceNoteUploadResponse {
    voice_note_id: string;
    message: string;
}

export interface VoiceNoteListResponse {
    voice_notes: VoiceNote[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface ScribeProcessRequest {
    patient_id?: string;
    appointment_id?: string;
    patient_name?: string;
    vitals?: Record<string, any>;
    allergies?: any[];
    chief_complaint?: string;
}

export interface ScribeDraftResponse {
    success: boolean;
    medical_record_id: string;
    appointment_id: string;
    patient_id: string;
    doctor_id: string;
    status: string;
    soap_note: {
        subjective: {
            chief_complaint: string;
            history_of_present_illness: string;
            review_of_systems?: string;
        };
        objective: {
            vitals_reviewed: string;
            physical_exam: string;
        };
        assessment: {
            primary_diagnosis: string;
            icd10_code: string;
            differentials: string[];
            ai_confidence: number;
            clinical_rationale: string;
        };
        plan: {
            medications: Array<{
                name: string;
                dosage: string;
                frequency: string;
                duration: string;
                instructions?: string;
            }>;
            diagnostics_ordered: string[];
            counseling: string;
            follow_up: string;
        };
    };
    confidence: number;
    basis: string;
    transcription: string;
    ai_metadata: AIMetadata;
    created_at: string;
}

export const voiceNotesApi = {
    upload: (formData: FormData) =>
        api.post<VoiceNoteUploadResponse>('/voice-notes/upload/', formData),

    get: (voiceNoteId: string) =>
        api.get<VoiceNote>(`/voice-notes/${voiceNoteId}/`),

    listByAppointment: (appointmentId: string, params?: { page?: number; page_size?: number }) =>
        api.get<VoiceNoteListResponse>(`/voice-notes/appointment/${appointmentId}/`, params),

    update: (voiceNoteId: string, data: { transcript?: string; transcription_status?: string }) =>
        api.put<VoiceNote>(`/voice-notes/${voiceNoteId}/`, data),

    delete: (voiceNoteId: string) =>
        api.delete<void>(`/voice-notes/${voiceNoteId}/`),

    getAudioUrl: (voiceNoteId: string) =>
        `${API_BASE}/voice-notes/${voiceNoteId}/audio`,

    processScribe: (voiceNoteId: string, data?: ScribeProcessRequest) =>
        api.post<ScribeDraftResponse>(`/voice-notes/${voiceNoteId}/scribe`, data || {}),
};

export interface IntakeMessageItem {
    role: 'patient' | 'assistant' | 'user' | string;
    content: string;
    timestamp: string;
}

export interface StructuredSymptoms {
    chief_complaint?: string | null;
    duration?: string | null;
    severity?: number | null;
    associated_symptoms?: string[];
    aggravating_factors?: string[];
    relieving_factors?: string[];
    summary?: string | null;
    has_red_flags?: boolean;
    red_flag_warnings?: string[];
}

export interface IntakeSession {
    session_id: string;
    id?: string;
    patient_id: string;
    status: 'in_progress' | 'completed' | 'cancelled' | 'escalated' | string;
    messages: IntakeMessageItem[];
    structured_symptoms?: StructuredSymptoms | null;
    ai_confidence?: number | null;
    basis?: string | null;
    created_at: string;
    updated_at: string;
    completed_at?: string | null;
}

export interface IntakeMessageResponse {
    session_id: string;
    reply: string;
    is_complete: boolean;
    structured_symptoms: StructuredSymptoms;
    ai_confidence: number;
    basis?: string | null;
    status: string;
}

export interface IntakeVoiceMessageResponse {
    session_id: string;
    transcription: string;
    detected_language: string;
    reply: string;
    audio_base64?: string | null;
    tts_provider: string;
    is_complete: boolean;
    structured_symptoms?: StructuredSymptoms | null;
    ai_confidence?: number | null;
    basis?: string | null;
}

export const intakeApi = {
    createSession: (initialMessage?: string, patientId?: string) =>
        api.post<IntakeSession>('/intake/sessions', { initial_message: initialMessage }, {
            params: patientId ? { patient_id: patientId } : undefined,
        }),
    getActiveSession: (patientId?: string) =>
        api.get<IntakeSession | null>('/intake/sessions/active', {
            params: patientId ? { patient_id: patientId } : undefined,
        }),
    getSessionById: (sessionId: string) =>
        api.get<IntakeSession>(`/intake/sessions/${sessionId}`),
    sendMessage: (sessionId: string, content: string) =>
        api.post<IntakeMessageResponse>(`/intake/sessions/${sessionId}/message`, { content }),
    sendVoiceMessage: (sessionId: string, formData: FormData) =>
        api.post<IntakeVoiceMessageResponse>(`/intake/sessions/${sessionId}/voice-message`, formData),
    completeSession: (sessionId: string, notes?: string) =>
        api.post<IntakeSession>(`/intake/sessions/${sessionId}/complete`, { notes }),
    listSessions: (patientId?: string, limit: number = 20) =>
        api.get<IntakeSession[]>('/intake/sessions', {
            params: {
                ...(patientId ? { patient_id: patientId } : {}),
                limit,
            },
        }),
};

export interface VoiceLanguageDetail {
    code: string;
    name: string;
    native_name: string;
    status: 'validated' | 'experimental' | string;
    stt_supported: boolean;
    tts_supported: boolean;
    tts_voice_id?: string | null;
    web_speech_lang: string;
}

export interface VoiceLanguagesResponse {
    validated_languages: VoiceLanguageDetail[];
    experimental_languages: VoiceLanguageDetail[];
    default_language: string;
    active_stt_provider: string;
    active_tts_provider: string;
}

export interface VoiceTranscriptionResponse {
    text: string;
    language?: string | null;
    provider: string;
    confidence: number;
    duration?: number | null;
    latency_ms: number;
}

export interface VoiceSynthesisRequest {
    text: string;
    language?: string;
    voice?: string;
}

export const voiceApi = {
    getLanguages: () =>
        api.get<VoiceLanguagesResponse>('/voice/languages'),
    transcribeAudio: (file: Blob | File, language?: string) => {
        const formData = new FormData();
        formData.append('file', file, 'recorded_speech.webm');
        return api.post<VoiceTranscriptionResponse>('/voice/transcribe', formData, {
            params: language ? { language } : undefined,
        });
    },
    synthesizeSpeech: async (payload: VoiceSynthesisRequest): Promise<Blob> => {
        const baseOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';
        const url = new URL('/api/v1/voice/synthesize', baseOrigin);
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
        const res = await fetch(url.toString(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            throw new Error(`Speech synthesis error (${res.status})`);
        }
        return res.blob();
    },
};
