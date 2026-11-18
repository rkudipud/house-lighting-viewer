import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

export const SCENES = [
  {id: 'HIGH_100', label: 'HIGH 100 %', group: 'lane', from: 'combinations'},
  {id: 'LOW_100', label: 'LOW / cove 100 %', group: 'lane', from: 'combinations'},
  {id: 'HIGH+LOW_100', label: 'HIGH + LOW 100 %', group: 'lane', from: 'combinations'},
  {id: 'Mood', label: 'Mood scene', group: 'scene', from: 'scenes'},
  {id: 'Relax', label: 'Relax scene', group: 'scene', from: 'scenes'},
  {id: 'Work', label: 'Work scene', group: 'scene', from: 'scenes'},
  {id: 'Full', label: 'Full scene', group: 'scene', from: 'scenes'},
];
const FRAME = 'canonical sheet metres: +x sheet-right = west, +z sheet-down = north';

export function gridStats(room) {
  const out = {};
  for (const {id} of SCENES) {
    const E = room.E[id];
    let sum = 0, n = 0, min = Infinity, sumAll = 0, nAll = 0;
    for (let z = 0; z < E.length; z++) for (let x = 0; x < E[z].length; x++) {
      const v = E[z][x];
      if (v == null) continue;
      sumAll += v; nAll++;
      if (room.stats_mask[z][x]) {sum += v; n++; if (v < min) min = v;}
    }
    const avg = n ? sum / n : 0, lo = n ? min : 0;
    out[id] = {avg, min: lo, U0: avg > 0 ? lo / avg : 0, avg_room: nAll ? sumAll / nAll : 0, cells: nAll, statCells: n};
  }
  return out;
}

