import GENERATED from './house-data.generated.json';
import {createPlan} from './master-adapter.js';
export {FT,ZONE_IDS} from './master-adapter.js';
export const PLAN=GENERATED.plan||createPlan(GENERATED);
export const metresRect=r=>r.map(n=>n*.3048);
export const inside=(x,z,r)=>x>=r[0]&&x<=r[2]&&z>=r[1]&&z<=r[3];
export function roomAt(x,z){
  return PLAN.rooms.find(r=>inside(x/.3048,z/.3048,r.rect)&&(!r.cutout||!inside(x/.3048,z/.3048,r.cutout)));
}
