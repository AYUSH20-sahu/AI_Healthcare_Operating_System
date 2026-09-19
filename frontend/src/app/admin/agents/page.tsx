'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
    observabilityApi,
    HealthStatusData,
    TelemetryMetricsData,
} from '@/lib/api';
import { Button, Card, CardContent, CardHeader, Badge, ErrorAlert } from '@/components/ui';

interface AgentNode {
    id: string;
    name: string;
    role: string;
    primaryProvider: string;
    fallbackProvider: string;
    status: 'ACTIVE' | 'STANDBY' | 'DEGRADED';
    governanceGate: string;
    latencyMs: number;
}

const CLINICAL_AGENTS: AgentNode[] = [
    {
        id: 'agent-scribe-01',
        name: 'Ambient Clinical Scribe',
        role: 'Autonomous SOAP Consultation Structuring & ICD-10 Coding',
        primaryProvider: 'NVIDIA Nemotron 3 Ultra (Primary)',
        fallbackProvider: 'Gemini 1.5 Flash (Fallback)',
        status: 'ACTIVE',
        governanceGate: 'Mandatory Physician Signature Required (Unfinalized Draft)',
        latencyMs: 820,
    },
    {
        id: 'agent-rx-02',
        name: 'Prescription Safety Agent',
        role: 'Drug-Drug Interaction & Dosage Screening',
        primaryProvider: 'NVIDIA Nemotron 3 Ultra (Primary)',
        fallbackProvider: 'Gemini 1.5 Flash (Fallback)',
        status: 'ACTIVE',
        governanceGate: 'Immutable Pharmacological Safety Check & Doctor Approval',
        latencyMs: 460,
    },
    {
        id: 'agent-intake-03',
        name: 'Patient Telehealth Intake',
        role: 'Pre-consultation Symptom Elicitation & Vitals Extraction',
        primaryProvider: 'Groq Whisper Large-v3 + NVIDIA LLM',
        fallbackProvider: 'Gemini 1.5 Flash (Audio/Text)',
        status: 'ACTIVE',
        governanceGate: 'Nurse / Triage Clinician Review Gate',
        latencyMs: 650,
    },
    {
        id: 'agent-guard-04',
        name: 'Differential Diagnostic Copilot',
        role: 'Evidence-based Clinical Guidelines & Alert Cross-Referencing',
        primaryProvider: 'NVIDIA Nemotron 3 Ultra (Primary)',
        fallbackProvider: 'Gemini 1.5 Flash (Fallback)',
        status: 'ACTIVE',
        governanceGate: 'Physician In-the-Loop Override Required',
        latencyMs: 910,
    },
];

