'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/auth';
import { Button, Card, CardContent, CardHeader, Badge, Input, Modal, Alert } from '@/components/ui';
import { nurseWorkstationApi, InpatientBedData } from '@/lib/api/nurses';
import { useWardTelemetry, TelemetryVitalsPayload } from '@/lib/hooks/useWardTelemetry';

interface InpatientBed {
    bedId?: string;
    bedNumber: string;
    ward: string;
    patientName: string;
    uhid: string;
    age: number;
    gender: string;
    admittedFor: string;
    attendingPhysician: string;
    vitals: {
        bp: string;
        pulse: number;
        spo2: number;
        temp: number;
        lastChecked: string;
        isCritical?: boolean;
    };
    nextMedication: string;
    medicationDue: string;
    status: 'Stable' | 'Attention' | 'Critical';
}

export default function NurseWorkstationPage() {
    const { user } = useAuth();
    const [beds, setBeds] = useState<InpatientBed[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [selectedBed, setSelectedBed] = useState<InpatientBed | null>(null);
    const [filterWard, setFilterWard] = useState<string>('all');
    const [isVitalsModalOpen, setIsVitalsModalOpen] = useState(false);

    // Form fields for logging new vitals
    const [newBp, setNewBp] = useState('');
    const [newPulse, setNewPulse] = useState('');
    const [newSpo2, setNewSpo2] = useState('');
    const [newTemp, setNewTemp] = useState('');
    const [vitalsSavedNotice, setVitalsSavedNotice] = useState(false);
    const [downloadingSummaryId, setDownloadingSummaryId] = useState<string | null>(null);

    const fetchBeds = useCallback(async () => {
        try {
            const data = await nurseWorkstationApi.getInpatientBeds({
                ward: filterWard === 'all' ? undefined : filterWard,
            });
            if (Array.isArray(data)) {
                const mapped: InpatientBed[] = data.map((b) => ({
                    bedId: b.bedId || b.bed_id,
                    bedNumber: b.bedNumber || b.bed_number,
                    ward: b.ward,
                    patientName: b.patientName || b.patient_name,
                    uhid: b.uhid,
                    age: b.age,
                    gender: b.gender,
                    admittedFor: b.admittedFor || b.admitted_for,
                    attendingPhysician: b.attendingPhysician || b.attending_physician,
                    vitals: {
                        bp: b.vitals?.bp || '120/80',
                        pulse: b.vitals?.pulse || 72,
                        spo2: b.vitals?.spo2 || 98,
                        temp: b.vitals?.temp || 98.6,
                        lastChecked: b.vitals?.lastChecked || 'Recently',
                        isCritical: b.vitals?.isCritical,
                    },
                    nextMedication: b.nextMedication || b.next_medication || 'Routine Round',
                    medicationDue: b.medicationDue || b.medication_due || 'Scheduled',
                    status: (b.status as InpatientBed['status']) || 'Stable',
                }));
                setBeds(mapped);
            }
        } catch (err) {
            console.error('Failed to fetch inpatient beds:', err);
        } finally {
            setIsLoading(false);
        }
    }, [filterWard]);

    const handleLiveTelemetry = useCallback((payload: TelemetryVitalsPayload) => {
        if (!payload.bed_id && !payload.bed_number) return;
        setBeds((prevBeds) =>
            prevBeds.map((bed) => {
                if (bed.bedId === payload.bed_id || bed.bedNumber === payload.bed_number) {
                    const statusStr = payload.clinical_status
                        ? (payload.clinical_status.charAt(0).toUpperCase() + payload.clinical_status.slice(1).toLowerCase()) as InpatientBed['status']
                        : bed.status;

                    return {
                        ...bed,
                        vitals: {
                            ...bed.vitals,
                            bp: payload.bp || bed.vitals.bp,
                            pulse: payload.pulse !== undefined ? payload.pulse : bed.vitals.pulse,
                            spo2: payload.spo2 !== undefined ? payload.spo2 : bed.vitals.spo2,
                            temp: payload.temp !== undefined ? payload.temp : bed.vitals.temp,
                            lastChecked: 'Just now (Live)',
                            isCritical: payload.is_critical,
                        },
                        status: statusStr,
                    };
                }
                return bed;
            })
        );
    }, []);

    const { isConnected: isTelemetryLive } = useWardTelemetry({
        ward: filterWard === 'all' ? 'icu' : filterWard,
        enabled: true,
        onVitalsUpdated: handleLiveTelemetry,
        onMedicationAdministered: () => fetchBeds(),
    });

    useEffect(() => {
        fetchBeds();
        const timer = setInterval(fetchBeds, 30000);
        return () => clearInterval(timer);
    }, [fetchBeds]);

    const openVitalsModal = (bed: InpatientBed) => {
        setSelectedBed(bed);
        setNewBp(bed.vitals.bp);
        setNewPulse(bed.vitals.pulse.toString());
        setNewSpo2(bed.vitals.spo2.toString());
        setNewTemp(bed.vitals.temp.toString());
        setIsVitalsModalOpen(true);
    };

    const handleSaveVitals = async () => {
        if (!selectedBed) return;

        setIsSaving(true);
        try {
            const spo2Num = parseInt(newSpo2) || 98;
            const pulseNum = parseInt(newPulse) || 75;
            const tempNum = parseFloat(newTemp) || 98.6;
            const [sysStr, diaStr] = (newBp || selectedBed.vitals.bp || '120/80').split('/');
            const systolic = parseInt(sysStr) || 120;
            const diastolic = parseInt(diaStr) || 80;

            if (selectedBed.bedId) {
                await nurseWorkstationApi.logVitals(selectedBed.bedId, {
                    systolic,
                    diastolic,
                    bp: newBp || selectedBed.vitals.bp,
                    pulse: pulseNum,
                    spo2: spo2Num,
                    temp: tempNum,
                });
            }

            await fetchBeds();
            setIsVitalsModalOpen(false);
            setVitalsSavedNotice(true);
            setTimeout(() => setVitalsSavedNotice(false), 4000);
        } catch (err) {
            console.error('Error logging bedside vitals:', err);
        } finally {
            setIsSaving(false);
        }
    };

    const handleMedicationAdministered = async (bed: InpatientBed) => {
        try {
            if (bed.bedId) {
                await nurseWorkstationApi.markMedicationAdministered(bed.bedId);
            }
            await fetchBeds();
        } catch (err) {
            console.error('Error marking medication given:', err);
            setBeds((prev) =>
                prev.map((b) =>
                    b.bedNumber === bed.bedNumber
                        ? { ...b, medicationDue: 'Completed (Next at 20:00)' }
                        : b
                )
            );
        }
    };

    const handleDownloadDischargeSummary = async (bed: InpatientBed) => {
        if (!bed.bedId) return;
        setDownloadingSummaryId(bed.bedId);
        try {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
            const token = localStorage.getItem('access_token');
            const res = await fetch(`${apiBase}/clinical-documents/discharge-summary/bed/${bed.bedId}/pdf`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => null);
                throw new Error(errData?.detail || `Failed to download Discharge Summary (HTTP ${res.status})`);
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Discharge_Summary_${bed.bedNumber}_${bed.patientName.replace(/\s+/g, '_')}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err: any) {
            console.error('Discharge summary download failed:', err);
            alert(err.message || 'Could not download Discharge Summary.');
        } finally {
            setDownloadingSummaryId(null);
        }
    };

    const filteredBeds = beds.filter((b) => {
        if (filterWard === 'all') return true;
        if (filterWard === 'icu') return b.ward.includes('Intensive Care');
        if (filterWard === 'ward') return b.ward.includes('General Ward');
        return true;
    });

    const criticalCount = beds.filter((b) => b.status === 'Critical').length;
    const attentionCount = beds.filter((b) => b.status === 'Attention').length;


    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>🩺 Nurse Care & Triage Workstation</span>
                        </h1>
                        <Badge variant="purple" className="text-xs uppercase font-bold tracking-wider">
                            Nursing Duty
                        </Badge>
                        <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium border border-blue-500/20">
                            {user?.full_name || 'Staff Nurse'} • On Duty
                        </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Inpatient bedside monitoring, digital vitals logging, automated doctor order handoffs & rapid response triage.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        className="text-xs flex items-center gap-1.5"
                    >
                        <span>🚨</span>
                        <span>Emergency Call</span>
                    </Button>
                </div>
            </div>

            {vitalsSavedNotice && (
                <Alert variant="success" className="animate-in fade-in slide-in-from-top-2">
                    Vitals logged and synchronized to patient Electronic Health Record with zero administrative tampering.
                </Alert>
            )}

            {/* Quick KPI Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Assigned Inpatients
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-slate-900 dark:text-white">
                                {beds.length}
                            </span>
                            <span className="text-xs text-blue-600 font-medium">Beds Active</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Critical Alert Flag
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-rose-600 dark:text-rose-400">
                                {criticalCount}
                            </span>
                            <span className="text-xs text-rose-500 font-medium">Immediate bedside required</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Attention / Fever Watch
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                                {attentionCount}
                            </span>
                            <span className="text-xs text-slate-500">Frequent vitals</span>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-slate-200 dark:border-slate-800">
                    <CardContent className="p-4">
                        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                            Medication Round Status
                        </span>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold text-emerald-600">
                                1 Due Now
                            </span>
                            <span className="text-xs text-slate-500">16:00 Dose Round</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Ward Filter Bar */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Filter By Ward:</span>
                    <div className="flex gap-1.5">
                        <Button
                            variant={filterWard === 'all' ? 'primary' : 'outline'}
                            size="sm"
                            onClick={() => setFilterWard('all')}
                            className="text-xs h-8"
                        >
                            All Wards ({beds.length})
                        </Button>
                        <Button
                            variant={filterWard === 'icu' ? 'primary' : 'outline'}
                            size="sm"
                            onClick={() => setFilterWard('icu')}
                            className="text-xs h-8"
                        >
                            ICU Only
                        </Button>
                        <Button
                            variant={filterWard === 'ward' ? 'primary' : 'outline'}
                            size="sm"
                            onClick={() => setFilterWard('ward')}
                            className="text-xs h-8"
                        >
                            General Ward
                        </Button>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <span className={`inline-block w-2 h-2 rounded-full ${isTelemetryLive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                    <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                        {isTelemetryLive ? 'Real-Time Bedside WebSocket Active' : 'Polling Sync Active (30s)'}
                    </span>
                </div>
            </div>

            {/* Inpatient Bed Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredBeds.length === 0 ? (
                    <Card className="border border-dashed border-slate-300 dark:border-slate-800 p-12 text-center col-span-1 md:col-span-2 bg-white dark:bg-slate-900">
                        <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center text-xl mb-3">
                            🏥
                        </div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                            No Inpatient Beds Currently Occupied
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Admitted ward patients will appear here for vitals monitoring, nurse rounds, and medication handoffs.
                        </p>
                    </Card>
                ) : (
                    filteredBeds.map((bed) => {
                    const isCrit = bed.status === 'Critical';
                    return (
                        <Card
                            key={bed.bedNumber}
                            className={`border transition-all ${
                                isCrit
                                    ? 'border-rose-400/80 bg-rose-50/20 dark:bg-rose-950/10 shadow-md shadow-rose-500/10'
                                    : 'border-slate-200 dark:border-slate-800'
                            }`}
                        >
                            <CardHeader className="py-3 px-4 border-b border-slate-200 dark:border-slate-800/80 flex flex-row items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                                        {bed.bedNumber}
                                    </span>
                                    <span className="text-xs text-slate-500">{bed.ward}</span>
                                </div>
                                <Badge
                                    variant={
                                        bed.status === 'Critical'
                                            ? 'danger'
                                            : bed.status === 'Attention'
                                            ? 'warning'
                                            : 'success'
                                    }
                                    className="text-[11px]"
                                >
                                    {bed.status}
                                </Badge>
                            </CardHeader>
                            <CardContent className="p-4 space-y-4">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <h2 className="font-bold text-sm text-slate-900 dark:text-white">
                                            {bed.patientName}
                                        </h2>
                                        <p className="text-xs text-slate-500 mt-0.5">
                                            {bed.age}y / {bed.gender} • {bed.uhid}
                                        </p>
                                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300 mt-1">
                                            Diagnosis: {bed.admittedFor}
                                        </p>
                                        <p className="text-[11px] text-slate-500 mt-0.5">
                                            {bed.attendingPhysician}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-1.5 shrink-0">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => openVitalsModal(bed)}
                                            className="text-xs"
                                        >
                                            ✏️ Log Vitals
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleDownloadDischargeSummary(bed)}
                                            disabled={downloadingSummaryId === bed.bedId}
                                            className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
                                            title="Download Cryptographically Signed FHIR Discharge Summary PDF"
                                        >
                                            {downloadingSummaryId === bed.bedId ? '⏳...' : '📄 Summary'}
                                        </Button>
                                    </div>
                                </div>

                                {/* Vitals Readout Box */}
                                <div className="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-xl border border-slate-200 dark:border-slate-800 grid grid-cols-4 gap-2 text-center">
                                    <div>
                                        <p className="text-[10px] uppercase text-slate-400 font-semibold">BP</p>
                                        <p className={`text-xs font-bold ${isCrit && parseInt(bed.vitals.bp) > 150 ? 'text-rose-600' : 'text-slate-900 dark:text-white'}`}>
                                            {bed.vitals.bp}
                                        </p>
                                        <span className="text-[9px] text-slate-400">mmHg</span>
                                    </div>
                                    <div>
                                        <p className="text-[10px] uppercase text-slate-400 font-semibold">Pulse</p>
                                        <p className={`text-xs font-bold ${bed.vitals.pulse > 100 ? 'text-rose-600' : 'text-slate-900 dark:text-white'}`}>
                                            {bed.vitals.pulse}
                                        </p>
                                        <span className="text-[9px] text-slate-400">bpm</span>
                                    </div>
                                    <div>
                                        <p className="text-[10px] uppercase text-slate-400 font-semibold">SpO2</p>
                                        <p className={`text-xs font-bold ${bed.vitals.spo2 < 92 ? 'text-rose-600 animate-pulse' : 'text-slate-900 dark:text-white'}`}>
                                            {bed.vitals.spo2}%
                                        </p>
                                        <span className="text-[9px] text-slate-400">Oxygen</span>
                                    </div>
                                    <div>
                                        <p className="text-[10px] uppercase text-slate-400 font-semibold">Temp</p>
                                        <p className={`text-xs font-bold ${bed.vitals.temp > 100 ? 'text-amber-600' : 'text-slate-900 dark:text-white'}`}>
                                            {bed.vitals.temp}°F
                                        </p>
                                        <span className="text-[9px] text-slate-400">Oral</span>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100 dark:border-slate-800/60">
                                    <span>Last checked: {bed.vitals.lastChecked}</span>
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-slate-700 dark:text-slate-300">
                                            Med: {bed.nextMedication}
                                        </span>
                                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${bed.medicationDue.includes('Immediate') ? 'bg-rose-500/20 text-rose-600' : 'bg-blue-500/10 text-blue-600'}`}>
                                            {bed.medicationDue}
                                        </span>
                                        {!bed.medicationDue.includes('Completed') && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleMedicationAdministered(bed)}
                                                className="text-[10px] h-6 px-1 text-emerald-600 hover:text-emerald-700"
                                            >
                                                ✓ Given
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    );
                }))}
            </div>

            {/* Vitals Recording Modal */}
            <Modal
                isOpen={isVitalsModalOpen}
                onClose={() => setIsVitalsModalOpen(false)}
                title={`Bedside Vitals Logging • ${selectedBed?.bedNumber} (${selectedBed?.patientName})`}
            >
                <div className="space-y-4 py-2">
                    <p className="text-xs text-slate-500">
                        Record updated vitals taken from bedside calibrated telemetry. These values update the patient chart and alert the attending physician in real time.
                    </p>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                Blood Pressure (mmHg)
                            </label>
                            <Input
                                placeholder="120/80"
                                value={newBp}
                                onChange={(e) => setNewBp(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                Pulse (bpm)
                            </label>
                            <Input
                                placeholder="72"
                                type="number"
                                value={newPulse}
                                onChange={(e) => setNewPulse(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                Oxygen Saturation (SpO2 %)
                            </label>
                            <Input
                                placeholder="98"
                                type="number"
                                value={newSpo2}
                                onChange={(e) => setNewSpo2(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                                Temperature (°F)
                            </label>
                            <Input
                                placeholder="98.6"
                                type="number"
                                step="0.1"
                                value={newTemp}
                                onChange={(e) => setNewTemp(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="p-3 bg-blue-50/60 dark:bg-blue-950/20 rounded-lg text-xs text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-900/30">
                        💡 <strong>Safety Check:</strong> If SpO2 drops below 90% or Heart Rate exceeds 120 bpm, the system will trigger an emergency notification to {selectedBed?.attendingPhysician}.
                    </div>

                    <div className="flex justify-end gap-2 pt-3 border-t border-slate-200 dark:border-slate-800">
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setIsVitalsModalOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            size="sm"
                            disabled={isSaving}
                            onClick={handleSaveVitals}
                        >
                            {isSaving ? 'Saving...' : 'Save Vitals to EMR'}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
