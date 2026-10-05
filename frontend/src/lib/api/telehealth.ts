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

export interface IceServerItem {
    urls: string | string[];
    username?: string;
    credential?: string;
}

export interface IceServersResponse {
    ice_servers: IceServerItem[];
    ttl: number;
    expires_at: number;
    realm?: string;
    username?: string;
}

export interface RecordingMetadata {
    appointment_id: string;
    original_filename: string;
    content_type: string;
    plaintext_bytes: number;
    encrypted_bytes: number;
    plaintext_sha256: string;
    encryption_algorithm: string;
    duration_seconds: number;
    recorded_by_user_id?: string | null;
    created_at: string;
    storage_path?: string;
}

export interface RecordingStatusResponse {
    has_recording: boolean;
    appointment_id: string;
    metadata: RecordingMetadata | null;
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
    getIceServers: () =>
        api.get<IceServersResponse>('/telehealth/ice-servers'),
    getRoomToken: (appointmentId: string) =>
        api.get<{
            room_id: string;
            appointment_id: string;
            peer_role: 'doctor' | 'patient';
            ws_url: string;
            ice_servers?: IceServerItem[];
            instructions?: string;
        }>(`/telehealth/room/${appointmentId}/token`),
    uploadRecording: (appointmentId: string, formData: FormData) =>
        api.post<{ success: boolean; message: string; metadata: RecordingMetadata }>(
            `/telehealth/room/${appointmentId}/recording`,
            formData
        ),
    getRecordingStatus: (appointmentId: string) =>
        api.get<RecordingStatusResponse>(`/telehealth/room/${appointmentId}/recording/status`),
};
