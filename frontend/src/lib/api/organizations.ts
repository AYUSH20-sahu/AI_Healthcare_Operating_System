/**
 * Multi-tenant Organization API endpoints & schemas.
 */

import { api } from './client';

export interface OrganizationAdminSummary {
    user_id: string;
    full_name: string;
    email: string;
    phone?: string;
}

export interface OrgStats {
    total_users: number;
    total_doctors: number;
    total_patients: number;
}

export interface Organization {
    organization_id: string;
    name: string;
    code: string;
    description?: string;
    address?: string;
    contact_email?: string;
    contact_phone?: string;
    is_active: boolean;
    facility_type?: string;
    departments?: string[];
    total_beds?: number;
    icu_beds?: number;
    has_emergency?: boolean;
    has_ambulance?: boolean;
    license_number?: string;
    abdm_facility_id?: string;
    insurance_network_code?: string;
    emergency_hotline?: string;
    operating_hours?: string;
    clinical_review_policy?: string;
    created_at: string;
    updated_at: string;
    admin?: OrganizationAdminSummary;
    stats?: OrgStats;
}

export interface OrganizationCreateRequest {
    name: string;
    code: string;
    description?: string;
    address?: string;
    contact_email?: string;
    contact_phone?: string;
    facility_type?: string;
    departments?: string[];
    total_beds?: number;
    icu_beds?: number;
    has_emergency?: boolean;
    has_ambulance?: boolean;
    license_number?: string;
    abdm_facility_id?: string;
    insurance_network_code?: string;
    emergency_hotline?: string;
    operating_hours?: string;
    clinical_review_policy?: string;
    admin_name: string;
    admin_email: string;
    admin_password: string;
    admin_phone?: string;
}

export interface OrganizationUpdateRequest {
    name?: string;
    code?: string;
    description?: string;
    address?: string;
    contact_email?: string;
    contact_phone?: string;
    is_active?: boolean;
}

export const adminOrganizationsApi = {
    list: () =>
        api.get<Organization[]>('/admin/organizations/'),

    getMyOrg: () =>
        api.get<Organization>('/admin/organizations/my-org'),

    get: (orgId: string) =>
        api.get<Organization>(`/admin/organizations/${orgId}`),

    create: (data: OrganizationCreateRequest) =>
        api.post<Organization>('/admin/organizations/', data),

    update: (orgId: string, data: OrganizationUpdateRequest) =>
        api.put<Organization>(`/admin/organizations/${orgId}`, data),

    delete: (orgId: string) =>
        api.delete<{ message: string; organization_id: string }>(`/admin/organizations/${orgId}`),
};
