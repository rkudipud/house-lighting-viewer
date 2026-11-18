import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {prepare,DEFAULT_SHA} from './layout_views/data.mjs';
import {buildPlan} from './layout_views/plan.mjs';
import {buildRcp} from './layout_views/rcp.mjs';
import {buildElevations,SHEETS} from './layout_views/elev.mjs';
import {drawingSource} from './drawing-source.mjs';

// usage: node layout_views.mjs <house-design.json> <output folder> [expected master sha256]
const [source,outDir,expected=DEFAULT_SHA,only]=process.argv.slice(2);
if(!source||!outDir)throw new Error('Usage: node layout_views.mjs <house-design.json> <output folder> [expected sha256]');
const D=prepare(source,expected);
if(only&&only!=='--staging'&&only!=='--review-draft')throw new Error('Only --staging or --review-draft is supported after expected SHA.');
D.drawingSource=drawingSource(D.house,source,{staging:only==='--staging',reviewDraft:only==='--review-draft',outDir});
fs.mkdirSync(outDir,{recursive:true});

const total=2+SHEETS.length;
const built=[buildPlan(D,{no:1,total}),buildRcp(D,{no:2,total}),...buildElevations(D,{total})];
const sheets=[];
for(const s of built){
  if(D.drawingSource.staging)s.svg=s.svg.replace('Read-only drawing from the canonical master','STAGING - NOT FINAL; awaiting integrated master hash');
  if(D.drawingSource.review_draft)s.svg=s.svg.replace('Read-only drawing from the canonical master','REVIEW DRAFT \u00b7 read-only drawing from the canonical master');
  fs.writeFileSync(path.join(outDir,`${s.id}.svg`),s.svg,'utf8');
  sheets.push({id:s.id,title:s.title,counts:s.counts,drawn:s.drawn,file:`${s.id}.svg`,sha256:createHash('sha256').update(s.svg).digest('hex')});
}
fs.writeFileSync(path.join(outDir,'sheets.json'),JSON.stringify({master_sha256:D.hash,master_bytes:D.size,drawing_source:D.drawingSource,sheets},null,2));
console.log(JSON.stringify(sheets.map(s=>({id:s.id,counts:s.counts})),null,1));
void only;
