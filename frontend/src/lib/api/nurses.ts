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

export interface InpatientBedData {
    bedId: string;
    bed_id: string;
    bedNumber: string;
    bed_number: string;
    ward: string;
    patientName: string;
    patient_name: string;
    patientId: string;
    patient_id: string;
    uhid: string;
    age: number;
    gender: string;
    admittedFor: string;
    admitted_for: string;
    attendingPhysician: string;
    attending_physician: string;
    admitDate: string;
    day: number;
    diet: string;
    allergies: string[];
    codeStatus: 'Full Code' | 'DNR' | 'DNI' | string;
    isolationPrecautions?: string;
    nextMedication: string;
    next_medication?: string;
    medicationDue: string;
    medication_due?: string;
    status: 'Stable' | 'Attention' | 'Critical';
    vitals: {
        bp: string;
        systolic: number;
        diastolic: number;
        pulse: number;
        spo2: number;
        temp: number;
        respiratoryRate: number;
        painScore: number;
        lastChecked: string;
        isCritical?: boolean;
    };
    latestVitals?: any;
}

export interface LogVitalsPayload {
    systolic: number;
    diastolic: number;
    bp?: string;
    pulse: number;
    spo2: number;
    temp: number;
    respiratory_rate?: number;
    pain_score?: number;
    notes?: string;
}

export interface ShiftTaskData {
    id: string;
    taskId?: string;
    bedId?: string;
    patientId: string;
    patientName: string;
    bedNumber: string;
    ward: string;
    taskType: 'medication' | 'ward_round';
    medication: string;
    dose: string;
    route: string;
    prescribedBy: string;
    roundTask?: string;
    task: string;
    category: 'positioning' | 'wound' | 'iv' | 'catheter' | 'nutrition' | 'assessment';
    priority: 'stat' | 'urgent' | 'routine';
    dueTime: string;
    dueBy: string;
    overdue: boolean;
    status: 'pending' | 'administered' | 'delayed' | 'refused' | 'done';
    notes?: string;
    administeredBy?: string;
    administeredAt?: string;
}

export interface ShiftTasksResponse {
    all: ShiftTaskData[];
    medTasks: ShiftTaskData[];
    roundTasks: ShiftTaskData[];
    totalTasks: number;
    pendingCount: number;
    overdueCount: number;
}

export interface AssignedPatientData {
    patientId: string;
    patientName: string;
    age: number;
    gender: string;
    bedNumber: string;
    ward: string;
    admittedFor: string;
    attendingPhysician: string;
    admitDate: string;
    day: number;
    status: 'stable' | 'attention' | 'critical';
    lastVitals?: { bp: string; pulse: number; spo2: number; temp: number };
    pendingMeds: number;
    pendingRounds: number;
    diet: string;
    allergies: string[];
    codeStatus: 'Full Code' | 'DNR' | 'DNI';
    isolationPrecautions?: string;
}

export const nurseWorkstationApi = {
    getInpatientBeds: (params?: { ward?: string; clinical_status?: string }) =>
        api.get<InpatientBedData[]>('/nurses/inpatient-beds', params),
    logVitals: (bedId: string, data: LogVitalsPayload) =>
        api.post<{ message: string; bed: InpatientBedData; vitalsLog: any }>(`/nurses/inpatient-beds/${bedId}/vitals`, data),
    getVitalsHistory: (bedId: string, limit?: number) =>
        api.get<any[]>(`/nurses/inpatient-beds/${bedId}/vitals-history`, { limit }),
    markMedicationAdministered: (bedId: string) =>
        api.post<{ message: string; bed: InpatientBedData }>(`/nurses/inpatient-beds/${bedId}/medication-administered`),
    getShiftTasks: (params?: { task_type?: string; status?: string }) =>
        api.get<ShiftTasksResponse>('/nurses/shift-tasks', params),
    updateTaskStatus: (taskId: string, data: { status: string; notes?: string }) =>
        api.patch<{ message: string; task: ShiftTaskData }>(`/nurses/shift-tasks/${taskId}/status`, data),
    getAssignedPatients: () =>
        api.get<AssignedPatientData[]>('/nurses/assigned-patients'),
};

