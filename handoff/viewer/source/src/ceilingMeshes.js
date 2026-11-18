import * as T from 'three';
import {FT, channelOf} from './photometry.js';
import {offsetClosed, railsOpen,cornerPath,diagonalRadii} from './ceilings.js';

const P = ([x, z]) => new T.Vector2(x * FT, z * FT);
const pointInPoly = (x, z, p) => {
  let c = false;
  for (let i = 0, j = p.length - 1; i < p.length; j = i++)
    if ((p[i][1] > z) !== (p[j][1] > z) && x < (p[j][0] - p[i][0]) * (z - p[i][1]) / (p[j][1] - p[i][1]) + p[i][0]) c = !c;
  return c;
};

// A quad strip between two equal-length plan polylines (feet) at heights yA / yB (metres).
// u runs 0 (A) -> 1 (B); v follows the length along A in metres.
export function stripGeo(A, yA, B, yB, closed, normalizeV = false) {
  const n = A.length, pos = [], uv = [], idx = [];
  let run = 0;
  for (let i = 0; i < n; i++) {
    if (i) run += Math.hypot(A[i][0] - A[i - 1][0], A[i][1] - A[i - 1][1]) * FT;
    pos.push(A[i][0] * FT, yA, A[i][1] * FT, B[i][0] * FT, yB, B[i][1] * FT);
    uv.push(0, run, 1, run);
  }
  const segs = closed ? n : n - 1;
  if (normalizeV && run > 0) for (let i = 1; i < uv.length; i += 2) uv[i] /= run;
  for (let i = 0; i < segs; i++) {
    const a = i * 2, b = ((i + 1) % n) * 2;
    idx.push(a, a + 1, b, b, a + 1, b + 1);
  }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);g.computeVertexNormals();
  return g;
}

function weightedRingGeo(A, yA, B, yB, weight) {
  const pos = [], uv = [], colors = [], idx = [], n = A.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n, steps = Math.max(1, Math.ceil(Math.hypot(A[j][0] - A[i][0], A[j][1] - A[i][1]) * FT / .10));
    for (let k = 0; k < steps; k++) {
      const t = k / steps, lerp = (a, b) => a + (b - a) * t;
      const ax = lerp(A[i][0], A[j][0]), az = lerp(A[i][1], A[j][1]);
      const bx = lerp(B[i][0], B[j][0]), bz = lerp(B[i][1], B[j][1]);
      const w = weight([ax, az]);
      pos.push(ax * FT, yA, az * FT, bx * FT, yB, bz * FT);
      uv.push(0, .5, 1, .5);
      colors.push(w, w, w, w, w, w);
    }
  }
  const count = pos.length / 6;
  for (let i = 0; i < count; i++) {
    const a = i * 2, b = ((i + 1) % count) * 2;
    idx.push(a, a + 1, b, b, a + 1, b + 1);
  }
  const g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  g.setAttribute('color', new T.Float32BufferAttribute(colors, 3));
  g.setIndex(idx);g.computeVertexNormals();return g;
}

// Downward-facing flat polygon with optional holes (feet) at height y.
export function capGeo(outline, holes, y) {
  const sh = new T.Shape(outline.map(P));
  for (const h of holes) sh.holes.push(new T.Path(h.map(P)));
  const g = new T.ShapeGeometry(sh);g.rotateX(Math.PI / 2);g.translate(0, y, 0);
  return g;
}

