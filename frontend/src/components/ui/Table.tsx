'use client';

import React from 'react';

export function Table({
    children,
    className = '',
    ...props
}: React.TableHTMLAttributes<HTMLTableElement>) {
    return (
        <div className="w-full overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
            <table className={`w-full text-left text-sm text-slate-700 dark:text-slate-300 ${className}`} {...props}>
                {children}
            </table>
        </div>
    );
}

export function TableHeader({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
    return (
        <thead
            className={`bg-slate-50/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold ${className}`}
            {...props}
        >
            {children}
        </thead>
    );
}

export function TableBody({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) {
    return (
        <tbody className={`divide-y divide-slate-100 dark:divide-slate-800/80 ${className}`} {...props}>
            {children}
        </tbody>
    );
}

export function TableRow({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLTableRowElement>) {
    return (
        <tr
            className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors ${className}`}
            {...props}
        >
            {children}
        </tr>
    );
}

export function TableHead({
    children,
    className = '',
    ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) {
    return (
        <th className={`px-4 py-3.5 ${className}`} {...props}>
            {children}
        </th>
    );
}

export function TableCell({
    children,
    className = '',
    ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
    return (
        <td className={`px-4 py-3.5 align-middle ${className}`} {...props}>
            {children}
        </td>
    );
}
