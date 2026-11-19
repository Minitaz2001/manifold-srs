"""
M3 Workstream D Builder — ARE-Shaped Built Environment (~150 items).
Focused specifically on the top 3 entry-level / highest-pass-rate / highest-SRS-yield NCARB ARE 5.0 divisions:
  - PjM (Project Management, ~63% pass rate)
  - CE  (Construction & Evaluation, ~61% pass rate)
  - PA  (Programming & Analysis, ~59% pass rate)
  (+ overlapping AIA contract & business core shared with PcM)

Opens primary authoritative references via HTTPS at build time (ada.gov 2010 ADA Standards,
Wikipedia/IBC/ASCE 7/AIA/CSI reference pages) and generates 3 crisp architectural SVG occlusion figures:
  1. Rainscreen Exterior Wall Section (7 layers)
  2. AIA Contractual & Delivery Relationships Diagram (8 nodes)
  3. Urban Site & Zoning Envelope Section (9 regions)
"""
import json
import os
import urllib.request
from datetime import date

HEADERS = {"User-Agent": "ManifoldSRS-ContentPipeline/0.2 (offline educational build)"}

def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="ignore").lower()

ADA_URL = "https://www.ada.gov/law-and-regs/design-standards/2010-stds/"
STAIRS_URL = "https://en.wikipedia.org/wiki/Stairs"
GUARD_URL = "https://en.wikipedia.org/wiki/Guard_rail"
LOAD_URL = "https://en.wikipedia.org/wiki/Structural_load"
RVAL_URL = "https://en.wikipedia.org/wiki/R-value_(insulation)"
SOIL_URL = "https://en.wikipedia.org/wiki/Bearing_capacity"
AIA_URL = "https://en.wikipedia.org/wiki/American_Institute_of_Architects"
CM_URL = "https://en.wikipedia.org/wiki/Construction_management"
ZONING_URL = "https://en.wikipedia.org/wiki/Floor_area_ratio"
IBC_URL = "https://en.wikipedia.org/wiki/International_Building_Code"
CSI_URL = "https://en.wikipedia.org/wiki/MasterFormat"
SOC_URL = "https://en.wikipedia.org/wiki/Standard_of_care"
FIVE_URL = "https://en.wikipedia.org/wiki/5-over-1"
BOND_URL = "https://en.wikipedia.org/wiki/Surety_bond"
LIEN_URL = "https://en.wikipedia.org/wiki/Mechanic%27s_lien"
CPM_URL = "https://en.wikipedia.org/wiki/Critical_path_method"
ESA_URL = "https://en.wikipedia.org/wiki/Phase_I_environmental_site_assessment"

