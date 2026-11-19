export const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
export const fx=(n,d=3)=>Number(n).toFixed(d);

export const COMPASS_NOTE='Drawn south-up (not rotated): sheet-top = SOUTH (utility/washing), sheet-bottom = NORTH (entrance/balcony), sheet-left = EAST (kitchen/dining/living), sheet-right = WEST (bedrooms).';
export const COMPASS_SOURCE='Compass: approximate homeowner north, recorded in the master (visualization_geometry.orientation): entrance/balcony/stairs face NORTH. Cardinal directions only \u2014 true bearing and magnetic declination are not surveyed.';
export const HEIGHT_NOTE='HEIGHTS (unsurveyed): except in R05, the 2.959 m band and 3.188 m slab underside are derived from homeowner-stated HD-11 figures and assumed slab/finish thicknesses. R05 only: band 3.048 m and centre approximately 3.277 m are homeowner-reported. The reported centre conflicts with the older slab estimate; actual slab and panel levels and their construction remain unmeasured. Bathrooms, utility, lobby and balcony levels are placeholders; opening heads are assumed. Verify all levels on site.';
export const CENTRE_NOTE='Raised centre (HD-14): a separate gypsum/POP panel below the slab. The homeowner confirms space will be provided for the aluminium profile/track and wiring; the clear cavity depth, the panel level and the driver location are unmeasured. LIV-X1/X2, DIN-X1 and DIN-L1 need a conditional product-fit and access check (H-CENTRE-RECESS). No slab chase or structural cutting is authorised.';
export const CURTAIN_NOTE='Curtains (HD-14): living, master and children\u2019s rooms carry TWO layers (sheer + blackout) on ceiling-mounted tracks concealed in recessed pockets, so each pocket needs two tracks. Track spacing, bracket dimensions, stack and clear pocket width/depth are unverified; pocket outlines here are indicative only.';
export const POOJA_NOTE='Pooja niche PN1: already built; its east-wall relationship is homeowner-confirmed (HD-10). HD-18 clarifies feet-and-inches notation, but dimensions and position remain homeowner estimates, not site measurements (OI-POOJA-01). The homeowner reports a reinforced slab extension beyond the 9-inch wall, top to bottom through the building. Extension geometry and load capacity are unverified: only the estimated front outline is drawn, not a physical back or structural section. No cutting or structural change is requested or approved.';

const STYLE=`text{font-family:"Segoe UI",Arial,sans-serif;fill:#203b43}
.mono{font-family:Consolas,monospace}.muted{fill:#5d7174}.green{fill:#266c5c}.blue{fill:#3d6288}.amber{fill:#9b641c}.red{fill:#a23b3b}
.title{font-size:34px;font-weight:600}.sub{font-size:18px}.sect{font-size:17px;font-weight:650;letter-spacing:1px}
.halo{paint-order:stroke;stroke:#fff;stroke-linejoin:round}`;

