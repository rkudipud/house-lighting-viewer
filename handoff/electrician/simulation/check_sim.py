"""Independent checks + analysis for the exploratory Radiance simulation (sim_radiance.py).

A. engine benchmarks against exact closed forms (isotropic point source, cos^m disc, Lambertian rectangle, integrating cube)
B. structural checks on runs/base/sim-results.json: units, shapes, finite/non-negative values, fixture accounting,
   coverage of every room grid incl. the L-shaped children's room (CBR H1-H6, desk) and the canonical pooja niche planes
C. comparison against the delivered analytic results (lighting-current-review/calc-results-current.json) on identical
   grids/masks, plus the same compliance grading rule (criteria bands in the master)
D. sensitivity: reflectance, beam, ceiling height, cove pocket, kitchen slot (paired runs at identical sampling), and the
   linear lumen +-20 % / MF 0.7-0.9 scalings
Writes analysis/checks.json, analysis/sim-summary.json, analysis/sim-heatmaps.json. Read-only on every other file.
"""
import hashlib, json, math, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = sys.argv[:1]
import sim_radiance as S                       # noqa: E402  (hash-guards the master on import)
from fm_calc_rooms import grade, HIGH_BAND, LOW_LANES      # noqa: E402
from fm_circuits import SCENES                 # noqa: E402
from fm_rooms import R, FIX                    # noqa: E402

SESSION = S.SESSION
ANALYTIC = os.path.join(SESSION, "lighting-current-review", "calc-results-current.json")
OUT = os.path.join(HERE, "analysis")
checks = []


def check(name, ok, **ev):
    checks.append(dict(check=name, result="PASS" if ok else "FAIL", **ev)); print(("PASS " if ok else "FAIL ") + name, ev if not ok else "")


def rc(octp, pts, mods=None, ab=0, ad=512, lw=1e-6, dj=0.7):
    env = dict(os.environ, RAYPATH=S.RADLIB + os.pathsep + HERE)
    cmd = [os.path.join(S.RADBIN, "rcontrib.exe"), "-h", "-V+", "-I+", "-ab", str(ab), "-ad", str(ad), "-lw", str(lw), "-dj", str(dj),
           "-ds", "0.02", "-dt", "0", "-dc", "1", "-st", "0", "-ss", "0"]
    for m in mods: cmd += ["-m", m]
    r = subprocess.run(cmd + [octp], input="".join(" ".join(map(str, p)) + "\n" for p in pts).encode(), capture_output=True, env=env, cwd=HERE)
    if r.returncode: raise RuntimeError(r.stderr.decode())
    return np.array(r.stdout.split(), float).reshape(len(pts), len(mods), 3)[:, :, 1].sum(axis=1)


def oconv(work, name, text):
    with open(os.path.join(work, name + ".rad"), "w") as fh: fh.write(text)
    octp = os.path.join(work, name + ".oct")
    with open(octp, "wb") as fh:     subprocess.run([os.path.join(S.RADBIN, "oconv.exe"), "-f", name + ".rad"], cwd=work, stdout=fh, check=True)
    return octp


