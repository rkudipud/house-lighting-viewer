import * as T from 'three';
import {FT, sourceHeight, aimVector, channelOf} from './photometry.js';
import {ipRating} from './lighting.js';
import {stripGeo} from './ceilingMeshes.js';
import {roomFloorRegions} from './master-adapter.js';

const KIND = {
  DL6: 'cob', DL7: 'cob', DL8: 'cob', DL10: 'cob', DL6A: 'gimbal', DL8A: 'gimbal', DL8D: 'opal', DL10D: 'opal',
  SPOT3: 'spot', SPOT5W: 'spotw', PIN3: 'pin', PIN6:'micro', CYLS: 'cyl', IP65W: 'cyl', BULK: 'bulk', FACE: 'face', UPDN: 'updn',
  READ: 'read', STEP: 'step', PEND: 'pend', TRK6: 'track', TRK6W: 'track', TRKLIN: 'track', CYL6: 'hang'
};
Object.assign(KIND,{DL8V:'cob',DL7V:'cob',DL6V:'cob',SPOT7V:'spotw',SPOT5V:'spotw',SPOT3V:'spot',BSPOT8V:'cob',BDIF9V:'opal',FACEV:'face',FACE10V:'faceh',PIN6V:'micro',CYLSV:'cyl',UPDNV:'updn',BULKD:'bulk'});
export const KIND_LABEL = {
  cob: 'Downlight', gimbal: 'Adjustable downlight', opal: 'Diffused downlight', spot: 'Spotlight',
  spotw: 'Recessed spotlight', pin: 'Pinhole spotlight', micro:'Micro spotlight', cyl: 'Surface cylinder', bulk: 'Bulkhead', face: 'Vertical mirror light',faceh:'Horizontal mirror light',
  updn: 'Up-down wall light', read: 'Reading light', step: 'Night step light', pend: 'Decorative pendant', track: 'Magnetic-track head', hang: 'Hanging directional cylinder'
};
const MARKERS = {
  downlight: {color: '#0072b2', shape: 'circle'},
  directional: {color: '#b0206c', shape: 'triangle'},
  linear: {color: '#d55e00', shape: 'diamond'},
  wall: {color: '#007b53', shape: 'square'},
};

function markerType(f) {
  if (f.pts || f.type === 'CURTAIN_S1') return 'linear';
  const kind = KIND[f.type];
  if (['spot', 'spotw', 'pin', 'micro', 'track', 'hang'].includes(kind)) return 'directional';
  if (['cob', 'gimbal', 'opal', 'cyl', 'bulk'].includes(kind)) return 'downlight';
  return 'wall';
}

function pathMidpoint(points) {
  const lengths = points.slice(1).map((p, i) => Math.hypot(p[0] - points[i][0], p[1] - points[i][1]));
  let remaining = lengths.reduce((a, b) => a + b, 0) / 2;
  for (let i = 0; i < lengths.length; i++) {
    if (remaining <= lengths[i] && lengths[i] > 0) {
      const t = remaining / lengths[i];
      return points[i].map((n, axis) => n + (points[i + 1][axis] - n) * t);
    }
    remaining -= lengths[i];
  }
  return points[0];
}

export const fixtureInfo = (f, zone, cat) => {
  const spec = cat?.[f.type] || {};
  return {id: f.id, room: zone.name, layer: f.layer, type: f.type, kind: KIND_LABEL[KIND[f.type]] || (f.pts ? 'LED strip' : f.type), desc: spec.desc || f.mount || f.note || '',
    W: f.W, lm: f.lm, beam: f.beam, cct: f.cct,cctSource:f.cctSource,cctRule:f.cctRule,groupId:f.groupId,masterCct:f.masterCct,rail:f.rail,lane:f.lane,held:Boolean(f.held),placementHoldIds:f.placementHoldIds,ip:f.ip,circuit:f.circuit,length_m: f.length_m, h_m: f.h_m,status:f.holdReason};
};

