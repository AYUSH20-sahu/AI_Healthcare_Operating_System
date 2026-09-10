'use client';

import React, { useState, useMemo } from 'react';
import { Input } from '@/components/ui/Input';

export interface TranscriptUtterance {
    id: string;
    speaker: 'doctor' | 'patient' | 'system';
    timestamp: string; // e.g. "00:15"
    text: string;
    entities?: {
        text: string;
        category: 'symptom' | 'medication' | 'allergy' | 'diagnosis';
    }[];
}

interface DiarizedTranscriptProps {
    utterances: TranscriptUtterance[];
    onUpdateUtterance?: (id: string, newText: string) => void;
    isLiveStreaming?: boolean;
    className?: string;
}

export function DiarizedTranscript({
    utterances,
    onUpdateUtterance,
    isLiveStreaming = false,
    className = '',
}: DiarizedTranscriptProps) {
    const [speakerFilter, setSpeakerFilter] = useState<'all' | 'doctor' | 'patient'>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editText, setEditText] = useState('');

    const filtered = useMemo(() => {
        return utterances.filter((item) => {
            const matchesSpeaker = speakerFilter === 'all' || item.speaker === speakerFilter;
            const q = searchQuery.toLowerCase().trim();
            const matchesSearch = !q || item.text.toLowerCase().includes(q);
            return matchesSpeaker && matchesSearch;
        });
    }, [utterances, speakerFilter, searchQuery]);

    const handleStartEdit = (u: TranscriptUtterance) => {
        setEditingId(u.id);
        setEditText(u.text);
    };

    const handleSaveEdit = (id: string) => {
        if (onUpdateUtterance && editText.trim()) {
            onUpdateUtterance(id, editText);
        }
        setEditingId(null);
    };

    const highlightEntities = (text: string, entities?: TranscriptUtterance['entities']) => {
        if (!entities || entities.length === 0) return text;

        // Render entities with colored badges
        return (
            <span>
                {text}
                <span className="block mt-1.5 flex flex-wrap gap-1">
                    {entities.map((ent, idx) => {
                        let colorClass = 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300';
                        if (ent.category === 'medication') {
                            colorClass = 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300';
                        } else if (ent.category === 'allergy') {
                            colorClass = 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300';
                        } else if (ent.category === 'diagnosis') {
                            colorClass = 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300';
                        }
                        return (
                            <span key={idx} className={`px-1.5 py-0.2 rounded text-[10px] font-semibold uppercase tracking-wider ${colorClass}`}>
                                {ent.category}: {ent.text}
                            </span>
                        );
                    })}
                </span>
            </span>
        );
    };

    return (
        <div className={`rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 shadow-sm overflow-hidden flex flex-col ${className}`}>
            {/* Header with Search & Filter */}
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-slate-900 dark:text-white">
                        Diarized Consultation Dialogue
                    </span>
                    {isLiveStreaming && (
                        <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 text-[10px] font-bold uppercase tracking-wider">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                            Live Stream
                        </span>
                    )}
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                    {/* Speaker Filter Tabs */}
                    <div className="flex items-center rounded-xl bg-slate-100 dark:bg-slate-800 p-0.5 text-xs">
                        <button
                            type="button"
                            onClick={() => setSpeakerFilter('all')}
                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                speakerFilter === 'all'
                                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                                    : 'text-slate-600 dark:text-slate-400'
                            }`}
                        >
                            All
                        </button>
                        <button
                            type="button"
                            onClick={() => setSpeakerFilter('doctor')}
                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                speakerFilter === 'doctor'
                                    ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm'
                                    : 'text-slate-600 dark:text-slate-400'
                            }`}
                        >
                            Doctor
                        </button>
                        <button
                            type="button"
                            onClick={() => setSpeakerFilter('patient')}
                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                speakerFilter === 'patient'
                                    ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                                    : 'text-slate-600 dark:text-slate-400'
                            }`}
                        >
                            Patient
                        </button>
                    </div>

                    <div className="w-44">
                        <Input
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Filter dialogue..."
                            className="py-1 text-xs"
                        />
                    </div>
                </div>
            </div>

            {/* Conversation Timeline Stream */}
            <div className="p-4 space-y-4 max-h-[460px] overflow-y-auto">
                {filtered.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 dark:text-slate-400 text-xs">
                        No speech dialogue recorded yet. Start recording or upload a consultation file.
                    </div>
                ) : (
                    filtered.map((u) => {
                        const isDoctor = u.speaker === 'doctor';
                        const isEditing = editingId === u.id;

                        return (
                            <div
                                key={u.id}
                                className={`flex gap-3 text-xs ${
                                    isDoctor ? 'justify-start' : 'justify-start flex-row-reverse sm:flex-row'
                                }`}
                            >
                                {/* Speaker Avatar */}
                                <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center font-bold text-xs shadow-sm ${
                                    isDoctor
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-indigo-600 text-white'
                                }`}>
                                    {isDoctor ? '👨‍⚕️' : '🧑'}
                                </div>

                                {/* Bubble Content */}
                                <div className="space-y-1 max-w-[85%] sm:max-w-[80%]">
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold text-slate-800 dark:text-slate-200">
                                            {isDoctor ? 'Doctor (Attending)' : 'Patient'}
                                        </span>
                                        <span className="font-mono text-[10px] text-slate-400">
                                            {u.timestamp}
                                        </span>
                                        {!isEditing && (
                                            <button
                                                type="button"
                                                onClick={() => handleStartEdit(u)}
                                                className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                            >
                                                ✎
                                            </button>
                                        )}
                                    </div>

                                    {isEditing ? (
                                        <div className="space-y-2 p-2 rounded-xl bg-slate-100 dark:bg-slate-800">
                                            <textarea
                                                rows={2}
                                                value={editText}
                                                onChange={(e) => setEditText(e.target.value)}
                                                className="w-full p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs"
                                            />
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => setEditingId(null)}
                                                    className="px-2 py-1 text-[11px] rounded bg-slate-200 dark:bg-slate-700"
                                                >
                                                    Cancel
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => handleSaveEdit(u.id)}
                                                    className="px-2 py-1 text-[11px] rounded bg-blue-600 text-white"
                                                >
                                                    Save
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className={`p-3 rounded-2xl leading-relaxed shadow-sm ${
                                            isDoctor
                                                ? 'bg-blue-50/80 dark:bg-blue-950/40 text-blue-950 dark:text-blue-100 border border-blue-200/60 dark:border-blue-800/40 rounded-tl-sm'
                                                : 'bg-slate-100 dark:bg-slate-800/80 text-slate-900 dark:text-slate-100 border border-slate-200/80 dark:border-slate-700/60 rounded-tr-sm'
                                        }`}>
                                            {highlightEntities(u.text, u.entities)}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