# ------------------------------------------------------------------ A. engine benchmarks
def engine_benchmarks():
    work = os.path.join(OUT, "engine-benchmarks"); os.makedirs(work, exist_ok=True)
    res = {}
    # A1 isotropic sphere source, black surroundings: E = Phi/(4 pi d^2) cos
    octp = oconv(work, "a1", "void light L\n0\n0\n3 1000 1000 1000\nL sphere s\n0\n0\n4 0 0 2 0.01\n")
    Phi = 1000 * math.pi * 4 * math.pi * 0.01 ** 2
    pts = [(x, 0, 0, 0, 0, 1) for x in (0, 1, 2)]
    sim = rc(octp, pts, ["L"]); ex = np.array([Phi / (4 * math.pi) * 2 / (x * x + 4) ** 1.5 for x in (0, 1, 2)])
    err = float(np.max(np.abs(sim / ex - 1))); res["A1_point_source_max_rel_err"] = err; check("A1 isotropic point source vs inverse-square cosine law", err < 0.005, max_rel_err=round(err, 5))
    # A2 cos^m disc as written by the simulator (DL 60 deg beam, 800 lm), floor 2.2 m below
    sc = S.Scene(dict(x=0.0)); m = S.E.m_from_beam(60.0); k = sc.disc("T", (0, 0, 2.2), (0, 0, -1), 800.0, m)
    octp = oconv(work, "a2", "\n".join(sc.lines))
    pts = [(x, 0, 0, 0, 0, 1) for x in (0, 0.5, 1.0, 1.5, 2.5)]
    I0 = 800 * (m + 1) / (2 * math.pi)
    ex = np.array([I0 * (2.2 / math.hypot(x, 2.2)) ** m * 2.2 / math.hypot(x, 2.2) ** 3 for x in (0, 0.5, 1.0, 1.5, 2.5)])
    # deterministic source sampling (-dj 0) isolates distribution + flux normalisation from jitter noise
    sim = rc(octp, pts, [k], dj=0)
    err = float(np.max(np.abs(sim / ex - 1))); res["A2_cosm_disc_max_rel_err"] = err
    check("A2 cos^m downlight (simulator primitive) vs I0 cos^m law, flux-normalised (-dj 0)", err < 0.01, m=round(m, 3), max_rel_err=round(err, 5))
    # production jitter (-dj 0.7): single-pass point noise reported; mean of 8 repeats must still meet 1 %
    reps = np.array([rc(octp, pts, [k]) for _ in range(8)])
    single = float(np.max(np.abs(reps / ex - 1))); err8 = float(np.max(np.abs(reps.mean(axis=0) / ex - 1)))
    res["A2b_jitter_single_pass_max_rel_err"] = single; res["A2b_jitter_mean8_max_rel_err"] = err8
    check("A2b cos^m downlight with production jitter (-dj 0.7): mean of 8 passes vs law", err8 < 0.01, single_pass_max_rel_err=round(single, 5), mean8_max_rel_err=round(err8, 5))
    # A3 Lambertian rectangle (simulator strip primitive) 1.2 x 0.01 m, 500 lm, 1.5 m above the point: corner-sum view factor
    sc = S.Scene(dict(x=0.0)); k = sc.lamb_rect("T", [(-0.6, -0.005, 1.5), (0.6, -0.005, 1.5), (0.6, 0.005, 1.5), (-0.6, 0.005, 1.5)], (0, 0, -1), 500.0)
    octp = oconv(work, "a3", "\n".join(sc.lines)); L = 500 / (math.pi * 1.2 * 0.01)

    def corner(a, b, c):
        A, B = a / c, b / c
        return 0.5 * L * (A / math.sqrt(1 + A * A) * math.atan(B / math.sqrt(1 + A * A)) + B / math.sqrt(1 + B * B) * math.atan(A / math.sqrt(1 + B * B)))
    sim = rc(octp, [(0, 0, 0, 0, 0, 1)], [k]); ex = 4 * corner(0.6, 0.005, 1.5)
    err = abs(sim[0] / ex - 1); res["A3_lambertian_strip_rel_err"] = err; check("A3 Lambertian strip (simulator primitive) vs exact view factor", err < 0.01, sim=round(sim[0], 3), exact=round(ex, 3))
    # A4 integrating cube rho 0.5: mean indirect = Phi rho/(A(1-rho)) truncated to ab bounces
    rho, Sd = 0.5, 3.0
    txt = f"void plastic w\n0\n0\n5 {rho} {rho} {rho} 0 0\nvoid light L\n0\n0\n3 1000 1000 1000\nL sphere s\n0\n0\n4 1.5 1.5 1.5 0.05\n"
    F = [[(0, 0, 0), (0, Sd, 0), (Sd, Sd, 0), (Sd, 0, 0)], [(0, 0, Sd), (Sd, 0, Sd), (Sd, Sd, Sd), (0, Sd, Sd)], [(0, 0, 0), (Sd, 0, 0), (Sd, 0, Sd), (0, 0, Sd)],
         [(0, Sd, 0), (0, Sd, Sd), (Sd, Sd, Sd), (Sd, Sd, 0)], [(0, 0, 0), (0, 0, Sd), (0, Sd, Sd), (0, Sd, 0)], [(Sd, 0, 0), (Sd, Sd, 0), (Sd, Sd, Sd), (Sd, 0, Sd)]]
    for i, f in enumerate(F): txt += f"w polygon p{i}\n0\n0\n12 " + " ".join(str(v) for p in f for v in p) + "\n"
    octp = oconv(work, "a4", txt); Phi = 1000 * math.pi * 4 * math.pi * 0.05 ** 2
    g = np.linspace(0.15, 2.85, 10); X, Y = np.meshgrid(g, g); pts = [(x, y, 0.001, 0, 0, 1) for x, y in zip(X.ravel(), Y.ravel())]
    Ed = (Phi / (4 * math.pi)) * 1.5 / ((X - 1.5) ** 2 + (Y - 1.5) ** 2 + 1.5 ** 2) ** 1.5
    full = Phi * rho / (6 * Sd * Sd * (1 - rho))
    for ab in (2, 5, 8):
        ind = float((rc(octp, pts, ["L"], ab=ab, ad=512, lw=1e-6) - Ed.ravel()).mean()); exp_ = full * (1 - rho ** ab)
        res[f"A4_cube_ab{ab}"] = dict(sim=ind, expected_truncated=exp_, expected_infinite=full)
        check(f"A4 integrating cube rho 0.5, ab {ab}: indirect vs truncated series", abs(ind / exp_ - 1) < 0.03, sim=round(ind, 4), expected=round(exp_, 4),
              captured_of_infinite=round(ind / full, 4))
    return res


