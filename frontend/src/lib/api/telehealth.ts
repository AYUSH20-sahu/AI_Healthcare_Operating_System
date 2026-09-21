/**
 * Telehealth Consultation Room and Doctor Scheduling APIs.
 */

import { api } from './client';

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
