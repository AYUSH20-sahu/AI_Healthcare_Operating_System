'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/lib/auth';
import { adminOrganizationsApi, Organization } from '@/lib/api';

export interface HospitalFacility {
    id: string;
    orgId: string;
    name: string;
    branch: string;
    code: string;
    departments?: string[];
    department?: string;
    totalBeds?: number;
    icuBeds?: number;
}

const fallbackFacilities: HospitalFacility[] = [
    { id: 'apex-main', orgId: 'apex-main', name: 'Apex Medical Center', branch: 'Main Tertiary Campus', code: 'AMC-01' },
    { id: 'stjude-opd', orgId: 'stjude-opd', name: 'St. Jude Specialty', branch: 'Cardio & Neuro OPD', code: 'SJS-02' },
    { id: 'city-trauma', orgId: 'city-trauma', name: 'City Trauma Center', branch: 'Emergency & Critical Care', code: 'CTC-03' },
];

interface HospitalSelectorProps {
    compact?: boolean;
}

export function HospitalSelector({ compact = false }: HospitalSelectorProps) {
    const { user, isSuperAdmin, token } = useAuth();
    const [facilities, setFacilities] = useState<HospitalFacility[]>(fallbackFacilities);
    const [selected, setSelected] = useState<HospitalFacility>(fallbackFacilities[0]);
    const [isOpen, setIsOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let isMounted = true;

        async function fetchRealOrganizations() {
            if (!token) return;
            setIsLoading(true);
            try {
                let orgList: Organization[] = [];

                // Try fetching assigned / accessible organizations
                try {
                    orgList = await adminOrganizationsApi.list();
                } catch {
                    try {
                        const myOrg = await adminOrganizationsApi.getMyOrg();
                        if (myOrg) orgList = [myOrg];
                    } catch {
                        orgList = [];
                    }
                }

                if (!isMounted) return;

                if (orgList && orgList.length > 0) {
                    const dynamicList: HospitalFacility[] = [];

                    for (const org of orgList) {
                        // Main organization campus
                        dynamicList.push({
                            id: org.organization_id,
                            orgId: org.organization_id,
                            name: org.name,
                            branch: org.facility_type || 'Main Facility Campus',
                            code: org.code,
                            departments: org.departments,
                            totalBeds: org.total_beds,
                            icuBeds: org.icu_beds,
                        });

                        // If single org admin with clinical departments, allow scoping to specific divisions
                        if (org.departments && org.departments.length > 0 && orgList.length === 1) {
                            for (const dept of org.departments) {
                                const deptInitials = dept
                                    .split(/[\s/]+/)
                                    .map((w) => w[0])
                                    .join('')
                                    .toUpperCase()
                                    .slice(0, 3);
                                dynamicList.push({
                                    id: `${org.organization_id}::${dept}`,
                                    orgId: org.organization_id,
                                    name: org.name,
                                    branch: dept,
                                    code: `${org.code.slice(0, 3)}-${deptInitials}`,
                                    department: dept,
                                });
                            }
                        }
                    }

                    setFacilities(dynamicList);

                    const savedId = typeof window !== 'undefined' ? localStorage.getItem('active_hospital_tenant') : null;
                    const match = dynamicList.find((f) => f.id === savedId) || dynamicList[0];
                    setSelected(match);

                    if (typeof window !== 'undefined' && match) {
                        localStorage.setItem('active_hospital_tenant', match.id);
                        localStorage.setItem('active_hospital_org_id', match.orgId);
                        if (match.department) {
                            localStorage.setItem('active_hospital_dept', match.department);
                        } else {
                            localStorage.removeItem('active_hospital_dept');
                        }
                    }
                }
            } catch (err) {
                console.warn('Could not load organizations for selector:', err);
            } finally {
                if (isMounted) setIsLoading(false);
            }
        }

        fetchRealOrganizations();

        const handleClickOutside = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            isMounted = false;
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [user?.user_id, token, isSuperAdmin]);

    const handleSelect = (facility: HospitalFacility) => {
        setSelected(facility);
        if (typeof window !== 'undefined') {
            localStorage.setItem('active_hospital_tenant', facility.id);
            localStorage.setItem('active_hospital_org_id', facility.orgId);
            if (facility.department) {
                localStorage.setItem('active_hospital_dept', facility.department);
            } else {
                localStorage.removeItem('active_hospital_dept');
            }
            window.dispatchEvent(new CustomEvent('aihos-tenant-changed', { detail: facility }));
        }
        setIsOpen(false);
    };

    if (compact) {
        return (
            <div className="relative flex justify-center py-2" ref={dropdownRef}>
                <button
                    type="button"
                    onClick={() => setIsOpen(!isOpen)}
                    title={`Facility: ${selected.name} (${selected.branch})`}
                    className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400 font-bold text-xs flex items-center justify-center hover:bg-blue-500/20 transition-colors"
                >
                    {selected.code.slice(0, 2)}
                </button>

                {isOpen && (
                    <div className="absolute left-12 top-0 z-50 w-72 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-1.5 space-y-1">
                        <div className="px-2.5 py-1 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center justify-between">
                            <span>{isSuperAdmin ? 'Enterprise Organizations' : 'Assigned Facility & Units'}</span>
                            {isLoading && <span className="animate-spin text-xs">⏳</span>}
                        </div>
                        <div className="max-h-64 overflow-y-auto space-y-1">
                            {facilities.map((facility) => {
                                const isSelected = facility.id === selected.id;
                                return (
                                    <button
                                        key={facility.id}
                                        type="button"
                                        onClick={() => handleSelect(facility)}
                                        className={`w-full flex items-start gap-2.5 px-2.5 py-2 text-left rounded-lg transition-colors ${
                                            isSelected
                                                ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                                                : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                                        }`}
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p className="text-xs font-semibold leading-tight truncate">{facility.name}</p>
                                            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{facility.branch}</p>
                                        </div>
                                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                                            {facility.code}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-2 rounded-xl bg-slate-100/70 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-all text-left"
            >
                <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-7 h-7 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 flex items-center justify-center font-bold text-[10px] shrink-0">
                        {selected.code.slice(0, 2)}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate leading-tight">
                            {selected.name}
                        </p>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">
                            {selected.branch}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-1">
                    {isLoading && <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping mr-1" />}
                    <svg className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </button>

            {isOpen && (
                <div className="absolute left-0 right-0 top-full mt-1.5 z-50 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-1.5 space-y-1">
                    <div className="px-2.5 py-1 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center justify-between">
                        <span>{isSuperAdmin ? 'Enterprise Organizations' : 'Assigned Facility & Units'}</span>
                        {selected.totalBeds !== undefined && selected.totalBeds > 0 && (
                            <span className="text-[9px] text-blue-600 dark:text-blue-400 font-normal">
                                {selected.totalBeds} Beds ({selected.icuBeds || 0} ICU)
                            </span>
                        )}
                    </div>
                    <div className="max-h-64 overflow-y-auto space-y-1">
                        {facilities.map((facility) => {
                            const isSelected = facility.id === selected.id;
                            return (
                                <button
                                    key={facility.id}
                                    type="button"
                                    onClick={() => handleSelect(facility)}
                                    className={`w-full flex items-center justify-between px-2.5 py-2 text-left rounded-lg transition-colors ${
                                        isSelected
                                            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                                    }`}
                                >
                                    <div className="min-w-0 pr-2">
                                        <p className="text-xs font-semibold leading-tight truncate">{facility.name}</p>
                                        <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{facility.branch}</p>
                                    </div>
                                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 shrink-0">
                                        {facility.code}
                                    </span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