# ------------------------------------------------------------------ helpers on results
def load(run):
    p = os.path.join(HERE, "runs", run, "sim-results.json")
    return json.load(open(p)) if os.path.exists(p) else None


def lane_sum(enc, tag, lanes, levels=None):
    out = None
    for fid, f in enc["fixtures"].items():
        lv = (levels.get(f["lane"], 0.0) or 0.0) if levels is not None else (1.0 if f["lane"] in lanes else 0.0)
        if lv == 0: continue
        v = lv * np.array(f["E"][tag]); out = v if out is None else out + v
    n = len(enc["points"][tag]); return out if out is not None else np.zeros(n)


def room_lane(enc, rid, tag, lanes):
    out = np.zeros(len(enc["points"][tag]))
    for f in enc["fixtures"].values():
        if f["room"] == rid and f["lane"] in lanes: out += np.array(f["E"][tag])
    return out


def st(v, task_flat):
    t = v[task_flat]; a = float(t.mean()) if t.size else 0.0
    return dict(avg=round(a), min=round(float(t.min())) if t.size else 0, U0=round(float(t.min()) / a, 2) if a > 0 else 0.0, avg_room=round(float(v.mean())))


def masked_task(meta):
    m = np.array(meta["mask"], bool); t = np.array(meta["task"], bool); return t[m]


