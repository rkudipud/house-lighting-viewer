import assert from 'node:assert/strict';
import {makeSheet,pageHeader,pageFooter,esc,fx,COMPASS_NOTE,COMPASS_SOURCE,HEIGHT_NOTE,POOJA_NOTE,CENTRE_NOTE} from './svg.mjs';
import {FT,DIR_NAME,uOf,uRange} from './data.mjs';
import {polyPath} from './plan.mjs';

export const SCL=140;          // px per metre on elevations
const PADX=40,TOPY=178,MINW=440,MARGIN=60,GAP=30,CONTENT=1580,EST=.54;
const KIND_STYLE={
  wardrobe_hinged:{fill:'#dfe7f2',stroke:'#5b7795'},shallow_cabinet_conditional:{fill:'#e6ecf4',stroke:'#5b7795',dash:true},
  loft:{fill:'url(#loft)',stroke:'#7a6fa8',dash:true},loft_continuous:{fill:'url(#loft)',stroke:'#7a6fa8',dash:true},loft_existing_rcc_shelf_with_shutters:{fill:'url(#loft)',stroke:'#7a6fa8',dash:true},
  tv_console_floating:{fill:'#e3e7ea',stroke:'#5f6f77'},study_desk_floating:{fill:'#efe1c8',stroke:'#8a6d3b'},study_overhead_unit:{fill:'#efe1c8',stroke:'#8a6d3b'},
  shoe_cabinet_exterior:{fill:'#dfe7f2',stroke:'#5b7795'},under_counter_shutters_optional:{fill:'#e6ecf4',stroke:'#5b7795',dash:true},wall_hooks_ladder_mop:{fill:'#eee9dc',stroke:'#8b8570',dash:true},
  counter:{fill:'#eceae1',stroke:'#7d7a6a'},bar:{fill:'#eceae1',stroke:'#7d7a6a'},wallcab:{fill:'#efe5d2',stroke:'#8a7448',dash:true},plant:{fill:'#d3e6c8',stroke:'#5c8a49'},
  'bath-vanity':{fill:'#eceae1',stroke:'#7d7a6a'},'bath-wc':{fill:'#f6f7f7',stroke:'#7b8a8c'},'bath-shower':{fill:'none',stroke:'#4f9a98',dash:true}
};
const style=k=>KIND_STYLE[k]||{fill:'#e8e4da',stroke:'#7d7a6a'};
const EDGE_TAG={S:'sheet-top edge',N:'sheet-bottom edge',W:'sheet-right edge',E:'sheet-left edge'};
const WALL_OF={'negative-z':'S','positive-z':'N','positive-x':'W','negative-x':'E'};
const f2=n=>Number(n).toFixed(2);

export function wrapLines(str,w,size){
  const out=[];let line='';
  for(const word of String(str).split(/\s+/)){
    if(line&&(line.length+word.length+1)*size*EST>w){out.push(line);line=word;}else line+=(line?' ':'')+word;
  }
  if(line)out.push(line);
  return out;
}

// text that must fit a model-space box: tries sizes, then rotated; returns false when it cannot fit
function fitBox(S,box,lines,{sizes=[.1,.09,.08,.07,.062],color='#203b43',weight=''}={}){
  const [x0,y0,x1,y1]=box,w=x1-x0,h=y1-y0,cx=(x0+x1)/2,cy=(y0+y1)/2,n=lines.length,maxLen=Math.max(...lines.map(l=>l.length));
  for(const rot of [false,true]){
    const W=rot?h:w,Hh=rot?w:h;
    for(const size of sizes){
      if(maxLen*size*EST<=W-.03&&n*size*1.2<=Hh-.02){
        const lh=size*1.2;
        lines.forEach((l,k)=>S.label(cx,cy-(n-1)/2*lh+k*lh+size*.34,l,size,color,'middle',`${weight}${rot?` transform="rotate(-90 ${fx(cx,4)} ${fx(cy,4)})"`:''}`));
        return true;
      }
    }
  }
  return false;
}

// HD-11 datum: FFL 0.000; slab underside and raised centre panel are derived (unmeasured); bath/utility/lobby levels were not provided
const RAISED_ROOMS=new Set(['living','dining','master','children']);
function levelsOf(D,roomId){
  const H=D.H,DER=['derived \u2013 unmeasured','derived'],NP=['not provided; placeholder','placeholder'];
  if(roomId==='kitchen')return {top:H.kitchenFlat,tray:null,name:'flat ceiling (band level)',st:DER};
  if(roomId==='bath1'||roomId==='bath2')return {top:H.bath,tray:null,name:'bath ceiling',st:NP};
  if(roomId==='utility')return {top:H.utility,tray:null,name:'utility ceiling',st:NP};
  if(roomId==='lobby')return {top:H.lobby,tray:null,name:'lobby ceiling',st:NP};
  if(roomId==='balcony')return {top:null,tray:null,name:'no ceiling recorded',st:DER};
  if(roomId==='dressing')return {top:H.band,tray:null,name:'false-ceiling band',st:['assumed \u2013 unmeasured','assumed']};
  return {top:H.band,tray:RAISED_ROOMS.has(roomId)?H.panel:null,name:'false-ceiling band',st:DER};
}

function wallRoles(D,p){
  if(p.suffix)return [];
  const dn=DIR_NAME[p.dir],roles=[];
  const re=new RegExp(`^${dn}\\b(?!-)`,'i');
  if(p.roomId==='master'){
    const R=D.ML.relations,map={wardrobe_wall:'wardrobes, W03 bay',headboard_wall:'headboard wall, W04',tv_door_wall:'TV wall, D02',dressing_wall:'dressing passage'};
    for(const [k,label] of Object.entries(map))if(R[k]?.compass_wall===dn)roles.push(label);
  }else if(p.roomId==='children'){
    const R=D.C.compass_relations,map={wardrobe_wall:'wardrobe wall',entry:'entry D03',headboard_wall:'headboard wall, W05',tv_wall:'TV wall',study:'study'};
    for(const [k,label] of Object.entries(map))if(R[k]&&re.test(String(R[k]).trim()))roles.push(label);
  }else if(p.roomId==='living'&&p.dir==='E')roles.push('pooja niche PN1');
  return roles;
}
export function panelTitle(D,p){
  if(p.roomId==='living'&&p.dir==='E'&&!p.suffix)return 'Living \u2013 east wall: pooja niche at NE corner beside main door';
  const roles=wallRoles(D,p);
  return `${p.roomName} \u2013 ${DIR_NAME[p.dir]} wall${p.suffix}${roles.length?` (${roles.join('; ')})`:''}`;
}