export function buildFixtures(env) {
  const {PLAN, plan, m, groups, glowMat, decalMat, mk, v, line} = env;
  const G = {};
  const geo = (key, make) => G[key] || (G[key] = make());
  const disc = r => geo('disc' + r, () => new T.CylinderGeometry(r, r, .004, 20));
  const cyl = (r, h, seg = 16) => geo(`cyl${r}_${h}_${seg}`, () => new T.CylinderGeometry(r, r, h, seg));
  const bx = (w, h, d) => geo(`box${w}_${h}_${d}`, () => new T.BoxGeometry(w, h, d));
  const dome = r => geo('dome' + r, () => new T.SphereGeometry(r, 20, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2));
  const markers = [], inspect = [];
  const zoneOf = new Map();
  const inTray = (x, z) => plan.trays.some(t => {
    let c = false, p = t.ring;
    for (let i = 0, j = p.length - 1; i < p.length; j = i++) if ((p[i][1] > z) !== (p[j][1] > z) && x < (p[j][0] - p[i][0]) * (z - p[i][1]) / (p[j][1] - p[i][1]) + p[i][0]) c = !c;
    return c;
  });

  // Marker textures encode fixture type as well as color; a dashed ring indicates a hold.
  const dotTex = {};
  const dot = (type, held) => dotTex[`${type}-${held}`] || (dotTex[`${type}-${held}`] = (() => {
    const c = document.createElement('canvas');c.width = c.height = 64;const g = c.getContext('2d');
    const {color, shape} = MARKERS[type];
    g.beginPath();
    if (shape === 'circle') g.arc(32, 32, 15, 0, Math.PI * 2);
    else if (shape === 'triangle') {g.moveTo(32, 15);g.lineTo(49, 47);g.lineTo(15, 47);g.closePath();}
    else if (shape === 'diamond') {g.moveTo(32, 14);g.lineTo(49, 32);g.lineTo(32, 50);g.lineTo(15, 32);g.closePath();}
    else g.rect(17, 17, 30, 30);
    g.fillStyle = color;g.fill();g.lineWidth = 6;g.strokeStyle = '#fff';g.stroke();
    g.lineWidth = 2;g.strokeStyle = '#172c33';g.stroke();
    if (held) {g.beginPath();g.arc(32, 32, 28, 0, Math.PI * 2);g.setLineDash([5, 3]);g.lineWidth = 4;g.strokeStyle = '#172c33';g.stroke();}
    const t = new T.CanvasTexture(c);t.colorSpace = T.SRGBColorSpace;return t;
  })());
  function addMarker(info, type, x, y, z) {
    if (![x, y, z].every(Number.isFinite)) throw new Error('Missing fixture marker position for ' + info.id);
    const s = new T.Sprite(new T.SpriteMaterial({map: dot(type, Boolean(info.held)), depthTest: false, transparent: true, toneMapped: false}));
    s.position.set(x, y, z);s.scale.set(.32, .32, 1);s.renderOrder = 30;
    s.userData.fixture = info;s.userData.markerType = type;
    markers.push(s);groups.markers.add(s);
  }
  function marker(f, zone, x, y, z) {
    addMarker(fixtureInfo(f, zone, PLAN.fixtures.cat), markerType(f), x, y, z);
  }
  function labels() {
    if (groups.markers.userData.labelled) return;
    groups.markers.userData.labelled = true;
    for (const s of markers) {
      const i = s.userData.fixture, c = document.createElement('canvas');c.width = 256;c.height = 50;const g = c.getContext('2d');
      g.fillStyle = 'rgba(22,40,36,.86)';g.fillRect(0, 0, 256, 50);g.fillStyle = '#fff';g.textAlign = 'center';g.font = '600 22px Consolas';
      g.fillText(`${i.id}  ${i.lm ?? ''} lm`, 128, 32);
      const t = new T.CanvasTexture(c);t.colorSpace = T.SRGBColorSpace;
      const l = new T.Sprite(new T.SpriteMaterial({map: t, depthTest: false, transparent: true}));
      l.position.set(0, -.8, 0);l.scale.set(4.2, .82, 1);s.add(l);
    }
  }
  groups.markers.userData.ensureLabels = labels;

  const g0 = new T.Group();
  function placed(parent, x, y, z) {const o = new T.Group();o.position.set(x, y, z);parent.add(o);return o;}
  const aimQuat = (a) => new T.Quaternion().setFromUnitVectors(new T.Vector3(0, -1, 0), new T.Vector3(a[0], a[1], a[2]));

  for (const zone of PLAN.fixtures.zones) {
    const room = zone.room;
    for (const f of zone.fixtures) {
      if(f.held){
        if(zone.id==='CBR'){
          const [x,z]=f.pts?pathMidpoint(f.pts):[f.x,f.z];
          marker(f,zone,x*FT,f.h_m??zone.ceil_m,z*FT);
        }
        continue;
      }
      const glowMat=(r,ch,gain,color)=>env.glowMat(r,ch,gain,color,f.circuit);
      const ch = channelOf(f), cat = PLAN.fixtures.cat[f.type];
      if (f.pts) {
        const [mx,mz] = pathMidpoint(f.pts);
        // Strip-type fixtures with their own builders: COVE and LIN (ceiling), BCOVE / NICHE / VANITY (baths), LIV-P1 (pooja niche), TASKW (utility shelf)
        if (['COVE_TW', 'COVE_FW', 'LIN', 'BCOVE', 'NICHE', 'VANITY'].includes(f.type) || f.id === 'LIV-P1') {marker(f, zone, mx * FT, f.h_m ?? zone.ceil_m, mz * FT);continue;}
        const y = f.h_m ?? (f.type === 'BACK' ? 1.5 : f.type === 'PLINTH' ? .13 : zone.plane_m + .55), gm = glowMat(room, ch, 3);
        for (let i = 1; i < f.pts.length; i++)
          line(v(f.pts[i - 1][0] * FT, y, f.pts[i - 1][1] * FT), v(f.pts[i][0] * FT, y, f.pts[i][1] * FT), .009, gm, groups.lights);
        marker(f, zone, mx * FT, y, mz * FT);
        continue;
      }
      if (f.id.startsWith('FW-')) continue;
      const kind = KIND[f.type];
      const x = f.x * FT, z = f.z * FT, hs = sourceHeight(f, zone, 0, 'low');
      const host = groups.ceiling;
      const high = ch === 'high' || ch === 'study';
      const gain = high ? 1.4 : 1.6;
      if (kind === 'cob') {
        mk(disc(.066), m.opalTrim, x, hs - .003, z, host);
        mk(disc(.046), m.groove, x, hs - .0055, z, host);
        mk(disc(.029), glowMat(room, ch, gain), x, hs - .008, z, host);
      } else if (kind === 'gimbal') {
        mk(cyl(.074, .008), m.steel, x, hs - .004, z, host);
        const grp = placed(host, x, hs - .018, z);
        grp.quaternion.copy(aimQuat(aimVector(f, hs)));
        mk(cyl(.056, .062), m.groove, 0, -.02, 0, grp);
        mk(cyl(.058, .006), m.steel, 0, -.052, 0, grp);
        mk(disc(.04), glowMat(room, ch, gain), 0, -.056, 0, grp);
      } else if (kind === 'opal') {
        mk(cyl(.098, .006), m.opalTrim, x, hs - .003, z, host);
        const d = mk(dome(1), glowMat(room, ch, 1.7), x, hs - .006, z, host);d.scale.set(.082, .042, .082);
      } else if (kind === 'spot') {
        mk(cyl(.05, .007), m.steel, x, hs - .0035, z, host);
        mk(disc(.034), m.groove, x, hs - .0065, z, host);
        mk(disc(.02), glowMat(room, ch, gain), x, hs - .009, z, host);
      } else if (kind === 'spotw') {
        mk(cyl(.056, .007), m.black, x, hs - .0035, z, host);
        mk(disc(.04), m.groove, x, hs - .0065, z, host);
        mk(disc(.024), glowMat(room, ch, gain), x, hs - .009, z, host);
      } else if(kind==='micro'){
        mk(disc(.04),m.groove,x,hs-.003,z,host);
        const head=placed(host,x,hs-.008,z);head.quaternion.copy(aimQuat(aimVector(f,hs)));
        mk(cyl(.025,.025),m.black,0,-.006,0,head);
        mk(disc(.012),glowMat(room,ch,3),0,-.02,0,head);
      } else if (kind === 'pin') {
        mk(cyl(.026, .006), m.black, x, hs - .003, z, host);
        mk(disc(.008), glowMat(room, ch, 4), x, hs - .006, z, host);
      } else if (kind === 'cyl') {
        mk(cyl(.05, .12), m.white, x, hs - .06, z, host);
        mk(cyl(.056, .01), m.steel, x, hs - .002, z, host);
        mk(disc(.038), glowMat(room, ch, gain), x, hs - .121, z, host);
      } else if (kind === 'bulk') {
        mk(bx(.38, .016, .13), m.black, x, hs - .008, z, host);
        mk(geo('bulk', () => new T.CapsuleGeometry(.04, .24, 4, 10).rotateZ(Math.PI / 2)), glowMat(room, ch, 1.5, '#e9edf0'), x, hs - .05, z, host);
        mk(bx(.04, .04, .105), m.steel, x - .16, hs - .018, z, host);mk(bx(.04, .04, .105), m.steel, x + .16, hs - .018, z, host);
      } else if (kind === 'face'||kind==='faceh') {
        const d = aimVector(f, hs), alongX = Math.abs(d[0]) > .5,horizontal=kind==='faceh';
        const w=horizontal?.60:.04,h=horizontal?.04:.5;
        mk(bx(alongX?.026:w,h,alongX?w:.026),m.steel,x,hs,z,host);
        mk(bx(alongX?.018:w-.012,h-.012,alongX?w-.012:.018),glowMat(room,ch,2.4,'#f4f1ea'),x+d[0]*.016,hs,z+d[2]*.016,host);
      } else if (kind === 'updn') {
        mk(bx(.08, .17, .07), m.black, x, hs, z + .036, host);
        mk(bx(.056, .008, .02), glowMat(room, ch, 3), x, hs + .088, z + .045, host);
        mk(bx(.056, .008, .02), glowMat(room, ch, 3), x, hs - .088, z + .045, host);
        const up = new T.Mesh(env.planeGeo, decalMat(room, ch, 'glowPool', .45));up.scale.set(.62, .8, 1);up.position.set(x, hs + .45, z + .004);groups.lights.add(up);
        const dn = new T.Mesh(env.planeGeo, decalMat(room, ch, 'glowPool', .45));dn.scale.set(.62, .8, 1);dn.position.set(x, hs - .45, z + .004);groups.lights.add(dn);
        up.renderOrder = dn.renderOrder = 5;
      } else if (kind === 'read') {
        mk(cyl(.012, .1), m.brassTrim, x, hs + .02, z, host);
        mk(cyl(.05, .07), m.brassTrim, x, hs - .03, z, host);
        mk(disc(.038), glowMat(room, ch, 2.6), x, hs - .066, z, host);
      } else if (kind === 'step') {
        mk(bx(.1, .045, .028), m.steel, x, hs, z, host);
        mk(bx(.07, .012, .012), glowMat(room, ch, 3), x, hs - .01, z + .018, host);
      } else if (kind === 'pend') {
        const top = inTray(f.x, f.z) ? plan.tray : plan.band, fy = f.hang_m, shade = fy + .27;
        line(v(x, shade, z), v(x, top, z), .006, m.black, host);
        mk(geo('pendShade', () => new T.CylinderGeometry(.2, .3, .26, 28, 1, true)), m.shadeDS || m.shade, x, fy + .13, z, host);
        mk(disc(.26), glowMat(room, ch, 1.8, '#f6e9d0'), x, fy + .01, z, host);
        mk(cyl(.07, .02), m.brassTrim, x, top - .01, z, host);
      }else if(!kind){
        throw new Error('No current fitting mesh for '+f.type);
      }
      marker(f, zone, x, kind === 'pend' ? f.hang_m : f.hang_m ?? hs, z);
    }
  }

  const lightEffects={floorPools:[],wallScallops:[],ceilingHalos:[]};
  for(const zone of PLAN.fixtures.zones){
    const down=zone.fixtures.filter(f=>!f.held&&f.lane==='HIGH'&&['cob','gimbal','opal','spot','spotw','micro','pin','cyl'].includes(KIND[f.type])&&Number.isFinite(f.x)&&Number.isFinite(f.z));
    const rects=PLAN.rooms.filter(r=>r.id===zone.room||(zone.room==='utility'&&r.id==='washing')).flatMap(roomFloorRegions).map(r=>r.rect);
    if(!down.length||!rects.length)continue;
    const bounds=[Math.min(...rects.map(r=>r[0])),Math.min(...rects.map(r=>r[1])),Math.max(...rects.map(r=>r[2])),Math.max(...rects.map(r=>r[3]))];
    const spanX=bounds[2]-bounds[0],spanZ=bounds[3]-bounds[1];
    for(const circuit of [...new Set(down.map(f=>f.circuit))]){
      const fixtures=down.filter(f=>f.circuit===circuit),canvas=document.createElement('canvas');
      canvas.width=Math.min(768,Math.max(128,Math.ceil(spanX*FT*96)));
      canvas.height=Math.min(768,Math.max(128,Math.ceil(spanZ*FT*96)));
      const g=canvas.getContext('2d'),X=x=>(x-bounds[0])/spanX*canvas.width,Z=z=>(z-bounds[1])/spanZ*canvas.height;
      g.beginPath();for(const r of rects)g.rect(X(r[0]),Z(r[1]),X(r[2])-X(r[0]),Z(r[3])-Z(r[1]));g.clip();
      for(const f of fixtures){
        const h=sourceHeight(f,zone,0,'low'),radius=T.MathUtils.clamp(h*Math.tan((f.beam||60)*Math.PI/360)*.75,.45,1.15)/FT;
        g.save();g.translate(X(f.x),Z(f.z));g.scale(radius/spanX*canvas.width,radius/spanZ*canvas.height);
        const grad=g.createRadialGradient(0,0,0,0,0,1);grad.addColorStop(0,'rgba(255,255,255,.32)');grad.addColorStop(.38,'rgba(255,255,255,.20)');grad.addColorStop(.72,'rgba(255,255,255,.06)');grad.addColorStop(1,'rgba(255,255,255,0)');
        g.fillStyle=grad;g.fillRect(-1,-1,2,2);g.restore();
      }
      const tex=new T.CanvasTexture(canvas);tex.colorSpace=T.SRGBColorSpace;
      const mat=env.registerDecal(zone.room,'high',circuit,new T.MeshBasicMaterial({map:tex,color:'#000',transparent:true,blending:T.AdditiveBlending,depthWrite:false,toneMapped:false,side:T.DoubleSide}),.8);
      const pool=new T.Mesh(new T.PlaneGeometry(spanX*FT,spanZ*FT),mat);pool.rotation.x=-Math.PI/2;
      pool.position.set((bounds[0]+bounds[2])*FT/2,.021,(bounds[1]+bounds[3])*FT/2);pool.renderOrder=3;groups.lights.add(pool);
      lightEffects.floorPools.push({room:zone.room,circuit,fixtures:fixtures.map(f=>f.id),mat});
    }
    for(const f of down){
      const x=f.x*FT,z=f.z*FT,h=sourceHeight(f,zone,0,'low');
      const halo=new T.Mesh(env.planeGeo,decalMat(zone.room,'high','glowRadial',.12,f.circuit));
      halo.rotation.x=-Math.PI/2;halo.scale.set(.30,.30,1);halo.position.set(x,h-.012,z);halo.renderOrder=5;groups.lights.add(halo);
      lightEffects.ceilingHalos.push(f.id);
      let nearest=null;
      for(const wall of PLAN.walls){
        const [x0,z0,x1,z1]=wall.rect.map(n=>n*FT),horizontal=x1-x0>z1-z0;
        const along=horizontal?x:z,lo=horizontal?x0:z0,hi=horizontal?x1:z1;
        if(along<lo+.15||along>hi-.15)continue;
        const normal=horizontal?z:x,faces=horizontal?[z0,z1]:[x0,x1],face=faces.reduce((a,b)=>Math.abs(normal-a)<Math.abs(normal-b)?a:b);
        const distance=Math.abs(normal-face);
        if(distance>.65||distance<.03||(nearest&&distance>=nearest.distance))continue;
        if(PLAN.openings.some(o=>o.wall===wall.id&&along>(o.span[0]*FT-.35)&&along<(o.span[1]*FT+.35)))continue;
        nearest={wall:wall.id,horizontal,face,distance,side:Math.sign(normal-face)};
      }
      if(nearest){
        const wash=new T.Mesh(env.planeGeo,decalMat(zone.room,'high','glowPool',.22,f.circuit));
        wash.scale.set(.80,.85,1);wash.position.set(nearest.horizontal?x:nearest.face+nearest.side*.006,h-.43,nearest.horizontal?nearest.face+nearest.side*.006:z);
        if(!nearest.horizontal)wash.rotation.y=Math.PI/2;
        wash.renderOrder=5;groups.lights.add(wash);lightEffects.wallScallops.push({id:f.id,wall:nearest.wall});
      }
    }
  }

  // The selected S1 strips are visual only and do not enter the frozen photometry.
  const curtainPockets = [];
  for (const p of PLAN.curtainPockets?.pockets || []) {
    const zone = PLAN.fixtures.zones.find(z => z.id === p.room), y = PLAN.heights.band.value - .018;
    const info = {id: p.id, room: zone.name, kind: 'Curtain-pocket LED strip', cct: p.cct, cctSource: `${p.cctRule}: fixed warm 2700 K`, rail: 'low', lane: 'LOW', circuit: p.circuit,
      held: p.held, placementHoldIds:p.placementHoldIds, W: p.wEnvelope, length_m: p.indicativeLengthM, ip: 'IP20', candidate: true, groupId: p.groupId,
      status: p.held ? `HELD (${p.status}): shown grey and unlit until released.`
        : `Selected for review (${p.label}): follows ${p.groupId} (room LOW slider). Additional to the 104 photometric fittings; indicative length, no lux credit.`};
    const mat = p.held ? new T.MeshBasicMaterial({color: '#8d8d8d', transparent: true, opacity: .55, depthWrite: false})
      : env.glowMat(zone.room, 'low', .6, '#efdcbc', p.circuit);
    const pocket=env.pocketInfo.find(q=>q.id===p.id);
    if(p.selected&&!pocket)throw new Error('Missing recessed pocket for '+p.id);
    const path=pocket?[[p.polylineFt[0][0],pocket.rect[1]],[p.polylineFt.at(-1)[0],pocket.rect[3]]]:p.polylineFt;
    for (let i = 1; i < path.length; i++) {
      const a = v(path[i - 1][0] * FT, y, path[i - 1][1] * FT), b = v(path[i][0] * FT, y, path[i][1] * FT);
      if (!p.held) {line(a, b, .006, mat, groups.lights);continue;}
      const n = Math.max(2, Math.round(a.distanceTo(b) / .16));
      for (let k = 0; k < n; k += 2) line(a.clone().lerp(b, k / n), a.clone().lerp(b, (k + 1) / n), .006, mat, groups.lights);
    }
    if(p.selected){
      const [a,b]=path, wash=new T.Mesh(env.planeGeo,decalMat(zone.room,'low','curtainWash',.32,p.circuit));
      wash.scale.set(Math.abs(b[1]-a[1])*FT,.85,1);wash.rotation.y=Math.PI/2;
      wash.position.set(a[0]*FT+p.intoRoomSign*.008,y-.43,(a[1]+b[1])*FT/2);wash.renderOrder=6;groups.lights.add(wash);
    }
    const [mx,mz] = pathMidpoint(path);
    addMarker(info, 'linear', mx * FT, y, mz * FT);
    curtainPockets.push({id: p.id, held: p.held, selected:p.selected, circuit: p.circuit, room: zone.room, mat,displayClipped:pocket?.displayClipped??false});
  }

  // Fans: geometry only. Downrod from the tray soffit when inside a tray, otherwise from the 2.70 m band.
  for (const fan of plan.fans) {
    const [fx, fz] = [fan.at[0] * FT, fan.at[1] * FT], top = inTray(fan.at[0], fan.at[1]) ? plan.tray : plan.band, dy = 2.36;
    mk(cyl(.027, top - dy, 10), m.white, fx, (top + dy) / 2, fz, groups.fans);
    mk(cyl(.075, .05, 16), m.white, fx, top - .02, fz, groups.fans);
    const hub = mk(geo('hub', () => new T.SphereGeometry(1, 14, 8)), m.white, fx, dy, fz, groups.fans);hub.scale.set(.12, .05, .12);
    for (let i = 0; i < 3; i++) {
      // Blade tip at half the planning sweep where one is recorded; otherwise the generic 1.14 m illustration.
      const tip = fan.sweepM ? fan.sweepM / 2 : .57, len = tip - .03, mid = (tip + .03) / 2;
      const a = i * Math.PI * 2 / 3, b = mk(geo('blade' + len.toFixed(3), () => new T.BoxGeometry(.13, .022, len)), m.white, fx + Math.sin(a) * mid, dy, fz + Math.cos(a) * mid, groups.fans);
      b.rotation.y = a - .18;
    }
  }

  // Only the installed canonical track arrangement is represented.
  const fx = {track: new T.Group(), cylinders: new T.Group(), painting: new T.Group(), texture: new T.Group()};
  const cfg=PLAN.fixtures.inputs.calc_geometry.art_wall;
  const wallX=PLAN.walls.find(w=>w.id==='dressing-west').rect[0]*FT;
  const own = (grp, geo2, mat, x, y, z) => {const o = new T.Mesh(geo2, mat);o.position.set(x, y, z);o.castShadow = false;grp.add(o);return o;};
  {
    const zone=PLAN.fixtures.zones.find(z=>z.id==='DIN'),heads=zone.fixtures.filter(f=>f.id.startsWith('FW-'));
    const tx=cfg.track_x_ft*FT,z0=Math.min(...heads.map(f=>f.z))*FT-.29,z1=Math.max(...heads.map(f=>f.z))*FT+.175;
    const mount=PLAN.heights.band.value;
    own(fx.track, bx(.05, .014, z1 - z0), m.black, tx, mount-.007, (z0 + z1) / 2);
    own(fx.track, bx(.02, .004, z1 - z0), m.steel, tx, mount-.001, (z0 + z1) / 2);
    for (const f of heads) {
      const zz = f.z * FT;
      marker(f,zone,f.x*FT,f.h_m??zone.ceil_m,zz);
      if (f.type === 'TRKLIN') {
        own(fx.track, bx(.03, .03, .3), m.black, tx, 2.68, zz);
        const lin = own(fx.track, bx(.02, .006, .26), glowMat('dining', 'art', 3, '#f6ecdc',f.circuit), tx, 2.662, zz);lin.name = f.id;
        continue;
      }
      const headY=(f.h_m??mount)-.035;
      const head = new T.Group();head.position.set(tx, headY, zz);head.quaternion.copy(aimQuat(aimVector(f, headY)));
      fx.track.add(head);
      own(head, cyl(.036, .1), m.black, 0, -.045, 0);
      own(head, cyl(.04, .008), m.steel, 0, -.098, 0);
      own(head, disc(.028), glowMat('dining', 'art', 3.6,undefined,f.circuit), 0, -.1, 0);
      own(fx.track, cyl(.008, .03), m.black, tx, mount-.02, zz);
    }
    const pz=cfg.art_zc_ft*FT,pg=fx.painting;
    env.panelFrame(wallX-.052,cfg.art_yc_m,pz,cfg.art_w_m,cfg.art_h_m,-Math.PI/2,m.metalDark,.015,.02,pg);
    const cv=new T.Mesh(env.planeGeo,m.painting);cv.scale.set(cfg.art_w_m,cfg.art_h_m,1);cv.rotation.y=-Math.PI/2;cv.position.set(wallX-.047,cfg.art_yc_m,pz);pg.add(cv);
  }
  fx.track.name = 'feature-track';fx.cylinders.name = 'feature-cylinders';

  return {markers, features: fx, ensureLabels: labels, curtainPockets,lightEffects};
}
