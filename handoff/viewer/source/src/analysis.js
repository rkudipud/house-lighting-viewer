import * as T from 'three';

// Frozen generic-optics lux grids (heatmaps.json) drawn as per-room working-plane overlays.
// The grids are not recomputed here; the brightness sliders only change the rendered light.
export const HEAT_STOPS = [[0, '#182864'], [50, '#2454bd'], [100, '#20aab2'], [200, '#5cc573'], [300, '#d6d95b'], [500, '#f5a23c'], [750, '#dc483a']];

const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const stops = HEAT_STOPS.map(([v, c]) => [v, hex(c)]);
// Canvas pixels are written directly in sRGB, so the ramp is interpolated in sRGB too.
const lut = lux => {
  if (lux >= stops.at(-1)[0]) return stops.at(-1)[1];
  for (let j = 1; j < stops.length; j++) if (lux < stops[j][0]) {
    const t = (lux - stops[j - 1][0]) / (stops[j][0] - stops[j - 1][0]);
    return stops[j - 1][1].map((a, k) => a + (stops[j][1][k] - a) * t);
  }
  return stops[0][1];
};

export function createAnalysis(heat, meta) {
  const group = new T.Group();group.name = 'analysis';group.visible = false;
  const rooms = {};
  let scene = 'HIGH+LOW_100';

  for (const [id, r] of Object.entries(heat.rooms)) {
    const nx = r.x_m.length, nz = r.z_m.length, s = r.step_m;
    const canvas = document.createElement('canvas');canvas.width = nx;canvas.height = nz;
    const ctx = canvas.getContext('2d'), tex = new T.CanvasTexture(canvas);
    tex.colorSpace = T.SRGBColorSpace;tex.magFilter = T.NearestFilter;tex.minFilter = T.LinearFilter;tex.generateMipmaps = false;
    const mat = new T.MeshBasicMaterial({map: tex, transparent: true, opacity: .8, depthWrite: false, toneMapped: false, side: T.DoubleSide});
    const w = nx * s, d = nz * s;
    const mesh = new T.Mesh(new T.PlaneGeometry(w, d), mat);
    // Canvas row 0 is the first (smallest) z sample: with the -90 degree X rotation, texture top maps to -z.
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.set(r.x_m[0] - s / 2 + w / 2, (r.plane_m || 0) + .014, r.z_m[0] - s / 2 + d / 2);
    mesh.renderOrder = 12;
    mesh.userData.analysisRoom = id;
    group.add(mesh);
    rooms[id] = {id, r, canvas, ctx, tex, mesh, nx, nz, step: s, active: id !== 'CBR'};
    mesh.visible = rooms[id].active;
  }

  function paint(id) {
    const R = rooms[id], E = R.r.E[scene];
    const img = R.ctx.createImageData(R.nx, R.nz), d = img.data;
    for (let z = 0; z < R.nz; z++) for (let x = 0; x < R.nx; x++) {
      const v = E[z][x], i = (z * R.nx + x) * 4;
      if (v == null) continue;
      const c = lut(v);
      d[i] = Math.round(c[0]);d[i + 1] = Math.round(c[1]);d[i + 2] = Math.round(c[2]);d[i + 3] = 255;
    }
    R.ctx.putImageData(img, 0, 0);R.tex.needsUpdate = true;
  }

  function setScene(id) {
    if (!meta.scenes.some(s => s.id === id)) throw new Error('Unknown frozen scene: ' + id);
    scene = id;
    for (const k of Object.keys(rooms)) if (rooms[k].active) paint(k);
  }
  const sample = (id, x, z) => {
    const R = rooms[id];if (!R) return null;
    const i = Math.round((x - R.r.x_m[0]) / R.step), j = Math.round((z - R.r.z_m[0]) / R.step);
    if (i < 0 || j < 0 || i >= R.nx || j >= R.nz) return null;
    return R.r.E[scene][j][i] ?? null;
  };
  const stats = id => meta.rooms.find(r => r.id === id)?.stats?.[scene] ?? null;
  setScene(scene);
  return {group, rooms, setScene, sample, stats, get scene() {return scene;}, show: v => {group.visible = v;}};
}
