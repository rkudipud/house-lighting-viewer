"""Per-room lumen and electrical lighting load sheet (XLSX + PDF) from the canonical master."""
import argparse, hashlib, json, os
from collections import OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--master", required=True, help="Current canonical house-design.json")
parser.add_argument("--output-dir", required=True, help="Directory for generated files")
args = parser.parse_args()
MASTER = args.master
HERE = args.output_dir
os.makedirs(HERE, exist_ok=True)
SQFT = 10.7639
TARGET_LM_PER_SQFT = 20
LM_PER_W_RULE = 100
PSU_EFF = 0.90      # planning assumption for 24 V / 48 V supplies
PF = 0.80           # planning assumption for inverter VA sizing
INV_EFF = 0.85      # planning assumption, inverter efficiency
BATT_DOD = 0.80     # planning assumption, usable battery fraction
STOREYS = 4
FLATS_PER_FLOOR = 1
FLATS = STOREYS * FLATS_PER_FLOOR

ROOM_NAMES = OrderedDict([
    ("LIV", "Living"), ("DIN", "Dining"), ("KIT", "Kitchen"), ("UTL", "Utility"),
    ("MBR", "Master bedroom"), ("DRS", "Master dressing"), ("TL1", "Toilet 1 (master)"),
    ("CBR", "Children's bedroom"), ("TL2", "Toilet 2 (common)"), ("LOB", "Washbasin lobby"),
    ("BAL", "Balcony / arrival"),
])
LOW_LAYERS = {"LOW", "PENDANT"}
CBR_REVIEW_ON = {"CBR-L1", "CBR-X1", "CBR-X2", "CBR-X3", "CBR-X4"}
# Homeowner-selected curtain-pocket strips (S1 extension): W per room, no photometric credit.
CURTAIN_W = {"LIV": 19.60, "DIN": 19.60, "MBR": 19.44, "CBR": 12.40}

raw = open(MASTER, "rb").read()
sha = hashlib.sha256(raw).hexdigest()
d = json.loads(raw)
L = d["lighting"]
fx = L["fixtures"]
layer = {f["id"]: f["layer"] for f in L["fixed_cct_map"]["fittings"]}
hold_ids = {}
for hold in L["design_inputs"]["provenance"]["layout_basis"]["holds"]:
    for fitting_id in hold.get("fixtures", []):
        hold_ids.setdefault(fitting_id, []).append(hold["id"])
areas = {r: v["area_m2"] for r, v in L["calculations"]["rooms"].items()}
assert len(fx) == 104
ext = L["electrical_checks"]["selected_curtain_S1_extension"]["with_S1"]
assert abs(sum(CURTAIN_W.values()) - ext["selected_strip_load_W"]) < 0.001
standby = L["electrical_checks"]["one_flat"]["standby_W_est"]


def grp(f):
    lay = layer[f["id"]]
    return "HIGH" if lay == "HIGH" else ("LOW" if lay in LOW_LAYERS else "OTHER")