# ------------------------------------------------------------------ B. structural checks
def structural(res):
    encs = res["enclosures"]; B = {}
    check("B0 base run bound to master b6f6bf1a and units declared", res["master_sha256"] == S.EXPECTED_MASTER and "lux" in res["units"]["E"],
          master=res["master_sha256"][:8], units=res["units"])
    covered = {r for e in encs.values() for r in e["rooms"]}
    check("B1 every room with fixtures is simulated", covered == set(R), missing=sorted(set(R) - covered))
    fix_all = {f["id"]: rid for rid in R for f in R[rid]["fixtures"]}
    seen = {fid for e in encs.values() for fid in e["fixtures"]}; skipped = {fid: why for e in encs.values() for fid, why in e["skipped"].items()}
    check("B2 fixture accounting: simulated + reported-skipped = all lux-credited fixtures in the master lighting inputs",
          seen | set(skipped) == set(fix_all) and not (seen & set(skipped)), simulated=len(seen), skipped=skipped, total=len(fix_all))
    bad = []; shapes = {}
    for eid, e in encs.items():
        for tag, P in e["points"].items():
            for fid, f in e["fixtures"].items():
                v = np.array(f["E"][tag])
                if v.shape != (len(P),) or not np.all(np.isfinite(v)) or v.min() < -1e-6: bad.append((eid, fid, tag))
        for tag, m in e["meta"].items():
            if tag.startswith("grid:"):
                rid = tag[5:]; G = S.room_grids(R[rid]); mm = np.array(m["mask"], bool)
                shapes[rid] = dict(grid=list(mm.shape), points=int(mm.sum()))
                if list(G["X"].shape) != m["grid_shape"] or not np.array_equal(G["mask"], mm) or int(mm.sum()) != len(e["points"][tag]): bad.append((eid, "grid", tag))
    check("B3 every result vector has one finite, non-negative lux value per point; room grids identical to the analytic heat-map grids/masks",
          not bad, bad=bad[:10], grid_shapes=shapes)
    outside = []
    for eid, e in encs.items():
        poly = e["poly_ft"]
        for rid in e["rooms"]:
            for f in R[rid]["fixtures"]:
                P = f.get("pts") or [(f["x"], f["z"])]
                out = [p for p in P if not S.E.point_in_poly(p[0], p[1], poly) and S.seg_dist(np.array([p], float), np.array(poly, float))[0] > 0.02]
                if out: outside.append(dict(fixture=f["id"], enclosure=eid, n_outside=len(out), example_ft=[round(float(c), 3) for c in out[0]]))
    known = {"KIT-L1", "LIV-P1"}
    check("B4 fixture positions inside their simulated enclosures (known exceptions reported, not moved)", {o["fixture"] for o in outside} <= known,
          outside=outside)
    B["fixtures_outside_enclosure"] = outside
    cb = encs.get("CBR")
    if cb:
        hs = [f"CBR-H{i}" for i in range(1, 7)]
        contrib = {h: round(float(np.mean(cb["fixtures"][h]["E"]["grid:CBR"])), 1) for h in hs if h in cb["fixtures"]}
        desk = np.array(cb["points"]["cbr_desk"]); ox, oz = next(r for r in S.DI["rooms"] if r["id"] == "CBR")["frame"]["origin_xz_m"]
        inpoly = all(S.E.point_in_poly(p[0] / S.FT, p[1] / S.FT, R["CBR"]["poly"]) for p in desk)
        m = cb["meta"]["grid:CBR"]; mm = np.array(m["mask"], bool)
        check("B5 children's room coverage: L-shaped grid fully masked, H1-H6 simulated and lighting it, desk grid inside the room",
              len(contrib) == 6 and min(contrib.values()) > 1 and inpoly and int(mm.sum()) == len(cb["points"]["grid:CBR"]),
              H_mean_lx_on_grid=contrib, desk_points=len(desk), desk_shape=cb["meta"]["cbr_desk"]["shape"], grid_points=int(mm.sum()),
              poly_ft=R["CBR"]["poly"])
    h = encs.get("HALL")
    if h:
        nc = S.canonical_niche(); back = np.array(h["points"]["pooja:canonical_back"]); op = np.array(h["points"]["pooja:canonical_opening"])
        okz = back[:, 1].min() >= nc["z_m"][0] and back[:, 1].max() <= nc["z_m"][1] and back[:, 2].min() >= nc["sill"] and back[:, 2].max() <= nc["top"]
        p2 = h["fixtures"].get("LIV-P2"); pts = h["points"]["pooja:points"]
        check("B6 pooja coverage: canonical niche back/opening planes sampled inside the canonical aperture; inherited records reported",
              okz and len(back) == len(op) > 0 and "LIV-P1" in h["skipped"], back_shape=h["meta"]["pooja:canonical_back"]["shape"],
              niche_z_m=nc["z_m"], sill_top_m=[nc["sill"], round(nc["top"], 4)], depth_m_HOLD=nc["depth"],
              LIV_P2_aim_ft=list(FIX["LIV-P2"]["aim"]))
    return B


