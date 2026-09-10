'use client';

import React, { useEffect, useRef, useState } from 'react';

export type RecordingState = 'idle' | 'recording' | 'paused' | 'processing' | 'review';

interface AudioWaveformProps {
    state: RecordingState;
    stream: MediaStream | null;
    durationSeconds: number;
    className?: string;
}

export function AudioWaveform({
    state,
    stream,
    durationSeconds,
    className = '',
}: AudioWaveformProps) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
    const animationFrameRef = useRef<number | null>(null);
    const [decibels, setDecibels] = useState<number>(-60);

    // Format timer MM:SS
    const formatTime = (secs: number) => {
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Set high resolution for retina displays
        const dpr = window.devicePixelRatio || 1;
        const width = canvas.parentElement?.clientWidth || 600;
        const height = 110;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);

        const BAR_COUNT = 48;
        const BAR_WIDTH = Math.max(3, (width - BAR_COUNT * 4) / BAR_COUNT);
        const BAR_GAP = 4;

        // Setup Web Audio API if stream is provided
        if (state === 'recording' && stream) {
            try {
                if (!audioContextRef.current) {
                    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
                    audioContextRef.current = new AudioCtx();
                }
                const audioCtx = audioContextRef.current;
                if (audioCtx.state === 'suspended') {
                    audioCtx.resume();
                }

                if (!analyserRef.current) {
                    const analyser = audioCtx.createAnalyser();
                    analyser.fftSize = 128;
                    analyser.smoothingTimeConstant = 0.8;
                    analyserRef.current = analyser;
                }

                if (!sourceRef.current) {
                    sourceRef.current = audioCtx.createMediaStreamSource(stream);
                    sourceRef.current.connect(analyserRef.current);
                }
            } catch (err) {
                console.warn('AudioContext initialization fallback:', err);
            }
        }

        let phase = 0;

        const draw = () => {
            ctx.clearRect(0, 0, width, height);

            const centerY = height / 2;

            if (state === 'recording') {
                let frequencyData: Uint8Array | null = null;
                if (analyserRef.current) {
                    const buffer = new ArrayBuffer(analyserRef.current.frequencyBinCount);
                    frequencyData = new Uint8Array(buffer);
                    analyserRef.current.getByteFrequencyData(frequencyData as any);

                    // Compute approximate dB level
                    let sum = 0;
                    for (let i = 0; i < frequencyData.length; i++) {
                        sum += frequencyData[i];
                    }
                    const avg = sum / frequencyData.length;
                    const db = Math.round(-60 + (avg / 255) * 54);
                    setDecibels(db);
                }

                phase += 0.05;

                for (let i = 0; i < BAR_COUNT; i++) {
                    const x = i * (BAR_WIDTH + BAR_GAP) + (width - BAR_COUNT * (BAR_WIDTH + BAR_GAP)) / 2;
                    let barHeight = 6;

                    if (frequencyData && frequencyData.length > 0) {
                        const freqIdx = Math.floor((i / BAR_COUNT) * (frequencyData.length * 0.7));
                        const val = frequencyData[freqIdx] / 255;
                        barHeight = Math.max(6, val * (height * 0.85));
                    } else {
                        // Simulated active wave movement
                        const wave = Math.sin(phase + i * 0.3) * 0.5 + 0.5;
                        const wave2 = Math.cos(phase * 1.5 + i * 0.15) * 0.5 + 0.5;
                        barHeight = Math.max(6, (wave * 0.6 + wave2 * 0.4) * (height * 0.65));
                    }

                    // Create gradient for bars
                    const gradient = ctx.createLinearGradient(0, centerY - barHeight / 2, 0, centerY + barHeight / 2);
                    gradient.addColorStop(0, '#3B82F6'); // Blue-500
                    gradient.addColorStop(0.5, '#6366F1'); // Indigo-500
                    gradient.addColorStop(1, '#8B5CF6'); // Purple-500

                    ctx.fillStyle = gradient;
                    ctx.beginPath();
                    ctx.roundRect(x, centerY - barHeight / 2, BAR_WIDTH, barHeight, 3);
                    ctx.fill();
                }
            } else if (state === 'paused') {
                // Static frozen wave
                for (let i = 0; i < BAR_COUNT; i++) {
                    const x = i * (BAR_WIDTH + BAR_GAP) + (width - BAR_COUNT * (BAR_WIDTH + BAR_GAP)) / 2;
                    const wave = Math.sin(i * 0.25) * 0.3 + 0.4;
                    const barHeight = wave * 30;

                    ctx.fillStyle = '#94A3B8'; // Slate-400
                    ctx.beginPath();
                    ctx.roundRect(x, centerY - barHeight / 2, BAR_WIDTH, barHeight, 3);
                    ctx.fill();
                }
            } else {
                // Idle or processing: subtle baseline
                for (let i = 0; i < BAR_COUNT; i++) {
                    const x = i * (BAR_WIDTH + BAR_GAP) + (width - BAR_COUNT * (BAR_WIDTH + BAR_GAP)) / 2;
                    ctx.fillStyle = '#CBD5E1'; // Slate-300
                    ctx.beginPath();
                    ctx.roundRect(x, centerY - 2, BAR_WIDTH, 4, 2);
                    ctx.fill();
                }
            }

            animationFrameRef.current = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        };
    }, [state, stream]);

    // Cleanup AudioContext on unmount
    useEffect(() => {
        return () => {
            if (sourceRef.current) {
                sourceRef.current.disconnect();
            }
            if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
                audioContextRef.current.close().catch(() => {});
            }
        };
    }, []);

    return (
        <div className={`rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-950 p-5 text-white shadow-lg relative overflow-hidden ${className}`}>
            {/* Header Telemetry Pill */}
            <div className="flex items-center justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                    {state === 'recording' && (
                        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-bold tracking-wider uppercase shadow-sm">
                            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                            <span>REC</span>
                        </div>
                    )}
                    {state === 'paused' && (
                        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-950/80 border border-amber-800 text-amber-300 text-xs font-bold tracking-wider uppercase">
                            <span>PAUSED</span>
                        </div>
                    )}
                    {state === 'processing' && (
                        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/80 border border-purple-800 text-purple-300 text-xs font-bold tracking-wider uppercase">
                            <span className="w-2 h-2 rounded-full bg-purple-400 animate-spin" />
                            <span>AI Transcribing</span>
                        </div>
                    )}
                    {state === 'idle' && (
                        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 text-xs font-medium">
                            <span>Ready to Record</span>
                        </div>
                    )}

                    <div className="flex items-center gap-1.5 text-xs text-slate-400">
                        <span>Audio Engine:</span>
                        <span className="font-mono text-slate-200 font-medium">Whisper-Large-v3</span>
                    </div>
                </div>

                {/* Live Duration Timer */}
                <div className="flex items-center gap-3 font-mono">
                    {state === 'recording' && (
                        <span className="text-xs text-slate-400 font-sans hidden sm:inline-block">
                            Input Level: <strong className="text-slate-200">{decibels} dB</strong>
                        </span>
                    )}
                    <span className="text-xl sm:text-2xl font-bold text-white tracking-widest bg-slate-900 px-3 py-1 rounded-xl border border-slate-800 shadow-inner">
                        {formatTime(durationSeconds)}
                    </span>
                </div>
            </div>

            {/* Canvas Multi-Bar Visualizer */}
            <div className="w-full flex justify-center items-center py-1">
                <canvas ref={canvasRef} className="w-full h-24 block" />
            </div>

            {/* Sub-label */}
            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800/80 mt-2">
                <span>Multi-channel consultation audio stream (Doctor + Patient)</span>
                <span>Stereo 48kHz • 256kbps WebM</span>
            </div>
        </div>
    );
}
