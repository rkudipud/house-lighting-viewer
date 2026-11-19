import * as T from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {PLAN,FT,roomAt} from './geometry.js';
import {createMaterials} from './materials.js';
import {createModel} from './model.js';
import {createLighting} from './lighting.js';
import {createAnalysis} from './analysis.js';
import {prepareNavigation,WALK_RADIUS} from './navigation.js';

const $=id=>{const e=document.getElementById(id);if(!e)throw new Error('The page is missing element #'+id);return e;};
function fatal(error){$('loading').style.display='none';$('fatal').style.display='grid';$('fatal-detail').textContent=String(error?.message||error);console.error(error);}
try{start();}catch(error){fatal(error);}

function start(){
  const source=document.getElementById('plan-data');
  if(source){
    const data=JSON.parse(source.textContent);
    if(!Array.isArray(data.rooms)||!Array.isArray(data.walls)||!Array.isArray(data.openings)||!data.fixtures?.zones)throw new Error('The embedded plan-data JSON is missing rooms, walls, openings or fixture zones.');
    Object.assign(PLAN,data);
  }
  const heatSource=document.getElementById('heat-data');
  const renderer=new T.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
  const BASE_RATIO=Math.min(devicePixelRatio,1);
  renderer.setPixelRatio(BASE_RATIO);renderer.setSize(innerWidth,innerHeight);
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;
  renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=.10;
  $('view').appendChild(renderer.domElement);
  renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();fatal('WebGL context lost. Reload the page to restart the view.');});
  const scene=new T.Scene();scene.background=new T.Color('#1d2a36');
  const camera=new T.PerspectiveCamera(65,innerWidth/innerHeight,.04,100);
  const ortho=new T.OrthographicCamera(-1,1,1,-1,.1,4);
  const pmrem=new T.PMREMGenerator(renderer),environment=new RoomEnvironment();
  const env=pmrem.fromScene(environment,.04);scene.environment=env.texture;scene.environmentIntensity=.08;
  environment.dispose();pmrem.dispose();
  const materials=createMaterials(renderer),model=createModel(scene,materials),lighting=createLighting(scene,model);
  const navigation=prepareNavigation(PLAN,model.collision);
  for(const room of PLAN.rooms)room.spawn=navigation.spawns[room.id];
  const cameraObstacles=[...model.shadowObjects,model.ceiling];
  model.neighbours.visible=false;

  // Fixed evening scene: a faint cool fill so the fittings carry the picture. There is no time-of-day control.
  materials.setDaylight(.08,10);
  const hemi=new T.HemisphereLight('#cfdcf2','#8e8573',.22);scene.add(hemi);
  const sun=new T.DirectionalLight('#9fb2da',.08);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);
  sun.shadow.camera.left=-11;sun.shadow.camera.right=11;sun.shadow.camera.top=11;sun.shadow.camera.bottom=-11;sun.shadow.camera.near=.1;sun.shadow.camera.far=65;
  sun.shadow.normalBias=.025;sun.shadow.bias=-.00008;sun.shadow.radius=3;scene.add(sun,sun.target);
  sun.target.position.set(4.7,0,7.7);sun.position.set(-9,22,-8).add(sun.target.position);
  // Reflected-ceiling-plan context: wall poche (visible from below only) and tray / panel outlines.
  const rcpPoche=new T.Group(),rcpLines=new T.Group();model.rcp.add(rcpPoche,rcpLines);
  {
    const poche=new T.MeshBasicMaterial({color:'#2b3b3f'}),lineA=new T.LineBasicMaterial({color:'#33474d',depthTest:false}),lineB=new T.LineBasicMaterial({color:'#b5833a',depthTest:false});
    const wallGeo=r=>{const g=new T.PlaneGeometry((r[2]-r[0])*FT,(r[3]-r[1])*FT);g.rotateX(Math.PI/2);g.translate((r[0]+r[2])/2*FT,PLAN.heights.band.value-.006,(r[1]+r[3])/2*FT);return g;};
    for(const w of PLAN.walls)rcpPoche.add(new T.Mesh(wallGeo(w.rect),poche));
    const loop=(pts,y,mat)=>{const g=new T.BufferGeometry().setFromPoints(pts.map(p=>new T.Vector3(p[0]*FT,y,p[1]*FT)));rcpLines.add(new T.LineLoop(g,mat));};
    for(const t of model.plan.trays)loop(t.ring,t.h+.004,lineB);
    for(const b of model.plan.baths){const [a,c,d,e]=b.panelRect;loop([[a,c],[d,c],[d,e],[a,e]],b.h+.004,lineB);}
    for(const z of model.plan.zones)loop(z.outline,z.h+.004,lineA);
  }

  // Frozen analytical heat maps (generic optics). They are never recomputed from the sliders.
  let analysis=null;
  if(heatSource&&PLAN.analysis){
    analysis=createAnalysis(JSON.parse(heatSource.textContent),PLAN.analysis);
    scene.add(analysis.group);
  }

  // Fixed finish decisions (no UI): painted art on the dining feature wall, track-spot variant, bath tile colours from the plan.
  for(const b of PLAN.bathrooms.rooms)model.setTiles(b.renderer_room_id,b.finishes.feature_colour);
  lighting.setFeature('track','art');
  model.features.track.visible=true;model.features.cylinders.visible=false;model.features.texture.visible=false;

  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const OVERVIEW={x:4.7,z:7.9};
  let mode='doll',fov=65;
  let yaw=0,pitch=0,pos=new T.Vector3(9.5*FT,0,46.4*FT),orbitYaw=.22,orbitPitch=1.12,orbitDistance=20;
  const orbitTarget=new T.Vector3(OVERVIEW.x,0,OVERVIEW.z),orbitGoal={x:OVERVIEW.x,z:OVERVIEW.z,distance:20};
  const rcp={x:OVERVIEW.x,z:OVERVIEW.z,half:8.6};
  let selectedRoom='living',guided=false,routeIndex=0,routePause=0,routeProgress=0,reducedStep=0,sheetPx=0;
  let mapScene='HIGH+LOW_100';
  const keys=new Set(),ray=new T.Raycaster();
  const path=navigation.path;
  const ROOM_ORDER=['balcony','living','dining','kitchen','utility','washing','master','dressing','bath1','lobby','bath2','children'];
  const rooms=[...PLAN.rooms].sort((a,b)=>{const i=ROOM_ORDER.indexOf(a.id),j=ROOM_ORDER.indexOf(b.id);return (i<0?99:i)-(j<0?99:j);});
  const roomById=id=>PLAN.rooms.find(r=>r.id===id);
  const roomName=id=>roomById(id)?.name||id;
  const lightRoomOf=id=>id==='washing'?'utility':id;
  const isWalk=()=>mode==='first'||mode==='third';

  const solidAt=(x,z,radius=WALK_RADIUS)=>model.collision.some(b=>b.y1>.16&&b.y0<1.65&&x>b.x0-radius&&x<b.x1+radius&&z>b.z0-radius&&z<b.z1+radius);
  function move(dx,dz){
    const steps=Math.max(1,Math.ceil(Math.hypot(dx,dz)/.08));
    for(let i=0;i<steps;i++){
      const x=pos.x+dx/steps,z=pos.z+dz/steps;
      if(x>.32&&x<9.02&&!solidAt(x,pos.z))pos.x=x;
      if(z>.25&&z<15.72&&!solidAt(pos.x,z))pos.z=z;
    }
  }
  const active=()=>mode==='rcp'?ortho:camera;
  function cancelGuided(){if(guided){guided=false;$('guided').textContent='Guided walk';}}

  // ---------- layout helpers ----------
  const portrait=matchMedia('(max-width:900px) and (orientation:portrait)');
  function syncSheet(){
    const collapsed=document.body.classList.contains('collapsed');
    sheetPx=portrait.matches&&!collapsed?Math.round($('desk').offsetHeight):0;
    document.documentElement.style.setProperty('--sheet',sheetPx+'px');
    layoutCameras();
  }
  function layoutCameras(){
    const w=innerWidth,h=innerHeight;
    camera.aspect=w/h;
    // On a phone the panel covers the lower part of the screen, so shift the picture up into the visible part.
    for(const c of [camera,ortho]){if(sheetPx>0)c.setViewOffset(w,h,0,sheetPx/2,w,h);else c.clearViewOffset();}
    camera.updateProjectionMatrix();
  }
  const overviewDistance=()=>{const a=innerWidth/Math.max(240,innerHeight-sheetPx);return a>=1.05?20:a>=.7?24:29;};

  // ---------- views ----------
  const VIEW_TEXT={first:'FIRST PERSON',third:'THIRD PERSON',doll:'DOLLHOUSE / ROOF OFF',heat:'LIGHT MAP / FROZEN ESTIMATE',rcp:'CEILING PLAN / LOOKING UP'};
  const HINT={
    first:'Drag to look / WASD or arrows to walk / Shift is faster',third:'Drag to look / WASD or arrows to walk / Shift is faster',
    doll:'Drag to orbit / scroll or pinch to zoom / tap a dot for fitting details',heat:'Drag to orbit / scroll or pinch to zoom',rcp:'Drag to pan / scroll or pinch to zoom / tap a dot for fitting details',
  };
  let hintTimer=0;
  function showHint(text){const h=$('hint');h.textContent=text;h.classList.remove('fade');clearTimeout(hintTimer);hintTimer=setTimeout(()=>h.classList.add('fade'),7000);}
  function syncView(){
    const doll=mode==='doll',heat=mode==='heat',plan=mode==='rcp',look=isWalk();
    model.world.visible=!plan;model.ceiling.visible=look||plan;model.lights.visible=look||plan||doll;
    model.grooves.visible=look||plan||doll;model.rcp.visible=plan;rcpPoche.visible=plan;
    model.avatar.visible=mode==='third';model.labels.visible=doll||heat||plan;model.labels.position.y=plan?2.25:0;
    model.fans.visible=true;model.neighbours.visible=false;model.markers.visible=doll||plan;
    model.features.painting.visible=!plan;
    if(analysis)analysis.show(heat);
    $('sec-map').hidden=!heat;
    for(const b of document.querySelectorAll('[data-view]')){const on=b.dataset.view===mode;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));}
    $('view-status').textContent=VIEW_TEXT[mode];showHint(HINT[mode]);
    if(look||heat)$('inspector').hidden=true;
    renderer.shadowMap.needsUpdate=true;
    if(heat)renderMap();
    layoutCameras();
  }
  function overviewPose(){
    orbitYaw=mode==='heat'?0:.22;orbitPitch=mode==='heat'?1.51:1.12;
    Object.assign(orbitGoal,{x:OVERVIEW.x,z:OVERVIEW.z,distance:overviewDistance()});
    orbitTarget.set(orbitGoal.x,0,orbitGoal.z);orbitDistance=orbitGoal.distance;
  }
  function setMode(value){
    if(!VIEW_TEXT[value])throw new Error('Unknown view '+value);
    const was=mode;mode=value;cancelGuided();keys.clear();
    if(value==='doll'||value==='heat'){
      if(was===value||was==='doll'||was==='heat'){orbitYaw=value==='heat'?0:.22;orbitPitch=value==='heat'?1.51:1.12;Object.assign(orbitGoal,{x:OVERVIEW.x,z:OVERVIEW.z,distance:overviewDistance()});}
      else overviewPose();
    }else if(value==='rcp'){fitRcp(selectedRoom==='balcony'?null:roomById(selectedRoom));}
    else if(roomAt(pos.x,pos.z)?.id!==selectedRoom){teleport(selectedRoom,true);}
    syncView();
  }
  function fitRcp(r){
    if(!r){rcp.x=OVERVIEW.x;rcp.z=OVERVIEW.z;rcp.half=8.6;return;}
    rcp.x=(r.rect[0]+r.rect[2])/2*FT;rcp.z=(r.rect[1]+r.rect[3])/2*FT;
    rcp.half=Math.max(2.4,Math.max((r.rect[3]-r.rect[1])*FT*.62,(r.rect[2]-r.rect[0])*FT*.62/(innerWidth/innerHeight)));
  }
  function focusOrbit(r){
    if(!r)return;
    const w=(r.rect[2]-r.rect[0])*FT,d=(r.rect[3]-r.rect[1])*FT;
    Object.assign(orbitGoal,{x:(r.rect[0]+r.rect[2])/2*FT,z:(r.rect[1]+r.rect[3])/2*FT,distance:T.MathUtils.clamp(Math.max(w,d)*1.9+3,10,26)});
    if(reduced){orbitTarget.set(orbitGoal.x,0,orbitGoal.z);orbitDistance=orbitGoal.distance;}
  }
  function teleport(id,quiet){
    const r=roomById(id);if(!r)return;
    cancelGuided();pos.set(r.spawn[0]*FT,0,r.spawn[1]*FT);
    if(solidAt(pos.x,pos.z)){
      let found=false;
      for(let dz=0;dz<1&&!found;dz+=.1)for(let dx=-.8;dx<=.8;dx+=.1)if(!solidAt(pos.x+dx,pos.z+dz)&&roomAt(pos.x+dx,pos.z+dz)?.id===id){pos.x+=dx;pos.z+=dz;found=true;break;}
    }
    const cx=(r.rect[0]+r.rect[2])/2*FT,cz=(r.rect[1]+r.rect[3])/2*FT,dx=cx-pos.x,dz=cz-pos.z;
    // Strip rooms and the balcony would otherwise face the open parapet / the street edge.
    const FACING={utility:Math.PI/2,washing:-Math.PI/2,balcony:0};
    yaw=id in FACING?FACING[id]:Math.hypot(dx,dz)>.6?Math.atan2(-dx,-dz):(id==='living'?.9:id==='dining'?1.45:id==='kitchen'?1.25:0);
    pitch=0;fov=65;camera.fov=65;camera.updateProjectionMatrix();keys.clear();
    if(!quiet)selectRoom(id,{moved:true});
  }

  // ---------- places ----------
  for(const r of rooms){const o=document.createElement('option');o.value=r.id;o.textContent=r.name;$('room').appendChild(o);}
  function selectRoom(id,{fromWalk=false,moved=false}={}){
    if(!roomById(id))return;
    selectedRoom=id;$('room').value=id;
    if(!fromWalk&&!moved){
      if(isWalk())teleport(id,true);
      else if(mode==='rcp')fitRcp(id==='balcony'?null:roomById(id));
      else focusOrbit(roomById(id));
    }
    syncLights();titleUpdate(true);
  }

  // ---------- room lights ----------
  const fmtK=a=>a&&a.length?a.map(k=>String(k).replace(/\s*K$/i,'')).join(' / ')+' K fixed':'';
  const INDEPENDENT_NAME={MIRROR:'mirror',FACE:'face',READ:'reading',STUDY:'study',ACCENT:'accent'};
  function syncMasterLights(){
    for(const lane of ['high','low']){
      const state=lighting.getMasterLight(lane),id='master-'+lane;
      $(id+'-on').checked=state.on;
      $(id+'-dim').value=state.dim;
      $(id+'-out').value=state.dim+'%';
      $('master-rail-'+lane).classList.toggle('off',!state.on);
    }
  }
  function syncLights(){
    syncMasterLights();
    const lr=lightRoomOf(selectedRoom),g=lighting.getRoomLight(lr);
    $('light-title').textContent='Lights / '+(lr!==selectedRoom?`${roomName(lr)} (incl. ${roomName(selectedRoom).toLowerCase()})`:roomName(lr));
    $('room-on').checked=g.on;$('room-on').disabled=g.held;
    $('room-on-label').textContent=g.held?'Room lights (on hold)':'Room lights';
    for(const lane of ['high','low']){
      const has=lane==='high'?g.hasHigh:g.hasLow,off=!has||g.held;
      $(lane+'-dim').value=g[lane];$(lane+'-dim').disabled=off;
      $(lane+'-out').value=has&&!g.held?g[lane]+'%':'--';
      $('rail-'+lane).classList.toggle('off',off);
      $(lane+'-cct').textContent=g.held?'Inactive placeholder':has?fmtK(g.cct[lane]):'No '+lane.toUpperCase()+' lane in this room';
    }
    const ids=lighting.members(lr),notes=[];
    if(g.held)notes.push('The fittings in this room are held for coordination.');
    else{
      const lanes=[...new Set(ids.filter(c=>!lighting.groupStates[c].fixtures.every(f=>f.held)).map(c=>lighting.groupStates[c].fixtures[0].lane))];
      const extra=lanes.filter(l=>!['READ','NIGHT'].includes(l)).map(l=>INDEPENDENT_NAME[l]).filter(Boolean);
      if(extra.length)notes.push(`Also on with the room, not dimmed here: ${extra.join(', ')}${g.cct.independent.length?' ('+fmtK(g.cct.independent)+')':''}.`);
      if(g.sharedLow.length)notes.push('The living and dining line profile shares one LOW level: the last slider moved wins.');
      if(g.zone==='CBR')notes.push('H1-H6 are active for review. The square CBR-X1 to CBR-X4 LINE frame is present but held for coordination, so it remains unlit and is not controlled by LOW; the four black slits are separate dark grooves, not light fittings. Bedside and desk fittings also remain held. C37 dimmer procurement remains on hold.');
    }
    const pockets=(PLAN.curtainPockets?.pockets||[]).filter(p=>p.room===g.zone);
    if(pockets.some(p=>p.selected))notes.push(pockets.filter(p=>p.selected).map(p=>`Curtain strip ${p.id} (${p.label}): selected for review, 2700 K; unmeasured 0-lumen visual placeholder, remains unlit and carries no lux credit.`).join(' '));
    if(pockets.some(p=>p.held))notes.push(`${pockets.filter(p=>p.held).map(p=>p.id).join(', ')} is held (shown grey, unlit).`);
    if(['MBR','CBR'].includes(g.zone))notes.push('Site hold: assumed strip return extends about 0.30 m beyond the modeled room corner. The viewer clips it only for display; actual pocket ends are unmeasured.');
    $('light-note').textContent=notes.join(' ');
    const individual=lighting.accessoryFixtures.filter(f=>f.room===g.zone),list=$('individual-list');
    $('individual-lights').hidden=individual.length===0;list.replaceChildren();
    for(const f of individual){
      const label=document.createElement('label'),input=document.createElement('input');
      label.className='accessory';label.textContent=`${f.id} / ${f.lane==='READ'?'reader':'PIR preview'}${f.held?' (held)':''}`;
      input.type='checkbox';input.checked=lighting.accessoryState[f.id];input.disabled=Boolean(f.held);input.dataset.individual=f.id;
      input.addEventListener('change',()=>{lighting.setAccessory(f.id,input.checked);syncLights();});
      label.appendChild(input);list.appendChild(label);
    }
  }
  function setRoomLight(id,values){
    const r=lighting.setRoomLight(lightRoomOf(id),values);syncLights();return r;
  }
  $('room-on').addEventListener('change',e=>setRoomLight(selectedRoom,{on:e.target.checked}));
  for(const lane of ['high','low'])$(lane+'-dim').addEventListener('input',e=>{
    const v=Number(e.target.value),g=lighting.getRoomLight(lightRoomOf(selectedRoom));
    setRoomLight(selectedRoom,{[lane]:v,...(!g.on&&v>0?{on:true}:{})});
  });
  for(const lane of ['high','low']){
    const id='master-'+lane;
    $(id+'-on').addEventListener('change',e=>{lighting.setMasterLight(lane,{on:e.target.checked});syncLights();});
    $(id+'-dim').addEventListener('input',e=>{
      const v=Number(e.target.value),state=lighting.getMasterLight(lane);
      lighting.setMasterLight(lane,{dim:v,...(!state.on&&v>0?{on:true}:{})});syncLights();
    });
  }

  // ---------- light-map (frozen) ----------
  function renderMap(){
    if(!analysis)return;
    const meta=PLAN.analysis,scene=analysis.scene||mapScene;
    for(const b of document.querySelectorAll('[data-map]')){const on=b.dataset.map===scene;b.classList.toggle('active',on);b.setAttribute('aria-pressed',String(on));}
    const label=meta.scenes.find(s=>s.id===scene)?.label||scene;
    $('map-note').textContent=`Frozen generic-optics estimate at ${label}. Provisional geometry, not measured, not recomputed by the sliders. UGR not calculated.`;
    const planes=[...new Set(meta.rooms.map(r=>r.plane_m))];
    $('lux-table').querySelector('tbody').innerHTML=meta.rooms.filter(r=>r.id!=='CBR').map(r=>{
      const s=r.stats?.[scene],n=v=>v==null||!Number.isFinite(v)?'--':Math.round(v);
      return `<tr title="${r.name}: grid plane ${r.plane_m} m, ceiling ${r.ceiling_m} m"><td>${r.name}</td><td>${s?n(s.avg):'--'}</td><td>${s?n(s.min):'--'}</td><td>${s&&Number.isFinite(s.U0)?s.U0.toFixed(2):'--'}</td></tr>`;
    }).join('');
    const c=meta.complianceCounts||{},k=meta.k2;
    $('map-flags').textContent=`Work plane ${planes.filter(p=>p>0).join(' / ')} m (baths and balcony at floor level). The older children\u2019s-room estimate is withheld; selected curtain strips have no lux credit. Checks vs criteria: ${c.PASS??0} pass, ${c.MARGINAL??0} marginal, ${c.HOLD??0} hold. K-2 kitchen worktop (selected for review): ${k.nominal}; marginal in sensitivity cases.`;
  }
  for(const b of document.querySelectorAll('[data-map]'))b.addEventListener('click',()=>{mapScene=b.dataset.map;analysis?.setScene(mapScene);renderMap();});
  if(analysis)analysis.setScene(mapScene);

  // ---------- fitting inspector ----------
  function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
  function showInspector(i){
    const st=lighting.groupStates[i.circuit],cct=i.cct==null?'n/a':String(i.cct).replace(/\s*K$/i,'')+' K fixed';
    $('inspector-body').innerHTML=`<p class="fine" style="margin:0 0 6px">${esc(i.status||'Review draft / not construction-released')}</p><div class="insp-id">${esc(i.id)}</div><div class="insp-kind">${esc(i.kind)}</div><dl>`+
      `<dt>Room</dt><dd>${esc(i.room)}</dd>`+
      `<dt>Colour temp.</dt><dd>${esc(cct)}${i.cctSource?`<br><small>${esc(i.cctSource)}</small>`:''}</dd>`+
      `<dt>Rail</dt><dd>${i.rail==='high'?'HIGH (main)':i.rail==='low'?'LOW (cove / mood)':'Independent circuit'} / ${esc(i.lane||i.layer)}</dd>`+
      `<dt>Circuit</dt><dd>${esc(i.circuit)}${st?` / ${st.on?st.dim+'%':'off'}`:''}${i.groupId?`<br><small>Brightness group ${esc(i.groupId)} (no colour control)</small>`:''}</dd>`+
      `<dt>Power</dt><dd>${i.W!=null?i.W+' W'+(i.length_m?` (${Number(i.length_m).toFixed(2)} m run)`:''):'n/a'}</dd>`+
      `<dt>Output</dt><dd>${i.candidate?'Not credited to the frozen lux estimate':i.lm!=null?Math.round(i.lm)+' lm':'n/a'}</dd>`+
      `<dt>Beam</dt><dd>${i.beam!=null?i.beam+'&deg;':'n/a'}</dd><dt>Ingress</dt><dd>${esc(i.ip)}</dd>${i.h_m!=null?`<dt>Mount height</dt><dd>${esc(i.h_m)} m</dd>`:''}${i.placementHoldIds?.length?`<dt>Site holds</dt><dd>${esc(i.placementHoldIds.join(', '))}</dd>`:''}</dl>${i.desc?`<p class="fine">${esc(i.desc)}</p>`:''}`;
    $('inspector').hidden=false;
  }
  function inspectAt(clientX,clientY){
    if(!model.markers.visible)return;
    const rect=renderer.domElement.getBoundingClientRect(),ndc=new T.Vector2((clientX-rect.left)/rect.width*2-1,-((clientY-rect.top)/rect.height)*2+1);
    ray.far=Infinity;ray.setFromCamera(ndc,active());
    const hit=ray.intersectObjects(model.markers.children.filter(s=>s.userData.fixture),false)[0];
    if(hit)showInspector(hit.object.userData.fixture);
  }
  $('close-inspector').addEventListener('click',()=>{$('inspector').hidden=true;});

  // ---------- camera ----------
  function cameraUpdate(){
    if(mode==='rcp'){
      const a=innerWidth/innerHeight;ortho.left=-rcp.half*a;ortho.right=rcp.half*a;ortho.top=rcp.half;ortho.bottom=-rcp.half;ortho.updateProjectionMatrix();
      ortho.up.set(0,0,-1);ortho.position.set(rcp.x,.35,rcp.z);ortho.lookAt(rcp.x,3,rcp.z);
    }else if(mode==='doll'||mode==='heat'){
      camera.position.set(orbitTarget.x+Math.sin(orbitYaw)*Math.cos(orbitPitch)*orbitDistance,orbitTarget.y+Math.sin(orbitPitch)*orbitDistance,orbitTarget.z+Math.cos(orbitYaw)*Math.cos(orbitPitch)*orbitDistance);
      camera.lookAt(orbitTarget);
    }else{
      const eye=new T.Vector3(pos.x,1.6,pos.z),forward=new T.Vector3(-Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),-Math.cos(yaw)*Math.cos(pitch));
      if(mode==='first'){camera.position.copy(eye);camera.lookAt(eye.clone().add(forward));}
      else{
        const desired=eye.clone().addScaledVector(forward,-1.8);desired.y+=.35;
        const delta=desired.clone().sub(eye),length=delta.length();ray.set(eye,delta.normalize());ray.far=length;
        const hit=ray.intersectObjects(cameraObstacles,true)[0];const distance=hit?Math.max(.12,hit.distance-.12):length;
        camera.position.copy(eye).addScaledVector(delta,distance);camera.lookAt(eye.clone().addScaledVector(forward,2));
      }
      model.avatar.position.copy(pos);model.avatar.rotation.y=yaw;
      if(mode==='third')model.avatar.visible=camera.position.distanceTo(eye)>.5;
    }
  }

  // ---------- panel wiring ----------
  for(const b of document.querySelectorAll('[data-view]'))b.addEventListener('click',()=>{
    if(b.dataset.view===mode&&(mode==='doll'||mode==='heat')){overviewPose();return;}
    setMode(b.dataset.view);
  });
  $('room').addEventListener('change',e=>selectRoom(e.target.value));
  $('collapse').addEventListener('click',()=>{document.body.classList.add('collapsed');$('collapse').setAttribute('aria-expanded','false');syncSheet();});
  $('restore').addEventListener('click',()=>{document.body.classList.remove('collapsed');$('collapse').setAttribute('aria-expanded','true');syncSheet();});
  $('help').addEventListener('click',()=>{$('help-dialog').showModal();keys.clear();});
  $('close-help').addEventListener('click',()=>$('help-dialog').close());
  $('guided').addEventListener('click',()=>{
    if(reduced){
      const p=path[reducedStep++%path.length];setMode('first');pos.set(p[0]*FT,0,p[1]*FT);$('guided').textContent='Next walk stop';return;
    }
    if(guided){cancelGuided();return;}
    setMode('first');guided=true;routeIndex=1;routePause=0;routeProgress=0;pos.set(path[0][0]*FT,0,path[0][1]*FT);$('guided').textContent='Stop walk';
  });
  for(const note of PLAN.surveyNotes){const li=document.createElement('li');li.textContent=note;$('about-notes').appendChild(li);}
  $('master-fingerprint').textContent='Source record SHA-256: '+PLAN.master.sha256+(PLAN.analysis?.source?.sha256?' / heat-map pack '+PLAN.analysis.source.sha256:'');
  addEventListener('resize',()=>{renderer.setSize(innerWidth,innerHeight);syncSheet();});
  if(typeof ResizeObserver==='function')new ResizeObserver(()=>syncSheet()).observe($('desk'));

  // ---------- keyboard, touch pad, pointer ----------
  function uiFocused(){return $('help-dialog').open||document.activeElement?.matches('input,select,textarea,[contenteditable=true]');}
  addEventListener('keydown',e=>{
    if(uiFocused()||e.ctrlKey||e.metaKey||e.altKey)return;
    const key=e.key.toLowerCase();
    if(['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright','shift'].includes(key)){e.preventDefault();keys.add(key);cancelGuided();}
    if(['1','2','3','4','5'].includes(key)){e.preventDefault();setMode({1:'first',2:'third',3:'doll',4:'heat',5:'rcp'}[key]);}
    if(key==='escape')$('inspector').hidden=true;
  });
  addEventListener('keyup',e=>keys.delete(e.key.toLowerCase()));
  addEventListener('blur',()=>{keys.clear();pointers.clear();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)keys.clear();});
  document.addEventListener('focusin',e=>{if(e.target.matches('input,select,textarea'))keys.clear();});
  for(const b of document.querySelectorAll('[data-pad]')){
    const k=b.dataset.pad,down=e=>{e.preventDefault();cancelGuided();keys.add(k);b.setPointerCapture?.(e.pointerId);},up=()=>keys.delete(k);
    b.addEventListener('pointerdown',down);b.addEventListener('pointerup',up);b.addEventListener('pointercancel',up);b.addEventListener('lostpointercapture',up);
    b.addEventListener('contextmenu',e=>e.preventDefault());
  }

  const pointers=new Map();let downX=0,downY=0,pinch=0,moved=false;
  const zoom=factor=>{
    if(mode==='doll'||mode==='heat')orbitDistance=T.MathUtils.clamp(orbitDistance*factor,8,37),orbitGoal.distance=orbitDistance;
    else if(mode==='rcp')rcp.half=T.MathUtils.clamp(rcp.half*factor,2,16);
  };
  const dom=renderer.domElement;
  dom.addEventListener('pointerdown',e=>{
    cancelGuided();pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});dom.setPointerCapture(e.pointerId);$('view').focus({preventScroll:true});
    if(pointers.size===1){downX=e.clientX;downY=e.clientY;moved=false;}
    if(pointers.size===2){const [a,b]=[...pointers.values()];pinch=Math.hypot(a.x-b.x,a.y-b.y);moved=true;}
  });
  dom.addEventListener('pointermove',e=>{
    const p=pointers.get(e.pointerId);if(!p)return;
    const dx=e.clientX-p.x,dy=e.clientY-p.y;p.x=e.clientX;p.y=e.clientY;
    if(Math.hypot(e.clientX-downX,e.clientY-downY)>5)moved=true;
    if(pointers.size>=2){
      const [a,b]=[...pointers.values()],d=Math.hypot(a.x-b.x,a.y-b.y);
      if(pinch>0&&(mode==='doll'||mode==='heat'||mode==='rcp'))zoom(pinch/d);
      pinch=d;return;
    }
    if(mode==='rcp'){const k=2*rcp.half/innerHeight;rcp.x+=dx*k;rcp.z-=dy*k;}
    else if(mode==='doll'||mode==='heat'){orbitYaw-=dx*.006;orbitPitch=T.MathUtils.clamp(orbitPitch+dy*.005,.25,Math.PI/2-.01);}
    else{yaw-=dx*.004;pitch=T.MathUtils.clamp(pitch-dy*.004,-1.4,1.4);}
  });
  const release=e=>{
    const had=pointers.delete(e.pointerId);if(pointers.size<2)pinch=0;
    if(had&&e.type==='pointerup'&&!moved&&pointers.size===0)inspectAt(e.clientX,e.clientY);
  };
  dom.addEventListener('pointerup',release);dom.addEventListener('pointercancel',release);
  dom.addEventListener('wheel',e=>{
    if(mode==='doll'||mode==='heat'||mode==='rcp'){e.preventDefault();zoom(Math.exp(e.deltaY*.001));}
  },{passive:false});

  // ---------- minimap (desktop) ----------
  const minimap=$('minimap'),ctx=minimap.getContext('2d');
  const bounds=PLAN.rooms.reduce((b,r)=>({x0:Math.min(b.x0,r.rect[0]),z0:Math.min(b.z0,r.rect[1]),x1:Math.max(b.x1,r.rect[2]),z1:Math.max(b.z1,r.rect[3])}),{x0:1e9,z0:1e9,x1:-1e9,z1:-1e9});
  const mm={pad:10,scale:Math.min((minimap.width-20)/(bounds.x1-bounds.x0),(minimap.height-20)/(bounds.z1-bounds.z0))};
  const mx=x=>mm.pad+(x-bounds.x0)*mm.scale,mz=z=>mm.pad+(z-bounds.z0)*mm.scale;
  function drawMinimap(){
    ctx.fillStyle='#e9eee5';ctx.fillRect(0,0,minimap.width,minimap.height);
    const here=roomAt(pos.x,pos.z)?.id;
    for(const r of PLAN.rooms){ctx.fillStyle=r.id===selectedRoom?'#bbd8c5':r.wet?'#d2e0db':'#f4f6ee';ctx.fillRect(mx(r.rect[0]),mz(r.rect[1]),(r.rect[2]-r.rect[0])*mm.scale,(r.rect[3]-r.rect[1])*mm.scale);}
    ctx.fillStyle='#637771';
    for(const w of PLAN.walls){const [x,z,X,Z]=w.rect;ctx.fillRect(mx(x),mz(z),Math.max(2,(X-x)*mm.scale),Math.max(2,(Z-z)*mm.scale));}
    for(const o of PLAN.openings){
      const w=PLAN.walls.find(w=>w.id===o.wall);if(!w)continue;const [x,z,X,Z]=w.rect;ctx.fillStyle=o.kind==='door'?'#f4f6ee':'#72aeb7';
      if(o.axis==='x')ctx.fillRect(mx(o.span[0]),mz(z),(o.span[1]-o.span[0])*mm.scale,Math.max(2,(Z-z)*mm.scale));
      else ctx.fillRect(mx(x),mz(o.span[0]),Math.max(2,(X-x)*mm.scale),(o.span[1]-o.span[0])*mm.scale);
    }
    if(isWalk()){
      ctx.save();ctx.translate(mx(pos.x/FT),mz(pos.z/FT));ctx.rotate(-yaw);
      ctx.fillStyle='#e6a742';ctx.beginPath();ctx.moveTo(0,-15);ctx.lineTo(-9,0);ctx.lineTo(9,0);ctx.closePath();ctx.fill();
      ctx.beginPath();ctx.arc(0,0,5,0,Math.PI*2);ctx.fillStyle='#173d42';ctx.fill();ctx.restore();
    }
    return here;
  }

  // ---------- titles ----------
  function titleUpdate(force){
    const r=roomById(selectedRoom);
    $('room-title').textContent=guided?path[Math.min(routeIndex,path.length-1)][2]:(mode==='heat'?'Light map / '+roomName(selectedRoom):roomName(selectedRoom));
    $('room-dim').textContent=isWalk()?(r?.dimension?.text||'Review draft / provisional placement'):mode==='rcp'?`Ceiling plan / left-right mirrored from the floor plan / heights assumed (band ${PLAN.heights.band.value} m)`:mode==='heat'?'Frozen generic-optics estimate / not recomputed / not construction-released':'Review draft / not construction-released';
  }

  // ---------- exports ----------
  const csvCell=v=>{v=v==null?'':String(v);return /[",\r\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;};
  const toCsv=rows=>'\ufeff'+rows.map(r=>r.map(csvCell).join(',')).join('\r\n')+'\r\n';
  function download(name,blob){
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.rel='noopener';document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href),5000);
  }
  const tag=PLAN.master.sha256.slice(0,8);
  function scheduleRows(){
    const header=['fixture_id','zone','room','lane','rail','circuit','type','description','fixed_cct_K','cct_source','master_cct_or_control','watts','lumens','beam_deg','ip','mount_height_m','x_ft_sheet','z_ft_sheet','length_m','finish','status','hold_reason','placement_hold_ids','note','review_status',...(PLAN.fixedCct.source?['cct_rule','map_layer','brightness_group']:[])];
    const rows=[header];
    for(const z of PLAN.fixtures.zones)for(const f of z.fixtures){
      rows.push([f.id,z.id,roomName(z.room),f.lane,f.rail,f.circuit,f.type,f.desc,String(f.cct??'').replace(/\s*K$/i,''),f.cctSource,f.masterCct,f.W_nominal??f.W,f.lm,f.beam_deg??f.beam,f.ip,f.mount_h_m,f.x_ft,f.z_ft,f.length_m,f.finish,f.held?'HELD / inactive':'review baseline',f.holdReason,f.placementHoldIds.join('; '),f.note,'REVIEW DRAFT - not a construction release',...(PLAN.fixedCct.source?[f.cctRule,f.mapLayer,f.groupId]:[])]);
    }
    for(const p of PLAN.curtainPockets.pockets.filter(p=>p.selected)){
      const z=PLAN.fixtures.zones.find(z=>z.id===p.room),[x,zf]=p.polylineFt[0];
      rows.push([p.id,p.room,roomName(z.room),'LOW','low',p.circuit,'CURTAIN_S1','Selected curtain-pocket strip','2700','Integrated S1 selection','2700K',p.watts,'','','IP20','',x,zf,p.indicativeLengthM,'','selected for review','H-CURTAIN-POCKET: site measurement and access open',p.placementHoldIds.join('; '),'No lux credit; no new knob','REVIEW DRAFT - not a construction release',...(PLAN.fixedCct.source?[p.cctRule,'LOW',p.groupId]:[])]);
    }
    return rows;
  }
  function groupRows(){
    const mapped=Boolean(PLAN.fixedCct.source);
    const rows=[['circuit','board','lane','rail','rooms','fixtures','control','control_device','dimming','fixed_cct_K','master_cct_or_control','watts_nominal','note','review_status',...(mapped?['brightness_group']:[])]];
    for(const c of PLAN.fixtures.controls.circuits){
      rows.push([c.circuit,c.board,c.lane,c.rail,[].concat(c.rooms||[]).join('; '),c.n_fixtures,c.control,c.control_device,c.dimming,[].concat(c.cct||[]).map(k=>String(k).replace(/\s*K$/i,'')).join(' / '),[].concat(c.masterCct??'').join(' / '),c.W_nominal,c.note,mapped?`REVIEW DRAFT - fixed CCT per fixed-CCT map ${PLAN.fixedCct.source.sha256.slice(0,8)}; brightness only`:'REVIEW DRAFT - fixed-CCT schedule provisional; control type per master pending fixed-CCT issue',...(mapped?[c.groupId]:[])]);
    }
    for(const p of PLAN.curtainPockets.pockets.filter(p=>p.selected)){
      rows.push([p.circuit,p.board,'LOW','low',p.room,1,'PWM','Existing room LOW knob','brightness only','2700','2700K',p.watts,`Selected S1; ${p.supply}; unmeasured; no lux credit`,'REVIEW DRAFT - not a construction release',...(mapped?[p.groupId]:[])]);
    }
    return rows;
  }
  function exportCsv(kind){
    const rows=kind==='groups'?groupRows():scheduleRows(),name=kind==='groups'?`circuit-groups-OPT1-${tag}.csv`:`fixture-schedule-OPT1-${tag}.csv`;
    const text=toCsv(rows);download(name,new Blob([text],{type:'text/csv;charset=utf-8'}));
    return {name,rows:rows.length-1,bytes:text.length};
  }
  async function exportPng(){
    const prev=renderer.getPixelRatio();
    let ratio=Math.min(2,Math.max(1.5,devicePixelRatio));
    const maxPx=6e6;if(innerWidth*innerHeight*ratio*ratio>maxPx)ratio=Math.sqrt(maxPx/(innerWidth*innerHeight));
    renderer.setPixelRatio(ratio);renderer.setSize(innerWidth,innerHeight);
    layoutCameras();cameraUpdate();
    const w0=renderer.domElement.width,h0=renderer.domElement.height,bar=Math.round(34*ratio);
    const c=document.createElement('canvas');c.width=w0;c.height=h0+bar;
    const g=c.getContext('2d');
    renderer.render(scene,active());g.drawImage(renderer.domElement,0,0);
    renderer.setPixelRatio(prev);renderer.setSize(innerWidth,innerHeight);
    g.fillStyle='#16343c';g.fillRect(0,h0,w0,bar);g.fillStyle='#eef5eb';g.textBaseline='middle';g.font=`${Math.round(12*ratio)}px "Segoe UI",Arial,sans-serif`;
    const nTotal=PLAN.fixtures.zones.reduce((n,z)=>n+z.fixtures.length,0)+PLAN.curtainPockets.selectedCount;
    g.fillText(`${VIEW_TEXT[mode].split(' / ')[0]} / ${roomName(selectedRoom)}  |  REVIEW DRAFT - not a construction release  |  fixed white  |  visual dimming only  |  ${nTotal} review fittings`,Math.round(12*ratio),h0+bar/2,w0-Math.round(24*ratio));
    const blob=await new Promise(res=>c.toBlob(res,'image/png'));
    const name=`light-planner-${mode}-${selectedRoom}.png`;download(name,blob);
    return {name,width:c.width,height:c.height,bytes:blob.size};
  }
  for(const d of PLAN.downloads||[]){
    const a=document.createElement('a');a.href=d.href;a.download=d.href.split('/').pop();a.target='_blank';a.rel='noopener';
    a.innerHTML=`${esc(d.label)}<small>${esc(d.note)} / PDF</small>`;$('pdf-links').appendChild(a);
  }

  // ---------- frame loop ----------
  let last=performance.now(),frames=0,frameElapsed=0,fps=0,tick=0;
  function frame(now){
    if($('fatal').style.display==='grid')return;
    const elapsed=Math.max(0,(now-last)/1000),dt=Math.min(.04,elapsed);last=now;
    if(!document.hidden){
      if(guided){
        const target=path[routeIndex],tx=target[0]*FT,tz=target[1]*FT,dx=tx-pos.x,dz=tz-pos.z,len=Math.hypot(dx,dz);
        if(len<.065){
          routePause+=dt;if(routePause>.65){routeIndex++;routePause=0;if(routeIndex>=path.length)cancelGuided();}
        }else{
          const rate=Math.min(dt*.95,len),before=pos.clone();move(dx/len*rate,dz/len*rate);
          const y=Math.atan2(-dx,-dz),delta=Math.atan2(Math.sin(y-yaw),Math.cos(y-yaw));yaw+=delta*(1-Math.exp(-dt*4));pitch=T.MathUtils.lerp(pitch,-.04,dt*3);
          routeProgress=before.distanceTo(pos)<.0001?routeProgress+dt:0;
          if(routeProgress>1.5){cancelGuided();$('hint').textContent='Walk paused at an obstruction. Pick a place to continue.';$('hint').classList.remove('fade');}
        }
      }else if(isWalk()){
        let f=(keys.has('w')||keys.has('arrowup')?1:0)-(keys.has('s')||keys.has('arrowdown')?1:0);
        let s=(keys.has('d')||keys.has('arrowright')?1:0)-(keys.has('a')||keys.has('arrowleft')?1:0);
        const norm=Math.hypot(f,s)||1,speed=(keys.has('shift')?2.7:1.35)*dt;f=f/norm*speed;s=s/norm*speed;
        move(-Math.sin(yaw)*f+Math.cos(yaw)*s,-Math.cos(yaw)*f-Math.sin(yaw)*s);
      }
      if(mode==='doll'||mode==='heat'){
        const t=reduced?1:1-Math.exp(-dt*5);
        orbitTarget.x+=(orbitGoal.x-orbitTarget.x)*t;orbitTarget.z+=(orbitGoal.z-orbitTarget.z)*t;orbitDistance+=(orbitGoal.distance-orbitDistance)*t;
      }
      materials.update(reduced?1:dt);model.update(reduced?1:dt,isWalk()?pos:null);lighting.update(reduced?1:dt);cameraUpdate();
      renderer.render(scene,active());
      frames++;frameElapsed+=elapsed;
      if(frameElapsed>=1){fps=frames/frameElapsed;$('perf').textContent=`${Math.round(fps)} fps / ${renderer.info.render.calls} draws`;frames=0;frameElapsed=0;}
      if(++tick%5===0){
        if(isWalk()){const r=roomAt(pos.x,pos.z);if(r&&r.id!==selectedRoom)selectRoom(r.id,{fromWalk:true});}
        if(!matchMedia('(max-width:900px)').matches)drawMinimap();
        titleUpdate();
      }
    }
    requestAnimationFrame(frame);
  }

  // Start with the review-active room lights on.
  lighting.setAllRooms(true);
  const query=new URLSearchParams(location.search);
  const startRoom=roomById(query.get('room'))?query.get('room'):'living';
  const startView=VIEW_TEXT[query.get('view')]?query.get('view'):'doll';
  selectedRoom=startRoom;$('room').value=startRoom;
  syncSheet();syncLights();
  if(startView!=='doll'){setMode(startView);}else{overviewPose();syncView();}
  if(query.get('room'))selectRoom(startRoom);
  titleUpdate(true);cameraUpdate();
  renderer.shadowMap.needsUpdate=true;renderer.compile(scene,camera);renderer.render(scene,active());
  $('loading').style.display='none';
  window.walkthrough={
    ready:true,PLAN,lighting,model,renderer,scene,camera,ortho,analysis,setMode,teleport:id=>{selectRoom(id);},selectRoom,
    setRoomLight,getRoomLight:id=>lighting.getRoomLight(lightRoomOf(id)),setAllRooms:on=>{lighting.setAllRooms(on);syncLights();},
    setMasterLight:(lane,values)=>{lighting.setMasterLight(lane,values);syncLights();},getMasterLight:lighting.getMasterLight,
    showInspector,syncLights,
    getState:()=>({mode,selectedRoom,position:pos.toArray(),yaw,pitch,fov,fps,draws:renderer.info.render.calls,triangles:renderer.info.render.triangles,guided,interiors:model.rooms.wardrobeProposals.interior.visible,orbit:{yaw:orbitYaw,pitch:orbitPitch,distance:orbitDistance,target:orbitTarget.toArray()},rcp:{...rcp},mapScene:analysis?.scene,sheetPx}),
    setPose:(x,z,y=0,p=0,f)=>{pos.set(x*FT,0,z*FT);yaw=y;pitch=p;if(f){fov=f;camera.fov=f;camera.updateProjectionMatrix();}cameraUpdate();},
    setOrbit:(y,p,d)=>{orbitYaw=y;orbitPitch=p;orbitDistance=d;orbitGoal.distance=d;cameraUpdate();},
    setRcp:(x,z,half)=>{rcp.x=x*FT;rcp.z=z*FT;rcp.half=half*FT;cameraUpdate();},fitRcp:id=>{fitRcp(roomById(id));cameraUpdate();},
    solidAt,move,path,navigation,
  };
  requestAnimationFrame(frame);
}
