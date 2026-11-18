import * as T from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { PLAN,FT,metresRect } from './geometry.js';
import { ceilingPlan,cornerPath,diagonalRadii } from './ceilings.js';
import { buildCeilings } from './ceilingMeshes.js';
import { buildFixtures } from './fixtureMeshes.js';
import { buildHall } from './hall.js';
import { buildRooms } from './rooms.js';
import { buildBaths } from './baths.js';
import { roomFloorRegions } from './master-adapter.js';

export function createModel(scene,materials) {
  const {m}=materials, world=new T.Group(), ceiling=new T.Group(), neighbours=new T.Group(), labels=new T.Group(),fans=new T.Group(),markers=new T.Group();
  const lights=new T.Group(),grooves=new T.Group(),rcp=new T.Group(),feature=new T.Group();
  const collision=[],floors=[],shadowObjects=[],emission=[];
  const frames=[],variants={};
  let cornerStyle=PLAN.design.cornerStyle;
  const H=PLAN.heights.soffit.value;
  // Animated or toggled parts live in noMerge groups under `world`, so view toggles keep working but the static mesh merge skips them.
  const dynamic=new T.Group();dynamic.userData.noMerge=true;world.add(dynamic);
  let mainDoor=null;
  const doors=[];
  m.greyCurtain=new T.MeshStandardMaterial({color:'#a7a29a',roughness:.95,side:T.DoubleSide});
  scene.add(world,ceiling,lights,grooves,rcp,feature,neighbours,labels,fans,markers);markers.visible=false;
  const boxGeo=new T.BoxGeometry(1,1,1),roundGeo=new RoundedBoxGeometry(1,1,1,2,.08),sphereGeo=new T.SphereGeometry(1,12,8);
  const cylinderCache=new Map();
  function mesh(geo,mat,x,y,z,sx=1,sy=1,sz=1,parent=world,cast=true){
    const o=new T.Mesh(geo,mat);o.position.set(x,y,z);o.scale.set(sx,sy,sz);o.castShadow=cast;o.receiveShadow=true;parent.add(o);return o;
  }
  function box(x,y,z,w,h,d,mat=m.wood,parent=world,rounded=false){return mesh(rounded?roundGeo:boxGeo,mat,x,y,z,w,h,d,parent);}
  function slab(rect,y,h,mat,parent=world){const [x,z,X,Z]=metresRect(rect);return box((x+X)/2,y,(z+Z)/2,X-x,h,Z-z,mat,parent);}
  function cylinder(x,y,z,r,h,mat=m.wood,rt=r,parent=world){
    const key=`${rt/r}`;if(!cylinderCache.has(key))cylinderCache.set(key,new T.CylinderGeometry(rt/r,1,1,16));
    return mesh(cylinderCache.get(key),mat,x,y,z,r,h,r,parent);
  }
  function ball(x,y,z,sx,sy,sz,mat,parent=world){return mesh(sphereGeo,mat,x,y,z,sx,sy,sz,parent);}
  function solid(rect,y,h,mat=m.wood,rounded=false){
    const [x,z,X,Z]=metresRect(rect);box((x+X)/2,y,(z+Z)/2,X-x,h,Z-z,mat,world,rounded);
    collision.push({x0:x,z0:z,x1:X,z1:Z,y0:y-h/2,y1:y+h/2,kind:'furniture'});
  }
  function setBathDoor(id,open){
    const d=doors.find(d=>d.id===id);
    if(!d)throw new Error('Unknown bathroom door: '+id);
    d.open=Boolean(open);d.pivot.rotation.y=d.open?d.sign*Math.PI/2:0;
    d.pivot.updateMatrixWorld(true);
    for(const [object,body] of d.colliders){
      const bounds=new T.Box3().setFromObject(object);
      Object.assign(body,{x0:bounds.min.x,z0:bounds.min.z,x1:bounds.max.x,z1:bounds.max.z,y0:bounds.min.y,y1:bounds.max.y});
    }
  }
  function line(a,b,r,mat,parent=world){
    const dir=new T.Vector3().subVectors(b,a),o=cylinder((a.x+b.x)/2,(a.y+b.y)/2,(a.z+b.z)/2,r,dir.length(),mat,r,parent);
    o.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),dir.normalize());return o;
  }
  const v=(x,y,z)=>new T.Vector3(x,y,z);
  function pleatedCurtain(a,b,bottom,top,face,alongX,sign,mat,amplitude,folds){
    const segments=Math.max(24,Math.ceil(folds*12)),rows=5,pos=[],uv=[],idx=[];
    for(let j=0;j<=rows;j++)for(let i=0;i<=segments;i++){
      const u=i/segments,t=j/rows,along=a+(b-a)*u,y=bottom+(top-bottom)*t;
      const depth=face+sign*amplitude*Math.cos(u*folds*Math.PI*2)*(1-.16*(1-t));
      pos.push(...(alongX?[along,y,depth]:[depth,y,along]));uv.push(u,t);
    }
    for(let j=0;j<rows;j++)for(let i=0;i<segments;i++){
      const a0=j*(segments+1)+i,b0=a0+segments+1;idx.push(a0,b0,a0+1,a0+1,b0,b0+1);
    }
    const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(pos,3));
    g.setAttribute('uv',new T.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
    const panel=new T.Mesh(g,mat);panel.castShadow=false;panel.receiveShadow=true;world.add(panel);return panel;
  }
  // Emissive and additive-decal materials are cached per room/channel/gain so merged meshes stay merged and the lighting engine drives each once.
  const glowCache=new Map(),decalCache=new Map();
  const glowMat=(room,layer,gain=2.2,color='#f1ece0',circuit=null)=>{
    const key=`${room}|${layer}|${gain}|${color}|${circuit}`;if(glowCache.has(key))return glowCache.get(key);
    const a=new T.MeshStandardMaterial({color,emissive:'#000',emissiveIntensity:.01,roughness:.55});
    emission.push({room,layer,circuit,mat:a,gain});glowCache.set(key,a);return a;
  };
  const decalMat=(room,layer,tex='glowEdge',gain=1,circuit=null,vertexColors=false)=>{
    const key=`${room}|${layer}|${tex}|${gain}|${circuit}|${vertexColors}`;if(decalCache.has(key))return decalCache.get(key);
    if(!materials.textures[tex])throw new Error('Missing glow texture '+tex);
    const a=new T.MeshBasicMaterial({map:materials.textures[tex],color:'#000',transparent:true,blending:T.AdditiveBlending,depthWrite:false,toneMapped:false,side:T.DoubleSide,polygonOffset:true,polygonOffsetFactor:-2,polygonOffsetUnits:-2,vertexColors});
    emission.push({room,layer,circuit,mat:a,kind:'decal',gain});decalCache.set(key,a);return a;
  };
  const registerDecal=(room,layer,circuit,mat,gain)=>{emission.push({room,layer,circuit,mat,kind:'decal',gain});return mat;};
  const planeGeo=new T.PlaneGeometry(1,1);planeGeo.setAttribute('uv1',planeGeo.attributes.uv.clone());
  function floorRect(rect,room,wet=false,role='nominal'){
    const [x,z,X,Z]=metresRect(rect),a=materials.floor(X-x,Z-z,wet),o=mesh(planeGeo,a,(x+X)/2,.015,(z+Z)/2,X-x,Z-z,1);
    o.rotation.x=-Math.PI/2;o.castShadow=false;o.userData.geometryRole=role;floors.push({room,rect,role,mesh:o,mat:a});
  }
  slab([.747,0,30.008,52.01],-.12,.24,m.stone);
  for(const r of PLAN.rooms){
    for(const region of roomFloorRegions(r))floorRect(region.rect,r.id,r.wet,region.role);
  }
  floorRect([11.247,44.005,24.998,48.012],'balcony',true);

  for(const wall of PLAN.walls){
    const ops=PLAN.openings.filter(o=>o.wall===wall.id).sort((a,b)=>a.span[0]-b.span[0]);
    const [x0,z0,x1,z1]=wall.rect,alongX=x1-x0>z1-z0,start=alongX?x0:z0,end=alongX?x1:z1;
    function part(a,b,lo,hi){
      if(b<=a||hi<=lo)return;
      const r=alongX?[a,z0,b,z1]:[x0,a,x1,b];slab(r,(lo+hi)/2,hi-lo,m.wall);
      const [x,z,X,Z]=metresRect(r);
      if(lo<1.7)collision.push({x0:x,z0:z,x1:X,z1:Z,y0:lo,y1:hi,kind:'wall'});
      if(lo===0){
        slab(r,.045,.09,m.wall);
      }
    }
    const thick=(alongX?z1-z0:x1-x0)*FT;
    const openingHeight=o=>[
      o.kind==='door'?0:(o.sillValue??PLAN.heights[o.sill||'windowSill'].value),
      o.headValue??(o.main?PLAN.heights.mainDoor.value:PLAN.heights.door.value),
    ];
    const cuts=[...new Set([start,end,...ops.flatMap(o=>o.span)])].sort((a,b)=>a-b);
    for(let i=1;i<cuts.length;i++){
      const a=cuts[i-1],b=cuts[i],mid=(a+b)/2,active=ops.filter(o=>mid>o.span[0]&&mid<o.span[1]&&!(o.kind==='niche'&&PLAN.pooja.frontOnly));
      const heights=[...new Set([0,H,...active.flatMap(openingHeight)])].sort((a,b)=>a-b);
      for(let j=1;j<heights.length;j++){
        const lo=heights[j-1],hi=heights[j],y=(lo+hi)/2;
        if(!active.some(o=>{const [s,h]=openingHeight(o);return y>s&&y<h;}))part(a,b,lo,hi);
      }
    }
    for(const o of ops){
      const [sill,head]=openingHeight(o);
      const a=o.span[0]*FT,b=o.span[1]*FT,cross=(alongX?(z0+z1)/2:(x0+x1)/2)*FT;
      const openW=b-a;
      function local(u,y,w,h,d,mat,offset=0,parent=world){
        return alongX?box(u,y,cross+offset,w,h,d,mat,parent):box(cross+offset,y,u,d,h,w,mat,parent);
      }
      if(o.kind==='niche'){
        if(PLAN.pooja.frontOnly)continue;
        const remaining=thick-PLAN.pooja.depthMm/1000;
        local((a+b)/2,(sill+head)/2,openW,head-sill,remaining,m.wall,-(thick-remaining)/2);
        continue;
      }
      if(o.kind==='bath-niche'){
        const remaining=thick-o.depthM;
        if(remaining<=0)throw new Error(`${o.id}: niche exceeds wall thickness`);
        local((a+b)/2,(sill+head)/2,openW,head-sill,remaining,m.wall,o.depthM/2);
        continue;
      }
      if(o.kind==='open'){
        // Open-air utility: parapet with a concrete coping, no glazing, raw lintel above.
        local((a+b)/2,sill+.02,openW,.04,thick+.06,m.concrete);
        local((a+b)/2,head-.04,openW,.08,thick+.02,m.paintedSlab);
        continue;
      }
      const jamb=o.jambM??.044;
      local(a+jamb/2,(sill+head)/2,jamb,head-sill,.12,m.frame);
      local(b-jamb/2,(sill+head)/2,jamb,head-sill,.12,m.frame);
      local((a+b)/2,head,openW,.05,.13,m.frame);
      if(o.main){
        // Single dark-wenge leaf with a long brass pull, hinged on the west jamb; opens inward when the viewer is near.
        const pivot=new T.Group();pivot.position.set(a,0,cross);dynamic.add(pivot);
        const leafH=head-.04,leaf=openW-.012,lm=m.wenge;
        box(leaf/2+.006,leafH/2+.01,0,leaf,leafH,.05,lm,pivot);
        for(const side of [-1,1]){
          box(leaf-.07,1.12,side*.062,.024,.9,.024,m.gold,pivot);
          for(const yy of [.72,1.52])box(leaf-.07,yy,side*.038,.02,.02,.04,m.gold,pivot);
        }
        mainDoor={pivot,x:(a+b)/2,z:cross,angle:0,target:0};
        continue;
      }
      if(o.kind==='door'){
        if(o.hingeEnd&&o.id.startsWith('bath')){
          if(alongX)throw new Error('Bathroom door requires an x-constant host wall');
          const sign=o.hingeEnd==='max'?-1:1,pivot=new T.Group();
          pivot.position.set(cross,0,sign===1?a:b);dynamic.add(pivot);
          const leaf=box(0,(head-.07)/2,sign*openW/2,o.leafThicknessM,head-.07,openW-2*jamb,m.wood,pivot);
          const handle=box(.055,1,sign*(openW-.12),.025,.18,.025,m.metal,pivot);
          leaf.userData.door=o.id;
          const colliders=[leaf,handle].map(object=>{
            const body={kind:'door',id:o.id};collision.push(body);return [object,body];
          });
          doors.push({id:o.id,pivot,leaf,handle,sign,colliders,open:true});
          setBathDoor(o.id,true);
          continue;
        }
        const n=o.double?2:1,w=openW/n;
        for(let leaf=0;leaf<n;leaf++){
          // Door leaves are parked 90 degrees to the wall, with the full clear opening traversable.
          const hinge=leaf===0?a:b,sign=leaf===0?1:-1;
          const center=cross+o.openSide*w*.5;
          const thickness=o.leafThicknessM??.045;
          const door=alongX?box(hinge,(head-.07)/2,center,thickness,head-.07,w,m.wood):box(center,(head-.07)/2,hinge,w,head-.07,thickness,m.wood);
          const handle=alongX?box(hinge+sign*.05,1,center+o.openSide*w*.2,.025,.18,.025,m.metal):box(center+o.openSide*w*.2,1,hinge+sign*.05,.025,.18,.025,m.metal);
          door.userData.door=o.id;handle.castShadow=false;
        }
      }else{
        local((a+b)/2,(sill+head)/2,openW-.06,head-sill-.04,.018,wall.id==='kitchen-utility'?m.glass:m.windowGlass).castShadow=false;
        local((a+b)/2,sill,openW,.055,.22,m.marble);
        const panes=Math.max(2,Math.round(openW/.48));
        for(let k=1;k<panes;k++)local(a+openW*k/panes,(sill+head)/2,.025,head-sill,.08,m.frame);
        local((a+b)/2,sill+(head-sill)*.5,openW,.022,.06,m.frame);
        if(o.kind==='vent'){
          // High frosted bath window with a plain white reveal; the old louvres are gone.
          local((a+b)/2,(sill+head)/2,openW-.05,head-sill-.03,.006,m.sheer,.012).castShadow=false;
        }else{
          const pocketId={'living-window':'CURT-LIV','dining-window':'CURT-DIN','master-window':'CURT-MBR-S','children-window':'CURT-CBR','master-top-window':'CURT-MBR-W03'}[o.id];
          const pocket=PLAN.curtainPockets?.pockets.find(p=>p.id===pocketId);
          if(pocket?.selected){
            const sign=pocket.intoRoomSign,inside=(alongX?(sign>0?z1:z0):(sign>0?x1:x0))*FT;
            const bottom=o.curtainBottomM??.04,top=PLAN.heights.band.value+.025;
            const [ca,cb]=(o.curtainSpan||o.span).map(n=>n*FT),stack=Math.min(.38,(cb-ca)*.22);
            pleatedCurtain(ca,cb,bottom,top,inside+sign*.055,alongX,sign,m.sheer,.012,Math.max(8,(cb-ca)*7));
            for(const [lo,hi] of [[ca,ca+stack],[cb-stack,cb]])
              pleatedCurtain(lo,hi,bottom,top,inside+sign*.11,alongX,sign,m.greyCurtain,.025,4);
          }
        }
      }
    }
  }
  // The non-visible roof remains a sun occluder in roof-off views.
  const roofMaterial=new T.MeshBasicMaterial({colorWrite:false,depthWrite:false});
  const roof=slab([1.503,0,30.008,44.005],H+.06,.12,roofMaterial);
  roof.renderOrder=-1;
  // False ceilings, trays, coves, linear profiles, black grooves and the bath drop ceilings come from the lighting schedule.
  const plan=ceilingPlan(PLAN);
  for(const style of ['diagonal','sharp']){
    const groups={};
    for(const [key,parent] of Object.entries({ceiling,lights,grooves})){
      const g=new T.Group();g.userData.noMerge=true;g.visible=style===cornerStyle;parent.add(g);groups[key]=g;
    }
    const p=style==='diagonal'?plan:ceilingPlan(PLAN,style);
    variants[style]={groups,plan:p,info:buildCeilings({plan:p,m,groups,glowMat,decalMat,registerDecal,PLAN})};
  }
  const ceilingInfo=variants.diagonal.info;
  function panelFrame(x,y,z,w,h,rot,mat,depth=.015,border=.02,parent=world){
    const o=new T.Mesh();o.material=mat;o.position.set(x,y,z);o.rotation.y=rot;
    o.userData.noMerge=true;o.receiveShadow=true;parent.add(o);
    const update=style=>{
      const points=[[-w/2,h/2],[w/2,h/2],[w/2,-h/2],[-w/2,-h/2]];
      const outer=[[-w/2-border,-h/2-border],[w/2+border,-h/2-border],[w/2+border,h/2+border],[-w/2-border,h/2+border]];
      const sh=new T.Shape(outer.map(p=>new T.Vector2(...p)));
      sh.holes.push(new T.Path(cornerPath(points,diagonalRadii(4,PLAN.design.radiusM,style)).map(p=>new T.Vector2(...p))));
      o.geometry.dispose();o.geometry=new T.ExtrudeGeometry(sh,{depth,bevelEnabled:false});o.geometry.translate(0,0,-depth);
      o.userData.cornerStyle=style;
    };
    update(cornerStyle);frames.push(update);return o;
  }
  function setCornerStyle(style){
    if(!['diagonal','sharp'].includes(style))throw new Error('Unknown corner style: '+style);
    cornerStyle=style;
    for(const [key,v] of Object.entries(variants))for(const g of Object.values(v.groups))g.visible=key===style;
    for(const update of frames)update(style);
  }
  function roundedPath(points,radius=.12){
    const sh=new T.Shape(),p=points.map(([x,z])=>new T.Vector2(x*FT,z*FT)),n=p.length;
    for(let i=0;i<n;i++){
      const prev=p[(i+n-1)%n],cur=p[i],next=p[(i+1)%n];
      const r=Math.min(radius,cur.distanceTo(prev)/3,cur.distanceTo(next)/3);
      const a=cur.clone().add(prev.clone().sub(cur).normalize().multiplyScalar(r));
      const b=cur.clone().add(next.clone().sub(cur).normalize().multiplyScalar(r));
      if(i===0)sh.moveTo(a.x,a.y);else sh.lineTo(a.x,a.y);
      sh.quadraticCurveTo(cur.x,cur.y,b.x,b.y);
    }sh.closePath();return sh;
  }

  function chair(x,z,rot=0,bar=false){
    const g=new T.Group();g.position.set(x,0,z);g.rotation.y=rot;world.add(g);
    const h=bar?.7:.45;
    box(0,h,0,.43,.10,.43,m.fabric,g,true);box(0,h+.23,.18,.42,.42,.09,m.chairBack,g,true);
    for(const X of [-.15,.15])for(const Z of [-.15,.15])box(X,h/2,Z,.034,h,.034,m.wood,g);
    if(bar)box(0,.22,-.16,.32,.025,.025,m.metal,g);
  }
  function plant(x,z,h,fig=false){
    if(fig){
      // Fiddle-leaf fig in a woven basket.
      cylinder(x,.2,z,.22,.4,m.wicker,.26);cylinder(x,.41,z,.2,.015,m.soil);
      line(v(x,.4,z),v(x,h*.72,z),.022,m.stem);
      for(let i=0;i<14;i++){
        const a=i*2.399,top=h*.42+(h*.58)*(i%7+1)/7,r=.12+.16*(i%3)/2,ex=x+Math.cos(a)*r,ez=z+Math.sin(a)*r;
        line(v(x,Math.min(top-.05,h*.72),z),v(ex,top,ez),.008,m.stem);
        const leaf=ball(ex,top,ez,.15,.2,.035,m.leaf);leaf.rotation.set(.7*Math.cos(a),a,.5*Math.sin(a));
      }
      return;
    }
    cylinder(x,.19,z,.19,.38,m.terracotta,.23);cylinder(x,.39,z,.18,.015,m.soil);
    for(let i=0;i<9;i++){
      const a=i*2.399,top=.5+(h-.5)*(i%4+1)/4,ex=x+Math.cos(a)*.25,ez=z+Math.sin(a)*.25;
      line(v(x,.39,z),v(ex,top,ez),.012,m.stem);
      const leaf=ball(ex,top,ez,.10,.27,.035,m.leaf);leaf.rotation.set(.5*Math.cos(a),a,.55*Math.sin(a));
    }
  }
  function lamp(x,z,room,y=.62){
    cylinder(x,y+.01,z,.10,.025,m.metal);cylinder(x,y+.18,z,.017,.35,m.metal);
    cylinder(x,y+.38,z,.16,.22,m.fabric,.11);cylinder(x,y+.28,z,.11,.013,glowMat(room,'read',2.4));
  }
  function artwork(x,y,z,w,h,rot=0){
    const g=new T.Group();g.position.set(x,y,z);g.rotation.y=rot;world.add(g);
    box(0,0,0,w+.06,h+.06,.04,m.wood,g);box(0,0,.024,w,h,.008,m.art,g);
    const a=ball(-w*.13,0,.036,w*.24,h*.29,.008,m.accent,g);a.rotation.z=-.3;
    ball(w*.16,h*.13,.04,w*.15,h*.18,.009,m.terracotta,g);
    for(let i=0;i<4;i++)box(w*(i-1.5)*.13,-h*.28,.042,.008,h*.26,.004,m.wood,g);
  }
  for(const f of PLAN.furniture)if(f.kind==='plant')plant(f.at[0]*FT,f.at[1]*FT,f.height,f.fig);
  const ctx={m,PLAN,FT,metresRect,box,cylinder,ball,slab,solid,line,v,world,dynamic,collision,glowMat,decalMat,planeGeo,lights,chair,plant,lamp,artwork,mesh,panelFrame};
  const hall=buildHall(ctx);
  const rooms=buildRooms(ctx);
  const baths=buildBaths(ctx);
  box(16.32*FT,1.10,43.67*FT,1.21,2.2,.03,m.steel);
  box(16.32*FT,1.10,43.69*FT,.014,2.2,.018,m.black);
  box(18.65*FT,1.26,44.03*FT,.10,.23,.022,m.black);

  const stairParts=[],st=PLAN.stairs,upper=metresRect(st.upper),lower=metresRect(st.lower),landing=metresRect(st.landing),rise=PLAN.heights.floorToFloor.value/(st.upperTreads+st.lowerTreads);
  for(let i=0;i<st.upperTreads;i++){
    const a=upper[0]+i*(upper[2]-upper[0])/st.upperTreads,b=upper[0]+(i+1)*(upper[2]-upper[0])/st.upperTreads,h=(i+1)*rise;
    stairParts.push({part:'flight-to-landing',mesh:box((a+b)/2,h/2,(upper[1]+upper[3])/2,b-a,h,upper[3]-upper[1],m.tile)});
  }
  stairParts.push({part:'landing',mesh:box((landing[0]+landing[2])/2,st.upperTreads*rise/2,(landing[1]+landing[3])/2,landing[2]-landing[0],st.upperTreads*rise,landing[3]-landing[1],m.tile)});
  if(st.risingFlightShown!==false)for(let i=0;i<st.lowerTreads;i++){
    const a=lower[2]-(i+1)*(lower[2]-lower[0])/st.lowerTreads,b=lower[2]-i*(lower[2]-lower[0])/st.lowerTreads,h=(st.upperTreads+i+1)*rise;
    stairParts.push({part:'rising-flight',mesh:box((a+b)/2,h/2,(lower[1]+lower[3])/2,b-a,h,lower[3]-lower[1],m.tile)});
  }
  collision.push({x0:upper[0],z0:upper[1],x1:landing[2],z1:landing[3],y0:0,y1:4,kind:'stairs'});
  collision.push({x0:lower[0],z0:lower[1],x1:lower[2],z1:lower[3],y0:0,y1:4,kind:'stairs'});
  for(const zz of [52.01*FT]){
    box(15*FT,.55,zz,29*FT,1.1,.08,m.wall);
    line(v(.8*FT,1.12,zz),v(30*FT,1.12,zz),.026,m.steel);
  }
  box(.747*FT,.55,48*FT,.08,1.1,8*FT,m.wall);
  for(let i=0;i<10;i++)box((11.3+i*1.4)*FT,1.65,48*FT,.025,1,.025,m.steel);
  line(v(11.3*FT,2.16,48*FT),v(25*FT,2.16,48*FT),.025,m.steel);
  box(-1,2.5,6,.8,5,13,m.skyline,neighbours);
  box(-.55,2.5,6,.05,5,13,m.wall,neighbours);
  box(5,-.31,8,200,.12,200,m.ground).receiveShadow=true;

  const avatar=new T.Group();scene.add(avatar);
  ball(0,1.51,0,.105,.135,.105,m.wood,avatar);box(0,1.09,0,.33,.54,.22,m.accent,avatar,true);
  for(const side of [-1,1]){
    box(side*.11,.5,0,.12,.64,.14,m.black,avatar,true);
    box(side*.23,1.02,0,.10,.5,.11,m.fabric,avatar,true);
    box(side*.11,.15,-.035,.14,.08,.24,m.black,avatar,true);
  }
  avatar.visible=false;
  function mergeGroup(group){
    const batches=new Map();
    group.updateMatrixWorld(true);
    const walk=o=>{
      if(o.isMesh&&!o.material.transparent&&o.geometry!==planeGeo&&o!==roof){
        const key=o.material.uuid+':'+o.castShadow;
        if(!batches.has(key))batches.set(key,{material:o.material,cast:o.castShadow,items:[]});
        batches.get(key).items.push(o);
      }
      for(const ch of o.children)if(!ch.userData.noMerge)walk(ch);
    };
    walk(group);
    const remove=[];
    for(const b of batches.values()){
      if(b.items.length<2)continue;
      const gs=b.items.map(o=>{
        const g=o.geometry.clone().applyMatrix4(o.matrixWorld);
        // All statics share position/normal/uv; strip addon-specific attributes.
        for(const name of Object.keys(g.attributes))if(!['position','normal','uv'].includes(name))g.deleteAttribute(name);
        return g.index?g.toNonIndexed():g;
      });
      const geo=mergeGeometries(gs,false);gs.forEach(g=>g.dispose());
      const o=new T.Mesh(geo,b.material);o.castShadow=b.cast;o.receiveShadow=true;group.add(o);remove.push(...b.items);
    }
    remove.forEach(o=>o.removeFromParent());
  }
  const mk=(geo,mat,x,y,z,parent)=>mesh(geo,mat,x,y,z,1,1,1,parent,false);
  const fixtures=buildFixtures({PLAN,plan,pocketInfo:ceilingInfo.pockets,m,groups:{ceiling,lights,grooves,fans,markers,feature},glowMat,decalMat,registerDecal,mk,v,line,planeGeo,panelFrame});
  for(const g of Object.values(fixtures.features))feature.add(g);
  mergeGroup(rooms.wardrobeProposals.closed);mergeGroup(rooms.wardrobeProposals.interior);
  mergeGroup(world);mergeGroup(ceiling);mergeGroup(lights);mergeGroup(fans);
  for(const variant of Object.values(variants))for(const g of Object.values(variant.groups))mergeGroup(g);
  world.traverse(o=>{if(o.isMesh&&!o.material.transparent&&o.parent!==rooms.wardrobeProposals.interior)shadowObjects.push(o);});
  // The main door swings inward when the viewer is within ~1.9 m.
  function update(dt,focus){
    if(mainDoor){
      mainDoor.target=focus&&Math.hypot(focus.x-mainDoor.x,focus.z-mainDoor.z)<1.9?1.75:0;
      mainDoor.angle+=(mainDoor.target-mainDoor.angle)*(1-Math.exp(-dt*4));
      mainDoor.pivot.rotation.y=mainDoor.angle;
    }
    hall.update(dt);
  }
  function label(room){
    const c=document.createElement('canvas');c.width=384;c.height=80;const ctx=c.getContext('2d');
    ctx.fillStyle='rgba(244,247,240,.91)';ctx.fillRect(0,0,384,80);
    ctx.fillStyle='#244638';ctx.font='600 27px Segoe UI';ctx.textAlign='center';ctx.fillText(room.name.toUpperCase(),192,33);
    ctx.font='21px Segoe UI';ctx.fillText(room.dimension?.text||'CARRY-FORWARD / SITE CHECK',192,63);
    const texture=new T.CanvasTexture(c);texture.colorSpace=T.SRGBColorSpace;
    const mat=new T.SpriteMaterial({map:texture,depthTest:false,transparent:true,toneMapped:false});
    const s=new T.Sprite(mat);s.position.set((room.rect[0]+room.rect[2])/2*FT,.15,(room.rect[1]+room.rect[3])/2*FT);s.scale.set(1.8,.375,1);s.renderOrder=20;labels.add(s);
  }
  PLAN.rooms.filter(r=>!['dressing','washing','lobby'].includes(r.id)).forEach(label);
  labels.visible=false;
  return {world,ceiling,lights,grooves,rcp,feature,features:fixtures.features,neighbours,labels,fans,markers,avatar,collision,floors,emission,shadowObjects,roof,box,line,glowMat,decalMat,plan,ceilingInfo,ensureMarkerLabels:fixtures.ensureLabels,curtainPockets:fixtures.curtainPockets,lightEffects:fixtures.lightEffects,update,hall,rooms,baths,doors,setBathDoor,stairParts,variants,setCornerStyle,getCornerStyle:()=>cornerStyle,setTiles:materials.setTiles};
}