function keyPlan(S,D,p,x,y){
  const KS=7.4,X0=.2277,Z0=.2246;
  S.add(`<g data-keyplan="${esc(p.id)}" transform="translate(${fx(x,2)} ${fx(y,2)}) scale(${KS}) translate(${-X0} ${-Z0})">`);
  S.rect([X0,Z0,9.1464,15.8526],'#fafbfb','#d5dddd',.04);
  for(const r of D.rooms)S.path(polyPath(r.poly),r.id===p.roomId||(p.roomId==='utility'&&(r.id==='utility'||r.id==='washing'))?'#f9dfc9':'#e9eeee','none',0);
  for(const w of D.walls)S.rect(w.rect,'#5c6b70','none',0);
  const e=p.edge,t=(e.lo+e.hi)/2;
  const a=e.horizontal?[e.lo,e.line]:[e.line,e.lo],b=e.horizontal?[e.hi,e.line]:[e.line,e.hi];
  S.line(a,b,'#d2552a',.34,'stroke-linecap="butt"');
  const from=e.horizontal?[t,e.line+e.s*1.5]:[e.line+e.s*1.5,t],to=e.horizontal?[t,e.line+e.s*.45]:[e.line+e.s*.45,t];
  S.line(from,to,'#1d5fa8',.2,'marker-end="url(#arrow)"');
  S.add('</g>');
  S.text(x+40,y-3,'N \u2193',11,'muted','middle','font-weight="700"');
}

function houseTilePanel(D,b,p){
  // bath finish regions mapped to this panel's wall
  const out=[];
  for(const [key,kind] of [['kitkat_wall_regions','feature'],['plain_wall_regions','plain']]){
    for(const r of b.finishes[key]||[]){
      if(WALL_OF[r.wall]!==p.dir)continue;
      const e=p.edge,[a,c]=r.segment_m,t0=e.horizontal?a[0]:a[1],t1=e.horizontal?c[0]:c[1];
      const [u0,u1]=uRange(e,t0,t1);
      out.push({kind,u0,u1,h0:r.height_range_m[0],h1:r.height_range_m[1],subtract:r.subtract||[]});
    }
  }
  return out;
}

function layoutPanel(D,p){
  const L=p.L,lv=levelsOf(D,p.roomId);
  const w=Math.max(L*SCL+2*PADX,MINW);
  // footprint-only strip lanes
  const strips=p.items.filter(i=>!i.h).sort((a,b)=>a.u0-b.u0),lanes=[];
  for(const it of strips){
    let k=lanes.findIndex(end=>end+.04<=it.u0);
    if(k<0){k=lanes.length;lanes.push(0);}
    lanes[k]=it.u1;it.lane=k;
  }
  const notes=buildNotes(D,p,lv);
  const noteLines=notes.flatMap(n=>wrapLines(n,w-24,11).map((t,i)=>({t,first:i===0})));
  const floorY=TOPY+(D.H.slab+.15)*SCL;
  const stripH=strips.length?(lanes.length*.30+.34)*SCL:0;
  const h=floorY+(strips.length?stripH+10:16)+22+noteLines.length*15+22;
  return {w,h,lv,strips,lanes,notes,noteLines,floorY};
}

function buildNotes(D,p,lv){
  const n=[];
  for(const g of p.gaps)if(g.openTo||g.u1-g.u0>.15)n.push(`OPEN EDGE ${f2(g.u0)}\u2013${f2(g.u1)} m: ${g.openTo?`open to ${g.openTo}`:'no wall record in the master'} \u2014 no partition is drawn or implied.`);
  for(const o of p.openings){
    const wd=Math.round((o.fullU[1]-o.fullU[0])*1000);
    n.push(`${o.code} ${o.name}: ${wd} mm wide, ${o.kind==='door'?`head ${f2(o.head)} m`:`sill ${f2(o.sill)} m, head ${f2(o.head)} m`} (${o.code==='PN1'?'homeowner estimates; not measured':'sill/head assumed'})${o.statusNote?` \u2014 ${o.statusNote}`:''}${o.assumedOpening?' \u2014 opening itself is ASSUMED':''}${o.clippedMin||o.clippedMax?' \u2014 continues past this wall edge (lift corner)':''}.`);
  }
  const bath=D.baths.find(b=>b.renderer_room_id===p.roomId);
  if(bath&&p.dir==='S'){
    const vn=bath.vanity,wc=bath.wc;
    n.push(`Vanity ${f2(vn.height_range_m[0])}\u2013${f2(vn.height_range_m[1])} m, basin top ${f2(vn.basin_top_m)} m, faucet ${f2(vn.faucet_top_m)} m; mirror ${vn.mirror_size_m[0]} \u00d7 ${vn.mirror_size_m[1]} m centred at ${f2(vn.mirror_center_xyz_m[1])} m. WC cistern to ${f2(wc.cistern_height_m)} m, seat ${f2(wc.seat_height_m)} m (dashed). All fixture dimensions are proposed, not site measured.`);
  }
  if(bath&&p.dir==='S'){
    const sh=bath.shower;
    n.push(`Shower: head ${f2(sh.head_xyz_m[1])} m, mixer ${f2(sh.mixer_xyz_m[1])} m, glass screen ${f2(sh.screen_height_m)} m. These are proposed dimensions, not site measured. Kit-kat tile only on this faucet wall inside the shower; plain porcelain elsewhere.`);
  }
  if(bath&&p.dir==='W'){
    const sh=bath.shower;
    n.push(`Shower niche ${sh.niche_width_m} \u00d7 ${sh.niche_height_m} m, ${Math.round(sh.niche_depth_m*1000)} mm deep, centred ${f2(sh.niche_center_xyz_m[1])} m: proposed model dimensions, not site measured. No new cutting without professional approval. Kit-kat covers this wet-area wall except the niche and vent.`);
  }
  for(const it of p.items){
    if(it.kind==='bath-shower'||it.kind==='bath-vanity'||it.kind==='bath-wc')continue;
    if(it.h){
      const selectedHeld=it.storage?.homeowner_selection?.status==='selected_subject_to_site_holds';
      const status=selectedHeld?' \u2014 conditionally selected, unmeasured placeholder; not fabrication dimensions':'';
      if(it.h[1]==null)n.push(`${it.id} ${it.label}: bottom ${f2(it.h[0])} m, top not in the master${it.outside?' \u2014 seen beyond the open edge':''}${status}.`);
      else n.push(`${it.id} ${it.label}: ${f2(it.h[0])}\u2013${f2(it.h[1])} m${it.outside?' \u2014 seen beyond the open edge':''}${it.hNote?` (${it.hNote})`:''}${status}.`);
    }
  }
  if(p.items.some(i=>!i.h))n.push('Items below the floor line are footprint only: their height is not in the master, so none is drawn.');
  const bed=p.items.find(i=>i.kind==='tenant-bed');
  if(bed)n.push(`Tenant's own bed: dashed queen (1524 mm) to king (1829 mm) \u00d7 1981 mm mattress envelope, head against this wall. Not joinery and not a tenant frame. Fixed bedside cabinets are omitted by the homeowner (HD-14); tenants may use movable tables.`);
  if(p.roomId==='master'){
    const R=D.ML.relations,dn=DIR_NAME[p.dir];
    if(R.wardrobe_wall.compass_wall===dn)n.push('Split wardrobe around W03 approved in principle; OPT-E BWP plywood carcass and laminate shutters selected. The relationship band is not fabrication geometry: dimensions remain held for site measurement. Loft size and support are held.');
    if(R.tv_door_wall.compass_wall===dn)n.push('TV opposite the bed: its position along this wall is held, so it is not drawn.');
    if(R.dressing_wall.compass_wall===dn)n.push('Dressing passage to R04a is on this wall, beside the TV/door wall; modelled plan position, not site verified.');
    if(R.headboard_wall.compass_wall===dn)n.push('Bed-head test wall only (H-MBR-BED; the tenant bed is not supplied): W04 sits at the end away from the wardrobe wall. W03 curtain pocket is held (H-MBR-W03).');
  }
  if(p.roomId==='children'&&D.C.compass_relations){
    const S5=D.house.storage.context_constraints_R05.switch_strip;
    if(p.dir==='S'&&!p.suffix)n.push(`Latch-side switch board (R05 only switch zone in the master): ${S5.v_m[0]}\u2013${S5.v_m[1]} m along the wall; keep free. Height not in the master.`);
  }
  if(p.roomId==='children'&&p.openings.some(o=>o.curtain))n.push(`CBR-H1 to H6 active/switchable at accepted positions (C37); product chain held. Curtain, bed and remaining fitting coordination have site holds. Curtain top ${f2(D.H.curtainTopAssumed)} m is an assumed HD-11 drawing top, not measured hardware (legacy 2.64 m retired).`);
  if(p.roomId==='kitchen')n.push(`Kitchen ceiling is one flat level at ${f2(D.H.kitchenFlat)} m (derived \u2013 unmeasured); no kitchen step. The hall cross-beam soffit is unmeasured (H-HALL-BEAM).`);
  if(p.roomId==='dining'&&p.dir==='S')n.push('Hall cross-beam depth and soffit are unmeasured (H-HALL-BEAM): DIN-H2/H3 and FW-T1 are held; the kitchen beyond is open to the dining.');
  if(p.openings.some(o=>o.curtain||['living-window','master-window','master-top-window'].includes(o.id)))n.push('Concealed ceiling curtain pocket: TWO tracks (sheer + blackout, HD-14). Clear pocket width/depth, track spacing and stack are unverified; the outline is indicative only.');
  if(p.roomId==='living'||p.roomId==='dining')n.push(CENTRE_NOTE);
  if(p.items.some(i=>/loft/.test(i.kind)))n.push('Loft heights are unmeasured and held (H-LOFT). Where shown, 3.08 m is a legacy placeholder, not raised to the slab and not an approval.');
  return n;
}

