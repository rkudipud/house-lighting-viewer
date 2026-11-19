import {makeSheet,pageHeader,pageFooter,northArrow,esc,fx,COMPASS_NOTE,COMPASS_SOURCE,HEIGHT_NOTE,POOJA_NOTE,CENTRE_NOTE,CURTAIN_NOTE} from './svg.mjs';
import {FT} from './data.mjs';
import {SC,TX,TY,polyPath,drawWalls,compassEdgeLabels} from './plan.mjs';
import assert from 'node:assert/strict';

export const LANE_COLOR={HIGH:'#3d6fa5',COVE:'#c4872a',MOOD:'#8a5fa8',LINE:'#17877e',ACCENT:'#cc6a2b',TASK:'#4d8f3a',READ:'#7c8a2a',NIGHT:'#6b7480',MIRROR:'#c0568a',FACE:'#ad467b',PERIM:'#c4872a',STUDY:'#8d6a3d',NEUTRAL:'#36484f'};
export const ROOM_LEVEL={living:'band',dining:'band',master:'band',dressing:'band',children:'band',lobby:'lobby',kitchen:'flat',bath1:'bath',bath2:'bath',utility:'utility',washing:'utility',balcony:'none'};
const LEVEL_FILL={band:'#eceff4',flat:'#f8f0d6',bath:'#dff0ee',utility:'#ebe6d6',lobby:'#e6ecdc',none:'url(#nowall)'};
// held fittings named in the lighting hold list (hold-list.md); every id is asserted against the master fixtures
const HOLD_FIX={'H-CENTRE-RECESS':['LIV-X1','LIV-X2','DIN-X1','DIN-L1'],'H-HALL-BEAM':['DIN-H2','DIN-H3','FW-T1'],'H-DRS-SWEEP':['DRS-H1','DRS-H2'],'H-POOJA-GEOMETRY':['LIV-P1','LIV-P2']};
const HOLD_TAG={'H-CENTRE-RECESS':'CR','H-HALL-BEAM':'HB','H-DRS-SWEEP':'DS','H-POOJA-GEOMETRY':'PG'};
const FIX_ROOM={BAL:'Entry / balcony',CBR:"Children's bedroom",DIN:'Dining',DRS:'Dressing',KIT:'Kitchen',LIV:'Living',LOB:'Lobby',MBR:'Master bedroom',TL1:'TL1 toilet',TL2:'TL2 toilet',UTL:'Utility'};

export function roundedPath(pts,radii,closed){
  const n=pts.length,rad=i=>Array.isArray(radii)?radii[i]:radii;
  const unit=(a,b)=>{const dx=b[0]-a[0],dz=b[1]-a[1],l=Math.hypot(dx,dz);return [dx/l,dz/l,l];};
  const cs=pts.map((p,i)=>{
    const end=!closed&&(i===0||i===n-1);
    if(end||!rad(i))return {p,a:p,b:p,r:0};
    const u1=unit(p,pts[(i-1+n)%n]),u2=unit(p,pts[(i+1)%n]),r=Math.min(rad(i),u1[2]/2,u2[2]/2);
    const cross=(-u1[0])*u2[1]-(-u1[1])*u2[0];
    return {p,r,a:[p[0]+u1[0]*r,p[1]+u1[1]*r],b:[p[0]+u2[0]*r,p[1]+u2[1]*r],sweep:cross>0?1:0};
  });
  const P=q=>`${fx(q[0],4)} ${fx(q[1],4)}`;
  let d=`M${P(cs[0].b)}`;
  for(let k=1;k<=(closed?n:n-1);k++){
    const c=cs[k%n];
    d+=`L${P(c.a)}`;
    if(c.r)d+=`A${fx(c.r,4)} ${fx(c.r,4)} 0 0 ${c.sweep} ${P(c.b)}`;
  }
  return d+(closed?'Z':'');
}

