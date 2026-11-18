import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

export function drawingSource(house,source,{staging=false,reviewDraft=false,outDir}={}){
  const validity=house.lighting.calculation_validity;
  const pending=/pending|stale/i.test(house.lighting.status+' '+(validity.niche_notation_update?.status||''));
  assert(staging||!pending,'Lighting integration is pending; use --staging in a separate folder, not final outputs.');
  if(staging&&outDir)assert(!path.resolve(outDir).split(path.sep).some(p=>['current-floorplan','current-layout-views'].includes(p.toLowerCase())),'Staging must not replace current drawing folders.');
  const hd18=house.visualization_geometry.pooja.decision_refs?.includes('HD-18');
  let notation=null,note='';
  if(hd18){
    const file=path.join(path.dirname(source),'fragments','pooja-notation-hd18.json');
    const bytes=fs.readFileSync(file),f=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
    assert.equal(f.decision,'HD-18');assert.equal(f.construction_release,false);
    const p=house.visualization_geometry.pooja,d=house.decisions.pooja_niche.dimensions;
    for(const [visual,canonical] of [['widthMm','width_mm'],['heightMm','height_mm'],['sillM','sill_m'],['depthMm','depth_mm']]){
      assert.equal(p[visual],f.dimensions[canonical],`HD-18 ${visual} differs from notation fragment`);
      assert.equal(d[canonical],f.dimensions[canonical],`HD-18 decisions.${canonical} differs`);
    }
    assert.deepEqual(p.z,f.dimensions.z_m);assert.deepEqual(d.z_m,p.z);
    assert(Math.abs(p.sillM+p.heightMm/1000-f.dimensions.top_m)<1e-10);
    assert(Math.abs(f.placement.corner_z_m-p.z[1]-f.placement.north_edge_clear_offset_m)<1e-10);
    assert.equal(p.geometry_hold.new_or_deeper_cutting_authorized,false);
    const binding=house.visualization_geometry.nominal_room_bindings.bindings.find(x=>x.architectural_room_id==='R04');
    assert.match(binding.assembly_hold,/east.*sheet-left/i);
    assert(Math.abs((binding.rect[0]-binding.assembly_rect_m[0])*1000-41.148)<1e-8);
    assert.equal(binding.rect[2],binding.assembly_rect_m[2]);
    note=`HD-18 clarifies feet-and-inches notation: sill 1 ft 5 in (${p.sillM} m), depth 1 ft 3 in (${p.depthMm} mm), north-corner gap 1 ft 4 in (${f.placement.north_edge_clear_offset_m} m). All remain homeowner estimates, not site measurements. Opening height ${p.heightMm} mm is derived from the estimated top minus sill.`;
    notation={fragment:{file:path.basename(file),sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length},dimensions:f.dimensions,placement:f.placement,construction_release:false};
  }
  return {staging,final:false,publication_status:staging?'STAGING - NOT FINAL; awaiting integrated master hash':reviewDraft?'REVIEW DRAFT; not construction-released':'review drawing; not construction-released',review_draft:reviewDraft,lighting_pending:pending,hd18:notation,note};
}
