'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface QueueStreamPayload {
    event: 'QUEUE_STATUS_UPDATED' | 'CONNECTED';
    organization_id?: string;
    appointment_id?: string;
    patient_name?: string;
    doctor_name?: string;
    old_status?: string;
    new_status?: string;
    scheduled_at?: string;
}

interface UseQueueStreamOptions {
    organizationId?: string;
    enabled?: boolean;
    onQueueUpdated?: (payload: QueueStreamPayload) => void;
}

export function useQueueStream({
    organizationId = 'default',
    enabled = true,
    onQueueUpdated,
}: UseQueueStreamOptions) {
    const [isConnected, setIsConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<QueueStreamPayload | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectAttemptsRef = useRef(0);

    const onQueueUpdatedRef = useRef(onQueueUpdated);
    onQueueUpdatedRef.current = onQueueUpdated;

    const connect = useCallback(() => {
        if (!enabled || typeof window === 'undefined') return;

        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        const token = localStorage.getItem('access_token') || '';
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

        const wsBase = apiUrl
            .replace(/^http:\/\//, 'ws://')
            .replace(/^https:\/\//, 'wss://')
            .replace(/\/$/, '');

        const targetOrg = encodeURIComponent(organizationId.trim() || 'default');
        const wsUrl = `${wsBase}/ws/queue/${targetOrg}?token=${encodeURIComponent(token)}`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttemptsRef.current = 0;

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
                    const data: QueueStreamPayload = JSON.parse(event.data);
                    setLastEvent(data);

                    if (data.event === 'QUEUE_STATUS_UPDATED' && onQueueUpdatedRef.current) {
                        onQueueUpdatedRef.current(data);
                    }
                } catch {
                    // Ignore non-json
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);

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
    }, [organizationId, enabled]);

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
