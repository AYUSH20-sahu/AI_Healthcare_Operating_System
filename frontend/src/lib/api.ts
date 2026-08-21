/**
 * API client for AI-HOS frontend
 * Communicates with the backend API at /api/v1
 */

const API_BASE = '/api/v1';

interface RequestOptions extends RequestInit {
    params?: Record<string, string | number | boolean | undefined>;
}

async function request<T>(
    endpoint: string,
    options: RequestOptions = {}
): Promise<T> {
    const { params, headers, ...fetchOptions } = options;

    // Build URL with query parameters
    const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, String(value));
            }
        });
    }

    // Get auth token from localStorage
    const token = localStorage.getItem('access_token');

    const defaultHeaders: HeadersInit = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
    };

    const response = await fetch(url.toString(), {
        ...fetchOptions,
        headers: defaultHeaders,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error?.message || `HTTP ${response.status}`);
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

    post: <T>(endpoint: string, data: unknown) =>
        request<T>(endpoint, { method: 'POST', body: JSON.stringify(data) }),

    put: <T>(endpoint: string, data: unknown) =>
        request<T>(endpoint, { method: 'PUT', body: JSON.stringify(data) }),

    delete: <T>(endpoint: string) =>
        request<T>(endpoint, { method: 'DELETE' }),
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
};

// Prescriptions API
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

    create: (data: {
        patient_id: string;
        doctor_id: string;
        medical_record_id?: string;
        medications: Medication[];
        notes?: string;
    }) =>
        api.post<Prescription>('/prescriptions/', data),

    update: (prescriptionId: string, data: {
        medications?: Medication[];
        notes?: string;
        status?: string;
    }) =>
        api.put<Prescription>(`/prescriptions/${prescriptionId}/`, data),

    checkInteractions: (patientId: string, medications: Medication[]) =>
        api.post<{ warnings: InteractionWarning[]; has_warnings: boolean }>(
            '/prescriptions/check-interactions/',
            { patient_id: patientId, medications }
        ),
};

export interface InteractionWarning {
    severity: 'mild' | 'moderate' | 'severe';
    type: 'interaction' | 'allergy';
    medication: string;
    description: string;
    recommendation?: string;
}