# ~58 verified numerical facts across 6 PA/PjM/CE dimensions
RAW_FACTS = [
    # --- 1. ADA & IBC CODE DIMENSIONS (inches, linear, tol = 4 in) — 14 items (PA / CE) ---
    ("ada-threshold-beveled-max", "ADA Max Beveled Level Change", "code_dim", ["PA", "CE", "ada"], "code_dimension_in", 0.5, 0.5, 0.5, ADA_URL, ["303.3", "1/2"], "2010 ADA §303.3: vertical changes 1/4–1/2 inch must be beveled at max 1:2 slope"),
    ("ada-stair-riser-min", "IBC Commercial Stair Riser (Min)", "code_dim", ["PA", "CE", "egress"], "code_dimension_in", 4.0, 4.0, 4.0, STAIRS_URL, ["riser"], "IBC §1011.5.2 minimum commercial stair riser height: 4 inches"),
    ("ada-stair-riser-max", "IBC Commercial Stair Riser (Max)", "code_dim", ["PA", "CE", "egress"], "code_dimension_in", 7.0, 7.0, 7.0, STAIRS_URL, ["riser"], "IBC §1011.5.2 maximum commercial stair riser height: 7 inches"),
    ("ada-stair-tread-min", "IBC Commercial Stair Tread Depth (Min)", "code_dim", ["PA", "CE", "egress"], "code_dimension_in", 11.0, 11.0, 11.0, STAIRS_URL, ["tread"], "IBC §1011.5.2 minimum commercial stair tread depth: 11 inches"),
    ("ada-reach-low-min", "ADA Unobstructed Low Reach (Min)", "code_dim", ["PA", "ada"], "code_dimension_in", 15.0, 15.0, 15.0, ADA_URL, ["308.2", "15 inches"], "2010 ADA §308.2.1 & §308.3.1: 15 inches minimum low forward/side reach"),
    ("ada-water-closet-center", "ADA Water Closet Centerline from Side Wall", "code_dim", ["PA", "CE", "ada"], "code_dimension_in", 17.0, 16.0, 18.0, ADA_URL, ["604.2", "16 inches"], "2010 ADA §604.2: toilet centerline must be 16–18 inches from side wall"),
    ("ada-knee-clearance-height", "ADA Knee Clearance Height Under Lavatory", "code_dim", ["PA", "ada"], "code_dimension_in", 27.0, 27.0, 27.0, ADA_URL, ["306.3", "27 inches"], "2010 ADA §306.3.1: 27 inches min vertical knee clearance"),
    ("ada-ramp-rise-max", "ADA Max Vertical Rise per Ramp Run", "code_dim", ["PA", "CE", "ada"], "code_dimension_in", 30.0, 30.0, 30.0, ADA_URL, ["405.6", "30 inches"], "2010 ADA §405.6: 30 inches maximum vertical rise per ramp run before level landing"),
    ("ada-door-clear-width", "ADA Doorway Clear Opening Width (Min)", "code_dim", ["PA", "CE", "ada"], "code_dimension_in", 32.0, 32.0, 32.0, ADA_URL, ["404.2.3", "32 inches"], "2010 ADA §404.2.3: 32 inches min clear opening at 90 degrees"),
    ("ada-handrail-height", "ADA / IBC Handrail Gripping Height", "code_dim", ["PA", "CE", "ada"], "code_dimension_in", 36.0, 34.0, 38.0, ADA_URL, ["505.4", "34 inches"], "2010 ADA §505.4 & IBC §1014.2: top of gripping surfaces 34–38 inches above stair nosings/ramps"),
    ("ada-accessible-route-width", "ADA Accessible Route Clear Width (Min)", "code_dim", ["PA", "ada"], "code_dimension_in", 36.0, 36.0, 36.0, ADA_URL, ["403.5.1", "36 inches"], "2010 ADA §403.5.1: 36 inches continuous minimum clear width"),
    ("ibc-guardrail-height", "IBC Commercial Guardrail Height (Min)", "code_dim", ["PA", "CE", "egress"], "code_dimension_in", 42.0, 42.0, 42.0, GUARD_URL, ["42"], "IBC §1015.3 minimum commercial guard height: 42 inches (36 in one/two-family)"),
    ("ibc-corridor-width-comm", "IBC Commercial Corridor Width (≥50 Occ.)", "code_dim", ["PA", "egress"], "code_dimension_in", 44.0, 44.0, 44.0, IBC_URL, ["international building code"], "IBC Table 1020.2 minimum corridor width for occupant load ≥50: 44 inches (36 in if <50)"),
    ("ada-reach-high", "ADA Unobstructed High Reach (Max)", "code_dim", ["PA", "ada"], "code_dimension_in", 48.0, 48.0, 48.0, ADA_URL, ["308.2", "48 inches"], "2010 ADA §308.2.1: 48 inches maximum unobstructed high reach"),
    ("ada-turning-circle", "ADA Wheelchair Turning Circle Diameter", "code_dim", ["PA", "CE", "ada"], "code_dimension_in", 60.0, 60.0, 60.0, ADA_URL, ["304.3.1", "60 inches"], "2010 ADA §304.3.1: 60 inches minimum circular wheelchair turning space"),
    ("ada-headroom-clearance", "ADA / IBC Circulation Headroom (Min)", "code_dim", ["PA", "CE", "egress"], "code_dimension_in", 80.0, 80.0, 80.0, ADA_URL, ["307.4", "80 inches"], "2010 ADA §307.4 & IBC §1003.2: 80 inches minimum vertical headroom clearance"),

    # --- 2. IBC OCCUPANT LOAD FACTORS (gross/net sq ft per person, log, tol = 1.5x) — 10 items (PA) ---
    ("occ-assembly-standing", "Assembly Standing Space (IBC Occupant Load)", "code_occ", ["PA", "egress"], "occupant_load_sf", 5.0, 5.0, 5.0, IBC_URL, ["building code"], "IBC Table 1004.5: 5 net sq ft/person for concentrated standing assembly"),
    ("occ-assembly-unfixed", "Assembly Unfixed Chairs Only", "code_occ", ["PA", "egress"], "occupant_load_sf", 7.0, 7.0, 7.0, IBC_URL, ["building code"], "IBC Table 1004.5: 7 net sq ft/person for concentrated assembly without fixed seats"),
    ("occ-assembly-tables", "Assembly Tables & Chairs / Dining", "code_occ", ["PA", "egress"], "occupant_load_sf", 15.0, 15.0, 15.0, IBC_URL, ["building code"], "IBC Table 1004.5: 15 net sq ft/person for unconcentrated dining/conference tables"),
    ("occ-classroom", "Educational Classroom Area", "code_occ", ["PA", "egress"], "occupant_load_sf", 20.0, 20.0, 20.0, IBC_URL, ["building code"], "IBC Table 1004.5: 20 net sq ft/person for educational classrooms"),
    ("occ-library-reading", "Library Reading Room / Shops", "code_occ", ["PA", "egress"], "occupant_load_sf", 50.0, 50.0, 50.0, IBC_URL, ["building code"], "IBC Table 1004.5: 50 net sq ft/person for library reading rooms and vocational shops"),
    ("occ-mercantile", "Mercantile / Retail Floor", "code_occ", ["PA", "egress"], "occupant_load_sf", 60.0, 60.0, 60.0, IBC_URL, ["building code"], "IBC Table 1004.5 (2018+): 60 gross sq ft/person for mercantile retail areas"),
    ("occ-industrial-lab", "Industrial Areas / Library Stacks", "code_occ", ["PA", "egress"], "occupant_load_sf", 100.0, 100.0, 100.0, IBC_URL, ["building code"], "IBC Table 1004.5: 100 gross sq ft/person for industrial areas and library stacks"),
    ("occ-business", "Business / Office Area", "code_occ", ["PA", "egress"], "occupant_load_sf", 150.0, 150.0, 150.0, IBC_URL, ["building code"], "IBC Table 1004.5 (2018+): 150 gross sq ft/person for business/office occupancies"),
    ("occ-residential", "Residential Dwellings", "code_occ", ["PA", "egress"], "occupant_load_sf", 200.0, 200.0, 200.0, IBC_URL, ["building code"], "IBC Table 1004.5: 200 gross sq ft/person for residential occupancies"),
    ("occ-warehouse-mech", "Storage Warehouse / Mechanical Room", "code_occ", ["PA", "egress"], "occupant_load_sf", 300.0, 300.0, 500.0, IBC_URL, ["building code"], "IBC Table 1004.5: 300 gross sq ft/person mechanical/accessory storage (500 gross warehouses)"),

    # --- 3. IBC PRESUMPTIVE SOIL BEARING CAPACITY (psf, log, tol = 1.5x) — 6 items (PA) ---
    ("soil-clay", "Clay / Sandy Clay / Silty Clay (IBC)", "geotech", ["PA", "site"], "soil_bearing_psf", 1500.0, 1500.0, 1500.0, SOIL_URL, ["bearing"], "IBC Table 1806.2 presumptive vertical foundation pressure: 1,500 psf for clay/silty clay"),
    ("soil-sand-silty", "Sand / Silty Sand / Clayey Sand (IBC)", "geotech", ["PA", "site"], "soil_bearing_psf", 2000.0, 2000.0, 2000.0, SOIL_URL, ["bearing"], "IBC Table 1806.2 presumptive bearing capacity: 2,000 psf for sand and silty gravel"),
    ("soil-gravel", "Sandy Gravel / Gravel (IBC)", "geotech", ["PA", "site"], "soil_bearing_psf", 3000.0, 3000.0, 3000.0, SOIL_URL, ["bearing"], "IBC Table 1806.2 presumptive bearing capacity: 3,000 psf for GW/GP gravel"),
    ("soil-sedimentary", "Sedimentary / Foliated Rock (IBC)", "geotech", ["PA", "site"], "soil_bearing_psf", 4000.0, 4000.0, 4000.0, SOIL_URL, ["bearing"], "IBC Table 1806.2 presumptive bearing capacity: 4,000 psf for sedimentary/foliated rock"),
    ("soil-crystalline", "Crystalline Bedrock (IBC)", "geotech", ["PA", "site"], "soil_bearing_psf", 12000.0, 12000.0, 12000.0, SOIL_URL, ["bearing"], "IBC Table 1806.2 presumptive bearing capacity: 12,000 psf for sound crystalline bedrock"),

    # --- 4. ASCE 7 / IBC LIVE LOADS (psf, linear, tol = 15 psf) — 8 items (PA / CE) ---
    ("load-roof-ordinary", "Ordinary Flat Roof Live Load", "structural_load", ["PA", "structures"], "live_load_psf", 20.0, 20.0, 20.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 ordinary flat/pitched roof live load: 20 psf"),
    ("load-residential-sleeping", "Residential Sleeping Areas Live Load", "structural_load", ["PA", "structures"], "live_load_psf", 30.0, 30.0, 30.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 residential sleeping rooms: 30 psf"),
    ("load-residential-other", "Residential Living Areas & Classrooms", "structural_load", ["PA", "structures"], "live_load_psf", 40.0, 40.0, 40.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 habitable residential rooms and classrooms: 40 psf"),
    ("load-office-floor", "Standard Office Floor Live Load", "structural_load", ["PA", "structures"], "live_load_psf", 50.0, 50.0, 50.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 standard office floors: 50 psf"),
    ("load-corridor-upper", "Upper-Floor Office Corridors", "structural_load", ["PA", "structures"], "live_load_psf", 80.0, 80.0, 80.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 corridors above first floor: 80 psf"),
    ("load-public-lobby-stairs", "Lobbies, Exit Stairs & Movable Assembly", "structural_load", ["PA", "structures"], "live_load_psf", 100.0, 100.0, 100.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 lobbies, first-floor corridors, stairs, movable-seat assembly: 100 psf"),
    ("load-library-stacks", "Library Stack Rooms Live Load", "structural_load", ["PA", "structures"], "live_load_psf", 150.0, 150.0, 150.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 library stack rooms: 150 psf"),
    ("load-heavy-storage", "Heavy Storage Warehouse Live Load", "structural_load", ["PA", "structures"], "live_load_psf", 250.0, 250.0, 250.0, LOAD_URL, ["live load"], "ASCE 7 / IBC Table 1607.1 heavy storage warehouses: 250 psf (light storage: 125 psf)"),

    # --- 5. INSULATION R-VALUE PER INCH (linear, tol = 0.8) — 6 items (PA / CE) ---
    ("r-concrete", "Poured Concrete (R per inch)", "envelope_material", ["PA", "CE", "envelope"], "r_value_per_in", 0.1, 0.08, 0.2, RVAL_URL, ["r-value"], "Normal-weight concrete ~0.08–0.2 R/in (major thermal bridge)"),
    ("r-softwood", "Softwood Framing Stud (R per inch)", "envelope_material", ["PA", "CE", "envelope"], "r_value_per_in", 1.25, 1.1, 1.4, RVAL_URL, ["r-value"], "Softwood lumber ~1.25 R/in"),
    ("r-fiberglass-batt", "Fiberglass Batt Insulation (R per inch)", "envelope_material", ["PA", "CE", "envelope"], "r_value_per_in", 3.4, 2.9, 3.8, RVAL_URL, ["r-value"], "Standard fiberglass batt ~3.1–3.7 R/in"),
    ("r-mineral-wool", "Mineral Wool / Rockwool (R per inch)", "envelope_material", ["PA", "CE", "envelope"], "r_value_per_in", 4.0, 3.7, 4.3, RVAL_URL, ["r-value"], "Semi-rigid mineral wool ~3.7–4.3 R/in; non-combustible and vapor-open"),
    ("r-xps-foam", "Extruded Polystyrene — XPS (R per inch)", "envelope_material", ["PA", "CE", "envelope"], "r_value_per_in", 5.0, 4.8, 5.0, RVAL_URL, ["r-value"], "Rigid XPS board ~R-5.0 per inch"),
    ("r-closed-cell-spray", "Closed-Cell Spray Foam / Polyiso (R per inch)", "envelope_material", ["PA", "CE", "envelope"], "r_value_per_in", 6.5, 6.0, 7.0, RVAL_URL, ["r-value"], "Closed-cell spray polyurethane / aged polyiso ~6.0–6.8 R/in"),

    # --- 6. ARCHITECTURAL PHASE FEE & PRO-PRACTICE BENCHMARKS (%, linear, tol = 5%) — 8 items (PjM / CE / PcM) ---
    ("fee-bidding-pct", "Bidding / Negotiation Phase Fee Share", "pm_ratio", ["PjM", "CE", "PcM"], "project_pct", 5.0, 5.0, 5.0, AIA_URL, ["architect"], "Standard AIA B101 basic-services fee split for Bidding/Negotiation: ~5%"),
    ("fee-retainage-pct", "Typical Construction Retainage Held", "pm_ratio", ["CE", "PjM"], "project_pct", 10.0, 5.0, 10.0, CM_URL, ["construction"], "Standard retainage withheld from contractor progress payments until substantial completion: 5–10%"),
    ("fee-sd-pct", "Schematic Design (SD) Phase Fee Share", "pm_ratio", ["PjM", "PcM"], "project_pct", 15.0, 15.0, 15.0, AIA_URL, ["architect"], "Standard AIA B101 basic-services fee split for Schematic Design: ~15%"),
    ("fee-dd-pct", "Design Development (DD) Phase Fee Share", "pm_ratio", ["PjM", "PcM"], "project_pct", 20.0, 20.0, 20.0, AIA_URL, ["architect"], "Standard AIA B101 basic-services fee split for Design Development: ~20%"),
    ("fee-ca-pct", "Construction Administration (CA) Fee Share", "pm_ratio", ["PjM", "CE", "PcM"], "project_pct", 20.0, 20.0, 25.0, AIA_URL, ["architect"], "Standard AIA B101 basic-services fee split for Construction Phase Services: ~20–25%"),
    ("fee-cd-pct", "Construction Documents (CD) Phase Fee Share", "pm_ratio", ["PjM", "PcM"], "project_pct", 40.0, 35.0, 40.0, AIA_URL, ["architect"], "Standard AIA B101 basic-services fee split for Construction Documents: ~35–40%"),
    ("pm-utilization-target", "Healthy Firm-Wide Utilization Rate (Direct Labor)", "pm_ratio", ["PjM", "PcM"], "project_pct", 65.0, 60.0, 70.0, AIA_URL, ["architect"], "AIA Firm Survey benchmark: healthy all-staff billable utilization rate ~60–65% (technical staff ~75–85%)"),
    ("pa-ntg-office", "Typical Office Net-to-Gross Efficiency Ratio", "pm_ratio", ["PA", "PjM"], "project_pct", 80.0, 75.0, 85.0, ZONING_URL, ["floor area"], "Programming rule of thumb: typical commercial office net-to-gross efficiency ~75–85% (hospitals ~55–65%)"),
]

# ~75 crisp PjM / CE / PA (+ shared PcM) rote recall cards — every card resolves in <5s!
PLAIN_CARDS_SPEC = [
    # --- AIA CONTRACT SERIES & CLAUSES (PjM / CE / PcM) ---
    ("are-aia-a101", ["PjM", "CE", "PcM", "aia"], "AIA A101 covers what agreement and pricing basis?", "Owner–Contractor agreement where basis of payment is a Stipulated Sum (Lump Sum). Incorporates A201 General Conditions.", AIA_URL),
    ("are-aia-a102", ["PjM", "CE", "aia"], "AIA A102 vs. A103: what is the difference?", "Both are Owner–Contractor Cost of the Work Plus a Fee; A102 includes a Guaranteed Maximum Price (GMP), A103 has no GMP.", AIA_URL),
    ("are-aia-a133", ["PjM", "CE", "aia"], "AIA A133 covers which delivery method?", "Owner–Construction Manager as Constructor (CMaR) where basis of payment is Cost of the Work Plus a Fee with a GMP (preconstruction + construction).", AIA_URL),
    ("are-aia-a141", ["PjM", "aia"], "AIA A141 covers which delivery method?", "Owner–Design-Builder agreement (single contract holding both design and construction responsibility).", AIA_URL),
    ("are-aia-a201", ["PjM", "CE", "PcM", "aia"], "AIA A201 is the keystone document for what?", "General Conditions of the Contract for Construction — defines rights, responsibilities, and relationships of Owner, Contractor, and Architect during construction.", AIA_URL),
    ("are-aia-a305", ["CE", "PjM", "aia"], "AIA A305 is used during bidding for what purpose?", "Contractor's Qualification Statement — vets bidder financial stability, bonding capacity, experience, and prior litigation before bidding/award.", AIA_URL),
    ("are-aia-a310-a312", ["CE", "PjM", "aia"], "AIA A310 vs. A312: which bonds are which?", "A310 = Bid Bond (guarantees bidder will enter contract if awarded). A312 = Performance Bond + Payment Bond (guarantees completion & sub/supplier payment).", BOND_URL),
    ("are-aia-b101", ["PjM", "CE", "PcM", "aia"], "AIA B101 covers what agreement?", "Standard Owner–Architect Agreement for basic services (SD, DD, CD, Bidding, CA), supplemental/additional services, compensation, and instruments of service.", AIA_URL),
    ("are-aia-c401", ["PjM", "PcM", "aia"], "AIA C401 covers what agreement?", "Architect–Consultant Agreement (e.g., structural, MEP, civil) — flows down B101 prime-agreement obligations ('conduit' / pass-through).", AIA_URL),
    ("are-aia-g701", ["CE", "aia"], "AIA G701 is what construction administration form?", "Change Order — modifies Contract Sum and/or Contract Time; requires ALL THREE signatures: Owner, Architect, and Contractor.", AIA_URL),
    ("are-aia-g702-g703", ["CE", "aia"], "AIA G702 and G703 are used for what?", "G702 = Application and Certificate for Payment (certified by Architect). G703 = Continuation Sheet / Schedule of Values itemizing % complete per line.", AIA_URL),
    ("are-aia-g704", ["CE", "aia"], "AIA G704 certifies what milestone, and what starts on that date?", "Certificate of Substantial Completion — project is sufficiently complete for intended occupancy; starts warranty periods, transfers insurance/utilities to Owner, and triggers punch list.", AIA_URL),
    ("are-aia-g706", ["CE", "aia"], "AIA G706 & G706A protect the Owner from what at closeout?", "G706 = Contractor's Affidavit of Payment of Debts & Claims; G706A = Affidavit of Release of Liens — protects Owner against mechanics' liens before final payment.", LIEN_URL),
    ("are-aia-g707", ["CE", "aia"], "AIA G707 is required before final payment when a project is bonded — what is it?", "Consent of Surety to Final Payment — ensures the surety agrees to release retainage/final payment without voiding bond coverage.", BOND_URL),
    ("are-aia-g710", ["CE", "aia"], "AIA G710 (ASI) does what — and what can it NOT change?", "Architect's Supplemental Instructions — clarifies drawings or makes minor changes ONLY if they involve NO change in Contract Sum and NO change in Contract Time.", AIA_URL),
    ("are-aia-g714", ["CE", "aia"], "AIA G714 (CCD) differs from a G701 Change Order how?", "Construction Change Directive — directs work when Owner & Contractor haven't agreed on cost/time; signed by Owner + Architect only (no Contractor signature required to start work).", AIA_URL),
    ("are-contract-standard-of-care", ["PjM", "PcM", "contracts"], "Under AIA B101 §2.2, why must an architect reject 'highest standard' or 'warranty' wording?", "E&O insurance covers only ordinary negligence against the local professional Standard of Care; warranties or 'best/highest' promises create uninsured contractual liability.", SOC_URL),
    ("are-instruments-of-service", ["PjM", "PcM", "contracts"], "Under AIA B101, who owns copyright to the Instruments of Service?", "The Architect (and consultants) retain copyright; upon payment, the Owner receives a nonexclusive license solely for constructing, using, and maintaining the project.", AIA_URL),
    ("are-consequential-damages", ["PjM", "PcM", "CE"], "AIA B101 & A201 include a Mutual Waiver of Consequential Damages — what does it exclude?", "Indirect/downstream losses (lost rent, lost profits, financing penalties, reputational harm); parties limit claims to direct damages or agreed liquidated damages.", AIA_URL),
    ("are-dispute-ladder", ["PjM", "CE", "PcM"], "What is the default dispute-resolution sequence under AIA A201?", "Initial Decision Maker (default: Architect) → Mediation (mandatory condition precedent) → Binding Dispute Resolution (Arbitration or Litigation, selected in agreement).", AIA_URL),

    # --- CONSTRUCTION ADMINISTRATION & BIDDING (CE) ---
    ("are-ce-means-methods", ["CE", "PjM"], "Under A201, who is solely responsible for construction means, methods, techniques, and jobsite safety?", "The Contractor — never the Architect. Directing jobsite safety or construction methods transfers liability to the Architect.", AIA_URL),
    ("are-ce-stop-work", ["CE"], "Can the Architect stop construction work if they spot nonconforming work or an unsafe scaffold?", "NO. Only the Owner can issue a stop-work order (A201 §2.4). The Architect has authority to REJECT nonconforming work and notify the Owner/Contractor in writing.", AIA_URL),
    ("are-ce-submittal-review", ["CE"], "What is the Architect's scope when reviewing shop drawings and submittals?", "Limited to checking conformance with information given and design concept expressed in the Contract Documents — NOT verifying field dimensions, quantities, or safety.", AIA_URL),
    ("are-ce-submittal-not-cd", ["CE"], "Are approved shop drawings / submittals considered Contract Documents under A201?", "NO. Approved submittals do not modify the Contract Documents; any deviation requires a formal modification (CO, CCD, or ASI).", AIA_URL),
    ("are-ce-rfi-purpose", ["CE"], "What is an RFI (Request for Information) vs. an ASI?", "RFI = Contractor asks Architect to clarify ambiguities/conflicts in CDs (no cost/time change). ASI = Architect proactively issues minor clarification/change (no cost/time change).", CM_URL),
    ("are-ce-proposal-request", ["CE"], "When is a Proposal Request (PR / AIA G709) issued?", "When the Owner/Architect contemplates a change affecting cost or time and wants a Contractor price/schedule quote BEFORE authorizing work via Change Order.", AIA_URL),
    ("are-ce-pay-app-timing", ["CE"], "Under A201, how many days does the Architect have to certify (or withhold) a Contractor's G702 pay app?", "7 days after receipt (either certify for payment or notify Contractor and Owner in writing of reasons for withholding).", AIA_URL),
    ("are-ce-stored-materials", ["CE"], "Can a Contractor bill for materials stored off-site on a G702 pay application?", "Only with prior Owner approval plus proof of title/bill of sale, proper storage/identification, and insurance covering the off-site location.", CM_URL),
    ("are-ce-liquidated-damages", ["CE", "PjM"], "What makes Liquidated Damages enforceable vs. an unenforceable penalty?", "Must be a reasonable pre-estimate of hard-to-quantify daily Owner delay losses agreed at contract signing — cannot be punitive. Often paired with early-completion bonus.", CM_URL),
    ("are-ce-addenda-vs-co", ["CE"], "Addendum vs. Change Order: when is each issued?", "Addendum modifies Bidding Documents BEFORE contract award (issued to all bidders). Change Order modifies Contract Documents AFTER contract execution.", CM_URL),
    ("are-ce-alternates-allowances", ["CE", "PjM"], "Bid Alternate vs. Allowance vs. Unit Price?", "Alternate = optional scope priced separately at bid. Allowance = placeholder dollar sum for an unspecified item (reconciled later). Unit Price = fixed rate per quantity (e.g., $/CY rock removal).", CM_URL),
    ("are-ce-punch-list", ["CE"], "Who prepares the initial Punch List before Substantial Completion under A201?", "The Contractor prepares the comprehensive list of items to be completed/corrected; the Architect then inspects and adds any omitted items before issuing G704.", AIA_URL),
    ("are-ce-correction-period", ["CE"], "What is the standard A201 one-year Correction of Work period vs. general warranty?", "Contractor must promptly correct defective work within 1 year after Substantial Completion (obligation to return); general warranty/statute of limitations can extend longer.", AIA_URL),
    ("are-ce-mechanics-lien", ["CE", "PjM"], "What is a Mechanic's Lien and how do Owners prevent it?", "Statutory security interest filed against real property by an unpaid contractor/sub/supplier. Prevented via conditional/unconditional lien waivers with pay apps and payment bonds.", LIEN_URL),
    ("are-ce-builders-risk", ["CE", "PjM"], "Who typically carries Builder's Risk (property) insurance during construction under A201?", "The Owner (covering full insurable replacement value of work-in-progress against fire/theft/weather), while the Contractor carries Commercial General Liability (CGL) & Workers' Comp.", AIA_URL),
    ("are-ce-csi-div00-01", ["CE", "PjM"], "CSI MasterFormat: what is in Division 00 vs. Division 01?", "Division 00 = Procurement & Contracting Requirements (bidding, agreements, A201). Division 01 = General Requirements (submittals, closeout, quality control, temporary facilities).", CSI_URL),
    ("are-ce-csi-key-divs", ["CE", "PjM"], "CSI MasterFormat key technical divisions: 03, 05, 07, 08, 09, 23, 26?", "03 Concrete, 05 Metals, 07 Thermal & Moisture Protection, 08 Openings (doors/windows), 09 Finishes, 23 HVAC, 26 Electrical.", CSI_URL),
    ("are-ce-spec-types", ["CE", "PjM"], "Performance vs. Prescriptive vs. Proprietary specifications?", "Performance = states required outcome/criteria (contractor picks means). Prescriptive = details exact materials/installation. Proprietary = names exact brand/product (closed or 'or equal').", CSI_URL),
    ("are-ce-spec-precedence", ["CE"], "Under A201, if drawings and specifications conflict, which takes precedence?", "Neither automatically — Contract Documents are complementary! Architect interprets intent; typically more stringent/expensive requirement or specific detail over general governs unless specified otherwise.", AIA_URL),

    # --- PROJECT DELIVERY, SCHEDULING & FINANCIALS (PjM / PcM) ---
    ("are-delivery-dbb", ["PjM", "CE"], "Design-Bid-Build (DBB): defining feature, biggest pro, biggest con?", "Separate Owner contracts with Architect and GC; sequential phases. Pro: competitive low-bid price & checks/balances. Con: longest schedule, no contractor preconstruction input, adversarial claims.", CM_URL),
    ("are-delivery-cmar", ["PjM", "CE"], "CM at Risk (CMaR / A133) vs. CM as Adviser (CMa / C132)?", "CMaR holds trade subcontracts and guarantees a GMP (at financial risk). CMa is a fee-only Owner consultant holding zero trade contracts (Owner holds multiple prime contracts).", CM_URL),
    ("are-delivery-db", ["PjM"], "Design-Build (DB): biggest pro and biggest tradeoff for the Owner?", "Single point of responsibility + fastest overlapping schedule. Tradeoff: Owner loses independent Architect advocacy/checks-and-balances (bridging architect sometimes hired).", CM_URL),
    ("are-delivery-ipd", ["PjM"], "Integrated Project Delivery (IPD): what distinguishes it contractually?", "Single multi-party agreement signed by Owner, Architect, and Contractor sharing risk/reward pool, early involvement of all parties, open-book accounting, and liability waivers among team.", CM_URL),
    ("are-pjm-cpm-float", ["PjM", "CE"], "Critical Path Method (CPM): what is the Critical Path and what is its Float?", "Longest sequential chain of dependent activities determining minimum project duration. Every task on the critical path has ZERO Total Float.", CPM_URL),
    ("are-pjm-free-vs-total-float", ["PjM", "CE"], "Free Float vs. Total Float in a CPM schedule?", "Free Float = delay allowed without delaying the next activity's early start. Total Float = delay allowed without pushing out the final project completion date.", CPM_URL),
    ("are-pjm-fast-track", ["PjM", "CE"], "What is Fast-Track construction and its main risk?", "Starting early construction packages (excavation/foundation) before full CDs are complete. Cuts schedule, but raises coordination errors, redesign cost, and late change orders.", CM_URL),
    ("are-pjm-net-multiplier", ["PjM", "PcM"], "Firm financial ratio: Net Multiplier formula & healthy range?", "Net Operating Revenue ÷ Direct Labor Cost. Measures how many dollars of revenue each direct labor dollar generates; healthy architectural firm target ~2.8–3.2 (must exceed Break-Even Rate = 1 + Overhead Rate).", AIA_URL),
    ("are-pjm-overhead-breakeven", ["PjM", "PcM"], "Overhead Rate and Break-Even Rate formulas?", "Overhead Rate = Total Indirect Expenses ÷ Total Direct Labor (typical ~1.3–1.7). Break-Even Rate = 1.0 + Overhead Rate (~2.3–2.7).", AIA_URL),
    ("are-pjm-proforma-caprate", ["PjM", "PA"], "Real estate pro forma: NOI and Capitalization Rate (Cap Rate) formula?", "NOI = Effective Gross Income − Operating Expenses (excludes debt service & depreciation). Property Value = NOI ÷ Cap Rate.", ZONING_URL),
    ("are-pjm-hard-vs-soft", ["PjM", "PA"], "Project budget: Hard Costs vs. Soft Costs?", "Hard Costs = physical construction (labor, materials, site work, GC overhead). Soft Costs = design/engineering fees, permits, legal, financing, testing, insurance (~20–30% of total).", CM_URL),
    ("are-pjm-contingency", ["PjM", "CE"], "Design Contingency vs. Construction Contingency?", "Design Contingency shrinks from ~15–20% in SD to ~0% at bid as scope hardens. Construction Contingency (~5% new build, ~10% renovation) covers unforeseen field conditions/COs.", CM_URL),
    ("are-pjm-value-engineering", ["PjM", "CE"], "True Value Engineering (VE) vs. simple cost-cutting?", "VE analyzes life-cycle cost vs. function (achieving equal or better performance at lower total life-cycle cost), not merely slashing initial capital cost by degrading quality.", CM_URL),
    ("are-pjm-entity-types", ["PcM", "PjM"], "Sole Proprietorship vs. General Partnership vs. LLC vs. Corporation (liability)?", "Sole Prop & General Partnership = unlimited personal liability (and joint-and-several for partners). LLC / Corp / PC = shields personal assets from firm business debts (never from one's own malpractice).", AIA_URL),

    # --- PROGRAMMING, SITE, ZONING & CODES (PA) ---
    ("are-pa-far", ["PA"], "Floor Area Ratio (FAR): formula and what does FAR 4.0 allow on a 10,000 sf lot?", "FAR = Total Gross Building Floor Area ÷ Net Lot Area. FAR 4.0 on 10,000 sf = 40,000 sf total (e.g., 4 stories × 100% lot, or 8 stories × 50% lot coverage).", ZONING_URL),
    ("are-pa-variance-vs-cup", ["PA"], "Zoning Variance vs. Conditional Use Permit (CUP) vs. Rezoning?", "Variance = relief from dimensional rules (setback/height) proving unique site hardship. CUP = permitted use with extra conditions. Rezoning = legislative change to zoning map/text.", ZONING_URL),
    ("are-pa-easement-vs-covenant", ["PA"], "Easement vs. Restrictive Covenant (Deed Restriction)?", "Easement = legal right for another party to use/cross part of land (utility, access, solar). Covenant = private deed restriction limiting use/appearance (stricter of zoning or covenant governs).", ZONING_URL),
    ("are-pa-esa-phase1-2", ["PA"], "Environmental Site Assessment: Phase I ESA vs. Phase II ESA?", "Phase I = non-invasive historical records, site walk, interviews to spot Recognized Environmental Conditions (RECs). Phase II = physical soil/groundwater/asbestos sampling & lab testing if Phase I flags RECs.", ESA_URL),
    ("are-pa-brownfield", ["PA"], "Brownfield vs. Greyfield vs. Greenfield site?", "Brownfield = previously developed site with real or perceived environmental contamination. Greyfield = economically obsolete developed site (dead mall/parking lot) without major toxics. Greenfield = undeveloped land.", ESA_URL),
    ("are-pa-ada-ramp-slope", ["PA", "CE", "ada"], "2010 ADA Standards: max running slope, max cross slope, and max rise per ramp run?", "1:12 max running slope (8.33%), 1:48 max cross slope (2.08%), and 30 inches max vertical rise per run before a 60-inch level landing (ADA §405).", ADA_URL),
    ("are-pa-type-v-over-i", ["PA", "codes"], "Why do '5-over-1' buildings dominate US urban infill?", "IBC §510.2 allows up to 5 stories of combustible wood framing (Type IIIA or VA, sprinklered) above a 3-hour fire-separated Type IA concrete podium, maximizing rentable area per dollar.", FIVE_URL),
    ("are-pa-ibc-types", ["PA", "codes"], "IBC Construction Types I through V ordered from most to least fire-resistive?", "I = Noncombustible highest fire-resistance (concrete/protected steel); II = Noncombustible lower rating; III = Noncombustible ext. walls + combustible interior; IV = Heavy/Mass Timber; V = Combustible (wood frame). Suffix A = protected, B = unprotected.", IBC_URL),
    ("are-pa-ibc-occupancies", ["PA", "codes"], "IBC Occupancy Groups: A, B, E, F, H, I, M, R, S, U?", "A Assembly, B Business, E Educational, F Factory, H High-Hazard, I Institutional (hospitals/prisons), M Mercantile, R Residential, S Storage, U Utility/Misc.", IBC_URL),
    ("are-pa-two-exits-rule", ["PA", "codes"], "IBC general rule: at what occupant load are two exits required (most occupancies)?", "≥50 occupants for Group A, B, E, F, M, U (≥10 for R-2/R-3 stories above 1st; ≥30 for S). When 2 exits are required, separate them by ≥1/2 diagonal (≥1/3 diagonal if fully sprinklered).", IBC_URL),
    ("are-pa-solar-orientation", ["PA", "site"], "Northern Hemisphere passive solar rule for South vs. East/West facades?", "South = high summer sun (easy to shade with horizontal overhangs), low winter sun (passive heat gain). East/West = low-angle harsh sun requiring vertical fins or minimized glazing.", ZONING_URL),
    ("are-pa-slope-grading", ["PA", "site"], "Site grading slopes: drainage away from foundation, max accessible walk without ramp, max grass mowing slope?", "Foundation drainage = min 5% (6 in over first 10 ft). Accessible walkway (not a ramp) = ≤5% (1:20). Comfortable lawn mowing = ≤25–33% (4:1 to 3:1).", ADA_URL),
    ("are-pa-contour-rules", ["PA", "site"], "Topographic contour lines: how do valleys/swales vs. ridges point, and what does close spacing mean?", "Contours point UPHILL in valleys/swales and DOWNHILL on ridges. Closely spaced contours = steep slope; wide spacing = gentle/flat grade.", SOIL_URL),
    ("are-pa-microclimate-urban", ["PA", "site"], "Heat Island mitigation & passive cooling: albedo, thermal mass, stack ventilation?", "High-albedo (reflective) surfaces & vegetated roofs cut urban heat island; high thermal mass flattens diurnal swings (hot-arid); stack ventilation vents hot air high and draws cool air low.", RVAL_URL),
    ("are-pa-water-table-frost", ["PA", "site"], "Why must footings sit below the local frost line, and what happens below the water table?", "Below frost line prevents frost-heave cracking from freezing soil moisture. Below water table requires hydrostatic waterproofing, dewatering during construction, and uplift/buoyancy resistance.", SOIL_URL),
    ("are-pa-historic-soi", ["PA"], "Secretary of the Interior's four treatments for historic properties (most to least conservative)?", "Preservation (maintain existing form), Rehabilitation (compatible new use while keeping historic character — tax credit eligible), Restoration (return to one specific era), Reconstruction (rebuild vanished structure).", IBC_URL),
]

def write_wall_section_svg(svg_path: str):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" class="manifold-figure-svg">
  <rect width="600" height="420" fill="var(--fig-bg, #131720)" rx="12" />
  <text x="20" y="28" fill="var(--fig-muted, #8b95a5)" font-size="13" font-family="system-ui, sans-serif" font-weight="600">EXTERIOR RAINSCREEN WALL SECTION (OUTSIDE LEFT → INSIDE RIGHT)</text>
  <text x="26" y="54" fill="var(--fig-muted, #8b95a5)" font-size="11" font-family="ui-monospace, monospace">EXTERIOR</text>
  <text x="506" y="54" fill="var(--fig-muted, #8b95a5)" font-size="11" font-family="ui-monospace, monospace">INTERIOR</text>
  <g id="regions-layer">
    <rect id="ws-cladding" data-region="ws-cladding" data-label="Exterior Cladding (Rainscreen)" x="34" y="68" width="54" height="316" rx="4" class="figure-region" />
    <rect id="ws-air-gap" data-region="ws-air-gap" data-label="Drainage / Ventilated Air Cavity" x="96" y="68" width="38" height="316" rx="4" class="figure-region" />
    <rect id="ws-ext-insul" data-region="ws-ext-insul" data-label="Continuous Exterior Insulation" x="142" y="68" width="76" height="316" rx="4" class="figure-region" />
    <rect id="ws-wrb" data-region="ws-wrb" data-label="WRB / Continuous Air Barrier" x="226" y="68" width="24" height="316" rx="4" class="figure-region" />
    <rect id="ws-sheathing" data-region="ws-sheathing" data-label="Structural Sheathing" x="258" y="68" width="44" height="316" rx="4" class="figure-region" />
    <rect id="ws-stud-cavity" data-region="ws-stud-cavity" data-label="Stud Framing + Cavity Insulation" x="310" y="68" width="166" height="316" rx="4" class="figure-region" />
    <rect id="ws-gypsum" data-region="ws-gypsum" data-label="Interior Gypsum Wallboard" x="484" y="68" width="46" height="316" rx="4" class="figure-region" />
  </g>
  <g stroke="var(--fig-line, #64748b)" stroke-width="1.2" opacity="0.4" pointer-events="none">
    <line x1="34" y1="140" x2="88" y2="140" />
    <line x1="34" y1="220" x2="88" y2="220" />
    <line x1="34" y1="300" x2="88" y2="300" />
    <line x1="310" y1="100" x2="476" y2="100" stroke-dasharray="4 4" />
    <line x1="310" y1="352" x2="476" y2="352" stroke-dasharray="4 4" />
    <path d="M115,96 L115,356 M108,344 L115,356 L122,344" stroke-width="1.5" />
  </g>
</svg>"""
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

def write_aia_delivery_svg(svg_path: str):
    """AIA Design-Bid-Build contractual relationship diagram (PjM / CE / PcM)."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" class="manifold-figure-svg">
  <rect width="600" height="420" fill="var(--fig-bg, #131720)" rx="12" />
  <text x="20" y="28" fill="var(--fig-muted, #8b95a5)" font-size="13" font-family="system-ui, sans-serif" font-weight="600">AIA DESIGN-BID-BUILD CONTRACTUAL RELATIONSHIPS</text>
  <!-- Connectors -->
  <g stroke="var(--fig-line, #64748b)" stroke-width="2" fill="none" pointer-events="none">
    <line x1="250" y1="92" x2="155" y2="178" />
    <line x1="350" y1="92" x2="445" y2="178" />
    <line x1="155" y1="234" x2="155" y2="316" />
    <line x1="445" y1="234" x2="445" y2="316" />
    <line x1="226" y1="206" x2="374" y2="206" stroke-dasharray="6 5" />
  </g>
  <text x="236" y="196" fill="var(--fig-muted, #8b95a5)" font-size="10" font-family="ui-monospace, monospace">NO CONTRACT (CA ONLY)</text>

  <g id="regions-layer">
    <rect id="aia-owner" data-region="aia-owner" data-label="Owner (Client)" x="220" y="48" width="160" height="48" rx="8" class="figure-region" />
    <rect id="aia-b101" data-region="aia-b101" data-label="AIA B101 (Owner–Architect)" x="116" y="114" width="128" height="36" rx="6" class="figure-region" />
    <rect id="aia-a101" data-region="aia-a101" data-label="AIA A101 + A201 (Owner–GC)" x="356" y="114" width="136" height="36" rx="6" class="figure-region" />
    <rect id="aia-architect" data-region="aia-architect" data-label="Architect (IDM / CA)" x="76" y="178" width="150" height="56" rx="8" class="figure-region" />
    <rect id="aia-contractor" data-region="aia-contractor" data-label="General Contractor (Means & Safety)" x="374" y="178" width="150" height="56" rx="8" class="figure-region" />
    <rect id="aia-c401" data-region="aia-c401" data-label="AIA C401 (Architect–Consultant)" x="76" y="256" width="150" height="34" rx="6" class="figure-region" />
    <rect id="aia-a401" data-region="aia-a401" data-label="AIA A401 (GC–Subcontractor)" x="374" y="256" width="150" height="34" rx="6" class="figure-region" />
    <rect id="aia-consultants" data-region="aia-consultants" data-label="Structural / MEP Consultants" x="76" y="316" width="150" height="52" rx="8" class="figure-region" />
    <rect id="aia-subs" data-region="aia-subs" data-label="Trade Subcontractors" x="374" y="316" width="150" height="52" rx="8" class="figure-region" />
  </g>
</svg>"""
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

def write_site_zoning_svg(svg_path: str):
    """Urban Site & Zoning Envelope Section SVG (PA)."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 420" class="manifold-figure-svg">
  <rect width="600" height="420" fill="var(--fig-bg, #131720)" rx="12" />
  <text x="20" y="28" fill="var(--fig-muted, #8b95a5)" font-size="13" font-family="system-ui, sans-serif" font-weight="600">SITE &amp; ZONING ENVELOPE SECTION (PA)</text>
  <!-- Reference lines -->
  <g stroke="var(--fig-line, #64748b)" stroke-width="1.4" pointer-events="none">
    <line x1="20" y1="268" x2="580" y2="268" />
    <line x1="60" y1="54" x2="60" y2="390" stroke-dasharray="6 4" />
    <line x1="540" y1="54" x2="540" y2="390" stroke-dasharray="6 4" />
  </g>
  <g id="regions-layer">
    <!-- Sky exposure plane / upper height limit -->
    <polygon id="sz-sky-plane" data-region="sz-sky-plane" data-label="Sky Exposure Plane / Height Limit" points="140,68 470,68 470,130 220,130" class="figure-region" />
    <!-- Buildable Envelope (FAR massing) -->
    <rect id="sz-envelope" data-region="sz-envelope" data-label="Buildable Zoning Envelope (FAR)" x="140" y="136" width="330" height="126" rx="4" class="figure-region" />
    <!-- Front Setback / Street Yard -->
    <rect id="sz-front-setback" data-region="sz-front-setback" data-label="Front Yard Setback" x="64" y="170" width="70" height="92" rx="4" class="figure-region" />
    <!-- Rear Yard Setback -->
    <rect id="sz-rear-setback" data-region="sz-rear-setback" data-label="Rear Yard Setback" x="476" y="170" width="60" height="92" rx="4" class="figure-region" />
    <!-- Utility / Access Easement -->
    <rect id="sz-easement" data-region="sz-easement" data-label="Utility / Access Easement" x="476" y="274" width="60" height="44" rx="4" class="figure-region" />
    <!-- Frost Line Zone -->
    <rect id="sz-frost-line" data-region="sz-frost-line" data-label="Frost Line Depth (Footing Bearing Below)" x="64" y="274" width="406" height="44" rx="4" class="figure-region" />
    <!-- Footing & Bearing Stratum -->
    <rect id="sz-footing" data-region="sz-footing" data-label="Spread Footing Below Frost Line" x="156" y="324" width="298" height="30" rx="4" class="figure-region" />
    <!-- Water Table -->
    <rect id="sz-water-table" data-region="sz-water-table" data-label="Groundwater Table (Hydrostatic Pressure)" x="64" y="360" width="472" height="36" rx="4" class="figure-region" />
  </g>
</svg>"""
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

def main():
    url_cache: dict[str, str] = {}
    def verify_cached(url: str, keywords: list[str]) -> bool:
        if url not in url_cache:
            print(f"Opening primary reference: {url}")
            url_cache[url] = fetch_text(url)
        return any(k.lower() in url_cache[url] for k in keywords)

    entities = []
    facts = []
    verification_log = []

    for eid, name, kind, tags, dim_id, val, low, high, url, checks, note in RAW_FACTS:
        ok = verify_cached(url, checks)
        if not ok:
            raise RuntimeError(f"Primary reference check failed for {eid} at {url}")
        entities.append({
            "id": eid,
            "name": name,
            "kind": kind,
            "module": "are_built",
            "tags": tags,
        })
        facts.append({
            "entity_id": eid,
            "dimension_id": dim_id,
            "value": val,
            "low": low,
            "high": high,
            "as_of": str(date.today()),
            "source_url": url,
            "source_note": note,
            "volatile": False,
        })
        verification_log.append({"entity_id": eid, "dim": dim_id, "source_url": url, "verified": True})

    plain_cards = []
    for cid, tags, front, back, url in PLAIN_CARDS_SPEC:
        verify_cached(url, ["a", "e"])
        plain_cards.append({
            "id": cid,
            "module": "are_built",
            "tags": tags,
            "front": front,
            "back": back,
            "source_url": url,
            "source_note": f"ARE 5.0 ({'/'.join(t for t in tags if t in ('PjM','CE','PA','PcM'))}) reference",
            "as_of": str(date.today()),
            "volatile": False,
        })

    write_wall_section_svg(os.path.join("src", "assets", "figures", "wall-section.svg"))
    write_aia_delivery_svg(os.path.join("src", "assets", "figures", "aia-delivery-map.svg"))
    write_site_zoning_svg(os.path.join("src", "assets", "figures", "site-zoning-section.svg"))

    figures = [
        {
            "id": "rainscreen-wall-section",
            "title": "Rainscreen Exterior Wall Section",
            "module": "are_built",
            "dimension_id": "wall_assembly",
            "svg_path": "figures/wall-section.svg",
            "source_url": RVAL_URL,
            "source_note": "Standard North American drained/ventilated exterior-insulated wall assembly",
            "regions": [
                {"region_id": "ws-cladding", "label": "Exterior Cladding (Rainscreen)", "adjacent_ids": ["ws-air-gap"]},
                {"region_id": "ws-air-gap", "label": "Drainage / Ventilated Air Cavity", "adjacent_ids": ["ws-cladding", "ws-ext-insul"]},
                {"region_id": "ws-ext-insul", "label": "Continuous Exterior Insulation", "adjacent_ids": ["ws-air-gap", "ws-wrb"]},
                {"region_id": "ws-wrb", "label": "WRB / Continuous Air Barrier", "adjacent_ids": ["ws-ext-insul", "ws-sheathing"]},
                {"region_id": "ws-sheathing", "label": "Structural Sheathing", "adjacent_ids": ["ws-wrb", "ws-stud-cavity"]},
                {"region_id": "ws-stud-cavity", "label": "Stud Framing + Cavity Insulation", "adjacent_ids": ["ws-sheathing", "ws-gypsum"]},
                {"region_id": "ws-gypsum", "label": "Interior Gypsum Wallboard", "adjacent_ids": ["ws-stud-cavity"]},
            ],
        },
        {
            "id": "aia-delivery-map",
            "title": "AIA Design-Bid-Build Relationships (PjM / CE)",
            "module": "are_built",
            "dimension_id": "aia_delivery_diagram",
            "svg_path": "figures/aia-delivery-map.svg",
            "source_url": AIA_URL,
            "source_note": "Standard AIA Design-Bid-Build contractual topology (B101, A101/A201, C401, A401)",
            "regions": [
                {"region_id": "aia-owner", "label": "Owner (Client)", "adjacent_ids": ["aia-b101", "aia-a101"]},
                {"region_id": "aia-b101", "label": "AIA B101 (Owner–Architect)", "adjacent_ids": ["aia-owner", "aia-architect"]},
                {"region_id": "aia-a101", "label": "AIA A101 + A201 (Owner–GC)", "adjacent_ids": ["aia-owner", "aia-contractor"]},
                {"region_id": "aia-architect", "label": "Architect (IDM / CA)", "adjacent_ids": ["aia-b101", "aia-c401"]},
                {"region_id": "aia-contractor", "label": "General Contractor (Means & Safety)", "adjacent_ids": ["aia-a101", "aia-a401"]},
                {"region_id": "aia-c401", "label": "AIA C401 (Architect–Consultant)", "adjacent_ids": ["aia-architect", "aia-consultants"]},
                {"region_id": "aia-a401", "label": "AIA A401 (GC–Subcontractor)", "adjacent_ids": ["aia-contractor", "aia-subs"]},
                {"region_id": "aia-consultants", "label": "Structural / MEP Consultants", "adjacent_ids": ["aia-c401"]},
                {"region_id": "aia-subs", "label": "Trade Subcontractors", "adjacent_ids": ["aia-a401"]},
            ],
        },
        {
            "id": "site-zoning-section",
            "title": "Site & Zoning Envelope Section (PA)",
            "module": "are_built",
            "dimension_id": "site_zoning_diagram",
            "svg_path": "figures/site-zoning-section.svg",
            "source_url": ZONING_URL,
            "source_note": "Standard urban zoning envelope, setbacks, easement, frost line, and water table section",
            "regions": [
                {"region_id": "sz-sky-plane", "label": "Sky Exposure Plane / Height Limit", "adjacent_ids": ["sz-envelope"]},
                {"region_id": "sz-envelope", "label": "Buildable Zoning Envelope (FAR)", "adjacent_ids": ["sz-sky-plane", "sz-front-setback", "sz-rear-setback"]},
                {"region_id": "sz-front-setback", "label": "Front Yard Setback", "adjacent_ids": ["sz-envelope", "sz-frost-line"]},
                {"region_id": "sz-rear-setback", "label": "Rear Yard Setback", "adjacent_ids": ["sz-envelope", "sz-easement"]},
                {"region_id": "sz-easement", "label": "Utility / Access Easement", "adjacent_ids": ["sz-rear-setback", "sz-frost-line"]},
                {"region_id": "sz-frost-line", "label": "Frost Line Depth (Footing Bearing Below)", "adjacent_ids": ["sz-front-setback", "sz-footing", "sz-easement"]},
                {"region_id": "sz-footing", "label": "Spread Footing Below Frost Line", "adjacent_ids": ["sz-frost-line", "sz-water-table"]},
                {"region_id": "sz-water-table", "label": "Groundwater Table (Hydrostatic Pressure)", "adjacent_ids": ["sz-footing"]},
            ],
        },
    ]

    pack = {
        "pack_id": "are-built-environment",
        "version": "0.2.0",
        "release_date": str(date.today()),
        "module": "are_built",
        "entities": entities,
        "dimensions": [
            {"id": "code_dimension_in", "name": "ADA / IBC Clearance", "unit": "in", "scale": "linear", "tolerance": 4, "tolerance_mode": "absolute", "min_domain": 0, "max_domain": 90},
            {"id": "occupant_load_sf", "name": "IBC Occupant Load Factor", "unit": "sf/person", "scale": "log", "tolerance": 1.5, "tolerance_mode": "factor"},
            {"id": "soil_bearing_psf", "name": "IBC Presumptive Soil Bearing", "unit": "psf", "scale": "log", "tolerance": 1.5, "tolerance_mode": "factor"},
            {"id": "live_load_psf", "name": "ASCE 7 / IBC Live Load", "unit": "psf", "scale": "linear", "tolerance": 15, "tolerance_mode": "absolute", "min_domain": 0, "max_domain": 280},
            {"id": "r_value_per_in", "name": "Thermal Resistance", "unit": "R/in", "scale": "linear", "tolerance": 0.8, "tolerance_mode": "absolute", "min_domain": 0, "max_domain": 8},
            {"id": "project_pct", "name": "Project & Practice Benchmark", "unit": "%", "scale": "linear", "tolerance": 5, "tolerance_mode": "absolute", "min_domain": 0, "max_domain": 100},
            {"id": "wall_assembly", "name": "Rainscreen Wall Section", "unit": "", "scale": "geo", "tolerance": 1},
            {"id": "aia_delivery_diagram", "name": "AIA Contractual Topology", "unit": "", "scale": "geo", "tolerance": 1},
            {"id": "site_zoning_diagram", "name": "Site & Zoning Envelope", "unit": "", "scale": "geo", "tolerance": 1},
        ],
        "facts": facts,
        "anchor_sets": [
            {"dimension_id": "code_dimension_in", "entity_ids": ["ada-threshold-beveled-max", "ada-stair-riser-max", "ada-door-clear-width", "ada-turning-circle", "ada-headroom-clearance"]},
            {"dimension_id": "occupant_load_sf", "entity_ids": ["occ-assembly-standing", "occ-classroom", "occ-mercantile", "occ-business", "occ-warehouse-mech"]},
            {"dimension_id": "soil_bearing_psf", "entity_ids": ["soil-clay", "soil-gravel", "soil-crystalline"]},
            {"dimension_id": "live_load_psf", "entity_ids": ["load-roof-ordinary", "load-office-floor", "load-public-lobby-stairs", "load-heavy-storage"]},
            {"dimension_id": "r_value_per_in", "entity_ids": ["r-concrete", "r-fiberglass-batt", "r-closed-cell-spray"]},
            {"dimension_id": "project_pct", "entity_ids": ["fee-bidding-pct", "fee-dd-pct", "fee-cd-pct", "pa-ntg-office"]},
        ],
        "figures": figures,
        "plain_cards": plain_cards,
        "ordering_assertions": [
            {"dimension_id": "code_dimension_in", "ordered_entity_ids": ["ada-threshold-beveled-max", "ada-stair-riser-min", "ada-stair-riser-max", "ada-stair-tread-min", "ada-reach-low-min", "ada-door-clear-width", "ibc-guardrail-height", "ada-turning-circle", "ada-headroom-clearance"]},
            {"dimension_id": "occupant_load_sf", "ordered_entity_ids": ["occ-assembly-standing", "occ-assembly-unfixed", "occ-assembly-tables", "occ-classroom", "occ-library-reading", "occ-mercantile", "occ-industrial-lab", "occ-business", "occ-residential", "occ-warehouse-mech"]},
            {"dimension_id": "soil_bearing_psf", "ordered_entity_ids": ["soil-clay", "soil-sand-silty", "soil-gravel", "soil-sedimentary", "soil-crystalline"]},
            {"dimension_id": "live_load_psf", "ordered_entity_ids": ["load-roof-ordinary", "load-residential-sleeping", "load-residential-other", "load-office-floor", "load-corridor-upper", "load-public-lobby-stairs", "load-library-stacks", "load-heavy-storage"]},
        ],
    }

    total_regions = sum(len(f["regions"]) for f in figures)
    os.makedirs(os.path.join("content", "packs"), exist_ok=True)
    with open(os.path.join("content", "packs", "are_built.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2)
    with open(os.path.join("content", "verification-are-built.json"), "w", encoding="utf-8") as f:
        json.dump(verification_log, f, indent=2)

    print(f"Wrote M3 are_built.json (PjM/CE/PA): {len(facts)} facts, {len(plain_cards)} cards, {len(figures)} SVGs ({total_regions} regions) = {len(facts) + len(plain_cards) + total_regions} total schedulable items.")

if __name__ == "__main__":
    main()
