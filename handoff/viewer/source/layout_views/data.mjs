import fs from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {createPlan,FT} from '../src/master-adapter.js';

export {FT};
export const DEFAULT_SHA='6746203bddc22f318d679a15f913b4688eb87d9c75ecb310fbb3f26264c62d3d';
export const MATTRESS_MM={queen:[1524,1981],king:[1829,1981]};
export const m=a=>a.map(n=>n*FT);
export const DIR_NAME={S:'south',W:'west',N:'north',E:'east'};
export const DIR_ORDER=['N','E','S','W'];

export const OPENING_INFO={
  'kitchen-window':{code:'W01',name:'Kitchen exterior window'},
  'dining-window':{code:'W07',name:'Dining side window'},
  'living-window':{code:'W06',name:'Living side window'},
  'utility-open':{code:'UP1',name:'Utility parapet opening (assumed, OI-UTL-01)',assumed:true},
  'pooja-niche':{code:'PN1',name:'Pooja niche, recessed (built; HD-16 / HD-18 estimates)'},
  'kitchen-utility-window':{code:'W02',name:'Kitchen-to-utility window'},
  'utility-door':{code:'D06',name:'Kitchen-utility double-leaf door'},
  'master-top-window':{code:'W03',name:'Master window'},
  'master-window':{code:'W04',name:'Master side window'},
  'master-door':{code:'D02',name:'Master bedroom door'},
  'children-door':{code:'D03',name:"Children's bedroom door"},
  'children-window':{code:'W05',name:"Children's side window",placeholder:true},
  'entrance':{code:'D01',name:'Main entrance door'},
  'entry-glass-left':{code:'G01',name:'Entry side panel'},
  'entry-glass-right':{code:'G02',name:'Entry side panel'},
  'bath1-door':{code:'D04',name:'TL1 door'},
  'bath1-vent':{code:'V01',name:'TL1 vent / window'},
  'bath1-niche':{code:'SN1',name:'TL1 shower niche'},
  'bath2-door':{code:'D05',name:'TL2 door'},
  'bath2-vent':{code:'V02',name:'TL2 vent / window'},
  'bath2-niche':{code:'SN2',name:'TL2 shower niche'}
};
export const ROOM_NAME={living:'Living',dining:'Dining',kitchen:'Kitchen',master:'Master bedroom',dressing:'Master dressing',children:"Children's bedroom",bath1:'TL1 attached toilet',bath2:'TL2 common toilet',utility:'Utility + washing',washing:'Washing',balcony:'Entry / balcony',lobby:'Common lobby'};

export const near=(a,b,t=.02)=>Math.abs(a-b)<=t;
export const inPoly=(p,poly)=>{
  let c=false;
  for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const [xi,zi]=poly[i],[xj,zj]=poly[j];
    if((zi>p[1])!==(zj>p[1])&&p[0]<(xj-xi)*(p[1]-zi)/(zj-zi)+xi)c=!c;
  }
  return c;
};
export function roomPoly(r){
  const [x0,z0,x1,z1]=r.rect,c=r.cutout;
  if(!c)return [[x0,z0],[x1,z0],[x1,z1],[x0,z1]];
  const [cx0,cz0,cx1,cz1]=c;
  if(near(cx1,x1)&&near(cz1,z1))return [[x0,z0],[x1,z0],[x1,cz0],[cx0,cz0],[cx0,z1],[x0,z1]];
  if(near(cx0,x0)&&near(cz1,z1))return [[x0,z0],[x1,z0],[x1,z1],[cx1,z1],[cx1,cz0],[x0,cz0]];
  throw new Error(`Unsupported cutout geometry in room ${r.id}`);
}
export function roomEdges(r){
  const poly=roomPoly(r);
  const edges=poly.map((p,i)=>{
    const q=poly[(i+1)%poly.length],dx=q[0]-p[0],dz=q[1]-p[1];
    let dir,horizontal;
    if(Math.abs(dz)<1e-9){dir=dx>0?'S':'N';horizontal=true;}
    else if(Math.abs(dx)<1e-9){dir=dz>0?'W':'E';horizontal=false;}
    else throw new Error(`Non-orthogonal edge in ${r.id}`);
    const lineAt=horizontal?p[1]:p[0],lo=horizontal?Math.min(p[0],q[0]):Math.min(p[1],q[1]),hi=horizontal?Math.max(p[0],q[0]):Math.max(p[1],q[1]);
    // interior direction along the normal axis
    const s={S:1,N:-1,W:-1,E:1}[dir];
    return {a:p,b:q,dir,horizontal,line:lineAt,lo,hi,len:hi-lo,s};
  });
  const seen={};
  for(const e of [...edges].sort((p,q)=>q.len-p.len)){
    seen[e.dir]=(seen[e.dir]||0)+1;
    e.suffix=seen[e.dir]>1?' (lift corner)':'';
  }
  return edges;
}
export const uOf=(e,t)=>e.dir==='S'||e.dir==='W'?t-e.lo:e.hi-t;
export const uRange=(e,t0,t1)=>{const a=uOf(e,t0),b=uOf(e,t1);return [Math.min(a,b),Math.max(a,b)];};

