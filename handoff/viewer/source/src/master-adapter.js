export const FT=.3048;
export const ZONE_IDS={LIV:'living',DIN:'dining',KIT:'kitchen',UTL:'utility',MBR:'master',DRS:'dressing',TL1:'bath1',LOB:'lobby',TL2:'bath2',CBR:'children',BAL:'balcony'};
const clone=v=>JSON.parse(JSON.stringify(v));
const feet=a=>a.map(v=>v/FT);
const channel=f=>f.lane==='COVE'?'low':f.lane==='ACCENT'?(f.id==='LIV-P1'?'pooja':f.id==='LIV-P2'?'poojaSpot':'art'):f.type==='VANITY'?'uv':f.lane.toLowerCase();

export function roomFloorRegions(room){
  const nominal=room.rect,assembly=room.assemblyRect||nominal,cut=room.assemblyCutout||room.cutout;
  const inside=(x,z,r)=>r&&x>r[0]&&x<r[2]&&z>r[1]&&z<r[3];
  const xs=[...new Set([nominal[0],nominal[2],assembly[0],assembly[2],...(cut?[cut[0],cut[2]]:[])])].sort((a,b)=>a-b);
  const zs=[...new Set([nominal[1],nominal[3],assembly[1],assembly[3],...(cut?[cut[1],cut[3]]:[])])].sort((a,b)=>a-b),regions=[];
  for(let i=1;i<xs.length;i++)for(let j=1;j<zs.length;j++){
    const x=(xs[i-1]+xs[i])/2,z=(zs[j-1]+zs[j])/2;
    if((!inside(x,z,nominal)&&!inside(x,z,assembly))||inside(x,z,cut))continue;
    regions.push({rect:[xs[i-1],zs[j-1],xs[i],zs[j]],role:inside(x,z,nominal)?'nominal':'assembly-hold'});
  }
  return regions;
}

function blackPath(p){
  if(p.pts_ft)return p.pts_ft;
  const f=p.fillet,points=f.corners_ft,out=[];
  for(let i=0;i<points.length;i++){
    const b=points[i];
    if(i===0||i===points.length-1){out.push(b);continue;}
    const a=points[i-1],c=points[i+1],la=Math.hypot(a[0]-b[0],a[1]-b[1]),lc=Math.hypot(c[0]-b[0],c[1]-b[1]);
    const r=Math.min(Array.isArray(f.radii_ft)?f.radii_ft[i]:f.radii_ft,la*.4,lc*.4);
    for(let n=0;n<=8;n++){
      const t=n/8,u=1-t;
      out.push([b[0]+u*u*(a[0]-b[0])*r/la+t*t*(c[0]-b[0])*r/lc,b[1]+u*u*(a[1]-b[1])*r/la+t*t*(c[1]-b[1])*r/lc]);
    }
  }
  return out;
}

export function adaptLighting(house){
  const L=house.lighting,D=L.design_inputs,model=D.model;
  const resolved=new Map(L.fixtures.map(f=>[f.id,f]));
  const zones=D.rooms.map(r=>({
    ...r,room:ZONE_IDS[r.id],poly:r.poly_ft,z0:r.bath_z0_ft,
    fixtures:r.fixtures.map(raw=>{
      const f=resolved.get(raw.id);
      if(!f)throw new Error('Unresolved canonical fitting '+raw.id);
      if(f.room!==r.id||f.type!==raw.type)throw new Error('Stale canonical fitting '+raw.id);
      const a=raw.aim_target;
      return {...raw,...f,src:'assumed',x:f.x_ft,z:f.z_ft,W:f.W_nominal,beam:f.beam_deg,
        layer:channel(raw).toUpperCase(),channel:channel(raw),pts:f.path_ft||undefined,
        h_m:raw.mount_h_m??undefined,tilt:raw.tilt_deg,toward:raw.tilt_toward_xz,dir:raw.dir_xyz,
        aim:a?[a.x_ft,a.z_ft,a.h_m]:undefined,
        jamb_h:raw.niche_u?[raw.niche_u.jamb_bottom_m,raw.niche_u.jamb_top_m]:undefined};
    }),
  }));
  const ceilings=Object.fromEntries(Object.entries(D.ceilings).map(([id,c])=>[id,{
    ...c,tray:c.tray_corners_ft,tray_h:c.tray_h_m,band_h:c.band_h_m,
    lines_lit:c.lines_lit_ft,lines_black:(c.lines_black||[]).map(blackPath),frame:c.frame_ft,beam:c.beam_band,
  }]));
  for(const fan of house.visualization_geometry.fans||[]){
    if(!Array.isArray(fan.at_m))continue;
    const zone=zones.find(z=>z.room===fan.room);
    if(zone)zone.fan=feet(fan.at_m);
  }
  return {
    src:'assumed',source:'house-design.json / lighting',revision:'current',
    assumptions:{MF:model.MF,CAL:model.cal_direct,RHO:model.rho_default,BAND_M:model.band_m,TRAY_M:model.tray_m,niche:{...D.niche,idol_face_x_ft:D.niche.idol_x_ft}},
    cat:D.catalogue.points,strips:D.catalogue.strips,ceilings,zones,
    expected:L.calculations,inputs:D,controls:L.controls,
  };
}

