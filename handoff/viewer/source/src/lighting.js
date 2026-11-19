import * as T from 'three';
import {PLAN,FT} from './geometry.js';
import {CH,channelOf,buildGrid,gridStats,patchStats,directAt,nicheStripE} from './photometry.js';
import {arange} from './schedule.js';

export function kelvin(k) {
  const t=k/100,r=t<=66?255:329.698727446*Math.pow(t-60,-.1332047592);
  const g=t<=66?99.4708025861*Math.log(t)-161.1195681661:288.1221695283*Math.pow(t-60,-.0755148492);
  const b=t>=66?255:t<=19?0:138.5177312231*Math.log(t-10)-305.0447927307;
  // Visual white balance, not a spectral colour or photometric calibration.
  const whiteG=99.4708025861*Math.log(40)-161.1195681661;
  const whiteB=138.5177312231*Math.log(30)-305.0447927307;
  const balance=(value,white)=>T.MathUtils.clamp(.4+.6*value/white,0,1);
  return new T.Color().setRGB(balance(r,255),balance(g,whiteG),balance(b,whiteB),T.SRGBColorSpace);
}
export function solarPosition(hour,day,northFront=true){
  const rad=Math.PI/180,lat=17.385*rad,b=(day-81)*360/364*rad;
  const eq=9.87*Math.sin(2*b)-7.53*Math.cos(b)-1.5*Math.sin(b),solarHour=hour+(4*(78.4867-82.5)+eq)/60;
  const dec=23.44*rad*Math.sin(2*Math.PI*(284+day)/365),ha=15*(solarHour-12)*rad;
  const up=Math.sin(lat)*Math.sin(dec)+Math.cos(lat)*Math.cos(dec)*Math.cos(ha);
  const east=-Math.cos(dec)*Math.sin(ha),north=Math.cos(lat)*Math.sin(dec)-Math.sin(lat)*Math.cos(dec)*Math.cos(ha),s=northFront?1:-1;
  return {dir:new T.Vector3(-east*s,up,north*s),altitude:Math.asin(up)/rad};
}

export const LAYERS=CH;
export const BATHS=['bath1','bath2'];
const zoneId=id=>id==='washing'?'utility':id;
export const ipRating=type=>{
  const spec=PLAN.fixtures.cat[type]||PLAN.fixtures.strips[type];
  if(!spec)throw new Error('Unscheduled fixture type '+type);
  return spec.ip;
};
const CHANNEL_LABEL={high:'HIGH',low:'Cove (LOW)',mood:'MOOD',perim:'Bath perimeter',line:'LINE',task:'TASK',read:'READ',night:'NIGHT',mirror:'VANITY',pooja:'Pooja strip',poojaSpot:'Pooja spot',art:'ART',study:'STUDY',uv:'Under-vanity'};
export const channelLabel=c=>CHANNEL_LABEL[c]||c;
const VISUAL_GLOW_SCALE=.22;
const RAIL_OF_LANE={HIGH:'high',TASK:'high',LOW:'low',COVE:'low',LINE:'low',MOOD:'low',PERIM:'low'};