// symbols in model units (metres) so the legend can reuse them
export function symbol(type,x,z,lane,{ghost=false}={}){
  const c=LANE_COLOR[lane]||'#555',sw=.014,op=ghost?' opacity=".45"':'';
  const g=inner=>`<g${op}>${inner}</g>`;
  const circ=(r,fill='#fff')=>`<circle cx="${fx(x,4)}" cy="${fx(z,4)}" r="${fx(r,4)}" fill="${fill}" stroke="${c}" stroke-width="${sw}"/>`;
  let m;
  if((m=/^DL(\d+)(A|V)?$/.exec(type))){
    const r=.05+.006*Number(m[1]);let s=circ(r);
    if(m[2]==='A')s+=`<path d="M${fx(x-r*.7,4)} ${fx(z+r*.7,4)}L${fx(x+r*1.5,4)} ${fx(z-r*1.5,4)}" stroke="${c}" stroke-width="${sw}"/>`;
    else if(m[2]==='V')s+=`<circle cx="${fx(x,4)}" cy="${fx(z,4)}" r="${fx(r*.55,4)}" fill="none" stroke="${c}" stroke-width="${sw}"/>`;
    else s+=`<circle cx="${fx(x,4)}" cy="${fx(z,4)}" r="${fx(r*.28,4)}" fill="${c}"/>`;
    return g(s);
  }
  if(type==='PIN6V'){const r=.045;return g(circ(r)+`<path d="M${fx(x-r,4)} ${fx(z,4)}H${fx(x+r,4)}M${fx(x,4)} ${fx(z-r,4)}V${fx(z+r,4)}" stroke="${c}" stroke-width="${sw}"/>`);}
  if((m=/^BSPOT(\d)V$/.exec(type))){const r=.04+.004*Number(m[1]),k=r*.65;return g(circ(r)+`<path d="M${fx(x-k,4)} ${fx(z-k,4)}L${fx(x+k,4)} ${fx(z+k,4)}M${fx(x-k,4)} ${fx(z+k,4)}L${fx(x+k,4)} ${fx(z-k,4)}" stroke="${c}" stroke-width="${sw}"/>`);}
  if((m=/^BDIF(\d)V$/.exec(type))){const r=.04+.004*Number(m[1]),k=r*.5;return g(circ(r)+`<rect x="${fx(x-k,4)}" y="${fx(z-k,4)}" width="${fx(2*k,4)}" height="${fx(2*k,4)}" fill="none" stroke="${c}" stroke-width="${sw}"/>`);}
  if(type==='FACEV')return g(`<rect x="${fx(x-.035,4)}" y="${fx(z-.035,4)}" width=".07" height=".07" fill="${c}" stroke="${c}" stroke-width=".006"/>`);
  if(type==='FACE10V')return g(`<rect x="${fx(x-.18,4)}" y="${fx(z-.025,4)}" width=".36" height=".05" fill="${c}" stroke="${c}" stroke-width=".006"/>`);
  if(type==='PEND')return g(circ(.17,'#fff')+`<circle cx="${fx(x,4)}" cy="${fx(z,4)}" r=".08" fill="${c}"/>`);
  if(type==='TRK6')return g(`<path d="M${fx(x,4)} ${fx(z-.08,4)}L${fx(x+.08,4)} ${fx(z,4)}L${fx(x,4)} ${fx(z+.08,4)}L${fx(x-.08,4)} ${fx(z,4)}Z" fill="#fff" stroke="${c}" stroke-width="${sw}"/>`);
  if(type==='TRKLIN')return g(`<rect x="${fx(x-.1,4)}" y="${fx(z-.03,4)}" width=".2" height=".06" fill="#fff" stroke="${c}" stroke-width="${sw}"/>`);
  if(type==='READ')return g(`<path d="M${fx(x,4)} ${fx(z-.08,4)}L${fx(x+.07,4)} ${fx(z+.06,4)}L${fx(x-.07,4)} ${fx(z+.06,4)}Z" fill="#fff" stroke="${c}" stroke-width="${sw}"/>`);
  if(type==='STEP')return g(`<rect x="${fx(x-.05,4)}" y="${fx(z-.05,4)}" width=".1" height=".1" fill="#fff" stroke="${c}" stroke-width="${sw}"/><circle cx="${fx(x,4)}" cy="${fx(z,4)}" r=".018" fill="${c}"/>`);
  if(type==='UPDNV')return g(`<path d="M${fx(x-.07,4)} ${fx(z-.07,4)}L${fx(x+.07,4)} ${fx(z-.07,4)}L${fx(x,4)} ${fx(z,4)}L${fx(x+.07,4)} ${fx(z+.07,4)}L${fx(x-.07,4)} ${fx(z+.07,4)}Z" fill="#fff" stroke="${c}" stroke-width="${sw}"/>`);
  if(type==='CYLSV')return g(circ(.08,c));
  if(type==='BULKD')return g(circ(.09)+`<circle cx="${fx(x,4)}" cy="${fx(z,4)}" r=".05" fill="none" stroke="${c}" stroke-width="${sw}"/>`);
  throw new Error(`No RCP symbol rule for fixture type ${type}`);
}
function pathStyle(type,lane){
  const c=LANE_COLOR[lane]||'#555';
  if(type==='COVE_TW'||type==='COVE_FW'||type==='BCOVE')return {c,w:.04,dash:'.10 .05'};
  if(type==='LIN')return {c,w:.045,dash:''};
  if(type==='BACK')return {c,w:.035,dash:'.03 .04'};
  return {c,w:.025,dash:'.06 .03'};
}

