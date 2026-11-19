import assert from 'node:assert/strict';
import {createPlan, FT} from './src/master-adapter.js';
import {drawingSource} from './drawing-source.mjs';
import path from 'node:path';

export const FIXED_COVE_CCT = {LIV: 2700, DIN: 2700, MBR: 2700, CBR: 2700, KIT: 2700};
const RAIL_OF_LANE = {HIGH: 'high', COVE: 'low', LINE: 'low', MOOD: 'low', PERIM: 'low'};
const sameLine = a => [...new Set(a)].sort((x, y) => parseInt(x) - parseInt(y));

function applyCctMap(plan, map, D) {
  const {json: M, sha256, file, baselineMasterSha, baseMapSha} = map;
  assert.equal(M.schema, 'lighting-fixed-cct-map/1', 'Unexpected fixed-CCT map schema');
  assert.equal(M.binding?.master_sha256, baselineMasterSha, 'Fixed-CCT map is bound to a different baseline');
  assert.equal(M.status?.construction_release, false);
  assert.equal(M.counts?.fittings, 104);assert.equal(M.counts?.cct_knobs, 0);
  const byId = new Map(M.fittings.map(f => [f.id, f]));
  assert.equal(byId.size, 104, 'Fixed-CCT map must list 104 unique fittings');
  const groupById = new Map(M.groups.map(g => [g.group_id, g]));
  const all = plan.fixtures.zones.flatMap(z => z.fixtures.map(f => [z, f]));
  assert.equal(all.length, 104);
  const bins = {};
  for (const [z, f] of all) {
    const m = byId.get(f.id);
    assert(m, `Fitting ${f.id} missing from the fixed-CCT map`);
    assert.equal(m.room, z.id, `${f.id}: map room ${m.room} != ${z.id}`);
    assert.equal(m.circuit, f.circuit, `${f.id}: map circuit ${m.circuit} != ${f.circuit}`);
    assert.equal(m.lane, f.lane, `${f.id}: map lane ${m.lane} != ${f.lane}`);
    assert(m.cct_fixed === true && [2700, 3000, 4000].includes(m.cct_k), `${f.id}: map CCT must be a fixed 2700/3000/4000 K`);
    assert.equal(parseInt(f.cct), m.cct_k, `${f.id}: canonical fitting and fixed-CCT map disagree`);
    assert(groupById.has(m.group_id), `${f.id}: unknown brightness group ${m.group_id}`);
    f.previousViewerCct = f.cct;
    f.cct = `${m.cct_k}K`;f.cctRule = m.cct_rule;f.mapLayer = m.layer;f.groupId = m.group_id;f.groupControl = m.control;
    f.placementHoldIds = [...m.placement_hold_ids];
    f.held = f.placementHoldIds.length > 0 || ['LIV-P1', 'LIV-P2'].includes(f.id);
    f.holdReason = f.placementHoldIds.length
      ? `${f.placementHoldIds.join(', ')}: ${f.id === 'CBR-L1' || /^CBR-X[1-4]$/.test(f.id)
        ? 'children ceiling, cove and LINE frame require the coordinated ceiling/curtain section and selected fan.'
        : 'placement or coordination evidence remains open.'}`
      : ['LIV-P1', 'LIV-P2'].includes(f.id)
        ? 'H-POOJA-GEOMETRY: count/load allowance only; niche placement and aim withheld.'
        : 'No fixture placement hold is recorded; product and construction approvals remain open.';
    f.cctSource = `Fixed-CCT map ${m.cct_rule}: ${m.cct_reason}`;
    bins[m.cct_k] = (bins[m.cct_k] || 0) + 1;
  }
  assert.deepEqual(bins, Object.fromEntries(Object.entries(M.counts.by_cct_k).map(([k, n]) => [k, n])), 'CCT bin counts differ from the map');
  assert.deepEqual(bins, {2700: 30, 3000: 12, 4000: 62}, 'Expected 30 x 2700 K, 12 x 3000 K, 62 x 4000 K');
  const C = M.curtain_pocket_candidates;
  const S = D.house.lighting.curtain_pocket_s1;
  assert.equal(S.status, 'HOMEOWNER_SELECTED_S1_REVIEW_EXTENSION');
  assert.equal(S.construction_release, false);
  assert.equal(S.product_approval, false);
  assert.equal(S.selected_S1_totals.fittings_including_selected_strips, 108);
  assert.equal(S.selected_S1_totals.circuits_including_selected_strips, 51);
  assert.equal(S.selected_S1_totals.photometry_credit_for_selected_strips, false);
  const selected = new Map(S.strips.map(s => [s.id, s]));
  assert.equal(selected.size, 4, 'Expected four selected S1 curtain strips');
  assert.equal(C.counts_toward_104, false);assert.equal(C.new_knobs, 0);assert.equal(C.cct_k, 2700);
  assert.equal(C.pockets.length, 5, 'Expected 5 curtain-pocket candidates');
  const pockets = C.pockets.map(p => {
    const g = groupById.get(p.group_id);
    assert(g && g.layer === 'LOW', `${p.id}: pocket must follow a LOW brightness group`);
    assert(plan.fixtures.zones.some(z => z.id === p.room), `${p.id}: unknown room ${p.room}`);
    const owner = all.find(([, f]) => f.circuit === g.circuits[0])?.[1];
    assert(owner && owner.rail === 'low', `${p.id}: ${p.group_id} must drive the room LOW rail`);
    assert(Array.isArray(p.polyline_ft) && p.polyline_ft.length >= 2);
    assert.equal(p.cct_k, 2700);
    const placeholderWindow = (p.to_field_measure || []).some(s => /placeholder/i.test(s));
    const s = selected.get(p.id), circuit = s ? `X-${p.id}` : null;
    if (s) {
      assert.equal(p.held, false, `${p.id}: selected strip is held in the map`);
      assert.equal(s.target_knob_group, p.group_id);
      assert.equal(s.cct_k, 2700);
      assert.equal(s.new_knob, false);
      assert.equal(s.photometry_credit, false);
      assert.deepEqual(s.polyline_ft, p.polyline_ft);
      assert(S.selected_S1_electrical.voltage_drop_changed.some(v => v.circuit === circuit && v.new_section), `${p.id}: selected S1 circuit missing`);
    }
    return {id: p.id, room: p.room, status: s?.status || p.status, held: p.held === true, selected: Boolean(s), groupId: p.group_id, circuit, lane: 'LOW', cct: '2700K',
      cctRule: C.cct_rule, placementHoldIds: [...p.placement_hold_ids], polylineFt: p.polyline_ft, indicativeLengthM: p.indicative_strip_length_m, lengthStatus: p.length_status, wEnvelope: p.W_envelope,
      watts: s?.W_nominal ?? null, supply: s?.proposed_supply ?? null, board: s?.fed_from_knob_board ?? null,
      pocketWidthM: s?.window_record?.pocket_widths_m?.[0] ?? null, intoRoomSign: s?.window_record?.into_room_sign ?? null,
      placeholderWindow, label: placeholderWindow ? 'placeholder window, unmeasured' : 'unmeasured'};
  });
  assert.equal(pockets.find(p => p.id === 'CURT-MBR-W03')?.held, true, 'CURT-MBR-W03 must be held');
  assert.equal(pockets.find(p => p.id === 'CURT-CBR')?.held, false, 'CURT-CBR is not held in the map');
  plan.curtainPockets = {
    status: S.status,
    note: 'Four selected 2700 K curtain-pocket strips follow the existing room LOW controls; they add four review circuits but no knobs and receive no lux credit. Pocket sizes, returns and feed access require site measurement. CURT-MBR-W03 remains held and unlit.',
    countsToward104: false, selectedCount: selected.size, newKnobs: 0, pockets,
  };
  return {
    status: 'Fixed-CCT map issued by the lighting authority (supersedes the provisional room table). Brightness control only; no colour-temperature control.',
    rule: M.policy,
    source: {file: path.basename(file), sha256, baseMapSha256: baseMapSha, schema: M.schema, bins: M.counts.by_cct_k, groups: M.counts.groups, knobGroups: M.counts.knob_groups},
    changedFromPrevious: all.filter(([, f]) => f.previousViewerCct !== f.cct).map(([, f]) => `${f.id} ${f.previousViewerCct} -> ${f.cct}`),
  };
}