# ------------------------------------------------------------------ C. comparison with the analytic model
def compare(res, ana):
    encs = res["enclosures"]; rooms = {}
    for e in encs.values():
        for rid in e["rooms"]:
            tag = f"grid:{rid}"; tf = masked_task(e["meta"][tag]); a = ana["rooms"].get(rid, {})
            hi = room_lane(e, rid, tag, ("HIGH",)); lo = room_lane(e, rid, tag, LOW_LANES)
            # the open-plan hall: neighbour-room light also reaches each grid (analytic treats LIV and DIN separately)
            hi_all = lane_sum(e, tag, ("HIGH",)); lo_all = lane_sum(e, tag, LOW_LANES)
            row = dict(sim=dict(), analytic=a.get("combinations", {}), analytic_scenes=a.get("scenes", {}))
            if hi.any(): row["sim"]["HIGH_100"] = st(hi, tf)
            if lo.any(): row["sim"]["LOW_100"] = st(lo, tf)
            if hi.any() and lo.any(): row["sim"]["HIGH+LOW_100"] = st(hi + lo, tf)
            if len(e["rooms"]) > 1:
                row["sim"]["HIGH_100_incl_open_plan_neighbour"] = st(hi_all, tf); row["sim"]["LOW_100_incl_open_plan_neighbour"] = st(lo_all, tf)
            row["sim_lanes_100"] = {ln: st(room_lane(e, rid, tag, (ln,)), tf) for ln in sorted({f["lane"] for f in e["fixtures"].values() if f["room"] == rid})}
            row["sim_scenes"] = {}
            for sname, lv in SCENES.items():
                if sname not in ("Mood", "Relax", "Work", "Full"): continue
                v = np.zeros(len(tf))
                for f in e["fixtures"].values():
                    if f["room"] == rid: v += (lv.get(f["lane"], 0.0) or 0.0) * np.array(f["E"][tag])
                row["sim_scenes"][sname] = st(v, tf)
            if rid in HIGH_BAND and "HIGH_100" in row["sim"]:
                lo_b, hi_b, ut = HIGH_BAND[rid]; s = row["sim"]["HIGH_100"]
                row["grade_HIGH_100"] = dict(sim=grade(s["avg"], lo_b, hi_b, s["U0"], ut), band=[lo_b, hi_b, ut],
                                             analytic=grade(a["combinations"]["HIGH_100"]["avg"], lo_b, hi_b, a["combinations"]["HIGH_100"]["U0"], ut) if "HIGH_100" in a.get("combinations", {}) else None)
            for k in ("HIGH_100", "LOW_100", "HIGH+LOW_100"):
                if k in row["sim"] and k in row["analytic"] and row["analytic"][k]["avg"]:
                    row.setdefault("ratio_sim_over_analytic_avg", {})[k] = round(row["sim"][k]["avg"] / row["analytic"][k]["avg"], 2)
            rooms[rid] = row
    tasks = {}
    if "KIT" in encs:
        e = encs["KIT"]; v = room_lane(e, "KIT", "kit_worktop", ("HIGH", "TASK")); P = np.array(e["points"]["kit_worktop"]) / S.FT
        z = {"left run under wall cabinet (x<=4.3, z<=11.1)": (P[:, 0] <= 4.3) & (P[:, 1] <= 11.1), "sink/window end, no wall cabinet (x<=4.3, z>11.1)": (P[:, 0] <= 4.3) & (P[:, 1] > 11.1),
             "top run incl. window section (z<=7.4, x>4.3)": (P[:, 1] <= 7.4) & (P[:, 0] > 4.3)}
        i = int(np.argmin(v))
        tasks["kitchen_worktop_HIGH+TASK_100"] = dict(sim=dict(**st(v, np.ones(len(v), bool)), weakest_point_ft=[round(float(c), 2) for c in P[i, :2]],
                                                        zones={k: dict(avg=round(float(v[m].mean())), min=round(float(v[m].min()))) for k, m in z.items()}),
                                                     analytic=ana["kitchen_worktop"]["final_cell_grid_0.1m_HIGH+TASK_100"], target=ana["kitchen_worktop"]["target"])
        lv = SCENES["Work"]; w = sum((lv.get(f["lane"], 0) or 0) * np.array(f["E"]["kit_worktop"]) for f in e["fixtures"].values())
        tasks["kitchen_worktop_Work_scene"] = dict(sim=st(w, np.ones(len(w), bool)), analytic=ana["kitchen_worktop"]["final_Work_scene(HIGH100,TASK85,COVE50)"], levels=lv)
    if "CBR" in encs:
        e = encs["CBR"]; d = ana["children"]["desk"]; one = lambda v: dict(**st(v, np.ones(len(v), bool)), max=round(float(v.max())))
        hi = room_lane(e, "CBR", "cbr_desk", ("HIGH",)); sd = room_lane(e, "CBR", "cbr_desk", ("STUDY",))
        tasks["children_desk"] = dict(sim=dict(HIGH_100=one(hi), STUDY_100=one(sd), HIGH_STUDY_100=one(hi + sd)),
                                      analytic={k: d[k] for k in ("HIGH_100", "STUDY_100", "HIGH_STUDY_100")}, target=d["target"])
    if "HALL" in encs:
        e = encs["HALL"]; out = {}
        for tag in ("pooja:canonical_back", "pooja:canonical_opening"):
            for ln in ("ACCENT", "HIGH", "COVE"):
                v = lane_sum(e, tag, (ln,)); out[f"{tag}:{ln}_100"] = dict(avg=round(float(v.mean()), 1), min=round(float(v.min()), 1), max=round(float(v.max()), 1))
        labels = e["meta"]["pooja:points"]["labels"]
        out["points_lx_100"] = {lab: {ln: round(float(lane_sum(e, "pooja:points", (ln,))[i]), 1) for ln in ("ACCENT", "HIGH", "COVE", "LINE")} for i, lab in enumerate(labels)}
        sp = out["points_lx_100"]; acc = [sp[l]["ACCENT"] for l in labels]
        out["accent_ratio_canonical_idol_vs_surround"] = round(acc[0] / max(1e-6, (sp[labels[3]]["HIGH"] + sp[labels[4]]["HIGH"]) / 2 + (sp[labels[3]]["COVE"] + sp[labels[4]]["COVE"]) / 2), 2)
        out["finding"] = ("LIV-P2 (as recorded) is aimed at the inherited idol point behind the wall face; its beam lands on the wall south of the canonical niche, "
                          "so the canonical niche receives little accent light. Pooja accent remains HOLD until the niche is measured and the spot aim/strip are re-set.")
        out["analytic_status"] = ana["pooja"]["status"]; tasks["pooja"] = out
    if "LOB" in encs:
        e = encs["LOB"]; v = lane_sum(e, "lobby_face", ("HIGH", "MIRROR")); h = lane_sum(e, "lobby_face", ("HIGH",))
        tasks["lobby_face_Ev"] = dict(sim={"HIGH+bar": dict(avg=round(float(v.mean())), min=round(float(v.min())), max=round(float(v.max()))),
                                           "HIGH_only": dict(avg=round(float(h.mean())))}, analytic=ana["lobby_face"])
    return rooms, tasks


