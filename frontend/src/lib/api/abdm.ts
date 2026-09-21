/**
 * Ayushman Bharat Digital Mission (ABDM) Sandbox & HL7 FHIR R4 Interoperability APIs.
 */

import { api } from './client';

export interface FhirResourceHeader {
    resourceType: string;
    id: string;
    [key: string]: any;
}

export interface FhirBundle {
    resourceType: 'Bundle';
    id: string;
    type: 'searchset' | 'collection' | string;
    timestamp: string;
    total: number;
    entry?: Array<{
        fullUrl: string;
        resource: FhirResourceHeader;
    }>;
}

export const fhirApi = {
    getPatientFhir: (patientId: string) =>
        api.get<FhirResourceHeader>(`/fhir/Patient/${patientId}`),
    getAppointmentFhir: (appointmentId: string) =>
        api.get<FhirResourceHeader>(`/fhir/Appointment/${appointmentId}`),
    getRecordFhir: (recordId: string) =>
        api.get<FhirResourceHeader>(`/fhir/DiagnosticReport/${recordId}`),
    getPrescriptionFhir: (prescriptionId: string) =>
        api.get<FhirResourceHeader>(`/fhir/MedicationRequest/${prescriptionId}`),
    getPatientBundle: (patientId?: string) =>
        api.get<FhirBundle>(patientId ? `/fhir/Patient/${patientId}/$everything` : '/fhir/Bundle'),
};

export interface AbdmStatusResponse {
    gateway_status: 'ONLINE' | 'OFFLINE' | string;
    environment: 'sandbox' | 'production' | string;
    base_url: string;
    hfr_facility_id: string;
    hfr_facility_name: string;
    supported_auth_modes: string[];
    client_configured: boolean;
    abdm_version: string;
}

export interface AbhaInitResponse {
    transaction_id: string;
    abha_address: string;
    auth_mode: string;
    message: string;
    sandbox_test_otp?: string | null;
    expires_in_seconds: number;
}

export interface AbhaVerifyResponse {
    status: 'LINKED' | 'UNLINKED' | string;
    patient_id: string;
    abha_address: string;
    verified_at: string;
    message: string;
}

export interface HfrFacilityInfo {
    facility_id: string;
    facility_name: string;
    facility_type: string;
    ownership: string;
    state: string;
    district: string;
    abdm_registered: boolean;
    hiu_hip_status: string;
}

export const abdmApi = {
    getStatus: () =>
        api.get<AbdmStatusResponse>('/abdm/status'),
    initAbhaLinking: (abhaAddress: string, authMode: string = 'MOBILE_OTP') =>
        api.post<AbhaInitResponse>('/abdm/abha/init', { abha_address: abhaAddress, auth_mode: authMode }),
    verifyAbhaOtp: (transactionId: string, otp: string) =>
        api.post<AbhaVerifyResponse>('/abdm/abha/verify', { transaction_id: transactionId, otp }),
    unlinkAbha: () =>
        api.delete<{ status: string; patient_id: string; message: string }>('/abdm/abha/unlink'),
    getHfrInfo: () =>
        api.get<HfrFacilityInfo>('/abdm/hfr'),
    getConsentStatus: (requestId: string) =>
        api.get<any>(`/abdm/consent/${requestId}`),
};
