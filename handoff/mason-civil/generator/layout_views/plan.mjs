import {makeSheet,pageHeader,pageFooter,northArrow,esc,fx,COMPASS_NOTE,COMPASS_SOURCE,HEIGHT_NOTE,POOJA_NOTE} from './svg.mjs';
import assert from 'node:assert/strict';
import {FT,inPoly,MATTRESS_MM} from './data.mjs';

export const ROOM_FILL={living:'#f6eedf',dining:'#f3ead8',kitchen:'#f5efd3',master:'#e7eef5',dressing:'#ebf0f5',children:'#e6f0ee',bath1:'#dff0ee',bath2:'#dff0ee',utility:'#ebeee9',washing:'#e3e9e9',balcony:'#e7f1e1',lobby:'#efeee7'};
export const SC=105,TX=126,TY=250;
export const WALL='#42545a';

export const polyPath=poly=>poly.map((p,i)=>`${i?'L':'M'}${fx(p[0],4)} ${fx(p[1],4)}`).join('')+'Z';

// walls, windows, doors (with swings), niches and the dashed parapet opening; every wall and opening carries its master id
export function drawWalls(S,D,{swings=true,tags=true}={}){
  const counts={walls:0,openings:0};
  for(const w of D.walls){S.add(`<g data-wall-id="${esc(w.id)}">`);S.rect(w.rect,WALL,WALL,.003);S.add('</g>');counts.walls++;}
  for(const o of D.openings){
    const w=D.walls.find(w=>w.id===o.wall);
    const [x,z,X,Z]=w.rect,ax=o.axis==='x',a=o.span[0],b=o.span[1],cross=ax?(z+Z)/2:(x+X)/2;
    S.add(`<g data-opening-id="${esc(o.id)}" data-opening-code="${esc(o.code)}">`);
    if(o.id==='pooja-niche'){
      const face=Math.max(x,X);
      assert(!ax,'PN1 must stay on the recorded east-wall face');
      S.add('<g data-niche-representation="front-outline-only">');
      S.line([face,a],[face,b],'#d3b8e5',.06,'stroke-dasharray=".08 .04"');
      S.line([face-.05,a],[face+.05,a],'#5b4668',.025);
      S.line([face-.05,b],[face+.05,b],'#5b4668',.025);
      S.add('</g>');
    }else if(o.kind.includes('niche')){
      S.line(ax?[a,cross]:[cross,a],ax?[b,cross]:[cross,b],'#786385',.07,'stroke-dasharray=".05 .03"');
    }else if(o.kind==='open'){
      S.rect(ax?[a,z-.003,b,Z+.003]:[x-.003,a,X+.003,b],'#fcfdfc','none',0);
      S.line(ax?[a,cross]:[cross,a],ax?[b,cross]:[cross,b],'#466c92',.05,'stroke-dasharray=".14 .07"');
    }else{
      S.rect(ax?[a,z-.003,b,Z+.003]:[x-.003,a,X+.003,b],'#fcfdfc','none',0);
      if(o.kind!=='door'){
        S.line(ax?[a,cross]:[cross,a],ax?[b,cross]:[cross,b],'#31818d',.045,o.kind==='vent'?'stroke-dasharray=".06 .03"':'');
      }else if(swings){
        const n=o.double?2:1,span=(b-a)/n,jamb=o.jambM??.025;
        for(let k=0;k<n;k++){
          const max=k===1||o.hingeEnd==='max',sign=max?-1:1,hinge=max?b-jamb:a+jamb,r=span-2*jamb,side=o.openSide??1;
          const h=ax?[hinge,cross]:[cross,hinge],closed=ax?[hinge+sign*r,cross]:[cross,hinge+sign*r],open=ax?[hinge,cross+side*r]:[cross+side*r,hinge];
          S.line(h,open,'#405f7e',.022);S.line(h,closed,'#8095aa',.009,'stroke-dasharray=".04 .03"');
          const start=Math.atan2(closed[1]-h[1],closed[0]-h[0]),end=Math.atan2(open[1]-h[1],open[0]-h[0]);
          let turn=end-start;if(turn>Math.PI)turn-=2*Math.PI;if(turn<-Math.PI)turn+=2*Math.PI;
          const pts=Array.from({length:21},(_,i)=>[h[0]+r*Math.cos(start+turn*i/20),h[1]+r*Math.sin(start+turn*i/20)]);
          S.path(pts.map((p,i)=>(i?'L':'M')+fx(p[0],4)+' '+fx(p[1],4)).join(''),'none','#8095aa',.009);
        }
      }else{
        S.line(ax?[a,cross]:[cross,a],ax?[b,cross]:[cross,b],'#405f7e',.03);
      }
    }
    S.add('</g>');counts.openings++;
    if(tags&&!o.kind.includes('niche')){
      // opening code tag on the room side of the wall
      const mid=(a+b)/2,off=.26;
      const p1=ax?[mid,cross+off]:[cross+off,mid],p2=ax?[mid,cross-off]:[cross-off,mid];
      const inRoom=p=>D.rooms.some(r=>!r.exterior&&inPoly(p,r.poly));
      const p=inRoom(p1)?p1:inRoom(p2)?p2:p1;
      S.label(p[0],p[1]+.035,o.code,.095,'#31606d');
    }
  }
  return counts;
}

