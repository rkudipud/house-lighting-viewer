import * as T from 'three';

export function buildBaths(c){
  const {m,PLAN,collision,box,cylinder,ball,line,v,world,glowMat,decalMat,planeGeo,lights}=c;
  const geometryCache=new Map(),diagnostics=[];
  if(PLAN.bathrooms?.rooms.length!==2)throw new Error('Current coordinated bathroom geometry is required.');

  function tile(b,region,mat,unit,holes,kind){
    const side=region.wall,alongX=side.endsWith('z'),[p0,p1]=region.segment_m;
    const a=alongX?p0[0]:p0[1],b1=alongX?p1[0]:p1[1],[lo,hi]=region.height_range_m;
    const cuts=[...new Set([a,b1,...holes.flatMap(h=>[h[0],h[1]])].filter(n=>n>=a&&n<=b1))].sort((a,b)=>a-b);
    for(let i=1;i<cuts.length;i++){
      const u0=cuts[i-1],u1=cuts[i],mid=(u0+u1)/2;
      const excluded=holes.filter(h=>mid>h[0]&&mid<h[1]);
      const ys=[...new Set([lo,hi,...excluded.flatMap(h=>[h[2],h[3]])].filter(n=>n>=lo&&n<=hi))].sort((a,b)=>a-b);
      for(let j=1;j<ys.length;j++){
        const y0=ys[j-1],y1=ys[j],ym=(y0+y1)/2;
        if(excluded.some(h=>ym>h[2]&&ym<h[3]))continue;
        const w=u1-u0,h=y1-y0,key=[w,h,unit].map(n=>n.toFixed(7)).join('|');
        let geo=geometryCache.get(key);
        if(!geo){
          geo=new T.PlaneGeometry(w,h);const uv=geo.attributes.uv;
          for(let k=0;k<uv.count;k++)uv.setXY(k,uv.getX(k)*w/unit,uv.getY(k)*h/unit);
          geometryCache.set(key,geo);
        }
        const o=new T.Mesh(geo,mat),[x,z,X,Z]=b.placement.rect_m;
        if(side==='negative-z')o.position.set(mid,ym,z+.004);
        else if(side==='positive-z'){o.position.set(mid,ym,Z-.004);o.rotation.y=Math.PI;}
        else if(side==='positive-x'){o.position.set(X-.004,ym,mid);o.rotation.y=-Math.PI/2;}
        else{o.position.set(x+.004,ym,mid);o.rotation.y=Math.PI/2;}
        o.name=`${b.lighting_room_id}-${kind}-${side}`;
        o.userData.noMerge=true;o.userData.tileRegion={kind,side,span:[u0,u1],height:[y0,y1]};
        o.receiveShadow=true;world.add(o);
        diagnostics.push({room:b.renderer_room_id,kind,mesh:o});
      }
    }
  }

  for(const b of PLAN.bathrooms.rooms){
    const room=b.renderer_room_id,idx=room==='bath1'?1:2,feature=m['kitkat'+idx];
    const [x,z,X,Z]=b.placement.rect_m,va=b.vanity,wc=b.wc,sh=b.shower,win=b.window;
    const nc=sh.niche_center_xyz_m,nw=sh.niche_width_m,nh=sh.niche_height_m,nd=sh.niche_depth_m;
    const holes={
      'negative-x':[[b.entrance.opening_segment_m[0][1],b.entrance.opening_segment_m[1][1],0,PLAN.heights.door.value]],
      'positive-x':[
        [win.segment_m[0][1],win.segment_m[1][1],win.sill_m,win.head_m],
        [nc[2]-nw/2,nc[2]+nw/2,nc[1]-nh/2,nc[1]+nh/2],
      ],
    };
    for(const r of b.finishes.kitkat_wall_regions)tile(b,r,feature,.16,holes[r.wall]||[],'kitkat');
    for(const r of b.finishes.plain_wall_regions)tile(b,r,m.porcelain,1.2,holes[r.wall]||[],'plain');

    const [vx,vz,vX,vZ]=va.rect_m,vc=(vx+vX)/2,vd=vZ-vz,vw=vX-vx,[bottom,top]=va.height_range_m;
    const cabinet=box(vc,(bottom+top-.04)/2,(vz+vZ)/2,vw,top-bottom-.04,vd,m.cabinet);
    cabinet.name=`${b.lighting_room_id}-vanity`;cabinet.userData.noMerge=true;
    box(vc,top-.02,(vz+vZ)/2,vw,.04,vd,m.stone);
    for(const dx of [-.16,.16])box(vc+dx,(bottom+top)/2,vZ+.008,.12,.012,.016,m.gold);
    collision.push({x0:vx,z0:vz,x1:vX,z1:vZ,y0:bottom,y1:va.basin_top_m,kind:'furniture',id:va.id});
    ball(vc,va.basin_top_m-.05,vz+.26,.20,.05,.16,m.white).castShadow=false;
    cylinder(vc,top+.10,vz+.07,.011,.2,m.steel);
    box(vc,va.faucet_top_m-.01,vz+.13,.014,.014,.14,m.steel);
    const [mx,my,mz]=va.mirror_center_xyz_m,[mw,mh]=va.mirror_size_m;
    c.panelFrame(mx,my,mz+.004,mw,mh,0,m.steel,.012,.018);
    const mirror=new T.Mesh(planeGeo,m.mirror);mirror.scale.set(mw,mh,1);mirror.position.set(mx,my,mz);
    mirror.name=`${b.lighting_room_id}-mirror`;mirror.userData.noMerge=true;world.add(mirror);
    const [u0,u1]=va.understrip_endpoints_xyz_m;
    line(v(...u0),v(...u1),.006,glowMat(room,'uv',2.4));
    const fl=new T.Mesh(planeGeo,decalMat(room,'uv','glowPool',.65));
    fl.scale.set(vw+.25,.65,1);fl.rotation.x=-Math.PI/2;fl.position.set(vc,.022,vZ);fl.renderOrder=3;lights.add(fl);
    for(const dz of [.12,.20]){
      const stub=cylinder(x+.05,1.95,z+dz,.011,.10,m.steel);stub.rotation.z=Math.PI/2;
    }

    const [cx,cz,cX,cZ]=wc.cistern_rect_m,wx=wc.centerline_x_m;
    box((cx+cX)/2,wc.cistern_height_m/2,(cz+cZ)/2,cX-cx,wc.cistern_height_m,cZ-cz,m.porcelain);
    box((cx+cX)/2,wc.cistern_height_m+.012,(cz+cZ)/2,cX-cx,.024,cZ-cz,m.stone);
    const [bx,bz,bX,bZ]=wc.bowl_rect_m;
    box(wx,wc.seat_height_m-.17,(bz+bZ)/2,bX-bx,.30,bZ-bz,m.white,world,true);
    ball(wx,wc.seat_height_m-.025,(bz+bZ)/2,(bX-bx)/2,.05,(bZ-bz)/2,m.white);
    box(wx,.80,cZ+.008,.20,.14,.014,m.steel);
    collision.push({x0:cx,z0:cz,x1:cX,z1:cZ,y0:0,y1:wc.cistern_height_m,kind:'furniture',id:wc.id+'-cistern'});
    collision.push({x0:bx,z0:bz,x1:bX,z1:bZ,y0:.10,y1:wc.seat_height_m,kind:'furniture',id:wc.id});

    const [[sx,sz],[,sZ]]=sh.screen_segment_m,st=sh.screen_thickness_m;
    const screen=box(sx,sh.screen_height_m/2,(sz+sZ)/2,st,sh.screen_height_m,sZ-sz,m.glass);
    screen.castShadow=false;screen.name=`${b.lighting_room_id}-screen`;screen.userData.noMerge=true;
    line(v(sx,0,sz),v(sx,sh.screen_height_m,sz),.008,m.steel);
    line(v(sx,sh.screen_height_m,sz),v(sx,sh.screen_height_m,sZ),.008,m.steel);
    collision.push({x0:sx-st/2,z0:sz,x1:sx+st/2,z1:sZ,y0:0,y1:sh.screen_height_m,kind:'furniture',id:sh.id+'-screen'});
    const [hx,hy,hz]=sh.head_xyz_m,[fx,fy,fz]=sh.mixer_xyz_m;
    line(v(fx,fy,fz),v(fx,hy,fz),.014,m.steel);
    line(v(fx,hy,fz),v(hx,hy,hz),.014,m.steel);
    box(hx,hy-.012,hz,.24,.025,.24,m.steel);box(fx,fy,fz,.22,.08,.05,m.steel);
    box(hx,.021,(z+Z)/2,.14,.012,.14,m.steel);

    c.panelFrame(X-.005,nc[1],nc[2],nw,nh,-Math.PI/2,m.porcelain,nd,.025);
    const back=new T.Mesh(planeGeo,m.porcelain);back.scale.set(nw,nh,1);back.rotation.y=-Math.PI/2;
    back.position.set(X+nd-.008,nc[1],nc[2]);world.add(back);
    const glowX=X+.025,glowY=nc[1]+nh/2-.012;
    box(glowX,glowY,nc[2],.018,.012,nw-.04,glowMat(room,'mood',2.6));
    const nl=new T.Mesh(planeGeo,decalMat(room,'mood','glowDown',.6));nl.scale.set(nw-.04,nh-.02,1);nl.rotation.y=-Math.PI/2;
    nl.position.set(X+nd-.009,nc[1],nc[2]);lights.add(nl);
    cylinder(X+.065,nc[1]-nh/2+.055,nc[2]-.16,.024,.10,m.white);
    diagnostics.push({room,kind:'fixtures',vanity:cabinet,mirror,screen});
  }
  return diagnostics;
}