function fansDraw(S,D){
  let n=0;
  for(const f of D.fans){
    const pending=!f.at_m,provisional=pending||/^provisional/.test(f.status||''),at=f.at_m||f.proposal.global_xz_m,[x,z]=at;
    S.add(`<g data-fan-room="${esc(f.room)}" data-fan-status="${provisional?'provisional':'assumed'}"${provisional?' opacity=".6"':''}>`);
    // planning sweep (nominal blade-tip circle) where one is recorded; not a product clearance
    const sweep=Number(f.proposal?.sweep_mm);
    if(sweep>0)S.add(`<circle data-fan-sweep-mm="${sweep}" cx="${fx(x,4)}" cy="${fx(z,4)}" r="${fx(sweep/2000,4)}" fill="none" stroke="#4f6b73" stroke-width=".012" stroke-dasharray=".06 .05"/>`);
    S.add(`<circle cx="${fx(x,4)}" cy="${fx(z,4)}" r=".26" fill="#fff" stroke="#4f6b73" stroke-width=".014"${provisional?' stroke-dasharray=".05 .04"':''}/>`);
    for(let a=0;a<4;a++){const t=a*Math.PI/2+Math.PI/4;S.line([x,z],[x+.26*Math.cos(t),z+.26*Math.sin(t)],'#4f6b73',.02);}
    S.label(x,provisional?z-.36:z+.43,provisional?(sweep>0?`FAN \u2014 provisional, ${sweep} mm planning sweep`:'FAN \u2014 provisional'):'FAN POINT',.075,'#3f565d');
    S.add('</g>');n++;
  }
  return n;
}

