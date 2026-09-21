"""
Prescription PDF Generator for AI-HOS.

Generates a hospital-grade prescription PDF using reportlab with:
- Hospital letterhead
- Patient & doctor info blocks
- Medications table with dosage/route/frequency
- Drug interaction warnings
- QR code for prescription verification
- Digital approval stamp
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

# reportlab imports — install: pip install reportlab qrcode[pil] Pillow
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False


# ─── Brand palette ────────────────────────────────────────────────────────────
BRAND_BLUE = colors.HexColor("#1E40AF")       # deep blue
BRAND_LIGHT = colors.HexColor("#EFF6FF")      # light blue bg
BRAND_ACCENT = colors.HexColor("#3B82F6")     # medium blue
GRAY_700 = colors.HexColor("#374151")
GRAY_400 = colors.HexColor("#9CA3AF")
RED_600 = colors.HexColor("#DC2626")
GREEN_700 = colors.HexColor("#15803D")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _qr_image(data: str, size_px: int = 80) -> Image | None:
    """Generate a QR code image flowable. Returns None if qrcode/Pillow not installed."""
    if not HAS_QR:
        return None
    try:
        qr = qrcode.QRCode(version=1, box_size=3, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return Image(buf, width=size_px, height=size_px)
    except Exception:
        # Silently return None if qrcode or Pillow is not properly installed.
        # The PDF will still generate — just without the QR code block.
        return None


def _style(name: str, **kwargs) -> ParagraphStyle:
    base = getSampleStyleSheet()["Normal"]
    return ParagraphStyle(name, parent=base, **kwargs)


# ─── Main generator ───────────────────────────────────────────────────────────

def generate_prescription_pdf(
    prescription: dict[str, Any],
    patient: dict[str, Any],
    doctor: dict[str, Any],
    organization: dict[str, Any],
    interactions: list[dict[str, Any]] | None = None,
    base_url: str = "https://aihos.example.com",
) -> bytes:
    """
    Generate a prescription PDF and return the raw bytes.

    Args:
        prescription: Dict with keys: prescription_id, medications (list), status,
                      finalized_at, notes, ai_generated
        patient: Dict with keys: full_name, date_of_birth, gender, patient_id, abha_address
        doctor: Dict with keys: full_name, specialty, license_number, qualification
        organization: Dict with keys: name, address, license_number, phone, email
        interactions: Optional list of drug interaction warnings
        base_url: Base URL for the QR verification link

    Returns:
        PDF bytes
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f"Prescription — {patient.get('full_name', 'Patient')}",
        author=f"Dr. {doctor.get('full_name', '')}",
    )

    story = []
    W = A4[0] - 4 * cm  # usable width

    # ── 1. Header: Hospital letterhead ───────────────────────────────────────
    header_data = [
        [
            Paragraph(
                f"<font color='#{BRAND_BLUE.hexval()[1:]}' size='18'><b>{organization.get('name', 'AI-HOS Clinical Centre')}</b></font>",
                _style("OrgName"),
            ),
            Paragraph(
                f"<font size='8' color='#374151'>"
                f"{organization.get('address', '')}<br/>"
                f"Tel: {organization.get('phone', '')} | {organization.get('email', '')}<br/>"
                f"License: {organization.get('license_number', '')}"
                f"</font>",
                _style("OrgAddr", alignment=TA_RIGHT),
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[W * 0.55, W * 0.45])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=6))

    # "PRESCRIPTION" title strip
    story.append(Paragraph(
        "<font size='13' color='#1E40AF'><b>MEDICAL PRESCRIPTION</b></font>",
        _style("Title", alignment=TA_CENTER),
    ))
    story.append(Spacer(1, 4 * mm))

    # ── 2. Patient & Doctor info side by side ─────────────────────────────────
    rx_id = str(prescription.get("prescription_id", ""))[:8].upper()
    fin_at = prescription.get("finalized_at") or prescription.get("created_at") or ""
    if fin_at:
        try:
            fin_at = datetime.fromisoformat(str(fin_at)).strftime("%d %b %Y, %I:%M %p")
        except Exception:
            pass

    patient_block = (
        f"<b>Patient</b><br/>"
        f"<b>Name:</b> {patient.get('full_name', '—')}<br/>"
        f"<b>DOB:</b> {patient.get('date_of_birth', '—')} &nbsp; "
        f"<b>Gender:</b> {patient.get('gender', '—')}<br/>"
        f"<b>UHID:</b> {patient.get('patient_id', '—')}<br/>"
        f"<b>ABHA:</b> {patient.get('abha_address') or 'Not linked'}"
    )

    doctor_block = (
        f"<b>Prescribing Physician</b><br/>"
        f"<b>Dr. {doctor.get('full_name', '—')}</b><br/>"
        f"{doctor.get('qualification', '')} | {doctor.get('specialty', '')}<br/>"
        f"Reg. No.: {doctor.get('license_number', '—')}<br/>"
        f"Date: {fin_at}"
    )

    info_style = _style("InfoStyle", fontSize=8.5, leading=13)
    info_table = Table(
        [[Paragraph(patient_block, info_style), Paragraph(doctor_block, info_style)]],
        colWidths=[W * 0.5, W * 0.5],
    )
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("BOX", (0, 0), (0, 0), 0.5, BRAND_ACCENT),
        ("BOX", (1, 0), (1, 0), 0.5, BRAND_ACCENT),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BRAND_ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5 * mm))

    # ── 3. Prescription ID + AI flag ─────────────────────────────────────────
    ai_flag = " &nbsp; <font color='#7C3AED'>[AI-Assisted Draft — Doctor Approved]</font>" if prescription.get("ai_generated") else ""
    story.append(Paragraph(
        f"<b>Prescription Ref:</b> <font color='#1E40AF'>{rx_id}</font>{ai_flag}",
        _style("RefLine", fontSize=8.5),
    ))
    story.append(Spacer(1, 3 * mm))

    # ── 4. Medications Table ─────────────────────────────────────────────────
    story.append(Paragraph("<b>Medications</b>", _style("SecHead", fontSize=10, textColor=BRAND_BLUE)))
    story.append(Spacer(1, 2 * mm))

    meds = prescription.get("medications") or []
    if meds:
        med_headers = ["#", "Drug / Formulation", "Dose", "Route", "Frequency", "Duration", "Instructions"]
        med_col_w = [0.04, 0.26, 0.08, 0.10, 0.14, 0.10, 0.28]
        med_col_w_abs = [W * w for w in med_col_w]

        header_row = [Paragraph(f"<b>{h}</b>", _style(f"MH{i}", fontSize=8, textColor=colors.white)) for i, h in enumerate(med_headers)]
        med_rows = [header_row]

        for idx, m in enumerate(meds):
            row = [
                Paragraph(str(idx + 1), _style("MC", fontSize=8, alignment=TA_CENTER)),
                Paragraph(f"<b>{m.get('name', '—')}</b>", _style("MN", fontSize=8)),
                Paragraph(str(m.get("dose", "—")), _style("MD", fontSize=8, alignment=TA_CENTER)),
                Paragraph(str(m.get("route", "—")), _style("MR", fontSize=8)),
                Paragraph(str(m.get("frequency", "—")), _style("MF", fontSize=8)),
                Paragraph(str(m.get("duration", "—")), _style("MDu", fontSize=8)),
                Paragraph(str(m.get("instructions", "As directed")), _style("MI", fontSize=8)),
            ]
            med_rows.append(row)

        med_table = Table(med_rows, colWidths=med_col_w_abs, repeatRows=1)
        med_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.4, GRAY_400),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(med_table)
    else:
        story.append(Paragraph("No medications listed.", _style("NoMed", fontSize=9, textColor=GRAY_400)))

    story.append(Spacer(1, 4 * mm))

    # ── 5. Clinical Notes ─────────────────────────────────────────────────────
    notes = prescription.get("notes") or prescription.get("clinical_notes") or ""
    if notes:
        story.append(Paragraph("<b>Clinical Notes</b>", _style("SecHead2", fontSize=10, textColor=BRAND_BLUE)))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(str(notes), _style("Notes", fontSize=9, leading=14, textColor=GRAY_700)))
        story.append(Spacer(1, 4 * mm))

    # ── 6. Drug Interaction Warnings ─────────────────────────────────────────
    if interactions:
        story.append(HRFlowable(width="100%", thickness=0.5, color=RED_600, spaceAfter=3))
        story.append(Paragraph(
            "<font color='#DC2626'><b>⚠ Drug Interaction Warnings</b></font>",
            _style("WarnHead", fontSize=9),
        ))
        for ix in interactions:
            severity = ix.get("severity", "MODERATE")
            sev_color = "#DC2626" if severity in ("CONTRAINDICATED", "MAJOR") else "#D97706"
            story.append(Paragraph(
                f"<font color='{sev_color}'><b>[{severity}]</b></font> "
                f"{ix.get('drug_a', '')} ↔ {ix.get('drug_b', '')}: {ix.get('description', '')}",
                _style(f"Warn{severity}", fontSize=8.5, leading=13, textColor=GRAY_700),
            ))
        story.append(Spacer(1, 3 * mm))

    # ── 7. QR Code + Footer ───────────────────────────────────────────────────
    verify_url = f"{base_url}/verify/rx/{rx_id}"
    qr_img = _qr_image(verify_url, size_px=70)

    footer_text = (
        f"<font size='7.5' color='#6B7280'>"
        f"This prescription was digitally approved via <b>AI-HOS</b> | Prescription ID: {rx_id}<br/>"
        f"Verification URL: {verify_url}<br/>"
        f"For queries contact {organization.get('phone', '')} | {organization.get('email', '')}<br/>"
        f"<b>This document is computer-generated and valid without physical signature.</b>"
        f"</font>"
    )

    if qr_img:
        footer_data = [[qr_img, Paragraph(footer_text, _style("Footer", fontSize=7.5, leading=11))]]
        footer_table = Table(footer_data, colWidths=[80, W - 80])
        footer_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (1, 0), (1, 0), 8),
        ]))
    else:
        footer_table = Paragraph(footer_text, _style("Footer2", fontSize=7.5, leading=11))

    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_400, spaceBefore=6, spaceAfter=6))
    story.append(footer_table)

    doc.build(story)
    return buf.getvalue()
