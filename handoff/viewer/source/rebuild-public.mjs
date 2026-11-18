import {build} from 'esbuild';
import {readFile,writeFile} from 'node:fs/promises';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root=dirname(fileURLToPath(import.meta.url));
const args=process.argv.slice(2);
if(args.length!==2||args[0]!=='--out')throw new Error('Usage: node rebuild-public.mjs --out <new HTML file>');
const output=resolve(args[1]);
const sha=value=>createHash('sha256').update(value).digest('hex');
const receipt=JSON.parse(await readFile(join(root,'public-source-manifest.json'),'utf8'));
const generated=JSON.parse(await readFile(join(root,'src','house-data.generated.json'),'utf8'));
if(!generated.generated||generated.plan?.master?.sha256!==receipt.authoritativeMasterSha256)
  throw new Error('Derived plan is not bound to the recorded authoritative master');
const planJson=JSON.stringify(generated.plan).replaceAll('<','\\u003c');
const heatJson=await readFile(join(root,'data','heat-data.json'),'utf8');
if(sha(planJson)!==receipt.embeddedPlanDataSha256||sha(heatJson)!==receipt.embeddedHeatDataSha256)
  throw new Error('Public plan or heat data differs from the recorded embedded data');
const result=await build({entryPoints:[join(root,'src','main.js')],bundle:true,format:'iife',minify:true,write:false,target:['es2020'],legalComments:'inline'});
const js=result.outputFiles[0].text.replaceAll('</script','<\\/script');
const license=await readFile(join(root,'node_modules','three','LICENSE'),'utf8');
if(!license.includes('Permission is hereby granted')||license.includes('-->'))throw new Error('Three.js MIT licence is missing or unsafe');
let html=await readFile(join(root,'template.html'),'utf8');
for(const key of ['<!--__PLAN_DATA__-->','<!--__HEAT_DATA__-->','/*__BUNDLE__*/'])if(!html.includes(key))throw new Error(`Template placeholder missing: ${key}`);
html=html.replace('<!--__PLAN_DATA__-->',()=>`<script id="plan-data" type="application/json">${planJson}</script>`)
  .replace('<!--__HEAT_DATA__-->',()=>`<script id="heat-data" type="application/json">${heatJson}</script>`)
  .replace('/*__BUNDLE__*/',()=>js)
  .replace('</head>',()=>`<!-- Bundled Three.js licence:\n${license}\n-->\n</head>`);
const actual=sha(html);
if(actual!==receipt.viewerHtmlSha256)throw new Error(`Rebuilt HTML differs from the verified viewer (${actual})`);
await writeFile(output,html,{flag:'wx'});
console.log(`Rebuilt verified viewer SHA-256 ${actual}`);