export function createPlan(generated,{includeLighting=true}={}){
  const house=generated.house,V=clone(house.visualization_geometry),A=house.architecture;
  if(!V||house.bathrooms.rooms.length!==2)throw new Error('Canonical visualisation and bathroom sections are required');
  const rooms=V.rooms.map(r=>{
    const binding=V.nominal_room_bindings?.bindings.find(b=>b.room_id===r.id);
    if(binding){
      r.rect=binding.rect.slice();r.assemblyRect=binding.assembly_rect_m.slice();r.bindingNote=binding.assembly_hold;
      if(r.cutout){
        r.assemblyCutout=r.cutout.slice();
        r.cutout=[Math.max(r.rect[0],r.cutout[0]),Math.max(r.rect[1],r.cutout[1]),Math.min(r.rect[2],r.cutout[2]),Math.min(r.rect[3],r.cutout[3])];
      }
    }
    if(!r.rect||!r.spawn)throw new Error('Current room geometry is pending: '+r.id);
    for(const k of ['rect','cutout','spawn','assemblyRect','assemblyCutout'])if(r[k])r[k]=feet(r[k]);
    const ar=A.rooms.find(a=>a.id===r.architectural_room_id)||A.rooms.find(a=>ZONE_IDS[a.lighting_room_id]===r.id);
    if(ar){
      r.architectural_room_id=ar.id;
      if(ar.dimensions.length){
        r.dimension={src:'dim',text:ar.dimensions.map(d=>d.original).join(' x '),basis:'Homeowner-confirmed printed dimension'};
        if(ar.dimensions.length===2){
          const unresolved=V.nominal_room_bindings?.unresolved.find(b=>b.room_id===r.id);
          const assembly=unresolved?feet(unresolved.assembly_rect_m):r.assemblyRect||r.rect;
          r.dimensionScope=unresolved?.assembly_scope;
          r.assemblyDifferenceM=[(assembly[2]-assembly[0])*FT-ar.dimensions[0].value_m,(assembly[3]-assembly[1])*FT-ar.dimensions[1].value_m];
          r.nominalDifferenceM=binding?[(r.rect[2]-r.rect[0])*FT-ar.dimensions[0].value_m,(r.rect[3]-r.rect[1])*FT-ar.dimensions[1].value_m]:null;
          if(binding&&r.nominalDifferenceM.some(n=>Math.abs(n)>1e-7))throw new Error('Canonical nominal binding mismatch: '+r.id);
        }
      }
    }
    return r;
  });
  const walls=V.walls.map(w=>({...w,rect:feet(w.rect)}));
  const openings=V.openings.map(o=>({...o,span:feet(o.span),...(o.curtainSpan?{curtainSpan:feet(o.curtainSpan)}:{})}));
  const editWall=(id,change)=>{
    const w=walls.find(w=>w.id===id);
    if(!w)throw new Error('Missing host wall '+id);
    change(w.rect);
  };
  for(const b of house.bathrooms.rooms){
    const r=b.renderer_room_id,[x,z,X,Z]=feet(b.placement.rect_m),door=b.entrance,win=b.window,sh=b.shower;
    rooms.push({id:r,name:r==='bath1'?'Attached bathroom':'Common bathroom',src:'dim',rect:[x,z,X,Z],wet:true,ceiling:'bath',
      spawn:[(b.wc.centerline_x_m+.10)/FT,(b.placement.rect_m[3]-.4)/FT],
      architectural_room_id:b.architectural_room_id,dimension:{src:'dim',text:'8 ft 9 in x 5 ft 6 in',basis:'Homeowner-confirmed printed dimensions; inferred anchor'},
      assemblyDifferenceM:[0,0]});
    editWall(r+'-west',p=>{p[1]=z;p[3]=Z;});
    if(r==='bath1'){
      editWall('bath1-north',p=>{p[2]=X;p[3]=z;});
      editWall('bath-shared',p=>{p[1]=Z;p[2]=X;});
    }else{
      editWall('bath-shared',p=>p[3]=z);
      editWall('children-north',p=>p[1]=Z);
    }
    editWall('east',p=>p[0]=X);
    openings.push({id:r+'-door',canonicalId:door.opening_id,src:'assumed',wall:r+'-west',axis:'z',
      span:door.opening_segment_m.map(p=>p[1]/FT),kind:'door',openSide:1,hingeEnd:door.hinge_end==='max_z'?'max':'min',
      jambM:door.jamb_allowance_m,leafThicknessM:door.leaf_thickness_m,note:door.hinge_basis});
    openings.push({id:r+'-vent',canonicalId:win.opening_id,src:'scaled',wall:'east',axis:'z',
      span:win.segment_m.map(p=>p[1]/FT),kind:'vent',sillValue:win.sill_m,headValue:win.head_m});
    openings.push({id:r+'-niche',src:'scaled',wall:'east',axis:'z',
      span:[(sh.niche_center_xyz_m[2]-sh.niche_width_m/2)/FT,(sh.niche_center_xyz_m[2]+sh.niche_width_m/2)/FT],
      kind:'bath-niche',sillValue:sh.niche_center_xyz_m[1]-sh.niche_height_m/2,headValue:sh.niche_center_xyz_m[1]+sh.niche_height_m/2,
      depthM:sh.niche_depth_m});
  }
  const furniture=V.essential_furniture.map(f=>{
    for(const k of ['rect','return','left','top','fridge','bar','at','counter'])if(f[k])f[k]=feet(f[k]);
    for(const k of ['wallX','z'])if(f[k]!=null)f[k]/=FT;
    return f;
  });
  for(const k of ['upper','landing','lower'])V.stairs[k]=feet(V.stairs[k]);
  V.pooja.z=feet(V.pooja.z);
  const heights=V.provisional_heights;
  const hmap={soffit:'slab_underside',band:'room_perimeter_band',coffer:'raised_soffit',toilet:'bathroom_soffit'};
  for(const [key,canonical] of Object.entries(hmap))heights[key]={src:'assumed',value:A.heights[canonical].value_m};
  return {
    version:'current-coordinated-design',master:{sha256:generated.master_sha256,filename:generated.master_filename,preview:generated.preview},
    design:V.design,provenance:{src:'assumed',title:'Current coordinated design | measured labels and proposed assembly',file:'house-design.json',feetToMetres:{src:'dim',value:FT}},
    plot:{src:'dim',x:A.dimension_basis.overall_dimensions[0].value_m/FT,z:A.dimension_basis.overall_dimensions[1].value_m/FT},
    heights,rooms,walls,openings,furniture,stairs:V.stairs,pooja:V.pooja,
    fixtures:includeLighting?adaptLighting(house):null,bathrooms:house.bathrooms,storage:house.storage,nominalBindings:V.nominal_room_bindings||null,
    surveyNotes:[
      'One editable source: house-design.json. This HTML is a generated snapshot, fingerprinted to that master.',
      'Original layout PDF and inherited children-room traces are retired as active layout authority. Confirmed numerical room sizes remain independent constraints; other-room shell placements are carry-forward design, not new measured evidence.',
      'Children-room relationships follow render pages 16-18. Proposed metric placement, return, concealed window and loft supports are not homeowner-approved setting-out or instructions to alter masonry.',
      'Nominal room-local extents and unresolved assembly bands are separate geometry. Exact nominal dimensions do not make the overall assembled shell an exact as-built model.',
      'Bathroom clear sizes use the printed 2667 x 1676.4 mm dimensions. Other assembly offsets are disclosed separately; lighting-zone polygons are not masonry walls.',
      'The vanity is left on entry on the services wall. Its cabinet faces sheet +z; the user looks -z. The requested true-north meaning and whole-building bearing remain unresolved.',
      'Bathroom min-z hinges are a provisional interpretation of behind the door, not a confirmed site hinge or instruction to rehang. Close the door before basin use; the open leaf occupies the approach.',
      'Kitkat feature tile is only on the L-shaped shower walls. Dry-zone walls, including behind the vanity and WC, remain plain.',
      'Four fit-out instances share this template. Floor-specific differences, loft capacities and moisture/structural checks are not established by the model.',
      'Pooja remains a hypothetical 115 mm cavity with 15 mm trim. No structural cutting or chasing is approved.',
      'Granite backing is not a leak remedy. Repair and dry the moisture source before concealing it; the construction system and stone supports remain subject to specialist approval.',
    ],
  };
}
