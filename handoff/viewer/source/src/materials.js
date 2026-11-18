import * as T from 'three';

export const STYLES = [
  {name:'Quiet Warm',subtitle:'Oak / linen / warm-grey stone',wall:'#eee9de',wood:'#b19a79',fabric:'#e7e2d7',accent:'#6e796b',cabinet:'#ddd8cd',stone:'#bcb7aa',floor:'#d8d4c9',rug:'#c2beb2',metal:'#74756d',floorType:'stone',floorRough:.44},
  {name:'Quiet Earth',subtitle:'Oak / taupe / same stone',wall:'#e5dfd3',wood:'#9f886c',fabric:'#ded7c9',accent:'#817867',cabinet:'#d1c9ba',stone:'#bcb7aa',floor:'#d8d4c9',rug:'#bcb5a7',metal:'#74756d',floorType:'stone',floorRough:.44},
  {name:'Quiet Sage',subtitle:'Oak / sage / same stone',wall:'#e6e9df',wood:'#b4a083',fabric:'#e2e4d9',accent:'#6e796b',cabinet:'#cbd2c4',stone:'#bcb7aa',floor:'#d8d4c9',rug:'#c0c6b8',metal:'#74756d',floorType:'stone',floorRough:.44},
];

export function createMaterials(renderer) {
  let seed=919; const rnd=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  const textures={};
  function texture(kind,size=256) {
    const c=document.createElement('canvas');c.width=c.height=size;
    const g=c.getContext('2d');g.fillStyle='#e5e0d6';g.fillRect(0,0,size,size);
    if(kind==='wood'){
      g.fillStyle='#d6c5ae';g.fillRect(0,0,size,size);
      for(let j=0;j<210;j++){
        const y=rnd()*size;g.beginPath();g.moveTo(0,y);g.strokeStyle=`rgba(60,34,14,${.02+rnd()*.16})`;g.lineWidth=.3+rnd()*1.5;
        for(let x=0;x<=size;x+=8)g.lineTo(x,y+Math.sin(x*.035+j)*1.6+Math.sin(x*.09+j)*.5);
        g.stroke();
      }
      for(let i=0;i<5;i++){g.strokeStyle='#a69780';g.globalAlpha=.17;g.beginPath();g.ellipse(rnd()*256,rnd()*256,28+rnd()*24,3,0,0,Math.PI*2);g.stroke();}g.globalAlpha=1;
    } else if(kind==='marble'){
      g.fillStyle='#f5f4ef';g.fillRect(0,0,size,size);
      for(let j=0;j<12;j++){
        let y=rnd()*size;g.beginPath();g.moveTo(0,y);g.strokeStyle=`rgba(93,94,83,${.04+rnd()*.12})`;g.lineWidth=.25+rnd()*1.2;
        for(let x=0;x<=size;x+=8){y+=rnd()*13-6;g.lineTo(x,y);}g.stroke();
      }
      g.strokeStyle='#b6b5ae';g.lineWidth=.65;g.strokeRect(0,0,size,size);
    } else if(kind==='cane'){
      g.fillStyle='#d8c9a3';g.fillRect(0,0,size,size);
      for(let y=0;y<size;y+=12)for(let x=0;x<size;x+=12){
        g.fillStyle='#857457';g.fillRect(x+4,y+4,5,5);
        g.strokeStyle='#f0dfb9';g.lineWidth=2;g.beginPath();g.moveTo(x,y+2);g.lineTo(x+12,y+2);g.moveTo(x+2,y);g.lineTo(x+2,y+12);g.stroke();
      }
    } else if(kind==='fabric'||kind==='rug'){
      g.fillStyle=kind==='rug'?'#d4cabb':'#f3eee4';g.fillRect(0,0,size,size);
      for(let y=0;y<size;y+=3){g.fillStyle=`rgba(60,50,30,${.03+rnd()*.08})`;g.fillRect(0,y,size,1);}
      for(let x=0;x<size;x+=3){g.fillStyle=`rgba(65,60,44,${.02+rnd()*.07})`;g.fillRect(x,0,1,size);}
    } else {
      g.fillStyle=kind==='tile'?'#eee9df':'#c9c8bd';g.fillRect(0,0,size,size);
      for(let i=0;i<(kind==='terrazzo'?900:5000);i++){
        const a=kind==='terrazzo'?1.8+rnd()*4:.5+rnd();
        g.fillStyle=['#eee9df','#8f978e','#b1a391','#646e68'][i%4];g.globalAlpha=kind==='terrazzo'?.6:.18;
        g.fillRect(rnd()*size,rnd()*size,a,a*(.5+rnd()));
      }g.globalAlpha=1;
      if(kind==='tile'){g.strokeStyle='#9e9e93';g.lineWidth=1.5;g.strokeRect(0,0,size,size);}
    }
    const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;t.wrapS=t.wrapT=T.RepeatWrapping;t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());return t;
  }
  ['wood','marble','fabric','rug','stone','tile','terrazzo','cane'].forEach(k=>textures[k]=texture(k));
  const m={};const mk=(key,color,roughness=.65,map,metalness=0)=>m[key]=new T.MeshStandardMaterial({color,roughness,metalness,map:map?textures[map]:null});
  mk('wall',STYLES[0].wall,.85);mk('ceiling','#f2efe7',.9);mk('wood',STYLES[0].wood,.4,'wood');
  mk('fabric',STYLES[0].fabric,.94,'fabric');mk('accent',STYLES[0].accent,.9,'fabric');mk('cabinet',STYLES[0].cabinet,.29);
  mk('chairBack',STYLES[0].fabric,.88,'fabric');mk('shade',STYLES[0].fabric,.76,'fabric');
  mk('stone',STYLES[0].stone,.44,'stone');mk('marble',STYLES[0].stone,.44,'stone');
  mk('rug',STYLES[0].rug,1,'rug');mk('metal',STYLES[0].metal,.3,null,.75);
  mk('black','#242c2b',.32);mk('white','#f0ece4',.26);mk('ceramic','#dedbd1',.23);mk('leaf','#496340',.83);
  mk('stem','#645037',.9);mk('soil','#332b20',1);mk('terracotta','#a6664a',.85);
  mk('tile','#ddddcf',.55,'tile');mk('frame','#403b30',.5);mk('steel','#d4d7d2',.23,null,.8);
  mk('art','#e4d6b8',.9);mk('skyline','#b6b5a6',1);mk('ground','#8b9d88',1);
  m.glass=new T.MeshPhysicalMaterial({color:'#dce8dc',transparent:true,opacity:.20,roughness:.08,metalness:.12,side:T.DoubleSide,depthWrite:false});
  m.windowGlass=m.glass.clone();
  m.sheer=new T.MeshStandardMaterial({color:'#fff7e8',roughness:1,transparent:true,opacity:.39,side:T.DoubleSide,depthWrite:false});
  m.mirror=new T.MeshStandardMaterial({color:'#c5d3ca',roughness:.055,metalness:1});
  m.screen=new T.MeshStandardMaterial({color:'#142027',roughness:.13,metalness:.3,emissive:'#122527',emissiveIntensity:.22});
  for(const [key,type,scale] of [['wood','wood',.002],['fabric','fabric',.002],['accent','fabric',.002],['stone','stone',.0015]]){
    const t=textures[type].clone();t.colorSpace=T.NoColorSpace;m[key].roughnessMap=t;m[key].bumpMap=t;m[key].bumpScale=scale;
  }
  const floorMaterials=[];let target=0;
  function floor(w,d,wet=false){
    const tex=textures.stone.clone();tex.repeat.set(w/1.2,d/1.2);
    const a=new T.MeshStandardMaterial({color:STYLES[target].floor,map:tex,roughness:wet?.84:STYLES[target].floorRough,metalness:wet?0:.05,envMapIntensity:wet?.2:.7});
    floorMaterials.push({a,w,d,wet});return a;
  }
  function setStyle(index){
    target=index;
    m.chairBack.map=textures.fabric;m.shade.map=textures.fabric;
    for(const f of floorMaterials){if(f.wet)continue;f.a.map.dispose();f.a.map=textures[STYLES[index].floorType].clone();f.a.map.repeat.set(f.w/1.2,f.d/1.2);}
  }
  function update(dt){
    const s=STYLES[target],t=1-Math.exp(-dt*7);
    for(const key of ['wall','wood','fabric','accent','cabinet','stone','rug','metal'])m[key].color.lerp(new T.Color(s[key]),t);
    m.tufted.color.lerp(new T.Color(s.fabric),t);
    for(const key of ['chairBack','shade'])m[key].color.lerp(new T.Color(s.fabric),t);
    for(const f of floorMaterials)if(!f.wet){f.a.color.lerp(new T.Color(s.floor),t);f.a.roughness=T.MathUtils.lerp(f.a.roughness,s.floorRough,t);}
  }
  const dayGlass=new T.Color('#dce8dc'),nightGlass=new T.Color('#04101e'),glassTarget=new T.Color();
  // Greyscale glow ramps used by additive decals (cove light on soffits, linear halos, wall washes, floor pools).
  function ramp(w,h,paint){
    const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d');paint(g,w,h);
    const t=new T.CanvasTexture(c);t.colorSpace=T.SRGBColorSpace;t.wrapS=t.wrapT=T.ClampToEdgeWrapping;return t;
  }
  const stops=(g,gr,list)=>{for(const [o,c] of list)gr.addColorStop(o,c);g.fillStyle=gr;};
  textures.glowEdge=ramp(128,4,(g,w,h)=>{stops(g,g.createLinearGradient(0,0,w,0),[[0,'#fff'],[.08,'#f4f4f4'],[.28,'#8a8a8a'],[.62,'#262626'],[1,'#000']]);g.fillRect(0,0,w,h);});
  textures.glowCenter=ramp(128,4,(g,w,h)=>{stops(g,g.createLinearGradient(0,0,w,0),[[0,'#000'],[.3,'#262626'],[.44,'#bcbcbc'],[.5,'#fff'],[.56,'#bcbcbc'],[.7,'#262626'],[1,'#000']]);g.fillRect(0,0,w,h);});
  textures.glowFeather=ramp(128,128,(g,w,h)=>{
    const im=g.createImageData(w,h);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const cross=Math.exp(-Math.pow((x/(w-1)-.5)/.22,2)*2), end=Math.min(1,y/(h*.12),(h-1-y)/(h*.12));
      const value=Math.round(255*cross*end*end*(3-2*end)),i=(y*w+x)*4;
      im.data[i]=im.data[i+1]=im.data[i+2]=value;im.data[i+3]=255;
    }
    g.putImageData(im,0,0);
  });
  textures.curtainWash=ramp(256,128,(g,w,h)=>{
    const im=g.createImageData(w,h);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const end=Math.min(1,x/(w*.06),(w-1-x)/(w*.06)),fall=Math.pow(1-y/(h-1),2);
      const value=Math.round(255*fall*end*end*(3-2*end)),i=(y*w+x)*4;
      im.data[i]=im.data[i+1]=im.data[i+2]=value;im.data[i+3]=255;
    }
    g.putImageData(im,0,0);
  });
  textures.glowDown=ramp(4,128,(g,w,h)=>{stops(g,g.createLinearGradient(0,0,0,h),[[0,'#fff'],[.12,'#d8d8d8'],[.4,'#6a6a6a'],[.75,'#1a1a1a'],[1,'#000']]);g.fillRect(0,0,w,h);});
  textures.glowUp=ramp(4,128,(g,w,h)=>{stops(g,g.createLinearGradient(0,0,0,h),[[0,'#000'],[.25,'#1a1a1a'],[.6,'#6a6a6a'],[.88,'#d8d8d8'],[1,'#fff']]);g.fillRect(0,0,w,h);});
  textures.glowRadial=ramp(128,128,(g,w,h)=>{stops(g,g.createRadialGradient(w/2,h/2,2,w/2,h/2,w/2),[[0,'#fff'],[.3,'#a8a8a8'],[.65,'#2e2e2e'],[1,'#000']]);g.fillRect(0,0,w,h);});
  // Scallop-style wash for a narrow spot hitting a wall: bright pool with a soft falloff.
  textures.glowPool=ramp(128,128,(g,w,h)=>{stops(g,g.createRadialGradient(w/2,h/2,1,w/2,h/2,w/2),[[0,'#fff'],[.22,'#dcdcdc'],[.55,'#5a5a5a'],[1,'#000']]);g.fillRect(0,0,w,h);});
  // Lime/stucco relief: layered value noise turned into a tangent-space normal map.
  function stuccoNormal(size=512){
    const h=new Float32Array(size*size);
    for(const [cells,amp] of [[4,.9],[8,.8],[16,.45],[32,.22],[64,.1],[128,.05]]){
      const lat=new Float32Array(cells*cells).map(()=>rnd());
      for(let y=0;y<size;y++)for(let x=0;x<size;x++){
        const fx=x/size*cells,fy=y/size*cells,x0=Math.floor(fx),y0=Math.floor(fy),tx=fx-x0,ty=fy-y0,sx=tx*tx*(3-2*tx),sy=ty*ty*(3-2*ty);
        const a=lat[(y0%cells)*cells+x0%cells],b=lat[(y0%cells)*cells+(x0+1)%cells],c=lat[((y0+1)%cells)*cells+x0%cells],d=lat[((y0+1)%cells)*cells+(x0+1)%cells];
        h[y*size+x]+=amp*(a+(b-a)*sx+(c-a)*sy+(a-b-c+d)*sx*sy);
      }
    }
    const c=document.createElement('canvas');c.width=c.height=size;const g=c.getContext('2d'),im=g.createImageData(size,size),k=11;
    for(let y=0;y<size;y++)for(let x=0;x<size;x++){
      const l=h[y*size+(x+size-1)%size],r=h[y*size+(x+1)%size],u=h[((y+size-1)%size)*size+x],d=h[((y+1)%size)*size+x];
      let nx=(l-r)*k,ny=(d-u)*k,nz=1;const n=Math.hypot(nx,ny,nz);nx/=n;ny/=n;nz/=n;
      const i=(y*size+x)*4;im.data[i]=(nx*.5+.5)*255;im.data[i+1]=(ny*.5+.5)*255;im.data[i+2]=(nz*.5+.5)*255;im.data[i+3]=255;
    }
    g.putImageData(im,0,0);const t=new T.CanvasTexture(c);t.wrapS=t.wrapT=T.RepeatWrapping;t.colorSpace=T.NoColorSpace;t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());return t;
  }
  textures.stuccoNormal=stuccoNormal();
  m.stucco=new T.MeshStandardMaterial({color:'#bcb7aa',roughness:.92,normalMap:textures.stuccoNormal,normalScale:new T.Vector2(.45,.45)});
  // Abstract canvas for the showpiece wall (warm earth, indigo and gold brush work).
  const paint=document.createElement('canvas');paint.width=512;paint.height=384;
  {
    const g=paint.getContext('2d');g.fillStyle='#e7dcc6';g.fillRect(0,0,512,384);
    const blobs=[['#b25a3b',.6,150,230,120,70,-.3],['#2b4a66',.55,330,150,150,80,.2],['#c9a24f',.55,260,300,130,45,.1],['#7c8764',.4,90,90,100,60,.5],['#8c3f2d',.45,410,290,90,60,-.5],['#f1e9d6',.5,220,160,110,40,.35]];
    for(const [col,a,x,y,rx,ry,rot] of blobs){g.globalAlpha=a;g.fillStyle=col;g.beginPath();g.ellipse(x,y,rx,ry,rot,0,Math.PI*2);g.fill();}
    for(let i=0;i<70;i++){g.globalAlpha=.05+rnd()*.12;g.strokeStyle=['#2b2a26','#9a5a3a','#d7bb78','#f4eee0'][i%4];g.lineWidth=1+rnd()*5;g.beginPath();const x=rnd()*512,y=rnd()*384;g.moveTo(x,y);g.quadraticCurveTo(x+rnd()*120-60,y+rnd()*80-40,x+rnd()*200-100,y+rnd()*120-60);g.stroke();}
    g.globalAlpha=.9;g.strokeStyle='#c9a24f';g.lineWidth=3;g.beginPath();g.moveTo(40,320);g.quadraticCurveTo(250,230,470,300);g.stroke();g.globalAlpha=1;
  }
  textures.painting=new T.CanvasTexture(paint);textures.painting.colorSpace=T.SRGBColorSpace;
  m.painting=new T.MeshStandardMaterial({map:textures.painting,roughness:.78});
  m.ceilingDS=m.ceiling.clone();m.ceilingDS.side=T.DoubleSide;m.shade.side=T.DoubleSide;
  m.groove=new T.MeshStandardMaterial({color:'#0a0b0b',roughness:.92,side:T.DoubleSide});
  m.opalTrim=new T.MeshStandardMaterial({color:'#f2efe8',roughness:.34});
  m.brassTrim=new T.MeshStandardMaterial({color:'#b9955a',roughness:.35,metalness:.85});

  // ---- Rev 4 materials: hall render p3, pooja niche, kit-kat bath tiles, joinery ----
  const canvasTex=(w,h,paint,repeat=false,srgb=true)=>{
    const c=document.createElement('canvas');c.width=w;c.height=h;paint(c.getContext('2d'),w,h);
    const t=new T.CanvasTexture(c);if(srgb)t.colorSpace=T.SRGBColorSpace;
    if(repeat)t.wrapS=t.wrapT=T.RepeatWrapping;t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());return t;
  };
  const mandala=(g,cx,cy,R,light,dark,petals=16)=>{
    g.save();g.translate(cx,cy);g.lineWidth=Math.max(1,R/60);
    for(let ring=0;ring<4;ring++){
      const r=R*(1-ring*.22),n=petals-ring*2;
      for(let k=0;k<n;k++){
        g.save();g.rotate(k/n*Math.PI*2+ring*.2);g.beginPath();g.ellipse(0,-r*.62,r*.17,r*.34,0,0,Math.PI*2);
        g.fillStyle=ring%2?dark:light;g.globalAlpha=.9;g.fill();g.strokeStyle=ring%2?light:dark;g.stroke();g.restore();
      }
    }
    g.globalAlpha=1;g.beginPath();g.arc(0,0,R*.16,0,Math.PI*2);g.fillStyle=light;g.fill();g.strokeStyle=dark;g.stroke();
    g.beginPath();g.arc(0,0,R*1.02,0,Math.PI*2);g.stroke();g.beginPath();g.arc(0,0,R*.97,0,Math.PI*2);g.stroke();
    g.restore();
  };
  m.poojaRelief=new T.MeshStandardMaterial({color:'#c8993a',transparent:true,roughness:.4,metalness:.6,map:canvasTex(256,256,(g,w,h)=>{
    g.clearRect(0,0,w,h);g.fillStyle='#fff';g.textAlign='center';g.textBaseline='middle';
    g.font='160px "Nirmala UI","Mangal",serif';g.fillText('\u0950',w/2,h/2);
  })});
  textures.wenge=canvasTex(256,512,(g,w,h)=>{
    g.fillStyle='#4b372c';g.fillRect(0,0,w,h);
    for(let i=0;i<240;i++){const x=rnd()*w;g.strokeStyle=rnd()<.55?`rgba(20,11,7,${.08+rnd()*.25})`:`rgba(120,90,70,${.04+rnd()*.12})`;g.lineWidth=.4+rnd()*1.7;g.beginPath();g.moveTo(x,0);for(let y=0;y<=h;y+=16)g.lineTo(x+Math.sin(y*.03+i)*1.1,y);g.stroke();}
  },true);
  m.wenge=new T.MeshStandardMaterial({color:'#ffffff',map:textures.wenge,roughness:.36,metalness:.02});
  textures.walnut=canvasTex(256,256,(g,w,h)=>{
    g.fillStyle='#5a3a27';g.fillRect(0,0,w,h);
    for(let i=0;i<160;i++){const y=rnd()*h;g.strokeStyle=rnd()<.6?`rgba(25,12,6,${.06+rnd()*.22})`:`rgba(150,105,72,${.05+rnd()*.12})`;g.lineWidth=.4+rnd()*1.5;g.beginPath();g.moveTo(0,y);for(let x=0;x<=w;x+=12)g.lineTo(x,y+Math.sin(x*.04+i)*1.6);g.stroke();}
  },true);
  m.walnut=new T.MeshStandardMaterial({color:'#ffffff',map:textures.walnut,roughness:.42});
  m.concrete=new T.MeshStandardMaterial({color:'#ffffff',roughness:.96,map:canvasTex(256,256,(g,w,h)=>{
    g.fillStyle='#a3a29b';g.fillRect(0,0,w,h);
    for(let i=0;i<5200;i++){g.fillStyle=`rgba(${rnd()<.5?'60,60,56':'210,208,198'},${.04+rnd()*.12})`;const s=.6+rnd()*2.4;g.fillRect(rnd()*w,rnd()*h,s,s);}
    for(let i=0;i<14;i++){g.fillStyle='rgba(40,40,36,.28)';g.beginPath();g.arc(rnd()*w,rnd()*h,.8+rnd()*1.6,0,7);g.fill();}
  },true)});
  m.paintedSlab=new T.MeshStandardMaterial({color:'#d9d6cc',roughness:.95});
  textures.kitkat=canvasTex(128,128,(g,w,h)=>{
    for(let i=0;i<8;i++){const x=i*16,gr=g.createLinearGradient(x,0,x+16,0);
      gr.addColorStop(0,'#bdbdbd');gr.addColorStop(.3,'#ffffff');gr.addColorStop(.75,'#e4e4e4');gr.addColorStop(1,'#7e7e7e');g.fillStyle=gr;g.fillRect(x,0,16,h);}
  },true);
  const TILES={teal:'#1c8790',rust:'#a24a2b',green:'#6e796b'};
  for(const k of [1,2])m['kitkat'+k]=new T.MeshStandardMaterial({color:TILES.green,map:textures.kitkat,roughness:.6,metalness:.02,envMapIntensity:.35});
  m.porcelain=new T.MeshStandardMaterial({color:'#bcb7aa',map:textures.stone,roughness:.6,envMapIntensity:.35});
  m.bathFloor=new T.MeshStandardMaterial({color:'#9d9689',map:textures.tile,roughness:.88});
  textures.tufted=canvasTex(256,256,(g,w,h)=>{
    g.fillStyle='#f5f2ea';g.fillRect(0,0,w,h);
    for(let i=0;i<8;i++){const x=i*32,gr=g.createLinearGradient(x,0,x+32,0);gr.addColorStop(0,'rgba(90,80,60,.34)');gr.addColorStop(.14,'rgba(255,255,255,.0)');gr.addColorStop(.6,'rgba(255,255,255,.5)');gr.addColorStop(1,'rgba(90,80,60,.28)');g.fillStyle=gr;g.fillRect(x,0,32,h);}
    for(let y=0;y<h;y+=3){g.fillStyle=`rgba(80,70,50,${.02+rnd()*.05})`;g.fillRect(0,y,w,1);}
  },true);
  m.tufted=new T.MeshStandardMaterial({color:STYLES[0].fabric,map:textures.tufted,roughness:.95});
  m.olive=new T.MeshStandardMaterial({color:'#6e7442',map:textures.fabric,roughness:.95});
  m.houndstooth=new T.MeshStandardMaterial({color:'#8d9094',roughness:.97,map:canvasTex(64,64,(g,w,h)=>{
    g.fillStyle='#f0f0ee';g.fillRect(0,0,w,h);g.fillStyle='#55585c';
    for(let y=0;y<h;y+=16)for(let x=0;x<w;x+=16){g.fillRect(x,y,8,8);g.fillRect(x+8,y+8,8,8);g.fillRect(x+8,y+4,4,4);g.fillRect(x+4,y+8,4,4);}
  },true)});
  m.blueWardrobe=new T.MeshStandardMaterial({color:'#31567f',roughness:.42,metalness:.02});
  m.gold=new T.MeshStandardMaterial({color:'#d6a53e',roughness:.26,metalness:.92});
  m.wicker=new T.MeshStandardMaterial({color:'#b88d57',roughness:.9,map:textures.cane});
  m.glassTop=new T.MeshPhysicalMaterial({color:'#cfe2e2',transparent:true,opacity:.34,roughness:.04,metalness:.1,side:T.DoubleSide,depthWrite:false,envMapIntensity:1.1});
  m.metalDark=new T.MeshStandardMaterial({color:'#37383a',roughness:.28,metalness:.9});
  m.hexPanel=new T.MeshStandardMaterial({color:'#ffffff',roughness:.55,map:canvasTex(128,148,(g,w,h)=>{
    g.fillStyle='#8e6648';g.fillRect(0,0,w,h);g.strokeStyle='#4b3123';g.lineWidth=2;
    const R=18,dx=R*Math.sqrt(3);
    for(let r=-1;r<7;r++)for(let c=-1;c<6;c++){const cx=c*dx+(r%2?dx/2:0),cy=r*R*1.5;g.beginPath();for(let k=0;k<6;k++){const a=Math.PI/6+k*Math.PI/3;g.lineTo(cx+R*Math.cos(a),cy+R*Math.sin(a));}g.closePath();g.stroke();}
  },true)});
  textures.mural=canvasTex(384,896,(g,w,h)=>{
    const gr=g.createLinearGradient(0,0,0,h);gr.addColorStop(0,'#0e3a45');gr.addColorStop(.55,'#1d5c66');gr.addColorStop(1,'#0b2c34');g.fillStyle=gr;g.fillRect(0,0,w,h);
    g.fillStyle='rgba(222,196,130,.2)';
    for(let i=0;i<3;i++){const x=40+i*110;g.beginPath();g.moveTo(x,360);g.lineTo(x,200);g.quadraticCurveTo(x+45,120,x+90,200);g.lineTo(x+90,360);g.fill();g.fillRect(x-8,360,106,10);}
    g.strokeStyle='rgba(235,205,140,.55)';g.lineWidth=2;for(let i=0;i<3;i++){const x=40+i*110;g.beginPath();g.moveTo(x,360);g.lineTo(x,200);g.quadraticCurveTo(x+45,120,x+90,200);g.lineTo(x+90,360);g.stroke();}
    // peacock: curving body, crest, fanned tail with eye feathers
    g.strokeStyle='#d9b45a';g.lineWidth=5;g.beginPath();g.moveTo(250,560);g.bezierCurveTo(210,640,150,640,130,540);g.bezierCurveTo(115,470,150,430,170,400);g.stroke();
    g.fillStyle='#1b7f8c';g.beginPath();g.ellipse(190,560,48,84,.25,0,Math.PI*2);g.fill();g.beginPath();g.arc(168,392,17,0,7);g.fill();
    g.strokeStyle='#d9b45a';g.lineWidth=2;for(let k=-2;k<=2;k++){g.beginPath();g.moveTo(168,376);g.lineTo(168+k*7,350);g.stroke();g.fillStyle='#d9b45a';g.beginPath();g.arc(168+k*7,347,3,0,7);g.fill();}
    for(let k=0;k<16;k++){
      const a=-Math.PI*.95+k*Math.PI*.9/15,len=250+(k%2)*40,x1=210+Math.cos(a)*len*.9,y1=640+Math.sin(a)*len;
      g.strokeStyle='rgba(120,196,176,.8)';g.lineWidth=2;g.beginPath();g.moveTo(215,650);g.quadraticCurveTo((215+x1)/2+(k%2?12:-12),(650+y1)/2,x1,y1);g.stroke();
      g.fillStyle='#d9b45a';g.beginPath();g.ellipse(x1,y1,15,22,a+Math.PI/2,0,7);g.fill();
      g.fillStyle='#1a8f9f';g.beginPath();g.ellipse(x1,y1,10,16,a+Math.PI/2,0,7);g.fill();
      g.fillStyle='#143c66';g.beginPath();g.ellipse(x1,y1,5,9,a+Math.PI/2,0,7);g.fill();
    }
    for(let i=0;i<60;i++){g.fillStyle=`rgba(220,196,130,${.05+rnd()*.12})`;g.beginPath();g.arc(rnd()*w,rnd()*h,1+rnd()*3,0,7);g.fill();}
  });
  m.mural=new T.MeshStandardMaterial({color:'#ffffff',map:textures.mural,roughness:.62});
  // Pooja niche back panel (marble, gold Om, white mandala jali) and the carved double shutter.
  textures.poojaBack=canvasTex(512,960,(g,w,h)=>{
    g.fillStyle='#f5f3ee';g.fillRect(0,0,w,h);
    for(let j=0;j<10;j++){let y=rnd()*h;g.beginPath();g.moveTo(0,y);g.strokeStyle=`rgba(110,108,96,${.05+rnd()*.12})`;g.lineWidth=.5+rnd()*1.4;for(let x=0;x<=w;x+=10){y+=rnd()*12-6;g.lineTo(x,y);}g.stroke();}
    g.fillStyle='#e6e2d6';g.beginPath();g.arc(w/2,500,205,0,7);g.fill();
    mandala(g,w/2,500,196,'#fbfaf6','#b7b09f');
    g.fillStyle='#c8993a';g.textAlign='center';g.font='bold 118px "Nirmala UI","Noto Sans Devanagari","Mangal","Arial Unicode MS",serif';g.fillText('\u0950',w/2,190);
  });
  m.poojaBack=new T.MeshStandardMaterial({color:'#ffffff',map:textures.poojaBack,roughness:.3,envMapIntensity:.5});
  textures.shutter=canvasTex(512,960,(g,w,h)=>{
    g.fillStyle='#5b3a26';g.fillRect(0,0,w,h);
    for(let i=0;i<120;i++){const y=rnd()*h;g.strokeStyle=`rgba(20,10,4,${.05+rnd()*.2})`;g.lineWidth=.5+rnd()*1.4;g.beginPath();g.moveTo(0,y);for(let x=0;x<=w;x+=16)g.lineTo(x,y+Math.sin(x*.03+i)*1.4);g.stroke();}
    g.strokeStyle='#d8b27a';g.lineWidth=3;g.strokeRect(14,14,w-28,h-28);g.strokeStyle='#2b180d';g.strokeRect(22,22,w-44,h-44);
    mandala(g,w/2,h/2,214,'#d8b27a','#2b180d',16);
    for(const y of [120,h-120])mandala(g,w/2,y,70,'#d8b27a','#2b180d',10);
  });
  m.shutter=new T.MeshStandardMaterial({color:'#ffffff',map:textures.shutter,roughness:.45,metalness:.04});

  function setTiles(bath,name){
    const keys=bath==='all'?['kitkat1','kitkat2']:[bath==='bath1'?'kitkat1':'kitkat2'];
    for(const k of keys)m[k].color.set(TILES[name]||TILES.teal);
  }

  function setDaylight(daylight,dt){
    const t=1-Math.exp(-dt*6);
    glassTarget.copy(nightGlass).lerp(dayGlass,daylight);
    m.windowGlass.color.lerp(glassTarget,t);
    m.windowGlass.opacity=T.MathUtils.lerp(m.windowGlass.opacity,.94-.74*daylight,t);
    m.windowGlass.envMapIntensity=T.MathUtils.lerp(m.windowGlass.envMapIntensity,.055+.5*daylight,t);
    m.sheer.opacity=T.MathUtils.lerp(m.sheer.opacity,.07+.32*daylight,t);
  }
  return {m,textures,floor,setStyle,update,setDaylight,setTiles,TILES};
}
