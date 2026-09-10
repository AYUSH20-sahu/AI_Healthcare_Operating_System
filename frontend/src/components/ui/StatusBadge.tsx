'use client';

import React from 'react';
import { Badge } from './Badge';

export type ClinicalStatus =
    | 'DRAFT'
    | 'FINALIZED'
    | 'AMENDED'
    | 'CANCELLED'
    | 'scheduled'
    | 'completed'
    | 'cancelled'
    | 'no_show';

export interface StatusBadgeProps {
    status: ClinicalStatus | string;
    showDot?: boolean;
    className?: string;
}

export function StatusBadge({ status, showDot = true, className = '' }: StatusBadgeProps) {
    const normalized = (status || '').toUpperCase();

    switch (normalized) {
        case 'DRAFT':
            return (
                <Badge variant="warning" dot={showDot} className={className}>
                    AI Draft • Review Req.
                </Badge>
            );
        case 'FINALIZED':
        case 'COMPLETED':
            return (
                <Badge variant="success" dot={showDot} className={className}>
                    Finalized
                </Badge>
            );
        case 'AMENDED':
            return (
                <Badge variant="info" dot={showDot} className={className}>
                    Amended
                </Badge>
            );
        case 'CANCELLED':
            return (
                <Badge variant="danger" dot={showDot} className={className}>
                    Cancelled
                </Badge>
            );
        case 'SCHEDULED':
            return (
                <Badge variant="primary" dot={showDot} className={className}>
                    Scheduled
                </Badge>
            );
        case 'NO_SHOW':
            return (
                <Badge variant="default" dot={showDot} className={className}>
                    No Show
                </Badge>
            );
        default:
            return (
                <Badge variant="default" dot={showDot} className={className}>
                    {status}
                </Badge>
            );
    }
}
