"""Exploratory Radiance (rcontrib) room-light simulation on the canonical master b6f6bf1a.

READ-ONLY on the master and on every delivered package. Fixture positions/aims are taken unchanged from
lighting.design_inputs through the existing loader (final-lighting/src/fm_rooms.py). Photometry is GENERIC and
PROVISIONAL (cos^m intensity from the catalogue beam angle and lumens; Lambertian strips): no IES/LDT files
exist for any selected product. Surface reflectances, cove pocket shape and furniture are labelled assumptions.

Each fixture is one Radiance light modifier, so rcontrib returns every fixture's direct + inter-reflected
contribution (lx, maintained = MF applied) on: room working-plane grids (same 0.25 ft grid and masks as the
analytic heat maps), kitchen worktop grid, children's desk grid, pooja niche planes, lobby face points.
Usage: python sim_radiance.py --output <new dir inside this folder> [--variant base] [--ab 5 --ad 2048]
"""
import argparse, hashlib, json, math, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)
MASTER = r"handoff/source-basis/house-design.json"
EXPECTED_MASTER = "b6f6bf1a127c7e39086deb9fd1d2c0dff79a495381e1a4b9457f6a9a468f23ac"
RADBIN = os.path.join(os.environ["APPDATA"], r"Python\Python315\site-packages\pyradiance\bin")
RADLIB = os.path.join(os.environ["APPDATA"], r"Python\Python315\site-packages\pyradiance\lib")
FT = 0.3048


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


if sha(MASTER) != EXPECTED_MASTER:
    raise SystemExit("master hash guard failed - refusing to simulate a changed master")
os.environ["LIGHTING_SOURCE"] = MASTER
sys.path.insert(0, os.path.join(SESSION, "final-lighting", "src"))
import lc_engine as E                     # noqa: E402  geometry helpers, beam->m rule, path expansion
from fm_rooms import R                    # noqa: E402
from fm_calc_rooms import room_grids      # noqa: E402  identical grids/masks to the analytic heat maps
from fm_source import DI, CG, MODEL       # noqa: E402

# ---------------------------------------------------------------- provisional assumptions (all labelled)
VARIANTS = {
    "base": dict(rho=dict(ceiling=0.80, wall=0.55, floor=0.25, furniture=0.40, pocket=0.80), pocket_w=0.15, lip=0.05,
                 slot_w=0.10, slot_d=0.10, kit_slot="side", beam_delta=0.0, ceil_delta=0.0, kit_extend=False),
    "rho_low": dict(rho=dict(ceiling=0.70, wall=0.35, floor=0.15, furniture=0.25, pocket=0.70)),
    "rho_high": dict(rho=dict(ceiling=0.85, wall=0.70, floor=0.40, furniture=0.55, pocket=0.85)),
    "beam_minus10": dict(beam_delta=-10.0),
    "beam_plus10": dict(beam_delta=+10.0),
    "ceil_minus0.1": dict(ceil_delta=-0.1),
    "ceil_plus0.1": dict(ceil_delta=+0.1),
    "pocket_narrow": dict(pocket_w=0.08, lip=0.08),
    "pocket_wide": dict(pocket_w=0.25, lip=0.03),
    "kit_slot_down": dict(kit_slot="down"),
    "kit_extend": dict(kit_extend=True),
}
ASSUMPTIONS = {
    "photometry": "GENERIC: point fittings = cos^m intensity, m = ln0.5/ln(cos(beam/2)) (min 0.6), catalogue lumens taken as luminaire "
                  "output; strips = Lambertian 10 mm emitters at catalogue lm/m. No IES/LDT, no product LOR, no cut-off/baffle optics.",
    "maintenance_factor": MODEL["MF"],
    "analytic_CAL_0.85_not_applied": "the analytic model multiplies direct light by an empirical 0.85; the simulation does not",
    "surfaces": "diffuse (Radiance plastic, no specularity); reflectances per variant (paint/tile LRV unselected); floor gloss not modelled",
    "geometry": "lighting calculation polygons extruded (not surveyed masonry); LIV+DIN one open-plan enclosure; doors/windows/curtains "
                "not modelled (walls everywhere); unfurnished except kitchen counters/wall cabinets and the CBR desk shelf",
    "tray_cove": "tray recess at tray_h inside the tray path; cove pocket = band slab (12 mm) + lip + outer upstand; strip on the pocket "
                 "floor facing up at pocket_w/2 outside the tray edge (pocket width and lip unmeasured)",
    "kitchen_slot": "flat ceiling with a shadow slot slot_w x slot_d outside the cove path; strip on the slot inner face aimed outward "
                    "(variant: down-facing); slot size unmeasured",
    "wall_cabinets": "kitchen wall cabinets 1.45-2.20 m over cabinets_occlusion_ft boxes; base counters 0-0.90 m on the counter rule",
    "back_strips": "TV backlight (BACK without mount height) = 0.8 m tall Lambertian panel at 0.8-1.6 m facing the nearer wall",
    "pooja": "canonical niche (0.6096 x 1.7018 m, sill 0.4318 m, depth 0.381 m HOLD) cut into the LIV x = 2.25 ft wall; the inherited "
             "LIV-P1 strip record lies outside that cavity and is reported, not simulated",
    "curtain_strips": "excluded (no lux credit, unmeasured pockets)",
}


