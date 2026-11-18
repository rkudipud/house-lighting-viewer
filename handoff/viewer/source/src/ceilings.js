// Ceiling plan data and 2-D path helpers (no three.js). Plan coordinates are feet, heights metres.
import {FT} from './photometry.js';

export const signedArea = p => {
  let a = 0;
  for (let i = 0; i < p.length; i++) { const [x0, z0] = p[i], [x1, z1] = p[(i + 1) % p.length]; a += x0 * z1 - x1 * z0; }
  return a / 2;
};
export const dropClosing = path => {
  const p = path.map(q => q.slice()), a = p[0], b = p[p.length - 1];
  if (p.length > 2 && Math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-6) p.pop();
  return p;
};
export const pathLength = (p, closed) => {
  let L = 0;
  for (let i = 0; i < p.length - (closed ? 0 : 1); i++) { const a = p[i], b = p[(i + 1) % p.length]; L += Math.hypot(b[0] - a[0], b[1] - a[1]); }
  return L;
};
const unit = (x, z) => { const n = Math.hypot(x, z) || 1; return [x / n, z / n]; };

// Mitred offset of a closed polygon. d > 0 moves toward the interior, d < 0 outward.
export function offsetClosed(path, d) {
  const p = dropClosing(path), n = p.length, flip = signedArea(p) > 0 ? 1 : -1, out = [];
  for (let i = 0; i < n; i++) {
    const a = p[(i + n - 1) % n], b = p[i], c = p[(i + 1) % n];
    const e1 = unit(b[0] - a[0], b[1] - a[1]), e2 = unit(c[0] - b[0], c[1] - b[1]);
    const n1 = [-e1[1] * flip, e1[0] * flip], n2 = [-e2[1] * flip, e2[0] * flip];
    let m = unit(n1[0] + n2[0], n1[1] + n2[1]);
    const k = Math.min(2.2, 1 / Math.max(0.45, m[0] * n1[0] + m[1] * n1[1]));
    out.push([b[0] + m[0] * d * k, b[1] + m[1] * d * k]);
  }
  return out;
}

// Offset of an open polyline to both sides (half-width h), returned as left/right rails.
export function railsOpen(path, h) {
  const n = path.length, L = [], R = [];
  for (let i = 0; i < n; i++) {
    const a = path[Math.max(0, i - 1)], b = path[i], c = path[Math.min(n - 1, i + 1)];
    const e1 = i === 0 ? unit(c[0] - b[0], c[1] - b[1]) : unit(b[0] - a[0], b[1] - a[1]);
    const e2 = i === n - 1 ? e1 : unit(c[0] - b[0], c[1] - b[1]);
    const n1 = [-e1[1], e1[0]], n2 = [-e2[1], e2[0]];
    const m = unit(n1[0] + n2[0], n1[1] + n2[1]), k = Math.min(2.2, 1 / Math.max(0.45, m[0] * n1[0] + m[1] * n1[1]));
    L.push([b[0] + m[0] * h * k, b[1] + m[1] * h * k]); R.push([b[0] - m[0] * h * k, b[1] - m[1] * h * k]);
  }
  return {L, R};
}

const rectPoly = r => [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]];
export const insetRect = (r, d) => [r[0] + d, r[1] + d, r[2] - d, r[3] - d];
export function cornerPath(points, radii, steps=8){
  const out=[],n=points.length;
  for(let i=0;i<n;i++){
    const p=points[(i+n-1)%n],q=points[i],s=points[(i+1)%n];
    const r=Math.min(radii[i]||0,Math.hypot(p[0]-q[0],p[1]-q[1])*.4,Math.hypot(s[0]-q[0],s[1]-q[1])*.4);
    if(!r){out.push(q.slice());continue;}
    const a=unit(p[0]-q[0],p[1]-q[1]),b=unit(s[0]-q[0],s[1]-q[1]);
    for(let j=0;j<=steps;j++){
      const t=j/steps,u=1-t;
      out.push([q[0]+u*u*a[0]*r+t*t*b[0]*r,q[1]+u*u*a[1]*r+t*t*b[1]*r]);
    }
  }
  return out;
}
export const diagonalRadii=(n,r,style)=>Array.from({length:n},(_,i)=>style==='diagonal'&&i%2===0?r:0);

