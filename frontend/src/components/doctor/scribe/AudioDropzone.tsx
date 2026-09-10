'use client';

import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/Button';

interface AudioDropzoneProps {
    onFileSelected: (file: File) => void;
    isUploading?: boolean;
    className?: string;
}

export function AudioDropzone({
    onFileSelected,
    isUploading = false,
    className = '',
}: AudioDropzoneProps) {
    const [dragActive, setDragActive] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [audioUrl, setAudioUrl] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement | null>(null);

    const ALLOWED_TYPES = ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg', 'audio/m4a', 'audio/x-m4a'];

    const handleFile = (file: File) => {
        setErrorMessage(null);

        // Validate type
        const extension = file.name.split('.').pop()?.toLowerCase();
        const validExtensions = ['webm', 'wav', 'mp3', 'm4a', 'ogg'];
        if (!validExtensions.includes(extension || '')) {
            setErrorMessage(`Unsupported format .${extension}. Please use .wav, .mp3, .m4a, or .webm`);
            return;
        }

        // Validate size (50MB)
        if (file.size > 50 * 1024 * 1024) {
            setErrorMessage('File size exceeds 50MB limit.');
            return;
        }

        setSelectedFile(file);
        const url = URL.createObjectURL(file);
        setAudioUrl(url);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    return (
        <div className={`rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 shadow-sm p-5 backdrop-blur-md ${className}`}>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
                Upload Pre-Recorded Consultation
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                Transcribe dictation audio from dictaphones, mobile recorders, or tele-health calls (.wav, .mp3, .m4a, .webm).
            </p>

            <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                    dragActive
                        ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/30'
                        : 'border-slate-300 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-600 bg-slate-50/50 dark:bg-slate-800/30'
                }`}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept="audio/*,.webm,.wav,.mp3,.m4a,.ogg"
                    className="hidden"
                    onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                            handleFile(e.target.files[0]);
                        }
                    }}
                />

                <div className="w-12 h-12 rounded-2xl bg-blue-100 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xl mx-auto mb-2 font-bold shadow-sm">
                    📁
                </div>

                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                    Click to select audio or drag & drop here
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    Maximum file size: 50MB
                </p>
            </div>

            {errorMessage && (
                <div className="mt-3 p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/40 text-rose-700 dark:text-rose-300 text-xs">
                    {errorMessage}
                </div>
            )}

            {selectedFile && (
                <div className="mt-4 p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                            <span className="text-base">🎵</span>
                            <div>
                                <p className="font-semibold text-slate-900 dark:text-white truncate max-w-xs">
                                    {selectedFile.name}
                                </p>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                                </p>
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={(e) => {
                                e.stopPropagation();
                                setSelectedFile(null);
                                setAudioUrl(null);
                            }}
                            className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                            ✕ Remove
                        </button>
                    </div>

                    {audioUrl && (
                        <audio controls src={audioUrl} className="w-full h-8" />
                    )}

                    <div className="flex justify-end pt-1">
                        <Button
                            size="sm"
                            variant="primary"
                            isLoading={isUploading}
                            onClick={() => onFileSelected(selectedFile)}
                        >
                            Upload & Transcribe with Whisper
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
