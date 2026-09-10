'use client';

import React, { createContext, useContext, useState } from 'react';

interface TabsContextType {
    activeTab: string;
    setActiveTab: (tab: string) => void;
}

const TabsContext = createContext<TabsContextType | undefined>(undefined);

export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
    defaultValue: string;
    value?: string;
    onValueChange?: (value: string) => void;
}

export function Tabs({
    defaultValue,
    value,
    onValueChange,
    children,
    className = '',
    ...props
}: TabsProps) {
    const [selectedTab, setSelectedTab] = useState(defaultValue);

    const activeTab = value !== undefined ? value : selectedTab;
    const setActiveTab = (tab: string) => {
        if (value === undefined) setSelectedTab(tab);
        onValueChange?.(tab);
    };

    return (
        <TabsContext.Provider value={{ activeTab, setActiveTab }}>
            <div className={`w-full ${className}`} {...props}>
                {children}
            </div>
        </TabsContext.Provider>
    );
}

export function TabList({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={`inline-flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900/90 rounded-xl border border-slate-200 dark:border-slate-800 ${className}`}
            role="tablist"
            {...props}
        >
            {children}
        </div>
    );
}

export interface TabTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    value: string;
    icon?: React.ReactNode;
}

export function TabTrigger({
    value,
    icon,
    children,
    className = '',
    ...props
}: TabTriggerProps) {
    const context = useContext(TabsContext);
    if (!context) throw new Error('TabTrigger must be used within Tabs');

    const isActive = context.activeTab === value;

    return (
        <button
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => context.setActiveTab(value)}
            className={`inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-lg transition-all duration-150 select-none ${
                isActive
                    ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200/60 dark:border-slate-700/60'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800/40'
            } ${className}`}
            {...props}
        >
            {icon && <span className="shrink-0">{icon}</span>}
            <span>{children}</span>
        </button>
    );
}

export interface TabContentProps extends React.HTMLAttributes<HTMLDivElement> {
    value: string;
}

export function TabContent({ value, children, className = '', ...props }: TabContentProps) {
    const context = useContext(TabsContext);
    if (!context) throw new Error('TabContent must be used within Tabs');

    if (context.activeTab !== value) return null;

    return (
        <div
            role="tabpanel"
            className={`mt-4 focus:outline-none animate-in fade-in-50 duration-150 ${className}`}
            {...props}
        >
            {children}
        </div>
    );
}