rows = []
for rid, name in ROOM_NAMES.items():
    fs = [f for f in fx if f["room"] == rid]
    a = areas[rid]
    sqft = a * SQFT
    r = dict(id=rid, name=name, n=len(fs), m2=a, sqft=sqft, target_lm=sqft * TARGET_LM_PER_SQFT)
    for g in ("HIGH", "LOW", "OTHER"):
        r["lm_" + g] = sum(f["lm"] for f in fs if grp(f) == g)
        r["W_" + g] = sum(f["W_nominal"] for f in fs if grp(f) == g)
    r["lm"] = sum(f["lm"] for f in fs)
    r["W"] = sum(f["W_nominal"] for f in fs)
    r["W_lv"] = sum(f["W_nominal"] for f in fs if f["supply"] in ("24V", "48VTRK"))
    r["curtain_W"] = CURTAIN_W.get(rid, 0.0)
    r["held_W"] = sum(f["W_nominal"] for f in fs if hold_ids.get(f["id"]))
    r["held_lm"] = sum(f["lm"] for f in fs if hold_ids.get(f["id"]))
    r["held_low_lm"] = sum(f["lm"] for f in fs if grp(f) == "LOW" and hold_ids.get(f["id"]))
    r["available_low_lm"] = sum(f["lm"] for f in fs if grp(f) == "LOW"
                                and (not hold_ids.get(f["id"]) or f["id"] in CBR_REVIEW_ON))
    r["W_all"] = r["W"] + r["curtain_W"]
    # Input power: 230 V fittings as rated, 24/48 V loads (incl. curtain strips) / PSU efficiency
    r["W_input"] = (r["W"] - r["W_lv"]) + (r["W_lv"] + r["curtain_W"]) / PSU_EFF
    r["lm_per_sqft"] = r["lm"] / sqft
    r["pct_target"] = 100 * r["lm"] / r["target_lm"]
    r["pct_high"] = 100 * r["lm_HIGH"] / r["target_lm"]
    r["rule_W_target"] = r["target_lm"] / LM_PER_W_RULE
    r["rule_W_installed"] = r["lm"] / LM_PER_W_RULE
    r["lm_per_W"] = r["lm"] / r["W"]
    rows.append(r)

assert sum(r["n"] for r in rows) == 104
T = {k: sum(r[k] for r in rows) for k in rows[0] if isinstance(rows[0][k], (int, float))}
T.update(id="FLAT", name="One flat (per floor)")
T["lm_per_sqft"] = T["lm"] / T["sqft"]; T["pct_target"] = 100 * T["lm"] / T["target_lm"]; T["pct_high"] = 100 * T["lm_HIGH"] / T["target_lm"]
T["lm_per_W"] = T["lm"] / T["W"]
assert abs(T["W"] - L["electrical_checks"]["one_flat"]["W_nominal"]) < 0.5
flat_input = T["W_input"] + standby
floor_input = flat_input * FLATS_PER_FLOOR
bldg_input = flat_input * FLATS

def kw(w): return w / 1000.0

inv = OrderedDict()
inv["Connected LED load, base 104 fittings (W)"] = (T["W"], T["W"] * FLATS_PER_FLOOR, T["W"] * FLATS)
inv["+ selected curtain-pocket strips (W)"] = (T["curtain_W"], T["curtain_W"] * FLATS_PER_FLOOR, T["curtain_W"] * FLATS)
inv["Connected LED load incl. curtain strips (W)"] = (T["W_all"], T["W_all"] * FLATS_PER_FLOOR, T["W_all"] * FLATS)
inv[f"Input power incl. 24/48 V supply losses @{int(PSU_EFF*100)}% eff. (W)"] = (T["W_input"], T["W_input"] * FLATS_PER_FLOOR, T["W_input"] * FLATS)
inv["+ standby of supplies/controls, est. (W)"] = (standby, standby * FLATS_PER_FLOOR, standby * FLATS)
inv["Planning lighting load, everything ON at 100% (W)"] = (flat_input, floor_input, bldg_input)
inv["Planning lighting load (kW)"] = (kw(flat_input), kw(floor_input), kw(bldg_input))
inv[f"Apparent power for inverter, PF {PF} (VA)"] = (flat_input / PF, floor_input / PF, bldg_input / PF)
inv[f"Apparent power for inverter, PF {PF} (kVA)"] = (flat_input / PF / 1000, floor_input / PF / 1000, bldg_input / PF / 1000)
inv["Contractor rule: area x 20 lm/sq ft / 100 lm/W (W)"] = (T["rule_W_target"], T["rule_W_target"] * FLATS_PER_FLOOR, T["rule_W_target"] * FLATS)
shares = {"LOW": 1.0, "HIGH": 0.5, "OTHER": 0.3}
typical_in = sum(
    f["W_nominal"] * shares[grp(f)] / (PSU_EFF if f["supply"] in ("24V", "48VTRK") else 1)
    for f in fx
) + T["curtain_W"] / PSU_EFF + standby
inv["Illustrative partial-load outage use, est. (W)"] = (typical_in, typical_in * FLATS_PER_FLOOR, typical_in * FLATS)
energy = OrderedDict()
for hrs in (1, 2, 4):
    energy[f"{hrs} h, everything ON (kWh)"] = (kw(flat_input) * hrs, kw(floor_input) * hrs, kw(bldg_input) * hrs)
    energy[f"{hrs} h, illustrative partial load (kWh)"] = (kw(typical_in) * hrs, kw(typical_in) * FLATS_PER_FLOOR * hrs, kw(typical_in) * FLATS * hrs)
