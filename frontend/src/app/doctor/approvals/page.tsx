'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
    approvalApi,
    DraftItem,
    Medication,
} from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Alert } from '@/components/ui/Alert';

function DoctorApprovalGateContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const queryType = searchParams.get('type') || 'medical_record';
    const queryId = searchParams.get('id');

    // Tab State: 'medical_records' or 'prescriptions'
    const [activeTab, setActiveTab] = useState<'medical_records' | 'prescriptions'>(
        queryType === 'prescription' ? 'prescriptions' : 'medical_records'
    );

    // Queue State
    const [draftMedicalRecords, setDraftMedicalRecords] = useState<DraftItem[]>([]);
    const [draftPrescriptions, setDraftPrescriptions] = useState<DraftItem[]>([]);
    const [selectedDraftId, setSelectedDraftId] = useState<string | null>(queryId);
    const [isLoadingQueue, setIsLoadingQueue] = useState<boolean>(true);

    // Selected Item Detail State
    const [currentStatus, setCurrentStatus] = useState<string>('DRAFT');
    const [finalizedTimestamp, setFinalizedTimestamp] = useState<string | null>(null);
    const [reviewerName, setReviewerName] = useState<string>('Dr. Rajesh Sharma');

    // Editable Medical Record State
    const [chiefComplaint, setChiefComplaint] = useState<string>('Chest pain on exertion radiating to left arm');
    const [assessment, setAssessment] = useState<string>('Angina Pectoris / Coronary Artery Disease');
    const [icd10Code, setIcd10Code] = useState<string>('I20.9');
    const [planText, setPlanText] = useState<string>('Start Metoprolol 50mg BID, Atorvastatin 40mg QHS. Schedule stress ECG.');
    const [aiConfidence, setAiConfidence] = useState<number>(94);
    const [clinicalBasis, setClinicalBasis] = useState<string>(
        'Spoken dialogue noted exertional tightness and relief upon rest. Aligns with stable angina protocol.'
    );

    // Editable Prescription State
    const [medications, setMedications] = useState<Medication[]>([
        {
            name: 'Metoprolol Tartrate',
            dosage: '50mg',
            frequency: 'Twice daily',
            duration: '30 days',
            route: 'oral',
            instructions: 'Take with food.',
            quantity: 60,
            refills: 1,
        },
        {
            name: 'Atorvastatin Calcium',
            dosage: '40mg',
            frequency: 'Once daily at bedtime',
            duration: '90 days',
            route: 'oral',
            instructions: 'Avoid grapefruit products.',
            quantity: 90,
            refills: 2,
        },
    ]);
    const [notes, setNotes] = useState<string>('Low-sodium diet recommended. Follow up in clinic in 2 weeks.');

    // Modal & Action States
    const [showApproveModal, setShowApproveModal] = useState<boolean>(false);
    const [showRejectModal, setShowRejectModal] = useState<boolean>(false);
    const [rejectionReason, setRejectionReason] = useState<string>('');
    const [reviewerNotes, setReviewerNotes] = useState<string>('Verified and clinically attested.');
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [statusBanner, setStatusBanner] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

    // 1. Fetch Drafts Queue from Backend M23
    const loadDraftQueue = useCallback(async () => {
        setIsLoadingQueue(true);
        try {
            const res = await approvalApi.listDrafts({ page: 1, page_size: 30 });
            setDraftMedicalRecords(res.medical_records || []);
            setDraftPrescriptions(res.prescriptions || []);

            // Set initial selected item if not set
            if (!selectedDraftId) {
                if (activeTab === 'medical_records' && res.medical_records.length > 0) {
                    selectMedicalRecord(res.medical_records[0]);
                } else if (activeTab === 'prescriptions' && res.prescriptions.length > 0) {
                    selectPrescription(res.prescriptions[0]);
                }
            } else {
                // If queryId provided, locate it
                const targetMr = res.medical_records.find((m) => m.record_id === selectedDraftId);
                if (targetMr) {
                    selectMedicalRecord(targetMr);
                    setActiveTab('medical_records');
                } else {
                    const targetRx = res.prescriptions.find((p) => p.prescription_id === selectedDraftId);
                    if (targetRx) {
                        selectPrescription(targetRx);
                        setActiveTab('prescriptions');
                    }
                }
            }
        } catch (err) {
            console.error('Failed to load approval drafts queue:', err);
        } finally {
            setIsLoadingQueue(false);
        }
    }, [selectedDraftId, activeTab]);

    useEffect(() => {
        loadDraftQueue();
    }, [loadDraftQueue]);

    // Select Medical Record
    const selectMedicalRecord = (item: DraftItem) => {
        setSelectedDraftId(item.record_id || null);
        setCurrentStatus('DRAFT');
        setFinalizedTimestamp(null);
        if (item.chief_complaint) setChiefComplaint(item.chief_complaint);
        if (item.assessment) setAssessment(item.assessment);
        if (item.confidence) setAiConfidence(item.confidence);
        if (item.basis) setClinicalBasis(item.basis);

        if (item.content) {
            const soap = item.content.soap || item.content;
            if (soap.subjective?.chief_complaint) setChiefComplaint(soap.subjective.chief_complaint);
            if (soap.assessment?.primary_diagnosis) setAssessment(soap.assessment.primary_diagnosis);
            if (soap.assessment?.icd10_code) setIcd10Code(soap.assessment.icd10_code);
            if (soap.plan?.counseling || soap.plan?.follow_up) {
                setPlanText(`${soap.plan.counseling || ''} ${soap.plan.follow_up || ''}`.trim());
            }
        }
        setStatusBanner(null);
    };

    // Select Prescription
    const selectPrescription = (item: DraftItem) => {
        setSelectedDraftId(item.prescription_id || null);
        setCurrentStatus('DRAFT');
        setFinalizedTimestamp(null);
        if (item.medications && item.medications.length > 0) {
            setMedications(item.medications);
        }
        if (item.notes) setNotes(item.notes);
        setStatusBanner(null);
    };

    // Tab Switching
    const handleTabChange = (tab: 'medical_records' | 'prescriptions') => {
        setActiveTab(tab);
        setSelectedDraftId(null);
        setCurrentStatus('DRAFT');
        setFinalizedTimestamp(null);
        setStatusBanner(null);
        if (tab === 'medical_records' && draftMedicalRecords.length > 0) {
            selectMedicalRecord(draftMedicalRecords[0]);
        } else if (tab === 'prescriptions' && draftPrescriptions.length > 0) {
            selectPrescription(draftPrescriptions[0]);
        }
    };

    // Medication Row Management
    const handleMedicationChange = (index: number, field: keyof Medication, value: any) => {
        const updated = [...medications];
        updated[index] = { ...updated[index], [field]: value };
        setMedications(updated);
    };

    const handleAddMedication = () => {
        setMedications([
            ...medications,
            {
                name: '',
                dosage: '500mg',
                frequency: 'Once daily',
                duration: '14 days',
                route: 'oral',
                instructions: 'Take as directed.',
                quantity: 14,
                refills: 0,
            },
        ]);
    };

    const handleRemoveMedication = (index: number) => {
        setMedications(medications.filter((_, i) => i !== index));
    };

    // 2. Action: Doctor Approves Draft (DRAFT -> FINALIZED)
    const handleConfirmApprove = async () => {
        if (!selectedDraftId) return;
        setIsSubmitting(true);
        setStatusBanner(null);
        try {
            if (activeTab === 'medical_records') {
                const res = await approvalApi.reviewMedicalRecord(selectedDraftId, {
                    action: 'approve',
                    reviewer_notes: reviewerNotes,
                    edited_content: {
                        chief_complaint: chiefComplaint,
                        assessment,
                        icd10_code: icd10Code,
                        plan: planText,
                    },
                });
                setCurrentStatus(res.status.toUpperCase());
                setFinalizedTimestamp(res.reviewed_at || new Date().toISOString());
                setStatusBanner({
                    type: 'success',
                    message: `Medical Record Approved and Finalized. Status: ${res.status.toUpperCase()}. Attested by ${reviewerName}.`,
                });
            } else {
                const res = await approvalApi.reviewPrescription(selectedDraftId, {
                    action: 'approve',
                    reviewer_notes: reviewerNotes,
                    edited_medications: medications,
                });
                setCurrentStatus(res.status.toUpperCase());
                setFinalizedTimestamp(res.reviewed_at || new Date().toISOString());
                setStatusBanner({
                    type: 'success',
                    message: `Prescription Order Approved and Finalized. Status: ${res.status.toUpperCase()}. Legal electronic signature stamped.`,
                });
            }
            setShowApproveModal(false);
            // Refresh queue list
            const queueRes = await approvalApi.listDrafts();
            setDraftMedicalRecords(queueRes.medical_records || []);
            setDraftPrescriptions(queueRes.prescriptions || []);
        } catch (err: any) {
            console.error('Approval failed:', err);
            setStatusBanner({
                type: 'error',
                message: err.message || 'Failed to approve draft. Duplicate approval safely prevented.',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    // 3. Action: Doctor Rejects Draft (DRAFT -> AMENDED/CANCELLED)
    const handleConfirmReject = async () => {
        if (!selectedDraftId) return;
        if (!rejectionReason.trim()) {
            setStatusBanner({
                type: 'error',
                message: 'Please provide a clinical rejection reason before confirming.',
            });
            return;
        }
        setIsSubmitting(true);
        setStatusBanner(null);
        try {
            if (activeTab === 'medical_records') {
                const res = await approvalApi.reviewMedicalRecord(selectedDraftId, {
                    action: 'reject',
                    reviewer_notes: reviewerNotes,
                    rejection_reason: rejectionReason,
                });
                setCurrentStatus(res.status.toUpperCase());
                setStatusBanner({
                    type: 'info',
                    message: `Draft Medical Record Rejected (Status: ${res.status.toUpperCase()}). Rejection Reason logged to audit trail.`,
                });
            } else {
                const res = await approvalApi.reviewPrescription(selectedDraftId, {
                    action: 'reject',
                    reviewer_notes: reviewerNotes,
                    rejection_reason: rejectionReason,
                });
                setCurrentStatus(res.status.toUpperCase());
                setStatusBanner({
                    type: 'info',
                    message: `Draft Prescription Order Rejected (Status: ${res.status.toUpperCase()}). Rejection Reason logged to audit trail.`,
                });
            }
            setShowRejectModal(false);
            setRejectionReason('');
            // Refresh queue
            const queueRes = await approvalApi.listDrafts();
            setDraftMedicalRecords(queueRes.medical_records || []);
            setDraftPrescriptions(queueRes.prescriptions || []);
        } catch (err: any) {
            console.error('Rejection failed:', err);
            setStatusBanner({
                type: 'error',
                message: err.message || 'Failed to reject draft.',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    // 4. Action: Request Changes (keeps DRAFT)
    const handleRequestChanges = async () => {
        if (!selectedDraftId) return;
        setIsSubmitting(true);
        setStatusBanner(null);
        try {
            if (activeTab === 'medical_records') {
                const res = await approvalApi.reviewMedicalRecord(selectedDraftId, {
                    action: 'request_changes',
                    reviewer_notes: reviewerNotes,
                    edited_content: {
                        chief_complaint: chiefComplaint,
                        assessment,
                        icd10_code: icd10Code,
                        plan: planText,
                    },
                });
                setCurrentStatus(res.status.toUpperCase());
                setStatusBanner({
                    type: 'success',
                    message: 'Draft changes saved. Record remains in DRAFT status for further clinical iteration.',
                });
            } else {
                const res = await approvalApi.reviewPrescription(selectedDraftId, {
                    action: 'request_changes',
                    reviewer_notes: reviewerNotes,
                    edited_medications: medications,
                });
                setCurrentStatus(res.status.toUpperCase());
                setStatusBanner({
                    type: 'success',
                    message: 'Draft prescription modified. Remains in DRAFT status.',
                });
            }
        } catch (err: any) {
            console.error('Request changes failed:', err);
            setStatusBanner({
                type: 'error',
                message: err.message || 'Failed to update draft.',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const isFinalized = currentStatus === 'FINALIZED';
    const isRejected = currentStatus === 'AMENDED' || currentStatus === 'CANCELLED';

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            {/* Header with M23 Gate Badge */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-200 dark:border-gray-800 pb-4">
                <div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/60 px-2 py-0.5 rounded border border-purple-200 dark:border-purple-800">
                            Milestone U-11
                        </span>
                        <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">
                            Human Approval Gate (M23)
                        </span>
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                        Doctor Human Review & Approval Gate
                    </h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Mandatory human-in-the-loop authorization. Only explicit clinician approval transitions AI clinical content from DRAFT to FINALIZED.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => router.push('/doctor/prescriptions')}
                    >
                        💊 Prescriptions Workspace
                    </Button>
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => router.push('/doctor/scribe')}
                    >
                        🎙️ Ambient Scribe
                    </Button>
                </div>
            </div>

            {/* Notification Banner */}
            {statusBanner && (
                <Alert
                    variant={statusBanner.type === 'error' ? 'error' : statusBanner.type === 'success' ? 'success' : 'info'}
                    title={statusBanner.type === 'error' ? 'Authorization Notice' : 'System Notification'}
                >
                    {statusBanner.message}
                </Alert>
            )}

            {/* Queue Navigation Tabs */}
            <div className="flex items-center gap-4 border-b border-gray-200 dark:border-gray-800">
                <button
                    type="button"
                    onClick={() => handleTabChange('medical_records')}
                    className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                        activeTab === 'medical_records'
                            ? 'border-purple-600 text-purple-600 dark:text-purple-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
                    }`}
                >
                    <span>📝 Draft Medical Notes (SOAP)</span>
                    <Badge variant={draftMedicalRecords.length > 0 ? 'purple' : 'neutral'}>
                        {draftMedicalRecords.length}
                    </Badge>
                </button>

                <button
                    type="button"
                    onClick={() => handleTabChange('prescriptions')}
                    className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
                        activeTab === 'prescriptions'
                            ? 'border-purple-600 text-purple-600 dark:text-purple-400'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400'
                    }`}
                >
                    <span>💊 Draft Prescriptions</span>
                    <Badge variant={draftPrescriptions.length > 0 ? 'warning' : 'neutral'}>
                        {draftPrescriptions.length}
                    </Badge>
                </button>
            </div>

            {/* Main Split-Screen Workspace: Queue List (Left) + Contextual Review (Right) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* Left Column: Drafts Pending Review Queue */}
                <div className="lg:col-span-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">
                            Pending Review Queue
                        </h3>
                        <Button size="sm" variant="secondary" onClick={loadDraftQueue}>
                            🔄 Refresh
                        </Button>
                    </div>

                    {isLoadingQueue ? (
                        <div className="p-8 text-center text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
                            Loading review queue...
                        </div>
                    ) : activeTab === 'medical_records' ? (
                        draftMedicalRecords.length === 0 ? (
                            <div className="p-8 text-center text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 rounded-xl border border-dashed border-gray-300 dark:border-gray-800">
                                No draft medical records pending review.
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {draftMedicalRecords.map((mr) => (
                                    <div
                                        key={mr.record_id}
                                        onClick={() => selectMedicalRecord(mr)}
                                        className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                                            selectedDraftId === mr.record_id
                                                ? 'bg-purple-50/80 dark:bg-purple-950/40 border-purple-400 dark:border-purple-700 shadow-sm'
                                                : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 hover:border-gray-300'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="font-bold text-gray-900 dark:text-white">
                                                {mr.patient_name || 'Patient'}
                                            </span>
                                            <Badge variant="warning">DRAFT</Badge>
                                        </div>
                                        <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 font-medium truncate">
                                            {mr.assessment || mr.chief_complaint || 'Clinical Note'}
                                        </div>
                                        <div className="text-[11px] text-gray-400 mt-1 flex items-center justify-between">
                                            <span>ID: {mr.record_id?.substring(0, 8)}...</span>
                                            <span>{new Date(mr.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )
                    ) : draftPrescriptions.length === 0 ? (
                        <div className="p-8 text-center text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 rounded-xl border border-dashed border-gray-300 dark:border-gray-800">
                            No draft prescriptions pending review.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {draftPrescriptions.map((rx) => (
                                <div
                                    key={rx.prescription_id}
                                    onClick={() => selectPrescription(rx)}
                                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                                        selectedDraftId === rx.prescription_id
                                            ? 'bg-purple-50/80 dark:bg-purple-950/40 border-purple-400 dark:border-purple-700 shadow-sm'
                                            : 'bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800 hover:border-gray-300'
                                    }`}
                                >
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="font-bold text-gray-900 dark:text-white">
                                            {rx.patient_name || 'Patient'}
                                        </span>
                                        <Badge variant="warning">DRAFT</Badge>
                                    </div>
                                    <div className="text-xs text-gray-600 dark:text-gray-300 mt-1 font-medium">
                                        {rx.medications ? `${rx.medications.length} Medication(s)` : 'Medication Order'}
                                    </div>
                                    <div className="text-[11px] text-gray-400 mt-1 flex items-center justify-between">
                                        <span>ID: {rx.prescription_id?.substring(0, 8)}...</span>
                                        <span>{new Date(rx.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Right Column: Contextual Review & Attestation Gate */}
                <div className="lg:col-span-8 space-y-4">
                    {/* Status & Review Header */}
                    <div className={`p-4 rounded-xl border flex flex-wrap items-center justify-between gap-3 ${
                        isFinalized
                            ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200'
                            : isRejected
                            ? 'bg-rose-50 dark:bg-rose-950/30 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200'
                            : 'bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200'
                    }`}>
                        <div className="flex items-center gap-3">
                            <span className="text-2xl">{isFinalized ? '🔒' : isRejected ? '❌' : '⏳'}</span>
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="font-bold text-sm">
                                        EHR Status: {currentStatus}
                                    </span>
                                    <Badge variant={isFinalized ? 'success' : isRejected ? 'danger' : 'warning'}>
                                        {isFinalized ? 'Legally Attested' : isRejected ? 'Rejected / Non-Final' : 'Pending Review'}
                                    </Badge>
                                </div>
                                <p className="text-xs opacity-90 mt-0.5">
                                    {isFinalized
                                        ? `Approved and finalized on ${finalizedTimestamp ? new Date(finalizedTimestamp).toLocaleString() : 'today'}. Duplicate review safely disabled.`
                                        : isRejected
                                        ? 'This draft was rejected and will remain non-final in the EHR.'
                                        : 'Review clinical content below. Edit any sections as needed, then approve or reject.'}
                                </p>
                            </div>
                        </div>

                        {selectedDraftId && (
                            <span className="text-xs font-mono bg-white/60 dark:bg-black/30 px-2.5 py-1 rounded">
                                ID: {selectedDraftId}
                            </span>
                        )}
                    </div>

                    {/* AI Explainability & Basis Callout */}
                    <Card className="border border-purple-200 dark:border-purple-900/60 bg-gradient-to-r from-purple-50/40 to-indigo-50/40 dark:from-purple-950/20 dark:to-indigo-950/20">
                        <CardContent className="p-4 space-y-2 text-xs">
                            <div className="flex items-center justify-between border-b border-purple-100 dark:border-purple-900/40 pb-2">
                                <div className="flex items-center gap-2">
                                    <span className="font-bold text-purple-900 dark:text-purple-200">
                                        🤖 AI Generation Evidence & Explainability
                                    </span>
                                    <Badge variant="primary">Confidence: {aiConfidence}%</Badge>
                                </div>
                                <span className="text-gray-500">M23 Physician Gate</span>
                            </div>
                            <p className="text-gray-700 dark:text-gray-300">
                                <span className="font-semibold text-purple-900 dark:text-purple-300">💡 Basis: </span>
                                {clinicalBasis}
                            </p>
                        </CardContent>
                    </Card>

                    {/* Form Review: Medical Record Content */}
                    {activeTab === 'medical_records' ? (
                        <Card>
                            <CardContent className="p-5 space-y-4">
                                <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 pb-3">
                                    <h2 className="text-base font-bold text-gray-900 dark:text-white">
                                        Structured Consultation Note (SOAP)
                                    </h2>
                                    <span className="text-xs text-gray-500">
                                        {isFinalized ? '🔒 Read-Only (Finalized)' : '✏️ Clinician Editable'}
                                    </span>
                                </div>

                                <div className="space-y-3 text-sm">
                                    <div>
                                        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                            Subjective / Chief Complaint:
                                        </label>
                                        <input
                                            type="text"
                                            disabled={isFinalized}
                                            value={chiefComplaint}
                                            onChange={(e) => setChiefComplaint(e.target.value)}
                                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded p-2 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                        />
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                                Assessment / Primary Diagnosis:
                                            </label>
                                            <input
                                                type="text"
                                                disabled={isFinalized}
                                                value={assessment}
                                                onChange={(e) => setAssessment(e.target.value)}
                                                className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded p-2 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                                ICD-10 Diagnostic Code:
                                            </label>
                                            <input
                                                type="text"
                                                disabled={isFinalized}
                                                value={icd10Code}
                                                onChange={(e) => setIcd10Code(e.target.value)}
                                                className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded p-2 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                            Treatment Plan / Patient Instructions:
                                        </label>
                                        <textarea
                                            rows={3}
                                            disabled={isFinalized}
                                            value={planText}
                                            onChange={(e) => setPlanText(e.target.value)}
                                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded p-2 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                        />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ) : (
                        /* Form Review: Prescription Content */
                        <Card>
                            <CardContent className="p-5 space-y-4">
                                <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 pb-3">
                                    <h2 className="text-base font-bold text-gray-900 dark:text-white">
                                        Medications Order (Safety Verified)
                                    </h2>
                                    {!isFinalized && (
                                        <Button size="sm" variant="secondary" onClick={handleAddMedication}>
                                            ➕ Add Medication
                                        </Button>
                                    )}
                                </div>

                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-sm">
                                        <thead className="bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300 text-xs uppercase font-semibold">
                                            <tr>
                                                <th className="px-3 py-2 text-left">Medication</th>
                                                <th className="px-3 py-2 text-left">Dosage</th>
                                                <th className="px-3 py-2 text-left">Frequency</th>
                                                <th className="px-3 py-2 text-left">Duration</th>
                                                <th className="px-3 py-2 text-left">Route</th>
                                                <th className="px-3 py-2 text-center">Refills</th>
                                                {!isFinalized && <th className="px-3 py-2 text-center">Action</th>}
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                                            {medications.map((med, index) => (
                                                <tr key={index}>
                                                    <td className="px-3 py-2">
                                                        <input
                                                            type="text"
                                                            disabled={isFinalized}
                                                            value={med.name}
                                                            onChange={(e) => handleMedicationChange(index, 'name', e.target.value)}
                                                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                                        />
                                                    </td>
                                                    <td className="px-3 py-2 w-28">
                                                        <input
                                                            type="text"
                                                            disabled={isFinalized}
                                                            value={med.dosage}
                                                            onChange={(e) => handleMedicationChange(index, 'dosage', e.target.value)}
                                                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                                        />
                                                    </td>
                                                    <td className="px-3 py-2 w-32">
                                                        <input
                                                            type="text"
                                                            disabled={isFinalized}
                                                            value={med.frequency}
                                                            onChange={(e) => handleMedicationChange(index, 'frequency', e.target.value)}
                                                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                                        />
                                                    </td>
                                                    <td className="px-3 py-2 w-28">
                                                        <input
                                                            type="text"
                                                            disabled={isFinalized}
                                                            value={med.duration}
                                                            onChange={(e) => handleMedicationChange(index, 'duration', e.target.value)}
                                                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                                        />
                                                    </td>
                                                    <td className="px-3 py-2 w-28">
                                                        <select
                                                            disabled={isFinalized}
                                                            value={med.route || 'oral'}
                                                            onChange={(e) => handleMedicationChange(index, 'route', e.target.value)}
                                                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-2 py-1 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                                        >
                                                            <option value="oral">Oral</option>
                                                            <option value="sublingual">Sublingual</option>
                                                            <option value="inhalation">Inhalation</option>
                                                            <option value="IV">Intravenous</option>
                                                        </select>
                                                    </td>
                                                    <td className="px-3 py-2 w-20 text-center">
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            disabled={isFinalized}
                                                            value={med.refills || 0}
                                                            onChange={(e) => handleMedicationChange(index, 'refills', parseInt(e.target.value) || 0)}
                                                            className="w-full text-center bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded px-1 py-1 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                                        />
                                                    </td>
                                                    {!isFinalized && (
                                                        <td className="px-3 py-2 w-16 text-center">
                                                            <button
                                                                type="button"
                                                                onClick={() => handleRemoveMedication(index)}
                                                                className="text-red-500 hover:text-red-700 dark:hover:text-red-400 font-bold p-1"
                                                            >
                                                                ✕
                                                            </button>
                                                        </td>
                                                    )}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                <div className="pt-2">
                                    <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                                        Clinical Prescribing Directions:
                                    </label>
                                    <textarea
                                        rows={2}
                                        disabled={isFinalized}
                                        value={notes}
                                        onChange={(e) => setNotes(e.target.value)}
                                        className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded p-2 text-sm text-gray-900 dark:text-white disabled:opacity-60"
                                    />
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Review Notes Input */}
                    {!isFinalized && (
                        <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 space-y-2">
                            <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 uppercase">
                                Clinician Attestation Notes (Optional):
                            </label>
                            <input
                                type="text"
                                value={reviewerNotes}
                                onChange={(e) => setReviewerNotes(e.target.value)}
                                placeholder="e.g. Reviewed against laboratory results and approved without modification."
                                className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded p-2 text-sm text-gray-900 dark:text-white"
                            />
                        </div>
                    )}

                    {/* Clinician Action Toolbar */}
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
                        <div className="flex items-center gap-2">
                            {!isFinalized && (
                                <Button
                                    variant="danger"
                                    onClick={() => setShowRejectModal(true)}
                                    disabled={isSubmitting || !selectedDraftId}
                                >
                                    ❌ Reject Draft
                                </Button>
                            )}
                            {!isFinalized && (
                                <Button
                                    variant="secondary"
                                    onClick={handleRequestChanges}
                                    disabled={isSubmitting || !selectedDraftId}
                                >
                                    💾 Save / Request Changes
                                </Button>
                            )}
                        </div>

                        <div className="flex items-center gap-3">
                            {isFinalized ? (
                                <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                                    <span>🔒</span>
                                    <span>Content is finalized. Immutable in production EHR.</span>
                                </div>
                            ) : (
                                <Button
                                    variant="primary"
                                    onClick={() => setShowApproveModal(true)}
                                    disabled={isSubmitting || !selectedDraftId}
                                >
                                    ✅ Approve & Finalize
                                </Button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Confirmation Modal: Approve */}
            <Modal
                isOpen={showApproveModal}
                onClose={() => setShowApproveModal(false)}
                title="Physician Attestation & Finalization (Gate M23)"
            >
                <div className="space-y-4">
                    <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                        Under clinical safety protocols, you are legally attesting as the licensed physician to the clinical accuracy and safety of this draft.
                    </p>
                    <div className="p-3 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 rounded-lg text-xs text-purple-900 dark:text-purple-200">
                        <strong>Action:</strong> Status will transition permanently from <span className="font-mono font-bold">DRAFT</span> to <span className="font-mono font-bold text-emerald-600">FINALIZED</span>. An immutable audit record will be logged.
                    </div>

                    <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-200 dark:border-gray-800">
                        <Button variant="secondary" onClick={() => setShowApproveModal(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            onClick={handleConfirmApprove}
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? 'Attesting...' : 'Confirm & Finalize'}
                        </Button>
                    </div>
                </div>
            </Modal>

            {/* Confirmation Modal: Reject with Mandatory Reason */}
            <Modal
                isOpen={showRejectModal}
                onClose={() => setShowRejectModal(false)}
                title="Reject AI Clinical Draft"
            >
                <div className="space-y-4">
                    <p className="text-sm text-gray-600 dark:text-gray-300">
                        Please specify the clinical reason for rejecting this draft. The rejection reason will be recorded in the audit trail.
                    </p>
                    <div>
                        <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 uppercase mb-1">
                            Rejection Reason (Required):
                        </label>
                        <textarea
                            rows={3}
                            value={rejectionReason}
                            onChange={(e) => setRejectionReason(e.target.value)}
                            placeholder="e.g. Inappropriate medication choice given renal impairment; or diagnostic criteria unfulfilled."
                            className="w-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded p-2 text-sm text-gray-900 dark:text-white"
                        />
                    </div>

                    <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-200 dark:border-gray-800">
                        <Button variant="secondary" onClick={() => setShowRejectModal(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="danger"
                            onClick={handleConfirmReject}
                            disabled={isSubmitting || !rejectionReason.trim()}
                        >
                            {isSubmitting ? 'Rejecting...' : 'Confirm Rejection'}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

export default function DoctorApprovalGatePage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#0B0F19]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
            </div>
        }>
            <DoctorApprovalGateContent />
        </Suspense>
    );
}