export async function prepareAnalysis(house, heatPath, expectedSha) {
  const L = house.lighting, C = L.calculations, V = L.calculation_validity;
  const bytes = await readFile(heatPath);
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  assert.equal(sha256, expectedSha, 'Heat-map pack hash differs from the authorized --heatmaps-sha');
  const listed = L.supporting_outputs?.files?.['heatmaps.json'];
  assert(listed, 'Master does not list heatmaps.json among its supporting outputs');
  assert.equal(listed.sha256, sha256, 'Heat-map pack hash differs from the hash recorded in the master');
  assert.equal(listed.bytes, bytes.length, 'Heat-map pack size differs from the size recorded in the master');
  const pack = JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/, ''));
  assert.equal(pack.frame, FRAME, 'Heat-map frame is not the expected canonical sheet frame');
  assert.deepEqual(Object.keys(pack.rooms).sort(), Object.keys(C.rooms).sort(), 'Heat-map rooms differ from the master calculation rooms');

  const tol = {avg: .51, min: .51, U0: .0101, avg_room: .51};
  let compared = 0, cells = 0, worst = {avg: 0, min: 0, U0: 0, avg_room: 0}, overshoot = 0;
  const rooms = [];
  for (const [id, room] of Object.entries(pack.rooms)) {
    const cr = C.rooms[id], nx = room.x_m.length, nz = room.z_m.length;
    assert.equal(room.plane_m, cr.plane_m, `${id}: heat-map plane differs from the master calculation plane`);
    assert.equal(room.stats_mask.length, nz);
    assert(room.stats_mask.every(r => r.length === nx));
    const computed = gridStats(room), stats = {};
    for (const s of SCENES) {
      const E = room.E[s.id];
      assert.equal(E.length, nz, `${id}/${s.id}: row count`);
      assert(E.every(r => r.length === nx), `${id}/${s.id}: column count`);
      assert(E.every(r => r.every(v => v === null || Number.isInteger(v))), `${id}/${s.id}: non-integer lux`);
      let ref = cr[s.from][s.id];
      if (!ref) {
        // Rooms with no LOW lane: the pack carries a zero LOW grid and HIGH+LOW equals HIGH.
        assert(s.from === 'combinations' && cr.combinations.HIGH_100 && !cr.lanes_at_100pct.COVE, `${id}/${s.id}: no master value`);
        if (s.id === 'LOW_100') {
          assert(E.every(r => r.every(v => v === null || v === 0)), `${id}/LOW_100: expected an all-zero grid for a room without a LOW lane`);
          stats[s.id] = null;
          continue;
        }
        ref = cr.combinations.HIGH_100;
      }
      for (const k of Object.keys(tol)) {
        const d = Math.abs(computed[s.id][k] - ref[k]);
        // Integer-lux grids: U0 = min/avg is limited by rounding when the average is small (balcony).
        const allow = k === 'U0' && ref.avg > 0 ? tol.U0 + (0.5 + 0.5 * ref.U0) / ref.avg : tol[k];
        worst[k] = Math.max(worst[k], d);
        assert(d <= allow, `${id}/${s.id}: grid ${k} ${computed[s.id][k]} differs from the master ${ref[k]}`);
      }
      compared++; cells += computed[s.id].cells;
      stats[s.id] = {avg: ref.avg, min: ref.min, U0: ref.U0, avg_room: ref.avg_room};
    }
    rooms.push({id, name: cr.name, area_m2: cr.area_m2, ceiling_m: cr.ceiling_m, plane_m: cr.plane_m, nx, nz, step_m: room.step_m, stats, pooja_dependent: cr.pooja_dependent_scene_validity || null});
  }

  const rows = C.compliance;
  const kind = r => /^PASS/.test(r.status) ? 'pass' : r.status;
  const counts = {pass: 0, MARGINAL: 0, HOLD: 0};
  for (const r of rows) counts[kind(r)]++;
  const reported = V.compliance_summary;
  assert.deepEqual(counts, {pass: reported.PASS, MARGINAL: reported.MARGINAL, HOLD: reported.HOLD}, 'Compliance rows differ from the master compliance summary');
  const byRoom = {};
  for (const r of rows) {
    const b = byRoom[r.room] ||= {pass: 0, MARGINAL: 0, HOLD: 0};
    b[kind(r)]++;
  }
  const flags = rows.filter(r => kind(r) !== 'pass').map(r => ({room: r.room, status: r.status, check: r.check, value: String(r.value), target: r.target, reason: r.reason, fix: r.cheapest_fix}));

  const sel = V.homeowner_selections.kitchen_worktop, kw = C.kitchen_worktop;
  const kitRow = rows.find(r => r.room === 'KIT' && /Worktop/.test(r.check));
  const fx = id => L.fixtures.find(f => f.id === id);
  assert.equal(sel.option, 'K-2');
  assert(fx('KIT-T4') && fx('KIT-T1'));
  const k2 = {
    option: sel.option, status: sel.status, scope: sel.scope, nominal: sel.nominal_result, residualRisk: sel.residual_risk,
    target: kw.target, planeM: C.rooms.KIT.plane_m,
    final: kw['final_HIGH+TASK_100'], workScene: kw['final_Work_scene(HIGH100,TASK85,COVE50)'], cellGrid: kw['final_cell_grid_0.1m_HIGH+TASK_100'], previousPositions: kw['rev3.3_positions_HIGH+TASK_100'],
    complianceStatus: kitRow.status, complianceNote: kitRow.cheapest_fix, complianceReason: kitRow.reason,
    fixtures: ['KIT-T4', 'KIT-T1'].map(id => ({id, type: fx(id).type, lane: fx(id).lane, circuit: fx(id).circuit, W: fx(id).W_nominal, lm: fx(id).lm, length_m: fx(id).length_m, lm_per_m: Math.round(fx(id).lm / fx(id).length_m)})),
  };

  const meta = {
    available: true,
    label: 'Generic-optics analytical estimate; provisional geometry; not measured, not manufacturer-validated, not construction-released.',
    basis: V.basis,
    maintenance: {MF: C.basis.MF, rho: C.basis.rho, CAL: C.basis.CAL, coveUF: C.basis.cove_UF},
    modelNote: String(C.model),
    ugr: 'UGR is not calculated.',
    source: {file: 'heatmaps.json', sha256, bytes: bytes.length, listedInMaster: true, frame: pack.frame, units: pack.units},
    scenes: SCENES.map(s => ({id: s.id, label: s.label, group: s.group})),
    sceneLevels: C.scenes.levels, sceneCct: C.scenes.cct,
    rooms,
    inactiveRooms: ['CBR'],
    complianceCounts: counts, complianceReported: reported, complianceByRoom: byRoom, flags,
    k2,
    crossCheck: {rooms: rooms.length, scenes: SCENES.length, comparedRoomScenes: compared, cells, maxDiff: worst, toleranceAbs: tol, status: 'grid statistics reproduce the master calculation values within rounding (U0 allows integer-lux rounding where the average is small)'},
    holdIds: V.hold_ids,
    release: {construction_release: V.construction_release, product_approval: V.product_approval},
    deskCBR: 'Inactive: child-room desk grid is carried in the pack but not displayed.',
  };
  const heat = JSON.stringify({units: pack.units, frame: pack.frame, sourceSha256: sha256, rooms: pack.rooms, desk_CBR: pack.desk_CBR});
  return {meta, heat};
}
