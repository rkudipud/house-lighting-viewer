export const WALK_RADIUS = .22;

export function prepareNavigation(plan, collision) {
  const ft=.3048,step=.08,x0=.32,z0=.25,nx=109,nz=193;
  const blocked=(x,z)=>collision.some(b=>b.y1>.16&&b.y0<1.65&&x>b.x0-WALK_RADIUS&&x<b.x1+WALK_RADIUS&&z>b.z0-WALK_RADIUS&&z<b.z1+WALK_RADIUS);
  const xy=i=>[x0+(i%nx)*step,z0+Math.floor(i/nx)*step];
  const inside=(p,r)=>p[0]>r[0]*ft&&p[0]<r[2]*ft&&p[1]>r[1]*ft&&p[1]<r[3]*ft;
  const free=new Uint8Array(nx*nz);
  for(let i=0;i<free.length;i++){const p=xy(i);free[i]=blocked(...p)?0:1;}
  const nearest=(point,filter)=>{let best=-1,dist=Infinity;for(let i=0;i<free.length;i++)if(free[i]&&filter(i)){const p=xy(i),d=Math.hypot(p[0]-point[0],p[1]-point[1]);if(d<dist){dist=d;best=i;}}return best;};
  const start=nearest([9.5*ft,46.4*ft],i=>inside(xy(i),plan.rooms.find(r=>r.id==='balcony').rect));
  const search=from=>{
    const prev=new Int32Array(free.length);prev.fill(-1);prev[from]=from;const queue=[from];
    for(let q=0;q<queue.length;q++){
      const i=queue[q],x=i%nx,z=Math.floor(i/nx);
      for(const j of [x>0?i-1:-1,x<nx-1?i+1:-1,z>0?i-nx:-1,z<nz-1?i+nx:-1]){
        if(j<0||!free[j]||prev[j]!==-1)continue;prev[j]=i;queue.push(j);
      }
    }
    return prev;
  };
  if(start<0)throw new Error('No clear entrance spawn in accepted model.');
  const connected=search(start),spawns={},indices={};
  for(const r of plan.rooms){
    const i=nearest(r.spawn.map(v=>v*ft),j=>connected[j]>=0&&inside(xy(j),r.rect)&&(!r.cutout||!inside(xy(j),r.cutout)));
    if(i<0)throw new Error(`No connected walking position in ${r.id}; geometry remains unchanged.`);
    spawns[r.id]=xy(i).map(v=>v/ft);indices[r.id]=i;
  }
  const order=['living','dining','kitchen','utility','washing','master','dressing','bath1','lobby','bath2','children','living'];
  let cursor=start;const path=[[...xy(start).map(v=>v/ft),'Entrance']];
  for(const id of order){
    const to=indices[id],prev=search(cursor),segment=[];
    for(let i=to;i!==cursor;i=prev[i]){if(i<0)throw new Error(`Disconnected route to ${id}`);segment.push(i);}
    segment.reverse();
    for(let j=0;j<segment.length;j++){
      const before=j?segment[j-1]:cursor,after=segment[j+1];
      if(after!==undefined&&segment[j]-before===after-segment[j])continue;
      path.push([...xy(segment[j]).map(v=>v/ft),plan.rooms.find(r=>r.id===id).name]);
    }
    cursor=to;
  }
  return {spawns,path,radius:WALK_RADIUS,step,roomOrder:order};
}
