'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
    appointmentBookingApi,
    intakeApi,
    Doctor,
    DoctorAvailabilityResponse,
    TimeSlotItem,
    Appointment,
} from '@/lib/api';

export default function BookAppointmentPage() {
    const router = useRouter();
    const searchParams = useSearchParams();

    // Step state (1: Doctor, 2: Date & Slot, 3: Reason & Intake, 4: Success)
    const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);

    // Data lists
    const [specialties, setSpecialties] = useState<string[]>([]);
    const [selectedSpecialty, setSelectedSpecialty] = useState<string>('All');
    const [doctors, setDoctors] = useState<Doctor[]>([]);
    const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);

    // Date & Slot
    const getTomorrowDateStr = () => {
        const d = new Date();
        d.setDate(d.getDate() + 1);
        return d.toISOString().split('T')[0];
    };
    const [selectedDate, setSelectedDate] = useState<string>(getTomorrowDateStr());
    const [availability, setAvailability] = useState<DoctorAvailabilityResponse | null>(null);
    const [selectedSlot, setSelectedSlot] = useState<TimeSlotItem | null>(null);

    // Reason & Intake Session
    const [reasonText, setReasonText] = useState('');
    const [intakeSessionId, setIntakeSessionId] = useState<string | null>(null);
    const [intakeSummary, setIntakeSummary] = useState<string | null>(null);

    // Final booked appointment
    const [bookedAppointment, setBookedAppointment] = useState<Appointment | null>(null);

    // Loading & Error states
    const [isLoadingDoctors, setIsLoadingDoctors] = useState(true);
    const [isLoadingSlots, setIsLoadingSlots] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    // Load specialties, doctors, and active intake on mount
    useEffect(() => {
        loadInitialData();
    }, []);

    const loadInitialData = async () => {
        setIsLoadingDoctors(true);
        setErrorMessage(null);
        try {
            const [specs, docsRes, activeIntake] = await Promise.allSettled([
                appointmentBookingApi.getSpecialties(),
                appointmentBookingApi.getDoctors(),
                intakeApi.getActiveSession(),
            ]);

            if (specs.status === 'fulfilled') {
                setSpecialties(['All', ...specs.value]);
            }
            if (docsRes.status === 'fulfilled') {
                setDoctors(docsRes.value.doctors || []);
            }
            if (activeIntake.status === 'fulfilled' && activeIntake.value) {
                const intake = activeIntake.value;
                setIntakeSessionId(intake.session_id);
                if (intake.structured_symptoms?.chief_complaint) {
                    setIntakeSummary(intake.structured_symptoms.chief_complaint);
                    setReasonText(intake.structured_symptoms.chief_complaint);
                }
            }
        } catch (err: any) {
            console.error('Failed to load initial booking data:', err);
            setErrorMessage('Unable to load clinical providers. Please retry.');
        } finally {
            setIsLoadingDoctors(false);
        }
    };

    // Reload doctors when specialty filter changes
    useEffect(() => {
        if (currentStep === 1) {
            loadDoctors(selectedSpecialty);
        }
    }, [selectedSpecialty]);

    const loadDoctors = async (spec: string) => {
        setIsLoadingDoctors(true);
        try {
            const res = await appointmentBookingApi.getDoctors(spec);
            setDoctors(res.doctors || []);
        } catch (err) {
            console.error('Failed to filter doctors:', err);
        } finally {
            setIsLoadingDoctors(false);
        }
    };

    // Load availability slots when doctor and date are selected
    useEffect(() => {
        if (selectedDoctor && selectedDate) {
            loadDoctorSlots(selectedDoctor.doctor_id, selectedDate);
        }
    }, [selectedDoctor, selectedDate]);

    const loadDoctorSlots = async (docId: string, dtStr: string) => {
        setIsLoadingSlots(true);
        setSelectedSlot(null);
        setErrorMessage(null);
        try {
            const res = await appointmentBookingApi.getAvailability(docId, dtStr, 30);
            setAvailability(res);
        } catch (err: any) {
            console.error('Failed to load availability:', err);
            setErrorMessage(err?.message || 'Failed to fetch doctor availability slots.');
        } finally {
            setIsLoadingSlots(false);
        }
    };

    // Handle Confirm Booking Submission
    const handleConfirmBooking = async () => {
        if (!selectedDoctor || !selectedSlot) return;
        setIsSubmitting(true);
        setErrorMessage(null);

        try {
            const res = await appointmentBookingApi.bookAppointment({
                doctor_id: selectedDoctor.doctor_id,
                scheduled_at: selectedSlot.start_time,
                duration_minutes: selectedSlot.duration_minutes || 30,
                reason: reasonText.trim() || undefined,
                intake_session_id: intakeSessionId || undefined,
            });
            setBookedAppointment(res);
            setCurrentStep(4);
        } catch (err: any) {
            console.error('Booking failed:', err);
            // Check for 409 conflict
            if (err?.status === 409 || err?.message?.includes('conflict') || err?.message?.includes('no longer available')) {
                setErrorMessage('⚠️ This slot was recently taken by another patient. Please select an alternate time.');
                // Refresh slots
                if (selectedDoctor) {
                    loadDoctorSlots(selectedDoctor.doctor_id, selectedDate);
                }
                setCurrentStep(2);
            } else {
                setErrorMessage(err?.message || 'Failed to schedule appointment. Please try again.');
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-6 pb-12">
            {/* Header & Steps Indicator */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/60">
                            Milestone U-15
                        </span>
                        <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300">
                            Direct Scheduling
                        </span>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                        Book Doctor Consultation
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Find a specialist, choose your preferred time slot, and link your AI intake summary.
                    </p>
                </div>

                <Link
                    href="/patient/appointments"
                    className="px-3.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition text-center"
                >
                    Cancel & Return
                </Link>
            </div>

            {/* Stepper Progress Bar */}
            {currentStep !== 4 && (
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-medium">
                    <div className={`p-2.5 rounded-xl border transition ${
                        currentStep === 1
                            ? 'bg-indigo-50 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 font-bold'
                            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-400'
                    }`}>
                        1. Select Doctor
                    </div>
                    <div className={`p-2.5 rounded-xl border transition ${
                        currentStep === 2
                            ? 'bg-indigo-50 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 font-bold'
                            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-400'
                    }`}>
                        2. Date & Time Slot
                    </div>
                    <div className={`p-2.5 rounded-xl border transition ${
                        currentStep === 3
                            ? 'bg-indigo-50 dark:bg-indigo-950/60 border-indigo-300 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 font-bold'
                            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-400'
                    }`}>
                        3. Review & Confirm
                    </div>
                </div>
            )}

            {/* Error Notification */}
            {errorMessage && (
                <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs sm:text-sm text-rose-700 dark:text-rose-300 flex items-center justify-between">
                    <span>{errorMessage}</span>
                    <button onClick={() => setErrorMessage(null)} className="text-rose-500 font-bold ml-2">✕</button>
                </div>
            )}

            {/* STEP 1: Select Doctor & Specialty */}
            {currentStep === 1 && (
                <div className="space-y-5">
                    {/* Specialty Chips */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
                            Filter by Clinical Specialty
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {specialties.map((spec) => (
                                <button
                                    key={spec}
                                    type="button"
                                    onClick={() => setSelectedSpecialty(spec)}
                                    className={`px-3 py-1.5 rounded-full text-xs font-semibold transition ${
                                        selectedSpecialty === spec
                                            ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30'
                                            : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-slate-300'
                                    }`}
                                >
                                    {spec}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Doctors List */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                                Available Physicians ({doctors.length})
                            </h2>
                            <span className="text-xs text-slate-400">
                                Showing licensed attending doctors
                            </span>
                        </div>

                        {isLoadingDoctors ? (
                            <div className="p-12 text-center text-slate-400 text-sm bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 flex items-center justify-center gap-2">
                                <svg className="animate-spin w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                                Loading doctors directory...
                            </div>
                        ) : doctors.length === 0 ? (
                            <div className="p-12 text-center text-slate-400 text-sm bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
                                No doctors found for specialty &ldquo;{selectedSpecialty}&rdquo;. Try another category.
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {doctors.map((doc) => {
                                    const isSelected = selectedDoctor?.doctor_id === doc.doctor_id;
                                    return (
                                        <div
                                            key={doc.doctor_id}
                                            onClick={() => setSelectedDoctor(doc)}
                                            className={`p-4 rounded-2xl border cursor-pointer transition-all shadow-sm flex items-start gap-3.5 ${
                                                isSelected
                                                    ? 'border-indigo-600 dark:border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/20 ring-2 ring-indigo-500/20'
                                                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                                            }`}
                                        >
                                            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold text-sm shadow-md shadow-indigo-500/20 flex-shrink-0">
                                                {doc.full_name.replace('Dr. ', '').charAt(0)}
                                            </div>

                                            <div className="flex-1 min-w-0 space-y-1">
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                                        {doc.full_name}
                                                    </h3>
                                                    {isSelected && (
                                                        <span className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs">
                                                            ✓
                                                        </span>
                                                    )}
                                                </div>

                                                <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                                                    {doc.specialty}
                                                </p>

                                                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                                                    {doc.hospital_affiliation || 'AI-HOS Medical Center'}
                                                </p>

                                                <div className="pt-1 flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                                                    <span>Lic: {doc.license_number}</span>
                                                    <span>•</span>
                                                    <span className="text-emerald-600 dark:text-emerald-400 font-sans font-semibold">
                                                        Telehealth & Clinic
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Step 1 Actions */}
                    <div className="flex justify-end pt-2">
                        <button
                            type="button"
                            disabled={!selectedDoctor}
                            onClick={() => setCurrentStep(2)}
                            className="px-6 py-2.5 rounded-xl bg-indigo-600 text-white text-xs sm:text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition shadow-sm"
                        >
                            Select Date & Time →
                        </button>
                    </div>
                </div>
            )}

            {/* STEP 2: Date & Available Slot Selection */}
            {currentStep === 2 && selectedDoctor && (
                <div className="space-y-5">
                    {/* Selected Doctor Recap */}
                    <div className="p-3.5 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/50 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs">
                                {selectedDoctor.full_name.replace('Dr. ', '').charAt(0)}
                            </div>
                            <div>
                                <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                                    {selectedDoctor.full_name}
                                </h4>
                                <span className="text-[11px] text-indigo-700 dark:text-indigo-300">
                                    {selectedDoctor.specialty} • {selectedDoctor.hospital_affiliation || 'AI-HOS Medical Center'}
                                </span>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={() => setCurrentStep(1)}
                            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
                        >
                            Change Doctor
                        </button>
                    </div>

                    {/* Date Selector */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
                            Choose Consultation Date
                        </label>
                        <div className="flex items-center gap-3 flex-wrap">
                            <input
                                type="date"
                                min={new Date().toISOString().split('T')[0]}
                                value={selectedDate}
                                onChange={(e) => setSelectedDate(e.target.value)}
                                className="px-3.5 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-100 shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                            <span className="text-xs text-slate-400">
                                {new Date(selectedDate + 'T00:00:00').toLocaleDateString(undefined, {
                                    weekday: 'long',
                                    month: 'short',
                                    day: 'numeric',
                                })}
                            </span>
                        </div>
                    </div>

                    {/* Time Slot Matrix */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                                Available Time Slots (30-Minute Appointments)
                            </h3>
                            {availability && (
                                <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                                    {availability.available_slots_count} slots open
                                </span>
                            )}
                        </div>

                        {isLoadingSlots ? (
                            <div className="p-8 text-center text-slate-400 text-sm bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 flex items-center justify-center gap-2">
                                <svg className="animate-spin w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                                Calculating open doctor slots...
                            </div>
                        ) : !availability || availability.slots.length === 0 ? (
                            <div className="p-8 text-center text-slate-400 text-xs bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
                                No consultation slots configured for this date.
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                                {availability.slots.map((slot, idx) => {
                                    const isChosen = selectedSlot?.start_time === slot.start_time;
                                    const disabled = !slot.is_available;

                                    return (
                                        <button
                                            key={idx}
                                            type="button"
                                            disabled={disabled}
                                            onClick={() => setSelectedSlot(slot)}
                                            className={`p-3 rounded-xl border text-xs font-semibold transition flex flex-col items-center justify-center gap-1 ${
                                                disabled
                                                    ? 'bg-slate-100 dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 text-slate-400 cursor-not-allowed opacity-60'
                                                    : isChosen
                                                    ? 'bg-indigo-600 border-indigo-600 text-white shadow-md shadow-indigo-500/30'
                                                    : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200 hover:border-indigo-400'
                                            }`}
                                        >
                                            <span className="text-sm font-bold">{slot.slot_time}</span>
                                            <span className="text-[10px] font-normal">
                                                {disabled ? (slot.conflict_reason || 'Unavailable') : 'Available'}
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Step 2 Actions */}
                    <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-slate-800">
                        <button
                            type="button"
                            onClick={() => setCurrentStep(1)}
                            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        >
                            ← Back to Doctors
                        </button>

                        <button
                            type="button"
                            disabled={!selectedSlot}
                            onClick={() => setCurrentStep(3)}
                            className="px-6 py-2.5 rounded-xl bg-indigo-600 text-white text-xs sm:text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition shadow-sm"
                        >
                            Review & Add Purpose →
                        </button>
                    </div>
                </div>
            )}

            {/* STEP 3: Purpose, Intake Linking & Final Confirmation */}
            {currentStep === 3 && selectedDoctor && selectedSlot && (
                <div className="space-y-5">
                    {/* Summary Card */}
                    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
                        <h2 className="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 pb-3">
                            Appointment Summary
                        </h2>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
                            <div>
                                <span className="text-slate-400 text-xs block">Physician</span>
                                <span className="font-bold text-slate-900 dark:text-white">
                                    {selectedDoctor.full_name}
                                </span>
                                <span className="text-xs text-indigo-600 dark:text-indigo-400 block">
                                    {selectedDoctor.specialty}
                                </span>
                            </div>

                            <div>
                                <span className="text-slate-400 text-xs block">Scheduled Time</span>
                                <span className="font-bold text-slate-900 dark:text-white">
                                    {new Date(selectedSlot.start_time).toLocaleDateString(undefined, {
                                        weekday: 'short',
                                        month: 'short',
                                        day: 'numeric',
                                        year: 'numeric',
                                    })}
                                </span>
                                <span className="text-xs text-slate-600 dark:text-slate-300 block font-semibold">
                                    {selectedSlot.slot_time} ({selectedSlot.duration_minutes} mins)
                                </span>
                            </div>

                            <div>
                                <span className="text-slate-400 text-xs block">Consultation Format</span>
                                <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                                    📹 HD Telehealth Room (WebRTC Encrypted)
                                </span>
                            </div>

                            <div>
                                <span className="text-slate-400 text-xs block">Hospital Affiliation</span>
                                <span className="text-slate-700 dark:text-slate-300">
                                    {selectedDoctor.hospital_affiliation || 'AI-HOS Medical Center'}
                                </span>
                            </div>
                        </div>

                        {/* AI Intake Linking Banner if active session exists */}
                        {intakeSummary && (
                            <div className="p-3.5 rounded-xl bg-cyan-50/60 dark:bg-cyan-950/30 border border-cyan-200 dark:border-cyan-800 text-xs space-y-1">
                                <div className="flex items-center gap-1.5 font-bold text-cyan-800 dark:text-cyan-300">
                                    <span>✨ Pre-Consultation AI Intake Attached</span>
                                </div>
                                <p className="text-slate-700 dark:text-slate-300">
                                    Symptoms collected by AI Intake Assistant: <strong>&ldquo;{intakeSummary}&rdquo;</strong>
                                </p>
                                <span className="text-[10px] text-cyan-600 dark:text-cyan-400">
                                    Your attending physician will review your structured symptoms before call start.
                                </span>
                            </div>
                        )}

                        {/* Purpose Input */}
                        <div className="space-y-1.5 pt-2">
                            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">
                                Purpose of Visit / Symptoms (Optional)
                            </label>
                            <textarea
                                rows={3}
                                value={reasonText}
                                onChange={(e) => setReasonText(e.target.value)}
                                placeholder="Describe what you would like to discuss with the doctor..."
                                className="w-full resize-none rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3 text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                        </div>
                    </div>

                    {/* Step 3 Actions */}
                    <div className="flex items-center justify-between pt-2">
                        <button
                            type="button"
                            onClick={() => setCurrentStep(2)}
                            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                        >
                            ← Back to Time Slots
                        </button>

                        <button
                            type="button"
                            disabled={isSubmitting}
                            onClick={handleConfirmBooking}
                            className="px-8 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-700 hover:to-cyan-700 text-white text-xs sm:text-sm font-bold shadow-md shadow-indigo-500/20 disabled:opacity-50 transition"
                        >
                            {isSubmitting ? 'Confirming Booking...' : 'Confirm & Book Consultation'}
                        </button>
                    </div>
                </div>
            )}

            {/* STEP 4: Success Screen */}
            {currentStep === 4 && bookedAppointment && (
                <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-8 shadow-xl text-center space-y-6">
                    <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-300 mx-auto flex items-center justify-center text-3xl font-bold shadow-inner">
                        ✓
                    </div>

                    <div className="space-y-1">
                        <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 text-xs font-bold uppercase tracking-wider">
                            Booking Confirmed
                        </span>
                        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white pt-2">
                            Your Appointment has been Scheduled!
                        </h2>
                        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                            A confirmation has been recorded. You can join the telehealth room directly at your scheduled time.
                        </p>
                    </div>

                    {/* Booking Details Card */}
                    <div className="max-w-md mx-auto p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-left space-y-2 text-xs">
                        <div className="flex justify-between">
                            <span className="text-slate-400">Doctor:</span>
                            <span className="font-bold text-slate-800 dark:text-slate-200">
                                {selectedDoctor?.full_name} ({selectedDoctor?.specialty})
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-slate-400">Date:</span>
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                                {new Date(bookedAppointment.scheduled_at).toLocaleDateString(undefined, {
                                    weekday: 'long',
                                    month: 'long',
                                    day: 'numeric',
                                })}
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-slate-400">Time:</span>
                            <span className="font-bold text-indigo-600 dark:text-indigo-400">
                                {new Date(bookedAppointment.scheduled_at).toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                })} ({bookedAppointment.duration_minutes} mins)
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-slate-400">Status:</span>
                            <span className="font-bold text-emerald-600 uppercase">Confirmed</span>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
                        <Link
                            href={`/patient/consultation/${bookedAppointment.appointment_id}`}
                            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold transition shadow-md shadow-indigo-500/20"
                        >
                            📹 Enter Telehealth Room
                        </Link>
                        <Link
                            href="/patient/appointments"
                            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition"
                        >
                            View All My Appointments
                        </Link>
                    </div>
                </div>
            )}
        </div>
    );
}
