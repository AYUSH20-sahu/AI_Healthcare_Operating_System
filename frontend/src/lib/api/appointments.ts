/**
 * Clinical and Telehealth Appointment schedules and booking management.
 */

import { api } from './client';
import type { Patient } from './patients';
import type { Doctor } from './doctors';

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