export function drawPlanBase(S,D){
  for(const r of D.rooms){
    S.add(`<g data-room-id="${r.id}" data-room-code="${esc(r.code)}">`);
    S.path(polyPath(r.poly),ROOM_FILL[r.id]||'#f4f4f0','none',0);
    S.add('</g>');
  }
}

function furniture(S,D){
  const drawn=[];
  const g=(id,fn)=>{S.add(`<g data-item-id="${esc(id)}">`);fn();S.add('</g>');drawn.push(id);};
  for(const it of D.items){
    if(it.kind==='wallcab'||it.storage||it.bath||it.bed)continue;
    const r=it.rect;
    switch(it.kind){
      case 'sofa':g(it.id,()=>S.rect(r,'#d9d2c4','#8e8571',.014,'rx=".05"'));break;
      case 'coffee':g(it.id,()=>S.rect(r,'#e6dfd0','#8e998e',.012,'rx=".08"'));break;
      case 'tv':g(it.id,()=>S.rect(r,'#ccd8df','#82949d',.012));break;
      case 'dining':g(it.id,()=>{
        const [x,z,X,Z]=r;S.rect(r,'#e8e1d3','#8e8571',.014);
        for(const v of [.2,.5,.8])for(const yy of [z-.23,Z+.03])S.rect([x+v*(X-x)-.17,yy,x+v*(X-x)+.17,yy+.20],'#f4f3ef','#a1aaa1',.01,'rx=".03"');
        for(const xx of [x-.23,X+.03])S.rect([xx,(z+Z)/2-.17,xx+.20,(z+Z)/2+.17],'#f4f3ef','#a1aaa1',.01,'rx=".03"');
      });break;
      case 'counter':g(it.id,()=>S.rect(r,it.id.includes('utility')?'#e7e8e2':'#e8e7df','#8e998e',.014));break;
      case 'fridge':g(it.id,()=>{S.rect(r,'#dfe3e6','#8e999b',.014);S.line([(r[0]+r[2])/2,r[1]],[(r[0]+r[2])/2,r[3]],'#a8b3b6',.01);});break;
      case 'bar':g(it.id,()=>S.rect(r,'#dbe6dd','#6f8d7c',.016));break;
      case 'basin':g(it.id,()=>{S.rect(r,'#dbe5e7','#66878d',.013);S.add(`<ellipse cx="${fx((r[0]+r[2])/2,4)}" cy="${fx((r[1]+r[3])/2,4)}" rx=".17" ry=".11" fill="#fff" stroke="#779199" stroke-width=".011"/>`);});break;
      case 'washer':g(it.id,()=>{S.rect(r,'#eef0ee','#8e999b',.013);S.add(`<circle cx="${fx((r[0]+r[2])/2,4)}" cy="${fx((r[1]+r[3])/2,4)}" r="${fx(Math.min(r[2]-r[0],r[3]-r[1])*.32,4)}" fill="#fff" stroke="#8e999b" stroke-width=".01"/>`);});break;
      case 'rug':g(it.id,()=>S.rect(r,'none','#b9ad98',.012,'stroke-dasharray=".08 .05"'));break;
      case 'plant':g(it.id,()=>S.add(`<circle cx="${fx(it.point[0],4)}" cy="${fx(it.point[1],4)}" r=".19" fill="#cfe2cb" stroke="#78937a" stroke-width=".012"/>`));break;
      default:throw new Error(`Plan has no drawing rule for item kind ${it.kind}`);
    }
  }
  return drawn;
}