export function buildRcp(D,{no,total}){
  const H=2260,W=1700;
  const L=D.house.lighting,fixtures=L.fixtures,CE=L.design_inputs.ceilings;
  const circuitIds=[...new Set(fixtures.map(f=>f.circuit))].sort();
  assert(fixtures.every(f=>typeof f.circuit==='string'&&f.circuit),'Every fitting must name its circuit');
  assert.deepEqual(circuitIds,L.controls.circuits.map(c=>c.circuit).sort(),'Fitting circuits must reconcile with the canonical controls');
  const lightingSummary=`${fixtures.length} base fittings, ${circuitIds.length} controlled groups`;
  const fixedWhite=L.status==='FIXED_WHITE_HOMEOWNER_SIGNED_REVIEW_CANDIDATE_NOT_CONSTRUCTION_RELEASED';
  const opt1=/^OPT1/.test(L.status)||fixedWhite,k2=L.calculation_validity.homeowner_selections?.kitchen_worktop;
  const strips=fixedWhite?L.curtain_pocket_s1.strips:[];
  if(fixedWhite){
    assert.equal(strips.length,4);assert(strips.every(s=>s.cct_k===2700&&!s.new_knob&&!s.photometry_credit));
    assert.equal(L.curtain_pocket_s1.selected_S1_totals.fittings_including_selected_strips,108);
    assert.equal(L.curtain_pocket_s1.selected_S1_totals.circuits_including_selected_strips,51);
  }
  if(opt1){
    assert.equal(k2?.option,'K-2','OPT-1 master must record the homeowner-selected kitchen option K-2');
    assert(fixtures.some(f=>f.id==='KIT-T4')&&fixtures.some(f=>f.id==='KIT-T1'&&f.type==='TASK_LO'),'K-2 fittings KIT-T4 and KIT-T1 (lower output) must be in the master');
    assert.equal(L.calculation_validity.construction_release,false);
  }
  const lightingNote=opt1
    ?`OPT-1 calculated review candidate from the bound master (${lightingSummary}). Four selected 2700 K curtain strips bring the review schedule to 108 fittings / 51 circuits; no new knobs or photometry credit. Kitchen task option K-2 is homeowner-selected for review: it adds the sink-end linear KIT-T4 and lowers KIT-T1 output. Generic-optics analytic estimates, not measured or manufacturer-validated; no photometry is shown on this sheet. Not construction-released; product, driver, dimmer and site-fit holds remain open. Each bathroom face-light pair has its own knob (HD-17). Pooja fittings remain count/load allowances only, with inherited positions held (H-POOJA-GEOMETRY); no corrected placement is implied.`
    :`${D.drawingSource.lighting_pending?'STAGING: lighting is stale pending HD-18 recoordination. ':''}HD-14 lighting proposal from the bound master (${lightingSummary}), including HD-16 and HD-17. Not construction-released; no photometry is shown. Each bathroom face-light pair has its own knob (HD-17). Pooja fittings remain count/load allowances only, with inherited positions held (H-POOJA-GEOMETRY); no corrected placement is implied. Site and product-fit holds remain open.`;
  const S=makeSheet({width:W,title:'Reflected ceiling plan (looking up)',desc:`Read-only reflected ceiling plan from the canonical master; HD-11 levels are homeowner-stated or derived and unmeasured; lighting is the ${opt1?'OPT-1 calculated review candidate':'HD-14 coordinated proposal'}, not construction-released.`,
    metadata:{sheet:'02-rcp',master_sha256:D.hash,fixtures:fixtures.length,circuits:circuitIds.length,heights:'hd11_homeowner_stated_or_derived_unmeasured',lighting_status:L.status}});
  pageHeader(S,{title:'Reflected ceiling plan \u2014 bottoms-up',subtitle:`Looking up \u00b7 south-up, same as plan \u00b7 ${opt1?'OPT-1 review candidate (K-2 kitchen)':'HD-14 proposal'}: ${lightingSummary} \u00b7 not released`,no,total,hash:D.hash});
  S.add(`<g id="rcp-plan" transform="translate(${TX} ${TY}) scale(${SC})">`);
  S.rect([0,0,D.plot.x*FT,D.plot.z*FT],'none','#b8c5c4',.012,'stroke-dasharray=".08 .06"');
  // ceiling levels
  for(const r of D.rooms){S.add(`<g data-room-id="${r.id}" data-ceiling-level="${ROOM_LEVEL[r.id]}">`);S.path(polyPath(r.poly),LEVEL_FILL[ROOM_LEVEL[r.id]],'none',0);S.add('</g>');}
  // hall cross-beam band: soffit is unmeasured (H-HALL-BEAM); the kitchen is one flat ceiling at band level
  const bb=CE.HALL.beam_band,kit=D.rooms.find(r=>r.id==='kitchen'),din=D.rooms.find(r=>r.id==='dining');
  const beam=[Math.min(kit.rect[0],din.rect[0]),bb.z0_ft*FT,Math.max(kit.rect[2],din.rect[2]),bb.z1_ft*FT];
  S.add('<g data-ceiling="beam-band">');S.rect(beam,'url(#beam)','#b58a4c',.012);S.add('</g>');
  // Panel outlines are recorded; their installed level and clear cavity depth are unmeasured.
  const ft2=a=>a.map(p=>[p[0]*FT,p[1]*FT]);
  const tray=(key,fill='#fbf4de')=>{
    const c=CE[key],pts=ft2(c.tray_corners_ft),radii=Array.isArray(c.tray_radii_ft)?c.tray_radii_ft.map(r=>r*FT):c.tray_radii_ft*FT;
    S.add(`<g data-ceiling="tray-${key}" data-tray-height="${D.H.panel}">`);S.path(roundedPath(pts,radii,true),fill,'#b9a36d',.018);S.add('</g>');
  };
  tray('HALL');tray('MBR');tray('CBR');
  // frames on the band and the painted-black false-track grooves
  const frame=key=>{S.path(roundedPath(ft2(CE[key].frame_ft),0,true),'none','#9aa3ad',.012,'stroke-dasharray=".05 .04"');};
  frame('MBR');frame('CBR');
  let grooves=0;
  for(const b of CE.MBR.lines_black){
    S.add('<g data-groove="MBR">');S.path(roundedPath(ft2(b.fillet.corners_ft),b.fillet.radii_ft*FT,false),'none','#111',.05);S.add('</g>');grooves++;
  }
  for(const b of CE.CBR.lines_black){
    S.add('<g data-groove="CBR">');S.path(`M${ft2(b.pts_ft).map(p=>fx(p[0],4)+' '+fx(p[1],4)).join('L')}`,'none','#111',.05);S.add('</g>');grooves++;
  }
  // lofts, held wardrobe zones
  for(const it of D.items.filter(i=>i.storage&&/loft/.test(i.kind))){
    S.add(`<g data-storage-id="${esc(it.storage.id)}" data-storage-kind="${esc(it.storage.kind)}">`);
    S.rect(it.storage.drawBounds,'url(#loft)','#526d9a',.02,'stroke-dasharray=".07 .04"');S.add('</g>');
  }
  const band=D.ML.relationship_zones_m.wardrobe_wall_band.rect;
  S.add('<g data-zone="master-wardrobe-wall-held">');S.rect(band,'url(#zone)','#5b7795',.014,'stroke-dasharray=".07 .04"');S.add('</g>');
  S.label((band[0]+band[2])/2,band[3]-.10,'split wardrobe in principle; size and loft held',.075,'#466c92');
  // curtain pockets (lighting geometry; pocket sizes assumed); the W03 pocket is HELD (H-MBR-W03)
  const cw=L.design_inputs.calc_geometry.curtains,pw=cw.pocket_widths_m[0];
  const pocketRect=w=>{const a=w.along0_ft*FT,b=w.along1_ft*FT,wall=w.wall_ft*FT,e=wall+w.into_room_sign*pw;
    return w.axis==='x'?[Math.min(wall,e),a,Math.max(wall,e),b]:[a,Math.min(wall,e),b,Math.max(wall,e)];};
  let pockets=0;
  for(const [id,w] of Object.entries(cw.windows)){
    S.add(`<g data-curtain-pocket="${esc(id)}">`);S.rect(pocketRect(w),'#e9dff0','#7c658c',.012,'stroke-dasharray=".04 .03"');S.add('</g>');pockets++;
  }
  const w03=cw.pending_windows['MBR-rear'];assert(w03,'master must carry the held W03 curtain pocket');
  S.add('<g data-curtain-pocket="MBR-rear" data-hold="H-MBR-W03">');S.rect(pocketRect(w03),'#f3e6e6','#b02f2f',.016,'stroke-dasharray=".07 .04"');S.add('</g>');pockets++;
  // walls drawn over the fills
  drawWalls(S,D,{swings:false,tags:false});
  // lit paths
  const counts={paths:0,points:0},byRoom={},byType={};
  for(const f of fixtures){
    assert(LANE_COLOR[f.lane],`No RCP lane colour for ${f.lane}`);
    byRoom[f.room]=(byRoom[f.room]||0)+1;byType[f.type]=(byType[f.type]||0)+1;
    const inactive=f.room==='CBR'&&!/^CBR-(H[1-6]|L1|X[1-4])$/.test(f.id),allowance=HOLD_FIX['H-POOJA-GEOMETRY'].includes(f.id),ghost=inactive||allowance;
    S.add(`<g data-fixture-id="${esc(f.id)}" data-fixture-type="${esc(f.type)}" data-fixture-room="${esc(f.room)}" data-lane="${esc(f.lane)}"${inactive?' data-inactive="placeholder"':''}${allowance?' data-held-allowance="count-load-only"':''}>`);
    if(f.path_ft){
      const st=pathStyle(f.type,f.lane);
      S.path(`M${f.path_ft.map(p=>fx(p[0]*FT,4)+' '+fx(p[1]*FT,4)).join('L')}`,'none',st.c,st.w,`${st.dash?`stroke-dasharray="${st.dash}" `:''}stroke-linecap="round" stroke-linejoin="round"${ghost?' opacity=".45"':''}`);
      counts.paths++;
    }else{
      S.add(symbol(f.type,f.x_ft*FT,f.z_ft*FT,f.lane,{ghost}));counts.points++;
    }
    S.add('</g>');
  }
  const stripRooms={'CURT-LIV':'living','CURT-DIN':'dining','CURT-MBR-S':'master','CURT-CBR':'children'};
  for(const s of strips){
    const room=D.rooms.find(r=>r.id===stripRooms[s.id]);assert(room,`Unknown curtain strip ${s.id}`);
    const clip='clip-'+s.id;
    S.add(`<defs><clipPath id="${clip}" clipPathUnits="userSpaceOnUse"><path d="${polyPath(room.poly)}"/></clipPath></defs>`);
    S.add(`<g data-curtain-strip="${esc(s.id)}" data-circuit="X-${esc(s.id)}" data-control="${esc(s.target_knob_group)}">`);
    S.path(`M${s.polyline_ft.map(p=>fx(p[0]*FT,4)+' '+fx(p[1]*FT,4)).join('L')}`,'none','#d08a22',.03,`stroke-dasharray=".04 .025" clip-path="url(#${clip})"`);S.add('</g>');
  }
  // fittings held by the lighting hold list get a dashed red outline and a short tag
  const fixById=Object.fromEntries(fixtures.map(f=>[f.id,f]));
  const RCH='#b02f2f';let holdMarks=0;
  for(const [hold,ids] of Object.entries(HOLD_FIX)){
    for(const id of ids){
      const f=fixById[id];assert(f,`hold ${hold}: fixture ${id} is not in the master lighting section`);
      const pts=f.path_ft?f.path_ft.map(p=>[p[0]*FT,p[1]*FT]):[[f.x_ft*FT,f.z_ft*FT]],pad=.14;
      const xs=pts.map(p=>p[0]),zs=pts.map(p=>p[1]);
      const bx=[Math.min(...xs)-pad,Math.min(...zs)-pad,Math.max(...xs)+pad,Math.max(...zs)+pad];
      S.add(`<g data-hold-mark="${hold}" data-hold-fixture="${esc(id)}">`);
      S.rect(bx,'none',RCH,.016,'stroke-dasharray=".07 .04"');
      S.label(bx[2]+.02,bx[1]+.07,HOLD_TAG[hold],.07,RCH,'start','font-weight="700"');
      S.add('</g>');holdMarks++;
    }
  }
  const fans=fansDraw(S,D);
  // held areas: master bed/W03, children's room
  const mr=D.ML.frame.room_rect_m,RC='#b02f2f';
  S.rect(mr,'none',RC,.03,'stroke-dasharray=".25 .08 .05 .08"');
  S.label((mr[0]+mr[2])/2,mr[3]-.28,'MASTER \u2014 HELD (H-MBR-BED, H-MBR-W03)',.11,RC);
  S.label((mr[0]+mr[2])/2,mr[3]-.15,'bed position is a test centreline only (tenant bed not supplied); W03 pocket held',.075,RC);
  const ch=D.rooms.find(r=>r.id==='children'),cx=(ch.rect[0]+ch.rect[2])/2;
  S.label(cx,ch.rect[1]+.25,"CHILDREN'S \u2014 H1-H6, COVE, LINE MODELLED ON",.09,RC);
  S.label(cx,ch.rect[1]+.38,'cove/LINE install, fan and pockets held, unmeasured (H-CBR-*)',.07,RC);
  // pooja niche PN1: its lighting is LIV-P1 (back strip) and LIV-P2 (pin spot)
  const pn=D.openings.find(o=>o.id==='pooja-niche'),pwl=D.walls.find(w=>w.id===pn.wall),pnx=Math.max(pwl.rect[0],pwl.rect[2]);
  S.add('<g data-pooja-light="PN1">');
  S.label(pnx+.10,pn.span[1]+.20,'PN1: LIV-P1 / P2 are allowances only; placement held (PG)',.06,'#4d3a5c','start','font-weight="700"');
  S.add('</g>');
  // room labels with ceiling levels
  const pos={living:[2.3,11.5],dining:[2.8,7.45],kitchen:[2.65,3.5],master:[6.9,4.1],children:[7.75,12.95],utility:[2.2,.62],balcony:[1.9,15.2],dressing:[5.6,5.9],lobby:[5.55,7.68],bath1:[7.55,6.35],bath2:[7.55,8.15]};
  const lev={living:'band 2.96 \u00b7 panel unmeasured',dining:'band 2.96 \u00b7 panel unmeasured',kitchen:'flat 2.96',master:'band 2.96 \u00b7 panel unmeasured',children:CE.CBR?.level_basis?`band ${CE.CBR.band_h_m.toFixed(3)} \u00b7 centre ~${CE.CBR.tray_h_m.toFixed(2)} (reported, unsurveyed)`:'band 2.96 \u00b7 panel unmeasured',utility:'2.95 (not provided)',balcony:'no ceiling recorded',dressing:'band 2.96',lobby:'2.70 (not provided)',bath1:'2.40 (not provided)',bath2:'2.40 (not provided)'};
  const nm={living:'LIVING',dining:'DINING',kitchen:'KITCHEN',master:'MASTER',children:"CHILDREN'S",utility:'UTILITY + WASH',balcony:'ENTRY / BALCONY',dressing:'DRESSING',lobby:'LOBBY',bath1:'TL1',bath2:'TL2'};
  for(const id of Object.keys(pos)){
    const r=D.rooms.find(r=>r.id===id),[x,z]=pos[id],small=['dressing','lobby','bath1','bath2'].includes(id);
    S.add(`<g data-room-label="${id}">`);
    S.label(x,z,`${id==='utility'?'R08':r.code} ${nm[id]}`.trim(),small?.085:.13,'#203b43','middle','font-weight="600"');
    S.label(x,z+(small?.11:.16),lev[id],small?.07:.09,'#5d7174');
    S.add('</g>');
  }
  S.label(beam[0]+.12,(beam[1]+beam[3])/2-.02,'HALL CROSS-BEAM',.075,'#7a5a24','start');
  S.label(beam[0]+.12,(beam[1]+beam[3])/2+.1,'soffit unmeasured (H-HALL-BEAM)',.065,'#7a5a24','start');
  S.add('</g>');
  compassEdgeLabels(S,D);

  // right column
  const X0=1200;let y=170;
  y=S.wrap(X0,y+4,lightingNote,440,13,18,'red');y+=10;
  S.text(X0,y+20,'CEILING LEVELS (HD-11, unmeasured)',17,'sect');y+=34;
  const lv=[['band','2.96 m perimeter band (derived, unmeasured)'],['tray','Raised centre: gypsum/POP panel; level unmeasured (HD-14)'],['flat','Kitchen: one flat ceiling at 2.96 m (band level)'],['beam','Hall cross-beam band \u2014 soffit unmeasured'],['bath','2.40 m bath ceiling (not provided)'],['lobby','2.70 m lobby (not provided; placeholder)'],['utility','2.95 m utility soffit (not provided)'],['loft','Loft / overhead area (dashed)'],['curtain','Curtain pocket, 2 tracks (size indicative)'],['hold','Held curtain pocket W03 (H-MBR-W03)'],['groove','Black-painted false-track groove']];
  for(const [k,t] of lv){
    y+=24;
    const fill={band:LEVEL_FILL.band,tray:'#fbf4de',flat:LEVEL_FILL.flat,beam:'url(#beam)',bath:LEVEL_FILL.bath,lobby:LEVEL_FILL.lobby,utility:LEVEL_FILL.utility,loft:'url(#loft)',curtain:'#e9dff0',hold:'#f3e6e6',groove:'#111'}[k];
    S.add(`<rect x="${X0}" y="${y-15}" width="34" height="16" fill="${fill}" stroke="${k==='groove'?'#111':k==='hold'?'#b02f2f':'#8a97a0'}"${k==='loft'||k==='hold'?' stroke-dasharray="6 3"':''}/>`);
    S.text(X0+48,y-2,t,14);
  }
  y+=34;S.text(X0,y,'FIXTURE SYMBOLS (enlarged)',17,'sect');y+=8;
  const meaning={DL:'recessed COB downlight',DLA:'adjustable (gimbal) downlight',DLV:'24 V downlight',PIN6V:'micro-gimbal pin-spot',BSPOT:'IP-rated bath spot (BSPOT8V)',BDIF:'bath diffuser (BDIF9V)',FACE:'lobby mirror bar (wall mounted)',FACEV:'vertical mirror side bar (wall)',PEND:'dining pendant',TRK6:'48 V track head',TRKLIN:'track linear',READ:'wall reading spot',STEP:'PIR step light',UPDNV:'up/down wall light',CYLSV:'surface cylinder',BULKD:'IP65 bulkhead'};
  const symRows=[['DL8','DL*',meaning.DL],['DL8A','DL*A',meaning.DLA],['DL8V','DL*V',meaning.DLV],['PIN6V','PIN6V',meaning.PIN6V],['BSPOT8V','BSPOT*V',meaning.BSPOT],['BDIF9V','BDIF*V',meaning.BDIF],['FACE10V','FACE10V',meaning.FACE],['FACEV','FACEV',meaning.FACEV],['PEND','PEND',meaning.PEND],['TRK6','TRK6',meaning.TRK6],['TRKLIN','TRKLIN',meaning.TRKLIN],['READ','READ',meaning.READ],['STEP','STEP',meaning.STEP],['UPDNV','UPDNV',meaning.UPDNV],['CYLSV','CYLSV',meaning.CYLSV],['BULKD','BULKD',meaning.BULKD]];
  for(const [t,codeName,txt] of symRows){
    y+=26;
    S.add(`<g transform="translate(${X0+20} ${y-6}) scale(120)">${symbol(t,0,0,'NEUTRAL')}</g>`);
    S.text(X0+48,y-2,`${codeName}  ${txt}`,14);
  }
  y+=10;
  const lineRows=[['COVE_TW','COVE','cove strip (COVE_TW / bath BCOVE)','8 4'],['LIN','LINE','lit LINE profile (LIN)',''],['BACK','MOOD','diffused back-light (BACK)','3 4'],['TASK','TASK','strip: task / niche / vanity / plinth','6 3']];
  for(const [,lane,txt,dash] of lineRows){
    y+=26;
    S.add(`<path d="M${X0} ${y-6}H${X0+34}" stroke="${LANE_COLOR[lane]}" stroke-width="${lane==='LINE'?5:4}" ${dash?`stroke-dasharray="${dash}"`:''} fill="none"/>`);
    S.text(X0+48,y-2,txt,14);
  }
  y+=26;S.add(`<circle cx="${X0+17}" cy="${y-6}" r="13" fill="#fff" stroke="#4f6b73" stroke-width="2"/><path d="M${X0+8} ${y-15}L${X0+26} ${y+3}M${X0+26} ${y-15}L${X0+8} ${y+3}" stroke="#4f6b73" stroke-width="2"/>`);S.text(X0+48,y-2,'Fan point (symbol, not to scale)',14);
  y+=26;S.add(`<g opacity=".45"><circle cx="${X0+17}" cy="${y-6}" r="9" fill="#fff" stroke="#3d6fa5" stroke-width="2"/></g>`);S.text(X0+48,y-2,'Faded = held CBR fittings; H1-H6 active for review',14);
  y+=26;S.add(`<rect x="${X0+3}" y="${y-17}" width="28" height="18" fill="none" stroke="#b02f2f" stroke-width="2" stroke-dasharray="6 3"/>`);S.text(X0+48,y-2,'Held fitting: CR product-fit/access check,',14);y+=17;S.text(X0+48,y-2,'HB hall beam, DS dressing sweep,',14);y+=17;S.text(X0+48,y-2,'PG pooja count/load allowance only',14);
  y+=30;
  S.text(X0,y,'Colour = lane recorded in the master:',13,'muted');
  let lx=X0;y+=22;
  for(const lane of ['HIGH','COVE','MOOD','LINE','ACCENT','TASK','READ','NIGHT','MIRROR','FACE','PERIM','STUDY']){
    const w=lane.length*8.4+26;
    if(lx+w>X0+450){lx=X0;y+=20;}
    S.add(`<rect x="${lx}" y="${y-11}" width="12" height="12" fill="${LANE_COLOR[lane]}"/>`);
    S.text(lx+17,y,lane,12.5,'mono');lx+=w;
  }
  y+=42;
  S.text(X0,y,'FITTINGS PER ROOM',17,'sect');y+=6;
  const order=['LIV','DIN','KIT','MBR','DRS','CBR','TL1','TL2','LOB','UTL','BAL'];
  for(const r of order){
    const types={};for(const f of fixtures.filter(f=>f.room===r))types[f.type]=(types[f.type]||0)+1;
    y+=22;S.text(X0,y,`${FIX_ROOM[r]}: ${byRoom[r]}`,14,'mono',undefined);
    y=S.wrap(X0+16,y+17,Object.entries(types).map(([t,n])=>`${t}\u00d7${n}`).join('  '),420,12.5,16,'muted mono');y-=6;
  }
  y+=26;S.text(X0,y,`TOTAL ${fixtures.length} fittings`,15,'mono');
  y+=30;
  const notes=[
    lightingNote,
    HEIGHT_NOTE,COMPASS_NOTE,COMPASS_SOURCE,
    CENTRE_NOTE+' H-HALL-BEAM \u2014 beam soffit unmeasured for DIN-H2/H3 and FW-T1. Band void is 228.6 mm gross (~216 mm net).',
    'MASTER: bed position is a held test centreline (H-MBR-BED); the tenant bed is not supplied. The W03 curtain pocket is held (H-MBR-W03: pocket and loft interface unresolved; offsets unmeasured).',
    CURTAIN_NOTE,
    'S1 MODEL CLASH: assumed MBR-S and CBR strip returns each extend about 0.30 m beyond a modeled room corner. Lines are clipped for display only. Measure pocket ends and coordinate site fit; do not extend or cut from the model.',
    `CHILDREN\u2019S ROOM: CBR-H1 to H6 and the curtain strip are selected for review. The cove is retained; the outward-shifted LINE paths and cove remain held and unlit. The fan is shown at the unmeasured proposed cove centre. Verify fan sweep, clearances, wiring and ceiling details (H-CBR-*).`,
    'Dining + living share one raised centre panel. The kitchen ceiling is one flat level at band height. Black-painted grooves are drawn only where the master records them (master and children\u2019s rooms).',
    POOJA_NOTE+' LIV-P1 / LIV-P2 are count/load allowances only; inherited positions are held (H-POOJA-GEOMETRY).',
    'Fan points and lofts are assumed; curtain-pocket sizes are indicative only (HD-14). Switch-plate zones are not drawn: the master holds none (only the R05 latch-side strip appears on the children\u2019s elevation).'
  ];
  for(const n of notes){y=S.wrap(X0,y+14,n,440,13,18,'muted');y+=2;}
  y+=24;S.text(X0,y,'CONDITIONAL DETAILS (schematic, not to scale)',17,'sect');y+=14;
  // (a) raised centre section
  S.add(`<g transform="translate(${X0} ${y})" fill="none">
<rect x="0" y="0" width="120" height="14" fill="#d9dde0" stroke="#5d6e77"/>
<text x="134" y="11" font-size="12.5" fill="#203b43">concrete slab (underside derived)</text>
<rect x="15" y="14" width="90" height="40" fill="none" stroke="#8a97a0" stroke-dasharray="6 3"/>
<text x="134" y="36" font-size="12.5" fill="#203b43">profile + wiring space to be provided;</text>
<text x="134" y="50" font-size="12.5" fill="#203b43">clear depth unmeasured</text>
<rect x="15" y="54" width="90" height="8" fill="#fbf4de" stroke="#7a6fa8"/>
<text x="134" y="68" font-size="12.5" fill="#203b43">separate gypsum/POP panel</text>
<text x="134" y="82" font-size="12.5" fill="#203b43">(panel level unmeasured)</text>
<path d="M60 62V92" stroke="#b02f2f" stroke-width="2" stroke-dasharray="5 3"/>
<circle cx="60" cy="96" r="6" fill="#fff" stroke="#b02f2f" stroke-width="2"/>
<text x="134" y="98" font-size="12.5" fill="#203b43">fitting: product fit, access and driver</text>
<text x="134" y="112" font-size="12.5" fill="#203b43">location to be checked (conditional)</text>
</g>`);
  y=S.wrap(X0,y+132,'(a) Raised centre, schematic section. Not a slab chase: no cutting or chasing is authorised.',440,12.5,16,'red');y+=14;
  // (b) curtain pocket plan
  S.add(`<g transform="translate(${X0} ${y})" fill="none">
<rect x="0" y="0" width="120" height="46" fill="#e9dff0" stroke="#7c658c" stroke-dasharray="3 2"/>
<path d="M8 16H112" stroke="#5d6e77" stroke-width="2.5"/><path d="M8 32H112" stroke="#5d6e77" stroke-width="2.5" stroke-dasharray="8 3"/>
<text x="134" y="19" font-size="12.5" fill="#203b43">track 1: sheer</text>
<text x="134" y="35" font-size="12.5" fill="#203b43">track 2: blackout</text>
</g>`);
  y=S.wrap(X0,y+66,'(b) Curtain pocket, schematic plan (LIV, MBR, CBR). Clear width, depth and track spacing are unverified (HD-14).',440,12.5,16,'red');
  y+=6;
  northArrow(S,X0+60,y+70,40);
  S.text(X0+120,y+62,'Approx. north points to sheet-bottom.',14,'muted');
  y+=130;
  const bottom=Math.max(y,TY+15.85*SC+90);
  pageFooter(S,bottom+50,D.hash);
  void H;void W;
  const svg=S.finish(bottom+50);
  return {id:'02-rcp',title:'Reflected ceiling plan (bottoms-up)',svg,
    counts:{fixtures:fixtures.length,circuits:circuitIds.length,selectedCurtainStrips:strips.length,reviewFixtures:fixtures.length+strips.length,reviewCircuits:circuitIds.length+strips.length,paths:counts.paths,points:counts.points,fans,curtainPockets:pockets,grooves,holdMarks,rooms:D.rooms.length,walls:D.walls.length},
    drawn:{fixtureTypes:byType,fixtureRooms:byRoom,fixtureIds:fixtures.map(f=>f.id),circuitIds,curtainStrips:strips.map(s=>s.id)}};
}