export function prepare(source,expected=DEFAULT_SHA){
  const bytes=fs.readFileSync(source);
  const hash=createHash('sha256').update(bytes).digest('hex');
  assert.equal(hash,expected,`Master SHA ${hash} does not match the expected ${expected}; refusing to draw from an unverified master.`);
  const house=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
  const P=createPlan({house,master_sha256:hash,master_filename:source,preview:true},{includeLighting:false});
  const V=house.visualization_geometry,A=house.architecture;
  const RC=house.decisions.r05_clearance;
  assert.equal(RC.decision,'HD-15');
  assert.equal(RC.geometry_changed,false);
  assert(Number.isFinite(RC.estimated_clearance_mm)&&RC.estimated_clearance_mm>0);
  const r05ClearanceNote=`R05 SITE-CHECK PINCH (HD-15): approximately ${RC.estimated_clearance_mm} mm at the bed-foot/study-return, not a comfortable walking route. Keep room and furniture positions unchanged. Measure the tenant bed frame, fixed return and unobstructed route on site (OI-R05-03).`;

  // compass: read from the master, never hard-coded; the drawing code assumes the confirmed south-up mapping and fails loudly otherwise
  const O=V.orientation;
  assert(O&&O.evidence_status==='homeowner_confirmed','Master has no homeowner-confirmed orientation.');
  assert.deepEqual(O.sheet_to_compass,{'+z_sheet_down':'north','-z_sheet_top':'south','+x_sheet_right':'west','-x_sheet_left':'east'},'Unexpected sheet_to_compass mapping');
  assert.deepEqual(O.true_north_vector_xz,[0,1],'North arrow must point to sheet-bottom');
  const compassChecks=[
    ['master_layout.relations.wardrobe_wall',V.master_layout.relations.wardrobe_wall.compass_wall,'south'],
    ['master_layout.relations.headboard_wall',V.master_layout.relations.headboard_wall.compass_wall,'west'],
    ['master_layout.relations.tv_door_wall',V.master_layout.relations.tv_door_wall.compass_wall,'east'],
    ['master_layout.relations.dressing_wall',V.master_layout.relations.dressing_wall.compass_wall,'north']
  ];
  for(const [k,got,want] of compassChecks)assert.equal(got,want,`${k} compass_wall`);

  // retired original layout: this generator never reads the original plan; the master records the exclusion
  assert.equal(house.decisions.retired_original_layout.status,'retired_by_homeowner_do_not_consult');
  // HD-14 warning batch: bedside cabinets omitted, two-layer concealed curtains, raised centre = separate gypsum/POP panel (dimensions unmeasured)
  const WR=house.decisions.warning_resolution;
  assert.equal(WR.decision,'HD-14');assert.equal(WR.construction_release,false);
  assert.deepEqual(WR.answers.bedside_joinery.excluded_item_ids,['ST-R04-NS01','ST-R04-NS02','ST-R05-NS01']);
  for(const id of WR.answers.bedside_joinery.excluded_item_ids){
    const a=house.storage.item_applicability[id];
    assert(a&&a.status==='omitted_by_homeowner'&&a.render_footprint===false,`${id} must be omitted by the homeowner (HD-14)`);
  }
  assert.equal(WR.answers.curtains.track_count,2);assert.deepEqual(WR.answers.curtains.layers,['sheer','blackout']);assert.deepEqual(WR.answers.curtains.rooms,['LIV','MBR','CBR']);
  assert.equal(WR.answers.centre_panel.clear_cavity_depth_m,null);assert.equal(WR.answers.centre_panel.actual_panel_level_m,null);assert.equal(WR.answers.centre_panel.structural_cutting_authorized,false);
  assert.match(WR.answers.centre_panel.construction,/gypsum\/POP panel below the concrete slab/);
  // vertical datum HD-11: read decisions.ceiling_heights / visualization_geometry.provisional_heights, never architecture.heights or lighting.design_inputs
  const HD=house.decisions.ceiling_heights,PV=V.provisional_heights;
  assert.equal(HD.status,'homeowner_stated_figures_unmeasured_on_site');
  assert.equal(HD.construction_release,false);
  assert.equal(HD.stated_by_homeowner.floor_to_floor_m,3.3528);assert.equal(HD.stated_by_homeowner.band_drop_m,.2286);
  assert.equal(HD.homeowner_accepted_assumptions.slab_thickness_m,.127);assert.equal(HD.homeowner_accepted_assumptions.floor_finish_m,.0381);
  const DL=HD.derived_levels_m;
  assert.equal(PV.floorToFloor.value,HD.stated_by_homeowner.floor_to_floor_m);
  assert.equal(PV.soffit.value,DL.slab_underside_soffit);assert.equal(PV.band.value,DL.perimeter_band_underside);assert.equal(PV.coffer.value,DL.raised_centre_panel);
  assert.deepEqual(HD.superseded_assumptions_m,{floorToFloor:3.2,soffit:3.08,band:2.7,coffer:2.88,kitchen_flat:2.88});
  // not-provided placeholders stay visible: bathrooms 2.40 (provisional_heights.toilet), utility (architecture placeholder), lobby/balcony none
  assert.match(PV.toilet.status,/not provided/);assert.equal(PV.toilet.value,2.4);
  const H={ftf:HD.stated_by_homeowner.floor_to_floor_m,drop:HD.stated_by_homeowner.band_drop_m,slabT:HD.homeowner_accepted_assumptions.slab_thickness_m,finish:HD.homeowner_accepted_assumptions.floor_finish_m,
    slab:DL.slab_underside_soffit,band:DL.perimeter_band_underside,panel:DL.raised_centre_panel,kitchenFlat:DL.kitchen_flat_ceiling,
    bath:PV.toilet.value,utility:A.heights.utility_soffit.value_m};
  assert.equal(H.utility,2.95,'utility placeholder changed; recheck the not-provided flag');
  // lobby placeholder (not provided in HD-11): the master records it only in the lighting layout_basis placeholder table
  const LOBPH=house.lighting.design_inputs.provenance.layout_basis.height_basis.placeholders_not_provided_m;
  assert.equal(LOBPH.LOB,2.7,'lobby placeholder changed; recheck the not-provided flag');H.lobby=LOBPH.LOB;
  // children's curtain top: the legacy 2.64 m is superseded; 2.939 m is an ASSUMED HD-11 drawing top, not measured hardware
  const HFA=house.lighting.calculation_validity.height_field_applicability.children_curtain;
  assert.equal(HFA.superseded_value_m,2.64);assert.equal(HFA.proposed_value_m,2.939);
  assert.equal(house.lighting.design_inputs.provenance.layout_basis.height_basis.derived_assumptions.curtain_top_m,2.939);
  H.curtainTopAssumed=HFA.proposed_value_m;
  // sills / heads / cove etc.: assumed values only (HD-11 keys excluded)
  const PH={},HD_KEYS=new Set(['floorToFloor','soffit','band','coffer']);
  for(const [k,v] of Object.entries(PV)){if(HD_KEYS.has(k))continue;assert.equal(v.src,'assumed',`provisional_heights.${k} must be assumed`);PH[k]=v.value;}
  for(const k of ['windowSill','kitchenSill','ventSill','door','mainDoor','windowHead','bathWindowHead','cove','parapet'])assert.equal(typeof PH[k],'number',`PH.${k}`);
  // pooja: already built (homeowner-confirmed); reinforcement is homeowner-reported only
  const PN=house.decisions.pooja_niche;
  assert.match(PN.built_status,/^Already built/);assert.equal(PN.existing_construction.reported_built,true);
  assert.equal(PN.existing_construction.evidence_status,'homeowner_report_not_independent_structural_verification');
  assert.equal(PN.existing_construction.new_cutting_requested,false);assert.equal(PN.construction_release,false);
  assert.equal(PN.dimensions.status,'homeowner_estimates_unverified_not_site_measurements');
  assert.equal(PN.existing_construction.outside_wall_extension.reported,true);
  assert.equal(PN.existing_construction.outside_wall_extension.measured_geometry,null);
  assert.equal(PN.geometry_hold.new_or_deeper_cutting_authorized,false);
  assert.equal(V.pooja.display_arrangement?.choice,'Small idols with a framed picture behind');
  assert.equal(V.pooja.display_arrangement.construction_release,false);
  assert.match(V.pooja.rendering_hold,/conceptual placeholders only/);

  // rooms (assembled geometry in metres, nominal sizes kept for labels)
  const rooms=P.rooms.map(r=>({
    id:r.id,code:r.architectural_room_id||'',name:ROOM_NAME[r.id]||r.name,
    rect:m(r.assemblyRect||r.rect),cutout:(r.assemblyCutout||r.cutout)?m(r.assemblyCutout||r.cutout):null,
    nominal:r.dimension?.text||null,exterior:!!r.exterior,ceilingKey:r.ceiling
  }));
  const wash=rooms.find(r=>r.id==='washing'),util=rooms.find(r=>r.id==='utility');
  const elevRooms=rooms.filter(r=>!['washing','utility'].includes(r.id));
  elevRooms.push({id:'utility',code:'R08 / R08a',name:'Utility + washing',nominal:util.nominal,exterior:false,cutout:null,
    rect:[Math.min(wash.rect[0],util.rect[0]),Math.min(wash.rect[1],util.rect[1]),Math.max(wash.rect[2],util.rect[2]),Math.max(wash.rect[3],util.rect[3])]});
  const elevOrder=['living','dining','kitchen','master','dressing','children','bath1','bath2','utility','balcony','lobby'];
  elevRooms.sort((a,b)=>elevOrder.indexOf(a.id)-elevOrder.indexOf(b.id));
  assert.equal(elevRooms.length,elevOrder.length);
  for(const r of elevRooms)r.poly=roomPoly(r);
  for(const r of rooms)r.poly=roomPoly(r);

  const walls=P.walls.map(w=>({id:w.id,rect:m(w.rect)}));

  const openings=P.openings.map(o=>{
    const info=OPENING_INFO[o.id];assert(info,`No label mapping for opening ${o.id}`);
    return {
      id:o.id,code:info.code,name:info.name,kind:o.kind,wall:o.wall,src:o.src,axis:o.axis,span:[o.span[0]*FT,o.span[1]*FT],
      sill:o.kind==='door'?0:(o.sillValue??PH[o.sill||'windowSill']),head:o.headValue??(o.main?PH.mainDoor:PH.door),
      double:!!o.double,openSide:o.openSide??1,hingeEnd:o.hingeEnd,jambM:o.jambM,main:!!o.main,
      placeholder:!!info.placeholder,assumedOpening:!!info.assumed,
      statusNote:/^homeowner_confirmed_roughly_centred/.test(o.position_status||'')?'centred (homeowner-confirmed); offsets unmeasured'
        :info.placeholder?'placeholder opening (concealed behind curtain)':null,
      curtain:o.curtainSpan?(assert.equal(o.curtainTopM,HFA.superseded_value_m,`${o.id}: legacy curtain top changed`),{span:m(o.curtainSpan),bottom:o.curtainBottomM,top:H.curtainTopAssumed}):null
    };
  });
  assert.equal(openings.length,21);

  // storage: global bounds, R05 local-to-global transform checked, superseded R04 records suppressed
  const C=V.children_layout,frame=C.frame,ML=V.master_layout;
  const residuals=[];
  const boundsOf=i=>{
    if(i.room_id!=='R05'||!i.bounds_uv_m)return i.bounds_m;
    const [u,v,U,W]=i.bounds_uv_m,to=(u,v)=>[frame.origin_xz_m[0]+u*frame.u_axis_xz[0]+v*frame.v_axis_xz[0],frame.origin_xz_m[1]+u*frame.u_axis_xz[1]+v*frame.v_axis_xz[1]];
    const a=to(u,v),b=to(U,W),r=[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[0],b[0]),Math.max(a[1],b[1])];
    const residual=Math.max(...r.map((n,k)=>Math.abs(n-i.bounds_m[k])));
    assert(residual<=.001,`${i.id}: global/local storage transform differs by ${residual} m`);
    residuals.push({id:i.id,max_rounding_residual_m:residual});return r;
  };
  const suppressedIds=new Set(ML.superseded_storage_ids);
  for(const id of suppressedIds){const hit=house.storage.items.find(i=>i.id===id);assert(hit,`unknown suppressed ${id}`);assert.equal(hit.room_id,'R04');}
  const storageAll=house.storage.items;
  const storage=storageAll.filter(i=>!suppressedIds.has(i.id)).map(i=>({...i,drawBounds:boundsOf(i)}));
  assert.equal(storageAll.length,18);assert.equal(suppressedIds.size,5);assert.equal(storage.length,13);

  // item list for elevations (plan-only items are flagged)
  const items=[];
  const addItem=o=>items.push({h:null,plan:false,...o});
  const EF=V.essential_furniture;
  for(const f of EF){
    switch(f.kind){
      case 'sofa':addItem({id:'FURN-sofa',kind:'sofa',label:'Sofa (L-shape)',rect:f.rect,src:f.src});addItem({id:'FURN-sofa-return',kind:'sofa',label:'Sofa return',rect:f.return,src:f.src});break;
      case 'coffee':addItem({id:'FURN-coffee',kind:'coffee',label:'Coffee table',rect:f.rect,plan:true,src:f.src});break;
      case 'tvunit':addItem({id:'FURN-tv',kind:'tv',label:'TV unit',rect:[f.wallX-f.depthM,f.z-f.widthM/2,f.wallX,f.z+f.widthM/2],src:f.src});break;
      case 'dining':addItem({id:'FURN-dining-table',kind:'dining',label:'Dining table',rect:f.rect,plan:true,src:f.src});break;
      case 'kitchen':
        addItem({id:'FURN-kitchen-left',kind:'counter',label:'Base cabinets + worktop',rect:f.left,h:[0,.9],hNote:'worktop plane 0.90 m (lighting calc input)',src:f.src});
        addItem({id:'FURN-kitchen-top',kind:'counter',label:'Base cabinets + worktop',rect:f.top,h:[0,.9],hNote:'worktop plane 0.90 m (lighting calc input)',src:f.src});
        addItem({id:'FURN-kitchen-fridge',kind:'fridge',label:'Fridge / tall unit zone',rect:f.fridge,src:f.src});
        addItem({id:'FURN-kitchen-bar',kind:'bar',label:'Breakfast counter',rect:f.bar,h:[0,f.barH],topThk:f.topThk,hNote:`counter height ${f.barH} m`,src:f.src});
        break;
      case 'vanity':
        if(f.rect[1]<2)addItem({id:'FURN-wash-basin',kind:'basin',label:'Utility wash basin',rect:f.rect,src:f.src});
        else addItem({id:'FURN-lobby-vanity',kind:'basin',label:'Lobby shared vanity',rect:f.rect,src:f.src});
        break;
      case 'washer':addItem({id:'FURN-washer',kind:'washer',label:'Washing machine',rect:f.rect,src:f.src});break;
      case 'utilityShelf':addItem({id:'FURN-utility-counter',kind:'counter',label:'Utility counter',rect:f.counter,h:[0,f.counterH],hNote:`counter height ${f.counterH} m`,src:f.src});break;
      case 'rug':addItem({id:'FURN-rug',kind:'rug',label:'Rug',rect:f.rect,plan:true,src:f.src});break;
      case 'plant':{
        const at=f.at;assert(Array.isArray(at)&&typeof f.height==='number','plant needs at[] and height');
        addItem({id:`FURN-plant-${items.filter(i=>i.kind==='plant').length+1}`,kind:'plant',label:f.fig?'Fig plant':'Balcony planter',rect:[at[0]-.2,at[1]-.2,at[0]+.2,at[1]+.2],h:[0,f.height],point:at,src:f.src});
        break;
      }
      default:throw new Error(`Unhandled essential furniture kind ${f.kind}`);
    }
  }
  // kitchen wall cabinets: lighting-occlusion boxes (bottom from the lighting calc; top is not in the master)
  const KW=house.lighting.design_inputs.calc_geometry.kitchen_worktop;
  KW.cabinets_occlusion_ft.forEach((b,i)=>addItem({id:`FURN-kitchen-wallcab-${i+1}`,kind:'wallcab',label:'Wall cabinets (lighting-occlusion box)',rect:[b[0]*FT,b[2]*FT,b[1]*FT,b[3]*FT],h:[KW.cabinet_bottom_m,null],hNote:`bottom ${KW.cabinet_bottom_m} m, top not in master`,src:'assumed'}));
  // tenants bring their own beds (decisions.bedrooms): beds are dashed mattress envelopes, bedside units are not drawn as joinery
  const BD=house.decisions.bedrooms;
  assert.equal(BD.bed_type,'tenant_supplied');assert.equal(BD.beds_in_joinery_scope,false);
  assert.deepEqual(BD.planning_envelope.mattress_sizes_mm.queen,MATTRESS_MM.queen);assert.deepEqual(BD.planning_envelope.mattress_sizes_mm.king,MATTRESS_MM.king);
  const notDrawn=[],tenantBeds=[];
  const envelope=(room,headX,axisZ)=>{
    const L=MATTRESS_MM.king[1]/1000,wk=MATTRESS_MM.king[0]/1000,wq=MATTRESS_MM.queen[0]/1000;
    return {room,king:[headX-L,axisZ-wk/2,headX,axisZ+wk/2],queen:[headX-L,axisZ-wq/2,headX,axisZ+wq/2],axisZ};
  };
  for(const s of storage){
    if(['bedside_unit','bedside_floating_shelf'].includes(s.kind)){notDrawn.push({id:s.id,reason:'fixed bedside cabinet omitted by the homeowner (HD-14); tenants may use movable tables'});continue;}
    if(s.kind==='queen_storage_bed'){
      const b=s.drawBounds,env=envelope(s.room_id,b[2],(b[1]+b[3])/2);
      tenantBeds.push({...env,id:`TENANT-BED-${s.room_id}`,fromStorage:s.id});
      continue;
    }
    const selection=s.homeowner_selection;
    addItem({id:s.id,kind:s.kind,label:s.kind.replaceAll('_',' '),rect:s.drawBounds,h:s.height_range_m,storage:s,src:'master storage',
      ...(selection?{hNote:`homeowner-selected conditional; unmeasured, not construction-ready: ${selection.condition}`}:{})});
  }
  {
    const band=ML.relationship_zones_m.wardrobe_wall_band.rect,w04=ML.openings.W04.span_m;
    tenantBeds.push({...envelope('R04',ML.frame.room_rect_m[2],(band[3]+w04[0])/2),id:'TENANT-BED-R04',fromStorage:null});
  }
  for(const t of tenantBeds)addItem({id:t.id,kind:'tenant-bed',label:"Tenant's bed (queen to king envelope)",rect:t.king,queenRect:t.queen,bed:t,src:'decisions.bedrooms'});
  const baths=P.bathrooms.rooms;
  for(const b of baths){
    const t=b.lighting_room_id;
    addItem({id:`BATH-${t}-VANITY`,kind:'bath-vanity',label:`${t} vanity`,rect:b.vanity.rect_m,h:b.vanity.height_range_m,bath:b,dirs:['S'],src:'master bathrooms'});
    const wr=[Math.min(b.wc.cistern_rect_m[0],b.wc.bowl_rect_m[0]),Math.min(b.wc.cistern_rect_m[1],b.wc.bowl_rect_m[1]),Math.max(b.wc.cistern_rect_m[2],b.wc.bowl_rect_m[2]),Math.max(b.wc.cistern_rect_m[3],b.wc.bowl_rect_m[3])];
    addItem({id:`BATH-${t}-WC`,kind:'bath-wc',label:`${t} WC`,rect:wr,h:[0,b.wc.cistern_height_m],bath:b,dirs:['S'],src:'master bathrooms'});
    addItem({id:`BATH-${t}-SHOWER`,kind:'bath-shower',label:`${t} shower`,rect:b.shower.rect_m,h:[0,b.shower.screen_height_m],bath:b,dirs:['S','W'],src:'master bathrooms'});
  }

  const fans=V.fans,curtains=house.lighting.design_inputs.calc_geometry.curtains;
  const pooja=P.pooja;
  const D={source,hash,size:bytes.length,house,P,V,A,H,HD,WR,RC,r05ClearanceNote,PV,PH,PN,O,compassChecks,rooms,elevRooms,walls,openings,storage,suppressedIds:[...suppressedIds],storageAll,items,notDrawn,tenantBeds,baths,fans,curtains,pooja,ML,C,residuals,stairs:V.stairs,plot:P.plot};
  D.panels=buildPanels(D);
  return D;
}