# ---------------------------------------------------------------- Radiance scene writer
class Scene:
    def __init__(self, rho):
        self.lines = []; self.n = 0; self.lightmat = {}
        for k, v in rho.items():
            self.lines.append(f"void plastic m_{k}\n0\n0\n5 {v} {v} {v} 0 0\n")

    def poly(self, mat, pts, normal, prefix="m_"):
        P = np.array(pts, float)
        nrm = sum(np.cross(P[i] - P[0], P[i + 1] - P[0]) for i in range(1, len(P) - 1))
        if np.dot(nrm, normal) < 0: P = P[::-1]
        self.n += 1
        self.lines.append(f"{prefix}{mat} polygon p{self.n}\n0\n0\n{3 * len(P)} " + " ".join(f"{v:.5f}" for v in P.ravel()) + "\n")

    def rect_h(self, mat, x0, x1, y0, y1, z, up):
        self.poly(mat, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], (0, 0, 1 if up else -1))

    def rect_v(self, mat, a, b, z0, z1, normal):
        self.poly(mat, [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], normal)

    def box(self, mat, x0, x1, y0, y1, z0, z1):
        self.rect_h(mat, x0, x1, y0, y1, z0, False); self.rect_h(mat, x0, x1, y0, y1, z1, True)
        self.rect_v(mat, (x0, y0), (x1, y0), z0, z1, (0, -1, 0)); self.rect_v(mat, (x0, y1), (x1, y1), z0, z1, (0, 1, 0))
        self.rect_v(mat, (x0, y0), (x0, y1), z0, z1, (-1, 0, 0)); self.rect_v(mat, (x1, y0), (x1, y1), z0, z1, (1, 0, 0))

    def disc(self, fid, pos, aim, lm, m, r=0.035):
        """cos^m source: Lambertian disc radiance modulated by cos^(m-1) -> I = I0 cos^m, flux = lm."""
        aim = np.array(aim, float); aim /= np.linalg.norm(aim)
        A = math.pi * r * r; L = lm * (m + 1) / (2 * math.pi * A)
        k = f"F_{fid}_{self.n}"; self.n += 1
        self.lines.append(f"void brightfunc b{k}\n2 cosm cosm.cal\n0\n4 {aim[0]:.6f} {aim[1]:.6f} {aim[2]:.6f} {m:.6f}\n")
        self.lines.append(f"b{k} light {k}\n0\n0\n3 {L:.6g} {L:.6g} {L:.6g}\n")
        self.lines.append(f"{k} ring r{k}\n0\n0\n8 {pos[0]:.5f} {pos[1]:.5f} {pos[2]:.5f} {aim[0]:.6f} {aim[1]:.6f} {aim[2]:.6f} 0 {r}\n")
        return k

    def lamb_rect(self, fid, corners, normal, lm):
        """Lambertian emitting rectangle carrying `lm` lumens; segments of one fixture with equal radiance share one modifier."""
        P = np.array(corners, float); A = np.linalg.norm(np.cross(P[1] - P[0], P[3] - P[0]))
        L = lm / (math.pi * A); key = (fid, f"{L:.5g}")
        if key not in self.lightmat:
            k = f"F_{fid}_{len(self.lightmat)}"; self.lightmat[key] = k
            self.lines.append(f"void light {k}\n0\n0\n3 {L:.6g} {L:.6g} {L:.6g}\n")
        k = self.lightmat[key]
        self.poly(k, corners, normal, prefix="")
        return k


def pip(poly, x, y):
    return E.point_in_poly(x, y, poly)


def seg_dist(P, poly):
    Q = np.array(poly, float); best = np.full(len(P), np.inf)
    for a, b in zip(Q, np.roll(Q, -1, axis=0)):
        ab = b - a; L2 = max(ab @ ab, 1e-12); t = np.clip(((P - a) @ ab) / L2, 0, 1)
        best = np.minimum(best, np.linalg.norm(P - (a + t[:, None] * ab), axis=1))
    return best


