/**
 * Hospital Admin Operations: User Management, Controlled Provisioning,
 * Capacity & Queue Management, Consent Registers, and Immutable Audit Trails.
 */

import { api } from './client';

export interface AdminDoctorProfile {
    doctor_id: string;
    specialty: string;
    license_number: string;
    hospital_affiliation?: string;
    phone?: string;
    department?: string;
    designation?: string;
    qualifications?: string;
    experience_years?: number;
    room_number?: string;
    shift?: string;
    is_head_physician?: boolean;
}

export interface AdminUser {
    user_id: string;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    created_at: string;
    phone?: string;
    is_verified?: boolean;
    department?: string;
    designation?: string;
    qualifications?: string;
    experience_years?: number;
    room_number?: string;
    shift?: string;
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
    role: 'doctor' | 'head_physician' | 'head_nurse' | 'nurse' | 'receptionist' | 'admin' | 'patient';
    phone?: string;
    emergency_contact_phone?: string;
    // Step 2: Licensure & Qualifications
    license_number?: string;
    qualifications?: string;
    experience_years?: number;
    specialty?: string;
    // Step 3: Departmental Assignment & Clinical Setup
    department?: string;
    designation?: string;
    room_number?: string;
    shift?: string;
    hospital_affiliation?: string;
    // Step 4: Governance & Review
    abdm_hpr_id?: string;
    clinical_privileges?: string[];
    background_verified?: boolean;
}

export const adminUsersApi = {
    list: (params?: { role?: string; is_active?: boolean; search?: string; department?: string; limit?: number; offset?: number }) =>
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

export interface ConsentItem {
    consent_id: string;
    patient_id: string;
    provider_id: string;
    provider_name?: string | null;
    provider_specialty?: string | null;
    provider_hospital?: string | null;
    record_scope: 'full_access' | 'records_only' | 'appointments_only' | 'notes_only' | string;
    is_active: boolean;
    granted_at: string;
    revoked_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface ConsentCreatePayload {
    provider_id: string;
    patient_id?: string;
    record_scope?: 'full_access' | 'records_only' | 'appointments_only' | 'notes_only' | string;
}

export const consentApi = {
    getMyConsents: (activeOnly: boolean = false) =>
        api.get<ConsentItem[]>('/consents/me', {
            params: activeOnly ? { active_only: true } : undefined,
        }),
    getPatientConsents: (patientId: string, activeOnly: boolean = true) =>
        api.get<ConsentItem[]>(`/consents/patients/${patientId}`, {
            params: { active_only: activeOnly },
        }),
    grantConsent: (data: ConsentCreatePayload) =>
        api.post<ConsentItem>('/consents', data),
    revokeConsent: (consentId: string) =>
        api.delete<ConsentItem>(`/consents/${consentId}`),
};

export interface AuditLogItem {
    log_id: string;
    user_id?: string | null;
    user_email?: string | null;
    user_name?: string | null;
    user_role?: string | null;
    action: string;
    resource_type: string;
    resource_id?: string | null;
    timestamp: string;
    outcome: 'SUCCESS' | 'FAILURE' | 'DENIED' | 'ERROR' | string;
    details?: Record<string, any> | null;
    ip_address?: string | null;
    user_agent?: string | null;
}

export interface AuditLogListResponse {
    logs: AuditLogItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface AuditLogQueryParams {
    user_id?: string;
    action?: string;
    resource_type?: string;
    resource_id?: string;
    outcome?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
    page?: number;
    page_size?: number;
}

export const adminAuditApi = {
    listLogs: (params?: AuditLogQueryParams) =>
        api.get<AuditLogListResponse>('/admin/audit', params as Record<string, any>),
    getLog: (logId: string) =>
        api.get<AuditLogItem>(`/admin/audit/${logId}`),
};
