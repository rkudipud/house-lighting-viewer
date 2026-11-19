import {build} from 'esbuild';
import {readFile,writeFile,stat,mkdir,copyFile,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {execFileSync} from 'node:child_process';
import {prepare} from './layout_views/data.mjs';
import {prepareTour} from './tour-data.mjs';
import {prepareAnalysis} from './analysis-data.mjs';

const root=dirname(fileURLToPath(import.meta.url));
const args=process.argv.slice(2),source=args[0]&&!args[0].startsWith('--')?args[0]:process.env.HOUSE_DESIGN_PATH;
if(!source)throw new Error('Pass the authoritative house-design.json path: node build.mjs "<master>" --sha <sha256> --heatmaps <heatmaps.json> --heatmaps-sha <sha256>');
const option=name=>args.includes(name)?args[args.indexOf(name)+1]:undefined;
const sha=/^[a-f0-9]{64}$/;
const expected=option('--sha'),heatPath=option('--heatmaps'),heatSha=option('--heatmaps-sha');
if(!sha.test(expected||''))throw new Error('An explicit authorized --sha is required.');
if(!heatPath||!sha.test(heatSha||''))throw new Error('--heatmaps and an explicit --heatmaps-sha are required.');
if(!option('--out'))throw new Error('Pass --out for a separate review build; the published baseline is not overwritten.');
const outDir=resolve(option('--out')),drawings=option('--drawings');
if(outDir===resolve(root)||outDir===resolve(root,'site'))throw new Error('Review output must not overwrite the source or published baseline.');

const bytes=await readFile(source);
const masterSha=createHash('sha256').update(bytes).digest('hex');
const house=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
if(masterSha!==expected)throw new Error('Master hash differs from authorized --sha');
const priorPath=option('--prior-master');
if(!priorPath)throw new Error('--prior-master is required to validate the CCT-only successor.');
const cctDelta=JSON.parse(execFileSync(process.env.PYTHON || 'python',
  [resolve(root,'../../electrician/lighting/source/validate_cct_revision.py'),priorPath,source],{encoding:'utf8'}));
if(cctDelta.current_master_sha256!==masterSha)throw new Error('CCT successor verification does not bind this master.');
const priorSha=cctDelta.prior_master_sha256;
if(!house.visualization_geometry||house.bathrooms.rooms.length!==2||!house.lighting.design_inputs)throw new Error('Required canonical design sections are missing');

// Gates on structured fields (a text scan of the validity block would trip on its own "not released" wording).
const L=house.lighting,V=L.calculation_validity||{};
if(V.construction_release!==false||V.product_approval!==false)throw new Error('Master must state construction_release=false and product_approval=false');
if(!Array.isArray(V.hold_ids)||!V.hold_ids.length)throw new Error('Master calculation_validity.hold_ids are missing');
if(L.status!=='FIXED_WHITE_HOMEOWNER_SIGNED_REVIEW_CANDIDATE_NOT_CONSTRUCTION_RELEASED')throw new Error(`Lighting status is not the signed fixed-white review record: ${L.status}`);
if(!house.storage.items.length||/awaiting|progress|pending/.test(house.storage.status))throw new Error('Storage design is not ready');

const generated=join(dirname(resolve(source)),'generated');
const coordination=JSON.parse(await readFile(option('--coordination-receipt')||join(generated,'homeowner-final-coordination-integration.json'),'utf8'));
const poojaReceipt=JSON.parse(await readFile(option('--pooja-receipt')||join(generated,'pooja-display-decision-receipt.json'),'utf8'));
const supplyBytes=await readFile(option('--supply-receipt')||join(generated,'living-supply-and-cabinet-selections-receipt.json'));
const supplyReceipt=JSON.parse(supplyBytes.toString('utf8'));
const interiorReceiptBytes=await readFile(option('--interior-receipt')||join(generated,'wardrobe-interiors-reference-receipt.json'));
const interiorReceipt=JSON.parse(interiorReceiptBytes.toString('utf8'));
if(coordination.after_master_sha256!==poojaReceipt.before_master_sha256||poojaReceipt.after_master_sha256!==supplyReceipt.before_master_sha256||
   supplyReceipt.after_master_sha256!==interiorReceipt.before_master_sha256||interiorReceipt.after_master_sha256!==priorSha||
   coordination.verification?.house_store_validate!=='PASS'||
   poojaReceipt.decision?.decision_id!=='HS-POOJA-DISPLAY'||supplyReceipt.selected_supply?.retain_supply_id!=='P01'||
   supplyReceipt.selected_supply?.remove_supply_id!=='P03'||
   supplyReceipt.selected_cabinets?.items?.map(i=>i.id).sort().join(',')!=='ST-R04a-WR01,ST-R08-UC01')
  throw new Error('The coordination, pooja and supply/cabinet receipts do not bind this master.');
if(coordination.holds_preserved?.construction_release!==false||coordination.holds_preserved?.product_approval!==false||
   poojaReceipt.retained?.construction_release!==false||poojaReceipt.retained?.product_approval!==false||
   supplyReceipt.holds?.construction_release!==false||supplyReceipt.holds?.product_approval!==false||
   supplyReceipt.selected_cabinets?.construction_release!==false||interiorReceipt.retained?.homeowner_interior_approval!==false||
   interiorReceipt.retained?.construction_release!==false||interiorReceipt.retained?.product_approval!==false)
  throw new Error('The review receipts must retain construction and product holds.');

const {meta:analysis,heat}=await prepareAnalysis(house,heatPath,heatSha);
const wardrobeRef=house.storage.wardrobe_interiors_review,wardrobePath=option('--wardrobes'),wardrobeSha=option('--wardrobes-sha'),wardrobePackDir=option('--wardrobe-pack-dir');
if(!wardrobePath||!sha.test(wardrobeSha||'')||!wardrobePackDir)throw new Error('--wardrobes, --wardrobes-sha and --wardrobe-pack-dir are required');
if(wardrobeRef?.sha256!==wardrobeSha||wardrobeRef.source_master_sha256!==interiorReceipt.before_master_sha256||
   wardrobeRef.homeowner_interior_approval!==false||wardrobeRef.construction_release!==false||
   interiorReceipt.copied_fragment_sha256!==wardrobeSha)throw new Error('Current master does not bind the provisional wardrobe fragment and its holds');
const wardrobeBytes=await readFile(wardrobePath);
if(createHash('sha256').update(wardrobeBytes).digest('hex')!==wardrobeSha)throw new Error('Wardrobe proposal hash differs from authorized --wardrobes-sha');
const wardrobe=JSON.parse(wardrobeBytes.toString('utf8').replace(/^\uFEFF/,''));
if(wardrobe.schema!=='wardrobe-interiors/1'||wardrobe.source_master_sha256!==wardrobeRef.source_master_sha256||
   wardrobe.status!=='provisional_design_not_homeowner_approved_or_fabrication_released')
  throw new Error('Wardrobe interiors are not the provisional proposal referenced by the current master');
const wardrobeReceipt=JSON.parse(await readFile(join(wardrobePackDir,'rollup-receipt.json'),'utf8'));
const wardrobeRebind=wardrobeReceipt.interior_reference_rebind;
if(wardrobeReceipt.source_master_sha256!==priorSha||
   wardrobeReceipt.original_interior_generation_basis_sha256!==wardrobeRef.source_master_sha256||
   wardrobeReceipt.outputs_sha256?.['wardrobe-interiors.json']!==wardrobeSha||
   wardrobeRebind?.sha256!==createHash('sha256').update(interiorReceiptBytes).digest('hex')||
   wardrobeRebind.before_master_sha256!==wardrobeRef.source_master_sha256||wardrobeRebind.after_master_sha256!==priorSha||
   wardrobeRebind.original_interior_source_sha256!==wardrobeSha)
  throw new Error('Wardrobe rollup receipt does not bind this master, the prior interior basis and reference JSON');
for(const id of ['R04','R05','R04a','R08','R09']){
  const room=wardrobe.rooms?.[id];
  if(!room?.sections?.length||!Number.isFinite(room.height_mm))throw new Error(`Missing wardrobe proposal ${id}`);
  for(const s of room.sections){
    if(s.width_status!=='proposed_placeholder_not_site_measured'||!s.bays?.length||
       !s.bays.every(b=>Number.isFinite(b.clear_width_mm)&&b.clear_width_mm>0&&
         [...b.shelf_heights_ffl_mm,...b.rail_heights_ffl_mm,...b.drawers_ffl_mm.flat(),...b.pullouts_ffl_mm.flat()]
         .every(h=>Number.isFinite(h)&&h>=0&&h<=room.height_mm)))
      throw new Error(`Invalid or non-provisional wardrobe proposal ${id}/${s.id}`);
  }
}
const cctMapPath=option('--cct-map'),cctMapSha=option('--cct-map-sha');
const embeddedMap=L.fixed_cct_map;
if(!embeddedMap)throw new Error('The canonical master is missing its integrated fixed-CCT map.');
const embeddedSha=createHash('sha256').update(JSON.stringify(embeddedMap)).digest('hex');
if(!cctMapPath||!sha.test(cctMapSha||''))throw new Error('The current --cct-map and explicit --cct-map-sha are required');
const mapBytes=await readFile(cctMapPath),mapSha=createHash('sha256').update(mapBytes).digest('hex');
if(mapSha!==cctMapSha)throw new Error('Current fixed-CCT map hash differs from authorized --cct-map-sha');
const currentMap=JSON.parse(mapBytes.toString('utf8').replace(/^\uFEFF/,''));
const lightingDir=dirname(resolve(cctMapPath)),manifestBytes=await readFile(join(lightingDir,'manifest.json'));
const manifest=JSON.parse(manifestBytes.toString('utf8').replace(/^\uFEFF/,''));
const lightingVerification=JSON.parse(await readFile(join(lightingDir,'verification.json'),'utf8'));
if(manifest.master_sha256!==masterSha||manifest.files?.['fixed-cct-map.json']?.sha256!==mapSha||
   manifest.files?.['fixed-cct-map.json']?.bytes!==mapBytes.length||manifest.original_heatmaps_sha256!==heatSha||
   lightingVerification.status!=='PASS'||lightingVerification.master_sha256!==masterSha||
   lightingVerification.manifest_sha256!==createHash('sha256').update(manifestBytes).digest('hex'))
  throw new Error('Lighting review manifest and verification do not bind this master, fixed-CCT map and frozen heatmap');
if(currentMap.binding?.master_sha256!==masterSha||!isDeepStrictEqual(currentMap.binding.original_map_binding,embeddedMap.binding))
  throw new Error('Current fixed-CCT map does not preserve the integrated master map binding');
const stripFittingMetadata=f=>{const {placement_hold_ids,viewer_operability,...base}=f;return base;};
const stripPocketMetadata=p=>{const {placement_hold_ids,photometry_credit,...base}=p;return base;};
const stripCandidateMetadata=c=>{const {source,pockets,...base}=c;return base;};
if(!isDeepStrictEqual(currentMap.fittings.map(stripFittingMetadata),embeddedMap.fittings)||
   !isDeepStrictEqual(currentMap.groups,embeddedMap.groups)||!isDeepStrictEqual(currentMap.policy,embeddedMap.policy)||
   !isDeepStrictEqual(currentMap.counts,embeddedMap.counts)||!isDeepStrictEqual(currentMap.status,embeddedMap.status)||
   !isDeepStrictEqual(stripCandidateMetadata(currentMap.curtain_pocket_candidates),stripCandidateMetadata(embeddedMap.curtain_pocket_candidates))||
   !isDeepStrictEqual(currentMap.curtain_pocket_candidates.pockets.map(stripPocketMetadata),embeddedMap.curtain_pocket_candidates.pockets.map(stripPocketMetadata)))
  throw new Error('Current fixed-CCT map changes a signed fitting, group or curtain-candidate value');
const currentSelection=currentMap.selected_curtain_S1;
if(!isDeepStrictEqual([...currentSelection.strips].sort(),L.curtain_pocket_s1.strips.map(s=>s.id).sort())||
   currentSelection.cct_k!==2700||currentSelection.new_knobs!==0||currentSelection.photometry_credit!==false||
   currentSelection.construction_release!==false)
  throw new Error('Current fixed-CCT map does not retain the selected strip identities and holds');
for(const f of currentMap.fittings){
  if(!Array.isArray(f.placement_hold_ids))throw new Error(`Missing placement holds for ${f.id}`);
  if(/^CBR-H[1-6]$/.test(f.id)&&(!f.viewer_operability?.startsWith('ACTIVE_FOR_REVIEW')||f.placement_hold_ids.length))
    throw new Error(`${f.id}: current HIGH review operability differs from the lighting pack`);
}
const cbrCeilingHeld=new Set(['CBR-L1','CBR-X1','CBR-X2','CBR-X3','CBR-X4']);
for(const id of cbrCeilingHeld){
  const fitting=currentMap.fittings.find(f=>f.id===id);
  if(!fitting?.placement_hold_ids.includes('H-CBR-CEIL'))
    throw new Error(`${id}: explicit H-CBR-CEIL must remain attached to its viewer fixture`);
}
for(const p of currentMap.curtain_pocket_candidates.pockets){
  const hold=p.id==='CURT-MBR-W03'?'H-MBR-W03':'H-CURTAIN-POCKET';
  if(!p.placement_hold_ids?.includes(hold)||p.photometry_credit!==false)throw new Error(`${p.id}: current pocket placement or no-lux-credit hold is missing`);
}
const cctMap={json:currentMap,sha256:mapSha,file:cctMapPath,baselineMasterSha:masterSha,
  baseMapSha:coordination.source_artifacts.fixed_cct_map_sha256};
const PLAN=prepareTour(prepare(source,expected),{preview:false,outDir,analysis,cctMap});
PLAN.wardrobeInteriors={sourceSha256:wardrobeSha,sourceMasterSha256:wardrobe.source_master_sha256,status:wardrobe.status,rooms:wardrobe.rooms};
delete PLAN.fixtures.inputs.budget;
delete PLAN.storage;
const nFix=PLAN.fixtures.zones.reduce((n,z)=>n+z.fixtures.length,0),nCirc=PLAN.fixtures.controls.circuits.length;
if(nFix!==104||nCirc!==47)throw new Error(`Expected 104 fixtures / 47 circuits, found ${nFix} / ${nCirc}`);
if(PLAN.curtainPockets.selectedCount!==4)throw new Error('Expected four selected S1 curtain strips');

// The public page keeps provenance file names but never local paths or private photo/attachment names.
const absPath=/^[A-Za-z]:[\\/]/;
const redactions={pathBasenames:0,privateSourcePaths:0,attachmentFields:0};
const pathReplacement=v=>/attachments|whatsapp/i.test(v)?'[private source file, not published]':v.split(/[\\/]/).pop();
const redact=v=>{
  if(typeof v==='string'){
    if(!absPath.test(v))return v;
    const replacement=pathReplacement(v);
    redactions[replacement.startsWith('[private')?'privateSourcePaths':'pathBasenames']++;
    return replacement;
  }
  if(Array.isArray(v))return v.map(redact);
  if(v&&typeof v==='object')return Object.fromEntries(Object.entries(v).flatMap(([k,x])=>{
    if(k==='attachments'){redactions.attachmentFields++;return [];}
    return [[k,redact(x)]];
  }));
  return v;
};
const checkRedaction=(original,publicValue)=>{
  if(typeof original==='string'&&absPath.test(original)){
    if(publicValue!==pathReplacement(original))throw new Error('Unexpected public path transformation');
  }else if(Array.isArray(original)){
    if(!Array.isArray(publicValue)||original.length!==publicValue.length)throw new Error('Public data array changed during privacy redaction');
    original.forEach((v,i)=>checkRedaction(v,publicValue[i]));
  }else if(original&&typeof original==='object'){
    const keys=Object.keys(original).filter(k=>k!=='attachments');
    if(!publicValue||typeof publicValue!=='object'||!isDeepStrictEqual(keys,Object.keys(publicValue)))throw new Error('Public data fields changed during privacy redaction');
    keys.forEach(k=>checkRedaction(original[k],publicValue[k]));
  }else if(!Object.is(original,publicValue))throw new Error('Public non-path data changed during privacy redaction');
};

const PRIVATE=[/(?<![A-Za-z0-9])[A-Za-z]:[\\/]/,/file:\/\/\/?[A-Za-z]:/i,/(?:^|[\s"'(=])\/(?:home|Users)\/[^/\s"'\\]+/i,/attachments/i,/whatsapp/i,/session-state/i,/\.copilot/i,/\\Users\\/i];
const scanText=(label,text)=>{for(const re of PRIVATE){const m=text.match(re);if(m)throw new Error(`${label}: private-path text found (${re}) near "${text.slice(Math.max(0,m.index-40),m.index+60)}"`);}};

await rm(outDir,{recursive:true,force:true});
await mkdir(join(outDir,'downloads'),{recursive:true});

const tag=masterSha.slice(0,8);
const DOWNLOADS=[
  ['layout-views','current-layout-views.pdf',`layout-views-review-draft-${tag}.pdf`,'Layout views: plan, ceiling plan, wall elevations','review draft, not construction released','layout-views-verification.json'],
  ['working-plan','house-working-floorplan.pdf',`working-floor-plan-review-draft-${tag}.pdf`,'Working floor plan','review draft, not construction released','floorplan-verification.json'],
  ['curtain-section','curtain-pocket-section-review.pdf',`curtain-pocket-section-review-${tag}.pdf`,'Curtain pocket section','schematic, unmeasured, not for fabrication','curtain-section-verification.json']
];
PLAN.downloads=[];
if(drawings){
  for(const [dir,name,as,label,note,receiptName] of DOWNLOADS){
    const src=join(drawings,dir,name),buf=await readFile(src);
    const receipt=JSON.parse(await readFile(join(drawings,dir,receiptName),'utf8'));
    const bound=receipt.source_master?.sha256??receipt.master_sha256;
    const pdf=receipt.combined_pdf??receipt.artifacts?.pdf??receipt.artifacts?.find?.(a=>a.file===name);
    const got=createHash('sha256').update(buf).digest('hex');
    if(bound!==priorSha||pdf?.file!==name||pdf.sha256!==got||pdf.bytes!==buf.length)
      throw new Error(`${name}: drawing receipt does not bind the verified predecessor and PDF bytes`);
    if(dir==='layout-views'&&(receipt.checks_total!==receipt.checks_passed||receipt.combined_pdf.pages!==13))
      throw new Error(`${name}: drawing checks or page count failed`);
    if(dir==='working-plan'&&(!receipt.verified_utc||receipt.construction_release!==false||receipt.render?.pdf_pages!==1))
      throw new Error(`${name}: floor-plan verification or review hold is missing`);
    if(dir==='curtain-section'&&(receipt.status!=='REVIEW_DRAFT_NOT_CONSTRUCTION_RELEASED'||receipt.checks?.pdf_pages!==1))
      throw new Error(`${name}: curtain section verification or review hold is missing`);
    for(const re of [/rkudipud/i,/whatsapp/i,/attachments/i,/[A-Za-z]:\\\\Users/i])if(re.test(buf.toString('latin1')))throw new Error(`${name}: private text in PDF bytes (${re})`);
    await copyFile(src,join(outDir,'downloads',as));
    PLAN.downloads.push({href:`downloads/${as}`,label,note,bytes:buf.length,sha256:got});
  }
}
const wardrobePdf=await readFile(join(wardrobePackDir,'wardrobe-signoff-pack.pdf'));
const wardrobePdfSha=createHash('sha256').update(wardrobePdf).digest('hex');
if(wardrobeReceipt.outputs_sha256?.['wardrobe-signoff-pack.pdf']!==wardrobePdfSha||wardrobeReceipt.pdf_pages!==17)
  throw new Error('Wardrobe review PDF does not match the rollup receipt');
const wardrobePdfName=`wardrobe-interiors-review-${tag}.pdf`;
await writeFile(join(outDir,'downloads',wardrobePdfName),wardrobePdf);
PLAN.downloads.push({href:`downloads/${wardrobePdfName}`,label:'Wardrobe and storage proposals',note:'current review pack; interiors originate from 2ce3fcb4; unmeasured, unapproved',bytes:wardrobePdf.length,sha256:wardrobePdfSha});

const PUBLIC=redact(PLAN);
checkRedaction(PLAN,PUBLIC);
await writeFile(join(root,'src','house-data.generated.json'),JSON.stringify({generated:true,plan:PUBLIC}));
const result=await build({entryPoints:[join(root,'src','main.js')],bundle:true,format:'iife',minify:true,write:false,target:['es2020'],legalComments:'inline'});
const js=result.outputFiles[0].text.replaceAll('</script','<\\/script');
const planJson=JSON.stringify(PUBLIC).replaceAll('<','\\u003c');
const heatJson=heat.replaceAll('<','\\u003c');
const threeLicense=await readFile(join(root,'node_modules','three','LICENSE'),'utf8');
if(!threeLicense.includes('Permission is hereby granted')||threeLicense.includes('-->'))throw new Error('Bundled Three.js MIT notice is missing or unsafe to embed');
let html=(await readFile(join(root,'template.html'),'utf8'));
for(const key of ['<!--__PLAN_DATA__-->','<!--__HEAT_DATA__-->','/*__BUNDLE__*/'])if(!html.includes(key))throw new Error(`Template placeholder missing: ${key}`);
html=html.replace('<!--__PLAN_DATA__-->',()=>`<script id="plan-data" type="application/json">${planJson}</script>`)
  .replace('<!--__HEAT_DATA__-->',()=>`<script id="heat-data" type="application/json">${heatJson}</script>`)
  .replace('/*__BUNDLE__*/',()=>js)
  .replace('</head>',()=>`<!-- Bundled Three.js licence:\n${threeLicense}\n-->\n</head>`);
// Third-party licence banners legitimately contain no paths, so the whole page is scanned.
scanText('index.html',html);
const index=join(outDir,'index.html');await writeFile(index,html);
await writeFile(join(outDir,'THREE-LICENSE.txt'),threeLicense);
await writeFile(join(outDir,'.nojekyll'),'');

const htmlBuf=await readFile(index),htmlSha=createHash('sha256').update(htmlBuf).digest('hex');
const planSha=createHash('sha256').update(planJson).digest('hex'),embeddedHeatSha=createHash('sha256').update(heatJson).digest('hex');
const info={
  product:'Hyderabad 2BHK light planner (review draft, not construction released)',
  masterSha256:masterSha,heatmapsSha256:heatSha,
  fixtures:nFix,circuits:nCirc,selectedCurtainStrips:4,effectiveReviewFixtures:108,effectiveReviewCircuits:51,
  fixedCctMapCanonicalJsonSha256:embeddedSha,currentFixedCctMapSha256:mapSha,baseFixedCctMapSha256:cctMap.baseMapSha,cctBins:PLAN.fixedCct.source.bins,
  curtainPocketRecords:PLAN.curtainPockets.pockets.length,status:'LOCAL REVIEW - not published',
  wardrobeInteriorsSha256:wardrobeSha,wardrobeBasisMasterSha256:wardrobe.source_master_sha256,wardrobeStatus:wardrobe.status,
  wardrobeReferenceReceiptSha256:createHash('sha256').update(interiorReceiptBytes).digest('hex'),
  supplyCabinetReceiptSha256:createHash('sha256').update(supplyBytes).digest('hex'),
  htmlSha256:htmlSha,htmlBytes:htmlBuf.length,embeddedPlanDataSha256:planSha,embeddedHeatDataSha256:embeddedHeatSha,
  downloads:PLAN.downloads.map(({href,bytes,sha256})=>({href,bytes,sha256})),
  threeJs:'0.181.1 (bundled; no runtime network access)'
};
scanText('build-info.json',JSON.stringify(info));
await writeFile(join(outDir,'build-info.json'),JSON.stringify(info,null,2));
const privacy={
  authoritativeMasterSha256:masterSha,embeddedPlanDataSha256:planSha,embeddedHeatDataSha256:embeddedHeatSha,viewerHtmlSha256:htmlSha,
  transformation:'The embedded plan is a derived viewer-specific selection, not a byte-identical copy of the authoritative master. The viewer omits the budget and unused source storage object, but retains derived storage items and holds. Absolute path values are replaced by basenames or a private-source marker; attachment fields are omitted. No other derived plan fields or values are changed by privacy redaction.',
  redactions,otherNonPathPlanFieldsPreserved:true,embeddedPlanHashInput:'UTF-8 bytes between the plan-data script tags, including JSON escaping',
  embeddedHeatHashInput:'UTF-8 bytes between the heat-data script tags, including JSON escaping',
  constructionRelease:false
};
scanText('privacy-transform.json',JSON.stringify(privacy));
await writeFile(join(outDir,'privacy-transform.json'),JSON.stringify(privacy,null,2));
const readme=`# Hyderabad 2BHK light planner

Review draft. Not a construction release and not product approval.

A static, offline-capable viewer for the proposed lighting of a four-storey-house flat.
Open \`index.html\` (or the published page): choose a room, walk or orbit the flat, switch lights
on and off, and set LOW (cove / mood) and HIGH (main) brightness per room.
Colour temperatures are fixed per fitting and are not adjustable.
- Fixed CCT per base fitting from the integrated master: ${Object.entries(PLAN.fixedCct.source.bins).map(([k,n])=>`${n} x ${k} K`).join(', ')}. Brightness controls only.
- Current lighting-review fixed-CCT map SHA-256 \`${mapSha}\`; its placement holds are retained separately from viewer on/off state.
- Four selected 2700 K curtain strips follow existing LOW controls. The review schedule has 108 fittings / 51 circuits including these additions; the frozen photometric baseline remains 104 / 47 with no curtain-strip lux credit. Pocket sizes are unmeasured and CURT-MBR-W03 remains held and unlit.
- Dimming is visual only; the lux maps are frozen generic-optics estimates and are not recomputed.
- The four bedside readers and two PIR night lights are individual fitting previews, off by default; held readers cannot be enabled. The actual readers dim on the fitting and the night lights are PIR-operated, not extra wall dimmers.
- The selected dressing and utility cabinets are unmeasured conditional illustrations (FH-ST-03 / FH-ST-12), not construction-ready. One living LOW supply is selected for review; product, protection and electrical design remain on hold.
- Wardrobe interiors are provisional and unapproved; the viewer's open-cabinet illustration is not measured joinery. The current-bound wardrobe review PDF identifies the unchanged original interior-generation basis as 2ce3fcb4; measurement and sign-off remain open.
- Door leaves are hidden in the viewer; openings remain in the design. D01's leaf arrangement remains a site check. Assumed MBR-S and CBR pocket returns extend about 0.30 m beyond modeled room corners. The viewer clips them only for display; actual pocket ends remain unmeasured and held.
- The linked review PDFs are in the adjacent \`downloads\` folder. When the viewer is opened from disk, a browser may open a PDF in a new tab; use the PDF viewer's Save button.
- Bound to the integrated lighting master SHA-256 \`${masterSha}\`.
- Three.js 0.181.1 is bundled into \`index.html\`; its MIT notice is embedded and provided as \`THREE-LICENSE.txt\`. No CDN or network access is needed at runtime.
`;
scanText('README.md',readme);
await writeFile(join(outDir,'README.md'),readme);
console.log(`Built ${outDir}\nindex.html ${(htmlBuf.length/1024/1024).toFixed(2)} MiB sha256 ${htmlSha}\nmaster ${masterSha}\nbase ${nFix} fittings / ${nCirc} circuits; review 108 / 51; downloads ${PLAN.downloads.length}; redactedPaths ${redactions.pathBasenames+redactions.privateSourcePaths}`);