export function drawPanel(S,D,p,ox,oy,lay,rec){
  const {w,h,lv,strips,noteLines,floorY}=lay,L=p.L,top=lv.top,slab=D.H.slab;
  S.add(`<g data-panel-id="${esc(p.id)}" data-room-id="${esc(p.roomId)}" data-wall-dir="${p.dir}">`);
  S.add(`<rect x="${ox}" y="${oy}" width="${w}" height="${h}" fill="#fff" stroke="#cfd9d9" rx="6"/>`);
  // header
  const title=panelTitle(D,p),tl=wrapLines(title,w-120,17);
  tl.forEach((t,i)=>S.text(ox+16,oy+28+i*22,t,17,'','start','font-weight="600"'));
  let hy=oy+28+tl.length*22;
  S.text(ox+16,hy,`Standing inside, looking ${DIR_NAME[p.dir].toUpperCase()} \u00b7 left to right`,12.5,'muted');hy+=17;
  S.text(ox+16,hy,`${f2(L)} m long \u00b7 tag ${p.id}`,11.5,'muted mono');hy+=17;
  S.text(ox+16,hy,'HD-11 LEVELS UNMEASURED \u00b7 HEADS ASSUMED',11.5,'red','start','font-weight="700"');
  keyPlan(S,D,p,ox+w-84,oy+40);
  // elevation group (metres, y flipped through negative heights)
  S.add(`<g transform="translate(${ox+PADX} ${oy+floorY}) scale(${SCL})">`);
  const wallTop=top??slab;
  let loftHeld=false;
  const ceilOcc=[],placed=[],openLabels=[];
  // ceiling void to the slab
  if(top!=null)S.rect([0,-slab,L,-top],'#e9edf1','none',0);
  for(const wl of p.walls)S.rect([wl.u0,-wallTop,wl.u1,0],'#f4f1ea','none',0);
  for(const g of p.gaps){
    const open=g.openTo||g.u1-g.u0>.15;
    if(open){
      S.rect([g.u0,-wallTop,g.u1,0],'url(#nowall)','#a9b4b4',.008,'stroke-dasharray=".06 .04"');
      // the label is drawn after the items, in the widest stretch of the open edge that no item covers at mid-height
      const lab=g.openTo?`OPEN to ${g.openTo}`:'NO WALL RECORD';
      const mid=wallTop/2,cover=p.items.filter(i=>i.h&&i.h[0]<=mid+.2&&(i.h[1]??i.h[0]+.32)>=mid-.2).map(i=>[i.u0,i.u1]).sort((a,b)=>a[0]-b[0]);
      let segs=[[g.u0,g.u1]];
      for(const [c0,c1] of cover)segs=segs.flatMap(([a,c])=>c1<=a||c0>=c?[[a,c]]:[...(c0>a?[[a,c0]]:[]),...(c1<c?[[c1,c]]:[])]);
      segs.sort((a,b)=>(b[1]-b[0])-(a[1]-a[0]));
      openLabels.push({lab,box:segs[0]&&segs[0][1]-segs[0][0]>.12?[segs[0][0],-wallTop,segs[0][1],0]:null,mid:(g.u0+g.u1)/2,y:-wallTop/2});
      rec.openEdges.push({panel:p.id,u:[+g.u0.toFixed(3),+g.u1.toFixed(3)],openTo:g.openTo});
    }else S.rect([g.u0,-wallTop,g.u1,0],'#f4f1ea','none',0);
  }
  // bath tile finishes
  const bath=D.baths.find(b=>b.renderer_room_id===p.roomId);
  if(bath){
    for(const r of houseTilePanel(D,bath,p)){
      S.add(`<g data-tile="${r.kind}" data-room-id="${p.roomId}">`);
      S.rect([r.u0,-r.h1,r.u1,-r.h0],r.kind==='feature'?'url(#feature)':'url(#plain)',r.kind==='feature'?'#4f9a98':'#c4d0d0',.01);
      if(r.kind==='feature')S.label((r.u0+r.u1)/2,-1.65,'kit-kat feature tile',.075,'#2f6f6c');
      else if(r.u1-r.u0>.8)S.label((r.u0+r.u1)/2,-2.2,'plain tile',.075,'#5d7174');
      S.add('</g>');
    }
  }
  // master wardrobe relationship band (design held)
  if(p.roomId==='master'&&D.ML.relations.wardrobe_wall.compass_wall===DIR_NAME[p.dir]){
    const band=D.ML.relationship_zones_m.wardrobe_wall_band.rect,bay=D.ML.relationship_zones_m.window_bay.rect;
    const [b0,b1]=uRange(p.edge,band[0],band[2]),[y0,y1]=uRange(p.edge,bay[0],bay[2]);
    S.add('<g data-zone="master-wardrobe-wall-held">');
    for(const [a,c] of [[b0,y0],[y1,b1]]){
      S.rect([a,-top,c,0],'url(#zone)','#5b7795',.012,'stroke-dasharray=".07 .04"');
      fitBox(S,[a,-top,c,0],['WARDROBE ZONE','in principle','sizes held'],{color:'#466c92',sizes:[.09,.08]});
    }
    S.add('</g><g data-zone="master-loft-held">');
    S.rect([b0,-slab,b1,-top],'url(#loft)','#7a6fa8',.012,'stroke-dasharray=".07 .04"');
    S.label(b0+.05,-top-.1,'LOFT held (H-LOFT: size, design and top not in master)',.07,'#6a5f98','start');
    S.add('</g>');
    loftHeld=true;
  }
  // children's latch-side switch strip
  if(p.roomId==='children'&&p.dir==='S'&&!p.suffix){
    const s=D.house.storage.context_constraints_R05.switch_strip,fr=D.C.frame;
    const to=(u,v)=>[fr.origin_xz_m[0]+u*fr.u_axis_xz[0]+v*fr.v_axis_xz[0],fr.origin_xz_m[1]+u*fr.u_axis_xz[1]+v*fr.v_axis_xz[1]];
    const [a,c]=uRange(p.edge,to(0,s.v_m[0])[0],to(0,s.v_m[1])[0]);
    S.add('<g data-zone="r05-switch-strip">');
    S.rect([a,-top,c,0],'url(#zone)','#a06a1c',.012,'stroke-dasharray=".05 .04"');
    fitBox(S,[a,-top,c,0],['SWITCH BOARD','keep free'],{color:'#8a5a14',sizes:[.075,.065]});
    S.add('</g>');
    rec.switchStrip=p.id;
  }
  // bath fixtures behind/around the openings
  if(bath){
    const vn=bath.vanity,wc=bath.wc,sh=bath.shower;
    if(p.dir==='S'){
      const ux=x=>uOf(p.edge,x);
      const [m0,m1]=uRange(p.edge,vn.mirror_center_xyz_m[0]-vn.mirror_size_m[0]/2,vn.mirror_center_xyz_m[0]+vn.mirror_size_m[0]/2);
      S.add(`<g data-bath-id="${esc(bath.id)}" data-bath-detail="services-wall">`);
      S.rect([m0,-(vn.mirror_center_xyz_m[1]+vn.mirror_size_m[1]/2),m1,-(vn.mirror_center_xyz_m[1]-vn.mirror_size_m[1]/2)],'#e4f0f5','#5a7f8f',.012);
      S.label((m0+m1)/2,-vn.mirror_center_xyz_m[1]+.03,'mirror',.07,'#3d6a7a');
      const [v0,v1]=uRange(p.edge,vn.rect_m[0],vn.rect_m[2]);
      S.line([v0,-vn.basin_top_m],[v1,-vn.basin_top_m],'#5d6a6c',.02);
      S.rect([(v0+v1)/2-.015,-vn.faucet_top_m,(v0+v1)/2+.015,-vn.basin_top_m],'#7a8a8d','none',0);
      const hx=ux(sh.head_xyz_m[0]);
      S.line([hx-.1,-sh.head_xyz_m[1]],[hx+.1,-sh.head_xyz_m[1]],'#5d6a6c',.025);
      S.label(hx,-sh.head_xyz_m[1]+.12,'shower head 2.15',.07,'#3d6a7a');
      S.add(`<circle cx="${fx(ux(sh.mixer_xyz_m[0]),3)}" cy="${fx(-sh.mixer_xyz_m[1],3)}" r=".035" fill="#fff" stroke="#5d6a6c" stroke-width=".01"/>`);
      S.label(ux(sh.mixer_xyz_m[0]),-sh.mixer_xyz_m[1]-.07,'mixer 1.05',.07,'#3d6a7a');
      const sc=ux(sh.screen_segment_m[0][0]);
      S.line([sc,0],[sc,-sh.screen_height_m],'#4f9a98',.02,'stroke-dasharray=".05 .03"');
      S.label(sc-.04,-1.5,'glass screen 2.00',.07,'#2f6f6c','end');
      S.label(sc-.04,-1.4,'(seen edge-on)',.07,'#2f6f6c','end');
      const [b0,b1]=uRange(p.edge,wc.bowl_rect_m[0],wc.bowl_rect_m[2]);
      S.line([b0,-wc.seat_height_m],[b1,-wc.seat_height_m],'#7b8a8c',.012,'stroke-dasharray=".04 .03"');
      S.add('</g>');
    }
    if(p.dir==='W'){
      const e=p.edge,[s0,s1]=uRange(e,sh.screen_segment_m[0][1],sh.screen_segment_m[1][1]);
      S.add(`<g data-bath-id="${esc(bath.id)}" data-bath-detail="shower-screen">`);
      S.rect([s0,-sh.screen_height_m,s1,0],'none','#4f9a98',.014,'stroke-dasharray=".06 .04"');
      S.label(s0+.05,-.12,`screen ${f2(sh.screen_height_m)} m proposed`,.07,'#2f6f6c','start');
      S.add('</g>');
    }
  }
  // openings
  for(const o of p.openings){
    const isDoor=o.kind==='door',y0=isDoor?0:o.sill,y1=o.head;
    const niche=/niche/.test(o.id),poojaN=o.code==='PN1';
    const dash=o.placeholder||o.assumedOpening||poojaN?'stroke-dasharray=".06 .04"':'';
    S.add(`<g data-opening-id="${esc(o.id)}" data-opening-code="${esc(o.code)}" data-panel-id="${esc(p.id)}">`);
    S.rect([o.u0,-y1,o.u1,-y0],isDoor?'#e3d3bd':niche?'#e7e0ef':'#d7ebf2',niche?'#786385':'#4b6a78',.018,dash);
    if(isDoor&&o.double)S.line([(o.u0+o.u1)/2,-y1],[(o.u0+o.u1)/2,-y0],'#4b6a78',.01);
    else if(!isDoor&&!niche)S.line([(o.u0+o.u1)/2,-y1],[(o.u0+o.u1)/2,-y0],'#7fa0ad',.008);
    const w=o.u1-o.u0,hh=y1-y0;
    const mark=o.statusNote||o.assumedOpening||o.placeholder||poojaN?'\u2020':'';
    const l1=`${o.code}${mark}`,l2=isDoor?`head ${f2(o.head)}`:`sill ${f2(o.sill)}`,l3=isDoor?'':`head ${f2(o.head)}`;
    const lines=poojaN?[l1,'built','estimated','sill '+f2(o.sill),'head '+f2(o.head)]:[l1,l2,...(l3?[l3]:[])];
    if(!fitBox(S,[o.u0,-y1,o.u1,-y0],lines,{sizes:[.1,.085,.075,.065],weight:'font-weight="600" '})){
      if(!fitBox(S,[o.u0,-y1,o.u1,-y0],[l1,`${isDoor?'':`${f2(o.sill)}\u2013`}${f2(o.head)}`],{sizes:[.075,.065],weight:'font-weight="600" '})){
        S.label((o.u0+o.u1)/2,-y1-.05,`${l1} ${isDoor?'':f2(o.sill)+'\u2013'}${f2(o.head)}`,.07,'#203b43');
      }
    }
    S.add('</g>');
    rec.openings.push({id:o.id,panel:p.id});
    // curtains
    if(o.kind==='window'||/pooja/.test(o.id)){/* niches carry no curtain */}
    if(o.kind==='window'&&!niche){
      const cw=D.house.lighting.design_inputs.calc_geometry.curtains,pw=cw.return_m;
      const BASE={'living-window':'LIV','dining-window':'DIN','master-top-window':'MBR-rear','master-window':'MBR-side'};
      S.add(`<g data-curtain-for="${esc(o.id)}">`);
      if(o.curtain){
        // children's curtain: top is the assumed HD-11 drawing level (legacy 2.64 m retired); fittings held under H-CBR-CURTAIN
        const [c0,c1]=uRange(p.edge,o.curtain.span[0],o.curtain.span[1]);
        S.rect([c0,-o.curtain.top,c1,-o.curtain.bottom],'none','#b02f2f',.012,'stroke-dasharray=".05 .04"');
        S.label((c0+c1)/2,-o.curtain.top+.14,'curtain drop HELD (H-CBR-CURTAIN)',.07,'#b02f2f');
        S.label((c0+c1)/2,-o.curtain.top+.24,`top ${f2(o.curtain.top)} assumed, not hardware`,.065,'#b02f2f');
        ceilOcc.push([c0,c1]);
        rec.curtains.push({opening:o.id,panel:p.id,kind:'cbr-held-assumed-top'});
      }else if(BASE[o.id]&&top!=null){
        const held=BASE[o.id]==='MBR-rear',win=held?cw.pending_windows[BASE[o.id]]:cw.windows[BASE[o.id]];
        assert(win,`curtain record for ${BASE[o.id]}`);
        let [c0,c1]=held?uRange(p.edge,win.along0_ft*FT,win.along1_ft*FT):[o.u0-pw,o.u1+pw];
        if(held){c0-=pw;c1+=pw;}
        c0=Math.max(0,c0);c1=Math.min(L,c1);
        S.rect([c0,-top,c1,-(top-.07)],held?'#f6dede':'#e9dff0',held?'#b02f2f':'#7c658c',.012,'stroke-dasharray=".04 .03"');
        const plab=held?'W03 pocket HELD (H-MBR-W03)':(['LIV','MBR-side'].includes(BASE[o.id])?'pocket: 2 tracks (sheer + blackout)':'curtain pocket (assumed)');
        {
          const ptw=plab.length*.07*EST,pc=(c0+c1)/2;
          if(pc-ptw/2<0)S.label(Math.max(c0,.03),-top+.17,plab,.07,held?'#b02f2f':'#6a5580','start');
          else if(pc+ptw/2>L)S.label(Math.min(c1,L-.03),-top+.17,plab,.07,held?'#b02f2f':'#6a5580','end');
          else S.label(pc,-top+.17,plab,.07,held?'#b02f2f':'#6a5580');
        }
        ceilOcc.push([c0,c1]);
        rec.curtains.push({opening:o.id,panel:p.id,kind:held?'held':'assumed'});
      }
      S.add('</g>');
    }
  }
  // furniture, storage and kitchen items with heights
  const hItems=p.items.filter(i=>i.h).sort((a,b)=>(a.h[0]-b.h[0])||(a.kind==='wallcab')-(b.kind==='wallcab'));
  const boxes=[];let fb=null;
  // narrow a label box to the widest span not already covered by an earlier item box at the same height
  const freeBox=b=>{
    let segs=[[b[0],b[2]]];
    for(const r of boxes){
      if(!(r[1]<b[3]&&r[3]>b[1]))continue;
      segs=segs.flatMap(([a,c])=>r[2]<=a||r[0]>=c?[[a,c]]:[...(r[0]>a?[[a,r[0]]]:[]),...(r[2]<c?[[r[2],c]]:[])]);
    }
    segs.sort((x,y)=>(y[1]-y[0])-(x[1]-x[0]));
    return segs[0]&&segs[0][1]-segs[0][0]>.12?[segs[0][0],b[1],segs[0][1],b[3]]:null;
  };
  for(const it of hItems){
    const st=style(it.kind),lo=it.h[0],hi=it.h[1]??lo+.32,open=it.h[1]==null;
    const attrs=it.storage?`data-storage-id="${esc(it.id)}" data-storage-kind="${esc(it.storage.kind)}"`:`data-item-id="${esc(it.id)}" data-item-kind="${esc(it.kind)}"`;
    S.add(`<g ${attrs} data-panel-id="${esc(p.id)}"${it.outside?' opacity=".6"':''}>`);
    const dash=st.dash||it.outside?'stroke-dasharray=".06 .04"':'';
    if(it.kind==='bath-shower'){S.add('</g>');rec.items.push({id:it.id,panel:p.id});continue;}
    if(open){
      S.path(`M${fx(it.u0,3)} ${fx(-lo-.32,3)}V${fx(-lo,3)}H${fx(it.u1,3)}V${fx(-lo-.32,3)}`,'none',st.stroke,.014,dash);
    }else S.rect([it.u0,-hi,it.u1,-lo],st.fill,st.stroke,.014,dash);
    if(it.kind==='bar'||(it.kind==='counter'&&it.topThk)){const t=it.topThk||.03;S.rect([it.u0,-hi,it.u1,-(hi-t)],'#b9b6a8',st.stroke,.008);}
    if(it.kind==='counter'||it.kind==='bar'){S.rect([it.u0,-hi-.0,it.u1,-(hi-.03)],'#b9b6a8',st.stroke,.008);}
    const nm=it.storage?it.label:it.kind==='wallcab'?'wall cabinets':it.kind==='bar'?'breakfast counter':it.kind==='plant'?it.label:it.label;
    const idl=it.storage?it.id:'';
    const lines=[nm,...(idl?[idl]:[]),...(open?['top not in master']:[])];
    const box=[it.u0,-(open?lo+.32:hi),it.u1,-lo];
    if(/loft/.test(it.kind)){
      // loft text stays below the ceiling band so it never collides with the band/tray labels
      const cap=top!=null?Math.min(hi,top-.05):hi,lbox=[it.u0,-cap,it.u1,-lo];
      for(const t of [[nm,idl],[nm],['loft',idl],['loft']].map(a=>a.filter(Boolean)))if(fitBox(S,lbox,t,{sizes:[.085,.075,.065,.058]}))break;
      if(top!=null&&lo<top&&hi>top-.1)ceilOcc.push([it.u0,it.u1]);
    }else if((fb=freeBox(box))&&(fitBox(S,fb,lines,{sizes:[.085,.075,.065]})||fitBox(S,fb,[nm],{sizes:[.075,.065,.058]}))){
      placed.push(fb);boxes.push(box);
    }else{
      boxes.push(box);
      const tw=nm.length*.07*EST,cx=(it.u0+it.u1)/2,ty=-(open?lo+.32:hi)-.07;
      let ax='middle',tx=cx;
      if(cx-tw/2<0){ax='start';tx=Math.max(it.u0,.02);}else if(cx+tw/2>L){ax='end';tx=Math.min(it.u1,L-.02);}
      const x0=ax==='middle'?tx-tw/2:ax==='end'?tx-tw:tx,rect=[x0,ty-.08,x0+tw,ty+.02];
      if(!placed.some(r=>r[0]<rect[2]&&r[2]>rect[0]&&r[1]<rect[3]&&r[3]>rect[1])){
        S.label(tx,ty,nm,.07,'#203b43',ax);placed.push(rect);
      }
    }
    S.add('</g>');
    rec.items.push({id:it.id,panel:p.id});
  }
  for(const o of openLabels){
    if(!o.box)continue;
    if(!fitBox(S,o.box,[o.lab],{color:'#6b7b7d',sizes:[.09,.08,.07]})&&!fitBox(S,o.box,['OPEN'],{color:'#6b7b7d',sizes:[.08,.07]}))S.label((o.box[0]+o.box[2])/2,o.y,'OPEN',.07,'#6b7b7d');
  }
  // ceiling, tray and slab lines with labels
  const ext=.12;
  S.line([-ext,0],[L+ext,0],'#203b43',.035);
  S.label(-ext+.02,.13,'FFL 0.00',.07,'#5d7174','start');
  S.line([-ext,-slab],[L+ext,-slab],'#5d6e77',.018,'stroke-dasharray=".08 .05"');
  const merged=lv.tray!=null&&Math.abs(lv.tray-slab)<.005;
  S.label(.02,-slab-.05,`slab underside ${f2(slab)} (derived \u2013 unmeasured)`,.075,'#5d6e77','start');
  if(top!=null){
    S.line([-ext,-top],[L+ext,-top],'#203b43',.035);
    const flat=p.roomId==='kitchen';
    const hit=(a,b)=>ceilOcc.some(([c0,c1])=>c0<b&&c1>a);
    const sideRoom=(w-PADX)/SCL-.05;
    // ceiling labels: first variant that fits a free stretch of the wall, else beside the wall, else overlaid
    const ceilLabel=(y,variants,size,color,{pref='end',altY=y}={})=>{
      for(const t of variants){
        const tw=t.length*size*EST+.06;
        if(tw>L-.04)continue;
        const cands=[];
        for(let a=L-tw;a>=-1e-6;a-=.1)cands.push(Math.max(0,a));
        if(pref==='middle')cands.sort((a,b)=>Math.abs(a+tw/2-L/2)-Math.abs(b+tw/2-L/2));
        for(const a of cands)if(!hit(a,a+tw)){
          if(Math.abs(a+tw-L)<1e-6)S.label(L-.03,y,t,size,color,'end');
          else S.label(a+.03,y,t,size,color,'start');
          return;
        }
      }
      const t=variants[variants.length-1],tw=t.length*size*EST+.06;
      if(L+ext+.06+tw<=sideRoom)S.label(L+ext+.06,y,t,size,color,'start');
      else S.label(L-.03,altY,t,size,color,'end');
    };
    const bathRoom=p.roomId==='bath1'||p.roomId==='bath2';
    ceilLabel(bathRoom?-top-.05:-top+.1,[`${lv.name} ${f2(top)} (${lv.st[0]})`,`${lv.name==='false-ceiling band'?'band':lv.name.split(' ')[0]} ${f2(top)} (${lv.st[1]})`],.075,'#203b43',{altY:-top-.04});
    if(lv.tray&&!merged){
      S.line([0,-lv.tray],[L,-lv.tray],'#9b8a5a',.014,'stroke-dasharray=".06 .04"');
      const tvars=[`raised tray ${f2(lv.tray)} \u2014 room centre only (derived \u2013 unmeasured)`,`raised tray ${f2(lv.tray)} (derived)`,`tray ${f2(lv.tray)} (derived)`];
      if(loftHeld)S.label(L-.03,-lv.tray-.05,tvars[0],.07,'#7a6a3c','end');
      else ceilLabel(-lv.tray-.05,tvars,.07,'#7a6a3c',{pref:'middle'});
    }
    if(flat&&p.dir==='N'){
      S.label(L/2,-top-.1,'hall cross-beam beyond: soffit unmeasured (H-HALL-BEAM)',.065,'#b02f2f');
    }
  }else{
    S.label(L-.02,-slab+.12,'balcony ceiling: not recorded',.075,'#203b43','end');
  }
  S.line([0,0],[0,-wallTop],'#8a9a9c',.012);S.line([L,0],[L,-wallTop],'#8a9a9c',.012);
  // footprint-only strip below the floor line
  if(strips.length){
    S.label(.02,.28,'FOOTPRINT ONLY \u2014 height not in master (modelled plan position; not site verified)',.07,'#9b641c','start','font-weight="600"');
    for(const it of strips){
      const y0=.35+it.lane*.30,y1=y0+.25;
      S.add(`<g data-item-id="${esc(it.id)}" data-item-kind="${esc(it.kind)}" data-panel-id="${esc(p.id)}" data-footprint-only="true"${it.outside?' opacity=".6"':''}>`);
      const bed=it.kind==='tenant-bed';
      S.rect([it.u0,y0,it.u1,y1],bed?'#f5f6fa':'#f1ece2',bed?'#5b7795':'#8a7a66',.012,'stroke-dasharray=".05 .04"');
      if(bed&&it.queenRect){
        const e=p.edge,[q0,q1]=uRange(e,it.queenRect[e.horizontal?0:1],it.queenRect[e.horizontal?2:3]);
        S.rect([q0,y0+.03,q1,y1-.03],'none','#5b7795',.008,'stroke-dasharray=".03 .03"');
      }
      const lab=bed?"tenant's bed \u2014 queen to king envelope":`${it.label}${it.outside?' (beyond)':''}`;
      if(!fitBox(S,[it.u0,y0,it.u1,y1],[lab],{sizes:[.075,.068,.06]})){
        if(!fitBox(S,[it.u0,y0,it.u1,y1],[bed?"tenant's bed":it.label.split(' ')[0]],{sizes:[.07,.06,.055]}))S.label((it.u0+it.u1)/2,(y0+y1)/2+.025,'\u2026',.07,'#203b43');
      }
      S.add('</g>');
      rec.items.push({id:it.id,panel:p.id,footprintOnly:true});
    }
  }
  S.add('</g>');
  // notes list
  let ny=oy+floorY+(strips.length?(lay.lanes.length*.30+.34)*SCL+14:18)+14;
  S.add(`<path d="M${ox+12} ${ny-12}H${ox+w-12}" stroke="#e1e8e8"/>`);
  for(const l of noteLines){S.text(ox+14+(l.first?0:10),ny,(l.first?'\u2022 ':'')+l.t,11,'muted');ny+=15;}
  S.add('</g>');
}