def walls(sc, poly_m, h, openings=()):
    """extrude the enclosure polygon (m) to height h, inward normals; openings: (edge, s0, s1, z0, z1, depth) recess boxes."""
    n = len(poly_m); area2 = sum(poly_m[i][0] * poly_m[(i + 1) % n][1] - poly_m[(i + 1) % n][0] * poly_m[i][1] for i in range(n))
    ccw = area2 > 0
    for i in range(n):
        a = np.array(poly_m[i]); b = np.array(poly_m[(i + 1) % n]); d = b - a; L = np.linalg.norm(d); u = d / L
        nin = np.array([-u[1], u[0]]) if ccw else np.array([u[1], -u[0]]); nrm = (nin[0], nin[1], 0)
        s = 0.0
        for (_, s0, s1, z0, z1, dep) in sorted([o for o in openings if o[0] == i], key=lambda o: o[1]):
            p0, p1 = a + u * s0, a + u * s1
            if s0 > s: sc.rect_v("wall", a + u * s, p0, 0, h, nrm)
            sc.rect_v("wall", p0, p1, 0, z0, nrm); sc.rect_v("wall", p0, p1, z1, h, nrm)
            q0, q1 = p0 - nin * dep, p1 - nin * dep
            sc.rect_v("wall", q0, q1, z0, z1, nrm)
            sc.rect_v("wall", p0, q0, z0, z1, (u[0], u[1], 0)); sc.rect_v("wall", p1, q1, z0, z1, (-u[0], -u[1], 0))
            sc.poly("wall", [(p0[0], p0[1], z0), (p1[0], p1[1], z0), (q1[0], q1[1], z0), (q0[0], q0[1], z0)], (0, 0, 1))
            sc.poly("wall", [(p0[0], p0[1], z1), (p1[0], p1[1], z1), (q1[0], q1[1], z1), (q0[0], q0[1], z1)], (0, 0, -1))
            s = s1
        if s < L: sc.rect_v("wall", a + u * s, b, 0, h, nrm)


def ceiling_raster(sc, poly_m, band, tray_poly_m, tray_h, V, cell=0.05, flat_slot=False):
    """Tray + cove pocket (or flat ceiling + shadow slot) as a run-length raster. Cell types: 1 band/flat, 2 pocket/slot, 3 tray."""
    xs = [p[0] for p in poly_m]; ys = [p[1] for p in poly_m]
    gx = np.arange(min(xs), max(xs) - 1e-9, cell); gy = np.arange(min(ys), max(ys) - 1e-9, cell); nx, ny = len(gx), len(gy)
    C = np.array([(x + cell / 2, y + cell / 2) for y in gy for x in gx])
    inside = np.array([pip(poly_m, *c) for c in C]); intray = np.array([pip(tray_poly_m, *c) for c in C]); dist = seg_dist(C, tray_poly_m)
    w = V["slot_w"] if flat_slot else V["pocket_w"]
    t = np.where(intray, 1 if flat_slot else 3, np.where(dist <= w, 2, 1))
    T = np.where(inside, t, 0).reshape(ny, nx)
    th = 0.012; hi = band + V["slot_d"] if flat_slot else tray_h
    lvl = {1: [("ceiling", band, False)], 3: [("ceiling", tray_h, False)],
           2: [("ceiling", hi, False)] if flat_slot else [("ceiling", band, False), ("pocket", band + th, True), ("pocket", tray_h, False)]}
    for j in range(ny):
        i = 0
        while i < nx:
            k = T[j, i]
            if k == 0: i += 1; continue
            e = i
            while e + 1 < nx and T[j, e + 1] == k: e += 1
            for mat, z, up in lvl[k]: sc.rect_h(mat, gx[i], gx[e] + cell, gy[j], gy[j] + cell, z, up)
            i = e + 1

    def vface(k1, k2, a, b, nrm):       # nrm points from cell k2 toward cell k1
        pair = {k1, k2}; flip = tuple(-v for v in nrm)
        if flat_slot:
            if pair == {1, 2}: sc.rect_v("ceiling", a, b, band, hi, nrm if k1 == 2 else flip)
        elif pair == {1, 2}: sc.rect_v("pocket", a, b, band + th, tray_h, nrm if k1 == 2 else flip)   # outer upstand
        elif pair == {2, 3}: sc.rect_v("pocket", a, b, band, band + th + V["lip"], nrm)               # lip (two-sided)
        elif pair == {1, 3}: sc.rect_v("ceiling", a, b, band, tray_h, nrm if k1 == 3 else flip)        # fascia
    for j in range(ny):
        for i in range(nx):
            k = T[j, i]
            if k == 0: continue
            if i + 1 < nx and T[j, i + 1] not in (0, k):
                x = gx[i] + cell; vface(k, T[j, i + 1], (x, gy[j]), (x, gy[j] + cell), (-1, 0, 0))
            if j + 1 < ny and T[j + 1, i] not in (0, k):
                y = gy[j] + cell; vface(k, T[j + 1, i], (gx[i], y), (gx[i] + cell, y), (0, -1, 0))
    return T