function storage(S,D){
  const drawn=[],list=D.items.filter(i=>i.storage);
  for(const it of list.filter(i=>!/loft|overhead/.test(i.kind))){
    const s=it.storage,r=s.drawBounds,[x,z,X,Z]=r,w=X-x,d=Z-z;
    S.add(`<g data-storage-id="${esc(s.id)}" data-storage-kind="${esc(s.kind)}">`);
    S.rect(r,/wardrobe|cabinet/.test(s.kind)?'#dce4ef':'#e9edf0','#5b7795',.014);
    if(s.leaves){const lx=w>d;for(let i=1;i<s.leaves;i++)S.line(lx?[x+w*i/s.leaves,z]:[x,z+d*i/s.leaves],lx?[x+w*i/s.leaves,Z]:[X,z+d*i/s.leaves],'#90a3b9',.008);}
    S.add('</g>');drawn.push(s.id);
  }
  for(const it of list.filter(i=>/loft|overhead/.test(i.kind))){
    const s=it.storage;
    S.add(`<g data-storage-id="${esc(s.id)}" data-storage-kind="${esc(s.kind)}">`);
    S.rect(s.drawBounds,'none','#526d9a',.022,'stroke-dasharray=".07 .04"');S.add('</g>');drawn.push(s.id);
  }
  return drawn;
}

function bathFixtures(S,D){
  for(const b of D.baths){
    S.add(`<g data-bath-id="${esc(b.id)}">`);
    const s=b.shower,[x,z,X,Z]=s.rect_m;
    S.rect(s.rect_m,'#eef5f3','none',0);
    S.line([x,z],[X,z],'#6b9f99',.065);S.line([X,z],[X,Z],'#6b9f99',.065);
    S.line(...s.screen_segment_m,'#77a4b0',.025);
    const vr=b.vanity.rect_m;
    S.rect(vr,'#dbe5e7','#66878d',.013);
    S.add(`<ellipse cx="${fx((vr[0]+vr[2])/2,4)}" cy="${fx((vr[1]+vr[3])/2,4)}" rx=".20" ry=".13" fill="#fff" stroke="#779199" stroke-width=".012"/>`);
    S.rect(b.wc.cistern_rect_m,'#eef0ee','#8e999b',.013);S.rect(b.wc.bowl_rect_m,'#fff','#8e999b',.012,'rx=".16"');
    S.add('</g>');
  }
}

export function drawStairsLift(S,D){
  const st=D.stairs,out=[];
  for(const key of ['upper','landing','lower']){
    const r=st[key];S.add(`<g data-stair-part="${key}">`);S.rect(r,'#f1f3f1','#839693',.014);
    if(key!=='landing'){
      const n=key==='upper'?st.upperTreads:st.lowerTreads,alongX=(r[2]-r[0])>(r[3]-r[1]);
      for(let i=1;i<n;i++){const t=i/n;S.line(alongX?[r[0]+(r[2]-r[0])*t,r[1]]:[r[0],r[1]+(r[3]-r[1])*t],alongX?[r[0]+(r[2]-r[0])*t,r[3]]:[r[2],r[1]+(r[3]-r[1])*t],'#a1adab',.008);}
    }
    S.add('</g>');out.push(key);
  }
  const lw=D.walls.find(w=>w.id==='lift-west'),le=D.walls.find(w=>w.id==='lift-east'),ln=D.walls.find(w=>w.id==='lift-north');
  const lift=[lw.rect[2],ln.rect[3],le.rect[0],lw.rect[3]];
  S.add('<g data-lift="shaft">');S.rect(lift,'#eceeee','#8d9a9c',.012);
  S.line([lift[0],lift[1]],[lift[2],lift[3]],'#b3bcbd',.008);S.line([lift[2],lift[1]],[lift[0],lift[3]],'#b3bcbd',.008);S.add('</g>');
  return {stairs:out,lift};
}

