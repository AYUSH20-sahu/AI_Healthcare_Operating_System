# Tech Stack — AI-HOS

## Frontend
- **Framework**: Next.js + React
- **Styling**: Tailwind CSS
- **Routing**: Role-based routing for Patient/Doctor/Admin

## Backend
- **Framework**: FastAPI (Python)
- **Containerization**: Docker

## Database
- **Primary**: PostgreSQL
- **Cache/Session**: Redis

## AI
- **LLM**: Pluggable provider interface (Gemini / OpenAI / Claude — selectable at config level)
- **Voice**: Whisper (STT), ElevenLabs (TTS) — behind provider interface

## Infrastructure
- **Container Orchestration**: Docker + Kubernetes
- **CI/CD**: GitHub Actions

## Interoperability Targets
- HL7 FHIR R4
- India's ABDM (ABHA, Consent Manager, HFR, HPR)
- NHCX for claims