def tray_poly(key):
    return [(x * FT, z * FT) for x, z in E.tray_path(key)[:-1]]


def strip_segments(pts, step=1e9):
    """one emitter per straight path segment (Radiance subdivides large sources itself, -ds)."""
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        a = np.array(a); b = np.array(b); L = np.linalg.norm(b - a)
        if L < 1e-6: continue
        n = max(1, int(math.ceil(L / step)))
        out += [(a + (b - a) * k / n, a + (b - a) * (k + 1) / n) for k in range(n)]
    return out


def outward(p, d, tray_m):
    nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
    return nrm if not pip(tray_m, *(p + nrm * 0.01)) else -nrm


def hrect(c, u, L, o, w, z):
    ow = o * w / 2
    return [(c[0] - u[0] * L / 2 - ow[0], c[1] - u[1] * L / 2 - ow[1], z), (c[0] + u[0] * L / 2 - ow[0], c[1] + u[1] * L / 2 - ow[1], z),
            (c[0] + u[0] * L / 2 + ow[0], c[1] + u[1] * L / 2 + ow[1], z), (c[0] - u[0] * L / 2 + ow[0], c[1] - u[1] * L / 2 + ow[1], z)]


def add_fixture(sc, f, room, V, ceil, tray_m=None, flat=False):
    """returns the list of modifier names, or a reason string when not simulated."""
    t = f["type"]; lane = f["layer"]; mods = []; w = 0.01
    if "pts" in f:
        lmpm = E.STRIP[t]["lmpm"]; P = [(x * FT, z * FT) for x, z in f["pts"]]
        if f["id"] == "LIV-P1":
            return ("inherited pooja U-strip record (x 2.15 ft, z 37.45-40.15 ft, behind the x 2.25 ft wall face) lies outside the "
                    "canonical niche cavity (z 39.93-41.93 ft); not physically placeable in this geometry - pooja lighting HELD")
        if lane == "COVE":
            for a, b in strip_segments(P):
                d = b - a; L = np.linalg.norm(d); mid = (a + b) / 2; u = d / L; o = outward(mid, d, tray_m)
                if flat and V["kit_slot"] == "side":
                    c = mid + o * 0.03; zc = ceil + V["slot_d"] / 2
                    corners = [(c[0] - u[0] * L / 2, c[1] - u[1] * L / 2, zc - w / 2), (c[0] + u[0] * L / 2, c[1] + u[1] * L / 2, zc - w / 2),
                               (c[0] + u[0] * L / 2, c[1] + u[1] * L / 2, zc + w / 2), (c[0] - u[0] * L / 2, c[1] - u[1] * L / 2, zc + w / 2)]
                    mods.append(sc.lamb_rect(f["id"], corners, (o[0], o[1], 0), lmpm * L))
                elif flat:
                    mods.append(sc.lamb_rect(f["id"], hrect(mid + o * V["slot_w"] / 2, u, L, o, w, ceil + V["slot_d"] - 0.003), (0, 0, -1), lmpm * L))
                else:
                    mods.append(sc.lamb_rect(f["id"], hrect(mid + o * V["pocket_w"] / 2, u, L, o, w, ceil + 0.015), (0, 0, 1), lmpm * L))
            return sorted(set(mods))
        normal = (0, 0, -1)
        if t == "LIN": h = (f.get("h_m") or ceil) + (V["ceil_delta"] if f.get("h_m") else 0) - 0.003
        elif t in ("TASK", "TASK_LO", "TASK_HO", "TASKW"): h = f.get("h_m", room["plane_m"] + MODEL["engine_defaults"]["task_strip_above_plane_m"]) - 0.006
        elif t == "BCOVE": h = ceil - 0.003
        elif t in ("NICHE", "VANITY"): h = f.get("h_m", 0.2) - 0.003
        elif t == "PLINTH": h = 0.05; normal = (0, 0, 1)
        elif t == "BACK":
            if "ceiling slot" in f.get("mount", ""): h = ceil - 0.003
            else: h = 1.2; normal = None
        else: return f"strip type {t} not mapped"
        for a, b in strip_segments(P):
            d = b - a; L = np.linalg.norm(d); u = d / L; mid = (a + b) / 2
            if normal is None:
                nh = np.array([-u[1], u[0]]); nh = nh if not pip(room["poly_m"], *(mid + nh * 0.2)) else -nh
                c = mid - nh * 0.0
                corners = [(a[0], a[1], h - 0.4), (b[0], b[1], h - 0.4), (b[0], b[1], h + 0.4), (a[0], a[1], h + 0.4)]
                mods.append(sc.lamb_rect(f["id"], corners, (nh[0], nh[1], 0), lmpm * L))
            else:
                mods.append(sc.lamb_rect(f["id"], hrect(mid, u, L, np.array([-u[1], u[0]]), w, h), normal, lmpm * L))
        return sorted(set(mods))
    for (x, z, hs, lm, m, a) in E.point_sources(f, room["plane_m"], ceil - V["ceil_delta"]):
        if t in ("FACEV", "FACE10V"):
            dv = np.array(f.get("dir", (0, 0, 1)), float); dx, dz = dv[0], dv[2]; side = np.array([-dz, dx])
            c = np.array([x * FT, z * FT]) + np.array([dx, dz]) * 0.01
            hh, ww = (0.3, 0.025) if t == "FACEV" else (0.025, 0.3)
            corners = [(c[0] - side[0] * ww, c[1] - side[1] * ww, hs - hh), (c[0] + side[0] * ww, c[1] + side[1] * ww, hs - hh),
                       (c[0] + side[0] * ww, c[1] + side[1] * ww, hs + hh), (c[0] - side[0] * ww, c[1] - side[1] * ww, hs + hh)]
            mods.append(sc.lamb_rect(f["id"], corners, (dx, dz, 0), lm)); continue
        mm = E.m_from_beam(E.CAT[t]["beam"] + V["beam_delta"])
        aim = np.array((a[0], a[2], a[1]))                      # engine (x, y_up, z_plan) -> radiance (x, y_plan, z_up)
        top = abs(hs - (ceil - V["ceil_delta"])) < 0.03
        p = np.array([x * FT, z * FT, hs + (V["ceil_delta"] - 0.004 if top else 0)]) + (0 if top else aim * 0.005)
        mods.append(sc.disc(f["id"], p, aim, lm, mm))
        if t.startswith("UPDN"):                               # up part (engine: indirect only) = lm * (1 - down fraction)
            mods.append(sc.disc(f["id"], p + np.array([0, 0, 0.01]), (0, 0, 1), f["lm"] - lm, mm))
    return mods


