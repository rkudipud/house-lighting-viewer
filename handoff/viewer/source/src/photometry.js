// Pure photometric estimator (no three.js), compared with the canonical lighting calculations.
// Plan coordinates are feet (x right, z down the sheet),
// heights metres. This is a design estimate, not a photometric simulation.
export const FT = 0.3048;
export const CH = ['high', 'low', 'mood', 'perim', 'line', 'task', 'read', 'night', 'mirror', 'pooja', 'poojaSpot', 'art', 'study', 'uv'];
export const channelOf = f => f.channel ?? (f.type === 'VANITY' ? 'uv' : f.layer.toLowerCase());
const INDIRECT_ONLY = ['BACK', 'PLINTH', 'NICHE', 'VANITY'];
export const mFromBeam = beam => Math.max(0.6, Math.log(0.5) / Math.log(Math.cos(beam * Math.PI / 360)));

export function inPoly(x, z, p) {
  let hit = false;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
    const [x1, z1] = p[j], [x2, z2] = p[i];
    if ((z1 > z) !== (z2 > z) && x < x1 + (z - z1) * (x2 - x1) / (z2 - z1)) hit = !hit;
  }
  return hit;
}
export function areaPerimeter(poly) {
  let a = 0, p = 0;
  for (let i = 0; i < poly.length; i++) {
    const [x1, z1] = poly[i], [x2, z2] = poly[(i + 1) % poly.length];
    a += x1 * z2 - x2 * z1; p += Math.hypot(x2 - x1, z2 - z1);
  }
  return {A: Math.abs(a) / 2 * FT * FT, P: p * FT};
}
const unit = v => { const n = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / n, v[1] / n, v[2] / n]; };

// Unit aim vector (x right, y up, z down the sheet) from aim [x_ft,z_ft,y_m] | tilt | dir | straight down.
export function aimVector(f, hs) {
  if (f.aim) return unit([(f.aim[0] - f.x) * FT, f.aim[2] - hs, (f.aim[1] - f.z) * FT]);
  if (f.tilt) {
    const t = f.tilt * Math.PI / 180, [dx, dz] = f.toward || [1, 0];
    return unit([Math.sin(t) * dx, -Math.cos(t), Math.sin(t) * dz]);
  }
  if (f.dir) return unit(f.dir);
  return [0, -1, 0];
}

// Mount height of a source. Explicit heights are absolute unless they are ceiling-level, which follow the offset.
export function sourceHeight(f, zone, off = 0, night = 'ceiling') {
  const ceil = zone.ceil_m + off;
  if (f.h_m !== undefined) return f.h_m >= 2.3 && !f.hang_m ? f.h_m + off : f.h_m;
  if (f.hang_m) return f.hang_m;
  if (f.type === 'READ') return 1.3;
  if (f.layer === 'NIGHT' && night === 'low') return 0.30;
  return ceil;
}

// Point sources for a fixture, or null when the fixture only contributes indirect/uniform light.
export function pointSources(f, zone, ctx) {
  const {strips, off = 0, night} = ctx, plane = ctx.plane;
  if (f.pts) {
    const st = strips[f.type] || {};
    if (st.uf != null || INDIRECT_ONLY.includes(f.type)) return null;
    const segs = [];
    for (let i = 0; i < f.pts.length - 1; i++) {
      const a = f.pts[i], b = f.pts[i + 1], n = Math.max(1, Math.floor(Math.hypot(b[0] - a[0], b[1] - a[1]) * FT / 0.25));
      for (let k = 0; k < n; k++) { const t = (k + .5) / n; segs.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]); }
    }
    const h = f.type === 'LIN' || f.h_m !== undefined ? sourceHeight(f, zone, off) : plane + 0.55, lm = f.lm / segs.length;
    return segs.map(([x, z]) => ({x, z, h, m: 1, I: lm * 2 / (2 * Math.PI), a: [0, -1, 0]}));
  }
  const hs=sourceHeight(f,zone,off,night),updown=f.type==='UPDN'||f.type==='UPDNV',a=updown?[0,-1,0]:aimVector(f,hs);
  const lm=updown?f.lm/2:f.lm,m=mFromBeam(f.beam);
  return [{x: f.x, z: f.z, h: hs, m, I: lm * (m + 1) / (2 * Math.PI), a}];
}