// HD-16 permits the estimated front only; the external construction is not surveyed.
function poojaDetail(S,D,ox,oy,w){
  const P=D.pooja,wall=D.walls.find(x=>x.id===P.wall),T=wall?Math.min(wall.rect[2]-wall.rect[0],wall.rect[3]-wall.rect[1]):null;
  const K=140;const W=P.widthMm/1000,Hn=P.heightMm/1000,sill=P.sillM;
  const h=690;
  S.add(`<g data-detail="pooja-niche"><rect x="${ox}" y="${oy}" width="${w}" height="${h}" fill="#fff" stroke="#cfd9d9" rx="6"/>`);
  S.text(ox+16,oy+28,'Pooja niche PN1 \u2014 recessed, built (living east wall)',17,'','start','font-weight="600"');
  S.text(ox+16,oy+48,'Flush room face reported; external extension geometry is unverified.',12.5,'muted');
  S.text(ox+16,oy+66,'HD-16 / HD-18 homeowner estimates \u00b7 site check (OI-POOJA-01)',11.5,'red','start','font-weight="700"');
  // front view
  const fx0=ox+24,fy0=oy+88;
  S.add(`<g transform="translate(${fx0} ${fy0+2.4*K}) scale(${K})">`);
  const FW=1.5;
  S.rect([0,-2.4,FW,0],'#f4f1ea','#8a9a9c',.01);
  const n0=(FW-W)/2;
  S.rect([n0,-sill-Hn,n0+W,-sill],'#f1eaf6','#786385',.018,'stroke-dasharray=".06 .04"');
  S.line([-.05,0],[FW+.05,0],'#203b43',.025);
  S.label(FW/2,-sill-Hn/2-.04,'recessed niche',.065,'#6a5580');
  S.label(FW/2,-sill-Hn/2+.06,`${P.widthMm} \u00d7 ${P.heightMm} mm`,.063,'#6a5580');
  S.label(FW/2,-sill-Hn/2+.16,'(estimated front)',.063,'#6a5580');
  S.label(FW/2,-sill+.12,`sill ${f2(sill)} m`,.07,'#203b43');
  S.label(FW/2,.12,'room face reported flush',.07,'#5d7174');
  S.add('</g>');
  const nx=ox+260;
  S.text(nx,oy+125,'EXTERNAL CONSTRUCTION HELD',12,'red','start','font-weight="700"');
  let hy=oy+149;
  for(const n of [`Estimated depth: ${P.depthMm} mm.`, `Modeled wall: ${Math.round(T*1000)} mm.`,
    'Homeowner reports a reinforced slab extension top to bottom through the building.',
    'No surveyed extension section or physical back is shown.',
    'Measure dimensions and verify support / capacity on site.']){
    hy=S.wrap(nx,hy,n,235,12,17,'muted');hy+=12;
  }
  const notes=[
    `Already built. Width ${P.widthMm} mm. ${D.drawingSource.note}`,
    'Reinforcement and extension are homeowner-reported, not independently verified. No allowable load is recorded. A mismatch with the old modeled wall is not proof of an unsafe or impossible niche. No cutting or deepening is authorised.',
    `East-wall relationship confirmed; the north-corner offset and opening position are provisional. Modeled z ${D.PN.dimensions.z_m.map(v=>f2(v)).join(' to ')} m. Balcony-edge alignment remains unresolved. LIV-P1 / LIV-P2 placement is subject to the integrated lighting holds.`
  ];
  let y=oy+466;
  for(const n of notes)for(const l of wrapLines(n,w-30,11.5)){S.text(ox+16,y,l,11.5,'muted');y+=15;}
  S.add('</g>');
  return {h,T};
}