// Weather/ceiling closure follows the assembled envelope; nominal room extents are separate from unresolved interface bands.
export function ceilingPlan(PLAN,style=PLAN.design.cornerStyle) {
  const C = PLAN.fixtures.ceilings, A = PLAN.fixtures.assumptions, band = A.BAND_M, tray = A.TRAY_M;
  const R=Object.fromEntries(PLAN.rooms.map(r=>[r.id,{...r,rect:r.assemblyRect||r.rect,cutout:r.assemblyCutout||r.cutout}]));
  const kit = R.kitchen.rect, liv = R.living,kitchenH=PLAN.levels?.kitchenFlat??tray;
  const beamZ=15.7;
  const open = [[kit[0], beamZ], [kit[2], beamZ], [kit[2], liv.cutout[1]], [liv.cutout[0], liv.cutout[1]], [liv.cutout[0], liv.rect[3]], [kit[0], liv.rect[3]]];
  const ch = R.children;
  const childPoly = [[ch.rect[0], ch.rect[1]], [ch.rect[2], ch.rect[1]], [ch.rect[2], ch.rect[3]], [ch.cutout[2], ch.rect[3]], [ch.cutout[2], ch.cutout[1]], [ch.cutout[0], ch.cutout[1]]];
  const zones = [
    {key:'kitchen',rooms:['kitchen'],h:kitchenH,outline:rectPoly([kit[0],kit[1],kit[2],beamZ]),holes:[]},
    {key: 'open', rooms: ['dining', 'living'], h: band, outline: open, holes: ['HALL']},
    {key: 'utility', rooms: ['washing', 'utility'], h: PLAN.fixtures.zones.find(z => z.id === 'UTL')?.ceil_m ?? band, outline: rectPoly([R.washing.rect[0], R.utility.rect[1], R.utility.rect[2], R.utility.rect[3]]), holes: []},
    {key: 'master', rooms: ['master'], h: band, outline: rectPoly(R.master.rect), holes: ['MBR']},
    {key: 'dressing', rooms: ['dressing'], h: band, outline: rectPoly(R.dressing.rect), holes: []},
    {key: 'lobby', rooms: ['lobby'], h: PLAN.levels?.lobby??band, outline: rectPoly(R.lobby.rect), holes: []},
    {key: 'children', rooms: ['children'], h: band, outline: childPoly, holes: ['CBR']},
  ];
  const trays = [];
  const roomOfPath = {HALL: p => p[1] < 25.3 ? 'dining' : 'living', KIT: () => 'kitchen', MBR: () => 'master', CBR: () => 'children'};
  for (const [key, c] of Object.entries(C)) {
    if(key==='KIT')continue;
    const vertices=c.tray,cornerRadii=diagonalRadii(vertices.length,PLAN.design.radiusM/FT,style);
    const ring = cornerPath(vertices,cornerRadii);
    trays.push({key, ring, h: c.tray_h, band: c.band_h, width: .12/FT, roomOf: roomOfPath[key], rooms: c.rooms, source: c.source, cove: c.cove,
      frame: c.frame || null, linesLit: c.lines_lit || [], linesBlack: c.lines_black || [], beam: c.beam || null, sharp:style==='sharp',cornerRadii,vertices});
  }
  // Baths: panel at 2.40 m, 0.10 m inset on all walls, recess 0.12 m deeper with an IP65 strip in the gap.
  const baths = ['bath1', 'bath2'].map(id => {
    const rect = R[id].rect, ins = 0.10 / FT, zone = PLAN.fixtures.zones.find(z => z.room === id);
    return {id, rect, panelRect: insetRect(rect, ins), h: zone.ceil_m, recessH: zone.ceil_m + 0.12, gap: ins,style};
  });
  return {zones, trays, baths, band, tray,style,kitchen:{h:kitchenH,beam:beamZ,step:kitchenH-band,stepHeld:!!PLAN.levels,x:[kit[0],kit[2]]},fans: PLAN.fixtures.zones.filter(z => z.fan).map(z => ({room: z.room, at: z.fan}))};
}