function roomLabels(S,D){
  const pos={living:[2.7,11.65],dining:[2.9,5.1],kitchen:[2.85,3.2],master:[6.95,3.85],children:[7.55,12.6],utility:[2.75,.82],balcony:[1.9,15.2],dressing:[5.78,6.3],lobby:[5.55,8.05],bath1:[7.1,6.4],bath2:[7.1,8.2]};
  const title={living:'LIVING',dining:'DINING',kitchen:'KITCHEN',master:'MASTER BEDROOM',children:"CHILDREN'S BEDROOM",utility:'UTILITY + WASHING',balcony:'ENTRY / BALCONY',dressing:'DRESSING',lobby:'LOBBY',bath1:'TL1',bath2:'TL2'};
  for(const id of Object.keys(pos)){
    const r=D.rooms.find(r=>r.id===id),[x,z]=pos[id],small=['dressing','lobby','bath1','bath2'].includes(id);
    const code=id==='utility'?'R08 / R08a':r.code;
    S.add(`<g data-room-label="${id}">`);
    if(small){
      S.label(x,z,code,.09,'#203b43','middle','font-weight="600"');
      S.label(x,z+.12,title[id],.09,'#203b43','middle','font-weight="600"');
      if(r.nominal)S.label(x,z+.24,r.nominal,.075,'#266c5c');
    }else{
      S.label(x,z,`${code} ${title[id]}`.trim(),id==='living'?.14:.15,'#203b43','middle','font-weight="600"');
      if(r.nominal)S.label(x,z+.2,r.nominal,.115,'#266c5c');
    }
    S.add('</g>');
  }
}

function masterOverlay(S,D){
  const ML=D.ML,Z=ML.relationship_zones_m,band=Z.wardrobe_wall_band.rect,bay=Z.window_bay.rect,room=ML.frame.room_rect_m;
  const O=D.O;
  S.add(`<g id="master-relationship-overlay" data-decision-status="${esc(ML.decision_status)}" data-suppressed-storage="${esc(D.suppressedIds.join(' '))}">`);
  S.rect(band,'url(#zone)','#5b7795',.012,'stroke-dasharray=".06 .035"');
  S.rect(bay,'#fcfdfc','#5b7795',.012,'stroke-dasharray=".06 .035"');
  S.label((band[0]+bay[0])/2,band[1]+.30,'WARDROBE',.1,'#466c92');
  S.label((band[0]+bay[0])/2,band[1]+.43,'ZONE',.1,'#466c92');
  S.label((bay[2]+band[2])/2,band[1]+.30,'WARDROBE',.1,'#466c92');
  S.label((bay[2]+band[2])/2,band[1]+.43,'ZONE',.1,'#466c92');
  S.label((bay[0]+bay[2])/2,band[1]+.28,'W03 BAY',.095,'#466c92');
  S.label((band[0]+band[2])/2,band[3]+.15,'split wardrobe approved in principle; size unmeasured',.085,'#466c92');
  // TV marker on the east wall (sheet-left of the master), D02 end
  const tvZ=(ML.openings.W04.span_m[0]+ML.frame.room_rect_m[1])/2;
  S.line([room[0]+.05,tvZ-.4],[room[0]+.05,tvZ+.4],'#466c92',.05);
  S.label(room[0]+.15,tvZ+.03,'TV',.1,'#466c92','start');
  S.label(room[0]+.15,tvZ+.16,'east wall',.075,'#466c92','start');
  S.add('</g>');
  return {ids:D.suppressedIds,compass:{wardrobe:ML.relations.wardrobe_wall.compass_wall,headboard:ML.relations.headboard_wall.compass_wall,tv:ML.relations.tv_door_wall.compass_wall,dressing:ML.relations.dressing_wall.compass_wall}};
}