export function prepareTour(D, {preview, outDir, analysis, cctMap}) {
  const {house, P, V, H, ML, items, tenantBeds} = D;
  const contract = drawingSource(house, D.source, {staging: false, reviewDraft: true, outDir});
  if (contract.hd18?.fragment) contract.hd18.fragment.file = path.basename(contract.hd18.fragment.file);
  const plan = createPlan({house, master_sha256: D.hash, master_filename: 'house-design.json', preview: false});
  plan.version = 'opt1-light-planning-viewer';
  plan.master = {...plan.master, bytes: D.size, contract, optimizationPending: false};
  plan.heights = structuredClone(V.provisional_heights);
  plan.levels = H;
  plan.pooja.frontOnly = true;
  plan.pooja.displayArrangement = structuredClone(V.pooja.display_arrangement);
  plan.pooja.wallFaceM = D.walls.find(w => w.id === V.pooja.wall).rect[2];
  plan.pooja.note = V.pooja.note;
  assert.equal(house.decisions.layout_visual_review.status,'homeowner_accepts_house_model_for_walkthrough');
  const platform=house.decisions.pooja_platform;
  assert.equal(platform.platform_height,null);
  assert.equal(platform.dimensions,null);
  assert.equal(platform.construction_release,false);
  plan.coordinationNotes = {
    platform: {source: 'house-design.json / decisions.pooja_platform',intent:structuredClone(platform),description: 'One fixed platform approximately halfway up the niche, with small idols and a framed picture behind. Exact dimensions and positions are unmeasured.',representation: 'Conceptual front-only display; no platform solid, verified back or assigned dimensions.'},
  };
  plan.stairs = {...plan.stairs, risingFlightShown: false, viewNote: 'Walkthrough view only: the flight rising to the floor above is omitted at homeowner request. Landing, approach and the remaining flight stay shown; the canonical floor plan is unchanged.'};
  plan.roomRelationships = ML;
  plan.numericalLighting = {available: false, reason: 'The viewer does not recompute lux. Brightness sliders change the rendered light only; the heat maps are frozen generic-optics estimates.'};
  plan.analysis = analysis;
  plan.viewer = {
    status: 'REVIEW DRAFT - not a construction release',
    lighting: '104 base photometric fittings / 47 circuits plus 4 selected curtain strips / 4 review circuits; K-2 kitchen task lighting selected for review',
    release: {construction_release: house.lighting.calculation_validity.construction_release, product_approval: house.lighting.calculation_validity.product_approval},
    rails: {high: 'HIGH rail: main downlights and ceiling lights', low: 'LOW rail: cove, mood, line and bath-perimeter lights', independent: 'TASK, MIRROR, FACE, READ, STUDY, ACCENT and NIGHT circuits keep their own control and are not exposed as sliders'},
  };
  plan.holds = {
    niche: V.pooja.rendering_hold,
    lighting: house.lighting.calculation_validity.hold_ids,
    childrenRoute: D.r05ClearanceNote,
    source: contract.note,
  };
  plan.openings = D.openings.map(o => ({
    ...P.openings.find(p => p.id === o.id),
    sillValue: o.sill, headValue: o.head, statusNote: o.statusNote,
    ...(o.curtain ? {curtainSpan: o.curtain.span.map(v => v / FT), curtainBottomM: o.curtain.bottom, curtainTopM: o.curtain.top} : {}),
  }));
  plan.curtains = D.curtains;
  plan.furniture = P.furniture;
  plan.storageItems = items.filter(i => i.storage).map(i => ({
    id: i.id, kind: i.kind, room: i.storage.room_id, rect: i.rect, height: i.h, src: 'assumed',
    homeownerSelection: i.storage.homeowner_selection ? {
      status: i.storage.homeowner_selection.status,
      condition: i.storage.homeowner_selection.condition,
      constructionRelease: i.storage.homeowner_selection.construction_release,
    } : null,
  }));
  plan.tenantBeds = tenantBeds.map(b => ({...b, src: 'assumed', supplied: false}));
  const band = ML.relationship_zones_m.wardrobe_wall_band.rect;
  const bay = ML.relationship_zones_m.window_bay.rect;
  plan.relationshipBands = [
    {id: 'MBR-wardrobe-left', rect: [band[0], band[1], bay[0], band[3]]},
    {id: 'MBR-wardrobe-right', rect: [bay[2], band[1], band[2], band[3]]},
  ];
  plan.suppressedStorageIds = [...D.suppressedIds, ...D.notDrawn.map(i => i.id)];
  plan.bedScope = 'Tenant-supplied queen illustrations inside the accepted mattress envelopes; king outline is a fit comparison, not approval. No fixed bedside cabinets or supplied under-bed joinery.';
  const K2 = new Set(['KIT-T1', 'KIT-T4']);
  const fixedRooms = {};
  for (const z of plan.fixtures.zones) for (const f of z.fixtures) {
    f.masterCct = f.cct;f.masterTunable = Boolean(f.tunable);
    if (f.tunable || /-/.test(String(f.cct))) {
      assert(FIXED_COVE_CCT[z.id], `No fixed CCT for the tunable cove in ${z.id}`);
      f.cct = `${FIXED_COVE_CCT[z.id]}K`;f.cctSource = 'provisional room table';
    } else f.cctSource = 'master fixed white';
    f.tunable = false;
    f.rail = RAIL_OF_LANE[f.lane] || 'independent';
    const bucket = (fixedRooms[z.id] ||= {high: [], low: [], independent: []});
    bucket[f.rail].push(f.cct);
    f.held = (z.id === 'CBR' && !/^CBR-H[1-6]$/.test(f.id)) || ['LIV-P1', 'LIV-P2'].includes(f.id);
    f.holdReason = f.held ? z.id === 'CBR' ? 'Held placeholder (H-CBR-*): ceiling, bed or desk coordination remains open.' : 'Pooja geometry held (H-POOJA-GEOMETRY): count/load allowance only; niche placement and aim withheld.'
      : z.id === 'CBR' ? 'CBR-H1 to H6 active for review; C37 dimmer procurement and site checks remain on hold.'
      : K2.has(f.id) ? 'K-2 kitchen task lighting selected for review, not a construction release. Cabinet and window geometry assumed; sensitivity cases are MARGINAL.'
      : z.id === 'MBR' ? 'Provisional baseline: bed now on sheet-right / compass-west wall; W03 moved. Bed lights and curtain coordination to recheck (OI-MBR-04).'
      : 'OPT-1 review baseline; not a construction release.';
  }
  const mapped = cctMap ? applyCctMap(plan, cctMap, D) : null;
  if (mapped) {
    for (const k of Object.keys(fixedRooms)) delete fixedRooms[k];
    for (const z of plan.fixtures.zones) for (const f of z.fixtures) (fixedRooms[z.id] ||= {high: [], low: [], independent: []})[f.rail].push(f.cct);
    for (const p of plan.curtainPockets.pockets.filter(p => p.selected)) fixedRooms[p.room].low.push(p.cct);
  }
  for (const c of plan.fixtures.controls.circuits) {
    const fx = plan.fixtures.zones.flatMap(z => z.fixtures).filter(f => f.circuit === c.circuit);
    c.masterCct = c.cct;c.cct = sameLine(fx.map(f => f.cct));c.rail = fx[0].rail;
    if (mapped) {
      assert.equal(c.cct.length, 1, `Circuit ${c.circuit} mixes colour temperatures: ${c.cct}`);
      c.groupId = sameLine(fx.map(f => f.groupId)).join(' / ');
    }
  }
  plan.fixedCct = mapped ? {
    ...mapped,
    rooms: Object.fromEntries(Object.entries(fixedRooms).map(([id, r]) => [id, {high: sameLine(r.high), low: sameLine(r.low), independent: sameLine(r.independent)}])),
  } : {
    status: 'PROVISIONAL room table - replace when the fixed-CCT lighting schedule is issued',
    rule: 'Warm 2700-3000 K in living, dining, bedrooms, balcony and pooja; neutral 4000 K in kitchen, bathrooms, utility and dressing task light. Only the master tunable-white coves are re-pinned: living, dining, master and children 2700 K; kitchen 4000 K.',
    coveRePin: FIXED_COVE_CCT,
    rooms: Object.fromEntries(Object.entries(fixedRooms).map(([id, r]) => [id, {high: sameLine(r.high), low: sameLine(r.low), independent: sameLine(r.independent)}])),
  };
  plan.surveyNotes = [
    `REVIEW DRAFT - NOT A CONSTRUCTION RELEASE. Hash-bound to the canonical house record (SHA-256 ${D.hash}). 104 base fittings / 47 circuits plus four selected curtain strips / four review circuits; K-2 kitchen task lighting is selected for review. Construction and product release are both false.`,
    plan.fixedCct.status + '. ' + plan.fixedCct.rule + ' No colour-temperature control is offered.',
    'Brightness sliders change the rendered light only. The heat-map layer is a frozen generic-optics estimate (provisional geometry, not measured, not manufacturer-validated) and is not recomputed by the sliders. UGR is not calculated.',
    'One provisional typical floor, not an exact as-built. Printed numerical room sizes are homeowner-confirmed; positions, heights, furniture and assembly interfaces still carry their source holds.',
    'Approximate homeowner north points to sheet-bottom (+z); east is sheet-left (-x). No surveyed true bearing or solar-obstruction survey is established.',
    `HD-11 unmeasured levels: band / flat kitchen ${H.band} m, raised centre / slab underside ${H.slab} m. Bath ${H.bath} m, utility ${H.utility} m and lobby ${H.lobby} m remain placeholders. Centre-panel cavity depth is unmeasured.`,
    contract.note,
    'Pooja is homeowner-reported already built. Only its unverified front outline is shown; no physical back, extension or structural section is modeled. No new cutting or deepening; structural and lighting holds remain.',
    'Pooja display: small symbolic idols with a framed picture behind, shown conceptually on the front only. The platform and physical back are not modeled or dimensioned.',
    plan.bedScope,
    'Master split wardrobe is approved in principle; displayed blocks and proposed interior compartments are unmeasured and not homeowner-approved for fabrication (OI-MBR-03). W03 curtain coordination remains held (OI-MBR-04).',
    D.r05ClearanceNote,
    'Bathroom basin is left on entry; kitkat tile stays on the L-shaped shower wet walls only. Door hinges, plumbing offsets, mounting and electrical wet-zone suitability need site confirmation.',
    'Child-room HIGH fittings H1-H6 are switchable for review. CBR-L1 (C39 cove) and CBR-X1-X4 (C40 LINE) remain unlit under H-CBR-CEIL pending the ceiling/curtain section and fan selection; desk and bed fittings retain their separate holds. The selected curtain strip follows LOW. Pooja strip/spot positions and aim are not shown. The upper stair flight is omitted from the walkthrough only.',
    'Storage/loft bounds are provisional. Granite is not waterproofing, and no loft support or load capacity is certified by this model.',
    'Dressing cabinet ST-R04a-WR01 and utility cabinet ST-R08-UC01 are homeowner-selected subject to site measurement and clearance/service checks (FH-ST-03 / FH-ST-12). Their displayed shapes are unmeasured and not construction-ready.',
    'D01 is drawn single-leaf in the model, while the architectural description says double-leaf; verify the existing entrance on site.',
    'Assumed MBR-S and CBR strip return lines each extend about 0.30 m beyond a modeled room corner. The viewer clips them only for display; measure and coordinate actual pocket ends before set-out.',
    'Living LOW uses one selected 480 W-class supply in the review record; distribution, protection, compatibility, voltage drop and inrush remain open for qualified electrical design. No product is approved.',
    ...(plan.curtainPockets ? [plan.curtainPockets.note] : []),
  ];
  assert.equal(plan.heights.soffit.value, H.slab);
  assert.equal(plan.pooja.trimM, 0);
  assert(!plan.storageItems.some(i => plan.suppressedStorageIds.includes(i.id)));
  return plan;
}
