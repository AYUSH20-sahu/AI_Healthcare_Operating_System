/**
 * System Health Checks, Resilience Mesh Telemetry, and Observability APIs.
 */

import { api } from './client';

export interface HealthStatusData {
    status: 'healthy' | 'degraded' | 'unhealthy';
    service: string;
    version: string;
    environment: string;
    timestamp: string;
    database: { status: string; latency_ms: number; details?: string };
    ai_provider_mesh: {
        status: string;
        primary_llm: string;
        fallback_llm: string;
        providers: Record<string, { configured: boolean; status: string }>;
        resilience_mesh_ready: boolean;
    };
    cache: { status: string; type: string; details?: string };
}

export interface TelemetryMetricsData {
    uptime_seconds: number;
    system_timestamp: string;
    service: string;
    environment: string;
    latency_percentiles?: {
        non_ai_endpoints?: {
            p50: number;
            p95: number;
            p99: number;
            avg?: number;
            samples?: number;
            min?: number;
            max?: number;
        };
        ai_turn_completion?: {
            p50: number;
            p95: number;
            p99: number;
            avg?: number;
            samples?: number;
            min?: number;
            max?: number;
        };
        [key: string]: any;
    };
    http_requests: {
        total: number;
        status_counts: Record<string, number>;
        error_rate_percent: number;
    };
    latency_metrics: {
        non_ai_api: {
            p50: number;
            p95: number;
            p99: number;
            min: number;
            max: number;
            avg: number;
            samples: number;
            target_p95_ms: number;
            target_met: boolean;
        };
        ai_conversational_turn: {
            p50: number;
            p95: number;
            p99: number;
            min: number;
            max: number;
            avg: number;
            samples: number;
            target_p95_ms: number;
            target_met: boolean;
        };
        stt_voice_intake: Record<string, number>;
        tts_speech_synthesis: Record<string, number>;
    };
    ai_call_metrics: {
        total_ai_calls: number;
        fallback_count: number;
        fallback_rate_percent: number;
        provider_distribution: Record<string, number>;
        token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
        provider_errors: Record<string, number>;
    };
    nfr_targets: {
        non_ai_api_p95_ms: number;
        ai_conversational_turn_p95_ms: number;
    };
}

export const observabilityApi = {
    getHealth: () => api.get<HealthStatusData>('/observability/health'),
    getMetrics: () => api.get<TelemetryMetricsData>('/observability/metrics'),
};
