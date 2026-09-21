/**
 * Clinical prescription management, interaction checking, and medication safety.
 */

import { api } from './client';
import type { Patient } from './patients';
import type { Doctor } from './doctors';

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

export interface InteractionWarning {
    severity: 'mild' | 'moderate' | 'severe';
    type: 'interaction' | 'allergy';
    medication: string;
    description: string;
    recommendation?: string;
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
    medical_record?: any;
}

export interface PrescriptionListResponse {
    prescriptions: Prescription[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

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
    ai_metadata: any;
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
