/**
 * Nursing department roster, Head Nurse leadership oversight, and staff nurse onboarding.
 */

import { api } from './client';
import type { DepartmentTeamResponse } from './doctors';

export interface JuniorNurseProvisionRequest {
    email: string;
    password: string;
    full_name: string;
    license_number: string;
    qualifications: string;
    designation: string;
    experience_years?: number;
    room_number?: string;
    shift?: string;
    phone?: string;
}

export const headNurseApi = {
    getTeam: () => api.get<DepartmentTeamResponse>('/nurses/department-team'),
    provisionJunior: (data: JuniorNurseProvisionRequest) =>
        api.post<{ message: string; nurse: any }>('/nurses/junior-staff', data),
    listNurses: (department?: string) => api.get<any[]>('/nurses/', { department }),
};
