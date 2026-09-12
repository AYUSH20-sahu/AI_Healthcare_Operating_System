/**
 * API client for AI-HOS frontend
 * Communicates with the backend API at /api/v1
 */

const API_BASE = '/api/v1';

export interface User {
    user_id: string;
    email: string;
    full_name: string;
    role: 'patient' | 'doctor' | 'admin' | 'nurse' | 'receptionist' | string;
    is_active: boolean;
    created_at: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface SignupRequest {
    email: string;
    password: string;
    full_name: string;
    role?: string;
}

interface RequestOptions extends RequestInit {
    params?: Record<string, string | number | boolean | undefined>;
    _retry?: boolean;
}

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
    refreshSubscribers.push(cb);
}

function onTokenRefreshed(token: string) {
    refreshSubscribers.forEach((cb) => cb(token));
    refreshSubscribers = [];
}

async function request<T>(
    endpoint: string,
    options: RequestOptions = {}
): Promise<T> {
    const { params, headers, _retry, ...fetchOptions } = options;

    const baseOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';
    // Build URL with query parameters
    const url = new URL(`${API_BASE}${endpoint}`, baseOrigin);
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, String(value));
            }
        });
    }

    // Get auth token from localStorage safely
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    const isFormData = typeof FormData !== 'undefined' && fetchOptions.body instanceof FormData;
    const defaultHeaders: HeadersInit = {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
    };

    const response = await fetch(url.toString(), {
        ...fetchOptions,
        headers: defaultHeaders,
    });

    // Handle 401 Unauthorized with token refresh if possible
    if (response.status === 401 && !_retry && typeof window !== 'undefined') {
        const refreshToken = localStorage.getItem('refresh_token');
        const isAuthEndpoint = endpoint.includes('/auth/login') || endpoint.includes('/auth/refresh') || endpoint.includes('/auth/signup');

        if (refreshToken && !isAuthEndpoint) {
            if (!isRefreshing) {
                isRefreshing = true;
                try {
                    const refreshUrl = new URL(`${API_BASE}/auth/refresh`, baseOrigin);
                    refreshUrl.searchParams.append('refresh_token', refreshToken);

                    const refreshRes = await fetch(refreshUrl.toString(), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                    });

                    if (refreshRes.ok) {
                        const newTokens: TokenResponse = await refreshRes.json();
                        localStorage.setItem('access_token', newTokens.access_token);
                        localStorage.setItem('refresh_token', newTokens.refresh_token);
                        isRefreshing = false;
                        onTokenRefreshed(newTokens.access_token);
                        // Retry original request
                        return request<T>(endpoint, { ...options, _retry: true });
                    } else {
                        throw new Error('Refresh failed');
                    }
                } catch {
                    isRefreshing = false;
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    localStorage.removeItem('auth_user');
                    window.dispatchEvent(new CustomEvent('aihos:auth_expired'));
                }
            } else {
                // Wait for refreshing process
                return new Promise<T>((resolve, reject) => {
                    subscribeTokenRefresh(() => {
                        request<T>(endpoint, { ...options, _retry: true })
                            .then(resolve)
                            .catch(reject);
                    });
                });
            }
        }
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        let message = `HTTP ${response.status}`;
        if (typeof error.detail === 'string') {
            message = error.detail;
        } else if (Array.isArray(error.detail)) {
            message = error.detail.map((d: { msg?: string }) => d.msg || 'Validation error').join(', ');
        } else if (error.error?.message) {
            message = error.error.message;
        }
        throw new Error(message);
    }

    // Handle 204 No Content
    if (response.status === 204) {
        return undefined as T;
    }

    return response.json();
}

export const api = {
    get: <T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>) =>
        request<T>(endpoint, { method: 'GET', params }),

    post: <T>(endpoint: string, data?: unknown, params?: Record<string, string | number | boolean | undefined>) => {
        const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
        return request<T>(endpoint, {
            method: 'POST',
            body: isFormData ? (data as FormData) : data !== undefined ? JSON.stringify(data) : undefined,
            params,
        });
    },

    put: <T>(endpoint: string, data: unknown) =>
        request<T>(endpoint, { method: 'PUT', body: JSON.stringify(data) }),

    patch: <T>(endpoint: string, data?: unknown) =>
        request<T>(endpoint, { method: 'PATCH', body: data !== undefined ? JSON.stringify(data) : undefined }),

    delete: <T>(endpoint: string) =>
        request<T>(endpoint, { method: 'DELETE' }),
};