export const SHEETS=[
  {no:3,roomId:'living',id:'03-elev-R01-living',title:'R01 Living'},
  {no:4,roomId:'dining',id:'04-elev-R02-dining',title:'R02 Dining'},
  {no:5,roomId:'kitchen',id:'05-elev-R03-kitchen',title:'R03 Kitchen'},
  {no:6,roomId:'master',id:'06-elev-R04-master',title:'R04 Master bedroom'},
  {no:7,roomId:'dressing',id:'07-elev-R04a-dressing',title:'R04a Master dressing'},
  {no:8,roomId:'children',id:'08-elev-R05-children',title:"R05 Children's bedroom"},
  {no:9,roomId:'bath1',id:'09-elev-R06-TL1',title:'R06 TL1 attached toilet'},
  {no:10,roomId:'bath2',id:'10-elev-R07-TL2',title:'R07 TL2 common toilet'},
  {no:11,roomId:'utility',id:'11-elev-R08-utility',title:'R08 Utility + washing'},
  {no:12,roomId:'balcony',id:'12-elev-R09-entry',title:'R09 Entry / balcony'},
  {no:13,roomId:'lobby',id:'13-elev-R12-lobby',title:'R12 Common lobby'}
];

function legend(S,y){
  const items=[['#f4f1ea','#8a9a9c','Wall surface',''],['url(#nowall)','#a9b4b4','Open edge (no wall)','.'],['#d7ebf2','#4b6a78','Window / glass',''],['#e3d3bd','#4b6a78','Door',''],['#dfe7f2','#5b7795','Built storage record',''],['url(#loft)','#7a6fa8','Loft / held zone (dashed)','4 3'],['#e9edf1','#c8d2d3','Ceiling void to slab',''],['#e9dff0','#7c658c','Curtain pocket (concealed; 2 tracks in LIV/MBR/CBR)','3 2'],['#f6dede','#b02f2f','Held pocket / curtain (red dashed)','3 2'],['#cfc4dc','#786385','Pooja niche PN1 (recessed, built)',''],['url(#feature)','#4f9a98','Kit-kat tile (wet area)',''],['#f1ece2','#8a7a66','Footprint only (below floor)','4 3']];
  let x=MARGIN,yy=y;
  for(const [fill,stroke,label,dash] of items){
    const iw=28+label.length*6.4+18;
    if(x+iw>1700-MARGIN){x=MARGIN;yy+=20;}
    S.add(`<rect x="${x}" y="${yy}" width="22" height="14" fill="${fill}" stroke="${stroke}"${dash&&dash!=='.'?` stroke-dasharray="${dash}"`:''}/>`);
    S.text(x+28,yy+12,label,12,'muted');
    x+=iw;
  }
}

