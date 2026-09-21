/**
 * Authentication and User Identity API endpoints & schemas.
 */

import { api } from './client';

export interface User {
    user_id: string;
    email: string;
    phone?: string;
    full_name: string;
    role: 'patient' | 'doctor' | 'admin' | 'nurse' | 'receptionist' | 'super_admin' | 'head_physician' | 'head_nurse' | string;
    organization_id?: string;
    is_active: boolean;
    created_at: string;
    department?: string;
    designation?: string;
    qualifications?: string;
    experience_years?: number;
    room_number?: string;
    shift?: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface LoginRequest {
    email?: string;
    phone?: string;
    identifier?: string;
    password: string;
}

export interface SignupRequest {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
}

export interface PatientSignupRequest {
    full_name: string;
    email: string;
    phone: string;
    password: string;
}

export interface PatientLoginRequest {
    identifier: string;
    password: string;
}

export interface OrgRegisterRequest {
    // Step 1: Admin & Basic Facility Information
    admin_name: string;
    email: string;
    phone?: string;
    password: string;
    organization_name: string;
    organization_code?: string;
    organization_address?: string;

    // Step 2: Clinical Facility & Department Configuration
    facility_type?: string;
    departments?: string[];
    total_beds?: number;
    icu_beds?: number;
    has_emergency?: boolean;
    has_ambulance?: boolean;

    // Step 3: Regulatory & Licensing Credentials
    license_number?: string;
    abdm_facility_id?: string;
    insurance_network_code?: string;

    // Step 4: Operational Settings & Safety Gate
    emergency_hotline?: string;
    operating_hours?: string;
    clinical_review_policy?: string;
}

export const authApi = {
    login: (credentials: LoginRequest) =>
        api.post<TokenResponse>('/auth/login', credentials),

    signup: (data: SignupRequest) =>
        api.post<User>('/auth/signup', data),

    patientLogin: (credentials: PatientLoginRequest) =>
        api.post<TokenResponse>('/auth/patient/login', credentials),

    patientRegister: (data: PatientSignupRequest) =>
        api.post<User>('/auth/patient/register', data),

    registerOrg: (data: OrgRegisterRequest) =>
        api.post<User>('/auth/register-org', data),

    refresh: (refreshToken: string) =>
        api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),

    logout: (refreshToken?: string) =>
        api.post<{ message: string }>('/auth/logout', { refresh_token: refreshToken }),

    me: () =>
        api.get<User>('/auth/me'),
};