export function illumAt(srcs, px, pz, py, n, k) {
  let E = 0;
  for (const s of srcs) {
    const vx = (px - s.x) * FT, vy = py - s.h, vz = (pz - s.z) * FT, d2 = vx * vx + vy * vy + vz * vz, d = Math.sqrt(d2);
    const cg = Math.max(0, (vx * s.a[0] + vy * s.a[1] + vz * s.a[2]) / d), ci = Math.max(0, -(vx * n[0] + vy * n[1] + vz * n[2]) / d);
    if (cg > 0 && ci > 0) E += s.I * Math.pow(cg, s.m) * ci / d2;
  }
  return E * k;
}

export function zoneSurface(zone, off = 0, assume) {
  const {A, P} = areaPerimeter(zone.poly), ceil = zone.ceil_m + off;
  return {A, P, S: 2 * A + P * ceil, rho: zone.rho ?? assume.RHO};
}
const indirectLx = (f, S, rho, assume) => f.lm * assume.MF * rho / (S * (1 - rho));

// Illuminance grid per channel on a horizontal plane (feet grid, 0.25 ft cells, same task mask as the solver).
export function buildGrid(zone, ctx) {
  const {assume, strips, plane, off = 0} = ctx, res = ctx.res || 0.25, K = assume.MF * assume.CAL;
  const xs = zone.poly.map(p => p[0]), zs = zone.poly.map(p => p[1]);
  const x0 = Math.min(...xs), z0 = Math.min(...zs), nx = Math.ceil((Math.max(...xs) - x0) / res - 1e-9), nz = Math.ceil((Math.max(...zs) - z0) / res - 1e-9);
  const mask = new Uint8Array(nx * nz), task = new Uint8Array(nx * nz), n = nx * nz;
  const arrays = {},groups={};
  for (const c of CH) arrays[c] = null;
  const sur = zoneSurface(zone, off, assume);
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const x = x0 + (i + .5) * res, z = z0 + (j + .5) * res;
    if (!inPoly(x, z, zone.poly)) continue;
    mask[j * nx + i] = 1;
    let ok = true;
    for (const dx of [-1.64, 1.64]) for (const dz of [-1.64, 1.64]) if (!inPoly(x + dx, z + dz, zone.poly)) ok = false;
    task[j * nx + i] = ok ? 1 : 0;
  }
  if (!task.some(Boolean)) task.set(mask);
  const bySrc = [];
  for (const f of zone.fixtures) {
    const ch = channelOf(f), arr = arrays[ch] || (arrays[ch] = new Float32Array(n));
    const group=f.circuit?(groups[f.circuit]||(groups[f.circuit]=new Float32Array(n))):null;
    const st = f.pts ? strips[f.type] : null;
    let uniform = 0;
    if (st && st.uf != null) uniform = f.lm * st.uf * assume.MF / sur.A;
    else uniform = indirectLx(f, sur.S, sur.rho, assume);
    const ps = (pointSources(f, zone, {...ctx, off}) || []).filter(s => s.h - plane > 0.05);
    for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
      const k = j * nx + i;
      if (!mask[k]) continue;
      let e = uniform;
      if (ps.length) e += illumAt(ps, x0 + (i + .5) * res, z0 + (j + .5) * res, plane, [0, 1, 0], K);
      arr[k] += e;
      if(group)group[k]+=e;
    }
    bySrc.push({f, ch});
  }
  return {zone, nx, nz, x0, z0, res, X: x0 + nx * res, Z: z0 + nz * res, mask, task, arrays,groups,plane, area: sur.A, S: sur.S, rho: sur.rho};
}