def enclosures(V):
    out = [dict(id="HALL", rooms=["LIV", "DIN"], poly=[(2.25, 15.3), (16.3, 15.3), (16.3, 37.6), (13.1, 37.6), (13.1, 43.25), (2.25, 43.25)], tray="HALL")]
    for rid, tr in (("KIT", "KIT"), ("MBR", "MBR"), ("CBR", "CBR"), ("UTL", None), ("DRS", None), ("LOB", None), ("TL1", None), ("TL2", None), ("BAL", None)):
        poly = list(R[rid]["poly"])
        if rid == "KIT" and V["kit_extend"]: poly = [(2.25, 5.2), (16.3, 5.2), (16.3, 15.9), (2.25, 15.9)]
        out.append(dict(id=rid, rooms=[rid], poly=poly, tray=tr))
    return out


def canonical_niche():
    rec = CG["pooja"]["canonical_geometry"]["record"]
    return dict(x_m=2.25 * FT, z_m=tuple(rec["z"]), sill=rec["sillM"], top=rec["sillM"] + rec["heightMm"] / 1000, depth=rec["depthMm"] / 1000)


def build_enclosure(enc, V, workdir):
    sc = Scene(V["rho"]); poly_m = [(x * FT, z * FT) for x, z in enc["poly"]]
    ceil = R[enc["rooms"][0]]["ceil_m"] + V["ceil_delta"]; tray_m = tray_h = None; flat = False
    if enc["tray"]:
        c = DI["ceilings"][enc["tray"]]; tray_m = tray_poly(enc["tray"]); flat = bool(c.get("flat")); tray_h = c["tray_h_m"] + V["ceil_delta"]
    top = (ceil + V["slot_d"]) if flat else (tray_h or ceil)
    openings = []
    if enc["id"] == "HALL":
        nc = canonical_niche(); n = len(poly_m)
        for i in range(n):
            a, b = poly_m[i], poly_m[(i + 1) % n]
            if abs(a[0] - nc["x_m"]) < 1e-6 and abs(b[0] - nc["x_m"]) < 1e-6:
                s0 = abs(a[1] - (nc["z_m"][1] if a[1] > b[1] else nc["z_m"][0])); openings.append((i, s0, s0 + abs(nc["z_m"][1] - nc["z_m"][0]), nc["sill"], nc["top"], nc["depth"]))
    sc.poly("floor", [(x, y, 0) for x, y in poly_m], (0, 0, 1))
    walls(sc, poly_m, top + 0.001, openings)
    if tray_m is not None: ceiling_raster(sc, poly_m, ceil, tray_m, tray_h, V, flat_slot=flat)
    else: sc.poly("ceiling", [(x, y, ceil) for x, y in poly_m], (0, 0, -1))
    if enc["id"] == "KIT":
        kw = CG["kitchen_worktop"]
        for (x0, x1, z0, z1) in kw["cabinets_occlusion_ft"]: sc.box("furniture", x0 * FT, x1 * FT, z0 * FT, z1 * FT, kw["cabinet_bottom_m"], 2.20)
        x0, x1 = kw["grid_x_ft"]; z0, z1 = kw["grid_z_ft"]; zt = kw["plane_m"] - 0.002
        sc.box("furniture", x0 * FT, kw["left_run_x_max_ft"] * FT, z0 * FT, z1 * FT, 0.0, zt)
        sc.box("furniture", kw["left_run_x_max_ft"] * FT, x1 * FT, z0 * FT, kw["top_run_z_max_ft"] * FT, 0.0, zt)
    if enc["id"] == "CBR":
        ox, oz = next(r for r in DI["rooms"] if r["id"] == "CBR")["frame"]["origin_xz_m"]
        for o in CG["children"]["occluders"]: sc.box("furniture", ox + o["v_m"][0], ox + o["v_m"][1], oz + o["u_m"][0], oz + o["u_m"][1], o["y_m"][0], o["y_m"][1])
    mods = {}; skipped = {}
    for rid in enc["rooms"]:
        room = dict(R[rid]); room["poly_m"] = [(x * FT, z * FT) for x, z in R[rid]["poly"]]
        for f in R[rid]["fixtures"]:
            res = add_fixture(sc, f, room, V, ceil, tray_m, flat)
            if isinstance(res, str): skipped[f["id"]] = res
            else: mods[f["id"]] = dict(room=rid, lane=f["layer"], mods=res, lm=f["lm"], type=f["type"])
    rad = os.path.join(workdir, f"{enc['id']}.rad")
    with open(rad, "w", encoding="ascii") as fh: fh.write("\n".join(sc.lines))
    return rad, mods, skipped, dict(ceil_m=round(ceil, 4), tray_h_m=tray_h, flat_slot=flat, primitives=sc.n)