function tenantBeds(S,D){
  for(const b of D.tenantBeds){
    S.add(`<g data-item-id="${b.id}" data-bed="tenant-supplied">`);
    S.rect(b.king,'none','#6b7f95',.018,'stroke-dasharray=".08 .05"');
    S.rect(b.queen,'none','#6b7f95',.012,'stroke-dasharray=".03 .04"');
    const hx=b.king[2],cz=(b.king[1]+b.king[3])/2;
    for(const dz of [-.3,.3])S.rect([hx-.17,cz+dz-.2,hx-.04,cz+dz+.2],'#fff','#a7b4c1',.008,'rx=".03"');
    S.label((b.king[0]+b.king[2])/2-.05,cz-.05,"TENANT'S BED",.085,'#41597a');
    S.label((b.king[0]+b.king[2])/2-.05,cz+.07,'queen to king',.072,'#41597a');
    S.label((b.king[0]+b.king[2])/2-.05,cz+.17,'1524\u20131829 \u00d7 1981',.072,'#41597a');
    S.add('</g>');
  }
}

export function compassEdgeLabels(S,D,{tx=TX,ty=TY,sc=SC}={}){
  const xL=tx+.2277*sc,xR=tx+9.1464*sc,yT=ty,yB=ty+15.8526*sc,cx=(xL+xR)/2,cy=(yT+yB)/2;
  S.text(cx,yT-22,'SOUTH \u2191  utility / washing end (sheet-top)',15,'muted','middle');
  S.text(cx,yB+34,'NORTH \u2193  entrance / balcony / stairs end (sheet-bottom)',15,'muted','middle');
  S.add(`<text transform="translate(${xL-24} ${cy}) rotate(-90)" font-size="15" class="muted" text-anchor="middle">EAST \u2190  kitchen \u00b7 dining \u00b7 living (sheet-left)</text>`);
  S.add(`<text transform="translate(${xR+34} ${cy}) rotate(90)" font-size="15" class="muted" text-anchor="middle">WEST \u2192  bedrooms (sheet-right)</text>`);
}

