'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface TelemetryVitalsPayload {
    event: 'VITALS_UPDATED' | 'MEDICATION_ADMINISTERED' | 'TASK_UPDATED' | 'CONNECTED';
    ward?: string;
    bed_id?: string;
    bed_number?: string;
    patient_name?: string;
    bp?: string;
    systolic?: number;
    diastolic?: number;
    pulse?: number;
    spo2?: number;
    temp?: number;
    respiratory_rate?: number;
    pain_score?: number;
    clinical_status?: string;
    is_critical?: boolean;
    recorded_by?: string;
    vitals_last_checked?: string;
    medication?: string;
    medication_due?: string;
    task_id?: string;
    status?: string;
}

interface UseWardTelemetryOptions {
    ward: string;
    enabled?: boolean;
    onVitalsUpdated?: (payload: TelemetryVitalsPayload) => void;
    onMedicationAdministered?: (payload: TelemetryVitalsPayload) => void;
    onTaskUpdated?: (payload: TelemetryVitalsPayload) => void;
}

export function useWardTelemetry({
    ward,
    enabled = true,
    onVitalsUpdated,
    onMedicationAdministered,
    onTaskUpdated,
}: UseWardTelemetryOptions) {
    const [isConnected, setIsConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<TelemetryVitalsPayload | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttemptsRef = useRef(0);

    const onVitalsUpdatedRef = useRef(onVitalsUpdated);
    onVitalsUpdatedRef.current = onVitalsUpdated;

    const onMedicationAdministeredRef = useRef(onMedicationAdministered);
    onMedicationAdministeredRef.current = onMedicationAdministered;

    const onTaskUpdatedRef = useRef(onTaskUpdated);
    onTaskUpdatedRef.current = onTaskUpdated;

    const connect = useCallback(() => {
        if (!enabled || !ward || typeof window === 'undefined') return;

        // Clean up previous socket if open
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        const token = localStorage.getItem('access_token') || '';
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

        // Convert HTTP(S) url to WS(S)
        const wsBase = apiUrl
            .replace(/^http:\/\//, 'ws://')
            .replace(/^https:\/\//, 'wss://')
            .replace(/\/$/, '');

        const targetWard = encodeURIComponent(ward.trim());
        const wsUrl = `${wsBase}/ws/telemetry/ward/${targetWard}?token=${encodeURIComponent(token)}`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttemptsRef.current = 0;

                // Setup 25-second heartbeat ping
                if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
                heartbeatIntervalRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send('ping');
                    }
                }, 25000);
            };

            ws.onmessage = (event) => {
                if (event.data === 'pong') return;

                try {
                    const data: TelemetryVitalsPayload = JSON.parse(event.data);
                    setLastEvent(data);

                    if (data.event === 'VITALS_UPDATED' && onVitalsUpdatedRef.current) {
                        onVitalsUpdatedRef.current(data);
                    } else if (data.event === 'MEDICATION_ADMINISTERED' && onMedicationAdministeredRef.current) {
                        onMedicationAdministeredRef.current(data);
                    } else if (data.event === 'TASK_UPDATED' && onTaskUpdatedRef.current) {
                        onTaskUpdatedRef.current(data);
                    }
                } catch {
                    // Non-JSON message ignore
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);

                // Auto-reconnect with exponential backoff (max 15s)
                if (enabled) {
                    const delay = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 15000);
                    reconnectAttemptsRef.current += 1;
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, delay);
                }
            };

            ws.onerror = () => {
                ws.close();
            };
        } catch {
            setIsConnected(false);
        }
    }, [ward, enabled]);

    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
            if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [connect]);

    return {
        isConnected,
        lastEvent,
        reconnect: connect,
    };
}