batt = OrderedDict()
for hrs in (2, 4):
    e = kw(typical_in) * hrs / (INV_EFF * BATT_DOD)
    batt[f"Battery energy for {hrs} h illustrative load (kWh)"] = (f"{e:.2f}", f"{e * FLATS_PER_FLOOR:.2f}", f"{e * FLATS:.2f}")
    batt[f"{hrs} h battery capacity per flat (Ah)"] = (f"{e*1000/12:,.0f} Ah @12 V", f"{e*1000/12*FLATS_PER_FLOOR:,.0f} Ah @12 V", f"{e*1000/12*FLATS:,.0f} Ah @12 V")
ASSUMPTIONS = [
    f"Source: canonical master house-design.json, SHA-256 {sha} (fixed-CCT revision with the provisional CBR R05 ceiling review). 104 photometric fittings per flat; lumens and wattages unchanged; CBR-X1-X4 positions are provisional and site-held (H-CBR-CEIL).",
    "Lumens are scheduled fitting/strip output, not measured lux on the working plane. Indirect coves and strips deliver less useful light than downlights, so lm/sq ft is not comparable to delivered brightness.",
    "Contractor rules (20 lm per sq ft; 1 W per 100 lm) are rough sanity checks, not a design method. The design uses efficient LEDs (about 85 lm/W average), so actual wattage is a little higher than lm/100 for the same lumens.",
    f"Areas are approximate lighting calculation zones, not verified net floor measurements. The working building multiplier assumes {STOREYS} storeys x {FLATS_PER_FLOOR} modelled 2BHK flat per floor = {FLATS} flat schedules; confirm the actual floor and flat count, floor variations and quantities on site. Common stair/lift lobby, terrace, exterior and parking lighting are excluded.",
    "Groups: HIGH is the main functional layer: 4000 K in the main rooms; the two lobby and two balcony HIGH fittings remain at 3000 K. LOW = coves/strips/mood including the dining pendant (2700 K). Task/accent/other = kitchen and study task, face, art, reading, pooja accent and PIR night lights.",
    f"CBR-L1 (C39 cove; {next(f['lm'] for f in fx if f['id']=='CBR-L1'):,} lm) and CBR-X1..X4 (C40 LINE; {sum(f['lm'] for f in fx if f['id'] in ('CBR-X1','CBR-X2','CBR-X3','CBR-X4')):,} lm) are modelled ON in the design-review viewer. The children LOW schedule contributes {next(r['lm_LOW'] for r in rows if r['id']=='CBR'):,} lm in that provisional model; H-CBR-CEIL still holds physical installation and operation pending site and product checks.",
    "Selected curtain-pocket strips (LIV, DIN, MBR, CBR; 8.88 m, 71.04 W per flat) are included in electrical load, but have no separate lumen credit. Their lengths remain to be measured.",
    f"Planning assumptions, not manufacturer data: 24/48 V supply efficiency {int(PSU_EFF*100)}%, power factor {PF} for illustrative VA, inverter efficiency {int(INV_EFF*100)}%, usable battery {int(BATT_DOD*100)}%. An illustrative partial load assumes all LOW including curtain strips, 50% of HIGH wattage and 30% of other wattage, plus estimated standby; this is not measured or a promised dimming setting.",
    "The 12.6 W standby allowance is added on top of assumed operating supply losses as a conservative allowance, not a measured value. Linear dimming and aggregate power factor are assumptions; PIR lights are switched, not necessarily dimmable. Actual controls, battery chemistry, ageing, surge and derating affect sizing.",
    "LIGHTING ONLY. Fans, refrigerator, Wi-Fi, TV, pumps, lift and sockets must be added before choosing an inverter. A licensed electrician must confirm the inverter VA, battery bank, changeover wiring and which circuits go on backup.",
]

# ---------------- XLSX ----------------
wb = Workbook()
H = Font(bold=True, color="FFFFFF"); HF = PatternFill("solid", fgColor="2F3B4C")
TF = PatternFill("solid", fgColor="E8EDF3"); B = Font(bold=True)
thin = Side(style="thin", color="BBBBBB"); BOR = Border(top=thin, bottom=thin, left=thin, right=thin)

def table(ws, r0, headers, data, fmts, total=None, widths=None):
    for j, h in enumerate(headers, 1):
        c = ws.cell(r0, j, h); c.font = H; c.fill = HF; c.alignment = Alignment(wrap_text=True, vertical="center"); c.border = BOR
    ws.row_dimensions[r0].height = 45
    rr = r0
    for row in data + ([total] if total else []):
        rr += 1
        for j, (v, f) in enumerate(zip(row, fmts), 1):
            c = ws.cell(rr, j, v); c.border = BOR
            if f: c.number_format = f
            if total and row is total: c.font = B; c.fill = TF
    if widths:
        for j, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(j)].width = w
    return rr

ws = wb.active; ws.title = "Per room"
ws["A1"] = "Per-room lumens and lighting wattage - one modelled flat"; ws["A1"].font = Font(bold=True, size=13)
hdr = ["Room", "Code", "Fittings", "Area m²", "Area sq ft", "Contractor target lm (20/sq ft)",
       "HIGH lm", "LOW lm", "Task/accent lm", "Scheduled lm total", "Scheduled lm/sq ft", "% of contractor target", "HIGH-only % of target",
       "HIGH W", "LOW W", "Task/accent W", "LED W (base)", "Curtain-strip W", "LED W incl. curtain",
       "Input W incl. supply loss", "Contractor W (target lm/100)", "Rule W (scheduled lm/100)", "Design lm/W"]
keys = ["name", "id", "n", "m2", "sqft", "target_lm", "lm_HIGH", "lm_LOW", "lm_OTHER", "lm", "lm_per_sqft", "pct_target", "pct_high",
        "W_HIGH", "W_LOW", "W_OTHER", "W", "curtain_W", "W_all", "W_input", "rule_W_target", "rule_W_installed", "lm_per_W"]