// ---------------------------------------------------------------- elevation panels
function matchWalls(D,e,reach){
  const out=[];
  for(const w of D.walls){
    const [x0,z0,x1,z1]=w.rect;
    const wHoriz=(x1-x0)>(z1-z0);
    if(wHoriz!==e.horizontal)continue;
    const [t0,t1]=e.horizontal?[x0,x1]:[z0,z1],[n0,n1]=e.horizontal?[z0,z1]:[x0,x1];
    const ov=Math.min(e.hi,t1)-Math.max(e.lo,t0);
    if(ov<=.05)continue;
    const nearFace=e.s>0?n1:n0,centre=(n0+n1)/2;
    const outer=e.s>0?centre<e.line+.1:centre>e.line-.1;
    if(outer&&Math.abs(nearFace-e.line)<=.2+reach)out.push({id:w.id,t0:Math.max(e.lo,t0),t1:Math.min(e.hi,t1),thick:n1-n0});
  }
  return out;
}
function itemOnEdge(item,e,room,D){
  if(item.plan)return null;
  if(item.dirs&&!item.dirs.includes(e.dir))return null;
  const [x0,z0,x1,z1]=item.rect;
  const [t0,t1]=e.horizontal?[x0,x1]:[z0,z1],[n0,n1]=e.horizontal?[z0,z1]:[x0,x1];
  const ov=Math.min(e.hi,t1)-Math.max(e.lo,t0);
  if(ov<=.05)return null;
  const centre=[(x0+x1)/2,(z0+z1)/2];
  const inside=inPoly(centre,room.poly);
  if(inside){
    const gap=e.s>0?n0-e.line:e.line-n1;
    if(gap>=-.03&&gap<=.2)return {ov,outside:false,depth:n1-n0};
    return null;
  }
  const dist=e.s>0?Math.abs(n1-e.line):Math.abs(n0-e.line);
  if(dist<=.03)return {ov,outside:true,depth:n1-n0};
  return null;
}
export function buildPanels(D){
  const panels=[];
  for(const room of D.elevRooms){
    const edges=roomEdges(room);
    for(const e of edges){
      const adj=[];
      for(const it of D.items){const hit=itemOnEdge(it,e,room,D);if(hit)adj.push({it,hit});}
      // a thin item standing just outside the room line (lobby vanity) may reach a wall record behind it; large outside runs may not
      const reach=Math.max(0,...adj.filter(a=>a.hit.outside&&a.hit.depth<=.6).map(a=>a.hit.depth));
      const wallMatches=matchWalls(D,e,reach);
      // covered intervals with a corner-join allowance, then gaps
      const ext=wallMatches.map(w=>[Math.max(e.lo,w.t0-.12),Math.min(e.hi,w.t1+.12)]).sort((a,b)=>a[0]-b[0]);
      const gaps=[];let cur=e.lo;
      for(const [a,b] of ext){if(a-cur>.08)gaps.push([cur,a]);cur=Math.max(cur,b);}
      if(e.hi-cur>.08)gaps.push([cur,e.hi]);
      const covered=wallMatches.reduce((s,w)=>s+(w.t1-w.t0),0);
      const gapInfo=gaps.map(([a,b])=>{
        const mid=(a+b)/2,probe=e.horizontal?[mid,e.line-e.s*.3]:[e.line-e.s*.3,mid];
        const other=D.rooms.find(r=>r.id!==room.id&&inPoly(probe,r.poly)&&!(room.id==='utility'&&['washing','utility'].includes(r.id)));
        const [u0,u1]=uRange(e,a,b);
        return {u0,u1,openTo:other?other.name:null};
      });
      const walls=wallMatches.map(w=>{const [u0,u1]=uRange(e,w.t0,w.t1);return {id:w.id,u0,u1};});
      const openings=[];
      for(const o of D.openings){
        if(!wallMatches.some(w=>w.id===o.wall))continue;
        const w=D.walls.find(w=>w.id===o.wall),wHoriz=(w.rect[2]-w.rect[0])>(w.rect[3]-w.rect[1]);
        if((o.axis==='x')!==wHoriz)continue;
        const a=Math.max(o.span[0],e.lo),b=Math.min(o.span[1],e.hi);
        if(b-a<=.02)continue;
        const [u0,u1]=uRange(e,a,b);
        openings.push({...o,u0,u1,clippedMin:o.span[0]<e.lo-.01,clippedMax:o.span[1]>e.hi+.01,fullU:uRange(e,o.span[0],o.span[1])});
      }
      const itemsOn=adj.map(({it,hit})=>{
        const a=Math.max(it.rect[e.horizontal?0:1],e.lo),b=Math.min(it.rect[e.horizontal?2:3],e.hi);
        const [u0,u1]=uRange(e,a,b);
        return {...it,u0,u1,outside:hit.outside,depth:hit.depth};
      }).sort((p,q)=>p.u0-q.u0);
      const coverage=covered/e.len;
      const keep=coverage>=.15||itemsOn.length>0||openings.length>0;
      panels.push({id:`${room.id}-${e.dir.toLowerCase()}${e.suffix?'-lift':''}`,roomId:room.id,roomCode:room.code,roomName:room.name,dir:e.dir,suffix:e.suffix,edge:e,
        title:`${room.name} \u2013 ${DIR_NAME[e.dir]} wall${e.suffix}`,L:e.len,walls,gaps:gapInfo,coverage,openings,items:itemsOn,keep,open:!keep});
    }
  }
  return panels;
}
