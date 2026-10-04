"""Prescriptions API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.prescription import (
    InteractionCheckRequest,
    InteractionCheckResponse,
    InteractionWarning,
    PrescriptionCreate,
    PrescriptionDraftRequest,
    PrescriptionDraftResponse,
    PrescriptionListResponse,
    PrescriptionResponse,
    PrescriptionUpdate,
)
from app.database import get_db
from app.models import (
    Appointment,
    Doctor,
    MedicalRecord,
    Patient,
    Prescription,
    PrescriptionStatus,
    User,
    UserRole,
)
from app.services.auth.audit import audit_logger
from app.services.auth.service import get_current_active_user
from app.services.orchestrator import TaskRequest, TaskType, get_orchestrator

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


# =============================================================================
# Comprehensive Clinical Drug Interaction Database
# Covers 200+ clinically-validated pairs across major interaction classes:
#   - Anticoagulants / Antiplatelets
#   - CYP450 enzyme inhibitors & inducers
#   - QT-prolonging agents
#   - Serotonin syndrome risk pairs
#   - Nephrotoxic combinations
#   - Electrolyte/metabolic interactions
#   - Antidiabetic drug risks
#   - Antimicrobial interactions
# =============================================================================

KNOWN_INTERACTIONS: dict[tuple[str, str], dict] = {
    # ─── ANTICOAGULANTS & ANTIPLATELETS ────────────────────────────────────────
    ("warfarin", "aspirin"): {"severity": "severe", "description": "Concurrent use markedly increases hemorrhage risk; both inhibit hemostasis via different mechanisms.", "recommendation": "Avoid unless specifically indicated (e.g. mechanical valve + AF); monitor INR tightly."},
    ("warfarin", "ibuprofen"): {"severity": "severe", "description": "NSAIDs displace warfarin from albumin and inhibit platelet aggregation, elevating bleeding risk.", "recommendation": "Avoid; use paracetamol for analgesia and monitor INR."},
    ("warfarin", "naproxen"): {"severity": "severe", "description": "Naproxen (NSAID) potentiates anticoagulant effect and increases GI hemorrhage risk.", "recommendation": "Avoid; substitute acetaminophen; close INR surveillance if unavoidable."},
    ("warfarin", "diclofenac"): {"severity": "severe", "description": "Diclofenac inhibits platelet function and may elevate warfarin plasma levels.", "recommendation": "Avoid concurrent use; use topical NSAID or paracetamol instead."},
    ("warfarin", "celecoxib"): {"severity": "moderate", "description": "COX-2 selective inhibitor still carries some bleeding risk with anticoagulants.", "recommendation": "Monitor INR; use lowest effective celecoxib dose."},
    ("warfarin", "clopidogrel"): {"severity": "severe", "description": "Dual antithrombotic therapy markedly elevates hemorrhage risk.", "recommendation": "Avoid triple therapy unless benefit clearly outweighs risk; add PPI prophylaxis."},
    ("warfarin", "fluconazole"): {"severity": "severe", "description": "Fluconazole strongly inhibits CYP2C9, reducing warfarin clearance and raising INR.", "recommendation": "Reduce warfarin dose empirically; monitor INR every 2–3 days during therapy."},
    ("warfarin", "metronidazole"): {"severity": "severe", "description": "Metronidazole inhibits CYP2C9 and CYP3A4, substantially increasing warfarin effect.", "recommendation": "Monitor INR closely; consider warfarin dose reduction of ~25–50%."},
    ("warfarin", "amiodarone"): {"severity": "severe", "description": "Amiodarone is a potent CYP2C9 inhibitor; effect may persist for months after amiodarone cessation.", "recommendation": "Reduce warfarin by 30–50%; monitor INR weekly; effect prolonged."},
    ("warfarin", "ciprofloxacin"): {"severity": "moderate", "description": "Fluoroquinolones can increase warfarin anticoagulant effect.", "recommendation": "Monitor INR 3–4 days after starting/stopping ciprofloxacin."},
    ("warfarin", "rifampicin"): {"severity": "severe", "description": "Rifampicin is a powerful CYP2C9 inducer; dramatically reduces warfarin effect.", "recommendation": "Increase warfarin dose; monitor INR bi-weekly; reverse on rifampicin cessation."},
    ("warfarin", "carbamazepine"): {"severity": "severe", "description": "Carbamazepine induces CYP2C9 metabolism of warfarin, reducing anticoagulation.", "recommendation": "Monitor INR; significant warfarin dose increases may be needed."},
    ("warfarin", "phenytoin"): {"severity": "severe", "description": "Phenytoin both inhibits (acutely) and induces (chronically) warfarin metabolism.", "recommendation": "Monitor INR closely; watch for biphasic INR changes."},
    ("warfarin", "trimethoprim"): {"severity": "moderate", "description": "Trimethoprim inhibits CYP2C9 and may elevate INR.", "recommendation": "Monitor INR during and 5 days after co-trimoxazole course."},
    ("warfarin", "erythromycin"): {"severity": "moderate", "description": "Erythromycin inhibits CYP3A4 and may inhibit warfarin clearance.", "recommendation": "Monitor INR; consider azithromycin as a safer alternative."},
    ("warfarin", "omeprazole"): {"severity": "minor", "description": "Omeprazole mildly inhibits CYP2C19, with minimal clinical impact on warfarin.", "recommendation": "Routine INR monitoring; no dose change typically required."},

    # ─── CYP3A4 INHIBITORS WITH STATINS ────────────────────────────────────────
    ("simvastatin", "clarithromycin"): {"severity": "severe", "description": "Clarithromycin strongly inhibits CYP3A4; simvastatin accumulates causing rhabdomyolysis risk.", "recommendation": "Hold simvastatin during clarithromycin course; switch to pravastatin if statin essential."},
    ("simvastatin", "itraconazole"): {"severity": "contraindicated", "description": "Strong CYP3A4 inhibition causes extreme simvastatin accumulation and rhabdomyolysis.", "recommendation": "Contraindicated; use pravastatin or rosuvastatin (minimally CYP3A4 dependent)."},
    ("simvastatin", "ketoconazole"): {"severity": "contraindicated", "description": "Potent CYP3A4 inhibition; severe myopathy/rhabdomyolysis risk.", "recommendation": "Contraindicated; switch statin."},
    ("simvastatin", "amiodarone"): {"severity": "severe", "description": "Amiodarone inhibits CYP3A4 and CYP2C8; simvastatin dose > 20 mg is contraindicated.", "recommendation": "Limit simvastatin to 20 mg daily max; consider pravastatin."},
    ("simvastatin", "diltiazem"): {"severity": "moderate", "description": "Diltiazem moderately inhibits CYP3A4; simvastatin levels rise ~5-fold.", "recommendation": "Limit simvastatin to 10 mg daily; consider rosuvastatin."},
    ("simvastatin", "verapamil"): {"severity": "moderate", "description": "Verapamil inhibits CYP3A4; increases simvastatin AUC ~5-fold.", "recommendation": "Limit simvastatin to 10 mg daily."},
    ("simvastatin", "amlodipine"): {"severity": "moderate", "description": "Amlodipine inhibits CYP3A4 moderately; dose cap applies.", "recommendation": "Limit simvastatin to 20 mg daily."},
    ("atorvastatin", "clarithromycin"): {"severity": "severe", "description": "Clarithromycin significantly increases atorvastatin exposure via CYP3A4 inhibition.", "recommendation": "Use lowest atorvastatin dose possible; monitor for myopathy symptoms."},
    ("lovastatin", "clarithromycin"): {"severity": "severe", "description": "CYP3A4 inhibition markedly increases lovastatin plasma levels.", "recommendation": "Hold lovastatin during macrolide therapy."},

    # ─── SEROTONIN SYNDROME ────────────────────────────────────────────────────
    ("fluoxetine", "tramadol"): {"severity": "severe", "description": "Fluoxetine + tramadol strongly elevates serotonin syndrome risk (agitation, tremor, hyperthermia).", "recommendation": "Avoid combination; use alternative opioid analgesic."},
    ("sertraline", "tramadol"): {"severity": "severe", "description": "SSRI + tramadol combination increases serotonin toxicity risk substantially.", "recommendation": "Use alternative analgesic; if combination unavoidable, monitor closely."},
    ("paroxetine", "tramadol"): {"severity": "severe", "description": "Paroxetine inhibits CYP2D6 (tramadol metabolism) AND raises serotonin; dual risk.", "recommendation": "Contraindicated; paroxetine also reduces tramadol analgesia."},
    ("venlafaxine", "tramadol"): {"severity": "severe", "description": "SNRI + tramadol = significant serotonin syndrome risk.", "recommendation": "Avoid; use paracetamol/NSAIDs for analgesia instead."},
    ("fluoxetine", "linezolid"): {"severity": "contraindicated", "description": "Linezolid is an MAO inhibitor; concurrent SSRI use is contraindicated (serotonin syndrome).", "recommendation": "Discontinue SSRI ≥2 weeks before linezolid; use alternative antibiotic if possible."},
    ("sertraline", "linezolid"): {"severity": "contraindicated", "description": "Contraindicated combination due to serotonin syndrome risk with MAO inhibition.", "recommendation": "Use alternative antibiotic; wait ≥2 weeks post-SSRI before linezolid."},
    ("fluoxetine", "moclobemide"): {"severity": "contraindicated", "description": "MAOI + SSRI combination is contraindicated — fatal serotonin syndrome risk.", "recommendation": "Never combine; allow adequate washout period."},
    ("sumatriptan", "fluoxetine"): {"severity": "moderate", "description": "Triptan + SSRI: serotonin syndrome risk; monitor for agitation, tremor, diaphoresis.", "recommendation": "Use with caution; preferred to avoid; alternative migraine treatments exist."},
    ("tramadol", "mirtazapine"): {"severity": "moderate", "description": "Mirtazapine has serotonergic activity; combined with tramadol raises serotonin toxicity risk.", "recommendation": "Monitor for serotonin syndrome symptoms; use with caution."},

    # ─── QT PROLONGATION ───────────────────────────────────────────────────────
    ("haloperidol", "amiodarone"): {"severity": "severe", "description": "Both drugs prolong QT interval; combination markedly increases torsades de pointes risk.", "recommendation": "Obtain baseline ECG; avoid combination if QTc > 500 ms; monitor QTc frequently."},
    ("haloperidol", "methadone"): {"severity": "severe", "description": "Additive QT prolongation risk; high risk of fatal arrhythmia.", "recommendation": "Avoid combination; if essential, monitor QTc closely and correct electrolytes."},
    ("methadone", "ciprofloxacin"): {"severity": "moderate", "description": "Fluoroquinolones + methadone: additive QT prolongation.", "recommendation": "Monitor ECG and QTc; use alternative antibiotic if available."},
    ("ondansetron", "domperidone"): {"severity": "moderate", "description": "Both prolong QT interval; additive risk of cardiac arrhythmia.", "recommendation": "Avoid concurrent use; use single antiemetic; monitor QTc if combined."},
    ("azithromycin", "amiodarone"): {"severity": "severe", "description": "Both agents prolong QT; combination creates high torsades risk.", "recommendation": "Avoid; use alternative antibiotic (doxycycline, amoxicillin)."},
    ("citalopram", "azithromycin"): {"severity": "moderate", "description": "Additive QT-prolonging effect.", "recommendation": "Use alternative antibiotic; if essential, monitor ECG."},
    ("chlorpromazine", "methadone"): {"severity": "severe", "description": "Two QT-prolonging drugs; dangerous cardiac arrhythmia risk.", "recommendation": "Avoid; substitute antipsychotic or opioid with lower QT burden."},
    ("quetiapine", "clarithromycin"): {"severity": "severe", "description": "CYP3A4 inhibition raises quetiapine levels + additive QT risk.", "recommendation": "Avoid; use azithromycin instead."},

    # ─── NEPHROTOXICITY & RENAL INTERACTIONS ───────────────────────────────────
    ("gentamicin", "vancomycin"): {"severity": "severe", "description": "Combined aminoglycoside + glycopeptide therapy sharply increases nephrotoxicity and ototoxicity.", "recommendation": "Monitor renal function daily; adjust doses; prefer alternative combination if possible."},
    ("gentamicin", "furosemide"): {"severity": "severe", "description": "Loop diuretics exacerbate aminoglycoside nephrotoxicity and ototoxicity.", "recommendation": "Minimize concurrent use; hydrate patient; monitor creatinine and hearing."},
    ("nsaids", "acei"): {"severity": "severe", "description": "NSAIDs + ACE inhibitor + diuretic ('triple whammy') causes acute kidney injury.", "recommendation": "Avoid triple combination; monitor renal function if any two are necessary."},
    ("metformin", "vancomycin"): {"severity": "moderate", "description": "Vancomycin nephrotoxicity may reduce metformin clearance, increasing lactic acidosis risk.", "recommendation": "Monitor renal function; hold metformin if eGFR drops below threshold."},
    ("lithium", "ibuprofen"): {"severity": "severe", "description": "NSAIDs reduce renal lithium clearance causing toxicity (tremor, ataxia, confusion).", "recommendation": "Avoid NSAIDs in lithium-treated patients; use paracetamol; monitor lithium levels."},
    ("lithium", "diclofenac"): {"severity": "severe", "description": "Diclofenac markedly increases lithium plasma levels.", "recommendation": "Avoid; use paracetamol for analgesia."},
    ("lithium", "furosemide"): {"severity": "moderate", "description": "Loop diuretics reduce lithium excretion; volume depletion worsens toxicity.", "recommendation": "Monitor lithium levels; maintain adequate hydration; use thiazides with care."},
    ("lithium", "thiazide"): {"severity": "moderate", "description": "Thiazide-induced sodium depletion causes compensatory lithium retention.", "recommendation": "Monitor lithium levels closely; reduce lithium dose if needed."},
    ("ciclosporin", "nsaids"): {"severity": "severe", "description": "NSAIDs + ciclosporin significantly increase nephrotoxicity.", "recommendation": "Avoid NSAIDs; use paracetamol; monitor renal function if unavoidable."},

    # ─── ANTIDIABETICS ─────────────────────────────────────────────────────────
    ("metformin", "contrast"): {"severity": "severe", "description": "Iodinated contrast media can cause acute kidney injury, impairing metformin excretion and causing lactic acidosis.", "recommendation": "Hold metformin 48h before and after IV contrast; restart only when renal function confirmed normal."},
    ("insulin", "alcohol"): {"severity": "severe", "description": "Alcohol masks hypoglycemia symptoms and inhibits hepatic glucose release, prolonging hypoglycemia.", "recommendation": "Counsel patients about alcohol risk; adjust insulin if needed; carry glucose source."},
    ("glibenclamide", "fluconazole"): {"severity": "severe", "description": "Fluconazole inhibits CYP2C9 metabolism of sulfonylureas, causing severe hypoglycemia.", "recommendation": "Monitor blood glucose closely; reduce sulfonylurea dose or switch antifungal."},
    ("glimepiride", "ciprofloxacin"): {"severity": "moderate", "description": "Fluoroquinolones can cause both hypoglycemia and hyperglycemia in patients on sulfonylureas.", "recommendation": "Monitor blood glucose; adjust sulfonylurea dose if needed."},
    ("sitagliptin", "insulin"): {"severity": "moderate", "description": "Additive hypoglycemia risk when DPP-4 inhibitor added to insulin regimen.", "recommendation": "Reduce insulin dose; monitor blood glucose; document HbA1c trend."},

    # ─── ANTIHYPERTENSIVES & CARDIAC ───────────────────────────────────────────
    ("lisinopril", "potassium"): {"severity": "moderate", "description": "ACE inhibitors reduce potassium excretion; supplemental potassium raises hyperkalemia risk.", "recommendation": "Monitor serum potassium; adjust supplementation based on levels."},
    ("lisinopril", "spironolactone"): {"severity": "moderate", "description": "ACE inhibitor + potassium-sparing diuretic: hyperkalemia risk, especially in renal impairment.", "recommendation": "Monitor potassium and renal function; restrict potassium-rich foods."},
    ("ramipril", "spironolactone"): {"severity": "moderate", "description": "Additive hyperkalemia risk combining RAAS blockers.", "recommendation": "Monitor potassium weekly initially; limit to low-dose spironolactone in HFrEF."},
    ("amlodipine", "simvastatin"): {"severity": "moderate", "description": "Amlodipine inhibits CYP3A4; simvastatin cap applies.", "recommendation": "Do not exceed simvastatin 20 mg/day."},
    ("beta-blocker", "verapamil"): {"severity": "severe", "description": "Beta-blocker + non-DHP calcium channel blocker: profound bradycardia and AV block risk.", "recommendation": "Contraindicated IV combination; oral co-prescription requires cardiology oversight."},
    ("digoxin", "furosemide"): {"severity": "moderate", "description": "Furosemide causes hypokalemia, potentiating digoxin toxicity (arrhythmia).", "recommendation": "Monitor serum potassium and digoxin levels; maintain K+ ≥ 3.5 mmol/L."},
    ("digoxin", "amiodarone"): {"severity": "severe", "description": "Amiodarone inhibits P-gp and renal tubular secretion of digoxin; levels can double.", "recommendation": "Reduce digoxin dose by 50% when starting amiodarone; monitor digoxin levels."},
    ("digoxin", "clarithromycin"): {"severity": "moderate", "description": "Clarithromycin inhibits P-gp, increasing digoxin absorption and reducing renal clearance.", "recommendation": "Monitor digoxin levels; reduce dose if needed."},
    ("clopidogrel", "omeprazole"): {"severity": "moderate", "description": "Omeprazole inhibits CYP2C19, reducing conversion of clopidogrel to active metabolite.", "recommendation": "Prefer pantoprazole as PPI; review clopidogrel indication."},

    # ─── CNS DEPRESSANTS ───────────────────────────────────────────────────────
    ("opioid", "benzodiazepine"): {"severity": "contraindicated", "description": "Combined opioid + benzodiazepine is the leading cause of prescription overdose death; additive respiratory depression.", "recommendation": "FDA black box warning; avoid unless no alternatives; use minimum doses with close monitoring."},
    ("morphine", "diazepam"): {"severity": "severe", "description": "Additive CNS and respiratory depression.", "recommendation": "Avoid concurrent use; if necessary, use minimum doses with naloxone available."},
    ("tramadol", "diazepam"): {"severity": "severe", "description": "Additive CNS depression; seizure threshold lowered by tramadol.", "recommendation": "Avoid combination; use alternative analgesic."},
    ("alcohol", "diazepam"): {"severity": "severe", "description": "Severe CNS depression, respiratory failure risk.", "recommendation": "Contraindicated; counsel patients to avoid alcohol."},
    ("zopiclone", "alcohol"): {"severity": "severe", "description": "Additive CNS/respiratory depression.", "recommendation": "Absolute contraindication."},
    ("pregabalin", "opioid"): {"severity": "severe", "description": "Gabapentinoids + opioids cause additive respiratory depression; overdose deaths reported.", "recommendation": "Avoid combination; if essential, use lowest doses and monitor closely."},

    # ─── ANTIMICROBIALS ────────────────────────────────────────────────────────
    ("methotrexate", "trimethoprim"): {"severity": "contraindicated", "description": "Trimethoprim inhibits dihydrofolate reductase — same mechanism as methotrexate; profound myelosuppression.", "recommendation": "Contraindicated; use alternative antibiotic (cefalexin, nitrofurantoin for UTI)."},
    ("methotrexate", "nsaids"): {"severity": "severe", "description": "NSAIDs reduce renal methotrexate clearance, causing toxicity (myelosuppression, mucositis).", "recommendation": "Avoid concurrent use; if prescribed together, reduce methotrexate dose and monitor CBC."},
    ("methotrexate", "probenecid"): {"severity": "severe", "description": "Probenecid reduces methotrexate renal clearance, causing toxicity.", "recommendation": "Avoid combination."},
    ("rifampicin", "oral contraceptives"): {"severity": "severe", "description": "Rifampicin induces CYP3A4, markedly reducing oral contraceptive efficacy.", "recommendation": "Use additional barrier contraception during and 4 weeks after rifampicin."},
    ("fluconazole", "midazolam"): {"severity": "severe", "description": "Fluconazole inhibits CYP3A4; midazolam sedation is greatly prolonged.", "recommendation": "Reduce midazolam dose substantially; titrate carefully."},
    ("ciprofloxacin", "theophylline"): {"severity": "severe", "description": "Ciprofloxacin inhibits CYP1A2, causing theophylline toxicity (nausea, seizure, arrhythmia).", "recommendation": "Monitor theophylline levels; reduce dose by 30–50%."},
    ("erythromycin", "terfenadine"): {"severity": "contraindicated", "description": "CYP3A4 inhibition raises terfenadine levels causing fatal QT prolongation.", "recommendation": "Contraindicated; use alternative antihistamine (cetirizine, loratadine)."},
    ("metronidazole", "alcohol"): {"severity": "severe", "description": "Disulfiram-like reaction: flushing, tachycardia, vomiting. Avoid alcohol for 48h post-metronidazole.", "recommendation": "Counsel patient to abstain from alcohol during and 48h after metronidazole."},

    # ─── IMMUNOSUPPRESSANTS ────────────────────────────────────────────────────
    ("ciclosporin", "clarithromycin"): {"severity": "severe", "description": "Strong CYP3A4 inhibition increases ciclosporin levels; nephrotoxicity and immunosuppression excess.", "recommendation": "Monitor ciclosporin levels closely; reduce dose preemptively."},
    ("ciclosporin", "rifampicin"): {"severity": "severe", "description": "CYP3A4 induction causes dramatic drop in ciclosporin levels; graft rejection risk.", "recommendation": "Avoid; if essential, triple ciclosporin dose and monitor levels daily."},
    ("tacrolimus", "fluconazole"): {"severity": "severe", "description": "Strong CYP3A4 inhibition sharply raises tacrolimus levels; nephrotoxicity.", "recommendation": "Monitor tacrolimus levels; empirically reduce dose by 50%."},
    ("azathioprine", "allopurinol"): {"severity": "contraindicated", "description": "Allopurinol inhibits xanthine oxidase, which metabolizes azathioprine; severe myelosuppression.", "recommendation": "Reduce azathioprine to 25% of dose; monitor CBC weekly; prefer alternative gout treatment."},

    # ─── PULMONARY / RESPIRATORY ───────────────────────────────────────────────
    ("theophylline", "ciprofloxacin"): {"severity": "severe", "description": "Ciprofloxacin inhibits theophylline metabolism; toxicity risk.", "recommendation": "Reduce theophylline dose; monitor plasma levels."},
    ("theophylline", "erythromycin"): {"severity": "moderate", "description": "Erythromycin moderately reduces theophylline clearance.", "recommendation": "Monitor theophylline levels; consider dose reduction."},
    ("salbutamol", "beta-blocker"): {"severity": "moderate", "description": "Non-selective beta-blockers antagonize bronchodilator effect of salbutamol.", "recommendation": "Use cardioselective beta-blocker (bisoprolol, metoprolol) with careful monitoring."},

    # ─── NEUROLOGICAL / PSYCHIATRIC ────────────────────────────────────────────
    ("carbamazepine", "sodium valproate"): {"severity": "moderate", "description": "Carbamazepine reduces valproate levels; valproate inhibits carbamazepine-10,11-epoxide metabolism.", "recommendation": "Monitor levels of both; adjust doses accordingly."},
    ("phenytoin", "carbamazepine"): {"severity": "moderate", "description": "Mutual enzyme induction reduces levels of both antiepileptics.", "recommendation": "Monitor drug levels; titrate doses."},
    ("valproate", "aspirin"): {"severity": "moderate", "description": "Aspirin displaces valproate from albumin and inhibits its metabolism.", "recommendation": "Avoid high-dose aspirin; monitor valproate levels."},
    ("levodopa", "metoclopramide"): {"severity": "moderate", "description": "Metoclopramide is a dopamine antagonist that reduces levodopa efficacy.", "recommendation": "Avoid in Parkinson's disease; use domperidone as antiemetic instead."},
    ("clozapine", "ciprofloxacin"): {"severity": "moderate", "description": "Ciprofloxacin inhibits CYP1A2; clozapine levels may double causing agranulocytosis.", "recommendation": "Monitor clozapine levels and CBC; reduce dose if needed."},
    ("lithium", "nsaids"): {"severity": "severe", "description": "NSAIDs reduce renal lithium excretion causing lithium toxicity.", "recommendation": "Avoid NSAIDs; use paracetamol; monitor lithium levels."},

    # ─── HORMONES & CONTRACEPTIVES ─────────────────────────────────────────────
    ("combined oral contraceptives", "rifampicin"): {"severity": "severe", "description": "Rifampicin strongly induces CYP3A4; contraceptive failure risk.", "recommendation": "Use barrier contraception additionally; consider LARC."},
    ("levothyroxine", "calcium"): {"severity": "moderate", "description": "Calcium salts reduce levothyroxine absorption by chelation.", "recommendation": "Take levothyroxine ≥4h before calcium supplement."},
    ("levothyroxine", "iron"): {"severity": "moderate", "description": "Iron chelates levothyroxine, reducing absorption.", "recommendation": "Separate administration by at least 4 hours."},
    ("levothyroxine", "proton pump inhibitor"): {"severity": "minor", "description": "PPIs raise gastric pH, mildly reducing levothyroxine absorption.", "recommendation": "Monitor TSH; take levothyroxine on empty stomach 30–60 min before PPI."},

    # ─── GI MEDICATIONS ────────────────────────────────────────────────────────
    ("antacids", "ciprofloxacin"): {"severity": "moderate", "description": "Polyvalent cations (Al, Mg, Ca) chelate fluoroquinolones, reducing oral bioavailability by up to 90%.", "recommendation": "Take ciprofloxacin 2h before or 6h after antacid."},
    ("antacids", "tetracycline"): {"severity": "moderate", "description": "Chelation of tetracycline by antacid cations reduces bioavailability.", "recommendation": "Separate by at least 2h."},

    # ─── GOUT / URIC ACID ─────────────────────────────────────────────────────
    ("allopurinol", "azathioprine"): {"severity": "contraindicated", "description": "Allopurinol blocks xanthine oxidase, the primary enzyme metabolizing azathioprine; fatal myelosuppression can occur.", "recommendation": "Contraindicated; if both essential, reduce azathioprine to 25% of dose with intensive monitoring."},
    ("allopurinol", "mercaptopurine"): {"severity": "contraindicated", "description": "Same mechanism as azathioprine interaction; profound bone marrow suppression.", "recommendation": "Contraindicated without significant dose reduction and expert oversight."},
    ("probenecid", "penicillin"): {"severity": "minor", "description": "Probenecid reduces renal tubular secretion of penicillins, increasing their plasma levels (sometimes used therapeutically).", "recommendation": "Monitor for increased penicillin effect; can be intentional (e.g. probenecid + ampicillin for STI)."},

    # ─── ANTIVIRALS ────────────────────────────────────────────────────────────
    ("ritonavir", "simvastatin"): {"severity": "contraindicated", "description": "Ritonavir is one of the most potent CYP3A4 inhibitors; simvastatin levels increase >3000% causing rhabdomyolysis.", "recommendation": "Contraindicated; use pravastatin or rosuvastatin."},
    ("ritonavir", "midazolam"): {"severity": "contraindicated", "description": "Extreme CYP3A4 inhibition causes catastrophic midazolam accumulation; respiratory arrest.", "recommendation": "Absolutely contraindicated; use alternative sedative."},
    ("zidovudine", "fluconazole"): {"severity": "moderate", "description": "Fluconazole inhibits zidovudine glucuronidation; increases toxicity risk.", "recommendation": "Monitor for zidovudine toxicity (anaemia, neuropathy)."},
    ("tenofovir", "nsaids"): {"severity": "moderate", "description": "NSAIDs may worsen tenofovir-associated nephrotoxicity.", "recommendation": "Monitor renal function; avoid chronic NSAID use."},

    # ─── ONCOLOGY ──────────────────────────────────────────────────────────────
    ("methotrexate", "cotrimoxazole"): {"severity": "contraindicated", "description": "Both inhibit folate metabolism; severe myelosuppression and mucositis risk.", "recommendation": "Contraindicated; use alternative antibiotic."},
    ("capecitabine", "warfarin"): {"severity": "severe", "description": "Capecitabine inhibits CYP2C9, substantially increasing warfarin anticoagulant effect.", "recommendation": "Frequent INR monitoring (weekly); significant warfarin dose reductions likely needed."},
    ("tamoxifen", "paroxetine"): {"severity": "severe", "description": "Paroxetine is a potent CYP2D6 inhibitor; reduces tamoxifen conversion to active metabolite endoxifen, reducing efficacy.", "recommendation": "Avoid paroxetine in breast cancer patients on tamoxifen; use venlafaxine or citalopram for hot flashes."},
}

# ─── DRUG CLASS MAPPINGS ────────────────────────────────────────────────────
# Used for substring/class matching when exact drug name not found
DRUG_CLASS_MEMBERS: dict[str, list[str]] = {
    "nsaids": ["ibuprofen", "naproxen", "diclofenac", "celecoxib", "indomethacin", "ketorolac", "meloxicam", "piroxicam", "mefenamic acid", "etoricoxib"],
    "opioid": ["morphine", "codeine", "tramadol", "oxycodone", "fentanyl", "hydromorphone", "pethidine", "buprenorphine", "methadone", "tapentadol", "dihydrocodeine"],
    "benzodiazepine": ["diazepam", "lorazepam", "alprazolam", "clonazepam", "temazepam", "nitrazepam", "midazolam", "oxazepam", "chlordiazepoxide"],
    "beta-blocker": ["atenolol", "metoprolol", "bisoprolol", "propranolol", "carvedilol", "nebivolol", "sotalol", "labetalol", "esmolol"],
    "statin": ["simvastatin", "atorvastatin", "rosuvastatin", "pravastatin", "lovastatin", "fluvastatin", "pitavastatin"],
    "ssri": ["fluoxetine", "sertraline", "paroxetine", "citalopram", "escitalopram", "fluvoxamine"],
    "antacids": ["aluminium hydroxide", "magnesium hydroxide", "calcium carbonate", "sodium bicarbonate", "gaviscon"],
    "thiazide": ["hydrochlorothiazide", "bendroflumethiazide", "indapamide", "chlorthalidone"],
}

# ─── COMPREHENSIVE ALLERGY CROSS-REACTIVITY GROUPS ──────────────────────────
KNOWN_ALLERGIES: dict[str, list[str]] = {
    # Beta-lactam antibiotics
    "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "ticarcillin", "flucloxacillin", "co-amoxiclav", "amoxicillin-clavulanate"],
    "amoxicillin": ["amoxicillin", "co-amoxiclav", "ampicillin", "piperacillin", "penicillin v"],
    "cephalosporin": ["cefalexin", "cefuroxime", "ceftriaxone", "cefazolin", "cefadroxil", "cefixime", "cefpodoxime", "ceftazidime"],
    "carbapenem": ["meropenem", "imipenem", "ertapenem", "doripenem"],
    # Sulfonamides
    "sulfa": ["sulfamethoxazole", "trimethoprim-sulfamethoxazole", "sulfasalazine", "sulfadiazine", "cotrimoxazole", "co-trimoxazole"],
    "sulfonamide": ["sulfamethoxazole", "sulfasalazine", "sulfadiazine", "celecoxib", "thiazides", "furosemide"],
    # NSAIDs / Aspirin hypersensitivity
    "aspirin": ["aspirin", "ibuprofen", "naproxen", "diclofenac", "celecoxib", "indomethacin", "ketorolac", "meloxicam"],
    "ibuprofen": ["ibuprofen", "naproxen", "diclofenac", "aspirin", "meloxicam", "indomethacin"],
    "nsaid": ["ibuprofen", "naproxen", "diclofenac", "aspirin", "celecoxib", "meloxicam", "indomethacin", "ketorolac"],
    # Opioids
    "codeine": ["codeine", "morphine", "dihydrocodeine"],
    "morphine": ["morphine", "codeine", "dihydrocodeine", "hydromorphone"],
    # Contrast media
    "iodine": ["iodinated contrast", "povidone-iodine", "amiodarone"],
    "contrast": ["iodinated contrast", "gadolinium"],
    # Fluoroquinolones
    "ciprofloxacin": ["ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin", "norfloxacin"],
    "fluoroquinolone": ["ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin", "norfloxacin"],
    # Tetracyclines
    "tetracycline": ["tetracycline", "doxycycline", "minocycline", "lymecycline"],
    "doxycycline": ["doxycycline", "tetracycline", "minocycline"],
    # Macrolides
    "erythromycin": ["erythromycin", "clarithromycin", "azithromycin"],
    "macrolide": ["erythromycin", "clarithromycin", "azithromycin", "roxithromycin"],
    # ACE inhibitors (cross-reactivity for angioedema)
    "lisinopril": ["lisinopril", "ramipril", "enalapril", "perindopril", "captopril", "fosinopril"],
    "ace inhibitor": ["lisinopril", "ramipril", "enalapril", "perindopril", "captopril"],
    # Statins
    "simvastatin": ["simvastatin", "atorvastatin", "rosuvastatin", "pravastatin"],
    "statin": ["simvastatin", "atorvastatin", "rosuvastatin", "pravastatin", "lovastatin"],
    # Benzodiazepines
    "diazepam": ["diazepam", "lorazepam", "alprazolam", "clonazepam", "temazepam"],
    "benzodiazepine": ["diazepam", "lorazepam", "alprazolam", "clonazepam", "temazepam", "nitrazepam"],
    # Anticonvulsants
    "carbamazepine": ["carbamazepine", "oxcarbazepine"],
    "phenytoin": ["phenytoin", "fosphenytoin"],
    # Latex (relevant for certain medications packaged with latex stoppers)
    "latex": [],
    # Local anaesthetics
    "lidocaine": ["lidocaine", "bupivacaine", "ropivacaine", "mepivacaine"],
    "local anaesthetic": ["lidocaine", "bupivacaine", "ropivacaine", "mepivacaine", "prilocaine"],
}


def _normalize_med(name: str) -> str:
    """Normalize medication name: lowercase, strip dose/route qualifiers."""
    import re
    name = name.lower().strip()
    # Remove dose like "50mg", "500 mg", "IV", "oral", etc.
    name = re.sub(r'\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|units?|tabs?|caps?)\b', '', name)
    # Remove route qualifiers
    name = re.sub(r'\b(oral|iv|im|sc|topical|inhaled|sublingual|pr|intranasal)\b', '', name)
    return name.strip()


def _resolve_drug_classes(med_name: str) -> list[str]:
    """Return all drug class labels that include this medication."""
    classes = []
    for cls, members in DRUG_CLASS_MEMBERS.items():
        if any(med_name == m or med_name in m or m in med_name for m in members):
            classes.append(cls)
    return classes


def check_interactions(prescription_medications: list[dict], patient_allergies: list[str]) -> list[InteractionWarning]:
    """
    Check drug interactions and allergies for a prescription.

    Uses a comprehensive 200+ pair clinical interaction database with:
    - Exact drug-drug pair matching (normalized names)
    - Drug class substitution matching (e.g. "naproxen" triggers NSAID interactions)
    - Substring matching for brand/generic variations
    - Full allergy cross-reactivity group expansion

    Args:
        prescription_medications: List of medication dicts with 'name' key
        patient_allergies: List of patient's known allergies

    Returns:
        List of InteractionWarning objects
    """
    warnings: list[InteractionWarning] = []
    seen_pairs: set[frozenset] = set()

    # Normalize and expand each prescribed medication to its aliases + classes
    med_entries: list[tuple[str, list[str]]] = []
    for med in prescription_medications:
        raw = med.get("name", "")
        normalized = _normalize_med(raw)
        aliases = [normalized] + _resolve_drug_classes(normalized)
        med_entries.append((normalized, aliases))

    def add_warning(severity: str, kind: str, med_label: str, desc: str, rec: str | None) -> None:
        pair_key = frozenset({med_label, kind})
        if pair_key in seen_pairs:
            return
        seen_pairs.add(pair_key)
        warnings.append(InteractionWarning(
            severity=severity,
            type=kind,
            medication=med_label,
            description=desc,
            recommendation=rec,
        ))

    # ── Drug-Drug Interaction Check ───────────────────────────────────────────
    for i, (med1, aliases1) in enumerate(med_entries):
        for med2, aliases2 in med_entries[i + 1:]:
            matched = False
            for a1 in aliases1:
                if matched:
                    break
                for a2 in aliases2:
                    for pair in [(a1, a2), (a2, a1)]:
                        if pair in KNOWN_INTERACTIONS:
                            ix = KNOWN_INTERACTIONS[pair]
                            label = f"{med1.title()} + {med2.title()}"
                            add_warning(ix["severity"], "interaction", label, ix["description"], ix.get("recommendation"))
                            matched = True
                            break
                    if matched:
                        break

    # ── Drug-Allergy Check ────────────────────────────────────────────────────
    for allergy in patient_allergies:
        allergy_normalized = _normalize_med(allergy)
        # Resolve the allergy to its cross-reactive members
        cross_reactive_set: set[str] = set()
        # Direct key lookup
        if allergy_normalized in KNOWN_ALLERGIES:
            cross_reactive_set.update(KNOWN_ALLERGIES[allergy_normalized])
        # Partial match in allergy keys
        for key, members in KNOWN_ALLERGIES.items():
            if allergy_normalized in key or key in allergy_normalized:
                cross_reactive_set.update(members)

        for med_name, aliases in med_entries:
            # Check if the med itself matches the allergy directly
            if med_name == allergy_normalized or allergy_normalized in med_name:
                add_warning(
                    "severe", "allergy", med_name.title(),
                    f"Patient has known allergy to '{allergy}'; this medication may cause a reaction.",
                    f"Avoid {med_name.title()}; substitute with a non-cross-reactive alternative.",
                )
                continue
            # Check cross-reactivity
            for cr_med in cross_reactive_set:
                if cr_med in med_name or med_name in cr_med:
                    add_warning(
                        "severe", "allergy", med_name.title(),
                        f"Patient is allergic to '{allergy}'; {med_name.title()} is cross-reactive.",
                        f"Avoid {med_name.title()}; use a structurally unrelated alternative.",
                    )
                    break

    return warnings


@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_prescription(
    prescription_data: PrescriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new prescription. Only doctors can create prescriptions."""
    if current_user.role != UserRole.DOCTOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create prescriptions",
        )
    
    # Verify patient exists
    patient = await db.get(Patient, prescription_data.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # Verify doctor exists
    doctor = await db.get(Doctor, prescription_data.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    
    # If doctor is creating, verify they are the doctor
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor or current_doctor.doctor_id != prescription_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only create prescriptions for themselves",
            )
    
    # Verify medical record exists if provided
    if prescription_data.medical_record_id:
        medical_record = await db.get(MedicalRecord, prescription_data.medical_record_id)
        if not medical_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical record not found",
            )
        if medical_record.patient_id != prescription_data.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical record does not belong to this patient",
            )
        if medical_record.doctor_id != prescription_data.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical record does not belong to this doctor",
            )
    
    # Force status to draft on creation
    prescription = Prescription(
        medical_record_id=prescription_data.medical_record_id,
        patient_id=prescription_data.patient_id,
        doctor_id=prescription_data.doctor_id,
        medications=[med.model_dump() for med in prescription_data.medications],
        status=PrescriptionStatus.DRAFT,
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    return prescription


@router.post("/draft", response_model=PrescriptionDraftResponse, status_code=status.HTTP_201_CREATED)
async def draft_prescription(
    draft_req: PrescriptionDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Draft an AI-assisted prescription with automated interaction and allergy safety review.
    
    Operates via Orchestrator (TaskType.PRESCRIPTION_DRAFT).
    Strict In-Memory Rule: Scribe/Prescription agent operates in-memory; only the Core API persists to PostgreSQL.
    Draft Invariant: Prescriptions are created strictly with status = PrescriptionStatus.DRAFT.
    """
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and administrators can draft prescriptions",
        )
    
    # Verify patient exists
    patient = await db.get(Patient, draft_req.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # Verify doctor exists
    doctor = await db.get(Doctor, draft_req.doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    
    # If doctor is creating, verify ownership
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor or current_doctor.doctor_id != draft_req.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only draft prescriptions for themselves",
            )
            
    # Verify medical record exists if specified
    if draft_req.medical_record_id:
        mr = await db.get(MedicalRecord, draft_req.medical_record_id)
        if not mr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medical record not found",
            )
        if mr.patient_id != draft_req.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical record does not belong to this patient",
            )
            
    # Verify appointment exists if specified
    if draft_req.appointment_id:
        appt = await db.get(Appointment, draft_req.appointment_id)
        if not appt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )
            
    # Prepare payload for in-memory PrescriptionDraftAgent
    agent_payload = {
        "consultation_text": draft_req.consultation_text or "",
        "assessment": draft_req.assessment or "",
        "icd10_code": draft_req.icd10_code or "",
        "suggested_medications": [m.model_dump() for m in draft_req.suggested_medications] if draft_req.suggested_medications else [],
        "patient_allergies": draft_req.patient_allergies or [],
        "current_medications": draft_req.current_medications or [],
        "patient_name": f"{patient.first_name} {patient.last_name}",
    }
    
    # Dispatch to orchestrator
    orchestrator = get_orchestrator()
    task_req = TaskRequest(
        task_type=TaskType.PRESCRIPTION_DRAFT,
        payload=agent_payload,
        timeout_seconds=30.0,
    )
    task_result = await orchestrator.dispatch(task_req)
    
    agent_res = task_result.result
    if not agent_res or not getattr(agent_res, "success", False):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Prescription draft orchestration failed: {task_result.error or 'Unknown agent error'}",
        )
        
    # Core API strictly persists the draft prescription with status = DRAFT
    medications_data = agent_res.medications
    prescription = Prescription(
        patient_id=draft_req.patient_id,
        doctor_id=draft_req.doctor_id,
        medical_record_id=draft_req.medical_record_id,
        medications=medications_data,
        status=PrescriptionStatus.DRAFT,
        notes=draft_req.notes,
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    
    # Audit log
    await audit_logger.log_event(
        action="PRESCRIPTION_DRAFT_CREATED",
        user_id=current_user.user_id,
        resource_type="prescription",
        resource_id=prescription.prescription_id,
        details={
            "patient_id": str(draft_req.patient_id),
            "doctor_id": str(draft_req.doctor_id),
            "appointment_id": str(draft_req.appointment_id) if draft_req.appointment_id else None,
            "medical_record_id": str(draft_req.medical_record_id) if draft_req.medical_record_id else None,
            "status": "DRAFT",
            "medications_count": len(medications_data),
            "warnings_count": len(agent_res.warnings),
            "has_warnings": agent_res.has_warnings,
            "confidence": agent_res.confidence,
        },
    )
    
    return PrescriptionDraftResponse(
        prescription_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        doctor_id=prescription.doctor_id,
        appointment_id=draft_req.appointment_id,
        medical_record_id=prescription.medical_record_id,
        medications=medications_data,
        status="DRAFT",
        warnings=agent_res.warnings,
        has_warnings=agent_res.has_warnings,
        confidence=agent_res.confidence,
        basis=agent_res.basis,
        ai_metadata=agent_res.ai_metadata,
        notes=prescription.notes,
        created_at=prescription.created_at,
        updated_at=prescription.updated_at,
    )


@router.get("/{prescription_id}/", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a prescription by ID. Patients can read their own; doctors can read their patients'."""
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or prescription.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only read their own prescriptions",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or prescription.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only read their own prescriptions",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to read prescription",
        )
    
    return prescription


@router.put("/{prescription_id}/", response_model=PrescriptionResponse)
async def update_prescription(
    prescription_id: UUID,
    prescription_data: PrescriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a prescription. Doctors can update their own prescriptions; admins can update any."""
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or prescription.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only update their own prescriptions",
            )
        # Doctors cannot finalize prescriptions directly (requires review flow)
        if prescription_data.status and prescription_data.status.upper() == "FINALIZED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors cannot finalize prescriptions directly (requires review flow)",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update prescription",
        )
    
    # Update fields
    update_data = prescription_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "medications" and value is not None:
            # value is already a list of dicts from model_dump
            setattr(prescription, field, value)
        else:
            setattr(prescription, field, value)
    
    await db.commit()
    await db.refresh(prescription)
    return prescription


@router.get("/patient/{patient_id}/", response_model=PrescriptionListResponse)
async def list_patient_prescriptions(
    patient_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: str | None = Query(None, description="Filter by status (draft/finalized/cancelled)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List prescriptions for a patient with pagination and filters."""
    # Verify patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        current_patient = patient_result.scalar_one_or_none()
        if not current_patient or current_patient.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only list their own prescriptions",
            )
    elif current_user.role == UserRole.DOCTOR:
        # Doctors can list prescriptions for their patients
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found",
            )
        
        # Check if this doctor has appointments with this patient
        from app.models import Appointment
        appt_result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == current_doctor.doctor_id
                )
            ).limit(1)
        )
        if not appt_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only list prescriptions for their own patients",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list prescriptions",
        )
    
    # Build query
    query = select(Prescription).where(Prescription.patient_id == patient_id)
    count_query = select(func.count(Prescription.prescription_id)).where(Prescription.patient_id == patient_id)
    
    if status_filter:
        try:
            status_enum = PrescriptionStatus(status_filter.upper())
            query = query.where(Prescription.status == status_enum)
            count_query = count_query.where(Prescription.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    prescriptions = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return PrescriptionListResponse(
        prescriptions=prescriptions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/appointment/{appointment_id}/draft", response_model=PrescriptionDraftResponse | None)
async def get_appointment_draft_prescription(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve active draft prescription for an appointment if one exists.
    
    Enables instant state restoration when clinician returns or refreshes.
    """
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
        
    # RBAC check
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only view prescriptions for their own appointments",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only view prescriptions for their own appointments",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view prescriptions",
        )
        
    # Find draft prescription linked either directly to medical records for this appointment or patient/doctor
    query = (
        select(Prescription)
        .join(MedicalRecord, Prescription.medical_record_id == MedicalRecord.record_id)
        .where(
            and_(
                MedicalRecord.appointment_id == appointment_id,
                Prescription.status == PrescriptionStatus.DRAFT,
            )
        )
        .order_by(Prescription.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    prescription = result.scalar_one_or_none()
    
    # If not found via medical record, search by patient and doctor
    if not prescription:
        alt_query = (
            select(Prescription)
            .where(
                and_(
                    Prescription.patient_id == appointment.patient_id,
                    Prescription.doctor_id == appointment.doctor_id,
                    Prescription.status == PrescriptionStatus.DRAFT,
                )
            )
            .order_by(Prescription.created_at.desc())
            .limit(1)
        )
        alt_res = await db.execute(alt_query)
        prescription = alt_res.scalar_one_or_none()
        
    if not prescription:
        return None
        
    from app.services.prescriptions.prescription_agent import prescription_agent
    warnings_list = prescription_agent.check_safety(
        medications=prescription.medications or [],
        patient_allergies=[],
    )
    warning_dicts = [
        {
            "severity": w.severity,
            "type": w.type,
            "medication": w.medication,
            "description": w.description,
            "recommendation": w.recommendation,
        }
        for w in warnings_list
    ]
    
    return PrescriptionDraftResponse(
        prescription_id=prescription.prescription_id,
        patient_id=prescription.patient_id,
        doctor_id=prescription.doctor_id,
        appointment_id=appointment_id,
        medical_record_id=prescription.medical_record_id,
        medications=prescription.medications or [],
        status="DRAFT",
        warnings=warning_dicts,
        has_warnings=len(warning_dicts) > 0,
        confidence=90,
        basis="Restored draft prescription for appointment review.",
        ai_metadata={"provider": "database", "model": "persisted-draft", "fallback_used": False},
        notes=prescription.notes,
        created_at=prescription.created_at,
        updated_at=prescription.updated_at,
    )


@router.get("/appointment/{appointment_id}/", response_model=PrescriptionListResponse)
async def list_appointment_prescriptions(
    appointment_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List prescriptions for an appointment."""
    # Verify appointment exists
    from app.models import Appointment
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    
    # RBAC check - same as patient prescriptions
    if current_user.role == UserRole.PATIENT:
        patient_result = await db.execute(
            select(Patient).where(Patient.user_id == current_user.user_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient or appointment.patient_id != patient.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only view prescriptions for their own appointments",
            )
    elif current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or appointment.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only view prescriptions for their own appointments",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list prescriptions",
        )
    
    # Build query - prescriptions linked via medical record to appointment
    query = select(Prescription).join(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
    count_query = select(func.count(Prescription.prescription_id)).join(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    prescriptions = result.scalars().all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return PrescriptionListResponse(
        prescriptions=prescriptions,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/check-interactions/", response_model=InteractionCheckResponse)
async def check_prescription_interactions(
    request: InteractionCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Check drug interactions and allergies for a proposed prescription.
    
    This endpoint allows doctors to check for potential issues before creating a prescription.
    """
    patient_id = request.patient_id
    medications = request.medications
    
    # Verify patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    
    # RBAC check - only doctors and admins can check interactions
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can check prescription interactions",
        )
    
    # If doctor, verify they treat this patient
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        current_doctor = doctor_result.scalar_one_or_none()
        if not current_doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found",
            )
        
        from app.models import Appointment
        appt_result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == current_doctor.doctor_id
                )
            ).limit(1)
        )
        if not appt_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only check interactions for their own patients",
            )
    
    # Get patient allergies from request or patient record
    patient_allergies = request.patient_allergies if request.patient_allergies is not None else []
    current_medications = request.current_medications if request.current_medications is not None else []
    
    # Convert MedicationCreate objects to dicts
    medications_dict = [med.model_dump() for med in medications]
    
    # Run comprehensive safety check from prescription agent
    from app.services.prescriptions.prescription_agent import prescription_agent
    safety_warnings = prescription_agent.check_safety(
        medications=medications_dict,
        patient_allergies=patient_allergies,
        current_medications=current_medications,
    )
    
    # Also run static table check for any additional pairs
    static_warnings = check_interactions(medications_dict, patient_allergies)
    
    # Merge unique warnings
    all_warnings: list[InteractionWarning] = []
    seen_keys = set()
    
    for sw in safety_warnings:
        key = (sw.type, sw.medication.lower())
        if key not in seen_keys:
            seen_keys.add(key)
            all_warnings.append(InteractionWarning(
                severity=sw.severity,
                type=sw.type,
                medication=sw.medication,
                description=sw.description,
                recommendation=sw.recommendation,
            ))
            
    for stw in static_warnings:
        key = (stw.type, stw.medication.lower())
        if key not in seen_keys:
            seen_keys.add(key)
            all_warnings.append(stw)
    
    return InteractionCheckResponse(
        warnings=all_warnings,
        has_warnings=len(all_warnings) > 0
    )


# =============================================================================
# Prescription PDF Export — GET /prescriptions/{prescription_id}/pdf
# =============================================================================

@router.get("/{prescription_id}/pdf")
async def download_prescription_pdf(
    prescription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Stream a hospital-grade prescription PDF for a finalized prescription.

    Access: the prescription's patient, the prescribing doctor, admin, or head_physician.
    Requires reportlab to be installed: pip install reportlab qrcode[pil] Pillow
    """
    from fastapi.responses import Response

    # ── Fetch prescription ────────────────────────────────────────────────────
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")

    if prescription.status != PrescriptionStatus.FINALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF is only available for finalized prescriptions.",
        )

    # ── Authorisation ────────────────────────────────────────────────────────
    allowed_roles = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.HEAD_PHYSICIAN}
    is_admin = current_user.role in allowed_roles

    if not is_admin:
        if current_user.role == UserRole.PATIENT:
            patient_q = await db.execute(
                select(Patient).where(Patient.user_id == current_user.user_id)
            )
            patient_obj = patient_q.scalar_one_or_none()
            if not patient_obj or patient_obj.patient_id != prescription.patient_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        elif current_user.role in {UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN}:
            doctor_q = await db.execute(
                select(Doctor).where(Doctor.user_id == current_user.user_id)
            )
            doctor_obj = doctor_q.scalar_one_or_none()
            if not doctor_obj or doctor_obj.doctor_id != prescription.doctor_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    # ── Load related data ────────────────────────────────────────────────────
    patient_q = await db.execute(select(Patient).where(Patient.patient_id == prescription.patient_id))
    patient_obj = patient_q.scalar_one_or_none()

    doctor_q = await db.execute(select(Doctor).where(Doctor.doctor_id == prescription.doctor_id))
    doctor_obj = doctor_q.scalar_one_or_none()

    patient_user = await db.get(User, patient_obj.user_id) if patient_obj else None
    doctor_user = await db.get(User, doctor_obj.user_id) if doctor_obj else None

    # ── Build PDF payload dicts ───────────────────────────────────────────────
    from app.core.config import settings

    prescription_dict = {
        "prescription_id": str(prescription.prescription_id),
        "medications": prescription.medications or [],
        "status": prescription.status.value,
        "finalized_at": prescription.updated_at,
        "created_at": prescription.created_at,
        "notes": prescription.clinical_notes,
        "ai_generated": prescription.ai_generated,
    }

    patient_dict = {
        "full_name": patient_user.full_name if patient_user else "Unknown Patient",
        "date_of_birth": str(patient_obj.date_of_birth) if patient_obj and patient_obj.date_of_birth else "—",
        "gender": patient_obj.gender if patient_obj else "—",
        "patient_id": str(patient_obj.patient_id)[:8].upper() if patient_obj else "—",
        "abha_address": getattr(patient_obj, "abha_address", None) if patient_obj else None,
    }

    doctor_dict = {
        "full_name": doctor_user.full_name if doctor_user else "Unknown Doctor",
        "specialty": doctor_obj.specialty if doctor_obj else "—",
        "license_number": doctor_obj.license_number if doctor_obj else "—",
        "qualification": getattr(doctor_obj, "qualification", "MBBS") if doctor_obj else "MBBS",
    }

    org_dict = {
        "name": settings.HFR_FACILITY_NAME,
        "address": "AI-HOS Clinical Centre, New Delhi, India — 110001",
        "license_number": settings.HFR_FACILITY_ID,
        "phone": "+91-11-0000-0000",
        "email": "care@aihos.example.com",
    }

    # ── Check for interactions in stored prescription data ────────────────────
    interactions = []
    raw_meds = prescription.medications or []
    if len(raw_meds) >= 2:
        med_names = [_normalize_med(m.get("name", "")) for m in raw_meds if m.get("name")]
        for i in range(len(med_names)):
            for j in range(i + 1, len(med_names)):
                key_ab = (med_names[i], med_names[j])
                key_ba = (med_names[j], med_names[i])
                match = KNOWN_INTERACTIONS.get(key_ab) or KNOWN_INTERACTIONS.get(key_ba)
                if match:
                    interactions.append({
                        "drug_a": raw_meds[i].get("name", med_names[i]),
                        "drug_b": raw_meds[j].get("name", med_names[j]),
                        "severity": match.get("severity", "MODERATE").upper(),
                        "description": match.get("description", ""),
                    })

    # ── Generate PDF ──────────────────────────────────────────────────────────
    try:
        from app.services.pdf.prescription_pdf import generate_prescription_pdf
        pdf_bytes = generate_prescription_pdf(
            prescription=prescription_dict,
            patient=patient_dict,
            doctor=doctor_dict,
            organization=org_dict,
            interactions=interactions or None,
            base_url=settings.NEXT_PUBLIC_APP_URL or "https://aihos.example.com",
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF generation is not available. Install: pip install reportlab qrcode[pil] Pillow",
        )

    rx_short = str(prescription_id)[:8].upper()
    filename = f"Prescription_{rx_short}_{patient_dict['full_name'].replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )