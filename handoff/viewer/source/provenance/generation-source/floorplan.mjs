import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {createPlan,roomFloorRegions,FT} from './src/master-adapter.js';
import {drawingSource} from './drawing-source.mjs';

const [source,output,mode]=process.argv.slice(2);
assert(!mode||mode==='--staging'||mode==='--review-draft','Only --staging or --review-draft is supported after the output folder.');
if(!source||!output)throw new Error('Usage: node floorplan.mjs <house-design.json> <output folder>');
const bytes=fs.readFileSync(source),hash=createHash('sha256').update(bytes).digest('hex'),house=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
const drawing=drawingSource(house,source,{staging:mode==='--staging',reviewDraft:mode==='--review-draft',outDir:output});
const P=createPlan({house,master_sha256:hash,master_filename:source,preview:true},{includeLighting:false});
const V=house.visualization_geometry,C=V.children_layout,frame=C.frame,items=house.storage.items;
assert(items.length,'The current storage proposal must be integrated before drawing this decision plan.');
assert(V.nominal_room_bindings,'Canonical nominal bindings are required.');
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const fixed=(n,d=3)=>Number(n).toFixed(d),metres=a=>a.map(n=>n*FT);
const children=P.rooms.find(r=>r.id==='children'),cRect=metres(children.rect);
const mappingResiduals=[];
const bounds=i=>{
  if(i.room_id!=='R05'||!i.bounds_uv_m)return i.bounds_m;
  const [u,v,U,W]=i.bounds_uv_m,to=(u,v)=>[frame.origin_xz_m[0]+u*frame.u_axis_xz[0]+v*frame.v_axis_xz[0],frame.origin_xz_m[1]+u*frame.u_axis_xz[1]+v*frame.v_axis_xz[1]];
  const a=to(u,v),b=to(U,W),r=[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[0],b[0]),Math.max(a[1],b[1])];
  const residual=Math.max(...r.map((n,k)=>Math.abs(n-i.bounds_m[k])));
  assert(residual<=.001,`${i.id}: global/local storage transform differs by ${residual} m`);
  mappingResiduals.push({id:i.id,max_rounding_residual_m:residual});return r;
};
const ML=V.master_layout||null,applic=house.storage.item_applicability||{};
const suppressed=new Set([...(ML?.superseded_storage_ids||[]),...Object.entries(applic).filter(([,a])=>a.render_footprint===false&&!/dashed optional/.test(a.render_as||'')).map(([id])=>id)]);
const optionalOutline=new Set(Object.entries(applic).filter(([,a])=>/dashed optional/.test(a.render_as||'')).map(([id])=>id));
const WR=house.decisions.warning_resolution;
assert.equal(WR.decision,'HD-14');assert.equal(WR.construction_release,false);
const RC=house.decisions.r05_clearance;
assert.equal(RC.decision,'HD-15');assert.equal(RC.geometry_changed,false);
const hd14Omitted=new Set(WR.answers.bedside_joinery.excluded_item_ids);
assert.deepEqual([...hd14Omitted].sort(),['ST-R04-NS01','ST-R04-NS02','ST-R05-NS01']);
assert.equal(WR.answers.curtains.track_count,2);assert.deepEqual(WR.answers.curtains.layers,['sheer','blackout']);
for(const id of hd14Omitted){assert(suppressed.has(id),`${id}: omitted bedside must not be drawn (HD-14)`);assert(!optionalOutline.has(id),`${id}: no optional outline (HD-14)`);}
for(const id of suppressed){
  const hit=items.find(i=>i.id===id);
  assert(hit,`master_layout suppresses unknown storage record ${id}`);
  assert(hit.room_id==='R04'||hd14Omitted.has(id),`${id}: only R04 records or HD-14 omitted bedsides may be suppressed`);
}
const storage=items.filter(i=>!suppressed.has(i.id)).map(i=>({...i,drawBounds:bounds(i)}));
const childBed=storage.find(i=>i.id==='ST-R05-BED01').drawBounds;
const desk=storage.find(i=>i.id==='ST-R05-DK01').drawBounds;
const pinch=Math.hypot(childBed[0]-desk[2],desk[1]-childBed[3]);
assert.equal(storage.filter(i=>i.id==='ST-R05-LF01').length,1,'R05 requires one canonical loft assembly');
const PJ0=V.pooja,poojaFace0=metres(P.walls.find(w=>w.id===PJ0.wall).rect)[2];
assert.equal(PJ0.style,'recessed_niche');assert.equal(PJ0.location_src,'homeowner_estimated_offset_from_unsurveyed_model_corner');
const PB=house.decisions.pooja_niche;
assert(/^Already built/.test(PB.built_status),'decisions.pooja_niche.built_status must record the niche as already built');
assert.equal(PB.existing_construction.new_cutting_requested,false);
assert.equal(PB.existing_construction.evidence_status,'homeowner_report_not_independent_structural_verification');
assert.equal(PB.existing_construction.outside_wall_extension.reported,true);
assert.equal(PB.existing_construction.outside_wall_extension.measured_geometry,null);
assert.match(PJ0.rendering_hold,/conceptual placeholders only/);
const short={living:'LIVING',dining:'DINING',kitchen:'KITCHEN',master:'MASTER',children:'CHILDREN',bath1:'TL1 / ATTACHED',bath2:'TL2 / COMMON',utility:'UTILITY + WASH',balcony:'ENTRY / BALCONY',dressing:'DRESS',lobby:'LOBBY',washing:'WASH'};
const svg=[];
const add=s=>svg.push(s);
add(`<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="__PAGE_H__" viewBox="0 0 1800 __PAGE_H__" role="img" aria-labelledby="title description">
<title id="title">Current working floor plan - Hyderabad 2BHK</title>
<desc id="description">Master-derived decision drawing. Confirmed nominal dimensions are distinguished from proposed layouts, carried-forward shell interfaces and unresolved measurement scope. No construction release.</desc>
<metadata>${esc(JSON.stringify({source,master_sha256:hash,construction_release:false,storage_status:house.storage.status}))}</metadata>
<defs><pattern id="hold" width=".10" height=".10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width=".10" height=".10" fill="#fbf0d7"/><path d="M0 0V.10" stroke="#cf9a43" stroke-width=".023"/></pattern>
<pattern id="structure" width=".12" height=".12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width=".12" height=".12" fill="#edf0f0"/><path d="M0 0V.12" stroke="#c5cdcf" stroke-width=".012"/></pattern>
<pattern id="zone" width=".09" height=".09" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><rect width=".09" height=".09" fill="#eaf0f7"/><path d="M0 0V.09" stroke="#a9bdd6" stroke-width=".012"/></pattern>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#466c92"/></marker>
<clipPath id="children-wall-clip"><rect x="${cRect[0]-.13}" y="${cRect[1]-.12}" width="${cRect[2]-cRect[0]+.37}" height="${cRect[3]-cRect[1]+.36}"/></clipPath></defs>
<style>text{font-family:"Segoe UI",Arial,sans-serif;fill:#203b43} .mono{font-family:Consolas,monospace}.muted{fill:#63777a}.confirmed{fill:#266c5c}.proposed{fill:#466c92}.hold{fill:#9b641c}.dim{font-family:Consolas,monospace;fill:#266c5c}.small{font-size:15px}.note{font-size:17px}.section{font-size:18px;font-weight:650;letter-spacing:1px}</style>
<rect width="1800" height="__PAGE_H__" fill="#fcfdfc"/>`);
function text(x,y,value,size=17,cls='',anchor='start'){
  add(`<text x="${x}" y="${y}" font-size="${size}" class="${cls}" text-anchor="${anchor}">${esc(value)}</text>`);
}
function wrap(x,y,value,width,size=17,leading=24,cls=''){
  const words=value.split(/\s+/);let line='',n=0;
  for(const word of words){
    if((line.length+word.length+1)*size*.51>width&&line){text(x,y+n*leading,line,size,cls);n++;line=word;}else line+=(line?' ':'')+word;
  }
  if(line)text(x,y+n++*leading,line,size,cls);
  return y+n*leading;
}
text(68,62,'Current working floor plan',36);
text(70,102,drawing.staging?'STAGING - NOT FINAL / awaiting integrated master hash / not a construction release':`${drawing.review_draft?'REVIEW DRAFT / ':''}Hyderabad 2BHK / decision drawing / not an as-built or construction release`,19,'muted');
text(1730,57,'SINGLE SOURCE',15,'muted','end');
text(1730,83,'house-design.json',18,'mono','end');
text(1730,110,hash.slice(0,24)+'...',14,'mono muted','end');
add('<path d="M70 140H1730" stroke="#c8d2d3"/>');
text(80,183,'HOUSE / CURRENT COORDINATED ASSEMBLY',18,'section');
text(915,183,'R05 / RENDER-LED CHILDREN\'S ROOM',18,'section');
text(915,207,'Pages 16-18 relationships; metric placement proposed',16,'muted');

function rect(r,fill,stroke='#819594',sw=.014,extra=''){
  add(`<rect x="${r[0]}" y="${r[1]}" width="${r[2]-r[0]}" height="${r[3]-r[1]}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`);
}
function line(a,b,color='#71878a',sw=.015,extra=''){
  add(`<path d="M${a[0]} ${a[1]}L${b[0]} ${b[1]}" fill="none" stroke="${color}" stroke-width="${sw}" ${extra}/>`);
}
function label(x,z,value,size=.18,color='#203b43',anchor='middle'){
  add(`<text x="${x}" y="${z}" font-size="${size}" fill="${color}" text-anchor="${anchor}">${esc(value)}</text>`);
}
function poojaRecess(w,o){
  const [,,X]=metres(w.rect),a=o.span[0]*FT,b=o.span[1]*FT,tx=X+.10;
  add(`<g id="pooja-niche" data-pooja-niche="HD-16" data-niche-representation="front-outline-only" data-size-status="${esc(V.pooja.size_src)}">`);
  line([X,a],[X,b],'#d3b8e5',.06,'stroke-dasharray=".08 .04"');
  line([X-.05,a],[X+.05,a],'#5b4668',.025);
  line([X-.05,b],[X+.05,b],'#5b4668',.025);
  const t=(dy,size,txt,bold)=>add(`<text x="${tx}" y="${a+dy}" font-size="${size}" fill="#4d3a5c"${bold?' font-weight="700"':''}>${esc(txt)}</text>`);
  t(.13,.15,'POOJA NICHE',true);t(.25,.09,'built; front only (HD-16)',true);
  t(.37,.085,'size / offset estimated');t(.49,.08,'extension unmeasured');t(.60,.08,'OI-POOJA-01 / no section drawn');
  add('</g>');
}
function wallDrawing(filter=()=>true){
  for(const w of P.walls.filter(filter))rect(metres(w.rect),'#42545a','#42545a',.003);
  for(const o of P.openings){
    const w=P.walls.find(w=>w.id===o.wall);if(!w||!filter(w))continue;
    const [x,z,X,Z]=metres(w.rect),ax=o.axis==='x',a=o.span[0]*FT,b=o.span[1]*FT,cross=ax?(z+Z)/2:(x+X)/2;
    if(o.id==='pooja-niche'){poojaRecess(w,o);continue;}
    if(o.kind.includes('niche')){
      line(ax?[a,cross]:[cross,a],ax?[b,cross]:[cross,b],'#786385',.07,'stroke-dasharray=".05 .03"');continue;
    }
    rect(ax?[a,z-.003,b,Z+.003]:[x-.003,a,X+.003,b],'#fcfdfc','none',0);
    if(o.kind!=='door'){
      line(ax?[a,cross]:[cross,a],ax?[b,cross]:[cross,b],'#31818d',.045,o.kind==='vent'?'stroke-dasharray=".06 .03"':'');continue;
    }
    const n=o.double?2:1,span=(b-a)/n,jamb=o.jambM??.025;
    for(let k=0;k<n;k++){
      const max=k===1||o.hingeEnd==='max',sign=max?-1:1,hinge=max?b-jamb:a+jamb,r=span-2*jamb,side=o.openSide??1;
      const h=ax?[hinge,cross]:[cross,hinge],closed=ax?[hinge+sign*r,cross]:[cross,hinge+sign*r],open=ax?[hinge,cross+side*r]:[cross+side*r,hinge];
      line(h,open,'#405f7e',.022);line(h,closed,'#8095aa',.009,'stroke-dasharray=".04 .03"');
      const start=Math.atan2(closed[1]-h[1],closed[0]-h[0]),end=Math.atan2(open[1]-h[1],open[0]-h[0]);
      let turn=end-start;if(turn>Math.PI)turn-=2*Math.PI;if(turn<-Math.PI)turn+=2*Math.PI;
      const points=Array.from({length:21},(_,i)=>[h[0]+r*Math.cos(start+turn*i/20),h[1]+r*Math.sin(start+turn*i/20)]);
      add(`<path d="${points.map((p,i)=>(i?'L':'M')+p.join(' ')).join('')}" fill="none" stroke="#8095aa" stroke-width=".009"/>`);
    }
  }
}
const MATTRESS={queen:[1.524,1.981],king:[1.829,1.981]};
function tenantBed(room,headX,axisZ,detail=false){
  const [wq,L]=MATTRESS.queen,[wk]=MATTRESS.king,k=detail?1.35:1;
  add(`<g data-bed-envelope="${room}" data-storage-kind="tenant-bed">`);
  rect([headX-L,axisZ-wk/2,headX,axisZ+wk/2],'none','#5a7a84',.016,'stroke-dasharray=".07 .04"');
  rect([headX-L,axisZ-wq/2,headX,axisZ+wq/2],'#eef3f3','#5a7a84',.01,'rx=".03"');
  label(headX-L/2,axisZ-.19*k,"TENANT'S BED",.12*k,'#3f5f68');
  label(headX-L/2,axisZ-.19*k+.14*k,'queen to king',.095*k,'#466c92');
  label(headX-L/2,axisZ-.19*k+.27*k,'mattress envelope',.095*k,'#466c92');
  label(headX-L/2,axisZ-.19*k+.40*k,'1524-1829 x 1981 mm',.09*k,'#466c92');
  if(detail)label(headX-L/2,axisZ-.19*k+.53*k,'no frame / gap implied',.085*k,'#9b641c');
  add('</g>');
}
function storageDrawing(list,detail=false){
  for(const s of list.filter(s=>!s.kind.includes('loft')&&!s.kind.includes('overhead'))){
    const r=s.drawBounds,[x,z,X,Z]=r,w=X-x,d=Z-z;
    if(optionalOutline.has(s.id)){
      add(`<g data-storage-id="${esc(s.id)}" data-storage-kind="${esc(s.kind)}">`);rect(r,'none','#6b7d97',.012,'stroke-dasharray=".05 .04"');
      if(detail)label((x+X)/2,(z+Z)/2+.04,`${s.id.split('-').at(-1)} optional`,.085,'#466c92');
      add('</g>');continue;
    }
    add(`<g data-storage-id="${esc(s.id)}" data-storage-kind="${esc(s.kind)}">`);
    if(s.kind==='queen_storage_bed'){
      assert(applic[s.id]?.status==='tenant_supplied_planning_envelope',`${s.id}: bed must be a tenant planning envelope`);
      tenantBed(s.room_id,X,(z+Z)/2,detail);
    }else{
      rect(r,s.kind.includes('wardrobe')?'#dce4ef':'#e9edf0','#5b7795',.014);
      if(s.leaves){
        const longX=w>d;
        for(let i=1;i<s.leaves;i++)line(longX?[x+w*i/s.leaves,z]:[x,z+d*i/s.leaves],longX?[x+w*i/s.leaves,Z]:[X,z+d*i/s.leaves],'#90a3b9',.008);
      }
      if(detail||s.kind.includes('wardrobe'))label((x+X)/2,(z+Z)/2+.055,s.id.split('-').at(-1),detail?.14:.115,'#466c92');
    }
    add('</g>');
  }
  for(const s of list.filter(s=>s.kind.includes('loft')||s.kind.includes('overhead'))){
    add(`<g data-storage-id="${esc(s.id)}" data-storage-kind="${esc(s.kind)}">`);rect(s.drawBounds,'none','#526d9a',.022,'stroke-dasharray=".07 .04"');
    if(detail&&s.kind.includes('loft'))label((s.drawBounds[0]+s.drawBounds[2])/2,s.drawBounds[1]+.20,'CONTINUOUS LOFT / ABOVE DOOR + WARDROBE',.115,'#466c92');
    add('</g>');
  }
}
function essentials(){
  for(const f of V.essential_furniture){
    if(f.kind==='plant'||f.kind==='rug')continue;
    if(f.kind==='kitchen'){
      for(const key of ['left','top','fridge','bar'])rect(f[key],key==='bar'?'#dbe6dd':'#e8e7df','#8e998e',.014);
      for(const x of [f.bar[0]+.48,f.bar[2]-.48])add(`<circle cx="${x}" cy="${f.bar[3]-.18}" r=".14" fill="#fff" stroke="#8e998e" stroke-width=".012"/>`);
      label((f.bar[0]+f.bar[2])/2,f.bar[1]+.22,'1800 x 600 BAR',.13);
    }else if(f.kind==='tvunit')rect([f.wallX-f.depthM,f.z-f.widthM/2,f.wallX,f.z+f.widthM/2],'#ccd8df','#82949d');
    else if(f.rect){
      rect(f.rect,'#e8e7df','#8e998e',.014,f.kind==='coffee'?'rx=".08"':'');
      if(f.return)rect(f.return,'#e8e7df','#8e998e',.014);
      if(f.kind==='dining'){
        const [x,z,X,Z]=f.rect;
        for(const v of [.25,.75])for(const yy of [z-.23,Z+.03])rect([x+v*(X-x)-.18,yy,x+v*(X-x)+.18,yy+.20],'#f4f3ef','#a1aaa1',.01);
        for(const xx of [x-.23,X+.03])rect([xx,(z+Z)/2-.18,xx+.20,(z+Z)/2+.18],'#f4f3ef','#a1aaa1',.01);
      }
    }else if(f.counter)rect(f.counter,'#e8e7df','#8e998e');
  }
}
function bathrooms(){
  for(const b of P.bathrooms.rooms){
    const s=b.shower,[x,z,X,Z]=s.rect_m;
    rect(s.rect_m,'#eef5f3','none',0);
    line([x,z],[X,z],'#6b9f99',.065);line([X,z],[X,Z],'#6b9f99',.065);
    line(...s.screen_segment_m,'#77a4b0',.025);
    rect(b.vanity.rect_m,'#dbe5e7','#66878d');
    const vr=b.vanity.rect_m;add(`<ellipse cx="${(vr[0]+vr[2])/2}" cy="${(vr[1]+vr[3])/2}" rx=".20" ry=".13" fill="#fff" stroke="#779199" stroke-width=".012"/>`);
    rect(b.wc.cistern_rect_m,'#eef0ee','#8e999b');rect(b.wc.bowl_rect_m,'#fff','#8e999b',.012,'rx=".16"');
    const id=b.renderer_room_id;
    label((b.placement.rect_m[0]+b.placement.rect_m[2])/2,b.placement.rect_m[3]-.23,short[id],.17);
  }
}
function curtain(){
  const c=C.curtain_and_window;
  line([c.curtain_plane_x_m,c.curtain_span_z_m[0]],[c.curtain_plane_x_m,c.curtain_span_z_m[1]],'#7c658c',.045,'stroke-dasharray=".06 .025"');
}
function dimension(a,b,caption,offset=.20,vertical=false){
  const p=vertical?[a[0]-offset,a[1]]:[a[0],a[1]-offset],q=vertical?[b[0]-offset,b[1]]:[b[0],b[1]-offset];
  line(a,p,'#467d70',.009);line(b,q,'#467d70',.009);line(p,q,'#467d70',.012);
  if(vertical)add(`<text transform="translate(${p[0]-.07} ${(p[1]+q[1])/2}) rotate(-90)" text-anchor="middle" font-size=".14" fill="#266c5c">${esc(caption)}</text>`);
  else label((p[0]+q[0])/2,p[1]-.06,caption,.14,'#266c5c');
}
function masterOverlay(){
  if(!ML)return;
  const Z=ML.relationship_zones_m,band=Z.wardrobe_wall_band.rect,bay=Z.window_bay.rect,room=ML.frame.room_rect_m;
  const w03=ML.openings.W03.proposed_span_m,w04=ML.openings.W04.span_m,axis=(band[3]+w04[0])/2;
  add(`<g id="master-relationship-overlay" data-decision-status="${esc(ML.decision_status)}" data-suppressed-storage="${esc([...suppressed].join(' '))}">`);
  rect(band,'url(#zone)','#5b7795',.012,'stroke-dasharray=".06 .035"');
  rect(bay,'#fcfdfc','#5b7795',.012,'stroke-dasharray=".06 .035"');
  for(const x of [(band[0]+bay[0])/2,(bay[2]+band[2])/2])label(x,band[1]+.30,'WARDROBE ZONE',.115,'#466c92');
  label((band[0]+band[2])/2,band[3]+.16,'loft over / sizes + shutters held',.095,'#466c92');
  label((bay[0]+bay[2])/2,band[1]+.25,'W03 BAY',.105,'#466c92');
  label((bay[0]+bay[2])/2,band[1]+.38,'centred; offsets',.075,'#9b641c');
  label((bay[0]+bay[2])/2,band[1]+.47,'unmeasured',.075,'#9b641c');
  line([w03[0]-.08,room[1]+.10],[w03[1]+.08,room[1]+.10],'#7c658c',.035,'stroke-dasharray=".06 .025"');
  line([room[2]-.10,w04[0]],[room[2]-.10,w04[1]],'#7c658c',.035,'stroke-dasharray=".06 .025"');
  tenantBed('R04',room[2],axis);
  label(room[2]-MATTRESS.queen[1]/2,axis+MATTRESS.king[0]/2+.15,'BED HEAD ON WEST WALL',.1,'#466c92');
  label(room[2]-MATTRESS.queen[1]/2,axis+MATTRESS.king[0]/2+.27,'indicative position only',.085,'#9b641c');
  line([room[0]+.05,axis-.45],[room[0]+.05,axis+.45],'#466c92',.05);
  label(room[0]+.17,axis+.04,'TV',.12,'#466c92','start');
  label(room[0]+.17,axis+.19,'opposite bed',.09,'#466c92','start');
  add('</g>');
  const U=P.openings.find(o=>o.id==='utility-open');
  if(U){const x=(U.span[0]*FT+2.09)/2;label(x,1.15,'PARAPET OPEN ON SOUTH WALL',.09,'#466c92');label(x,1.28,'no corner return',.085,'#466c92');}
}
add('<g id="house-plan" transform="translate(80 220) scale(70)">');
rect([0,0,P.plot.x*FT,P.plot.z*FT],'none','#b8c5c4',.012,'stroke-dasharray=".08 .06"');
for(const r of P.rooms)for(const p of roomFloorRegions(r))rect(metres(p.rect),p.role==='assembly-hold'?'url(#hold)':'#f6f8f6','none',0);
rect(C.return.rect_m,'url(#structure)','#a8b5b7',.012);
essentials();storageDrawing(storage);wallDrawing();bathrooms();curtain();masterOverlay();
const positions={living:[3.2,11.25],dining:[2.8,5.55],kitchen:[2.85,2.85],master:[6.75,3.8],children:[7.85,12.75],utility:[2.8,.85],balcony:[1.85,14.85],dressing:[5.76,6.45],lobby:[5.56,8.15]};
for(const [id,p] of Object.entries(positions)){
  const r=P.rooms.find(r=>r.id===id);label(...p,`${r.architectural_room_id||''} ${short[id]}`.trim(),id==='dressing'||id==='lobby'?.14:.19);
  if(r.dimension&&id!=='utility')label(p[0],p[1]+.25,r.dimension.text+(id==='balcony'?' / scope hold':''),.125,'#266c5c');
}
label(4.95,12.55,'LIFT',.17);label(4.95,12.80,'INTERFACE HOLD',.11,'#9b641c');
for(const key of ['upper','landing','lower']){
  const r=V.stairs[key];rect(r,'#f1f3f1','#839693',.014);
  if(key!=='landing')for(let i=1;i<8;i++)line([r[0]+(r[2]-r[0])*i/8,r[1]],[r[0]+(r[2]-r[0])*i/8,r[3]],'#a1adab',.009);
}
label(6.7,14.9,'STAIR / CARRY-FORWARD',.17);
add('</g>');
assert.deepEqual(V.orientation.sheet_to_compass,{'+z_sheet_down':'north','-z_sheet_top':'south','+x_sheet_right':'west','-x_sheet_left':'east'},'unexpected sheet-to-compass mapping');
assert.deepEqual(V.orientation.true_north_vector_xz,[0,1],'north arrow must point to sheet-bottom');
function northArrow(cx,cy,id){
  add(`<g id="${id}" data-north-arrow="sheet-bottom"><circle cx="${cx}" cy="${cy}" r="30" fill="#fcfdfc" stroke="#203b43" stroke-width="1.6"/><path d="M${cx} ${cy-24}V${cy+14}" stroke="#203b43" stroke-width="2.4"/><path d="M${cx} ${cy+26}L${cx-9} ${cy+4}L${cx} ${cy+9}L${cx+9} ${cy+4}Z" fill="#203b43"/></g>`);
  text(cx,cy-38,'APPROX. NORTH',12.5,'mono','middle');text(cx,cy+54,'N = sheet-bottom',12.5,'mono','middle');
}
function northArrowCompact(cx,cy,id){
  add(`<g id="${id}" data-north-arrow="sheet-bottom"><circle cx="${cx}" cy="${cy}" r="22" fill="#fcfdfc" stroke="#203b43" stroke-width="1.4"/><path d="M${cx} ${cy-17}V${cy+10}" stroke="#203b43" stroke-width="2.2"/><path d="M${cx} ${cy+19}L${cx-7} ${cy+3}L${cx} ${cy+7}L${cx+7} ${cy+3}Z" fill="#203b43"/></g>`);
  text(cx-32,cy-4,'APPROX. NORTH',12.5,'mono','end');text(cx-32,cy+12,'= sheet-bottom',12.5,'mono','end');
}
northArrow(830,300,'north-arrow-house');
text(410,212,'SOUTH  (utility / washing end, sheet-top)',14,'muted','middle');
add(`<text transform="translate(62 780) rotate(-90)" text-anchor="middle" font-size="14" class="muted">EAST  (kitchen / dining / living, sheet-left)</text>`);
add(`<text transform="translate(764 780) rotate(90)" text-anchor="middle" font-size="14" class="muted">WEST  (bedrooms, sheet-right)</text>`);
text(80,1372,'Scale bar (model metres)',14,'muted');
add('<path d="M80 1390H220M80 1384V1396M150 1384V1396M220 1384V1396" stroke="#203b43" stroke-width="2"/>');
text(80,1414,'0',13,'mono');text(150,1414,'1',13,'mono','middle');text(220,1414,'2 m',13,'mono','end');
wrap(300,1374,'Drawn south-up: approximate homeowner north, not a surveyed true bearing. Sheet-top = south, sheet-bottom = north, sheet-left = east, sheet-right = west. Doors/swings require site confirmation.',560,15,21,'muted');

add(`<g id="children-plan" transform="translate(960 270) scale(118) translate(${-cRect[0]} ${-cRect[1]})">`);
rect(cRect,'#f6f9f8','#799a94',.016);
rect(C.return.rect_m,'url(#structure)','#9cabad',.016);
storageDrawing(storage.filter(s=>s.room_id==='R05'),true);
add('<g clip-path="url(#children-wall-clip)">');
wallDrawing(w=>['children-north','living-east','lift-north','lift-east','front-children'].includes(w.id));
add('</g>');
const cw=P.openings.find(o=>o.id==='children-window'),[wa,wb]=cw.span.map(n=>n*FT);
line([cRect[2],wa],[cRect[2],wb],'#31818d',.045);curtain();
// Keep the return label inside the part of the hatch left visible by the lift-notch wall.
label(C.return.rect_m[0]+.25,C.return.rect_m[1]+.65,'RETURN',.115);
label(C.return.rect_m[0]+.25,C.return.rect_m[1]+.83,'900 x 1750',.085,'#466c92');
label(C.return.rect_m[0]+.25,C.return.rect_m[1]+1.0,'PROPOSED',.085,'#466c92');
dimension([cRect[0],cRect[1]],[cRect[2],cRect[1]],'v = 3.810 m / nominal',.20);
dimension([cRect[0],cRect[1]],[cRect[0],cRect[3]],'u = 4.572 m / nominal',.27,true);
line([cRect[0]+.35,cRect[1]+1.07],[cRect[0]+1.15,cRect[1]+1.07],'#466c92',.018);
label(cRect[0]+.75,cRect[1]+.97,'+v: east (TV) to west (bed head)',.1,'#466c92');
line([cRect[0]+.35,cRect[1]+1.07],[cRect[0]+.35,cRect[1]+1.65],'#466c92',.018);
label(cRect[0]+.45,cRect[1]+1.65,'+u: north',.115,'#466c92','start');
add('</g>');
northArrowCompact(1698,238,'north-arrow-children');
let ny=282;
const CR=C.compass_relations;
for(const paragraph of [
  'CONFIRMED NUMBERS: 3.810 x 4.572 m nominal; 15 ft side on the outer west wall (homeowner-confirmed). Axis allocation and global position are proposed.',
  `RELATIONS (compass): wardrobe ${CR.wardrobe_wall}; entry ${CR.entry}; headboard ${CR.headboard_wall}; TV ${CR.tv_wall}; study ${CR.study}; curtain ${CR.curtain}.`,
  'LOFT: one continuous assembly above entrance and wardrobe. Dashed outline is overhead, not a second cabinet slab.',
  'BED: tenant-supplied queen-to-king mattress envelope (1524-1829 x 1981 mm), not joinery. No frame or walking gap implied. Fixed bedside cabinets are omitted by the homeowner (HD-14); tenants may use movable tables. See OI-BED-01 / OI-R05-03.',
  'WET AREAS: basin left on entry. Feature tile only on the two shower walls. Close bath door before basin use.',
]){ny=wrap(1460,ny,paragraph,300,14.5,20)+16;}
text(915,850,'DIMENSION RECONCILIATION',18,'section');
text(915,878,'Local geometry may agree while the assembled shell remains unresolved.',15,'muted');
const cols=[915,1088,1265,1450,1610],header=['Room','Nominal m','Local model m','Shell delta mm','State'];
header.forEach((v,i)=>text(cols[i],913,v,15,'muted'));
add('<path d="M915 925H1730" stroke="#bdcdcc"/>');
const roomOrder=['living','dining','kitchen','master','children','bath1','bath2','utility','balcony'],measurements=[];
for(let k=0;k<roomOrder.length;k++){
  const r=P.rooms.find(r=>r.id===roomOrder[k]),ar=house.architecture.rooms.find(a=>a.id===r.architectural_room_id);
  const unresolved=P.nominalBindings.unresolved.find(b=>b.room_id===r.id),nom=ar.dimensions.map(d=>d.value_m);
  const local=unresolved?[(unresolved.assembly_rect_m[2]-unresolved.assembly_rect_m[0]),(unresolved.assembly_rect_m[3]-unresolved.assembly_rect_m[1])]:[(r.rect[2]-r.rect[0])*FT,(r.rect[3]-r.rect[1])*FT];
  const delta=r.assemblyDifferenceM,state=unresolved?'SCOPE HOLD':delta.some(v=>Math.abs(v)>.001)?'ASSEMBLY HOLD':'LOCAL MATCH';
  if(!unresolved)assert(local.every((v,i)=>Math.abs(v-nom[i])<1e-8),`${ar.id}: local geometry differs from canonical nominal size`);
  const vals=[ar.id+' '+short[r.id].split(' / ')[0],nom.map(v=>fixed(v)).join(' x '),local.map(v=>fixed(v)).join(' x '),delta.map(v=>(v>=0?'+':'')+fixed(v*1000,1)).join(' / '),state];
  const y=953+k*32;vals.forEach((v,i)=>text(cols[i],y,v,i===4?12.5:14.5,i===1?'mono confirmed':i===3||i===4?'mono hold':'mono'));
  measurements.push({room_id:ar.id,nominal_size_m:nom,local_model_size_m:local,assembly_delta_m:delta,state});
}
wrap(915,1270,'LOCAL MATCH means the proposed model binds to the confirmed nominal numbers. It does not confirm walls, returns, openings, materials or construction approval.',815,15,22,'muted');
const legend=[['#266c5c','Confirmed numerical dimension'],['#466c92','Proposed layout / storage'],['#9b641c','Unresolved assembly / scope'],['#526d9a','Dashed outline: overhead loft (held)'],['#5b4668','Pooja niche (built): estimated front only (HD-16); depth held']];
legend.forEach(([c,s],i)=>{add(`<rect x="${915+(i%2)*410}" y="${1330+Math.floor(i/2)*30}" width="16" height="10" fill="${c}"/>`);text(940+(i%2)*410,1340+Math.floor(i/2)*30,s,15);});
add('<path d="M70 1440H1730" stroke="#c8d2d3"/>');
let registerTop=1475;
if(ML){
  const U=V.openings.find(o=>o.id==='utility-open'),R=ML.relations,PJ=V.pooja,poojaFace=metres(P.walls.find(w=>w.id===PJ.wall).rect)[2];
  assert.equal(ML.openings.W03.position_status,'homeowner_confirmed_roughly_centred_offsets_unmeasured');
  assert.equal(PJ.compass_wall,'east');assert.equal(PJ.decision,'HD-16');
  text(70,1475,'R04 MASTER, UTILITY AND POOJA / LAYOUT CORRECTIONS',18,'section');
  const cap=s=>s[0].toUpperCase()+s.slice(1),edge=w=>({N:'sheet top',E:'sheet right',W:'sheet left',S:'sheet bottom'})[R[w].sheet_wall];
  const notes=[
    ['WALL ROLES (COMPASS)',`${cap(R.wardrobe_wall.compass_wall)} wall (${edge('wardrobe_wall')}): wardrobe | W03 bay | wardrobe, loft over. ${cap(R.headboard_wall.compass_wall)} wall (${edge('headboard_wall')}): headboard, with the W04 corner window at its north end. ${cap(R.tv_door_wall.compass_wall)} wall (${edge('tv_door_wall')}): TV opposite the bed and door D02 at its north end. ${cap(R.dressing_wall.compass_wall)} wall (${edge('dressing_wall')}): dressing passage at its east end. A wardrobe on the west wall is excluded by topology: the wall opposite holds the room entry. No room, wall or nominal size moved.`],
    ['OPENINGS / HOLDS',`D01 is single-leaf in this model, while the architecture description says double-leaf; confirm on site. W03 keeps its inherited ${fixed(ML.openings.W03.width_m*1000,0)} mm width, centred (homeowner-confirmed); offsets unmeasured. The split wardrobe is approved in principle, but the zones are illustrative and unmeasured; the five superseded R04 storage records are not drawn (OI-MBR-03). Beds are tenant-supplied: only the queen-to-king mattress envelope is shown, with no frame or walking gap implied (OI-BED-01); fixed bedside cabinets are omitted by the homeowner (HD-14: ST-R04-NS01, ST-R04-NS02, ST-R05-NS01; no optional outline). Concealed curtains in the living, master and children rooms need two tracks, sheer + blackout (HD-14); pocket sizes are unverified. The W03 curtain pocket and the master bed position are held for lighting (H-MBR-W03, H-MBR-BED).`],
    ['UTILITY',`One continuous east wall runs from the kitchen to the south corner; no return encloses the washing corner. The parapet opening reaches that wall face (${fixed(U.span[0])} to ${fixed(U.span[1])} m). Corner wall height to be site-checked (OI-UTL-02).`],
    ['POOJA NICHE (HD-16 / HD-18)',`Already built, flush with the east wall's room face as reported (x ${fixed(poojaFace,3)} m, estimated z ${fixed(PJ.z[0],3)} to ${fixed(PJ.z[1],3)} m). Front outline only. ${drawing.note} The homeowner reports a reinforced slab extension beyond the wall. Its geometry and capacity are unverified: no physical back or structural section is drawn. Confirm dimensions and balcony-edge relation on site (OI-POOJA-01). No cutting or deepening is authorised.`]];
  let bottom=0;
  notes.forEach(([heading,body],i)=>{const x=70+i*420;text(x,1508,heading,15,'proposed');bottom=Math.max(bottom,wrap(x,1532,body,385,14.5,20,'muted'));});
  add(`<path d="M70 ${bottom+6}H1730" stroke="#c8d2d3"/>`);
  registerTop=bottom+42;
}
text(70,registerTop,'DECISIONS & SITE CHECKS / SOURCE OPEN-ITEM REGISTER',18,'section');
text(1730,registerTop,'Quoted in full from the master. "sheet-N" and legacy wall IDs are drawing labels, not compass; compass names govern.',13.5,'muted','end');
const openItems=house.open_items.items;
const colCount=openItems.length>8?3:2,colW=colCount===3?560:840;
let rowY=registerTop+33,rowBottom=rowY;
const registerQuoted=[];
for(let k=0;k<openItems.length;k++){
  const item=openItems[k],col=k%colCount;
  if(col===0&&k){rowY=rowBottom+12;rowBottom=rowY;}
  const x=70+col*colW,y=rowY;
  const resolved=item.status==='resolved_in_proposed_geometry',open=item.status==='open';
  const titleBottom=wrap(x,y,item.id+' / '+item.topic+(resolved?' [PROPOSED RESOLUTION]':' ['+item.status.replaceAll('_',' ').toUpperCase()+']'),colW-40,14,18,resolved?'proposed':open?'hold':'muted');
  const clearanceHold=item.id==='OI-R05-03';
  const content=clearanceHold?item.issue:!open&&item.resolution?item.resolution:item.issue;
  registerQuoted.push({id:item.id,field:content===item.issue?'issue':'resolution',text:content});
  rowBottom=Math.max(rowBottom,wrap(x,titleBottom+3,content,colW-40,13.5,18,'muted'));
}
const pageH=Math.ceil(rowBottom+52);
text(70,pageH-22,'Master SHA256: '+hash,13,'mono muted');
text(1730,pageH-22,'Readable decision plan / all_models_reconciled = false',14,'hold','end');
add('</svg>');
const result=svg.join('\n').replaceAll('__PAGE_H__',String(pageH));
// Superseded open-item wording (pre-124ef698 OI-MBR-01/03/04, OI-UTL-01, OI-R05-04) and sheet-letter wall labels must not be drawn.
const OBSOLETE_OI=['Door v 0.16-1.01','prefer >= 2.20','Wardrobe wall N with W03','headboard E with W04','TV/door W;','Topology-derived',
  'west-upper is the continuous wall','north-utility return','Compass not established','re-place to N wardrobe','N wardrobe / E headboard',
  'bedside and bay base are later holds','MBR-rear pocket must follow','bed head now E','(sheet N)','(sheet E)','(sheet W)','(sheet S)','pre-compass wording'];
const LOAD_FIGURE=/\d\s*kg\b|\bkg\/m\b/i,norm=s=>s.replace(/\s+/g,' ').trim();
const unesc=s=>s.replaceAll('&quot;','"').replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&amp;','&');
const visibleText=norm([...result.matchAll(/<text\b[^>]*>([^<]*)<\/text>/g)].map(m=>unesc(m[1])).join(' '));
const obsoleteHits=OBSOLETE_OI.filter(p=>visibleText.includes(p)).concat(LOAD_FIGURE.test(visibleText)?['loft-load kg figure']:[]);
assert.deepEqual(obsoleteHits,[],`Superseded open-item wording is still drawn: ${obsoleteHits.join(', ')}`);
assert.deepEqual(registerQuoted.filter(q=>!visibleText.includes(norm(q.text))).map(q=>q.id),[],'Open-item register text must be quoted in full');
const corrPath=path.join(path.dirname(source),'generated','open-item-compass-correction-receipt.json');
let correction=null;
if(fs.existsSync(corrPath)){
  const cb=fs.readFileSync(corrPath),c=JSON.parse(cb.toString('utf8').replace(/^\uFEFF/,''));
  if(c.after_master_sha256===hash){
    assert.equal(c.geometry_and_lighting_unchanged,true);assert.equal(c.construction_release,false);
    const quoted=c.corrected_open_items.map(id=>registerQuoted.find(q=>q.id===id));
    assert(quoted.every(Boolean),'Every corrected open item must appear in the register');
    assert(quoted.find(q=>q.id==='OI-MBR-03').text.includes('Fixed bedside cabinets are omitted by the homeowner (HD-14), not to be re-placed'),'OI-MBR-03 must confirm the bedside omission');
    assert(!LOAD_FIGURE.test(quoted.find(q=>q.id==='OI-R05-04').text),'OI-R05-04 must carry no loft-load figure');
    correction={receipt:{file:corrPath,sha256:createHash('sha256').update(cb).digest('hex'),bytes:cb.length},before_master_sha256:c.before_master_sha256,
      corrected_open_items:c.corrected_open_items,geometry_and_lighting_unchanged:c.geometry_and_lighting_unchanged,quoted_in_full:quoted,
      obsolete_wording_absent:true,sheet_letter_wall_labels:'replaced by sheet top/right/left/bottom beside the compass names'};
  }
}
const verification={
  generated_utc:new Date().toISOString(),source_master:{file:source,sha256:hash,bytes:bytes.length},
  release:'decision_floorplan_only',construction_release:false,all_models_reconciled:false,
  geometry_source:'Canonical visualization_geometry + bathrooms + storage; no retired drawing loaded',
  rooms:P.rooms.length,storage_items:storage.length,unique_storage_ids:new Set(storage.map(s=>s.id)).size,
  loft_items:storage.filter(s=>s.kind.includes('loft')).map(s=>s.id),
  source_open_items:openItems.map(i=>({id:i.id,status:i.status,topic:i.topic,issue:i.issue,resolution:i.resolution})),
  register_quoted_in_full:registerQuoted,obsolete_wording_checked:OBSOLETE_OI,open_item_compass_correction:correction,
  measurements,storage_frame_rounding_checks:mappingResiduals,
  curtain_nightstand_clearance_m:null,curtain_nightstand_clearance_note:'not applicable: ST-R05-NS01 is omitted by the homeowner (HD-14); the earlier nightstand-to-curtain clearance check is retired',
  hd14:{decision:WR.decision,construction_release:WR.construction_release,bedside_units_omitted_not_drawn:[...hd14Omitted].sort(),curtains:'two tracks (sheer + blackout) in living, master and children rooms; pocket sizes unverified, none invented',raised_centre:'separate gypsum/POP panel below the slab; clear cavity depth and panel level unmeasured; no slab chasing or structural cutting authorised'},
  hd15:{decision:RC.decision,geometry_changed:RC.geometry_changed,estimated_clearance_mm:RC.estimated_clearance_mm,status:RC.status,recheck:RC.recheck},
  nominal_geometry_agreement_tolerance_m:1e-8,
  review_flags:[`Frame-based bed/study corner distance from the preserved storage record is ${fixed(pinch*1000,1)} mm; not drawn (the bed is shown as a mattress-only envelope) and not a certified usable passage. Requires ergonomic review under OI-BED-01 / OI-R05-03.`,
    'Pooja niche is already built; dimensions and position are homeowner estimates (HD-16 / OI-POOJA-01). The reinforced slab extension is homeowner-reported, not independently verified. Front outline only; no back or structural section is drawn. No cutting or deepening is authorised.'],
  page:{width_px:1800,height_px:pageH},
  canonical_storage_records:items.length,suppressed_storage_ids:[...suppressed],optional_outline_storage_ids:[...optionalOutline],
  item_applicability_honoured:Object.fromEntries(Object.entries(applic).map(([id,a])=>[id,{render_footprint:a.render_footprint,render_as:a.render_as}])),
  orientation:{schema:V.orientation.schema,evidence_status:V.orientation.evidence_status,sheet_to_compass:V.orientation.sheet_to_compass,true_north_vector_xz:V.orientation.true_north_vector_xz,north_arrow:'points to sheet-bottom; drawing not rotated'},
  tenant_bed_envelopes:{mattress_mm:{queen:[1524,1981],king:[1829,1981]},drawn:['R04','R05'],basis:'storage.item_applicability + decisions.bedrooms; mattress-only, no frame/bedside/walking gap implied; 1.68 x 2.13 frame not drawn (coordinator instruction)'},
  pooja_niche:{decision:PJ0.decision,built_status:PB.built_status,reinforcement:'homeowner-reported, not structurally certified',new_cutting_requested:PB.existing_construction.new_cutting_requested,compass_wall:PJ0.compass_wall,style:PJ0.style,location_src:PJ0.location_src,size_src:PJ0.size_src,wall_id:PJ0.wall,
    room_face_x_m:poojaFace0,physical_back_drawn:false,structural_section_drawn:false,z_m:PJ0.z,estimated_size:{widthMm:PJ0.widthMm,heightMm:PJ0.heightMm,sillM:PJ0.sillM,depthMm:PJ0.depthMm},outside_wall_extension:PB.existing_construction.outside_wall_extension,geometry_hold:PJ0.geometry_hold,open_item:'OI-POOJA-01',construction_release:false,drawn_as:'estimated front outline only, with dimensions and explicit extension geometry hold'},
  master_layout:ML?{decision_status:ML.decision_status,evidence_status:ML.evidence_status,relations:Object.fromEntries(Object.entries(ML.relations).map(([k,v])=>[k,{sheet_wall:v.sheet_wall,compass_wall:v.compass_wall}])),
    w03_span_m:ML.openings.W03.proposed_span_m,w03_status:ML.openings.W03.position_status,utility_open_span_m:V.openings.find(o=>o.id==='utility-open').span}:null,
  expected_symbols:{house_storage:storage.length,children_lofts:1,house_beds:storage.filter(s=>s.kind==='queen_storage_bed').length,children_beds:1,master_overlay:ML?1:0,bed_envelopes:3,pooja_niche:1,north_arrows:2},
  artifacts:{svg:{file:'house-working-floorplan.svg',sha256:createHash('sha256').update(result).digest('hex'),bytes:Buffer.byteLength(result)}},
};
assert(verification.unique_storage_ids===storage.length,'Duplicate canonical storage IDs');
assert(fs.readFileSync(source).equals(bytes),'Master changed during generation; regenerate');
fs.mkdirSync(output,{recursive:true});
verification.drawing_source=drawing;
if(drawing.staging||drawing.review_draft)fs.writeFileSync(path.join(output,'README.md'),`# Working plan - ${drawing.staging?'STAGING / NOT FINAL':'REVIEW DRAFT'}\n\nBound master SHA256: \`${hash}\`.\n\nDecision drawing only: not an as-built survey or construction release. Room and opening positions, split wardrobe zones, and selected dressing and utility cabinets remain unmeasured and subject to site checks. This plan does not show lighting.\n\n${drawing.note}\n\nPooja: estimated front outline only; reported extension geometry and capacity are unverified. No back or structural section is drawn; no cutting or deepening is authorised. W03 curtain pocket, loft support and construction details remain held.\n\nNorth is approximate homeowner cardinal north, not a surveyed true bearing. SVG, PNG and searchable PDF are accompanied by floorplan-verification.json.\n`);
fs.writeFileSync(path.join(output,'house-working-floorplan.svg'),result);
fs.writeFileSync(path.join(output,'floorplan-verification.json'),JSON.stringify(verification,null,2));
console.log(`Generated working floorplan: ${P.rooms.length} rooms / ${storage.length} storage records / ${openItems.length} decision callouts; master ${hash}`);