# ------------------------------------------------------------------ D. sensitivity
SENS_GROUPS = [  # (dir prefix, rooms this group is reported for, sampling)
    ("sens128-", ("MBR", "CBR"), "ab 8 / ad 128"),
    ("sens512kit-", ("KIT",), "ab 8 / ad 512"),
    ("sens128hall-", ("LIV", "DIN"), "ab 8 / ad 128"),
]


def sensitivity():
    out = {}; full = load("base"); runs = sorted(os.listdir(os.path.join(HERE, "runs")))
    if not load("sens128-base"): return {"status": "not run"}
    out["groups"] = {}
    for pre, use, samp in SENS_GROUPS:
        base = load(pre + "base")
        if not base: out["groups"][pre] = dict(status="not run", rooms=use); continue
        dev = {}
        for eid, b in base["enclosures"].items():
            for rid in b["rooms"]:
                tag = f"grid:{rid}"; tf = masked_task(b["meta"][tag])
                for name, lanes in (("HIGH_100", ("HIGH",)), ("LOW_100", LOW_LANES)):
                    s0 = room_lane(full["enclosures"][eid], rid, tag, lanes); s1 = room_lane(b, rid, tag, lanes)
                    if s0.any(): dev[f"{rid}:{name}"] = round(100 * (s1[tf].mean() / s0[tf].mean() - 1), 2)
        used = {k: v for k, v in dev.items() if k.split(":")[0] in use}
        out["groups"][pre] = dict(sampling=samp, rooms=use, baseline_vs_base_run_pct=dev,
                                  superseded={k: v for k, v in dev.items() if k not in used})
        check(f"D1 sweep baseline {pre}base ({samp}) vs base run (ab 8 / ad 512): room-mean difference for {'/'.join(use)}",
              max(abs(x) for x in used.values()) < 6, max_abs_pct=max(abs(x) for x in used.values()))
        for d in runs:
            if not d.startswith(pre) or d == pre + "base": continue
            r = load(d)
            if not r: continue
            v = d[len(pre):]; out.setdefault(v, {})
            for eid, e in r["enclosures"].items():
                b = base["enclosures"][eid]
                for rid in e["rooms"]:
                    if rid not in use: continue
                    tag = f"grid:{rid}"; tf = masked_task(e["meta"][tag]); row = dict(sampling=samp, run=d)
                    for name, lanes in (("HIGH_100", ("HIGH",)), ("LOW_100", LOW_LANES)):
                        s1 = room_lane(e, rid, tag, lanes); s0 = room_lane(b, rid, tag, lanes)
                        if s0.any(): row[name] = dict(avg_change_pct=round(100 * (s1[tf].mean() / s0[tf].mean() - 1), 1), U0=[st(s0, tf)["U0"], st(s1, tf)["U0"]],
                                                      avg=[st(s0, tf)["avg"], st(s1, tf)["avg"]])
                    if rid == "KIT":
                        s1 = room_lane(e, rid, "kit_worktop", ("HIGH", "TASK")); s0 = room_lane(b, rid, "kit_worktop", ("HIGH", "TASK"))
                        row["worktop_HIGH+TASK"] = dict(avg=[round(s0.mean()), round(s1.mean())], min=[round(s0.min()), round(s1.min())])
                        c1 = room_lane(e, rid, tag, ("COVE",)); c0 = room_lane(b, rid, tag, ("COVE",))
                        row["COVE_100"] = dict(avg=[round(c0[tf].mean()), round(c1[tf].mean())])
                    if rid == "CBR":
                        s1 = room_lane(e, rid, "cbr_desk", ("HIGH", "STUDY")); s0 = room_lane(b, rid, "cbr_desk", ("HIGH", "STUDY"))
                        row["desk_HIGH+STUDY"] = dict(avg=[round(s0.mean()), round(s1.mean())], min=[round(s0.min()), round(s1.min())])
                    out[v][rid] = row
    out["lumens_plus_minus_20pct"] = "linear: every value x0.8 / x1.2 (no rerun needed)"
    out["MF_0.7_0.9"] = "linear: every value x0.875 / x1.125 relative to MF 0.8"
    return out