fm = [None, None, "0", "0.00", "0", "#,##0", "#,##0", "#,##0", "#,##0", "#,##0", "0.0", "0%", "0%", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0", "0", "0"]
data = [[r[k] / 100 if k in ("pct_target", "pct_high") else r[k] for k in keys] for r in rows]
tot = [T[k] / 100 if k in ("pct_target", "pct_high") else T[k] for k in keys]
end = table(ws, 3, hdr, data, fm, tot, [20, 6, 8, 8, 9, 12, 9, 9, 10, 11, 10, 10, 10, 8, 8, 9, 9, 9, 10, 11, 11, 11, 8])
ws.freeze_panes = "C4"

ws2 = wb.create_sheet("Flat & building")
ws2["A1"] = "Lighting load totals and inverter planning (lighting only)"; ws2["A1"].font = Font(bold=True, size=13)
r = table(ws2, 3, ["Item", "Per flat", f"Per floor ({FLATS_PER_FLOOR} flats)", f"Whole building ({FLATS} flats)"],
          [[k, a, b, c] for k, (a, b, c) in inv.items()], [None, "#,##0.00", "#,##0.00", "#,##0.00"], widths=[58, 20, 24, 24])
r = table(ws2, r + 2, ["Backup energy", "Per flat", f"Per floor ({FLATS_PER_FLOOR} flats)", f"Whole building ({FLATS} flats)"],
          [[k, a, b, c] for k, (a, b, c) in energy.items()], [None, "0.00", "0.00", "0.00"])
r = table(ws2, r + 2, ["Battery guide (illustrative load)", "Per flat", f"Per floor ({FLATS_PER_FLOOR} flats)", f"Whole building ({FLATS} flats)"],
          [[k, a, b, c] for k, (a, b, c) in batt.items()], [None, None, None, None])

ws3 = wb.create_sheet("Fittings")
fh = ["Fitting", "Room", "Group", "Layer", "Description", "Supply", "Circuit", "CCT K", "W", "lm", "Hold IDs", "Viewer model ON allowed"]
fdata = [[f["id"], f["room"], grp(f), layer[f["id"]], f["desc"], f["supply"], f["circuit"], f["cct"], f["W_nominal"], f["lm"],
          "; ".join(hold_ids.get(f["id"], [])), "Yes (site held)" if f["id"] in CBR_REVIEW_ON
          else "No" if hold_ids.get(f["id"]) else "Yes"] for f in fx]
table(ws3, 1, fh, fdata, [None] * 8 + ["0.00", "#,##0", None, None],
      [None, None, "TOTAL", None, None, None, None, None, T["W"], T["lm"], None, None],
      [10, 6, 8, 9, 60, 8, 8, 7, 8, 8, 22, 16])
ws3.freeze_panes = "A2"

ws4 = wb.create_sheet("Assumptions")
for i, a in enumerate(ASSUMPTIONS, 1):
    c = ws4.cell(i, 1, f"{i}. {a}"); c.alignment = Alignment(wrap_text=True, vertical="top")
    ws4.row_dimensions[i].height = 48
ws4.column_dimensions["A"].width = 140
xlsx = os.path.join(HERE, "lighting-load-per-room.xlsx")
wb.save(xlsx)

# ---------------- PDF ----------------
ss = getSampleStyleSheet()
small = ParagraphStyle("s", parent=ss["Normal"], fontSize=8, leading=10)
cell = ParagraphStyle("c", parent=ss["Normal"], fontSize=7.5, leading=9)
pdf = os.path.join(HERE, "lighting-load-per-room.pdf")
doc = SimpleDocTemplate(pdf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                        title="Lighting load and lumen schedule", author="House lighting plan")
ST = TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F3B4C")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                 ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                 ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8EDF3")), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")])
def f0(v): return f"{v:,.0f}"
def f1(v): return f"{v:,.1f}"
story = [Paragraph("Lighting load and lumen schedule - per room, per flat, per floor, whole building", ss["Title"]),
         Paragraph(f"Working assumption: {STOREYS} storeys x {FLATS_PER_FLOOR} modelled flat per floor = {FLATS} flats; confirm floor and flat count and variations on site. Lighting only. Master SHA-256 {sha[:16]}...; 104 fittings + 4 provisional curtain strips per flat.", small),
         Spacer(1, 4 * mm),
         Paragraph("1. Per room (one flat): area, contractor target, scheduled lumens and watts", ss["Heading3"])]
h1 = ["Room", "Fit-\ntings", "Area\nm²", "Area\nsq ft", "Target lm\n20/sq ft", "HIGH\nlm", "LOW\nlm", "Task/acc.\nlm", "Total\nlm", "lm /\nsq ft",
      "% of\ntarget", "HIGH\nonly %", "HIGH\nW", "LOW\nW", "Task/acc.\nW", "LED W\nbase", "Curtain\nW", "Input W\n(incl. loss)", "Contractor\nW (lm/100)"]
