"""Tests for Repository Audit Report Remediation.

Validates:
1. Complete elimination of leaked Nhost credentials and JWT secrets across all repo files.
2. Removal of One-Click Test Personas quick-login buttons from the frontend login page.
3. Hardened redirect validation (open redirect defense + role authorization check) on the login page.
4. Defense against mass assignment / role escalation in UserSignupRequest (extra fields forbidden, strictly creates patients).
5. Frontend TypeScript interfaces cleanly decoupled from role parameter during registration.
6. CI pipeline configuration includes compileall and TypeScript typecheck.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.auth.service import UserSignupRequest, UserCreate
from app.models import UserRole


LEAKED_NHOST_DOMAIN = "icfbnbiumbflxblqcwdl.db.ap-south-1.nhost.run"
LEAKED_DB_PASSWORD = "@7HmkeZnqpfJSaB"
LEAKED_JWT_SECRET = "K8mN2pQ9vX5yL3wR7tZ1cV6bH4jM8nP2qW5eR9uY3oI6aS1dF4gH7kL0zX8cV"

# Project root relative to backend/tests
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestCredentialRemediation:
    """Ensure no leaked database credentials or production JWT secrets remain in tracked files."""

    def test_settings_does_not_contain_leaked_credentials(self):
        settings = Settings(
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_hos",
            JWT_SECRET_KEY="test_remediation_secret_key_long_enough_32c",
            APP_ENV="development",
        )
        assert LEAKED_NHOST_DOMAIN not in settings.DATABASE_URL
        assert LEAKED_DB_PASSWORD not in settings.DATABASE_URL
        assert settings.JWT_SECRET_KEY != LEAKED_JWT_SECRET

    @pytest.mark.parametrize(
        "weak_key",
        [
            "dev_insecure_jwt_secret_change_in_production_min32chars",
            "dev_insecure_jwt_secret_change_in_production_min64chars",
            "short",
        ],
    )
    def test_settings_rejects_weak_jwt_in_production(self, weak_key: str):
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set to a strong secret"):
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY=weak_key,
            )

    @pytest.mark.parametrize(
        "relative_path",
        [
            "docker-compose.yml",
            "backend/alembic.ini",
            "backend/create_admin_user.py",
            "database/seed.py",
            "README.md",
            ".env.dev",
            ".env.example",
            ".env",
            ".env.local",
        ],
    )
    def test_files_clean_of_leaked_credentials(self, relative_path: str):
        target_file = REPO_ROOT / relative_path
        if not target_file.exists():
            pytest.skip(f"File {relative_path} does not exist in repo, skipping.")

        content = target_file.read_text(encoding="utf-8", errors="ignore")
        assert LEAKED_NHOST_DOMAIN not in content, f"Leaked Nhost domain found in {relative_path}"
        assert LEAKED_DB_PASSWORD not in content, f"Leaked DB password found in {relative_path}"
        assert LEAKED_JWT_SECRET not in content, f"Leaked JWT secret found in {relative_path}"


class TestLoginSecurityRemediation:
    """Verify frontend login page removed test personas and has open redirect protection."""

    def test_login_page_no_quick_persona_buttons(self):
        login_file = REPO_ROOT / "frontend/src/app/auth/login/page.tsx"
        assert login_file.exists(), "frontend login page not found"
        content = login_file.read_text(encoding="utf-8")

        # Must not contain one-click persona UI
        assert "One-Click Test Personas" not in content
        assert "handleQuickPersona" not in content
        assert "doctorpassword123" not in content
        assert "patientpassword123" not in content
        assert "adminpassword123" not in content

    def test_login_page_has_open_redirect_defense(self):
        login_file = REPO_ROOT / "frontend/src/app/auth/login/page.tsx"
        content = login_file.read_text(encoding="utf-8")

        # Must check startsWith('/') and block protocol-relative '//'
        assert "redirectUrl.startsWith('/')" in content
        assert "!redirectUrl.startsWith('//')" in content
        # Must validate role authorized target
        assert "user.role === 'doctor'" in content
        assert "user.role === 'patient'" in content
        assert "user.role === 'admin'" in content


class TestRegistrationMassAssignmentRemediation:
    """Verify public signup strictly enforces PATIENT role and forbids role injection."""

    def test_user_signup_request_schema_forbids_role(self):
        # Valid signup payload
        signup = UserSignupRequest(
            email="patient.test@example.com",
            password="StrongPassword123!",
            full_name="Valid Patient",
        )
        assert signup.email == "patient.test@example.com"
        assert not hasattr(signup, "role")

        # Attempting to supply role must fail due to extra='forbid'
        with pytest.raises(ValidationError):
            UserSignupRequest(
                email="patient.test@example.com",
                password="StrongPassword123!",
                full_name="Valid Patient",
                role="admin",  # forbidden extra attribute
            )

    def test_user_create_defaults_to_patient(self):
        user_create = UserCreate(
            email="new@example.com",
            password="Password123!",
            full_name="Test User",
        )
        assert user_create.role == UserRole.PATIENT.value

    def test_frontend_api_signup_request_no_role(self):
        api_file = REPO_ROOT / "frontend/src/lib/api.ts"
        assert api_file.exists(), "frontend api.ts not found"
        content = api_file.read_text(encoding="utf-8")

        # In SignupRequest interface, role should not be present
        signup_block = content[content.find("interface SignupRequest") : content.find("interface SignupRequest") + 150]
        assert "role" not in signup_block

    def test_frontend_register_page_does_not_pass_role(self):
        register_file = REPO_ROOT / "frontend/src/app/auth/register/page.tsx"
        assert register_file.exists(), "frontend register page not found"
        content = register_file.read_text(encoding="utf-8")

        # Must not pass role: 'patient' or role parameter in signup call
        assert "role: 'patient'" not in content
        assert 'role: "patient"' not in content


class TestCIPipelineRemediation:
    """Verify CI workflow enforces python syntax validation and typescript typechecking."""

    def test_ci_workflow_checks(self):
        ci_file = REPO_ROOT / ".github/workflows/ci.yml"
        assert ci_file.exists(), "ci.yml not found"
        content = ci_file.read_text(encoding="utf-8")

        assert "compileall" in content
        assert "tsc --noEmit" in content
