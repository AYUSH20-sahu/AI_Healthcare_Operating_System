/**
 * AI-HOS API Client - Central Facade
 * 
 * Modular domain implementations are organized in ./api/:
 * - client.ts: Base ApiClient, ApiError, fetch wrapper, token refresh
 * - auth.ts: Identity, login, registration, token handling
 * - organizations.ts: Multi-tenant organization governance
 * - patients.ts: Patient records, portal dashboard, reports, reminders
 * - doctors.ts: Doctor directory, availability, Head Physician oversight
 * - nurses.ts: Ward roster, Head Nurse oversight, staff nurse onboarding
 * - appointments.ts: Schedules, queue, booking
 * - prescriptions.ts: Prescriptions, medication safety, interaction checks
 * - clinical.ts: Medical records, copilot analysis, M23 approvals, scribe, intake
 * - admin.ts: Admin user management, 4-step provisioning, operations, audit
 * - telehealth.ts: Telehealth rooms, doctor schedule, WebRTC signaling
 * - abdm.ts: ABDM M1/M2/M3 sandbox & HL7 FHIR R4 interoperability
 * - observability.ts: Health checks and telemetry metrics
 */

export * from './api/index';
export { default } from './api/client';