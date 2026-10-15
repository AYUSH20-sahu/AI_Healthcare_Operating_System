# AI-HOS Frontend Architecture & UI Design System

## 1. Framework Architecture

The AI-HOS frontend is built on **Next.js 14.2** utilizing the modern **App Router** paradigm (`frontend/src/app/`) with TypeScript and Tailwind CSS.

### 1.1 Directory Structure & Portal Hierarchies
```
frontend/src/
├── app/
│   ├── layout.tsx                     # Global Root Layout (Theme & Auth Providers)
│   ├── page.tsx                       # Public Landing Page & Service Discovery
│   ├── login/                         # Unified Role-Aware Authentication Screen
│   ├── doctor/                        # Doctor Clinical Workstation Portal
│   │   ├── page.tsx                   # Doctor Consultation Copilot & Active Encounter
│   │   ├── appointments/              # Outpatient Schedule & Filter Matrix
│   │   ├── patients/[id]/             # Detailed Longitudinal Patient History
│   │   ├── consultations/room/        # Doctor WebRTC Virtual Room
│   │   └── scribe/                    # Ambient Audio Scribe Studio
│   ├── patient/                       # Patient Self-Service Portal
│   │   ├── page.tsx                   # Patient Home Dashboard
│   │   ├── appointments/              # Appointment Overview & Cancellation
│   │   ├── appointments/book/         # 4-Step Booking Wizard
│   │   ├── consultation/[id]/         # Patient WebRTC Virtual Consultation Room
│   │   ├── records/                   # Patient Encounter Records & SOAP Viewer
│   │   ├── prescriptions/             # Active Medications & Refill Tracking
│   │   ├── reports/                   # Diagnostic Lab Report Upload & Viewing
│   │   └── intake/                    # AI Voice & Chat Symptom Triage Session
│   ├── nurse/                         # Inpatient Ward & Triage Portal
│   │   ├── page.tsx                   # Ward Overview & Bed Allocation
│   │   └── vitals/                    # Vital Signs Logging & Telemetry Queue
│   └── admin/                         # Hospital Administrative Portal
│       ├── page.tsx                   # Executive Overview & System Metrics
│       └── users/                     # Staff & Provider Provisioning
├── components/
│   ├── ui/                            # Design System Atoms & Molecules
│   │   ├── Button.tsx, Card.tsx, Badge.tsx, StatusBadge.tsx, Modal.tsx...
│   ├── copilot/                       # Clinical Decision Support Panels
│   ├── PatientSummary.tsx             # Reusable Longitudinal Patient Health Summary
│   └── ScribePanel.tsx                # Voice Note Waveform & SOAP Transcriber
└── lib/
    ├── api/                           # Domain-partitioned API Client Modules
    │   ├── client.ts, auth.ts, appointments.ts, telehealth.ts, doctors.ts...
    ├── auth.tsx                       # Context Provider & Role Guard Wrappers
    └── hooks/                         # Real-time WebSocket Hooks (useQueueStream...)
```

---

## 2. WebRTC Virtual Room & Telehealth Client Pipeline

The virtual consultation room (`src/app/patient/consultation/[appointmentId]/page.tsx` and `src/app/doctor/consultations/room/page.tsx`) implements an enterprise WebRTC pipeline:

1. **Progressive Media Acquisition**:
   - Queries `navigator.mediaDevices.getUserMedia` with preference for HD 720p user-facing video.
   - Automatically degrades through fallback tiers (Standard Video/Audio $\to$ Video-only $\to$ Audio-only) if device hardware or bandwidth is constrained.
   - Binds streams reactively via `useEffect` hooks to ensure video playback begins immediately upon DOM rendering.
2. **WebSocket Signalling Relay**:
   - Uses `getTelehealthWsUrl` from `@/lib/api/telehealth` to generate an absolute, validated `ws://` or `wss://` URI.
   - Handles full bidirectional signalling: `room_joined`, `peer_joined`, `offer`, `answer`, `ice-candidate`, `bye`.
3. **Picture-in-Picture (PiP) Dual Preview**:
   - Primary viewport: Remote attending physician or patient video feed.
   - Floating PiP: Mirrored local self-preview with instant mic mute and video toggle controls.

---

## 3. Design System & Theming

- **Curated Color Tokens**:
  - Primary Accent: Deep Indigo / Cyan gradient (`indigo-600` to `cyan-600`).
  - Clinical Success: Emerald (`emerald-600`).
  - Warning & Red Flags: Amber (`amber-500`) and Crimson (`rose-600`).
  - Neutral Base: Slate (`slate-900` dark / `slate-50` light).
- **Glassmorphism & Elevation**: Elevated cards utilize subtle translucent borders (`border-slate-200 dark:border-slate-800`), backdrop blurs, and soft box shadows.
- **Accessibility (a11y)**: All interactive inputs maintain explicit focus rings, keyboard navigability, and WCAG AA color contrast compliance.
