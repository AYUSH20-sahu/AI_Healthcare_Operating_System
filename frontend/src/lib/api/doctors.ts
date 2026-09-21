/**
 * Doctor directory, availability scheduling, Head Physician departmental oversight,
 * and junior resident staff provisioning.
 */

import { api } from './client';
import type { Appointment } from './appointments';

export interface Doctor {
    doctor_id: string;
    user_id: string | null;
    specialty: string;
    license_number: string;
    hospital_affiliation: string | null;
    email: string;
    full_name: string;
    phone: string | null;
    department?: string;
    designation?: string;
    qualifications?: string;
    experience_years?: number;
    room_number?: string;
    shift?: string;
    is_head_physician?: boolean;
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

export interface JuniorPhysicianProvisionRequest {
    email: string;
    password: string;
    full_name: string;
    license_number: string;
    qualifications: string;
    designation: string;
    specialty?: string;
    experience_years?: number;
    room_number?: string;
    shift?: string;
    phone?: string;
}

export interface DepartmentTeamResponse {
    department: string;
    head_physician?: {
        name: string;
        email: string;
        designation?: string;
    };
    head_nurse?: {
        name: string;
        email: string;
        designation?: string;
    };
    total_members: number;
    team: any[];
}

export const headPhysicianApi = {
    getTeam: () => api.get<DepartmentTeamResponse>('/doctors/department-team'),
    provisionJunior: (data: JuniorPhysicianProvisionRequest) =>
        api.post<{ message: string; doctor: any }>('/doctors/junior-staff', data),
};