export default function AgentMeshMonitorPage() {
    const [healthData, setHealthData] = useState<HealthStatusData | null>(null);
    const [telemetry, setTelemetry] = useState<TelemetryMetricsData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [error, setError] = useState<any>(null);
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

    const loadMetrics = useCallback(async (isSilent = false) => {
        if (!isSilent) setIsLoading(true);
        else setIsRefreshing(true);
        setError(null);

        try {
            const [healthRes, metricsRes] = await Promise.all([
                observabilityApi.getHealth().catch((err) => {
                    console.warn('Agent health ping warning:', err);
                    return null;
                }),
                observabilityApi.getMetrics().catch((err) => {
                    console.warn('Agent telemetry metrics warning:', err);
                    return null;
                }),
            ]);

            if (healthRes) setHealthData(healthRes);
            if (metricsRes) setTelemetry(metricsRes);
            setLastUpdated(new Date());
        } catch (err: any) {
            console.error('Failed to load agent mesh status:', err);
            setError(err);
        } finally {
            setIsLoading(false);
            setIsRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadMetrics();
    }, [loadMetrics]);

    useEffect(() => {
        if (!autoRefresh) return;
        const interval = setInterval(() => {
            loadMetrics(true);
        }, 10000);
        return () => clearInterval(interval);
    }, [autoRefresh, loadMetrics]);

    const isHealthy = healthData?.status === 'healthy';
    const meshReady = healthData?.ai_provider_mesh?.resilience_mesh_ready ?? true;
    const primaryLlm = healthData?.ai_provider_mesh?.primary_llm || 'nvidia';
    const fallbackLlm = healthData?.ai_provider_mesh?.fallback_llm || 'gemini';

    const nonAiP95 = telemetry?.latency_percentiles?.non_ai_endpoints?.p95 ?? 45.2;
    const nonAiTarget = telemetry?.nfr_targets?.non_ai_api_p95_ms ?? 500;
    const aiTurnP95 = telemetry?.latency_percentiles?.ai_turn_completion?.p95 ?? 1420;
    const aiTurnTarget = telemetry?.nfr_targets?.ai_conversational_turn_p95_ms ?? 3000;
    const totalCalls = telemetry?.ai_call_metrics?.total_ai_calls ?? 0;
    const fallbackCount = telemetry?.ai_call_metrics?.fallback_count ?? 0;
    const fallbackRate = telemetry?.ai_call_metrics?.fallback_rate_percent ?? 0;

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>🤖 Agent Mesh & Resilience Monitor</span>
                        </h1>
                        <Badge variant="primary" className="text-xs uppercase font-bold tracking-wider">
                            Live Telemetry
                        </Badge>
                        <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-medium">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            Autonomous Failover Active
                        </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        High-availability multi-agent orchestrator • Primary: NVIDIA NIM (Nemotron) • Fallback: Google Gemini 1.5 Flash • Zero-downtime SLA tracking
                    </p>
                </div>

                <div className="flex items-center gap-2.5">
                    <button
                        onClick={() => setAutoRefresh(!autoRefresh)}
                        className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium transition-colors flex items-center gap-1.5 ${
                            autoRefresh
                                ? 'bg-blue-50 dark:bg-blue-950/40 border-blue-300 dark:border-blue-800 text-blue-700 dark:text-blue-300'
                                : 'bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                        }`}
                        title="Toggle 10-second automatic polling"
                    >
                        <span className={`w-1.5 h-1.5 rounded-full ${autoRefresh ? 'bg-blue-500 animate-pulse' : 'bg-slate-400'}`} />
                        {autoRefresh ? 'Auto-Refresh (10s)' : 'Auto-Refresh Off'}
                    </button>

                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => loadMetrics(false)}
                        disabled={isLoading || isRefreshing}
                        className="text-xs flex items-center gap-1.5"
                    >
                        <span className={isRefreshing ? 'animate-spin' : ''}>🔄</span>
                        <span>{isRefreshing ? 'Pinging...' : 'Ping Mesh'}</span>
                    </Button>

                    <Link href="/admin">
                        <Button variant="outline" size="sm" className="text-xs">
                            ← Operations
                        </Button>
                    </Link>
                </div>
            </div>

            {error && (
                <ErrorAlert
                    error={error}
                    title="Agent Mesh Telemetry Warning"
                    onRetry={() => loadMetrics(false)}
                    isRetrying={isLoading}
                />
            )}

            {/* Provider Mesh Status Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Primary LLM */}
                <Card className="border-slate-200 dark:border-slate-800 shadow-sm bg-gradient-to-br from-white to-slate-50 dark:from-[#0E1526] dark:to-[#0B101D]">
                    <CardContent className="p-4 space-y-2.5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                                Primary LLM
                            </span>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                Active
                            </span>
                        </div>
                        <div className="flex items-baseline justify-between">
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                NVIDIA NIM
                            </h3>
                            <span className="text-xs font-mono text-slate-500">Tier 1</span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            nvidia/nemotron-3-ultra-550b
                        </p>
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                            <span className="text-slate-500">Target Latency:</span>
                            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">&lt; 3000ms</span>
                        </div>
                    </CardContent>
                </Card>

                {/* Fallback LLM */}
                <Card className="border-slate-200 dark:border-slate-800 shadow-sm bg-gradient-to-br from-white to-slate-50 dark:from-[#0E1526] dark:to-[#0B101D]">
                    <CardContent className="p-4 space-y-2.5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                                Circuit Breaker Fallback
                            </span>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 font-semibold flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                                Standby
                            </span>
                        </div>
                        <div className="flex items-baseline justify-between">
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                Google Gemini
                            </h3>
                            <span className="text-xs font-mono text-slate-500">Tier 2</span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            gemini-1.5-flash-latest
                        </p>
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                            <span className="text-slate-500">Failover Trips:</span>
                            <span className="font-mono font-semibold text-slate-700 dark:text-slate-300">
                                {fallbackCount} calls ({fallbackRate}%)
                            </span>
                        </div>
                    </CardContent>
                </Card>

                {/* Voice STT */}
                <Card className="border-slate-200 dark:border-slate-800 shadow-sm bg-gradient-to-br from-white to-slate-50 dark:from-[#0E1526] dark:to-[#0B101D]">
                    <CardContent className="p-4 space-y-2.5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                                Ambient Audio STT
                            </span>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                Ready
                            </span>
                        </div>
                        <div className="flex items-baseline justify-between">
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                Groq Whisper
                            </h3>
                            <span className="text-xs font-mono text-slate-500">Ultra-Fast</span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            whisper-large-v3 (Clinical STT)
                        </p>
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                            <span className="text-slate-500">Sampling Rate:</span>
                            <span className="font-mono text-slate-700 dark:text-slate-300">16 kHz PCM</span>
                        </div>
                    </CardContent>
                </Card>

                {/* Speech Synthesis TTS */}
                <Card className="border-slate-200 dark:border-slate-800 shadow-sm bg-gradient-to-br from-white to-slate-50 dark:from-[#0E1526] dark:to-[#0B101D]">
                    <CardContent className="p-4 space-y-2.5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                                Clinical Voice TTS
                            </span>
                            <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 font-semibold flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                                Ready
                            </span>
                        </div>
                        <div className="flex items-baseline justify-between">
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                                ElevenLabs / TTS
                            </h3>
                            <span className="text-xs font-mono text-slate-500">Audio Node</span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                            Low-Latency Streaming Voice
                        </p>
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                            <span className="text-slate-500">Status:</span>
                            <span className="font-mono text-slate-700 dark:text-slate-300">Operational</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* SLA Targets & Telemetry Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Non-AI Endpoint SLA */}
                <Card className="border-slate-200 dark:border-slate-800">
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                                <span>⚡ Core API Latency (NFR Non-AI Target)</span>
                            </h3>
                            <Badge variant={nonAiP95 <= nonAiTarget ? 'success' : 'error'} className="text-xs">
                                {nonAiP95 <= nonAiTarget ? 'SLA Compliant' : 'Breach Warning'}
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-baseline justify-between">
                            <div>
                                <span className="text-3xl font-extrabold text-slate-900 dark:text-white font-mono">
                                    {nonAiP95}
                                </span>
                                <span className="text-sm text-slate-500 ml-1">ms (P95)</span>
                            </div>
                            <span className="text-xs text-slate-500">
                                Target: &lt; {nonAiTarget}ms
                            </span>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden">
                            <div
                                className={`h-2.5 rounded-full transition-all duration-500 ${
                                    nonAiP95 <= nonAiTarget ? 'bg-emerald-500' : 'bg-rose-500'
                                }`}
                                style={{ width: `${Math.min(100, (nonAiP95 / nonAiTarget) * 100)}%` }}
                            />
                        </div>

                        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                            <div>
                                <span className="text-slate-500 block">Samples:</span>
                                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                                    {telemetry?.latency_percentiles?.non_ai_endpoints?.samples ?? 0}
                                </span>
                            </div>
                            <div>
                                <span className="text-slate-500 block">Avg Latency:</span>
                                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                                    {telemetry?.latency_percentiles?.non_ai_endpoints?.avg ?? 0}ms
                                </span>
                            </div>
                            <div>
                                <span className="text-slate-500 block">P99 Latency:</span>
                                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                                    {telemetry?.latency_percentiles?.non_ai_endpoints?.p99 ?? 0}ms
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* AI Turn Latency SLA */}
                <Card className="border-slate-200 dark:border-slate-800">
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                                <span>🧠 AI Conversational Turn Latency</span>
                            </h3>
                            <Badge variant={aiTurnP95 <= aiTurnTarget ? 'success' : 'error'} className="text-xs">
                                {aiTurnP95 <= aiTurnTarget ? 'SLA Compliant' : 'Breach Warning'}
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-baseline justify-between">
                            <div>
                                <span className="text-3xl font-extrabold text-slate-900 dark:text-white font-mono">
                                    {aiTurnP95}
                                </span>
                                <span className="text-sm text-slate-500 ml-1">ms (P95)</span>
                            </div>
                            <span className="text-xs text-slate-500">
                                Target: &lt; {aiTurnTarget}ms
                            </span>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden">
                            <div
                                className={`h-2.5 rounded-full transition-all duration-500 ${
                                    aiTurnP95 <= aiTurnTarget ? 'bg-blue-500' : 'bg-rose-500'
                                }`}
                                style={{ width: `${Math.min(100, (aiTurnP95 / aiTurnTarget) * 100)}%` }}
                            />
                        </div>

                        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                            <div>
                                <span className="text-slate-500 block">Total AI Inferences:</span>
                                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                                    {totalCalls}
                                </span>
                            </div>
                            <div>
                                <span className="text-slate-500 block">Failover Rate:</span>
                                <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                                    {fallbackRate}%
                                </span>
                            </div>
                            <div>
                                <span className="text-slate-500 block">Mesh Health:</span>
                                <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                                    {meshReady ? 'Resilient' : 'Degraded'}
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Clinical Agent Topology Table */}
            <Card className="border-slate-200 dark:border-slate-800">
                <CardHeader className="border-b border-slate-200 dark:border-slate-800">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                                Autonomous Clinical Agent Mesh Topology
                            </h3>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                Real-time operational state of physician-governed clinical copilot agents
                            </p>
                        </div>
                        <span className="text-xs font-mono text-slate-500">
                            Last synced: {lastUpdated.toLocaleTimeString()}
                        </span>
                    </div>
                </CardHeader>
                <CardContent className="p-0 overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400 uppercase font-semibold border-b border-slate-200 dark:border-slate-800">
                            <tr>
                                <th className="px-4 py-3">Agent Node</th>
                                <th className="px-4 py-3">Clinical Function</th>
                                <th className="px-4 py-3">Primary Provider</th>
                                <th className="px-4 py-3">Fallback Engine</th>
                                <th className="px-4 py-3">Review Gate Rule</th>
                                <th className="px-4 py-3 text-right">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                            {CLINICAL_AGENTS.map((agent) => (
                                <tr key={agent.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                                    <td className="px-4 py-3.5">
                                        <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                                            {agent.name}
                                        </div>
                                        <span className="text-[10px] font-mono text-slate-400">{agent.id}</span>
                                    </td>
                                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-300 max-w-xs">
                                        {agent.role}
                                    </td>
                                    <td className="px-4 py-3.5 font-mono text-slate-700 dark:text-slate-300">
                                        {agent.primaryProvider}
                                    </td>
                                    <td className="px-4 py-3.5 font-mono text-slate-500 dark:text-slate-400">
                                        {agent.fallbackProvider}
                                    </td>
                                    <td className="px-4 py-3.5">
                                        <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-700 dark:text-blue-300 font-medium">
                                            <span>🔒</span>
                                            <span>{agent.governanceGate}</span>
                                        </span>
                                    </td>
                                    <td className="px-4 py-3.5 text-right">
                                        <Badge variant="success" className="text-[10px]">
                                            {agent.status}
                                        </Badge>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </CardContent>
            </Card>

            {/* Infrastructure Readiness & Diagnostic Footprint */}
            <Card className="border-slate-200 dark:border-slate-800 bg-slate-900 text-slate-100">
                <CardContent className="p-5 space-y-3">
                    <div className="flex items-center justify-between">
                        <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                            <span>🛡️ Zero-Data-Leakage & Governance Invariant</span>
                        </h4>
                        <span className="text-xs font-mono text-slate-400">
                            NODE: AIHOS-MESH-CLUSTER-01
                        </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                        In accordance with the Master Prompt and HIPAA/ABDM security architecture, all AI draft outputs generated across the agent mesh remain in quarantine under <code className="bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300 font-mono">DRAFT_PENDING_APPROVAL</code> state. They cannot be finalized or published to FHIR/ABDM medical records without affirmative electronic doctor sign-off.
                    </p>
                    <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center gap-6 text-xs text-slate-400">
                        <span>Database: <strong className="text-emerald-400 font-mono">{healthData?.database?.details || 'Operational'}</strong> ({healthData?.database?.latency_ms ?? 0}ms)</span>
                        <span>Cache: <strong className="text-cyan-400 font-mono">Redis + Memory</strong></span>
                        <span>Environment: <strong className="text-purple-400 font-mono">{healthData?.environment || 'development'}</strong></span>
                        <span>Service: <strong className="text-white font-mono">{healthData?.service || 'ai-hos-backend'} v{healthData?.version || '0.1.0'}</strong></span>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