def points_for(enc):
    pts = {}; meta = {}
    for rid in enc["rooms"]:
        rr = R[rid]; G = room_grids(rr); m = G["mask"]; X, Z = G["X"][m], G["Z"][m]
        pts[f"grid:{rid}"] = np.column_stack([X * FT, Z * FT, np.full(X.shape, rr["plane_m"] + 0.0005), np.zeros_like(X), np.zeros_like(X), np.ones_like(X)])
        meta[f"grid:{rid}"] = dict(grid_shape=list(G["X"].shape), mask=m.astype(int).tolist(), task=G["task"].astype(int).tolist(),
                                   x_ft=[round(float(v), 4) for v in G["X"][0]], z_ft=[round(float(v), 4) for v in G["Z"][:, 0]], plane_m=rr["plane_m"])
    if enc["id"] == "KIT":
        kw = CG["kitchen_worktop"]; s = kw["fine_step_m"] / FT
        X, Z = np.meshgrid(np.arange(kw["grid_x_ft"][0] + s / 2, kw["grid_x_ft"][1], s), np.arange(kw["grid_z_ft"][0] + s / 2, kw["grid_z_ft"][1], s))
        m = (X <= kw["left_run_x_max_ft"]) | (Z <= kw["top_run_z_max_ft"]); n = int(m.sum())
        pts["kit_worktop"] = np.column_stack([X[m] * FT, Z[m] * FT, np.full(n, kw["plane_m"] + 0.0005), np.zeros(n), np.zeros(n), np.ones(n)])
        meta["kit_worktop"] = dict(shape=list(X.shape), n=n, step_m=kw["fine_step_m"], plane_m=kw["plane_m"], rule=kw["counter_rule"])
    if enc["id"] == "CBR":
        d = CG["children"]["desk"]; ox, oz = next(r for r in DI["rooms"] if r["id"] == "CBR")["frame"]["origin_xz_m"]; s = 0.05
        U, Vv = np.meshgrid(np.arange(d["u_m"][0] + s / 2, d["u_m"][1], s), np.arange(d["v_m"][0] + s / 2, d["v_m"][1], s))
        pts["cbr_desk"] = np.column_stack([ox + Vv.ravel(), oz + U.ravel(), np.full(U.size, d["h_m"] + 0.0005), np.zeros(U.size), np.zeros(U.size), np.ones(U.size)])
        meta["cbr_desk"] = dict(shape=list(U.shape), step_m=s, plane_m=d["h_m"], basis="u,v on the planned R05 frame (unsurveyed); shelf ST-R05-OH01 modelled as occluder")
    if enc["id"] == "HALL":
        nc = canonical_niche(); s = 0.05
        Zg, Yg = np.meshgrid(np.arange(nc["z_m"][0] + s / 2, nc["z_m"][1], s), np.arange(nc["sill"] + s / 2, nc["top"], s))
        for tag, x in (("pooja:canonical_back", nc["x_m"] - nc["depth"] + 0.002), ("pooja:canonical_opening", nc["x_m"] + 0.002)):
            pts[tag] = np.column_stack([np.full(Zg.size, x), Zg.ravel(), Yg.ravel(), np.ones(Zg.size), np.zeros(Zg.size), np.zeros(Zg.size)])
            meta[tag] = dict(shape=list(Zg.shape), step_m=s, x_m=round(x, 4), normal="+x (facing the room)")
        ip = CG["pooja"]["idol_point"]; zc = sum(nc["z_m"]) / 2; xw = nc["x_m"] + 0.002
        pts["pooja:points"] = np.array([[nc["x_m"] - nc["depth"] + 0.10, zc, 1.1, 1, 0, 0], [ip["x_ft"] * FT, ip["z_ft"] * FT, ip["h_m"], 1, 0, 0],
                                        [xw, ip["z_ft"] * FT, ip["h_m"], 1, 0, 0], [xw, nc["z_m"][0] - 0.30, 1.1, 1, 0, 0], [xw, nc["z_m"][1] + 0.30, 1.1, 1, 0, 0]])
        meta["pooja:points"] = dict(labels=["canonical idol test point (0.10 m in front of niche back, h 1.1 m, centre)",
                                            "inherited idol point x 2.05 ft z 38.8 ft h 1.1 m (behind the wall face in canonical geometry)",
                                            "wall face at the inherited aim (z 38.8 ft, h 1.1 m)",
                                            "wall surround 0.30 m south of the canonical niche (h 1.1 m)", "wall surround 0.30 m north of the canonical niche (h 1.1 m)"])
    if enc["id"] == "LOB":
        lf = CG["lobby_face"]; n = lf["normal"]
        pts["lobby_face"] = np.array([[x * FT, lf["z_ft"] * FT, lf["h_m"], n[0], n[2], n[1]] for x in lf["x_ft"]]); meta["lobby_face"] = dict(x_ft=lf["x_ft"], h_m=lf["h_m"])
    return pts, meta