def sampling_convergence():
    a, b = load("smoke3"), load("smoke4")
    if not (a and b): return {"status": "not available"}
    rows = {}
    for fid in a["enclosures"]["KIT"]["fixtures"]:
        x = np.array(a["enclosures"]["KIT"]["fixtures"][fid]["E"]["grid:KIT"]); y = np.array(b["enclosures"]["KIT"]["fixtures"][fid]["E"]["grid:KIT"])
        rows[fid] = dict(mean_ad1024=round(x.mean(), 2), mean_ad128=round(y.mean(), 2), mean_diff_pct=round(100 * (y.mean() / x.mean() - 1), 2),
                         point_rms_pct=round(100 * np.sqrt(np.mean((y - x) ** 2)) / x.mean(), 1))
    worst = max(abs(r["mean_diff_pct"]) for r in rows.values())
    check("D0 sampling convergence (KIT ab 8: ad 128 vs ad 1024): room-mean difference per fixture", worst < 6, worst_mean_diff_pct=worst)
    return dict(reference="runs/smoke3 (ab 8 ad 1024 lw 1e-6)", test="runs/smoke4 (ab 8 ad 128 lw 1e-5)", per_fixture=rows,
                note="direct-dominated fittings converge within 1 %; the fully indirect kitchen slot cove is the noisiest term (~5 % mean, ~50 % per point at ad 128); base run uses ad 512")


