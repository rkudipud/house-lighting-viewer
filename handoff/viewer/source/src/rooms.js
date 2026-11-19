import * as T from 'three';

export function buildRooms(c){
  const {m,PLAN,FT,metresRect,box,cylinder,ball,slab,solid,line,v,world,collision,planeGeo,chair,panelFrame}=c;
  const rec=kind=>PLAN.furniture.filter(f=>f.kind===kind);
  const zones=new T.Group();zones.userData.noMerge=true;world.add(zones);
  const closedJoinery=new T.Group(),interiors=new T.Group();
  closedJoinery.userData.noMerge=true;closedJoinery.visible=false;interiors.userData.noMerge=true;interiors.visible=true;
  world.add(closedJoinery,interiors);
  const interiorRecords=[];
  const proposal=PLAN.wardrobeInteriors?.rooms;
  if(!proposal)throw new Error('Provisional wardrobe proposal is missing');
  const targets={
    'MBR-wardrobe-left':['R04','A',1],'MBR-wardrobe-right':['R04','B',1],
    'ST-R05-WR01':['R05','C',1],'ST-R04a-WR01':['R04a','D',1],
    'ST-R08-UC01':['R08','U',-1],'ST-R09-SH01':['R09','S',1]
  };
  function drawInterior(id,rect,lo,hi){
    const [roomId,sectionId,frontSign]=targets[id],room=proposal[roomId],section=room.sections.find(s=>s.id===sectionId);
    if(!section)throw new Error(`Missing provisional wardrobe section ${roomId}/${sectionId}`);
    const [x,z,X,Z]=rect,wide=X-x>=Z-z,u0=wide?x:z,u1=wide?X:Z,d0=wide?z:x,d1=wide?Z:X;
    const back=frontSign>0?d0:d1,front=frontSign>0?d1:d0,depth=d1-d0,total=section.bays.reduce((n,b)=>n+b.clear_width_mm,0);
    const part=(u,y,d,w,h,thick,mat=m.cabinet)=>wide
      ?box(u,y,d,w,h,thick,mat,interiors)
      :box(d,y,u,thick,h,w,mat,interiors);
    const panel=.016,centreD=(d0+d1)/2;
    part((u0+u1)/2,(lo+hi)/2,back+frontSign*panel/2,u1-u0,hi-lo,panel,m.wood);
    for(const u of [u0+panel/2,u1-panel/2])part(u,(lo+hi)/2,centreD,panel,hi-lo,depth,m.cabinet);
    for(const y of [lo+panel/2,hi-panel/2])part((u0+u1)/2,y,centreD,u1-u0,panel,depth,m.cabinet);
    let cursor=u0;
    const features=[];
    for(const [index,bay] of section.bays.entries()){
      const end=index===section.bays.length-1?u1:cursor+(u1-u0)*bay.clear_width_mm/total;
      const middle=(cursor+end)/2,width=Math.max(.02,end-cursor-panel);
      if(index)part(cursor,(lo+hi)/2,centreD,panel,hi-lo,depth,m.cabinet);
      for(const mm of bay.shelf_heights_ffl_mm){
        const y=mm/1000;
        if(y<=lo||y>=hi)throw new Error(`Shelf outside proposed cabinet ${id}/${bay.id}`);
        part(middle,y,centreD,width,panel,Math.max(panel,depth-panel),m.cabinet);
      }
      for(const mm of bay.rail_heights_ffl_mm){
        const y=mm/1000;
        if(y<=lo||y>=hi)throw new Error(`Rail outside proposed cabinet ${id}/${bay.id}`);
        const a=wide?v(cursor+.035,y,centreD):v(centreD,y,cursor+.035);
        const b=wide?v(end-.035,y,centreD):v(centreD,y,end-.035);
        line(a,b,.009,m.steel,interiors);
      }
      for(const [kind,ranges] of [['drawer',bay.drawers_ffl_mm],['pullout',bay.pullouts_ffl_mm]]){
        for(const [a,b] of ranges){
          const y0=a/1000,y1=b/1000;
          if(y0<lo||y1>hi||y1<=y0)throw new Error(`${kind} outside proposed cabinet ${id}/${bay.id}`);
          const y=(y0+y1)/2;
          part(middle,y,front-frontSign*.012,width,(y1-y0)-.008,.024,kind==='drawer'?m.cabinet:m.wood);
          const d=front+frontSign*.006;
          const start=wide?v(middle-.05,y,d):v(d,y,middle-.05);
          const endHandle=wide?v(middle+.05,y,d):v(d,y,middle+.05);
          line(start,endHandle,.004,m.steel,interiors);
        }
      }
      features.push({id:bay.id,kind:bay.kind,shelves:bay.shelf_heights_ffl_mm.length,rails:bay.rail_heights_ffl_mm.length,
        drawers:bay.drawers_ffl_mm.length,pullouts:bay.pullouts_ffl_mm.length});
      cursor=end;
    }
    interiorRecords.push({target:id,room:roomId,section:sectionId,rect,features,unmeasured:true});
  }
  const renderedItems=[];
  const notice=(text,x,y,z,width=.9)=>{
    const cv=document.createElement('canvas');cv.width=768;cv.height=80;const ctx=cv.getContext('2d');
    ctx.fillStyle='rgba(49,56,51,.88)';ctx.fillRect(0,0,768,80);ctx.fillStyle='#fff';ctx.textAlign='center';ctx.font='27px Segoe UI';ctx.fillText(text,384,53);
    const tex=new T.CanvasTexture(cv);tex.colorSpace=T.SRGBColorSpace;
    const label=new T.Sprite(new T.SpriteMaterial({map:tex,transparent:true}));label.position.set(x,y,z);label.scale.set(width,.12,1);world.add(label);
  };
  const outline=(rect,y,color,parent=zones)=>{
    const [x,z,X,Z]=rect,g=new T.BufferGeometry().setFromPoints([v(x,y,z),v(X,y,z),v(X,y,Z),v(x,y,Z),v(x,y,z)]);
    const o=new T.Line(g,new T.LineDashedMaterial({color,dashSize:.065,gapSize:.045}));o.computeLineDistances();parent.add(o);return o;
  };
  for(const b of PLAN.relationshipBands||[]){
    outline(b.rect,.035,'#727f8c');
    const [x,z,X,Z]=b.rect;
    const marker=box((x+X)/2,1.05,(z+Z)/2,X-x,2.1,Z-z,new T.MeshStandardMaterial({color:'#b8b2a5',transparent:true,opacity:.62,depthWrite:false}),zones);
    marker.castShadow=false;marker.name=b.id;
    if(targets[b.id]){marker.visible=false;drawInterior(b.id,b.rect,0,2.1);}
    const cv=document.createElement('canvas');cv.width=768;cv.height=96;const ctx=cv.getContext('2d');
    ctx.fillStyle='rgba(39,53,48,.85)';ctx.fillRect(0,0,768,96);ctx.fillStyle='#fff';ctx.textAlign='center';ctx.font='27px Segoe UI';
    ctx.fillText('WARDROBE CONCEPT - MEASURE ON SITE',384,61);
    const tex=new T.CanvasTexture(cv);tex.colorSpace=T.SRGBColorSpace;
    const label=new T.Mesh(new T.PlaneGeometry(Math.min(1.25,X-x-.04),.16),new T.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false,side:T.DoubleSide}));
    label.position.set((x+X)/2,1.78,Z+.004);label.visible=!targets[b.id];zones.add(label);
    renderedItems.push({id:b.id,rect:b.rect,relationshipOnly:true});
  }
  for(const b of PLAN.tenantBeds||[]){
    const [x,z,X,Z]=b.queen,w=Z-z,d=X-x,g=new T.Group();g.position.set((x+X)/2,0,(z+Z)/2);g.rotation.y=-Math.PI/2;world.add(g);
    collision.push({x0:x,z0:z,x1:X,z1:Z,y0:0,y1:.65,kind:'furniture',id:b.id});
    box(0,.24,0,w,.38,d,m.wood,g,true);box(0,.48,0,w,.20,d,m.fabric,g,true);
    for(const side of [-1,1])box(side*w*.24,.63,-d/2+.30,w*.40,.13,.40,m.fabric,g,true);
    box(0,.595,.36,w,.03,d*.40,m.accent,g,true);
    outline(b.king,.034,'#7c8b91');
    renderedItems.push({id:b.id,rect:b.queen,king:b.king,tenantSupplied:true,head:'sheet-right'});
  }
  for(const s of PLAN.storageItems||[]){
    const [x,z,X,Z]=s.rect,[lo,sourceHi]=s.height,wide=X-x>=Z-z;
    if(![x,z,X,Z,lo,sourceHi].every(Number.isFinite))throw new Error('Missing active storage geometry '+s.id);
    const ceiling={R04a:PLAN.levels.band,R05:PLAN.levels.band,R08:PLAN.levels.utility}[s.room];
    const hi=s.kind.includes('loft')&&Number.isFinite(ceiling)?Math.min(sourceHi,ceiling-.005):sourceHi;
    if(hi<=lo)throw new Error('Storage display height is invalid '+s.id);
    const topOnly=s.kind==='study_desk_floating'||s.kind==='tv_console_floating';
    const bottom=topOnly?hi-.035:lo;
    const parent=targets[s.id]?closedJoinery:world;
    box((x+X)/2,(bottom+hi)/2,(z+Z)/2,X-x,hi-bottom,Z-z,topOnly?m.wood:m.cabinet,parent);
    collision.push({x0:x,z0:z,x1:X,z1:Z,y0:bottom,y1:hi,kind:'furniture',id:s.id});
    if(!topOnly){
      const n=Math.max(1,Math.ceil((wide?X-x:Z-z)/.6));
      for(let i=1;i<n;i++)if(wide)box(x+i*(X-x)/n,(lo+hi)/2,Z+.002,.006,hi-lo,.004,m.groove,parent);
      else box(X+.002,(lo+hi)/2,z+i*(Z-z)/n,.004,hi-lo,.006,m.groove,parent);
    }
    if(targets[s.id])drawInterior(s.id,s.rect,lo,hi);
    if(s.kind==='tv_console_floating')box(X-.03,1.20,(z+Z)/2,.035,.55,Math.min(.95,Z-z),m.screen);
    if(s.kind.includes('loft')){
      notice('H-LOFT / SITE CHECK',(x+X)/2,hi-.12,(z+Z)/2);
    }
    if(s.homeownerSelection){
      if(s.homeownerSelection.constructionRelease!==false)throw new Error('Conditional cabinet lost its construction hold '+s.id);
      notice(`SELECTED / UNMEASURED - ${s.room==='R04a'?'FH-ST-03':'FH-ST-12'}`,(x+X)/2,(lo+hi)/2,(z+Z)/2,1.05);
    }
    renderedItems.push({id:s.id,rect:s.rect,height:[lo,hi],sourceHeight:s.height,displayOnlyClip:hi<sourceHi,hold:s.kind.includes('loft')?'H-LOFT':null,homeownerSelection:s.homeownerSelection});
  }
  for(const f of rec('wardrobeZone')){
    const [x,z,X,Z]=metresRect(f.rect),g=new T.BufferGeometry().setFromPoints([
      v(x,.034,z),v(X,.034,z),v(X,.034,Z),v(x,.034,Z),v(x,.034,z)]);
    const outline=new T.Line(g,new T.LineDashedMaterial({color:'#738078',transparent:true,opacity:.38,dashSize:.08,gapSize:.06}));
    outline.computeLineDistances();zones.add(outline);
    const cv=document.createElement('canvas');cv.width=1024;cv.height=100;
    const ctx=cv.getContext('2d');ctx.fillStyle='rgba(78,93,83,.64)';ctx.font='32px Segoe UI';ctx.textAlign='center';
    ctx.fillText('Wardrobe concept - measure on site',512,60);
    const tex=new T.CanvasTexture(cv);tex.colorSpace=T.SRGBColorSpace;
    const label=new T.Mesh(new T.PlaneGeometry(Math.min(1.7,Math.max(X-x,Z-z)-.06),.16),new T.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false,side:T.DoubleSide}));
    label.rotation.x=-Math.PI/2;if(Z-z>X-x)label.rotation.z=Math.PI/2;
    label.position.set((x+X)/2,.036,(z+Z)/2);zones.add(label);
  }
  let breakfast;
  for(const f of rec('kitchen')){
    const top=.9;
    for(const r of [f.left,f.top]){
      const [x,z,X,Z]=metresRect(r),vertical=Z-z>X-x;
      solid(r,.495,.75,m.cabinet);slab(r,top-.015,.03,m.stone);
      slab(r,.06,.12,m.black);
      const len=vertical?Z-z:X-x,n=Math.ceil(len/.6);
      for(let i=1;i<n;i++){
        if(vertical)box(X+.001,.49,z+i*len/n,.003,.72,.006,m.groove);
        else box(x+i*len/n,.49,Z+.001,.006,.72,.003,m.groove);
      }
    }
    const l=metresRect(f.left),t=metresRect(f.top),hx=(l[0]+l[2])/2,hz=9*FT,sz=13.2*FT;
    box(l[0]+.01,1.2,(l[1]+l[3])/2,.02,.6,l[3]-l[1],m.stone);
    box((t[0]+t[2])/2,1.2,t[1]+.01,t[2]-t[0],.6,.02,m.stone);
    for(const r of [[8.95,5.17,11.266,6.35],[2.249,5.25,3.42,7.75]])slab(r,1.86,.72,m.cabinet);
    solid(f.fridge,1.02,2.04,m.black);
    const fr=metresRect(f.fridge);
    box(fr[0]-.015,1.04,(fr[1]+fr[3])/2,.03,.56,.018,m.steel);
    box(hx,top+.006,hz,.50,.018,.62,m.black);
    for(const xx of [-.14,.14])for(const zz of [-.18,.18])cylinder(hx+xx,top+.026,hz+zz,.07,.013,m.steel);
    box(l[0]+.19,1.92,hz,.38,.09,.72,m.steel);box(l[0]+.1,2.19,hz,.20,.48,.27,m.steel);
    box(hx,top+.006,sz,.47,.02,.59,m.steel);box(hx,top+.018,sz,.37,.025,.45,m.black);
    line(v(l[0]+.08,top+.01,sz),v(l[0]+.08,top+.34,sz),.014,m.steel);line(v(l[0]+.08,top+.34,sz),v(hx,top+.34,sz),.014,m.steel);
    const [x,z,X,Z]=metresRect(f.bar),cx=(x+X)/2,cz=(z+Z)/2;
    solid(f.bar,f.barH-.015,.03,m.stone);
    for(const xx of [x+.025,X-.025])box(xx,(f.barH-.03)/2,cz,.03,f.barH-.03,.52,m.cabinet);
    for(const xx of [cx-.43,cx+.43]){
      cylinder(xx,.62,Z-.20,.17,.05,m.wood);
      for(const dx of [-.11,.11])for(const dz of [-.11,.11])box(xx+dx,.30,Z-.20+dz,.025,.60,.025,m.metalDark);
    }
    breakfast={width:X-x,depth:Z-z,height:f.barH,eastClearance:16.256*FT-X,fridgePlaneClearance:fr[0]-X,stools:2};
  }
  for(const f of rec('bed')){
    const [x,z,X,Z]=metresRect(f.rect),cx=(x+X)/2,cz=(z+Z)/2,west=f.head==='west';
    const w=west?Z-z:X-x,d=west?X-x:Z-z,g=new T.Group();g.position.set(cx,0,cz);g.rotation.y=west?Math.PI/2:0;world.add(g);
    collision.push({x0:x,z0:z,x1:X,z1:Z,y0:0,y1:.65,kind:'furniture'});
    box(0,.23,0,w,.38,d,m.wood,g,true);box(0,.46,0,w-.06,.22,d-.06,m.fabric,g,true);
    box(0,.85,-d/2+.06,w+.12,1.1,.12,m.fabric,g,true);
    for(const side of [-1,1]){
      box(side*w*.24,.63,-d/2+.43,w*.40,.16,.40,m.fabric,g,true);
      if((f.tables??[-1,1]).includes(side))box(side*(w/2+.27),.4,-d/2+.4,.38,.055,.38,m.wood,g);
    }
    box(0,.60,.38,w,.055,d*.44,m.accent,g,true);
  }
  for(const f of rec('study')){
    const [x,z,X,Z]=metresRect(f.rect),cx=(x+X)/2;
    solid(f.rect,f.topH-.015,.03,m.wood);
    for(const xx of [x+.025,X-.025])box(xx,(f.topH-.03)/2,(z+Z)/2,.03,f.topH-.03,.5,m.cabinet);
    box(cx,.76,Z-.3,.32,.02,.23,m.black);box(cx,.94,Z-.18,.5,.30,.018,m.screen);chair(cx,z-.1,Math.PI);
  }
  for(const f of rec('vanity')){
    if(f.rect[1]<4)continue;
    const [x,z,X]=metresRect(f.rect),cx=(x+X)/2;
    box(cx,.80,z+.23,.75,.05,.46,m.stone);
    collision.push({x0:cx-.375,z0:z,x1:cx+.375,z1:z+.46,y0:.77,y1:.92,kind:'furniture'});
    ball(cx,.86,z+.25,.19,.075,.19,m.white);
    cylinder(cx,.97,z+.05,.011,.3,m.steel);box(cx,1.11,z+.11,.016,.016,.12,m.steel);
    panelFrame(cx,1.4,z+.03,.6,.76,0,m.steel,.012,.018);
    const mir=new T.Mesh(planeGeo,m.mirror);mir.scale.set(.6,.76,1);mir.position.set(cx,1.4,z+.022);world.add(mir);
  }
  for(const f of rec('utilityShelf')){
    const [x,z,X,Z]=metresRect(f.counter),cx=(x+X)/2,cz=(z+Z)/2,dep=X-x,w=Z-z;
    const uc=PLAN.storageItems.find(s=>s.id==='ST-R08-UC01');
    if(uc){
      if(Math.max(...uc.rect.map((n,i)=>Math.abs(n-[x,z,X,Z][i])))>.002)throw new Error('Utility counter and canonical UC01 footprints differ');
    }else solid(f.counter,f.counterH/2,f.counterH-.05,m.paintedSlab);
    box(cx,f.counterH-.025,cz,dep,.05,w,m.concrete);box(cx,f.shelfH-.05,cz,dep,.10,w,m.concrete);
    ball(cx,f.counterH+.05,cz,.19,.07,.19,m.white);
    cylinder(X-.07,f.counterH+.15,cz,.012,.2,m.steel);box(X-.14,f.counterH+.25,cz,.14,.014,.014,m.steel);
  }
  for(const f of rec('washer')){
    const [x,z,X,Z]=metresRect(f.rect),cx=(x+X)/2;
    solid(f.rect,.45,.88,m.white,true);
    const drum=cylinder(cx,.43,Z+.016,.21,.04,m.black);drum.rotation.x=Math.PI/2;
    const glass=cylinder(cx,.43,Z+.041,.165,.014,m.glass);glass.rotation.x=Math.PI/2;
    box(cx,.77,Z+.02,(X-x)*.86,.085,.02,m.steel);
    box(5.2*FT,.018,2.4*FT,.14,.01,.14,m.steel);
  }
  if(interiorRecords.length!==Object.keys(targets).length)throw new Error('Not all provisional cabinet sections have a model footprint');
  const wardrobeProposals={interior:interiors,closed:closedJoinery,records:interiorRecords};
  return {wardrobeZones:zones,wardrobeProposals,breakfast,renderedItems};
}
