// test-e2e.mjs
// Unified Full-Stack E2E Test Suite for Milestone U-24
// Validates end-to-end integration across Patient, Doctor, and Admin journeys

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const PASS = '✓';
const FAIL = '✗';

let totalTests = 0;
let passedTests = 0;

function assert(condition, message) {
    totalTests++;
    if (condition) {
        passedTests++;
        console.log(`  ${PASS} ${message}`);
    } else {
        console.error(`  ${FAIL} FAILED: ${message}`);
        throw new Error(`Assertion failed: ${message}`);
    }
}

async function loginUser(email, password) {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Login failed for ${email} (${res.status}): ${text}`);
    }
    const data = await res.json();
    return data.access_token;
}

async function runE2E() {
    console.log(`\n=============================================================`);
    console.log(`[AI-HOS] Milestone U-24: Unified Full-Stack E2E Test Suite`);
    console.log(`Target Backend: ${BACKEND_URL}`);
    console.log(`Timestamp:      ${new Date().toISOString()}`);
    console.log(`=============================================================\n`);

    // -------------------------------------------------------------
    // Phase 1: System Infrastructure & Health
    // -------------------------------------------------------------
    console.log(`[Phase 1] Validating System Health & Core API...`);
    let healthRes;
    try {
        healthRes = await fetch(`${BACKEND_URL}/health`);
    } catch (err) {
        console.error(`\n  ${FAIL} [Connection Error] Could not connect to backend server at: ${BACKEND_URL}`);
        console.error(`\n  Please start the backend server before running E2E integration tests:`);
        console.error(`    1. In a separate terminal, run:`);
        console.error(`       cd backend`);
        console.error(`       .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000 --reload`);
        console.error(`    2. Or via Docker:`);
        console.error(`       docker compose up backend\n`);
        process.exit(1);
    }
    assert(healthRes.ok, `Backend /health endpoint returns HTTP 200 OK`);
    const health = await healthRes.json();
    assert(health.status === 'ok' || health.status === 'healthy', `System status is reported as '${health.status}'`);

    // -------------------------------------------------------------
    // Phase 2: Patient E2E Journey
    // -------------------------------------------------------------
    console.log(`\n[Phase 2] Executing Patient E2E Workflow...`);
    const patientToken = await loginUser('patient@test.com', 'patientpassword123');
    assert(!!patientToken, `Patient authentication succeeded (JWT access token issued)`);

    const patientHeaders = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${patientToken}`,
    };

    const patMeRes = await fetch(`${BACKEND_URL}/api/v1/auth/me`, { headers: patientHeaders });
    assert(patMeRes.ok, `Patient identity query /auth/me succeeded`);
    const patMe = await patMeRes.json();
    assert(patMe.role === 'patient', `Authenticated user role is strictly 'patient'`);
    assert(patMe.email === 'patient@test.com', `Patient email verified: ${patMe.email}`);

    // Query Patient Appointments
    const patApptsRes = await fetch(`${BACKEND_URL}/api/v1/appointments`, { headers: patientHeaders });
    assert(patApptsRes.ok, `Patient appointment list retrieved (HTTP ${patApptsRes.status})`);
    const patAppts = await patApptsRes.json();
    const apptList = Array.isArray(patAppts) ? patAppts : patAppts.appointments || [];
    console.log(`    Found ${apptList.length} scheduled appointment(s) for patient.`);

    // Active Intake Session Check
    const activeIntakeRes = await fetch(`${BACKEND_URL}/api/v1/intake/sessions/active`, { headers: patientHeaders });
    assert(
        activeIntakeRes.status === 200 || activeIntakeRes.status === 404,
        `Intake active session check returns valid HTTP code (${activeIntakeRes.status})`
    );

    // Patient Access Control Boundary: Attempt to access admin routes must return 403
    const patAdminRes = await fetch(`${BACKEND_URL}/api/v1/admin/users/`, { headers: patientHeaders });
    assert(patAdminRes.status === 403, `RBAC Boundary Enforced: Patient blocked from Admin API (HTTP 403)`);

    // -------------------------------------------------------------
    // Phase 3: Doctor E2E Journey
    // -------------------------------------------------------------
    console.log(`\n[Phase 3] Executing Doctor E2E Workflow & Clinical Gate...`);
    const doctorToken = await loginUser('doctor@test.com', 'doctorpassword123');
    assert(!!doctorToken, `Doctor authentication succeeded (JWT access token issued)`);

    const doctorHeaders = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${doctorToken}`,
    };

    const docMeRes = await fetch(`${BACKEND_URL}/api/v1/auth/me`, { headers: doctorHeaders });
    assert(docMeRes.ok, `Doctor identity query /auth/me succeeded`);
    const docMe = await docMeRes.json();
    assert(docMe.role === 'doctor', `Authenticated user role is strictly 'doctor'`);
    assert(docMe.email === 'doctor@test.com', `Doctor email verified: ${docMe.email}`);

    // Inspect Doctor Consultations / Appointments
    const docApptsRes = await fetch(`${BACKEND_URL}/api/v1/appointments`, { headers: doctorHeaders });
    assert(docApptsRes.ok, `Doctor schedule list retrieved (HTTP ${docApptsRes.status})`);

    // Inspect Approval Queue Drafts
    const approvalQueueRes = await fetch(`${BACKEND_URL}/api/v1/approval/drafts`, { headers: doctorHeaders });
    assert(approvalQueueRes.ok, `Doctor approval queue /approval/drafts accessed (HTTP ${approvalQueueRes.status})`);
    const queueData = await approvalQueueRes.json();
    assert(Array.isArray(queueData.medical_records), `Approval queue includes medical_records array`);
    assert(Array.isArray(queueData.prescriptions), `Approval queue includes prescriptions array`);
    console.log(`    Draft medical records pending review: ${queueData.medical_records.length}`);
    console.log(`    Draft prescriptions pending review:  ${queueData.prescriptions.length}`);

    // Doctor Access Control Boundary: Attempt to provision users must return 403
    const docAdminRes = await fetch(`${BACKEND_URL}/api/v1/admin/users/`, { headers: doctorHeaders });
    assert(docAdminRes.status === 403, `RBAC Boundary Enforced: Doctor blocked from Admin API (HTTP 403)`);

    // -------------------------------------------------------------
    // Phase 4: Admin E2E Journey
    // -------------------------------------------------------------
    console.log(`\n[Phase 4] Executing Admin E2E Workflow & Governance...`);
    const adminToken = await loginUser('admin@test.com', 'adminpassword123');
    assert(!!adminToken, `Admin authentication succeeded (JWT access token issued)`);

    const adminHeaders = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${adminToken}`,
    };

    const adminMeRes = await fetch(`${BACKEND_URL}/api/v1/auth/me`, { headers: adminHeaders });
    assert(adminMeRes.ok, `Admin identity query /auth/me succeeded`);
    const adminMe = await adminMeRes.json();
    assert(adminMe.role === 'admin', `Authenticated user role is strictly 'admin'`);

    // Query Users List
    const usersListRes = await fetch(`${BACKEND_URL}/api/v1/admin/users/`, { headers: adminHeaders });
    assert(usersListRes.ok, `Admin user management list retrieved (HTTP ${usersListRes.status})`);
    const usersData = await usersListRes.json();
    assert(usersData.total >= 3, `User roster contains seeded users (total: ${usersData.total})`);

    // Provision New Doctor with License & Specialty
    const testDocEmail = `e2e.doc.${Date.now()}@hospital.org`;
    const testLicense = `MD-E2E-${Date.now().toString().slice(-6)}`;
    const provRes = await fetch(`${BACKEND_URL}/api/v1/admin/users/`, {
        method: 'POST',
        headers: adminHeaders,
        body: JSON.stringify({
            full_name: 'Dr. E2E Validation Specialist',
            email: testDocEmail,
            password: 'clinicianPassw0rd!123',
            role: 'doctor',
            specialty: 'Internal Medicine',
            license_number: testLicense,
            hospital_affiliation: 'AI-HOS Global Medical Center',
        }),
    });
    assert(provRes.ok, `Admin successfully provisioned clinician: ${testDocEmail} (HTTP ${provRes.status})`);
    const provData = await provRes.json();
    assert(provData.doctor_profile?.license_number === testLicense, `Verified unique medical license assigned`);

    // Consent Registry Inspection
    const consentsRes = await fetch(`${BACKEND_URL}/api/v1/consents`, { headers: adminHeaders });
    assert(consentsRes.ok, `Consent registry queried (HTTP ${consentsRes.status})`);
    const consentsData = await consentsRes.json();
    assert(Array.isArray(consentsData), `Consent records returned as list (count: ${consentsData.length})`);

    // Immutable Audit Trail Inspection
    const auditRes = await fetch(`${BACKEND_URL}/api/v1/admin/audit/logs`, { headers: adminHeaders });
    assert(auditRes.ok, `Immutable audit trail queried (HTTP ${auditRes.status})`);
    const auditData = await auditRes.json();
    const auditLogs = auditData.logs || auditData.items || auditData;
    assert(Array.isArray(auditLogs) && auditLogs.length > 0, `Audit log entries verified in system of record`);

    // -------------------------------------------------------------
    // Phase 5: Security Defense Checks
    // -------------------------------------------------------------
    console.log(`\n[Phase 5] Executing Security & Privilege Escalation Defenses...`);

    // Unauthenticated access attempt to protected endpoint
    const unauthRes = await fetch(`${BACKEND_URL}/api/v1/admin/users/`);
    assert(unauthRes.status === 401, `Unauthenticated request strictly returns HTTP 401 Unauthorized`);

    // Public Registration Privilege Escalation Check: role="admin" must be rejected or coerced to patient
    const attemptEmail = `exploit.${Date.now()}@test.com`;
    const exploitRes = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: attemptEmail,
            password: 'exploitPassword123!',
            full_name: 'Exploit Tester',
            role: 'admin', // Malicious attempt to self-promote
        }),
    });
    // Should either reject (400/422) or coerce to patient (role != admin)
    if (exploitRes.ok) {
        const exploitData = await exploitRes.json();
        assert(exploitData.role === 'patient', `Privilege escalation neutralized: assigned role is 'patient'`);
    } else {
        assert(
            exploitRes.status === 400 || exploitRes.status === 422,
            `Privilege escalation rejected with validation error (HTTP ${exploitRes.status})`
        );
    }

    console.log(`\n=============================================================`);
    console.log(`✓ ALL E2E WORKFLOW CHECKS PASSED SUCCESSFULLY!`);
    console.log(`  Tests Executed: ${totalTests}`);
    console.log(`  Tests Passed:   ${passedTests}`);
    console.log(`  Failure Count:  0`);
    console.log(`  Milestone:      U-24 (Full Test Coverage + E2E)`);
    console.log(`=============================================================\n`);
}

runE2E().catch((err) => {
    console.error('\n✗ E2E TEST RUN ABORTED WITH ERROR:', err.message);
    process.exit(1);
});
