'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { patientReportsApi, PatientReportItem } from '@/lib/api';
import { Card, CardContent, Button, Badge } from '@/components/ui';

const CATEGORIES = [
    { key: 'all', label: 'All Reports' },
    { key: 'lab', label: 'Laboratory' },
    { key: 'imaging', label: 'Imaging & Scans' },
    { key: 'prescription', label: 'Prescriptions' },
    { key: 'discharge', label: 'Discharge Summaries' },
    { key: 'other', label: 'Other' },
];

export default function PatientReportsPage() {
    const [reports, setReports] = useState<PatientReportItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState('all');
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

    // Form states
    const [title, setTitle] = useState('');
    const [reportType, setReportType] = useState('lab');
    const [notes, setNotes] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isDragOver, setIsDragOver] = useState(false);

    // Deleting state
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        loadReports(activeFilter);
    }, [activeFilter]);

    const loadReports = async (filter: string) => {
        setIsLoading(true);
        try {
            const data = await patientReportsApi.list(filter);
            setReports(data.reports);
        } catch (err: any) {
            console.error('Failed to load reports:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            validateAndSetFile(e.target.files[0]);
        }
    };

    const validateAndSetFile = (file: File) => {
        setUploadError(null);
        setUploadSuccess(null);

        const allowedMimes = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'];
        if (!allowedMimes.includes(file.type)) {
            setUploadError(`Unsupported file format (${file.type || 'unknown'}). Allowed: PDF, PNG, JPEG, WebP.`);
            return;
        }

        const maxBytes = 10 * 1024 * 1024; // 10 MB
        if (file.size > maxBytes) {
            setUploadError(`File is too large (${(file.size / (1024 * 1024)).toFixed(2)} MB). Max limit is 10 MB.`);
            return;
        }

        setSelectedFile(file);
        if (!title.trim()) {
            // Auto-fill title from filename without extension
            const nameWithoutExt = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
            setTitle(nameWithoutExt);
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            validateAndSetFile(e.dataTransfer.files[0]);
        }
    };

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragOver(true);
    };

    const handleDragLeave = () => {
        setIsDragOver(false);
    };

    const handleUploadSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedFile) {
            setUploadError('Please select or drop a medical document file to upload.');
            return;
        }
        if (!title.trim()) {
            setUploadError('Please specify a title for this medical report.');
            return;
        }

        setIsUploading(true);
        setUploadError(null);
        setUploadSuccess(null);

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('title', title.trim());
            formData.append('report_type', reportType);
            if (notes.trim()) {
                formData.append('notes', notes.trim());
            }

            await patientReportsApi.upload(formData);
            setUploadSuccess('Report uploaded and archived successfully!');
            setTitle('');
            setNotes('');
            setSelectedFile(null);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
            await loadReports(activeFilter);
        } catch (err: any) {
            setUploadError(err.message || 'Failed to upload report. Please check file size and format.');
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async (reportId: string) => {
        if (!confirm('Are you sure you want to delete this report? This action cannot be undone.')) {
            return;
        }
        setDeletingId(reportId);
        try {
            await patientReportsApi.delete(reportId);
            setReports((prev) => prev.filter((r) => r.report_id !== reportId));
        } catch (err: any) {
            alert(err.message || 'Failed to delete report.');
        } finally {
            setDeletingId(null);
        }
    };

    const handleDownload = async (report: PatientReportItem) => {
        try {
            const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
            const res = await fetch(patientReportsApi.getDownloadUrl(report.report_id), {
                headers: {
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
            });
            if (!res.ok) {
                throw new Error(`Failed to download report (${res.status})`);
            }
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = report.file_name;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (err: any) {
            alert(err.message || 'Download failed');
        }
    };

    const formatBytes = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    const formatDate = (isoString: string) => {
        const d = new Date(isoString);
        return d.toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getBadgeVariant = (type: string) => {
        switch (type) {
            case 'lab':
                return 'primary';
            case 'imaging':
                return 'purple';
            case 'prescription':
                return 'success';
            case 'discharge':
                return 'warning';
            default:
                return 'neutral';
        }
    };

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                        <span>📁 Patient Medical Reports & Documents</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Securely upload and manage laboratory test results, diagnostic scans, discharge summaries, and external prescriptions.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-1.5 rounded-full border border-emerald-200 dark:border-emerald-800/50 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span>HIPAA/ABDM Encrypted Storage</span>
                    </span>
                </div>
            </div>

            {/* Top Grid: Upload Drawer & Guidelines */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Upload Form Card (2 cols) */}
                <Card className="lg:col-span-2 border border-slate-200 dark:border-slate-800 shadow-sm bg-white dark:bg-slate-900">
                    <CardContent className="p-6">
                        <h2 className="text-base font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <span>📤 Upload Medical Document</span>
                            <span className="text-xs font-normal text-slate-500 dark:text-slate-400">
                                (Max 10 MB: PDF, PNG, JPG, WebP)
                            </span>
                        </h2>

                        <form onSubmit={handleUploadSubmit} className="space-y-4">
                            {/* Drag & Drop Box */}
                            <div
                                onDrop={handleDrop}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onClick={() => fileInputRef.current?.click()}
                                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                                    isDragOver
                                        ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/30 scale-[1.01]'
                                        : selectedFile
                                        ? 'border-emerald-500 bg-emerald-50/30 dark:bg-emerald-950/20'
                                        : 'border-slate-300 dark:border-slate-700 hover:border-blue-400 bg-slate-50/50 dark:bg-slate-800/40'
                                }`}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    className="hidden"
                                    accept=".pdf,image/png,image/jpeg,image/webp"
                                    onChange={handleFileChange}
                                />
                                {selectedFile ? (
                                    <div className="space-y-1">
                                        <div className="w-10 h-10 mx-auto rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-300 flex items-center justify-center font-bold text-lg">
                                            ✓
                                        </div>
                                        <p className="text-sm font-semibold text-slate-900 dark:text-white">
                                            {selectedFile.name}
                                        </p>
                                        <p className="text-xs text-slate-500 dark:text-slate-400">
                                            {formatBytes(selectedFile.size)} • {selectedFile.type || 'Document'}
                                        </p>
                                        <p className="text-[11px] text-blue-600 dark:text-blue-400 hover:underline pt-1">
                                            Click or drop to replace file
                                        </p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <div className="w-12 h-12 mx-auto rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                            </svg>
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-slate-900 dark:text-white">
                                                <span className="text-blue-600 dark:text-blue-400 font-semibold hover:underline">
                                                    Click to browse
                                                </span>{' '}
                                                or drag & drop file here
                                            </p>
                                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                                Supports Blood Reports, MRI/X-Ray Scans, Hospital Discharge Summaries
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Title & Category Row */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                        Document Title *
                                    </label>
                                    <input
                                        type="text"
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                        placeholder="e.g. Complete Blood Count (CBC) - Aug 2026"
                                        className="w-full text-sm px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                        Report Category *
                                    </label>
                                    <select
                                        value={reportType}
                                        onChange={(e) => setReportType(e.target.value)}
                                        className="w-full text-sm px-3.5 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                    >
                                        <option value="lab">Laboratory (Blood, Urine, Pathology)</option>
                                        <option value="imaging">Imaging & Radiology (X-Ray, CT, MRI, Ultrasound)</option>
                                        <option value="prescription">External Doctor Prescription</option>
                                        <option value="discharge">Discharge Summary / Clinical Note</option>
                                        <option value="other">Other Health Record</option>
                                    </select>
                                </div>
                            </div>

                            {/* Notes */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                                    Clinical Notes / Symptoms (Optional)
                                </label>
                                <textarea
                                    value={notes}
                                    onChange={(e) => setNotes(e.target.value)}
                                    rows={2}
                                    placeholder="e.g. Fasting sample taken at Apollo Diagnostics; doctor requested for cholesterol checkup."
                                    className="w-full text-sm px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                                />
                            </div>

                            {/* Feedback Messages */}
                            {uploadError && (
                                <div className="p-3 text-xs rounded-lg bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 flex items-start gap-2">
                                    <span className="font-bold">⚠️</span>
                                    <span>{uploadError}</span>
                                </div>
                            )}

                            {uploadSuccess && (
                                <div className="p-3 text-xs rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 flex items-start gap-2">
                                    <span className="font-bold">✓</span>
                                    <span>{uploadSuccess}</span>
                                </div>
                            )}

                            {/* Submit Button */}
                            <div className="flex justify-end gap-3 pt-2">
                                <Button
                                    type="submit"
                                    variant="primary"
                                    disabled={!selectedFile || isUploading}
                                    className="px-6 py-2 text-sm font-semibold flex items-center gap-2"
                                >
                                    {isUploading ? (
                                        <>
                                            <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                                            <span>Archiving Document...</span>
                                        </>
                                    ) : (
                                        <>
                                            <span>Upload & Save Report</span>
                                            <span>→</span>
                                        </>
                                    )}
                                </Button>
                            </div>
                        </form>
                    </CardContent>
                </Card>

                {/* Storage & Privacy Info Card (1 col) */}
                <div className="space-y-4">
                    <Card className="border border-slate-200 dark:border-slate-800 shadow-sm bg-gradient-to-br from-blue-50/40 via-white to-indigo-50/30 dark:from-slate-900 dark:to-slate-800/60">
                        <CardContent className="p-5 space-y-4 text-xs text-slate-600 dark:text-slate-300">
                            <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                                <span>🔒 Patient Data Isolation</span>
                            </h3>
                            <p>
                                All files are encrypted at rest and isolated strictly to your patient ID under isolated tenant directories.
                            </p>
                            <div className="space-y-2 pt-1 border-t border-slate-200 dark:border-slate-700">
                                <div className="flex items-center justify-between font-medium">
                                    <span>Supported Formats:</span>
                                    <span className="font-mono text-slate-800 dark:text-slate-200">PDF, PNG, JPG, WebP</span>
                                </div>
                                <div className="flex items-center justify-between font-medium">
                                    <span>Max File Size:</span>
                                    <span className="font-mono text-slate-800 dark:text-slate-200">10 Megabytes</span>
                                </div>
                                <div className="flex items-center justify-between font-medium">
                                    <span>Access Control:</span>
                                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Strict 403 RBAC</span>
                                </div>
                            </div>
                            <div className="p-3 bg-blue-100/50 dark:bg-blue-950/40 rounded-lg border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-300 text-[11px]">
                                💡 <strong>Telehealth Integration:</strong> Uploaded reports are immediately available to your consulting doctor during virtual tele-consultations.
                            </div>
                        </CardContent>
                    </Card>

                    {/* Quick Link to Reminders */}
                    <Card className="border border-purple-200 dark:border-purple-900/40 bg-purple-50/30 dark:bg-purple-950/20">
                        <CardContent className="p-4 flex items-center justify-between">
                            <div>
                                <h4 className="text-xs font-bold text-purple-900 dark:text-purple-300">
                                    Medicine Reminders
                                </h4>
                                <p className="text-[11px] text-purple-700 dark:text-purple-400 mt-0.5">
                                    Schedule daily dosage alerts
                                </p>
                            </div>
                            <Link href="/patient/reminders">
                                <Button variant="secondary" size="sm" className="text-xs">
                                    Open Reminders →
                                </Button>
                            </Link>
                        </CardContent>
                    </Card>
                </div>
            </div>

            {/* Document Library Section */}
            <div className="space-y-4 pt-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2 overflow-x-auto pb-1">
                        {CATEGORIES.map((cat) => (
                            <button
                                key={cat.key}
                                onClick={() => setActiveFilter(cat.key)}
                                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
                                    activeFilter === cat.key
                                        ? 'bg-blue-600 text-white shadow-sm'
                                        : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
                                }`}
                            >
                                {cat.label}
                            </button>
                        ))}
                    </div>

                    <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                        Showing {reports.length} {reports.length === 1 ? 'document' : 'documents'}
                    </span>
                </div>

                {isLoading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {[1, 2, 3].map((i) => (
                            <Card key={i} className="p-5 animate-pulse border border-slate-200 dark:border-slate-800">
                                <div className="h-4 w-2/3 bg-slate-200 dark:bg-slate-700 rounded mb-3" />
                                <div className="h-3 w-1/2 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                                <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded mt-4" />
                            </Card>
                        ))}
                    </div>
                ) : reports.length === 0 ? (
                    <Card className="border border-dashed border-slate-300 dark:border-slate-800 p-12 text-center bg-white dark:bg-slate-900">
                        <div className="w-12 h-12 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center text-xl mb-3">
                            📄
                        </div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                            No medical reports found
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">
                            {activeFilter === 'all'
                                ? 'You haven’t uploaded any medical reports or lab scans yet. Use the upload box above to archive your first document.'
                                : `No documents found under the '${activeFilter}' category.`}
                        </p>
                    </Card>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {reports.map((report) => (
                            <Card
                                key={report.report_id}
                                className="border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm transition-all bg-white dark:bg-slate-900 flex flex-col justify-between"
                            >
                                <CardContent className="p-5 space-y-3">
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="flex items-center gap-2.5">
                                            <div className="w-9 h-9 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-sm shrink-0">
                                                {report.mime_type.includes('pdf') ? 'PDF' : 'IMG'}
                                            </div>
                                            <div className="min-w-0">
                                                <h4 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                                    {report.title}
                                                </h4>
                                                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                                                    {report.file_name}
                                                </p>
                                            </div>
                                        </div>

                                        <Badge
                                            variant={getBadgeVariant(report.report_type) as any}
                                            className="text-[10px] uppercase font-bold tracking-wider shrink-0"
                                        >
                                            {report.report_type}
                                        </Badge>
                                    </div>

                                    {report.notes && (
                                        <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 bg-slate-50 dark:bg-slate-800/60 p-2 rounded border border-slate-100 dark:border-slate-800">
                                            {report.notes}
                                        </p>
                                    )}

                                    <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                                        <span>{formatBytes(report.file_size_bytes)}</span>
                                        <span>{formatDate(report.created_at)}</span>
                                    </div>

                                    <div className="pt-2 flex items-center gap-2">
                                        <Button
                                            variant="secondary"
                                            size="sm"
                                            onClick={() => handleDownload(report)}
                                            className="flex-1 text-xs font-semibold flex items-center justify-center gap-1.5"
                                        >
                                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                            </svg>
                                            <span>Download</span>
                                        </Button>

                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            disabled={deletingId === report.report_id}
                                            onClick={() => handleDelete(report.report_id)}
                                            className="text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 px-2.5"
                                            title="Delete report"
                                        >
                                            {deletingId === report.report_id ? (
                                                <span className="w-3 h-3 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                                            ) : (
                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                </svg>
                                            )}
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