// avg / min / U0 over the task area and mean over the whole room, for per-channel weights.
export function gridStats(g, weights,byGroup=false) {
  const arrays=byGroup?g.groups:g.arrays,chans=Object.keys(arrays).filter(c=>arrays[c]&&weights[c]);
  let sum = 0, min = Infinity, max = 0, num = 0, roomSum = 0, roomNum = 0;
  for (let k = 0; k < g.mask.length; k++) {
    if (!g.mask[k]) continue;
    let e = 0;
    for (const c of chans) e += arrays[c][k] * weights[c];
    roomSum += e; roomNum++;
    if (g.task[k]) { sum += e; num++; if (e < min) min = e; if (e > max) max = e; }
  }
  const avg = num ? sum / num : 0;
  return {avg, min: num ? min : 0, max, U0: avg > 1e-9 ? min / avg : 0, avg_room: roomNum ? roomSum / roomNum : 0};
}

// Direct-only illuminance of a fixture subset at one point p = [x_ft, z_ft, y_m] (no inter-reflected term).
export function directAt(zone, fixtures, p, n, ctx) {
  const K = ctx.assume.MF * ctx.assume.CAL;
  let ps = [];
  for (const f of fixtures) { const s = pointSources(f, zone, {...ctx, plane: zone.plane_m}); if (s) ps = ps.concat(s); }
  return illumAt(ps, p[0], p[1], p[2], n, K);
}

// Direct E (lx) at p = [x_m, y_m, z_m], normal n, from the concealed pooja U-strip: the head faces down+back, each jamb faces inward+back.
export function nicheStripE(f, p, n, assume, eff = 0.85) {
  const x = f.pts[0][0] * FT, [za, zb] = [f.pts[0][1] * FT, f.pts[1][1] * FT].sort((a, b) => a - b), [hb, ht] = f.jamb_h;
  const lmpm = f.lm / f.length_m * assume.MF * eff, d = 0.01, nu = unit(n);
  let E = 0;
  const add = (qx, qy, qz, ne) => {
    const vx = p[0] - qx, vy = p[1] - qy, vz = p[2] - qz, r = Math.hypot(vx, vy, vz), ce = (vx * ne[0] + vy * ne[1] + vz * ne[2]) / r, cr = -(vx * nu[0] + vy * nu[1] + vz * nu[2]) / r;
    if (ce > 0 && cr > 0) E += lmpm * d / Math.PI * ce * cr / (r * r);
  };
  const head = unit([-1, -1, 0]);
  for (let z = za + d / 2; z < zb; z += d) add(x, ht, z, head);
  for (const [z, sg] of [[za, 1], [zb, -1]]) {
    const ne = unit([-1, 0, sg]);
    for (let y = hb + d / 2; y < ht; y += d) add(x, y, z, ne);
  }
  return E;
}

// Direct + indirect illuminance of a fixture subset on any surface patch (vertical readouts).
// pts: [[x_ft, z_ft, y_m], ...]; n: outward unit normal. Returns the mean and max over the patch.
export function patchStats(zone, fixtures, pts, n, ctx) {
  const {assume, strips} = ctx, sur = zoneSurface(zone, ctx.off || 0, assume), K = assume.MF * assume.CAL;
  let ps = [], ind = 0;
  for (const f of fixtures) { const p = pointSources(f, zone, {...ctx, plane: zone.plane_m}); if (p) ps = ps.concat(p); ind += indirectLx(f, sur.S, sur.rho, assume); }
  if(!pts.length)throw new Error('Empty photometry receiver patch');
  let sum=0,min=Infinity,max=0;
  for(const [x,z,y] of pts){const e=illumAt(ps,x,z,y,n,K)+ind;sum+=e;min=Math.min(min,e);max=Math.max(max,e);}
  const avg=sum/pts.length;
  return {avg,min,max,U0:avg>1e-9?min/avg:0};
}