// Auth API
export const authApi = {
    login: (credentials: LoginRequest) =>
        api.post<TokenResponse>('/auth/login', credentials),

    signup: (data: SignupRequest) =>
        api.post<User>('/auth/signup', data),

    refresh: (refreshToken: string) =>
        api.post<TokenResponse>('/auth/refresh', undefined, { refresh_token: refreshToken }),

    me: () =>
        api.get<User>('/auth/me'),
};


// Types matching backend schemas
export interface Patient {
    patient_id: string;
    user_id: string | null;
    abha_address: string | null;
    full_name: string;
    date_of_birth: string;
    gender: string;
    phone: string | null;
    email: string | null;
    address: string | null;
    emergency_contact_name: string | null;
    emergency_contact_phone: string | null;
    created_at: string;
    updated_at: string;
}

export interface PatientListResponse {
    patients: Patient[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface Doctor {
    doctor_id: string;
    user_id: string | null;
    specialty: string;
    license_number: string;
    hospital_affiliation: string | null;
    email: string;
    full_name: string;
    phone: string | null;
    created_at: string;
    updated_at: string;
}

export interface DoctorListResponse {
    doctors: Doctor[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface Appointment {
    appointment_id: string;
    patient_id: string;
    doctor_id: string;
    scheduled_at: string;
    duration_minutes: number;
    status: 'scheduled' | 'completed' | 'cancelled' | 'no_show';
    notes: string | null;
    created_at: string;
    updated_at: string;
    patient?: Patient;
    doctor?: Doctor;
}

export interface AppointmentListResponse {
    appointments: Appointment[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
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

export interface Prescription {
    prescription_id: string;
    medical_record_id: string | null;
    patient_id: string;
    doctor_id: string;
    medications: Medication[];
    status: 'DRAFT' | 'FINALIZED' | 'CANCELLED';
    created_at: string;
    updated_at: string;
    finalized_at: string | null;
    patient?: Patient;
    doctor?: Doctor;
    medical_record?: MedicalRecord;
}

export interface Medication {
    name: string;
    dosage: string;
    frequency: string;
    duration: string;
    route?: string;
    instructions?: string;
    quantity?: number;
    refills?: number;
}

export interface PrescriptionListResponse {
    prescriptions: Prescription[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

// Patient API
export const patientsApi = {
    list: (params?: { page?: number; page_size?: number; search?: string }) =>
        api.get<PatientListResponse>('/patients/', params),

    get: (patientId: string) =>
        api.get<Patient>(`/patients/${patientId}/`),

    create: (data: Partial<Patient>) =>
        api.post<Patient>('/patients/', data),

    update: (patientId: string, data: Partial<Patient>) =>
        api.put<Patient>(`/patients/${patientId}/`, data),
};

// Doctor API
export const doctorsApi = {
    list: (params?: { page?: number; page_size?: number; specialty?: string }) =>
        api.get<DoctorListResponse>('/doctors/', params),

    get: (doctorId: string) =>
        api.get<Doctor>(`/doctors/${doctorId}/`),

    create: (data: Partial<Doctor>) =>
        api.post<Doctor>('/doctors/', data),

    update: (doctorId: string, data: Partial<Doctor>) =>
        api.put<Doctor>(`/doctors/${doctorId}/`, data),
};

// Appointments API
export const appointmentsApi = {
    list: (params?: {
        page?: number;
        page_size?: number;
        patient_id?: string;
        doctor_id?: string;
        status?: string;
        date_from?: string;
        date_to?: string;
    }) =>
        api.get<AppointmentListResponse>('/appointments/', params),

    get: (appointmentId: string) =>
        api.get<Appointment>(`/appointments/${appointmentId}/`),

    create: (data: {
        patient_id: string;
        doctor_id: string;
        scheduled_at: string;
        duration_minutes?: number;
        notes?: string;
    }) =>
        api.post<Appointment>('/appointments/', data),

    update: (appointmentId: string, data: Partial<Appointment>) =>
        api.put<Appointment>(`/appointments/${appointmentId}/`, data),

    cancel: (appointmentId: string) =>
        api.delete<void>(`/appointments/${appointmentId}/`),
};

// Medical Records API
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

// Prescriptions API
export interface PrescriptionDraftRequest {
    patient_id: string;
    doctor_id: string;
    appointment_id?: string;
    medical_record_id?: string;
    consultation_text?: string;
    assessment?: string;
    icd10_code?: string;
    suggested_medications?: Medication[];
    patient_allergies?: string[];
    current_medications?: string[];
    notes?: string;
}

export interface PrescriptionDraftResponse {
    prescription_id: string;
    patient_id: string;
    doctor_id: string;
    appointment_id?: string;
    medical_record_id?: string;
    medications: Medication[];
    status: string;
    warnings: InteractionWarning[];
    has_warnings: boolean;
    confidence: number;
    basis: string;
    ai_metadata: AIMetadata;
    notes?: string;
    created_at: string;
    updated_at: string;
}

export const prescriptionsApi = {
    list: (params?: {
        page?: number;
        page_size?: number;
        patient_id?: string;
        doctor_id?: string;
        status?: string;
    }) =>
        api.get<PrescriptionListResponse>('/prescriptions/', params),

    listByPatient: (patientId: string, params?: {
        page?: number;
        page_size?: number;
        status?: string;
    }) =>
        api.get<PrescriptionListResponse>(`/prescriptions/patient/${patientId}/`, params),

    listByAppointment: (appointmentId: string, params?: {
        page?: number;
        page_size?: number;
    }) =>
        api.get<PrescriptionListResponse>(`/prescriptions/appointment/${appointmentId}/`, params),

    get: (prescriptionId: string) =>
        api.get<Prescription>(`/prescriptions/${prescriptionId}/`),

    getAppointmentDraft: (appointmentId: string) =>
        api.get<PrescriptionDraftResponse | null>(`/prescriptions/appointment/${appointmentId}/draft`),

    create: (data: {
        patient_id: string;
        doctor_id: string;
        medical_record_id?: string;
        medications: Medication[];
        notes?: string;
    }) =>
        api.post<Prescription>('/prescriptions/', data),

    draft: (data: PrescriptionDraftRequest) =>
        api.post<PrescriptionDraftResponse>('/prescriptions/draft', data),

    update: (prescriptionId: string, data: {
        medications?: Medication[];
        notes?: string;
        status?: string;
    }) =>
        api.put<Prescription>(`/prescriptions/${prescriptionId}/`, data),

    checkInteractions: (
        patientId: string,
        medications: Medication[],
        patientAllergies?: string[],
        currentMedications?: string[]
    ) =>
        api.post<{ warnings: InteractionWarning[]; has_warnings: boolean }>(
            '/prescriptions/check-interactions/',
            {
                patient_id: patientId,
                medications,
                patient_allergies: patientAllergies,
                current_medications: currentMedications,
            }
        ),
};

export interface InteractionWarning {
    severity: 'mild' | 'moderate' | 'severe';
    type: 'interaction' | 'allergy';
    medication: string;
    description: string;
    recommendation?: string;
}

// Voice Notes API
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

export interface AdminDoctorProfile {
    doctor_id: string;
    specialty: string;
    license_number: string;
    hospital_affiliation?: string;
    phone?: string;
}

export interface AdminUser {
    user_id: string;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    created_at: string;
    doctor_profile?: AdminDoctorProfile;
}

export interface AdminUserListResponse {
    users: AdminUser[];
    total: number;
    limit: number;
    offset: number;
}

export interface ProvisionUserRequest {
    email: string;
    password: string;
    full_name: string;
    role: 'doctor' | 'nurse' | 'receptionist' | 'admin' | 'patient';
    specialty?: string;
    license_number?: string;
    hospital_affiliation?: string;
    phone?: string;
}

export const adminUsersApi = {
    list: (params?: { role?: string; is_active?: boolean; search?: string; limit?: number; offset?: number }) =>
        api.get<AdminUserListResponse>('/admin/users/', params),

    provision: (data: ProvisionUserRequest) =>
        api.post<AdminUser>('/admin/users/', data),

    toggleStatus: (userId: string, isActive: boolean) =>
        api.patch<AdminUser>(`/admin/users/${userId}/status`, { is_active: isActive }),

    updateRole: (userId: string, newRole: string, specialty?: string, licenseNumber?: string) =>
        api.patch<AdminUser>(`/admin/users/${userId}/role`, {
            new_role: newRole,
            specialty,
            license_number: licenseNumber,
        }),

    deleteUser: (userId: string) =>
        api.delete<{ detail: string; user_id: string }>(`/admin/users/${userId}`),

    resetPassword: (userId: string, newPassword: string) =>
        api.post<{ message: string }>(`/admin/users/${userId}/reset-password`, { new_password: newPassword }),
};


export interface AIMetadata {
    provider: string;
    model: string;
    fallback_used: boolean;
    latency_ms: number;
    confidence: number;
    tokens?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number } | null;
}

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

// Approval Gate API (M23 / U-11)
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
        api.get<Prescription>(`/approval/prescriptions/${prescriptionId}`),
};

// Patient Portal API (Milestone U-12)
export interface PatientSelfUpdate {
    full_name?: string;
    phone?: string;
    address?: string;
    emergency_contact_name?: string;
    emergency_contact_phone?: string;
    abha_address?: string;
}

export interface PatientPortalAppointmentItem {
    appointment_id: string;
    doctor_id: string;
    doctor_name: string;
    doctor_specialty?: string | null;
    hospital_affiliation?: string | null;
    scheduled_at: string;
    duration_minutes: number;
    status: string;
    reason?: string | null;
    meeting_link?: string | null;
}

export interface PatientPortalRecordItem {
    record_id: string;
    doctor_id: string;
    doctor_name: string;
    appointment_id?: string | null;
    status: string;
    chief_complaint?: string | null;
    assessment?: string | null;
    plan?: string | null;
    content?: Record<string, any> | null;
    finalized_at?: string | null;
    created_at: string;
}

export interface PatientPortalPrescriptionItem {
    prescription_id: string;
    doctor_id: string;
    doctor_name: string;
    medical_record_id?: string | null;
    status: string;
    medications: Medication[];
    notes?: string | null;
    finalized_at?: string | null;
    created_at: string;
}

export interface PatientPortalDashboardResponse {
    patient: Patient;
    upcoming_appointments_count: number;
    finalized_records_count: number;
    active_prescriptions_count: number;
    next_appointment?: PatientPortalAppointmentItem | null;
    recent_prescriptions: PatientPortalPrescriptionItem[];
}

export const patientPortalApi = {
    getProfile: () => api.get<Patient>('/patients/me'),
    updateProfile: (data: PatientSelfUpdate) => api.put<Patient>('/patients/me', data),
    getDashboard: () => api.get<PatientPortalDashboardResponse>('/patients/me/dashboard'),
    getAppointments: () => api.get<PatientPortalAppointmentItem[]>('/patients/me/appointments'),
    getRecords: () => api.get<PatientPortalRecordItem[]>('/patients/me/records'),
    getPrescriptions: () => api.get<PatientPortalPrescriptionItem[]>('/patients/me/prescriptions'),
    cancelAppointment: (appointmentId: string) => api.delete<void>(`/appointments/${appointmentId}/`),
};

// =============================================================================
// AI Patient Intake & Symptom Collection API (Milestone U-13 / M25)
// =============================================================================

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

// =============================================================================
// Telehealth & Doctor Schedule API (Milestone U-14)
// =============================================================================

export interface PatientIntakeSummary {
    session_id?: string | null;
    chief_complaint?: string | null;
    duration?: string | null;
    severity?: number | null;
    associated_symptoms?: string[];
    summary?: string | null;
    has_red_flags: boolean;
    red_flag_warnings: string[];
}

export interface DoctorScheduleItem {
    appointment_id: string;
    patient_id: string;
    patient_name: string;
    patient_gender?: string | null;
    patient_age?: number | null;
    patient_abha?: string | null;
    patient_phone?: string | null;
    scheduled_at: string;
    duration_minutes: number;
    status: string;
    meeting_link?: string | null;
    telehealth_room_id?: string | null;
    notes?: string | null;
    intake_summary?: PatientIntakeSummary | null;
}

export interface DoctorScheduleResponse {
    date: string;
    total_appointments: number;
    scheduled_count: number;
    in_consultation_count: number;
    completed_count: number;
    appointments: DoctorScheduleItem[];
}

export interface TelehealthRoomData {
    appointment_id: string;
    room_id: string;
    meeting_link: string;
    status: string;
    doctor_id: string;
    doctor_name: string;
    doctor_specialty: string;
    doctor_hospital?: string | null;
    patient_id: string;
    patient_name: string;
    patient_gender?: string | null;
    patient_age?: number | null;
    patient_abha?: string | null;
    patient_phone?: string | null;
    scheduled_at: string;
    duration_minutes: number;
    intake_summary?: PatientIntakeSummary | null;
    telehealth_started_at?: string | null;
    telehealth_ended_at?: string | null;
}

export interface TelehealthActionResponse {
    appointment_id: string;
    status: string;
    message: string;
    meeting_link?: string | null;
    telehealth_started_at?: string | null;
    telehealth_ended_at?: string | null;
}

export const telehealthApi = {
    getDoctorSchedule: (dateStr?: string) =>
        api.get<DoctorScheduleResponse>('/telehealth/schedule', {
            params: dateStr ? { date_str: dateStr } : undefined,
        }),
    getRoom: (appointmentId: string) =>
        api.get<TelehealthRoomData>(`/telehealth/rooms/${appointmentId}`),
    startRoom: (appointmentId: string) =>
        api.post<TelehealthActionResponse>(`/telehealth/rooms/${appointmentId}/start`, {}),
    endRoom: (appointmentId: string) =>
        api.post<TelehealthActionResponse>(`/telehealth/rooms/${appointmentId}/end`, {}),
};

// =============================================================================
// Appointment Availability & Booking API (Milestone U-15 / M28)
// =============================================================================

export interface TimeSlotItem {
    slot_time: string;
    start_time: string;
    end_time: string;
    duration_minutes: number;
    is_available: boolean;
    conflict_reason?: string | null;
}

export interface DoctorAvailabilityResponse {
    doctor_id: string;
    doctor_name: string;
    specialty: string;
    hospital_affiliation?: string | null;
    date: string;
    total_slots: number;
    available_slots_count: number;
    slots: TimeSlotItem[];
}

export interface PatientAppointmentBookRequest {
    doctor_id: string;
    scheduled_at: string;
    duration_minutes?: number;
    reason?: string | null;
    intake_session_id?: string | null;
}

export const appointmentBookingApi = {
    getSpecialties: () =>
        api.get<string[]>('/doctors/specialties'),
    getDoctors: (specialty?: string, page: number = 1, pageSize: number = 50) =>
        api.get<DoctorListResponse>('/doctors', {
            params: {
                page,
                page_size: pageSize,
                ...(specialty && specialty !== 'All' ? { specialty } : {}),
            },
        }),
    getAvailability: (doctorId: string, dateStr: string, durationMinutes: number = 30) =>
        api.get<DoctorAvailabilityResponse>('/appointments/availability', {
            params: {
                doctor_id: doctorId,
                date_str: dateStr,
                duration_minutes: durationMinutes,
            },
        }),
    bookAppointment: (data: PatientAppointmentBookRequest) =>
        api.post<Appointment>('/appointments/book', data),
};

// =============================================================================
// Milestone U-16: Patient Reports & Medicine Reminders
// =============================================================================

export interface PatientReportItem {
    report_id: string;
    patient_id: string;
    title: string;
    report_type: 'lab' | 'imaging' | 'prescription' | 'discharge' | 'other' | string;
    file_name: string;
    file_size_bytes: number;
    mime_type: string;
    notes?: string | null;
    created_at: string;
    updated_at: string;
}

export interface PatientReportListResponse {
    reports: PatientReportItem[];
    total: number;
}

export interface MedicineReminderItem {
    reminder_id: string;
    patient_id: string;
    medication_name: string;
    dosage: string;
    frequency: string;
    times_of_day: string[];
    instructions?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface MedicineReminderListResponse {
    reminders: MedicineReminderItem[];
    total: number;
}

export interface MedicineReminderCreatePayload {
    medication_name: string;
    dosage: string;
    frequency: string;
    times_of_day: string[];
    instructions?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    is_active?: boolean;
}

export interface MedicineReminderUpdatePayload {
    medication_name?: string;
    dosage?: string;
    frequency?: string;
    times_of_day?: string[];
    instructions?: string | null;
    start_date?: string | null;
    end_date?: string | null;
    is_active?: boolean;
}

export const patientReportsApi = {
    list: (reportType?: string) =>
        api.get<PatientReportListResponse>('/patients/me/reports', {
            params: reportType && reportType !== 'all' ? { report_type: reportType } : undefined,
        }),
    get: (reportId: string) =>
        api.get<PatientReportItem>(`/patients/me/reports/${reportId}`),
    upload: (formData: FormData) =>
        api.post<PatientReportItem>('/patients/me/reports', formData),
    delete: (reportId: string) =>
        api.delete<{ detail: string; report_id: string }>(`/patients/me/reports/${reportId}`),
    getDownloadUrl: (reportId: string) =>
        `/api/v1/patients/me/reports/${reportId}/download`,
};

export const patientRemindersApi = {
    list: (activeOnly?: boolean) =>
        api.get<MedicineReminderListResponse>('/patients/me/reminders', {
            params: activeOnly !== undefined ? { active_only: activeOnly } : undefined,
        }),
    create: (data: MedicineReminderCreatePayload) =>
        api.post<MedicineReminderItem>('/patients/me/reminders', data),
    update: (reminderId: string, data: MedicineReminderUpdatePayload) =>
        api.put<MedicineReminderItem>(`/patients/me/reminders/${reminderId}`, data),
    toggleActive: (reminderId: string, isActive: boolean) =>
        api.put<MedicineReminderItem>(`/patients/me/reminders/${reminderId}`, { is_active: isActive }),
    delete: (reminderId: string) =>
        api.delete<{ detail: string; reminder_id: string }>(`/patients/me/reminders/${reminderId}`),
};

// =============================================================================
// Milestone U-17: Admin Operations & Telemetry API
// =============================================================================

export interface OperationalDashboardData {
    users_summary: {
        total_users: number;
        active_users: number;
        doctors_count: number;
        patients_count: number;
        nurses_count: number;
        receptionists_count: number;
        admins_count: number;
    };
    appointments_summary: {
        total_appointments: number;
        today_total: number;
        today_scheduled: number;
        today_in_progress: number;
        today_completed: number;
        today_cancelled: number;
    };
    clinical_summary: {
        prescriptions_finalized: number;
        medical_records_finalized: number;
        intake_sessions_total: number;
        patient_reports_archived: number;
    };
    active_doctors_count: number;
    system_telemetry: {
        database_status: string;
        gemini_live_mesh: string;
        fhir_r4_compliance: string;
        audit_logging_pipeline: string;
        server_time_utc: string;
    };
    future_capabilities: Record<string, { is_available: boolean; status: string; roadmap_milestone: string }>;
}

export interface QueueItem {
    appointment_id: string;
    patient_id: string;
    patient_name: string;
    patient_phone?: string | null;
    patient_abha?: string | null;
    doctor_id: string;
    doctor_name: string;
    doctor_specialty: string;
    scheduled_at: string;
    duration_minutes: number;
    status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | string;
    reason?: string | null;
    meeting_link?: string | null;
    intake_chief_complaint?: string | null;
    intake_severity?: number | null;
    wait_time_minutes: number;
}

export interface QueueListResponse {
    queue: QueueItem[];
    total_in_queue: number;
    active_consultations_count: number;
    completed_today_count: number;
    date: string;
}

export interface DoctorSlotDetail {
    slot_time: string;
    is_available: boolean;
    booked_appointment_id?: string | null;
    patient_name?: string | null;
}

export interface DoctorCapacityItem {
    doctor_id: string;
    doctor_name: string;
    specialty: string;
    hospital_affiliation?: string | null;
    email?: string | null;
    phone?: string | null;
    total_slots: number;
    booked_slots: number;
    available_slots: number;
    utilization_rate_pct: number;
    slots: DoctorSlotDetail[];
}

export interface DoctorAvailabilityMatrixResponse {
    date: string;
    total_doctors: number;
    overall_clinic_utilization_pct: number;
    doctors: DoctorCapacityItem[];
}

export interface OperationalAnalyticsResponse {
    appointments_by_specialty: { specialty: string; count: number }[];
    appointments_by_status: Record<string, number>;
    prescriptions_issued_count: number;
    medical_records_finalized_count: number;
    intake_severity_distribution: Record<string, number>;
    future_metrics: Record<string, { is_available: boolean; status: string; note: string }>;
}

export const adminOperationsApi = {
    getDashboard: () =>
        api.get<OperationalDashboardData>('/admin/operations/dashboard'),
    getQueue: (params?: { date_str?: string; status_filter?: string; doctor_id?: string; search?: string }) =>
        api.get<QueueListResponse>('/admin/operations/queue', params),
    updateQueueStatus: (appointmentId: string, status: string) =>
        api.patch<QueueItem>(`/admin/operations/queue/${appointmentId}/status`, { status }),
    getDoctorAvailability: (dateStr?: string, specialty?: string) =>
        api.get<DoctorAvailabilityMatrixResponse>('/admin/operations/doctors-availability', {
            params: {
                ...(dateStr ? { date_str: dateStr } : {}),
                ...(specialty && specialty !== 'all' ? { specialty } : {}),
            },
        }),
    getAnalytics: () =>
        api.get<OperationalAnalyticsResponse>('/admin/operations/analytics'),
};

