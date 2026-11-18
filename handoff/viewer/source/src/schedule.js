// Feature (showpiece) wall variants and fixture catalogue helpers. Pure data, shared by the bundle and the Node cross-check.
import {FT} from './photometry.js';

// Dining/passage face of the master-dressing wall, in the solver frame (feet): faces -x toward the dining passage.
export const FW = {x: 16.3, z0: 16.1, z1: 22.0, artZ: 19.1, artW: 1.0, artH: 0.75, artY: 1.55};
export const TRACK_X = Math.round((FW.x - 0.66 / FT) * 100) / 100;
export const CYL_X = Math.round((FW.x - 0.49 / FT) * 100) / 100;

export function featureFixtures(cat, mode, finish) {
  const art = finish === 'art', aimY = art ? 1.55 : 1.30;
  const spec = t => ({W: cat[t].W, lm: cat[t].lm, beam: cat[t].beam});
  if (mode === 'track') {
    const t = art ? 'TRK6' : 'TRK6W';
    const heads = [17.6, 19.1, 20.6].map((z, i) => ({id: `FW-T${i + 1}`, layer: 'ART', type: t, x: TRACK_X, z, cct: '3000K', note: 'magnetic-track head', aim: [FW.x, z, aimY], ...spec(t)}));
    heads.push({id: 'FW-T4', layer: 'ART', type: 'TRKLIN', x: TRACK_X, z: 21.0, cct: '3000K', note: 'track linear module, passage light', ...spec('TRKLIN')});
    return heads;
  }
  return [18.0, 20.2].map((z, i) => ({id: `FW-C${i + 1}`, layer: 'ART', type: 'CYL6', x: CYL_X, z, cct: '3000K', note: 'hanging cylinder, bottom 2.15 m, tilted to wall', h_m: 2.15, aim: [FW.x, z, aimY], ...spec('CYL6')}));
}

// numpy.arange semantics (exclusive end, no tolerance) so sampled patches match the solver point for point.
export const arange = (a, b, s) => { const out = [], n = Math.ceil((b - a) / s); for (let i = 0; i < n; i++) out.push(a + i * s); return out; };
export const FEATURE_WALL_PTS = () => {
  const pts = [];
  for (const y of arange(0.10, 2.65, 0.05)) for (const z of arange(FW.z0 + 0.05, FW.z1, 0.1)) pts.push({x: FW.x, z, y});
  return pts;
};
export const inArt = p => Math.abs(p.z - FW.artZ) <= FW.artW / 2 / FT && Math.abs(p.y - FW.artY) <= FW.artH / 2;
export const inWall = p => p.y >= 0.3 && p.y <= 2.4;