REMOTE_ENGINE = {}


def run_rcontrib_remote(rad_path, mods, P, args, tag):
    raise RuntimeError('Remote execution is omitted from this public source snapshot.')


def run_rcontrib(oct_path, mods, P, args, workdir, tag):
    """(N, n_mods) lux (photopic channel G; all channels equal), MF not applied."""
    if args.remote: return run_rcontrib_remote(os.path.join(workdir, tag + ".rad"), mods, P, args, tag)
    modfile = os.path.join(workdir, f"{tag}.mods")
    with open(modfile, "w", encoding="ascii") as fh: fh.write("\n".join(mods) + "\n")
    chunks = np.array_split(np.arange(len(P)), max(1, min(args.procs * 3, max(1, len(P) // 40))))
    env = dict(os.environ, RAYPATH=RADLIB + os.pathsep + HERE)

    def job(ix):
        idx = chunks[ix]; inp = "".join(" ".join(f"{v:.6f}" for v in P[i]) + "\n" for i in idx)
        cmd = [os.path.join(RADBIN, "rcontrib.exe"), "-h", "-V+", "-I+", "-fa", "-ab", str(args.ab), "-ad", str(args.ad), "-lw", str(args.lw),
               "-dj", "0.7", "-ds", "0.02", "-dt", "0", "-dc", "1", "-st", "0", "-ss", "0", "-M", modfile, oct_path]
        r = subprocess.run(cmd, input=inp.encode(), capture_output=True, env=env, cwd=HERE)
        if r.returncode: raise RuntimeError(r.stderr.decode()[:2000])
        return idx, np.array(r.stdout.split(), float).reshape(len(idx), len(mods), 3)[:, :, 1]
    out = np.zeros((len(P), len(mods)))
    with ThreadPoolExecutor(args.procs) as ex:
        for idx, v in ex.map(job, range(len(chunks))): out[idx] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True); ap.add_argument("--variant", default="base", choices=list(VARIANTS))
    ap.add_argument("--rooms", default=""); ap.add_argument("--ab", type=int, default=5); ap.add_argument("--ad", type=int, default=2048)
    ap.add_argument("--lw", type=float, default=2e-4); ap.add_argument("--procs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--remote", default="", help="Remote execution is unavailable in this public source snapshot")
    ap.add_argument("--remote-procs", type=int, default=16)
    args = ap.parse_args()
    out = os.path.abspath(args.output)
    if os.path.commonpath([out, HERE]) != HERE or out == HERE: raise SystemExit("--output must be a new directory inside " + HERE)
    if os.path.exists(out) and os.listdir(out): raise SystemExit("refusing to write into a non-empty output directory")
    os.makedirs(out, exist_ok=True); work = os.path.join(out, "radiance"); os.makedirs(work)
    V = dict(VARIANTS["base"]); V.update(VARIANTS[args.variant]); V["rho"] = dict(VARIANTS["base"]["rho"], **VARIANTS[args.variant].get("rho", {}))
    MF = MODEL["MF"]
    result = dict(schema="lighting.simulation.radiance/1", status="EXPLORATORY - generic provisional photometry; not product-specific, not measured, not a release",
                  master_sha256=EXPECTED_MASTER, variant=args.variant, V=V, MF=MF, assumptions=ASSUMPTIONS,
                  params=dict(ab=args.ab, ad=args.ad, lw=args.lw, other="-dj 0.7 -ds 0.02 -dt 0 -dc 1 -st 0 -ss 0 -I+ -V+"),
                  engine=dict(name="Radiance rcontrib 6.0a (pyradiance wheel bundle)", rcontrib_sha256=sha(os.path.join(RADBIN, "rcontrib.exe")),
                              oconv_sha256=sha(os.path.join(RADBIN, "oconv.exe")), cosm_cal_sha256=sha(os.path.join(HERE, "cosm.cal"))),
                  units=dict(xyz="metres; x = plan x_ft*0.3048, y = plan z_ft*0.3048 (sheet-down), z = height above local floor",
                             E="lux, maintained (MF applied), per fixture at 100 % output"),
                  enclosures={})
    want = set(args.rooms.split(",")) - {""}; t0 = time.time()
    for enc in enclosures(V):
        if want and enc["id"] not in want: continue
        t1 = time.time(); rad, mods, skipped, info = build_enclosure(enc, V, work); octp = os.path.join(work, enc["id"] + ".oct")
        with open(octp, "wb") as fh:
            r = subprocess.run([os.path.join(RADBIN, "oconv.exe"), "-f", os.path.basename(rad)], cwd=work, stdout=fh, stderr=subprocess.PIPE)
        if r.returncode or r.stderr.strip(): raise RuntimeError(r.stderr.decode())
        allmods = sorted({m for v in mods.values() for m in v["mods"]}); col = {m: i for i, m in enumerate(allmods)}
        pts, meta = points_for(enc); tags = list(pts); P = np.vstack([pts[t] for t in tags])
        C = run_rcontrib(octp, allmods, P, args, work, enc["id"]) * MF
        span = {}; s0 = 0
        for t in tags: span[t] = (s0, s0 + len(pts[t])); s0 += len(pts[t])
        fixtures = {}
        for fid, v in mods.items():
            s = C[:, [col[m] for m in sorted(set(v["mods"]))]].sum(axis=1)
            fixtures[fid] = dict(room=v["room"], lane=v["lane"], lm=v["lm"], type=v["type"], modifiers=len(set(v["mods"])),
                                 E={t: np.round(s[a:b], 3).tolist() for t, (a, b) in span.items()})
        result["enclosures"][enc["id"]] = dict(rooms=enc["rooms"], poly_ft=enc["poly"], info=info, skipped=skipped, fixtures=fixtures,
                                               points={t: np.round(pts[t], 5).tolist() for t in tags}, meta=meta, seconds=round(time.time() - t1, 1))
        print(f"{enc['id']}: {len(allmods)} modifiers, {len(P)} points, {info['primitives']} primitives, {time.time() - t1:.1f}s", flush=True)
    result["seconds"] = round(time.time() - t0, 1)
    if args.remote:
        result["engine"] = dict(name="Radiance rcontrib 6.0a (pyradiance 1.1.5 Linux wheel bundle), remote", remote=dict(REMOTE_ENGINE, procs=args.remote_procs),
                                cosm_cal_sha256=result["engine"]["cosm_cal_sha256"], local_oconv_sha256_for_scene_check=result["engine"]["oconv_sha256"])
    with open(os.path.join(out, "sim-results.json"), "w", encoding="utf-8") as fh: json.dump(result, fh, separators=(",", ":"))
    print("wrote", os.path.join(out, "sim-results.json"))


if __name__ == "__main__":
    main()
