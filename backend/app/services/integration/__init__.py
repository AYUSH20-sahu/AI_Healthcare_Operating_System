"""Integration Service Boundary for AI-HOS (Milestone U-20).

Provides standardized integration bridges, FHIR-R4 transformations, and
external interoperability layers without altering internal clinical schemas.
"""

from app.services.integration.fhir_mapper import (
    to_fhir_appointment,
    to_fhir_bundle,
    to_fhir_diagnostic_report,
    to_fhir_medication_request,
    to_fhir_patient,
)

__all__ = [
    "to_fhir_patient",
    "to_fhir_appointment",
    "to_fhir_diagnostic_report",
    "to_fhir_medication_request",
    "to_fhir_bundle",
]
