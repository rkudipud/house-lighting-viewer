import * as T from 'three';

export function buildHall(c){
  const {m,PLAN,FT,metresRect,box,cylinder,ball,solid,world,glowMat,decalMat,planeGeo,chair,panelFrame}=c;
  const rec=kind=>PLAN.furniture.filter(f=>f.kind===kind);
  for(const f of rec('sofa')){
    const [x,z,X,Z]=metresRect(f.rect),r=metresRect(f.return),w=X-x,d=Z-z;
    solid(f.rect,.22,.34,m.fabric,true);solid(f.return,.22,.34,m.fabric,true);
    box(x+.11,.65,(z+Z)/2,.22,.62,d,m.fabric,world,true);
    box((r[0]+r[2])/2,.65,r[1]+.11,r[2]-r[0],.62,.22,m.fabric,world,true);
    box((x+X)/2,.51,Z-.08,w,.26,.16,m.fabric,world,true);
    box(r[2]-.08,.51,(r[1]+r[3])/2,.16,.26,r[3]-r[1],m.fabric,world,true);
    for(let i=0;i<4;i++)box((x+X)/2+.05,.46,z+(i+.5)*d/4,w-.3,.14,d/4-.02,m.fabric,world,true);
    box((r[0]+r[2])/2,.46,(r[1]+r[3])/2+.06,r[2]-r[0]-.12,.14,r[3]-r[1]-.3,m.fabric,world,true);
    for(const zz of [z+.65,Z-.6])box(x+.28,.67,zz,.15,.37,.42,m.accent,world,true);
  }
  for(const f of rec('coffee')){
    const [x,z,X,Z]=metresRect(f.rect);
    solid(f.rect,.43,.03,m.stone,true);
    for(const zz of [z+.23,Z-.23])cylinder((x+X)/2,.21,zz,.10,.41,m.metalDark);
  }
  for(const f of rec('rug')){
    const [x,z,X,Z]=metresRect(f.rect);box((x+X)/2,.027,(z+Z)/2,X-x,.016,Z-z,m.rug);
  }
  // Keep the existing mural-edge LOW glow without the competing mural pattern.
  const wx=2.249*FT+.004,z0=25.66*FT,z1=30.05*FT,mh=2.72;
  box(wx,mh/2,(z0+z1)/2,.006,mh,z1-z0,m.wall);
  for(const f of rec('tvunit')){
    const x=f.wallX*FT,z=f.z*FT;
    solid([f.wallX-f.depthM/FT,f.z-f.widthM/FT/2,f.wallX,f.z+f.widthM/FT/2],.42,.06,m.wood);
    box(x-.035,1.22,z,.05,.72,1.28,m.black);box(x-.062,1.22,z,.005,.68,1.24,m.screen);
  }
  for(const f of rec('dining')){
    const [x,z,X,Z]=metresRect(f.rect),cx=(x+X)/2,cz=(z+Z)/2,w=X-x,d=Z-z;
    solid(f.rect,.77,.045,m.wood,true);
    for(const xx of [x+.13,X-.13])for(const zz of [z+.13,Z-.13])box(xx,.37,zz,.045,.74,.045,m.wood);
    for(const xx of [x+w*.26,x+w*.74])for(const side of [-1,1]){
      chair(xx,cz+side*(d/2+.24),side<0?Math.PI:0);
      cylinder(xx,.802,cz+side*d*.27,.10,.012,m.white);
    }
    for(const side of [-1,1]){
      chair(cx+side*(w/2+.24),cz,side<0?-Math.PI/2:Math.PI/2);
      cylinder(cx+side*w*.4,.802,cz,.10,.012,m.white);
    }
  }

  const P=PLAN.pooja,wallIn=P.wallFaceM??2.249*FT,back=wallIn-P.depthMm/1000;
  const za=P.z[0]*FT,zb=P.z[1]*FT,zc=(za+zb)/2,nw=zb-za,sill=P.sillM,head=sill+P.heightMm/1000;
  if(P.frontOnly){
    const face=new T.Mesh(planeGeo,new T.MeshStandardMaterial({color:'#766f60',roughness:1}));
    face.scale.set(nw,head-sill,1);face.rotation.y=Math.PI/2;
    face.position.set(wallIn+.001,(sill+head)/2,zc);face.name='pooja-front-only';world.add(face);
    const cv=document.createElement('canvas');cv.width=512;cv.height=1429;
    const ctx=cv.getContext('2d');ctx.textAlign='center';
    ctx.fillStyle='#c2ab80';ctx.fillRect(112,250,288,405);ctx.fillStyle='#544d41';ctx.fillRect(129,267,254,371);
    ctx.strokeStyle='#d5bc8d';ctx.lineWidth=8;ctx.strokeRect(137,275,238,355);
    ctx.beginPath();ctx.arc(256,437,68,0,Math.PI*2);ctx.stroke();
    ctx.fillStyle='#d8c29a';
    for(const [x,scale] of [[174,.82],[256,1],[338,.82]]){
      ctx.beginPath();ctx.arc(x,690-60*scale,25*scale,0,Math.PI*2);ctx.fill();
      ctx.beginPath();ctx.moveTo(x-25*scale,690-25*scale);ctx.quadraticCurveTo(x,650-25*scale,x+25*scale,690-25*scale);
      ctx.lineTo(x+38*scale,710);ctx.lineTo(x-38*scale,710);ctx.closePath();ctx.fill();
    }
    ctx.strokeStyle='#eee9de';ctx.lineWidth=3;ctx.setLineDash([14,10]);
    ctx.beginPath();ctx.moveTo(25,720);ctx.lineTo(487,720);ctx.stroke();
    ctx.setLineDash([]);ctx.fillStyle='#eee9de';ctx.font='25px Segoe UI';
    ctx.fillText('CONCEPT ONLY / NOT TO SCALE',256,1080);
    ctx.fillText('Back, support and lighting held',256,1120);
    const texture=new T.CanvasTexture(cv);texture.colorSpace=T.SRGBColorSpace;
    const label=new T.Mesh(planeGeo,new T.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false}));
    label.scale.set(nw,head-sill,1);label.rotation.y=Math.PI/2;label.position.set(wallIn+.002,(sill+head)/2,zc);world.add(label);
    return {niche:{frontOnly:true,wallX:wallIn,projection:0,width:nw,sill,head,estimatedDepth:P.depthMm/1000,backModeled:false,lightingPlaced:false,display:'symbolic idols and framed picture; conceptual only',platform:'schematic annotation only',platformSolid:false},update(){}};
  }
  // This is a geometric hypothesis, not a masonry-cutting detail.
  const reveal=panelFrame(wallIn+P.trimM, (sill+head)/2, zc,nw,head-sill,Math.PI/2,m.wall,P.depthMm/1000+P.trimM,.018);
  reveal.name='pooja-reveal';
  const backing=new T.Mesh(planeGeo,m.stone);backing.scale.set(nw,head-sill,1);backing.rotation.y=Math.PI/2;
  backing.position.set(back+.003,(sill+head)/2,zc);world.add(backing);
  box((back+wallIn)/2,sill+.01,zc,wallIn-back,.02,nw,m.stone);
  // A shallow brass relief, rather than a projecting idol or freestanding props.
  const relief=new T.Mesh(planeGeo,m.poojaRelief);relief.scale.set(.24,.24,1);relief.rotation.y=Math.PI/2;
  relief.position.set(PLAN.fixtures.assumptions.niche.idol_face_x_ft*FT,1.1,zc);world.add(relief);relief.userData.nicheRelief=true;
  const p1=PLAN.fixtures.zones.find(z=>z.id==='LIV').fixtures.find(f=>f.id==='LIV-P1');
  const sx=p1.pts[0][0]*FT,a=p1.pts[0][1]*FT,b=p1.pts[1][1]*FT,top=p1.h_m,lo=p1.jamb_h[0];
  const glow=glowMat('living','pooja',2.8,'#ffe2b8');
  box(sx,top,(a+b)/2,.012,.012,b-a,glow);
  for(const zz of [a,b])box(sx,(lo+top)/2,zz,.012,top-lo,.012,glow);
  return {niche:{wallX:wallIn,backX:back,projection:P.trimM,depth:wallIn-back,stripX:sx},update(){}};
}