export function buildCeilings(ctx) {
  const {plan, m, groups, glowMat, decalMat, registerDecal, PLAN} = ctx;
  const add = (group, geo, mat, order = 0) => {
    const o = new T.Mesh(geo, mat);o.castShadow = false;o.receiveShadow = true;o.renderOrder = order;group.add(o);return o;
  };
  const trays = Object.fromEntries(plan.trays.map(t => [t.key, t]));
  const info = {trays: [], lin: [], grooves: [], baths: [], pockets: []};
  function coveWash(ring,y,room,circuit,hall){
    const pad=.25/FT,xs=ring.map(p=>p[0]),zs=ring.map(p=>p[1]);
    const x0=Math.min(...xs)-pad,x1=Math.max(...xs)+pad,z0=Math.min(...zs)-pad,z1=Math.max(...zs)+pad;
    const canvas=document.createElement('canvas'),pixels=96;
    canvas.width=Math.ceil((x1-x0)*FT*pixels);canvas.height=Math.ceil((z1-z0)*FT*pixels);
    const g=canvas.getContext('2d'),X=x=>(x-x0)/(x1-x0)*canvas.width,Z=z=>(z-z0)/(z1-z0)*canvas.height;
    g.beginPath();ring.forEach((p,i)=>i?g.lineTo(X(p[0]),Z(p[1])):g.moveTo(X(p[0]),Z(p[1])));g.closePath();
    g.lineJoin='round';g.lineCap='round';g.lineWidth=2;g.strokeStyle='rgba(255,255,255,.55)';
    g.shadowColor='rgba(255,255,255,.9)';g.shadowBlur=.55*pixels;g.stroke();
    g.shadowBlur=.22*pixels;g.stroke();
    if(hall){
      g.shadowColor='transparent';g.globalCompositeOperation='destination-in';
      const gradient=g.createLinearGradient(0,Z(25.3-.15/FT),0,Z(25.3+.15/FT));
      gradient.addColorStop(0,room==='living'?'rgba(255,255,255,0)':'#fff');
      gradient.addColorStop(1,room==='living'?'#fff':'rgba(255,255,255,0)');
      g.fillStyle=gradient;g.fillRect(0,0,canvas.width,canvas.height);
    }
    const tex=new T.CanvasTexture(canvas);tex.colorSpace=T.SRGBColorSpace;
    const mat=registerDecal(room,'low',circuit,new T.MeshBasicMaterial({map:tex,color:'#000',transparent:true,blending:T.AdditiveBlending,depthWrite:false,toneMapped:false,side:T.DoubleSide}),.35);
    const geo=capGeo(ring,[],y),pos=geo.attributes.position,uv=geo.attributes.uv;
    for(let i=0;i<pos.count;i++)uv.setXY(i,(pos.getX(i)/FT-x0)/(x1-x0),1-(pos.getZ(i)/FT-z0)/(z1-z0));
    add(groups.lights,geo,mat,3);
  }
  const selectedPockets=(PLAN.curtainPockets?.pockets||[]).filter(p=>p.selected);
  for (const z of plan.zones) {
    const xs=z.outline.map(p=>p[0]),zs=z.outline.map(p=>p[1]),bounds=[Math.min(...xs),Math.min(...zs),Math.max(...xs),Math.max(...zs)];
    const pocketHoles=[];
    for (const p of selectedPockets) {
      const room=PLAN.fixtures.zones.find(q=>q.id===p.room)?.room;
      if(!z.rooms.includes(room))continue;
      const [a,b]=p.polylineFt;
      if(Math.abs(a[0]-b[0])>1e-6||!p.pocketWidthM||!p.intoRoomSign)throw new Error('Unsupported curtain pocket geometry '+p.id);
      const half=p.pocketWidthM/(2*FT),margin=.02;
      const raw=[a[0]-half,Math.min(a[1],b[1]),a[0]+half,Math.max(a[1],b[1])];
      const r=[Math.max(raw[0],bounds[0]+margin),Math.max(raw[1],bounds[1]+margin),Math.min(raw[2],bounds[2]-margin),Math.min(raw[3],bounds[3]-margin)];
      if(r[2]-r[0]<.12/FT||r[3]-r[1]<.3/FT)throw new Error('Curtain pocket is outside its ceiling '+p.id);
      const hole=[[r[0],r[1]],[r[2],r[1]],[r[2],r[3]],[r[0],r[3]]];
      pocketHoles.push(hole);
      add(groups.ceiling,capGeo(hole,[],z.h+.07),m.ceiling);
      add(groups.ceiling,stripGeo(hole,z.h,hole,z.h+.07,true),m.ceilingDS);
      const near=p.intoRoomSign>0?r[0]+.035/FT:r[2]-.035/FT;
      for(const d of [0,.045/FT]){
        const x=near+p.intoRoomSign*d,path=[[x,r[1]+.03],[x,r[3]-.03]],rail=railsOpen(path,.003/FT);
        add(groups.ceiling,stripGeo(rail.L,z.h+.063,rail.R,z.h+.063,false),m.opalTrim);
      }
      info.pockets.push({id:p.id,room,rect:r,ceiling:z.h,displayClipped:r.some((v,i)=>Math.abs(v-raw[i])>1e-6),unmeasured:true});
    }
    add(groups.ceiling, capGeo(z.outline, [...z.holes.map(k => trays[k].ring),...pocketHoles], z.h), m.ceiling);
  }
  const k=plan.kitchen,beam=[[k.x[0],k.beam],[k.x[1],k.beam]];
  add(groups.ceiling,stripGeo(beam,plan.band,beam,k.h,false),m.ceilingDS);
  const kit=PLAN.fixtures.zones.find(z=>z.id==='KIT').fixtures.find(f=>f.id==='KIT-L1');
  const slot=railsOpen(kit.pts,PLAN.design.grooveM/2/FT),halo=railsOpen(kit.pts,.45/FT);
  add(groups.ceiling,stripGeo(slot.L,k.h-.002,slot.R,k.h-.002,false),m.groove);
  add(groups.lights,stripGeo(slot.L,k.h-.004,slot.R,k.h-.004,false),glowMat('kitchen','low',.8,undefined,kit.circuit),4);
  add(groups.lights,stripGeo(halo.L,k.h-.003,halo.R,k.h-.003,false,true),decalMat('kitchen','low','glowFeather',.22,kit.circuit),3);
  info.kitchen={flat:true,h:k.h,stepCount:k.stepHeld?null:1,stepHeld:k.stepHeld,step: k.step,stripId:kit.id,lengthM:kit.length_m};

  // Balcony soffit (the slab of the floor above) so the surface-mounted balcony lights have something to sit on.
  const bal = PLAN.rooms.find(r => r.id === 'balcony').rect;
  add(groups.ceiling, capGeo([[bal[0], bal[1]], [bal[2], bal[1]], [bal[2], bal[3]], [bal[0], bal[3]]], [], plan.band), m.ceiling);

  // Stepped trays: riser (2.70 -> 2.88), soffit, soft cove light on the soffit and up the riser.
  for (const t of plan.trays) {
    const ring = t.ring;
    add(groups.ceiling, stripGeo(ring, t.band, ring, t.h, true), m.ceilingDS);
    add(groups.ceiling, capGeo(ring, [], t.h), m.ceiling);
    const rise=offsetClosed(ring,.003),n=ring.length;
    const owners=t.key==='HALL'?['dining','living']:[t.roomOf(ring[0])];
    for(const room of owners){
      const zone=PLAN.fixtures.zones.find(z=>z.room===room),f=zone?.fixtures.find(f=>f.lane==='COVE');
      if(!f)throw new Error('Missing scheduled cove for '+room);
      const weight=p=>{
        if(t.key!=='HALL')return 1;
        const q=T.MathUtils.clamp((p[1]-25.3)*FT/.30+.5,0,1),blend=q*q*(3-2*q);
        return room==='living'?blend:1-blend;
      };
      coveWash(ring,t.h-.004,room,f.circuit,t.key==='HALL');
      add(groups.lights,weightedRingGeo(rise,t.h,rise,t.band+.01,weight),decalMat(room,'low','glowEdge',.24,f.circuit,true),5);
    }
    info.trays.push({key: t.key, points: n, source: t.source,radii:t.cornerRadii,ring:t.ring,continuous:true});
  }

  // Flush linear L-profiles (LINE circuit), from the lighting schedule.
  for (const zone of PLAN.fixtures.zones) for (const f of zone.fixtures) {
    if (f.type !== 'LIN' || !f.pts) continue;
    const y = f.h_m ?? zone.ceil_m, room = zone.room, {L, R} = railsOpen(f.pts, 0.026 / FT), halo = railsOpen(f.pts, 0.28 / FT);
    add(groups.ceiling, stripGeo(L, y - .002, R, y - .002, false), m.opalTrim);
    const c = railsOpen(f.pts, 0.0105 / FT), ch = channelOf(f);
    add(groups.lights, stripGeo(c.L, y - .004, c.R, y - .004, false), glowMat(room, ch, 1.1, undefined, f.circuit), 6);
    add(groups.lights, stripGeo(halo.L, y - .003, halo.R, y - .003, false, true), decalMat(room, ch, 'glowFeather', .14, f.circuit), 5);
    info.lin.push({id: f.id, y});
  }

  // Black-painted shadow grooves (assumed unlit), selectable on/off.
  for (const t of plan.trays) for (const original of t.linesBlack) {
    const path=plan.style==='sharp'&&original.length>3?[original[0],[original[0][0],original.at(-1)[1]],original.at(-1)]:original;
    const {L, R} = railsOpen(path, PLAN.design.grooveM/2/FT);
    add(groups.grooves, stripGeo(L, plan.band - .003, R, plan.band - .003, false), m.groove, 3);
    info.grooves.push({tray: t.key});
  }

  // Bathrooms: 2.52 m slab with a 100 mm perimeter recess, dropped 2.40 m panel, IP65 strip washing the wall tiles.
  for (const b of plan.baths) {
    const [x0, z0, x1, z1] = b.rect, [px0, pz0, px1, pz1] = b.panelRect;
    const outer = [[x0, z0], [x1, z0], [x1, z1], [x0, z1]], panel = cornerPath([[px0,pz0],[px1,pz0],[px1,pz1],[px0,pz1]],diagonalRadii(4,PLAN.design.radiusM/FT,b.style));
    add(groups.ceiling, capGeo(outer, [panel], b.recessH), m.ceiling);
    add(groups.ceiling, capGeo(panel, [], b.h), m.ceiling);
    add(groups.ceiling, stripGeo(panel, b.h, panel, b.recessH, true), m.ceilingDS);
    const perimeter=PLAN.fixtures.zones.find(z=>z.room===b.id).fixtures.find(f=>f.type==='BCOVE');
    const rails=railsOpen(perimeter.pts,.04/FT);
    add(groups.lights,stripGeo(rails.L,b.recessH-.004,rails.R,b.recessH-.004,false),decalMat(b.id,'perim','glowCenter',.25,perimeter.circuit),4);
    const edge = .004, wy0 = b.h - .85, wy1 = b.h;
    // wall wash: one plane per wall, bright at the top, fading toward the tiles below.
    const walls = [
      {pos: [(x0 + x1) / 2, (z0 + edge) , 0], w: x1 - x0, rot: 0},
      {pos: [(x0 + x1) / 2, (z1 - edge), 0], w: x1 - x0, rot: Math.PI},
      {pos: [x1 - edge, (z0 + z1) / 2, 0], w: z1 - z0, rot: -Math.PI / 2},
    ];
    for (const w of walls) {
      const g = new T.PlaneGeometry(w.w * FT, wy1 - wy0);
      const o = add(groups.lights, g, decalMat(b.id, 'perim', 'glowDown', .5,perimeter.circuit), 4);
      o.position.set(w.pos[0] * FT, (wy0 + wy1) / 2, w.pos[1] * FT);o.rotation.y = w.rot;
    }
    info.baths.push({id: b.id, panel: b.panelRect, h: b.h});
  }
  return info;
}
