import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {prepare,FT} from './layout_views/data.mjs';
import {makeSheet,pageHeader,pageFooter} from './layout_views/svg.mjs';

// Four civil coordination sheets; the only geometry input is the hash-guarded master.
const [source,outDir,expected]=process.argv.slice(2);
if(!source||!outDir||!expected)throw new Error('Usage: node civil_details.mjs <house-design.json> <output folder> <master sha256>');
const D=prepare(source,expected),H=D.house,L=H.lighting;
const masterBytes=fs.readFileSync(source);
const digest=b=>createHash('sha256').update(b).digest('hex');
const P=H.decisions.pooja_niche.dimensions;
const R05=L.design_inputs.ceilings.CBR;
assert.equal(R05.band_h_m,3.048);
assert.equal(R05.tray_h_m,3.2766);
const selected=L.curtain_pocket_s1.strips;
assert.deepEqual(selected.map(x=>x.id).sort(),['CURT-CBR','CURT-DIN','CURT-LIV','CURT-MBR-S']);
assert.equal(H.decisions.r05_clearance.estimated_clearance_mm,387.6);
assert.equal(H.decisions.pooja_platform.idol_or_picture_position,'Small idols with a framed picture behind');
assert.equal(H.storage.homeowner_selections.master_bedroom_split_wardrobe.status,'approved_in_principle');
assert.equal(H.storage.homeowner_selections.included_optional_storage.status,'homeowner_selected_subject_to_site_holds');
assert.deepEqual(H.storage.homeowner_selections.included_optional_storage.items.map(i=>i.id).sort(),['ST-R04a-WR01','ST-R08-UC01']);
assert.equal(L.controls.selected_living_low_supply.supply.retain_supply_id,'P01');
assert.equal(L.controls.selected_living_low_supply.supply.remove_supply_id,'P03');
assert.equal(L.controls.selected_living_low_supply.supply.planned_nameplate_W,480);
assert.equal(L.controls.selected_living_low_supply.supply.reference_output_rating_A,20);
assert.equal(H.lighting.calculation_validity.construction_release,false);
assert.equal(H.decisions.ceiling_heights.raised_panel_clarification.structural_cutting_authorized,false);
const sheet=(title,desc,id,no)=> {
  const S=makeSheet({width:1700,title,desc,metadata:{sheet:id,master_sha256:D.hash,construction_release:false}});
  pageHeader(S,{title,subtitle:'Civil coordination \u00b7 review only \u00b7 all site dimensions require verification',no,total:4,hash:D.hash,compass:false});
  return S;
};
const text=(S,x,y,t,n=17,c='')=>S.text(x,y,t,n,c);
const wrap=(S,x,y,t,w=680,n=16,lead=23,c='')=>S.wrap(x,y,t,w,n,lead,c);
const section=(S,x,y,t)=>text(S,x,y,t,18,'sect');
const lines=(S,x,y,items,w=700,n=16,lead=23,gap=9)=>{
  for(const item of items)y=wrap(S,x,y,item,w,n,lead)+gap;
  return y;
};
const frame=(S,x,y,w,h)=>S.add(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff" stroke="#cfd9d9" rx="6"/>`);
const finish=(S,h)=>{pageFooter(S,h-5,D.hash);return S.finish(h);};
const sheets=[];
function add(id,title,svg){sheets.push({id,title,svg});}

// C01: cross section is an explanatory diagram, not a measured building section.
{
  const S=sheet('Section A \u2014 ceiling and curtain coordination','Conceptual section only; no construction or set-out dimensions','C01-ceiling-section',1);
  section(S,75,165,'SCHEMATIC SECTION / NOT TO SCALE');
  text(S,75,193,'Illustrative section, not verified in R05; pocket, cove and slab are separate conditions.',16,'muted');
  frame(S,75,215,790,720);
  S.add('<rect x="145" y="270" width="650" height="32" fill="#d9dde0" stroke="#5d6e77"/>');
  text(S,165,291,'Concrete slab (underside reference; not surveyed)',15);
  S.add('<rect x="145" y="356" width="290" height="12" fill="#fbf4de" stroke="#9e8e62"/>');
  S.add('<path d="M435 362H472V412H645" fill="none" stroke="#9b641c" stroke-width="8"/>');
  S.add('<circle cx="466" cy="388" r="7" fill="#c4872a"/>');
  S.add('<path d="M645 412H680V340H795" fill="none" stroke="#7c658c" stroke-width="7" stroke-dasharray="9 5"/>');
  S.add('<circle cx="715" cy="375" r="8" fill="#fff" stroke="#5d6e77" stroke-width="3"/><circle cx="758" cy="375" r="8" fill="#fff" stroke="#5d6e77" stroke-width="3"/>');
  S.add('<circle cx="690" cy="353" r="7" fill="#d05a3a"/>');
  S.add('<rect x="795" y="302" width="26" height="530" fill="#cfd8d7" stroke="#5d6e77"/>');
  S.add('<rect x="802" y="520" width="15" height="225" fill="#d7ebf2" stroke="#31818d" stroke-width="3"/>');
  S.add('<path d="M135 832H830" stroke="#203b43" stroke-width="5"/>');
  S.add('<path d="M120 304V832" stroke="#466c92" stroke-width="2" stroke-dasharray="7 5"/>');
  text(S,163,340,'A  separate gypsum / POP centre panel',15);
  text(S,163,396,'Panel level and cavity unverified',14,'red');
  text(S,475,448,'B  band + perimeter cove',15);
  text(S,475,470,'Separate LOW lighting',14,'muted');
  text(S,550,510,'C  curtain pocket',15);
  text(S,550,531,'Tracks, brackets and strip profile',14,'muted');
  text(S,550,553,'fit to be measured',14,'red');
  text(S,145,865,'FFL 0.000  |  window sill / head not measured',15,'muted');
  text(S,145,899,'NOT an instruction to chase or cut concrete.',16,'red');
  section(S,920,165,'DATUMS / PER FLAT');
  let y=lines(S,920,198,[
    '11 ft floor-to-floor (3.3528 m) and about 9 in band drop (0.2286 m): homeowner-stated, not measured.',
    'Elsewhere, assumed slab and finish thicknesses yield an old 3.188 m slab and 2.959 m band estimate; neither is surveyed.',
    `R05 only: band ${R05.band_h_m.toFixed(3)} m and centre approx. ${R05.tray_h_m.toFixed(3)} m are homeowner-reported, not surveyed.`,
    'R05 slab unmeasured: the reported centre conflicts with the older slab estimate. The real section and wiring cavity remain unknown.',
    'Bathroom, utility, lobby and balcony levels and hall cross-beam soffit are not provided. Measure before coordination.'
  ],690,16,23,11);
  section(S,920,y+16,'COVE IS NOT THE CURTAIN POCKET');y+=48;
  y=lines(S,920,y,[
    'Cove: perimeter ceiling-light feature, fixed 2700 K. Curtain pocket: concealed ceiling-track recess at a window; it is not automatically an LED cove.',
    'Living, master and children: two tracks, sheer plus blackout. Selected S1 strips add a separate 2700 K profile within four pocket locations, only if site fit, access and clearance are verified.',
    'CURT-LIV, CURT-DIN, CURT-MBR-S and CURT-CBR selected for review. CURT-MBR-W03 remains held and excluded. Do not fabricate from assumed strip centre-lines.'
  ],690,16,23,11);
  section(S,75,1000,'SITE MOCK-UP BEFORE CLOSING THE CEILING');
  lines(S,75,1032,[
    'Measure pocket clear width and depth, return lengths, two-track spacing, curtain stack, brackets and the strip/profile/lip. Confirm the source is concealed at standing and seated eye height.',
    'Confirm profile fixing, cable bends, ventilated and accessible drivers / junctions, the HIGH versus LOW local controls and the selected dimmer/fitting chain with the electrician.',
    'MBR-S and CBR assumed strip returns run about 0.30 m beyond their model room corners. This is a model clash, not a site measurement; resolve after measuring actual ends.'
  ],1510,16,23,10);
  add('C01-ceiling-section','Ceiling, cove and curtain section',finish(S,1375));
}

// C02: opening widths are rounded model spans for identification only, never fabrication sizes.
{
  const S=sheet('Openings and stair \u2014 site register','All opening dimensions and stair geometry require field survey','C02-openings-stair',2);
  section(S,75,165,'OPENING IDS / MODEL REFERENCE ONLY');
  text(S,75,195,'Widths below are rounded model spans, NOT measured openings, clear leaves or fabrication sizes.',16,'red');
  text(S,75,220,'For each F1-F4: record actual clear width, height, jamb offsets, sill/head, leaf/hinge and swing.',16,'muted');
  const order=['D01','D02','D03','D04','D05','D06','W01','W02','W03','W04','W05','W06','W07','V01','V02','G01','G02','PN1','SN1','SN2','UP1'];
  const desc={D01:'Main entrance',D02:'Master bedroom door',D03:'Children bedroom door',D04:'Attached toilet door',D05:'Common toilet door',D06:'Kitchen / utility door',
    W01:'Kitchen exterior window',W02:'Kitchen / utility window',W03:'Master south window',W04:'Master west window',W05:'Children west window',
    W06:'Living east window',W07:'Dining east window',V01:'Attached toilet vent',V02:'Common toilet vent',
    G01:'Entry glazed panel 1',G02:'Entry glazed panel 2',PN1:'Pooja niche front',SN1:'Attached shower niche',SN2:'Common shower niche',UP1:'Utility parapet opening'};
  const sourceLabel=o=>o.code==='PN1'?'homeowner estimate; built':
    ['SN1','SN2'].includes(o.code)?'proposed model; existing recess to verify':
    o.code==='W03'?'roughly centred; width / offsets unmeasured':
    o.code==='W05'?'concealed placeholder; not surveyed':
    o.src==='assumed'?'assumed / proposed':'scaled model; site unverified';
  const lookup=Object.fromEntries(D.openings.map(o=>[o.code,o]));
  assert.equal(order.length,D.openings.length);
  const table=(ids,x,y)=>{
    text(S,x,y,'ID',14,'sect');text(S,x+95,y,'LOCATION / BASIS',14,'sect');text(S,x+625,y,'MODEL m',14,'sect');
    y+=18;
    for(const id of ids){
      const o=lookup[id];assert(o,`Missing opening ${id}`);
      S.add(`<path d="M${x} ${y}H${x+720}" stroke="#d7e0df"/>`);
      text(S,x,y+21,id,16,'mono');
      text(S,x+95,y+20,desc[id],16);
      text(S,x+625,y+20,((o.span[1]-o.span[0])).toFixed(2),16,'mono');
      text(S,x+95,y+40,sourceLabel(o),13,'muted');
      y+=53;
    }
  };
  table(order.slice(0,11),75,260);table(order.slice(11),885,260);
  section(S,75,900,'OPENING CONFLICTS / HOLD');
  lines(S,75,932,[
    'D01: the architecture description says double-leaf while the current visualization shows a single leaf. Confirm the actual entrance, sidelights and swing per floor; neither depiction is a joinery order.',
    'W03 is roughly centred by homeowner description, not measured. W05 is a 0.75 m visual placeholder behind a curtain; its real width, jambs and sill/head are unknown.',
    'D03 and D04/D05 hinge/swing are proposed. Confirm existing frames, bathroom door swing and loft clearance; no re-hanging or cutting is authorised.'
  ],720,16,23,11);
  section(S,885,900,'S01 / STAIR \u2014 SURVEY, DO NOT SET OUT');
  lines(S,885,932,[
    'The model shows two flights and a turning bay beside the balcony. Its 7 and 15 drawn tread lines are illustrative, not verified riser counts.',
    'Measure each floor\u2019s rise, tread/going, width, landings, arrival direction, headroom and guard geometry. Confirm the actual entry connection and the applicable local rules with the responsible professional.',
    'The master has four requested floor instances F1-F4, but actual storey labels, elevations and differences are unknown. Record each separately; do not assume four identical as-built flats.'
  ],720,16,23,11);
  add('C02-openings-stair','Opening register and stair site survey',finish(S,1375));
}

// C03: only a front outline of the pooja niche is represented.
{
  const S=sheet('Pooja and lofts \u2014 no structural assumptions','Existing niche, proposed display and held loft details','C03-pooja-lofts',3);
  section(S,75,165,'PN1 / EXISTING NICHE \u2014 FRONT ONLY');
  frame(S,75,195,730,650);
  S.add('<rect x="110" y="235" width="320" height="530" fill="#f4f1ea" stroke="#8a9a9c"/>');
  S.add('<rect x="200" y="295" width="140" height="390" fill="#f1eaf6" stroke="#786385" stroke-width="3" stroke-dasharray="10 7"/>');
  S.add('<path d="M215 490H325" stroke="#786385" stroke-width="3" stroke-dasharray="8 6"/>');
  S.add('<path d="M100 765H445" stroke="#203b43" stroke-width="4"/>');
  text(S,125,805,'ROOM FACE / FFL',15,'muted');
  text(S,465,265,'HOMEOWNER ESTIMATES',16,'red');
  let y=lines(S,465,296,[
    `Width ${P.width_mm} mm; sill ${P.sill_m} m; top ${P.top_m} m.`,
    `Opening height ${P.height_mm} mm derived; depth ${P.depth_mm} mm estimated.`,
    'North-corner gap 406.4 mm estimated. All require a site survey.',
    'One fixed platform intended roughly halfway up; its actual height and size are unknown.'
  ],310,15,22,10);
  text(S,110,835,'Front outline only. Physical back and extension are not drawn.',15,'red');
  section(S,865,165,'LOFTS / WARDROBES');
  frame(S,865,195,760,650);
  S.add('<path d="M925 480H1545M925 275V480M1545 275V480" fill="none" stroke="#819594" stroke-width="3"/>');
  S.add('<rect x="955" y="300" width="560" height="88" fill="#f2f0f8" stroke="#7a6fa8" stroke-width="2" stroke-dasharray="8 5"/>');
  S.add('<rect x="985" y="398" width="170" height="260" fill="#e3d3bd" stroke="#4b6a78" stroke-width="2"/>');
  S.add('<rect x="1195" y="398" width="280" height="260" fill="#dce4ef" stroke="#5b7795" stroke-width="2"/>');
  text(S,1010,350,'continuous loft: extent / support to verify',16);
  text(S,1015,540,'DOOR',16);text(S,1280,540,'WARDROBE',16);
  text(S,925,700,'R05: one continuous loft over entrance and wardrobe.',16);
  text(S,925,727,'Soffit / top / depth / support / load are unmeasured.',15,'red');
  text(S,925,754,'2.20 m is a project target, NOT a verified code minimum.',15,'muted');
  section(S,75,895,'CONSTRAINTS AND RELEASE GATES');
  lines(S,75,928,[
    'The niche is already built. The homeowner reports an external reinforced extension beyond the wall, but its geometry and capacity are not independently verified. An estimated depth greater than the model wall is not proof of unsafe or impossible construction.',
    'Selected display: small idols with a framed picture behind. Exact positions, display sizes, platform fixing and thermal/fire clearances remain unmeasured or unapproved. LIV-P1/P2 are held allowances, not final light positions.',
    'No niche deepening, concrete cutting, slab chasing or new structural support is authorised. Have the responsible professional verify the existing extension, fixings and permissible loads.',
    'Master split wardrobe is approved in principle; OPT-E BWP plywood carcass and laminate shutters are selected. Its dimensions and loft remain site holds. The utility shelf is recorded as existing RCC; check its actual condition and capacity.',
    'Dressing cabinet ST-R04a-WR01 and utility cabinet ST-R08-UC01 are selected subject to measured fit, circulation and service access; their drawn dimensions are unmeasured placeholders.'
  ],1510,16,23,11);
  add('C03-pooja-lofts','Pooja front, loft and wardrobe coordination',finish(S,1375));
}

// C04: explicit action owners and decision versus site/professional holds.
{
  const S=sheet('Site checklist \u2014 each floor separately','Review is complete without inventing field measurements','C04-site-checklist',4);
  section(S,75,165,'COPY FOR EACH STOREY');
  text(S,75,195,'Master instances F1-F4 are placeholders: actual G / 1 / 2 / 3 labels and floor differences are not confirmed.',16,'red');
  text(S,75,222,'Actual storey: __________________   Date: __________   Surveyed by: __________________',16,'muted');
  const boxes=[
    {x:75,y:260,w:740,h:420,title:'MASON / SITE SURVEY',items:[
      'Record room internal dimensions, wall thicknesses, openings, lintel/sill/head heights and door swings; photograph and label each room.',
      'Reconcile dining 110.6 mm, living 145.1 mm and master 41.1 mm model assembly residuals. These are not measured gaps; do not fill or move walls from the model.',
      'Confirm actual D01 leaf count, W03 offsets, W05 size, both toilet hinges and utility parapet / corner height.'
    ]},
    {x:865,y:260,w:760,h:420,title:'CEILING / JOINERY',items:[
      'Survey FFL, slab underside, band, centre-panel level, beam soffit and bath / utility / lobby ceilings; record measured floor-finish and slab thickness.',
      'Mock up curtain pocket, two tracks, brackets, stack and the selected profile; MBR-S / CBR modeled returns cross room boundaries, so coordinate actual ends.',
      'Measure wardrobe, loft soffit / depth and shutter clearance. Keep the approved split layout in principle; do not fabricate placeholder dimensions.',
      'Dressing cabinet ST-R04a-WR01: measure clear width and door / route clearance (FH-ST-03). Utility cabinet ST-R08-UC01: measure geometry and service access (FH-ST-12). Both selections remain conditional.'
    ]},
    {x:75,y:715,w:740,h:430,title:'ELECTRICIAN / LIGHTING',items:[
      'Fixed CCT is assigned by fitting; coves and the four selected S1 strips are 2700 K. LOW mood and HIGH general use local controls.',
      'CBR-H1-H6 are active/switchable at accepted positions. C37 dimmer and the exact fitting / driver / control chain are procurement holds, not construction release.',
      'Confirm supply access, cable routes, wet-zone protection, product fit and each pocket mock-up. W03 strip is held; pooja lights are allowances only.',
      'Living LOW uses one selected P01 supply concept (24 V, 480 W nameplate); no product is approved. The 20 A supply reference exceeds a candidate controller input of 12.5 A. Hold controller / repeater, distribution, branch protection and inrush for electrical design.'
    ]},
    {x:865,y:715,w:760,h:430,title:'STRUCTURAL / SITE PROFESSIONAL',items:[
      'Review stair rise, going, landings, headroom and guard against applicable local requirements on every storey.',
      'Verify existing niche extension, platform fixing, fire clearance, load capacity and loft supports; no new cutting or deepening authorised.',
      'Measure actual tenant bed frame and study return: the 387.6 mm R05 model pinch is not a comfortable route. Keep selected layout; escalate only with measured consequences.'
    ]}
  ];
  for(const b of boxes){
    frame(S,b.x,b.y,b.w,b.h);section(S,b.x+18,b.y+30,b.title);
    lines(S,b.x+18,b.y+65,b.items,b.w-38,15,22,13);
  }
  section(S,75,1200,'OPEN HOMEOWNER DESIGN CHOICE VS SITE / PROFESSIONAL HOLD');
  lines(S,75,1232,[
    'Open design choice recorded in the master: pooja niche back / base finish. Small idols with a framed picture behind and the approximate platform intent are already selected; exact placement is a site coordination matter.',
    'Do not re-ask the HD-15 furniture layout, the four S1 strips, fixed CCT, CBR-H1-H6 or the split-wardrobe concept. Measurements, code compliance, product compatibility, capacities and formal professional approvals remain open.'
  ],1510,15,22,9);
  add('C04-site-checklist','Per-floor site and professional checklist',finish(S,1415));
}

const openingRegister=D.openings.map(o=>{
  const vi=H.visualization_geometry.openings.findIndex(v=>v.id===o.id);
  let geometryRef;
  if(vi>=0)geometryRef=`house-design.json#/visualization_geometry/openings/${vi}/span`;
  else {
    const match=/^(bath[12])-(door|vent|niche)$/.exec(o.id);
    assert(match,`Missing current-master opening source for ${o.id}`);
    const bi=H.bathrooms.rooms.findIndex(b=>b.renderer_room_id===match[1]);
    assert(bi>=0,`Missing bathroom source for ${o.id}`);
    const field={door:'entrance/opening_segment_m',vent:'window/segment_m',niche:'shower/niche_width_m'}[match[2]];
    geometryRef=`house-design.json#/bathrooms/rooms/${bi}/${field}`;
  }
  return {
    code:o.code,name:o.name,kind:o.kind,model_opening_id:o.id,model_wall_id:o.wall,
    model_geometry_ref:geometryRef,model_width_m:Number((o.span[1]-o.span[0]).toFixed(2)),
    model_width_status:o.code==='PN1'?'homeowner_estimate_unverified':
      ['SN1','SN2'].includes(o.code)?'proposed_model_not_measured':o.src==='assumed'?'assumed_not_measured':'scaled_model_not_measured',
    actual_width_m:null,actual_height_m:null,actual_jamb_offsets_m:null,storey_measurements:'required_separately_F1_to_F4'
  };
});
const overlaps=selected.filter(s=>['CURT-MBR-S','CURT-CBR'].includes(s.id)).map(s=>{
  const room=H.visualization_geometry.rooms.find(r=>r.id===(s.room==='MBR'?'master':'children'));
  const modelEnd=Math.max(...s.polyline_ft.map(p=>p[1]*FT));
  const excess=modelEnd-room.rect[3];
  assert(excess>.29&&excess<.31,`${s.id} return overlap changed; re-evaluate the hold`);
  return {id:s.id,excess_beyond_model_room_m:Number(excess.toFixed(2)),status:'assumed_model_clash_not_site_measurement'};
});
assert.equal(digest(fs.readFileSync(source)),D.hash,'Master changed during civil-detail generation');
fs.mkdirSync(outDir,{recursive:true});
for(const s of sheets)fs.writeFileSync(path.join(outDir,`${s.id}.svg`),s.svg);
fs.writeFileSync(path.join(outDir,'opening-register.json'),JSON.stringify({
  schema:'civil_opening_register/1',source_master_sha256:D.hash,scope:'model identification only; rounded to 0.01 m; no as-built dimensions',
  storeys:H.architecture.floor_instances.map(f=>({id:f.id,actual_storey_label:f.actual_storey_label,site_variations:f.site_variations})),
  openings:openingRegister,entrance_leaf_conflict:'Architecture describes double-leaf; current visualization depicts single-leaf. Existing condition unverified.',
  strip_return_model_holds:overlaps,construction_release:false
},null,2));
fs.writeFileSync(path.join(outDir,'details-source.json'),JSON.stringify({
  source_master_sha256:D.hash,construction_release:false,sheets:sheets.map(s=>({id:s.id,title:s.title,file:`${s.id}.svg`,sha256:digest(Buffer.from(s.svg))})),
  selected_strips:selected.map(s=>s.id),strip_return_model_holds:overlaps
},null,2));
console.log(`Generated ${sheets.length} civil detail sheets and ${openingRegister.length} opening records from ${D.hash}`);
