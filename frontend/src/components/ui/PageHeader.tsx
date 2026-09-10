'use client';

import React from 'react';

export interface BreadcrumbItem {
    label: string;
    href?: string;
    active?: boolean;
}

export interface BreadcrumbProps {
    items: BreadcrumbItem[];
    className?: string;
}

export function Breadcrumb({ items, className = '' }: BreadcrumbProps) {
    return (
        <nav aria-label="Breadcrumb" className={`flex items-center text-xs text-slate-500 dark:text-slate-400 ${className}`}>
            <ol className="flex items-center gap-1.5 flex-wrap">
                {items.map((item, index) => {
                    const isLast = index === items.length - 1 || item.active;

                    return (
                        <li key={index} className="flex items-center gap-1.5">
                            {index > 0 && (
                                <svg
                                    className="w-3.5 h-3.5 text-slate-400 dark:text-slate-600 shrink-0"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M9 5l7 7-7 7"
                                    />
                                </svg>
                            )}
                            {item.href && !isLast ? (
                                <a
                                    href={item.href}
                                    className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                >
                                    {item.label}
                                </a>
                            ) : (
                                <span className={isLast ? 'font-medium text-slate-900 dark:text-slate-100' : ''}>
                                    {item.label}
                                </span>
                            )}
                        </li>
                    );
                })}
            </ol>
        </nav>
    );
}

export interface PageHeaderProps {
    title: React.ReactNode;
    subtitle?: React.ReactNode;
    breadcrumbs?: BreadcrumbItem[];
    actions?: React.ReactNode;
    badge?: React.ReactNode;
    className?: string;
}

export function PageHeader({
    title,
    subtitle,
    breadcrumbs,
    actions,
    badge,
    className = '',
}: PageHeaderProps) {
    return (
        <div className={`space-y-2 pb-6 border-b border-slate-200/80 dark:border-slate-800 ${className}`}>
            {breadcrumbs && <Breadcrumb items={breadcrumbs} className="mb-2" />}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                            {title}
                        </h1>
                        {badge}
                    </div>
                    {subtitle && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-2xl leading-relaxed">
                            {subtitle}
                        </p>
                    )}
                </div>
                {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
            </div>
        </div>
    );
}