export function makeSheet({width,title,desc,metadata}){
  const parts=[];
  const add=s=>parts.push(s);
  const text=(x,y,value,size=17,cls='',anchor='start',extra='')=>add(`<text x="${fx(x,2)}" y="${fx(y,2)}" font-size="${size}" class="${cls}" text-anchor="${anchor}" ${extra}>${esc(value)}</text>`);
  const wrap=(x,y,value,w,size=16,leading=22,cls='')=>{
    const words=String(value).split(/\s+/);let line='',n=0;
    for(const word of words){
      if((line.length+word.length+1)*size*.52>w&&line){text(x,y+n*leading,line,size,cls);n++;line=word;}else line+=(line?' ':'')+word;
    }
    if(line){text(x,y+n*leading,line,size,cls);n++;}
    return y+n*leading;
  };
  // model-unit helpers: call inside a scaled group, sizes and stroke widths in metres
  const rect=(r,fill,stroke='#819594',sw=.012,extra='')=>add(`<rect x="${fx(r[0],4)}" y="${fx(r[1],4)}" width="${fx(r[2]-r[0],4)}" height="${fx(r[3]-r[1],4)}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`);
  const line=(a,b,color='#71878a',sw=.012,extra='')=>add(`<path d="M${fx(a[0],4)} ${fx(a[1],4)}L${fx(b[0],4)} ${fx(b[1],4)}" fill="none" stroke="${color}" stroke-width="${sw}" ${extra}/>`);
  const path=(d,fill='none',stroke='#71878a',sw=.012,extra='')=>add(`<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" ${extra}/>`);
  const label=(x,y,value,size=.12,color='#203b43',anchor='middle',extra='')=>add(`<text x="${fx(x,4)}" y="${fx(y,4)}" font-size="${size}" fill="${color}" text-anchor="${anchor}" class="halo" stroke-width="${fx(size*.22,4)}" ${extra}>${esc(value)}</text>`);
  const lines=(x,y,arr,size,color,anchor='middle',leading=1.22)=>arr.forEach((v,i)=>label(x,y+i*size*leading,v,size,color,anchor));
  const finish=height=>`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="t d">
<title id="t">${esc(title)}</title>
<desc id="d">${esc(desc)}</desc>
<metadata>${esc(JSON.stringify(metadata))}</metadata>
<defs>
<pattern id="hold" width=".10" height=".10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width=".10" height=".10" fill="#fbf0d7"/><path d="M0 0V.10" stroke="#cf9a43" stroke-width=".02"/></pattern>
<pattern id="zone" width=".09" height=".09" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><rect width=".09" height=".09" fill="#eaf0f7"/><path d="M0 0V.09" stroke="#a9bdd6" stroke-width=".011"/></pattern>
<pattern id="loft" width=".08" height=".08" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width=".08" height=".08" fill="#f2f0f8"/><path d="M0 0V.08" stroke="#b9b1d3" stroke-width=".010"/></pattern>
<pattern id="beam" width=".08" height=".08" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width=".08" height=".08" fill="#ecd9bd"/><path d="M0 0V.08" stroke="#c49a5c" stroke-width=".012"/></pattern>
<pattern id="feature" width=".06" height=".06" patternUnits="userSpaceOnUse" patternTransform="rotate(90)"><rect width=".06" height=".06" fill="#bfe0dc"/><path d="M0 0V.06" stroke="#5aa39b" stroke-width=".012"/></pattern>
<pattern id="plain" width=".15" height=".15" patternUnits="userSpaceOnUse"><rect width=".15" height=".15" fill="#f3f6f6"/><path d="M0 0H.15V.15" fill="none" stroke="#d6dfdf" stroke-width=".006"/></pattern>
<pattern id="nowall" width=".12" height=".12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width=".12" height=".12" fill="#fafafa"/><path d="M0 0V.12" stroke="#d9d9d9" stroke-width=".008"/></pattern>
<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#466c92"/></marker>
</defs>
<style>${STYLE}</style>
<rect width="${width}" height="${height}" fill="#fcfdfc"/>
${parts.join('\n')}
</svg>`;
  return {add,text,wrap,rect,line,path,label,lines,finish};
}

export function northArrow(S,x,y,r=30){
  S.add(`<g id="north-arrow" data-north="sheet-bottom" transform="translate(${x} ${y})"><circle r="${r}" fill="#fff" stroke="#203b43" stroke-width="1.5"/>
<path d="M0 ${r-6}L${fx(r*.38,1)} ${fx(-r*.45,1)}L0 ${fx(-r*.2,1)}L${fx(-r*.38,1)} ${fx(-r*.45,1)}Z" fill="#203b43"/>
<text y="${r+17}" font-size="16" font-weight="700" text-anchor="middle">N</text>
<text y="${-r-6}" font-size="12" class="muted" text-anchor="middle">S</text></g>`);
}

export function pageHeader(S,{title,subtitle,no,total,hash}){
  S.text(60,60,title,34,'title');
  S.text(62,92,subtitle,18,'muted sub');
  S.text(1560,48,`SHEET ${no} / ${total}`,15,'muted','end');
  S.text(1560,70,'house-design.json',16,'mono','end');
  S.text(1560,90,hash.slice(0,24)+'…',13,'mono muted','end');
  northArrow(S,1604,62,20);
  S.add('<path d="M60 116H1640" stroke="#c8d2d3"/>');
}

export function pageFooter(S,y,hash){
  S.add(`<path d="M60 ${y-34}H1640" stroke="#c8d2d3"/>`);
  S.text(60,y-12,'Master SHA256: '+hash,12.5,'mono muted');
  S.text(1640,y-12,'Read-only drawing from the canonical master \u00b7 not a construction release \u00b7 unmeasured levels and sizes marked',13,'amber','end');
}