export function createLighting(scene,model) {
  const numerical=PLAN.numericalLighting?.available!==false;
  const states={},stats={},grids={},floorBasis={},overlays=new T.Group(),pools=[],spots=[],groupStates={},autoScenes={};
  scene.add(overlays);overlays.visible=false;
  const zones=PLAN.fixtures.zones,{CAT:cat,strips}=PLAN.fixtures.cat?{CAT:PLAN.fixtures.cat,strips:PLAN.fixtures.strips}:{};
  const assume=PLAN.fixtures.assumptions;
  const inputs=PLAN.fixtures.inputs;
  const selectedPockets=(PLAN.curtainPockets?.pockets||[]).filter(p=>p.selected);
  const pocketFixtures=selectedPockets.map(p=>({id:p.id,room:p.room,lane:'LOW',channel:'low',layer:'LOW',
    type:'CURTAIN_S1',circuit:p.circuit,cct:p.cct,held:false,lm:0,rail:'low'}));
  const circuits=[...PLAN.fixtures.controls.circuits,...selectedPockets.map(p=>({circuit:p.circuit,rooms:[p.room],lane:'LOW'}))];
  const allFixtures=[...zones.flatMap(z=>z.fixtures),...pocketFixtures];
  const accessoryFixtures=allFixtures.filter(f=>f.lane==='READ'||f.lane==='NIGHT');
  if(accessoryFixtures.length!==6||new Set(accessoryFixtures.map(f=>f.circuit)).size!==6)throw new Error('Expected six independently switched reader / PIR fitting previews');
  const accessoryState=Object.fromEntries(accessoryFixtures.map(f=>[f.id,false]));
  for(const circuit of circuits){
    const fixtures=allFixtures.filter(f=>f.circuit===circuit.circuit);
    if(!fixtures.length)throw new Error('Empty scheduled circuit '+circuit.circuit);
    groupStates[circuit.circuit]={on:false,dim:100,k:parseInt(fixtures[0].cct),auto:true,tunable:fixtures.every(f=>f.tunable),fixtures};
  }
  const members=(room,ch)=>[...new Set(allFixtures.filter(f=>{
    if(f.room!==zones.find(z=>z.room===zoneId(room))?.id)return false;
    return !ch||(ch==='high'||ch==='low'?RAIL_OF_LANE[f.lane]===ch:channelOf(f)===ch);
  }).map(f=>f.circuit))];
  function setCircuit(id,values){
    const s=groupStates[id];
    if(!s)throw new Error('Unknown scheduled dimmer '+id);
    if(values.k!=null)throw new Error('Colour temperature is fixed per fitting and cannot be changed');
    if(values.dim!=null&&(!Number.isFinite(values.dim)||values.dim<0||values.dim>100))throw new Error('Brightness must be 0-100');
    Object.assign(s,values,{auto:false});
  }
  let plane='reference',heightOffset=0,feature={mode:'track',finish:'art'};
  const patches={};
  const heatStops=[[0,'#182864'],[50,'#2454bd'],[100,'#20aab2'],[200,'#5cc573'],[300,'#d6d95b'],[500,'#f5a23c'],[750,'#dc483a']];
  const heatLUT=[];
  for(let lux=0;lux<=750;lux++){
    let c=new T.Color(heatStops.at(-1)[1]);
    for(let j=1;j<heatStops.length;j++)if(lux<heatStops[j][0]){c=new T.Color(heatStops[j-1][1]).lerp(new T.Color(heatStops[j][1]),(lux-heatStops[j-1][0])/(heatStops[j][0]-heatStops[j-1][0]));break;}
    c.convertLinearToSRGB();heatLUT.push([Math.round(c.r*255),Math.round(c.g*255),Math.round(c.b*255)]);
  }
  const fixtureCache={};
  const zoneFixtures=z=>z.fixtures;
  const planeFor=z=>plane==='reference'?z.plane_m:plane;
  const ctxFor=(z,p,night='ceiling')=>({assume,strips,plane:p,off:heightOffset,night});
  for(const z of zones){
    const state={};
    Object.defineProperty(state,'auto',{enumerable:true,get:()=>members(z.room).every(id=>groupStates[id].auto),set:value=>members(z.room).forEach(id=>groupStates[id].auto=value)});
    for(const ch of CH){
      const ids=members(z.room,ch),lane={};
      for(const prop of ['on','dim','k'])Object.defineProperty(lane,prop,{
        enumerable:true,
        get:()=>prop==='on'?ids.some(id=>groupStates[id].on):ids.length?groupStates[ids[0]][prop]:prop==='k'?2700:100,
        set:value=>{
          for(const id of ids){
            if(prop==='k'&&!groupStates[id].tunable)throw new Error('Fixed-white fitting cannot change CCT: '+id);
            groupStates[id][prop]=value;
          }
        },
      });
      state[ch]=lane;
    }
    states[z.room]=state;
    const p=z.poly.map(p=>p.map(n=>n*FT)),xs=p.map(p=>p[0]),zs=p.map(p=>p[1]);
    const light=new T.PointLight('#fff0d7',0,Math.min(4,Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...zs)-Math.min(...zs))*.85),2);
    light.position.set((Math.min(...xs)+Math.max(...xs))/2,Math.min(2.15,z.ceil_m-.4),(Math.min(...zs)+Math.max(...zs))/2);
    scene.add(light);pools.push({room:z.room,light});
  }
  states.washing=states.utility;
  // Real feature-wall spot lights (non-shadow). Three always exist so the shader light count never changes.
  for(let i=0;i<3;i++){
    const l=new T.SpotLight('#ffe2b0',0,7,.3,.55,2);l.castShadow=false;scene.add(l,l.target);spots.push({light:l,f:null});
  }
  function placeSpots(){
    const heads=allFixtures.filter(f=>f.id.startsWith('FW-')&&f.type!=='TRKLIN');
    spots.forEach((s,i)=>{
      const f=heads[i];s.f=f||null;if(!f)return;
      const h=f.h_m??2.7;s.light.position.set(f.x*FT,h,f.z*FT);s.light.target.position.set(f.aim[0]*FT,f.aim[2],f.aim[1]*FT);
      s.light.angle=Math.min(.7,f.beam*Math.PI/180*.78);s.light.penumbra=.55;s.light.target.updateMatrixWorld();
    });
  }
  function mkOverlay(g){
    const c=document.createElement('canvas');c.width=g.nx;c.height=g.nz;
    const tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;tex.minFilter=tex.magFilter=T.LinearFilter;
    const mat=new T.MeshBasicMaterial({map:tex,transparent:true,opacity:.83,depthWrite:false});
    const mesh=new T.Mesh(new T.PlaneGeometry((g.X-g.x0)*FT,(g.Z-g.z0)*FT),mat);mesh.rotation.x=-Math.PI/2;
    mesh.position.set((g.x0+g.X)/2*FT,g.plane+.03,(g.z0+g.Z)/2*FT);mesh.renderOrder=10;mesh.userData.room=g.zone.room;overlays.add(mesh);
    g.canvas=c;g.tex=tex;g.mesh=mesh;
  }
  const art=()=>{
    const g=inputs.calc_geometry.art_wall,pts=[];
    for(const y of arange(...g.grid_y_m))for(const z of arange(g.z0_ft+.05,g.z1_ft,g.grid_z_step_ft)){
      if(Math.abs(z-g.art_zc_ft)<=g.art_w_m/2/FT&&Math.abs(y-g.art_yc_m)<=g.art_h_m/2)pts.push([g.x_ft,z,y]);
    }
    return pts;
  };
  const perGroup=(z,fx,pts,normal)=>Object.fromEntries([...new Set(fx.map(f=>f.circuit))].map(id=>[id,patchStats(z,fx.filter(f=>f.circuit===id),pts,normal,ctxFor(z,z.plane_m)).avg]));
  function buildPatches(z,fx){
    const ctx=ctxFor(z,z.plane_m),zz={...z,fixtures:fx};
    if(z.id==='DIN'){
      const pts=art(),heads=fx.filter(f=>channelOf(f)==='art'&&f.type!=='TRKLIN');
      patches.feature={art:patchStats(zz,heads,pts,[-1,0,0],ctx),amb:perGroup(zz,fx.filter(f=>channelOf(f)!=='art'),pts,[-1,0,0])};
    }else if(BATHS.includes(z.room)){
      const b=PLAN.bathrooms.rooms.find(b=>b.renderer_room_id===z.room),[x,y,zzp]=b.vanity.user_face_center_xyz_m;
      const pts=[-.08,0,.08].map(dx=>[(x+dx)/FT,zzp/FT,y]);
      patches[z.room]=perGroup(zz,fx,pts,b.vanity.user_face_normal_xyz);
    }else if(z.id==='LOB'){
      const g=inputs.calc_geometry.lobby_face;
      patches.lobby=perGroup(zz,fx,g.x_ft.map(x=>[x,g.z_ft,g.h_m]),g.normal);
    }else if(z.id==='LIV'){
      // Reference planes follow the authoritative shallow-niche schedule, not the retired deep enclosure.
      const p1=fx.find(f=>f.id==='LIV-P1'),p2=fx.find(f=>f.id==='LIV-P2');
      if(p1&&p2){
        const [tx,tz,th]=p2.aim,n=inputs.calc_geometry.pooja.normal;
        const spotFace=directAt(zz,[p2],[tx,tz,th],n,ctx),stripFace=nicheStripE(p1,[tx*FT,th,tz*FT],n,assume);
        patches.pooja={spotFace,stripFace};
      }
    }else if(z.id==='UTL'){
      const g=inputs.calc_geometry.utility_counter,pts=[];
      for(const x of arange(...g.x_ft,g.step_ft))for(const z of arange(...g.z_ft,g.step_ft))pts.push([x,z,g.h_m]);
      patches.utility=Object.fromEntries(['high','task'].map(c=>[c,patchStats(zz,fx.filter(f=>channelOf(f)===c),pts,[0,1,0],ctx).avg]));
    }
  }
  function rebuildZone(z){
    const fx=zoneFixtures(z),zz={...z,fixtures:fx};fixtureCache[z.room]=fx;
    floorBasis[z.room]=buildGrid(zz,ctxFor(z,0,'low'));
    const old=grids[z.room];if(old?.mesh){old.mesh.geometry.dispose();old.mesh.material.map.dispose();old.mesh.material.dispose();old.mesh.removeFromParent();}
    const g=buildGrid(zz,ctxFor(z,planeFor(z)));mkOverlay(g);grids[z.room]=g;
    buildPatches(z,fx);
  }
  function rebuild(){
    for(const z of zones)if(numerical)rebuildZone(z);else fixtureCache[z.room]=zoneFixtures(z);
    placeSpots();recompute();
  }
  const weight=(room,c)=>{const s=states[zoneId(room)][c];return s.on?s.dim/100:0;};
  const weightsOf=room=>Object.fromEntries(CH.map(c=>[c,weight(room,c)]));
  const groupWeight=id=>{const s=groupStates[id];return s.on?s.dim/100:0;};
  const groupWeights=()=>Object.fromEntries(Object.keys(groupStates).map(id=>[id,groupWeight(id)]));
  function paintOverlays(){
    for(const [room,g] of Object.entries(grids)){
      const w=groupWeights(),chans=Object.keys(g.groups).filter(c=>w[c]),ctx=g.canvas.getContext('2d'),im=ctx.createImageData(g.nx,g.nz);
      for(let k=0;k<g.mask.length;k++){
        if(!g.mask[k])continue;
        let e=0;for(const c of chans)e+=g.groups[c][k]*w[c];
        const col=heatLUT[Math.min(750,Math.round(e))];im.data[k*4]=col[0];im.data[k*4+1]=col[1];im.data[k*4+2]=col[2];im.data[k*4+3]=255;
      }
      ctx.putImageData(im,0,0);g.tex.needsUpdate=true;
    }
  }
  function floorMaps(){
    const color=new T.Color();
    for(const f of model.floors){
      const g=floorBasis[zoneId(f.room)];if(!g)continue;
      const chans=Object.keys(g.groups),colors=chans.map(c=>kelvin(groupStates[c].k).multiplyScalar(groupWeight(c)));
      const c=f.lightCanvas||document.createElement('canvas');
      if(!f.lightCanvas){
        f.lightCanvas=c;c.width=g.nx;c.height=g.nz;
        const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;t.channel=1;f.mat.lightMap=t;f.mat.lightMapIntensity=1.1;f.mat.needsUpdate=true;
      }
      const ctx=c.getContext('2d'),im=ctx.createImageData(g.nx,g.nz);
      for(let i=0;i<g.mask.length;i++){
        color.setRGB(0,0,0);
        for(let l=0;l<chans.length;l++){
          const e=g.groups[chans[l]][i]/300;
          color.r+=colors[l].r*e;color.g+=colors[l].g*e;color.b+=colors[l].b*e;
        }
        color.convertLinearToSRGB();
        im.data[i*4]=Math.min(255,color.r*255);im.data[i*4+1]=Math.min(255,color.g*255);im.data[i*4+2]=Math.min(255,color.b*255);im.data[i*4+3]=255;
      }
      ctx.putImageData(im,0,0);
      const r=f.rect,t=f.mat.lightMap,W=g.X-g.x0,H=g.Z-g.z0;
      t.repeat.set((r[2]-r[0])/W,(r[3]-r[1])/H);t.offset.set((r[0]-g.x0)/W,(g.Z-r[3])/H);t.needsUpdate=true;
    }
  }
  function recompute(){
    if(!numerical)return;
    for(const [room,g] of Object.entries(grids)){
      const s=gridStats(g,groupWeights(),true);
      stats[room]={...s,uniformity:s.U0,area:g.area,samples:g.task.reduce((a,b)=>a+b,0)};
    }
    stats.washing=stats.utility;
    if(overlays.visible)paintOverlays();
    floorMaps();
  }
  function applyScene(room,name,manual=true){
    const title=name[0].toUpperCase()+name.slice(1),def=inputs.scenes.levels[title];
    if(!def)throw new Error('Unknown canonical scene '+name);
    const zone=zones.find(z=>z.room===zoneId(room)),high=zone.fixtures.find(f=>f.lane==='HIGH');
    for(const id of members(room)){
      const s=groupStates[id],lane=s.fixtures[0].lane;
      let level=def[lane]??0;
      if(lane==='ACCENT'&&def[lane]===null){
        if(!numerical){s.on=false;s.dim=0;if(manual)s.auto=false;continue;}
        const f=s.fixtures[0],refs=PLAN.fixtures.expected;
        const setting=f.id.startsWith('FW-')?refs.art.scenes[title].track_level_for_3to1:
          refs.pooja.scenes[title].recommended[f.id==='LIV-P1'?'strip':'spot'];
        level=parseFloat(setting)/100;
        if(!Number.isFinite(level)||level<0||level>1)throw new Error('Missing commissioned accent level for '+id+' / '+title);
      }
      s.on=level>0;if(level>0)s.dim=level*100;
      if(s.tunable)s.k=['Work','Full'].includes(title)?parseInt(high.cct):2700;
      if(manual)s.auto=false;
    }
    if(!manual)autoScenes[zone.id]=title;
  }
  function setScene(id,name,manual=true){
    const ids=id==='all'?zones.map(z=>z.room):[zoneId(id)];
    for(const room of ids)applyScene(room,name,manual);
    recompute();
  }
  function setTime(hour){
    let changed=false;
    for(const z of zones){
      const s=states[z.room];if(!s.auto)continue;const name=hour>=18.1?'Full':'Off';
      if(autoScenes[z.id]!==name){applyScene(z.room,name,false);changed=true;}
    }
    if(changed)recompute();
  }
  function setFeature(mode=feature.mode,finish=feature.finish){
    if(mode!=='track'||finish!=='art')throw new Error('Only the current canonical feature-wall design is available');
  }
  function readouts(){
    if(!numerical)return {available:false,reason:PLAN.numericalLighting.reason};
    const wArt=weight('dining','art'),F=patches.feature;
    let amb=0;for(const [id,v] of Object.entries(F.amb))amb+=v*groupWeight(id);
    const face=room=>Object.entries(patches[room]).reduce((sum,[id,v])=>sum+v*groupWeight(id),0);
    const P=patches.pooja,U=patches.utility;
    const spot=P.spotFace*weight('living','poojaSpot'),strip=P.stripFace*weight('living','pooja');
    return {
      feature:{avg:F.art.avg*wArt,max:F.art.max*wArt,ambient:amb,total:F.art.avg*wArt+amb,artRef100:F.art.avg},
      face:{bath1:face('bath1'),bath2:face('bath2'),lobby:face('lobby')},
      pooja:{spot,strip,idol:spot+strip,spotRef:P.spotFace,stripRef:P.stripFace},
      counter:{high:U.high*weight('utility','high'),highTask:U.high*weight('utility','high')+U.task*weight('utility','task'),highRef:U.high,highTaskRef:U.high+U.task},
    };
  }
  function update(dt){
    const t=1-Math.exp(-dt*7);
    for(const e of model.emission){
      const s=e.circuit?groupStates[e.circuit]:states[zoneId(e.room)][e.layer];if(!s)throw new Error('Unscheduled emissive layer '+e.layer);
      const held=e.circuit?groupStates[e.circuit].fixtures.every(f=>f.held):e.layer==='pooja'||e.layer==='poojaSpot';
      const scheduled=e.circuit?groupStates[e.circuit].fixtures.some(f=>!f.held&&f.lm>0):true;
      const level=scheduled&&!held&&s.on?s.dim/100:0;
      if(e.kind==='decal'){
        const target=kelvin(s.k).multiplyScalar(level*(e.gain??1)*VISUAL_GLOW_SCALE);e.mat.color.lerp(target,t);
      }else{
        e.mat.emissive.lerp(kelvin(s.k),t);e.mat.emissiveIntensity=T.MathUtils.lerp(e.mat.emissiveIntensity,level*(e.gain??(e.layer==='high'?3.4:2.2))*VISUAL_GLOW_SCALE,t);
      }
    }
    for(const {room,light} of pools){
      const s=states[room],col=new T.Color(0,0,0);let power=0,weightSum=0;
      for(const f of fixtureCache[room]){
        const c=channelOf(f);if(c==='art')continue;
        const lm=(f.held?0:groupWeight(f.circuit))*f.lm,k=kelvin(groupStates[f.circuit].k);col.r+=k.r*lm;col.g+=k.g*lm;col.b+=k.b*lm;weightSum+=lm;power+=lm;
      }
      if(weightSum)col.multiplyScalar(1/weightSum);
      // PointLight.power is luminous flux in lumens; keep the pooled source at the schedule total.
      light.color.lerp(col,t);light.power=T.MathUtils.lerp(light.power,power,t);
    }
    const w=weight('dining','art'),k=kelvin(states.dining.art.k);
    for(const sp of spots){
      if(!sp.f){sp.light.power=T.MathUtils.lerp(sp.light.power,0,t);continue;}
      sp.light.color.lerp(k,t);sp.light.power=T.MathUtils.lerp(sp.light.power,sp.f.lm*w,t);
    }
  }
  rebuild();

  // ---- Simple per-room rails: ON/OFF, HIGH (main) and LOW (cove / mood / line / perimeter) brightness ----
  const railOfCircuit=id=>RAIL_OF_LANE[groupStates[id].fixtures[0].lane]||'independent';
  const roomLight=Object.fromEntries(zones.map(z=>[z.room,{on:false,high:100,low:100}]));
  const masterLight={high:{on:true,dim:100},low:{on:true,dim:100}};
  const circuitLocalDim=Object.fromEntries(Object.keys(groupStates).map(id=>[id,100]));
  const roomsOfCircuit=id=>zones.filter(z=>members(z.room).includes(id)).map(z=>z.room);
  const clampPct=v=>Math.max(0,Math.min(100,Math.round(Number(v))));
  function applyCircuit(id){
    const s=groupStates[id],rail=railOfCircuit(id),accessory=s.fixtures.find(f=>Object.hasOwn(accessoryState,f.id));
    const roomOn=roomsOfCircuit(id).some(r=>roomLight[r].on),held=s.fixtures.every(f=>f.held);
    const master=rail==='high'||rail==='low'?masterLight[rail]:null;
    s.auto=false;
    s.on=accessory?!accessory.held&&accessoryState[accessory.id]:!held&&roomOn&&(!master||master.on);
    s.dim=master?circuitLocalDim[id]*master.dim/100:100;
  }
  function applyRoomLight(room){
    for(const id of members(room)){
      const rail=railOfCircuit(id);
      if(rail==='high'||rail==='low')circuitLocalDim[id]=roomLight[room][rail];
      applyCircuit(id);
    }
  }
  function setRoomLight(room,values={}){
    const id=zoneId(room),r=roomLight[id];
    if(!r)throw new Error('Unknown room '+room);
    if(values.on!=null)r.on=Boolean(values.on);
    for(const k of ['high','low'])if(values[k]!=null){
      if(!Number.isFinite(Number(values[k])))throw new Error('Brightness must be a number 0-100');
      r[k]=clampPct(values[k]);
    }
    applyRoomLight(id);
    return getRoomLight(id);
  }
  function setMasterLight(lane,values={}){
    if(lane!=='high'&&lane!=='low')throw new Error('Unknown whole-house lighting lane '+lane);
    const state=masterLight[lane];
    if(values.on!=null)state.on=Boolean(values.on);
    if(values.dim!=null){
      if(!Number.isFinite(Number(values.dim)))throw new Error('Brightness must be a number 0-100');
      state.dim=clampPct(values.dim);
    }
    for(const id of Object.keys(groupStates))if(railOfCircuit(id)===lane)applyCircuit(id);
    recompute();
    return getMasterLight(lane);
  }
  function getMasterLight(lane){
    if(lane!=='high'&&lane!=='low')throw new Error('Unknown whole-house lighting lane '+lane);
    return {...masterLight[lane]};
  }
  function getRoomLight(room){
    const id=zoneId(room),r=roomLight[id],zone=zones.find(z=>z.room===id),ids=members(id);
    const active=ids.filter(id=>!groupStates[id].fixtures.every(f=>f.held));
    const rails=active.map(railOfCircuit),cct=PLAN.fixedCct?.rooms?.[zone.id]||{high:[],low:[],independent:[]};
    return {room:id,zone:zone.id,on:r.on,high:r.high,low:r.low,hasHigh:rails.includes('high'),hasLow:rails.includes('low'),
      held:active.length===0,cct,sharedLow:ids.filter(c=>railOfCircuit(c)==='low'&&roomsOfCircuit(c).length>1)};
  }
  function getLumenBudget(room){
    const zone=zones.find(z=>z.room===zoneId(room));if(!zone)throw new Error('Unknown room '+room);
    const result={scheduled:{high:0,low:0},available:{high:0,low:0},effective:{high:0,low:0}};
    for(const f of zone.fixtures){
      const rail=railOfCircuit(f.circuit);if(rail!=='high'&&rail!=='low')continue;
      const lm=Number(f.lm);
      if(!Number.isFinite(lm)||lm<0)throw new Error('Invalid scheduled lumens for '+f.id);
      result.scheduled[rail]+=lm;
      if(!f.held){result.available[rail]+=lm;result.effective[rail]+=lm*groupWeight(f.circuit);}
    }
    return result;
  }
  function setAccessory(id,on){
    const f=accessoryFixtures.find(f=>f.id===id);
    if(!f)throw new Error('Unknown individual fitting '+id);
    if(f.held&&on)throw new Error('This fitting is held for coordination: '+id);
    accessoryState[id]=Boolean(on);
    const zone=zones.find(z=>z.id===f.room);if(!zone)throw new Error('Unknown fitting room '+id);
    applyRoomLight(zone.room);
  }
  function setAllRooms(on){
    if(!on)for(const id of Object.keys(accessoryState))accessoryState[id]=false;
    for(const z of zones)setRoomLight(z.room,{on});
  }
  for(const z of zones)applyRoomLight(z.room);
  function reference(room){
    if(!numerical)return null;
    if(heightOffset!==0)return null;
    const zone=zones.find(z=>z.room===room),ref=PLAN.fixtures.expected.rooms[zone.id].lanes_at_100pct;
    let avg=0;
    for(const [lane,value] of Object.entries(ref)){
      const weights=zone.fixtures.filter(f=>f.lane===lane).map(f=>groupWeight(f.circuit));
      if(weights.some(w=>Math.abs(w-weights[0])>1e-8))return null;
      avg+=value.avg*(weights[0]??0);
    }
    return avg;
  }
  return {
    setRoomLight,getRoomLight,getLumenBudget,setAllRooms,setMasterLight,getMasterLight,railOfCircuit,roomLight,accessoryFixtures,accessoryState,setAccessory,
    states,groupStates,circuits,setCircuit,members,reference,grids,floorBasis,stats,overlays,pools,spots,recompute,setScene,setTime,update,heatStops,zones,readouts,setFeature,
    refreshOverlays:paintOverlays,weight,weightsOf,groupWeight,groupWeights,
    fixtures:room=>fixtureCache[zoneId(room)]||[],
    get feature(){return feature;},
    setPlane(value){plane=value;rebuild();},get plane(){return plane;},
    setHeight(value){heightOffset=value;rebuild();},get heightOffset(){return heightOffset;},
    restoreAuto(){for(const z of zones){states[z.room].auto=true;delete autoScenes[z.id];}},
  };
}
