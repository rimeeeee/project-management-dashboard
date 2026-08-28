const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const projects=require("../seed/prototype-seed.json").projects;
const out=[];
for(const p of projects){
  const s=new Date(p.start), e=new Date(p.end);
  // 2026-01-01 부터 600일, 매일 한국시간 09:00 시점으로 비교
  for(let i=0;i<600;i++){
    const n=new Date(Date.UTC(2026,0,1+i,0,0,0)); // KST 09:00 == UTC 00:00
    const v=(s<e)? Math.round(clamp((n-s)/(e-s),0,1)*100) : 0;
    out.push([p.id, i, v].join("\t"));
  }
}
process.stdout.write(out.join("\n"));