export function buildPlan(D,{no,total}){
  const W=1700,H=2150;
  const S=makeSheet({width:W,title:'Furnished floor plan (top-down)',desc:'Read-only furnished floor plan generated from the canonical master; south-up with a north arrow.',
    metadata:{sheet:'01-plan-furnished',master_sha256:D.hash,orientation:D.O.sheet_to_compass,heights:'hd11_homeowner_stated_or_derived_unmeasured'}});
  pageHeader(S,{title:'Furnished floor plan \u2014 top-down',subtitle:'Hyderabad 2BHK \u00b7 one floor \u00b7 sheet drawn south-up (north arrow at right)',no,total,hash:D.hash});
  S.add(`<g id="house-plan" transform="translate(${TX} ${TY}) scale(${SC})">`);
  S.rect([0,0,D.plot.x*FT,D.plot.z*FT],'none','#b8c5c4',.012,'stroke-dasharray=".08 .06"');
  drawPlanBase(S,D);
  // balcony has no wall records except its south face; its other edges are drawn dashed
  const bal=D.rooms.find(r=>r.id==='balcony');
  S.rect(bal.rect,'none','#9bb398',.02,'stroke-dasharray=".10 .06"');
  const fur=furniture(S,D);
  const sto=storage(S,D);
  tenantBeds(S,D);
  const wc=drawWalls(S,D);
  bathFixtures(S,D);
  const sl=drawStairsLift(S,D);
  const mo=masterOverlay(S,D);
  roomLabels(S,D);
  S.label(4.95,12.75,'LIFT',.14,'#203b43');S.label(4.95,12.93,'(not elevated)',.08,'#5d7174');
  S.label(6.7,15.2,'STAIR',.15,'#203b43');
  S.label(8.3,14.3,'landing',.085,'#5d7174');
  {
    // No back or extension section is drawn while the HD-16 geometry hold is open.
    const pj=D.openings.find(o=>o.id==='pooja-niche'),pw=D.walls.find(w=>w.id===pj.wall),px=Math.max(pw.rect[0],pw.rect[2])+.12,pz=pj.span[0];
    S.add('<g data-pooja-callout="PN1">');
    S.label(px,pz+.12,'POOJA NICHE PN1',.12,'#4d3a5c','start','font-weight="700"');
    S.label(px,pz+.27,'built; front outline only (HD-16)',.075,'#4d3a5c','start','font-weight="700"');
    S.label(px,pz+.41,'estimated size / offset; depth held',.07,'#4d3a5c','start');
    S.label(px,pz+.52,'extension unmeasured / OI-POOJA-01',.07,'#4d3a5c','start');
    S.add('</g>');
  }
  const U=D.openings.find(o=>o.id==='utility-open');
  S.label((U.span[0]+U.span[1])/2,.06,'PARAPET OPENING \u2014 SOUTH WALL, no corner return (assumed)',.085,'#466c92');
  S.add('</g>');
  compassEdgeLabels(S,D);

  // right column
  const X0=1200,Y0=170;
  S.text(X0,Y0+20,'ROOM SCHEDULE',17,'sect');
  S.text(X0,Y0+44,'confirmed nominal sizes (feet-inches as printed)',13,'muted');
  let y=Y0+72;
  const rows=[...D.elevRooms.filter(r=>r.id!=='balcony'),D.elevRooms.find(r=>r.id==='balcony')];
  for(const r of rows){S.text(X0,y,r.code||'',14,'mono');S.text(X0+95,y,r.name,14);S.text(X0+290,y,r.nominal||'\u2014 (derived)',14,'mono green');y+=24;}
  S.text(X0,y,'R10',14,'mono');S.text(X0+95,y,'Lift (shaft, interior not elevated)',14);y+=34;

  S.text(X0,y,'LEGEND',17,'sect');y+=14;
  const sw=(kind,label)=>{
    y+=26;
    if(kind==='wall')S.add(`<rect x="${X0}" y="${y-13}" width="34" height="9" fill="${WALL}"/>`);
    if(kind==='win')S.add(`<path d="M${X0} ${y-8}H${X0+34}" stroke="#31818d" stroke-width="4"/>`);
    if(kind==='door')S.add(`<path d="M${X0} ${y-2}H${X0+30}" stroke="#405f7e" stroke-width="2"/><path d="M${X0} ${y-2}A30 30 0 0 1 ${X0+30} ${y-30}" fill="none" stroke="#8095aa"/>`);
    if(kind==='open')S.add(`<path d="M${X0} ${y-8}H${X0+34}" stroke="#466c92" stroke-width="4" stroke-dasharray="9 5"/>`);
    if(kind==='niche')S.add(`<rect x="${X0}" y="${y-18}" width="34" height="14" fill="${WALL}"/><path d="M${X0+5} ${y-4}H${X0+29}" stroke="#d3b8e5" stroke-width="4" stroke-dasharray="5 3"/>`);
    if(kind==='snich')S.add(`<path d="M${X0} ${y-8}H${X0+34}" stroke="#786385" stroke-width="6" stroke-dasharray="5 3"/>`);
    if(kind==='zone')S.add(`<rect x="${X0}" y="${y-18}" width="34" height="16" fill="url(#zone)" stroke="#5b7795" stroke-dasharray="5 3" transform="scale(1)"/>`);
    if(kind==='loft')S.add(`<rect x="${X0}" y="${y-18}" width="34" height="16" fill="none" stroke="#526d9a" stroke-width="2" stroke-dasharray="7 4"/>`);
    if(kind==='bed')S.add(`<rect x="${X0}" y="${y-18}" width="34" height="16" fill="none" stroke="#6b7f95" stroke-width="2" stroke-dasharray="7 4"/>`);
    if(kind==='joinery')S.add(`<rect x="${X0}" y="${y-18}" width="34" height="16" fill="#dce4ef" stroke="#5b7795"/>`);
    if(kind==='feature')S.add(`<rect x="${X0}" y="${y-18}" width="34" height="16" fill="#eef5f3" stroke="#6b9f99" stroke-width="3"/>`);
    S.text(X0+48,y-4,label,14);
  };
  sw('wall','Wall (as recorded in the master)');
  sw('win','Window / glazed panel');
  sw('door','Door with swing (dashed = closed leaf)');
  sw('open','Parapet opening UP1 (assumed, no corner return)');
  sw('niche','Pooja PN1: estimated front only; no back drawn');
  sw('snich','Shower niche SN1 / SN2 (dotted)');
  sw('joinery','Built storage record (hinged / counters)');
  sw('loft','Loft / overhead (dashed outline)');
  sw('zone','Split wardrobe in principle \u2014 unmeasured zones');
  sw('bed',"Tenant's own bed: queen\u2013king envelope");
  sw('feature','Shower wet-area walls (kit-kat tile)');
  y+=26;
  S.text(X0,y,'NOTES',17,'sect');y+=10;
  const notes=[
    COMPASS_NOTE,COMPASS_SOURCE,
    HEIGHT_NOTE+' This sheet draws no heights; elevations and the ceiling plan label each as homeowner-stated, derived or assumed.',
    'Room sizes are the homeowner-confirmed nominal sizes. Wall and opening positions are the master\u2019s assembled geometry; the master records which are inferred or unmeasured, and most opening offsets are inherited or placeholder (modelled plan position; not site verified).',
    'D01 is single-leaf in the model, while the architectural description says double-leaf; confirm on site. W03 (master window): centred (homeowner-confirmed); offsets unmeasured. W05 (children\u2019s window): placeholder concealed behind the curtain. UP1 (utility parapet opening, OI-UTL-01): assumed.',
    'Beds are the tenants\u2019 own: dashed queen-to-king mattress envelope, 1524\u20131829 \u00d7 1981 mm; no tenant frame is drawn. Fixed bedside cabinets are omitted by the homeowner (HD-14: ST-R04-NS01, ST-R04-NS02, ST-R05-NS01); tenants may use movable tables. Room and bed positions are unchanged.',
    D.r05ClearanceNote,
    'Master split wardrobe is approved in principle; its hatched zones, compartments and loft remain unmeasured. The five superseded ST-R04 records are not drawn. Dressing and utility cabinets are selected conditionally, subject to FH-ST-03 / FH-ST-12 site checks.',
    POOJA_NOTE,
    'The lift interior and the stair are drawn in plan only. Tags W/D/G/V are opening codes used on the elevation sheets; PN1 (pooja niche), SN1/SN2 (shower niches) and UP1 are tagged on the elevations.'
  ];
  for(const n of notes){y=S.wrap(X0,y+14,n,440,13,18,'muted');y+=2;}
  northArrow(S,X0+60,y+80,40);
  S.text(X0+120,y+70,'Approx. north points to sheet-bottom.',14,'muted');
  S.text(X0+120,y+90,'The drawing is not rotated.',14,'muted');
  y+=140;
  const bottom=Math.max(y,TY+15.85*SC+80);
  pageFooter(S,bottom+50,D.hash);
  const svg=S.finish(bottom+50);
  return {id:'01-plan-furnished',title:'Furnished floor plan (top-down)',svg,
    counts:{rooms:D.rooms.length,walls:wc.walls,openings:wc.openings,storageDrawn:sto.length,storageSuppressed:D.suppressedIds.length,furniture:fur.length,tenantBeds:D.tenantBeds.length,stairParts:sl.stairs.length,baths:D.baths.length},
    drawn:{storage:sto,furniture:fur,suppressed:mo.ids}};
}