export function buildElevations(D,{total}){
  const sheets=[];
  for(const def of SHEETS){
    const room=D.elevRooms.find(r=>r.id===def.roomId);
    const kept=D.panels.filter(p=>p.roomId===def.roomId&&p.keep),openPanels=D.panels.filter(p=>p.roomId===def.roomId&&!p.keep);
    const lays=kept.map(p=>({p,lay:layoutPanel(D,p)}));
    const blocks=lays.map(({p,lay})=>({kind:'panel',p,lay,w:lay.w,h:lay.h}));
    if(def.roomId==='living')blocks.push({kind:'pooja',w:520,h:690});
    // greedy row packing
    const rows=[];let cur=null;
    for(const b of blocks){
      if(!cur||cur.w+GAP+b.w>CONTENT){cur={w:0,h:0,items:[]};rows.push(cur);}
      cur.items.push(b);cur.w+=(cur.items.length>1?GAP:0)+b.w;cur.h=Math.max(cur.h,b.h);
    }
    const S=makeSheet({width:1700,title:`Elevations \u2014 ${def.title}`,desc:'Read-only interior elevations from the canonical master; HD-11 levels are homeowner-stated or derived and unmeasured; wall names by compass.',
      metadata:{sheet:def.id,room:def.roomId,master_sha256:D.hash,heights:'hd11_homeowner_stated_or_derived_unmeasured',compass:'visualization_geometry.orientation'}});
    pageHeader(S,{title:`Interior elevations \u2014 ${def.title}`,subtitle:`${room.nominal?`${room.nominal} \u00b7 `:''}every wall seen from inside \u00b7 named by compass \u00b7 HD-11 levels unmeasured`,no:def.no,total,hash:D.hash});
    legend(S,130);
    const rec={openings:[],items:[],curtains:[],openEdges:[],switchStrip:null};
    let y=178;
    for(const row of rows){
      let x=MARGIN;
      for(const b of row.items){
        if(b.kind==='panel')drawPanel(S,D,b.p,x,y,b.lay,rec);
        else poojaDetail(S,D,x,y,b.w);
        x+=b.w+GAP;
      }
      y+=row.h+GAP;
    }
    // footer notes
    y+=4;
    S.text(MARGIN,y,'ABOUT THIS SHEET',15,'sect');y+=6;
    const foot=[HEIGHT_NOTE,COMPASS_NOTE,COMPASS_SOURCE];
    if(def.roomId==='living')foot.push(POOJA_NOTE);
    if(def.roomId==='children')foot.push(D.r05ClearanceNote);
    foot.push('\u2020 marks an opening that is assumed, a placeholder, centred-but-unmeasured, or (PN1) a built niche whose size is unmeasured. Window and door positions are modelled plan positions, not site verified; sills and heads are assumptions. Held items (red dashed) are not approved layouts. The 2.939 m children\u2019s curtain top is an assumed HD-11 drawing level, not measured hardware. Living, master and children\u2019s concealed curtain pockets need two tracks (sheer + blackout, HD-14); their clear sizes are unverified.');
    if(openPanels.length)foot.push(`Edges not elevated because they are open to another space or have no wall record: ${openPanels.map(p=>`${DIR_NAME[p.dir]} edge${p.gaps[0]?.openTo?` (open to ${p.gaps[0].openTo})`:' (no wall record)'}`).join('; ')}. No partition is invented.`);
    foot.push('Dimensions in metres unless marked mm. Wall names are compass directions; the small sheet tags (e.g. master-s) are only drawing IDs. Items without a height in the master are shown as footprints below the floor line.');
    for(const n of foot){for(const l of wrapLines(n,CONTENT,12.5)){y+=18;S.text(MARGIN,y,l,12.5,'muted');}y+=4;}
    y+=40;
    pageFooter(S,y,D.hash);
    const svg=S.finish(y);
    sheets.push({id:def.id,title:`Elevations \u2014 ${def.title}`,roomId:def.roomId,no:def.no,svg,
      counts:{panels:kept.length,openEdgesNotElevated:openPanels.length,openingsDrawn:rec.openings.length,itemsDrawn:rec.items.length,curtains:rec.curtains.length,openEdgeNotes:rec.openEdges.length},
      drawn:{panels:kept.map(p=>p.id),openPanels:openPanels.map(p=>p.id),openings:rec.openings,items:rec.items,curtains:rec.curtains,switchStrip:rec.switchStrip}});
  }
  return sheets;
}