def prow(r):
    return [r["name"], r["n"], f"{r['m2']:.2f}", f0(r["sqft"]), f0(r["target_lm"]), f0(r["lm_HIGH"]), f0(r["lm_LOW"]), f0(r["lm_OTHER"]),
            f0(r["lm"]), f1(r["lm_per_sqft"]), f"{r['pct_target']:.0f}%", f"{r['pct_high']:.0f}%", f1(r["W_HIGH"]), f1(r["W_LOW"]), f1(r["W_OTHER"]),
            f1(r["W"]), f1(r["curtain_W"]), f1(r["W_input"]), f0(r["rule_W_target"])]
t = Table([h1] + [prow(r) for r in rows] + [prow(T)], repeatRows=1)
t.setStyle(ST); story += [t, Spacer(1, 3 * mm),
    Paragraph("Read it like this: 'Target lm' is the contractor's 20 lm/sq ft rule. 'Total lm' is what the planned fittings emit. "
              "Above 100% means the plan has more source light than the rule; coves and strips (LOW) bounce off the ceiling, so part of that is mood light, not task light. "
              "'HIGH only %' compares the functional HIGH layer, including mirror lights, with the rule. 'Contractor W' is the rule's 1 W per 100 lm applied to the target; 'LED W base' is scheduled wattage.", small),
    PageBreak(), Paragraph("2. Totals and inverter planning (lighting only)", ss["Heading3"])]
t2 = Table([["Item", "Per flat", f"Per floor ({FLATS_PER_FLOOR} flats)", f"Whole building ({FLATS} flats)"]] +
           [[Paragraph(k, cell), f"{a:,.2f}", f"{b:,.2f}", f"{c:,.2f}"] for k, (a, b, c) in inv.items()] +
           [[Paragraph(k, cell), f"{a:,.2f}", f"{b:,.2f}", f"{c:,.2f}"] for k, (a, b, c) in energy.items()] +
           [[Paragraph(k, cell), a, b, c] for k, (a, b, c) in batt.items()],
           colWidths=[130 * mm, 35 * mm, 45 * mm, 55 * mm])
st2 = TableStyle(ST.getCommands()[:-2]); t2.setStyle(st2)
story += [t2, Spacer(1, 4 * mm), Paragraph("3. Assumptions and limits", ss["Heading3"])]
story += [Paragraph(f"{i}. {a}", small) for i, a in enumerate(ASSUMPTIONS, 1)]
doc.build(story)

summary = dict(master_sha256=sha, generator_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
               outputs={os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in (xlsx, pdf)},
               fittings=104, per_flat=dict(target_lm=round(T["target_lm"]), installed_lm=T["lm"],
               lm_HIGH=T["lm_HIGH"], lm_LOW=T["lm_LOW"], lm_OTHER=T["lm_OTHER"], W_base=round(T["W"], 1), W_curtain=round(T["curtain_W"], 1),
               W_input=round(T["W_input"], 1), standby_W=standby, planning_W=round(flat_input, 1), contractor_W=round(T["rule_W_target"]),
               typical_W=round(typical_in, 1), area_sqft=round(T["sqft"])),
               per_floor=dict(planning_kW=round(kw(floor_input), 2), kVA_pf=round(floor_input / PF / 1000, 2), typical_kW=round(kw(typical_in * FLATS_PER_FLOOR), 2)),
               building=dict(storeys=STOREYS, flats_per_floor=FLATS_PER_FLOOR, flats=FLATS, planning_kW=round(kw(bldg_input), 2), kVA_pf=round(bldg_input / PF / 1000, 2), typical_kW=round(kw(typical_in * FLATS), 2)),
               rows=[{k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()} for r in rows])
json.dump(summary, open(os.path.join(HERE, "lighting-load-summary.json"), "w"), indent=1)
print(json.dumps(summary["per_flat"], indent=1)); print(summary["building"])
for r in rows: print(f"{r['id']:4} {r['sqft']:6.0f}sqft tgt{r['target_lm']:6.0f} inst{r['lm']:6.0f} {r['pct_target']:4.0f}% W{r['W']:6.1f} +c{r['curtain_W']:4.1f} in{r['W_input']:6.1f} rule{r['rule_W_target']:4.0f}")
