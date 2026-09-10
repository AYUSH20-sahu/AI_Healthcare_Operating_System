// test-admin.mjs
// Verifies Admin User credentials, JWT auth, and Level-4 Admin clearance APIs

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

async function testAdmin() {
    console.log(`\n==============================================`);
    console.log(`[AI-HOS] Testing Admin Authentication & APIs`);
    console.log(`Target Backend: ${BACKEND_URL}`);
    console.log(`==============================================\n`);

    // 1. Health check
    try {
        const healthRes = await fetch(`${BACKEND_URL}/health`);
        const health = await healthRes.json();
        console.log(`✓ [Health Check] Backend is healthy:`, health);
    } catch (e) {
        console.error(`✗ [Health Check] Could not connect to backend at ${BACKEND_URL}:`, e.message);
        process.exit(1);
    }

    // 2. Test Admin Login
    const candidates = [
        { email: 'admin@test.com', password: 'adminpassword123' },
        { email: 'admin@hospital.com', password: 'admin123' },
    ];

    let authToken = null;
    let loggedInEmail = null;

    for (const cand of candidates) {
        console.log(`\n[Auth] Attempting login with: ${cand.email}...`);
        try {
            const loginRes = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: cand.email, password: cand.password }),
            });

            if (loginRes.ok) {
                const tokenData = await loginRes.json();
                authToken = tokenData.access_token;
                loggedInEmail = cand.email;
                console.log(`✓ [Auth] Successfully authenticated as ${cand.email}!`);
                console.log(`  Access Token: ${authToken.slice(0, 20)}...`);
                break;
            } else {
                const err = await loginRes.text();
                console.log(`  Candidate ${cand.email} returned HTTP ${loginRes.status}: ${err}`);
            }
        } catch (e) {
            console.log(`  Candidate ${cand.email} connection error:`, e.message);
        }
    }

    if (!authToken) {
        console.error('\n✗ [Auth Error] No admin credentials succeeded.');
        process.exit(1);
    }

    // 3. Verify /api/v1/auth/me
    console.log(`\n[Identity] Verifying server-verified role via /api/v1/auth/me...`);
    const meRes = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${authToken}` },
    });
    if (!meRes.ok) {
        console.error(`✗ Failed to get user profile: HTTP ${meRes.status}`);
        process.exit(1);
    }
    const me = await meRes.json();
    console.log(`✓ [Identity] Profile:`, {
        user_id: me.user_id,
        email: me.email,
        full_name: me.full_name,
        role: me.role,
        is_active: me.is_active,
    });

    if (me.role !== 'admin') {
        console.error(`✗ Role is '${me.role}', expected 'admin'`);
        process.exit(1);
    }
    console.log(`✓ [Role Clearance] Verified role is strictly 'admin'.`);

    // 4. Test /api/v1/admin/users/ (List users)
    console.log(`\n[Admin API] Testing GET /api/v1/admin/users/...`);
    const listRes = await fetch(`${BACKEND_URL}/api/v1/admin/users/`, {
        headers: { Authorization: `Bearer ${authToken}` },
    });
    if (!listRes.ok) {
        console.error(`✗ Admin API rejected: HTTP ${listRes.status}`);
        const text = await listRes.text();
        console.error(text);
        process.exit(1);
    }
    const userList = await listRes.json();
    console.log(`✓ [Admin API] Successfully listed users: Total = ${userList.total}`);
    userList.users.slice(0, 5).forEach((u, i) => {
        console.log(`  [${i + 1}] ${u.full_name} <${u.email}> - Role: ${u.role}, Active: ${u.is_active}`);
    });

    // 5. Test provisioning a new user through Admin API
    const testDocEmail = `test.doc.${Date.now()}@hospital.org`;
    console.log(`\n[Admin API] Testing POST /api/v1/admin/users/ (Provision Doctor: ${testDocEmail})...`);
    const provRes = await fetch(`${BACKEND_URL}/api/v1/admin/users/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
            full_name: 'Dr. Test Clinician',
            email: testDocEmail,
            password: 'clinicianPassword123',
            role: 'doctor',
            specialty: 'Cardiology',
            license_number: `LIC-${Date.now().toString().slice(-6)}`,
            hospital_affiliation: 'AI-HOS Verified Clinic',
        }),
    });

    if (!provRes.ok) {
        console.error(`✗ Admin provisioning failed: HTTP ${provRes.status}`);
        const text = await provRes.text();
        console.error(text);
        process.exit(1);
    }
    const provUser = await provRes.json();
    console.log(`✓ [Admin API] Successfully provisioned Doctor account:`, {
        user_id: provUser.user_id,
        email: provUser.email,
        role: provUser.role,
        license: provUser.doctor_profile?.license_number,
        specialty: provUser.doctor_profile?.specialty,
    });

    console.log(`\n==============================================`);
    console.log(`✓ ALL ADMIN CHECKS PASSED!`);
    console.log(`  Admin Email: ${loggedInEmail}`);
    console.log(`  Clearance:   Level 4 Administrator`);
    console.log(`==============================================\n`);
}

testAdmin().catch((err) => {
    console.error('Fatal error:', err);
    process.exit(1);
});
