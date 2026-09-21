/**
 * Ayushman Bharat Digital Mission (ABDM) Sandbox & HL7 FHIR R4 Interoperability APIs.
 */

import { api } from './client';

// ─── FHIR R4 Resource Types ───────────────────────────────────────────────────

export interface FhirCoding { system?: string; code?: string; display?: string; }
export interface FhirCodeableConcept { coding?: FhirCoding[]; text?: string; }
export interface FhirIdentifier { system?: string; value?: string; }
export interface FhirHumanName { use?: string; text?: string; family?: string; given?: string[]; }
export interface FhirContactPoint { system?: string; value?: string; use?: string; }
export interface FhirAddress { text?: string; line?: string[]; city?: string; state?: string; postalCode?: string; country?: string; }
export interface FhirReference { reference?: string; display?: string; }
export interface FhirAnnotation { text?: string; }
export interface FhirMeta { lastUpdated?: string; versionId?: string; }

export interface FhirPatient {
    resourceType: 'Patient';
    id: string;
    identifier?: FhirIdentifier[];
    active?: boolean;
    name?: FhirHumanName[];
    telecom?: FhirContactPoint[];
    gender?: string;
    birthDate?: string;
    address?: FhirAddress[];
    generalPractitioner?: FhirReference[];
    meta?: FhirMeta;
}

export interface FhirAppointment {
    resourceType: 'Appointment';
    id: string;
    status: string;
    serviceType?: FhirCodeableConcept[];
    appointmentType?: FhirCodeableConcept;
    start?: string;
    end?: string;
    minutesDuration?: number;
    participant?: Array<{ actor?: FhirReference; status?: string }>;
    comment?: string;
    meta?: FhirMeta;
}

export interface FhirDiagnosticReport {
    resourceType: 'DiagnosticReport';
    id: string;
    status: string;
    code?: FhirCodeableConcept;
    subject?: FhirReference;
    encounter?: FhirReference;
    effectiveDateTime?: string;
    issued?: string;
    performer?: FhirReference[];
    conclusion?: string;
    section?: Array<{ title?: string; text?: { div?: string } }>;
    meta?: FhirMeta;
}

export interface FhirMedicationRequest {
    resourceType: 'MedicationRequest';
    id: string;
    status: string;
    intent: string;
    medicationCodeableConcept?: FhirCodeableConcept;
    subject?: FhirReference;
    requester?: FhirReference;
    authoredOn?: string;
    dosageInstruction?: Array<{ text?: string; timing?: unknown; route?: FhirCodeableConcept }>;
    note?: FhirAnnotation[];
    meta?: FhirMeta;
}

export interface FhirResourceHeader { resourceType: string; id: string; [key: string]: unknown; }

export type FhirResource = FhirPatient | FhirAppointment | FhirDiagnosticReport | FhirMedicationRequest | FhirResourceHeader;

export interface FhirBundle {
    resourceType: 'Bundle';
    id?: string;
    type: string;
    timestamp?: string;
    total?: number;
    meta?: FhirMeta;
    entry?: Array<{ fullUrl?: string; resource?: FhirResource }>;
}

export const fhirApi = {
    getPatient: (patientId: string) =>
        api.get<FhirPatient>(`/fhir/Patient/${patientId}`),
    getPatientFhir: (patientId: string) =>
        api.get<FhirResourceHeader>(`/fhir/Patient/${patientId}`),
    getAppointmentFhir: (appointmentId: string) =>
        api.get<FhirResourceHeader>(`/fhir/Appointment/${appointmentId}`),
    getRecordFhir: (recordId: string) =>
        api.get<FhirResourceHeader>(`/fhir/DiagnosticReport/${recordId}`),
    getPrescriptionFhir: (prescriptionId: string) =>
        api.get<FhirResourceHeader>(`/fhir/MedicationRequest/${prescriptionId}`),
    getEverything: (patientId: string) =>
        api.get<FhirBundle>(`/fhir/Patient/${patientId}/$everything`),
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
