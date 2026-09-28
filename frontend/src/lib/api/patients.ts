/**
 * Patient demographic records, patient portal dashboard, reports, and medication reminders.
 */

import { api } from './client';
import type { Medication } from './prescriptions';

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
    blood_group?: string | null;
    created_at: string;
    updated_at: string;
}

export type PatientProfile = Patient;

export interface PatientListResponse {
    patients: Patient[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

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
    doctor_specialty?: string | null;
    doctor_hospital?: string | null;
    appointment_id?: string | null;
    status: string;
    chief_complaint?: string | null;
    subjective?: string | null;
    objective?: string | null;
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