def heatmaps(res):
    out = {}
    for e in res["enclosures"].values():
        for rid in e["rooms"]:
            tag = f"grid:{rid}"; m = np.array(e["meta"][tag]["mask"], bool)
            layers = {}
            for name, lanes in (("HIGH_100", ("HIGH",)), ("LOW_100", LOW_LANES)):
                v = room_lane(e, rid, tag, lanes); g = np.full(m.shape, np.nan); g[m] = v
                layers[name] = [[None if np.isnan(c) else int(round(c)) for c in row] for row in g]
            hl = [[None if a is None else a + b for a, b in zip(r1, r2)] for r1, r2 in zip(layers["HIGH_100"], layers["LOW_100"])]
            layers["HIGH+LOW_100"] = hl
            out[rid] = dict(plane_m=e["meta"][tag]["plane_m"], step_ft=0.25, x_ft=e["meta"][tag]["x_ft"], z_ft=e["meta"][tag]["z_ft"], layers=layers,
                            label="SIMULATED (Radiance, generic provisional photometry, MF applied) - not product-specific, not measured")
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    if os.environ.get("CHECK_REUSE_BENCH") == "1":
        # no-Radiance mode: carry the A-benchmark results from the previous verified analysis, labelled as reused
        prev_s = json.load(open(os.path.join(OUT, "sim-summary.json"))); prev_c = json.load(open(os.path.join(OUT, "checks.json")))
        A = dict(prev_s["engine_benchmarks"], reused_from="analysis/sim-summary.json of the previous full check run (Radiance not re-run)")
        for c in prev_c["checks"]:
            if c["check"].startswith("A"):
                checks.append(dict(c, reused=True)); print(c["result"], c["check"], "(reused)")
    else:
        A = engine_benchmarks()
    res = load("base")
    if res is None: raise SystemExit("runs/base missing")
    ana = json.load(open(ANALYTIC))
    B = structural(res); conv = sampling_convergence()
    rooms, tasks = compare(res, ana); sens = sensitivity()
    mast = S.sha(S.MASTER); check("E1 master unchanged (b6f6bf1a)", mast == S.EXPECTED_MASTER, sha=mast[:8])
    man = os.path.join(SESSION, "lighting-current-review", "manifest.json")
    if os.path.exists(man):
        mh = S.sha(man); check("E2 delivered lighting-current-review manifest unchanged (a852f200)", mh.startswith("a852f200"), sha=mh[:8])
    summary = dict(schema="lighting.simulation.summary/1", status=res["status"], master_sha256=res["master_sha256"], params=res["params"], engine=res["engine"],
                   variant=res["variant"], V=res["V"], assumptions=res["assumptions"], engine_benchmarks=A, sampling_convergence=conv, structural=B,
                   rooms=rooms, tasks=tasks, sensitivity=sens, skipped={k: v for e in res["enclosures"].values() for k, v in e["skipped"].items()},
                   enclosure_info={k: dict(rooms=e["rooms"], **e["info"], seconds=e["seconds"]) for k, e in res["enclosures"].items()})
    json.dump(summary, open(os.path.join(OUT, "sim-summary.json"), "w"), indent=1)
    json.dump(heatmaps(res), open(os.path.join(OUT, "sim-heatmaps.json"), "w"), separators=(",", ":"))
    json.dump(dict(passed=sum(c["result"] == "PASS" for c in checks), total=len(checks), checks=checks), open(os.path.join(OUT, "checks.json"), "w"), indent=1)
    print(f"{sum(c['result'] == 'PASS' for c in checks)}/{len(checks)} checks passed")


if __name__ == "__main__":
    main()
