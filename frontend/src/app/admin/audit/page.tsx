'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { adminAuditApi, AuditLogItem, AuditLogListResponse } from '@/lib/api';
import { Button, Card, CardContent, Badge } from '@/components/ui';

const RESOURCE_TYPES = [
    { key: 'all', label: 'All Resources' },
    { key: 'users', label: 'Users & Roles' },
    { key: 'consents', label: 'Consent Agreements' },
    { key: 'appointments', label: 'Appointments & Queue' },
    { key: 'prescriptions', label: 'Prescriptions' },
    { key: 'medical_records', label: 'Medical Records' },
    { key: 'voice_notes', label: 'Voice Notes' },
];

const OUTCOMES = ['all', 'SUCCESS', 'FAILURE', 'DENIED', 'ERROR'];

export default function AdminAuditPage() {
    const [data, setData] = useState<AuditLogListResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [resourceType, setResourceType] = useState('all');
    const [outcomeFilter, setOutcomeFilter] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    // Selected log item for payload drawer inspection
    const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

    useEffect(() => {
        loadLogs();
    }, [page, resourceType, outcomeFilter, startDate, endDate]);

    const loadLogs = async () => {
        setIsLoading(true);
        try {
            const res = await adminAuditApi.listLogs({
                page,
                page_size: 25,
                resource_type: resourceType !== 'all' ? resourceType : undefined,
                outcome: outcomeFilter !== 'all' ? outcomeFilter : undefined,
                start_date: startDate ? new Date(startDate).toISOString() : undefined,
                end_date: endDate ? new Date(endDate + 'T23:59:59').toISOString() : undefined,
                search: searchTerm.trim() || undefined,
            });
            setData(res);
        } catch (err: any) {
            console.error('Failed to load audit logs:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setPage(1);
        loadLogs();
    };

    const handleClearFilters = () => {
        setResourceType('all');
        setOutcomeFilter('all');
        setSearchTerm('');
        setStartDate('');
        setEndDate('');
        setPage(1);
    };

    const formatTimestamp = (isoString: string) => {
        const d = new Date(isoString);
        return d.toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    const getActionBadgeVariant = (action: string) => {
        if (action.includes('REVOKE') || action.includes('DELETE') || action.includes('DEACTIVATE')) {
            return 'danger';
        }
        if (action.includes('GRANT') || action.includes('PROVISION') || action.includes('CREATE')) {
            return 'success';
        }
        if (action.includes('ROLE') || action.includes('STATUS') || action.includes('UPDATE')) {
            return 'purple';
        }
        return 'primary';
    };

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <Link href="/admin" className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs">
                            ← Admin Console
                        </Link>
                        <span className="text-slate-300 dark:text-slate-700">•</span>
                        <Badge variant="warning" className="text-[10px] uppercase font-bold">
                            FHIR AuditEvent
                        </Badge>
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white mt-1 flex items-center gap-2">
                        <span>🛡️ Compliance & Immutable Audit Trails</span>
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Append-only legal audit log capturing clinical authorizations, access grants, user state changes, and EHR interactions.
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadLogs}
                        disabled={isLoading}
                        className="text-xs"
                    >
                        ↻ Refresh Logs
                    </Button>
                </div>
            </div>

            {/* Integrity Assurance Notice */}
            <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900/60 bg-gradient-to-r from-blue-50 to-indigo-50/40 dark:from-blue-950/20 dark:to-indigo-950/20 flex items-start gap-3">
                <span className="text-xl shrink-0">🔒</span>
                <div className="text-xs text-blue-900 dark:text-blue-200 space-y-0.5">
                    <p className="font-bold">
                        Read-Only System Compliance Registry
                    </p>
                    <p className="text-blue-800/80 dark:text-blue-300/80 leading-relaxed">
                        Audit records are cryptographically recorded in an immutable append-only ledger. They cannot be modified, amended, or erased by any user or administrator, satisfying HIPAA Security Rule § 164.312(b) and ABDM Milestone standards.
                    </p>
                </div>
            </div>

            {/* Filter Toolbar */}
            <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                <CardContent className="p-4 space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        {/* Resource Type */}
                        <div>
                            <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                                Resource Type
                            </label>
                            <select
                                value={resourceType}
                                onChange={(e) => {
                                    setResourceType(e.target.value);
                                    setPage(1);
                                }}
                                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            >
                                {RESOURCE_TYPES.map((r) => (
                                    <option key={r.key} value={r.key}>{r.label}</option>
                                ))}
                            </select>
                        </div>

                        {/* Outcome */}
                        <div>
                            <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                                Event Outcome
                            </label>
                            <select
                                value={outcomeFilter}
                                onChange={(e) => {
                                    setOutcomeFilter(e.target.value);
                                    setPage(1);
                                }}
                                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            >
                                {OUTCOMES.map((o) => (
                                    <option key={o} value={o}>{o === 'all' ? 'All Outcomes' : o}</option>
                                ))}
                            </select>
                        </div>

                        {/* Date From */}
                        <div>
                            <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                                From Date
                            </label>
                            <input
                                type="date"
                                value={startDate}
                                onChange={(e) => {
                                    setStartDate(e.target.value);
                                    setPage(1);
                                }}
                                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            />
                        </div>

                        {/* Date To */}
                        <div>
                            <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                                To Date
                            </label>
                            <input
                                type="date"
                                value={endDate}
                                onChange={(e) => {
                                    setEndDate(e.target.value);
                                    setPage(1);
                                }}
                                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                            />
                        </div>
                    </div>

                    {/* Search Row */}
                    <form onSubmit={handleSearchSubmit} className="flex gap-2 pt-1 border-t border-slate-100 dark:border-slate-800">
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Search by action (e.g. LOGIN, GRANT_CONSENT), operator email, or IP address..."
                            className="flex-1 text-xs px-3.5 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                        <Button type="submit" variant="primary" size="sm" className="text-xs">
                            Filter
                        </Button>
                        <Button type="button" variant="ghost" size="sm" onClick={handleClearFilters} className="text-xs">
                            Clear
                        </Button>
                    </form>
                </CardContent>
            </Card>

            {/* Audit Log Table */}
            <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-800">
                            <tr>
                                <th className="px-4 py-3">Timestamp (UTC)</th>
                                <th className="px-4 py-3">Operator</th>
                                <th className="px-4 py-3">Action</th>
                                <th className="px-4 py-3">Resource</th>
                                <th className="px-4 py-3">Outcome</th>
                                <th className="px-4 py-3 text-right">Payload</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {isLoading ? (
                                [1, 2, 3, 4, 5].map((i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td colSpan={6} className="px-4 py-3.5">
                                            <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-full" />
                                        </td>
                                    </tr>
                                ))
                            ) : !data || data.logs.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-4 py-12 text-center text-slate-400">
                                        No audit log records match the selected filters.
                                    </td>
                                </tr>
                            ) : (
                                data.logs.map((log) => (
                                    <tr
                                        key={log.log_id}
                                        className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                                    >
                                        <td className="px-4 py-3 font-mono text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap">
                                            {formatTimestamp(log.timestamp)}
                                        </td>
                                        <td className="px-4 py-3">
                                            {log.user_email ? (
                                                <div>
                                                    <span className="font-semibold text-slate-900 dark:text-white block">
                                                        {log.user_name || log.user_email}
                                                    </span>
                                                    <span className="text-[11px] text-slate-400 font-mono">
                                                        {log.user_email}
                                                    </span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-400 italic">System Agent</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <Badge
                                                variant={getActionBadgeVariant(log.action) as any}
                                                className="text-[10px] font-mono uppercase tracking-wider"
                                            >
                                                {log.action}
                                            </Badge>
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="font-semibold text-slate-800 dark:text-slate-200">
                                                {log.resource_type}
                                            </div>
                                            {log.resource_id && (
                                                <div className="text-[10px] text-slate-400 font-mono truncate max-w-[120px]">
                                                    {log.resource_id}
                                                </div>
                                            )}
                                        </td>
                                        <td className="px-4 py-3">
                                            <Badge
                                                variant={log.outcome === 'SUCCESS' ? 'success' : 'danger'}
                                                className="text-[10px] font-bold"
                                            >
                                                {log.outcome}
                                            </Badge>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <Button
                                                variant="secondary"
                                                size="sm"
                                                onClick={() => setSelectedLog(log)}
                                                className="text-[11px] px-2.5 py-1"
                                            >
                                                Inspect ↗
                                            </Button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination Footer */}
                {data && data.total > 0 && (
                    <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                        <span>
                            Showing {((page - 1) * data.page_size) + 1} - {Math.min(page * data.page_size, data.total)} of {data.total} audit events
                        </span>

                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={page <= 1 || isLoading}
                                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                                className="text-xs"
                            >
                                ← Previous
                            </Button>
                            <span className="font-mono text-xs">
                                Page {page} of {data.total_pages}
                            </span>
                            <Button
                                variant="outline"
                                size="sm"
                                disabled={page >= data.total_pages || isLoading}
                                onClick={() => setPage((p) => Math.min(p + 1, data.total_pages))}
                                className="text-xs"
                            >
                                Next →
                            </Button>
                        </div>
                    </div>
                )}
            </Card>

            {/* Audit Log Payload Detail Modal */}
            {selectedLog && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-2xl w-full shadow-2xl space-y-4 max-h-[85vh] overflow-hidden flex flex-col">
                        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                            <div>
                                <h3 className="font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
                                    <span>AuditEvent Payload Inspection</span>
                                    <Badge variant={selectedLog.outcome === 'SUCCESS' ? 'success' : 'danger'}>
                                        {selectedLog.outcome}
                                    </Badge>
                                </h3>
                                <p className="text-xs text-slate-500 font-mono mt-0.5">
                                    Event ID: {selectedLog.log_id}
                                </p>
                            </div>
                            <button
                                onClick={() => setSelectedLog(null)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="space-y-3 text-xs overflow-y-auto pr-1">
                            <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                                <div>
                                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Action</span>
                                    <span className="font-bold text-slate-900 dark:text-white">{selectedLog.action}</span>
                                </div>
                                <div>
                                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Resource</span>
                                    <span className="font-bold text-slate-900 dark:text-white">{selectedLog.resource_type} ({selectedLog.resource_id || 'Global'})</span>
                                </div>
                                <div>
                                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Operator Email</span>
                                    <span className="font-mono text-slate-800 dark:text-slate-200">{selectedLog.user_email || 'System'}</span>
                                </div>
                                <div>
                                    <span className="text-[10px] uppercase font-bold text-slate-400 block">Timestamp</span>
                                    <span className="font-mono text-slate-800 dark:text-slate-200">{formatTimestamp(selectedLog.timestamp)}</span>
                                </div>
                                {selectedLog.ip_address && (
                                    <div>
                                        <span className="text-[10px] uppercase font-bold text-slate-400 block">IP Address</span>
                                        <span className="font-mono">{selectedLog.ip_address}</span>
                                    </div>
                                )}
                            </div>

                            <div>
                                <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                                    Structured Event Payload (JSON)
                                </span>
                                <pre className="p-3 rounded-xl bg-slate-950 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-60">
                                    {JSON.stringify(selectedLog.details || {}, null, 2)}
                                </pre>
                            </div>
                        </div>

                        <div className="flex justify-end pt-2 border-t border-slate-200 dark:border-slate-800">
                            <Button variant="outline" size="sm" onClick={() => setSelectedLog(null)} className="text-xs">
                                Close Inspector
                            </Button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
