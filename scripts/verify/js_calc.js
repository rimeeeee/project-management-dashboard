const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
function entryTotal(e){
  return (e.spends || []).reduce((s,x)=> s + (Number(x.amt) || 0), 0);
}
// 입력 내역 표의 비목 요약: "장비·재료비 외 2"
function catSummary(e){
  const list = e.spends || [];
  if(!list.length) return "-";
  if(list.length === 1) return list[0].cat;
  return `${list[0].cat} 외 ${list.length - 1}`;
}
function calcActual(p){
  if(!p.tasks.length) return 0;
  return Math.round(100 * p.tasks.filter(t=>t.done).length / p.tasks.length);
}
function calcPlanned(p){
  const s = new Date(p.start), e = new Date(p.end), n = new Date();
  if(!(s < e)) return 0;
  return Math.round(clamp((n - s) / (e - s), 0, 1) * 100);
}
function calcStatus(p){
  const diff = calcActual(p) - calcPlanned(p);
  const hasIssue = latestIssue(p) !== null;
  if(diff < -15) return { key:"c", label:"조치 필요" };
  if(diff < -5 || hasIssue) return { key:"w", label:"점검 필요" };
  return { key:"g", label:"정상" };
}
const STAGES = ["기획","착수","진행","마무리","완료"];
// 예전 데이터에 단계 값이 없을 때만 쓰는 추정값
function autoStage(p){
  const a = calcActual(p);
  const started = new Date() >= new Date(p.start);
  if(a >= 100) return 4;
  if(a >= 75) return 3;
  if(a >= 25) return 2;
  if(started || a > 0) return 1;
  return 0;
}
function calcBudget(p){
  const spent = p.entries.reduce((s,e)=> s + entryTotal(e), 0);
  const rate = p.budget > 0 ? spent / p.budget * 100 : 0;
  const planned = calcPlanned(p);
  return { spent, rate, planned };
}
const hasIssueText = (e) => !!(e.issue && e.issue.trim());
// 아직 해결되지 않은 확인사항이 하나라도 있는지 (상태 판정에 사용)
function openIssues(p){
  return p.entries.filter(e => hasIssueText(e) && !e.issueDone);
}
function latestIssue(p){
  const open = openIssues(p);
  return open.length ? open[open.length - 1] : null;
}
// 확인사항 해결/재개 전환
function toggleIssueDone(pkey){
  const p = proj();
  const e = p.entries.find(x => periodOf(p, x.date).key === pkey);
  if(!e || !hasIssueText(e)) return;
  e.issueDone = !e.issueDone;
  saveState(); renderNav(); renderDash();
}
// 지표 현재값 = 모든 회차 실적의 합계
function kpiValue(p, k){
  return p.entries.reduce((s,e)=> s + (Number(e.kpi && e.kpi[k.name]) || 0), 0);
}

const state={projects:require("../seed/prototype-seed.json").projects};
const out=state.projects.map(p=>{
  const actual=calcActual(p), planned=calcPlanned(p), b=calcBudget(p), st=calcStatus(p);
  const byCat={};
  p.entries.forEach(e=>(e.spends||[]).forEach(s=>{byCat[s.cat]=(byCat[s.cat]||0)+Number(s.amt);}));
  return {
    id:p.id, actual, planned, diff:actual-planned,
    status:st.label, statusKey:st.key,
    tasksDone:p.tasks.filter(t=>t.done).length, tasksTotal:p.tasks.length,
    spent:b.spent, rate:Number(b.rate.toFixed(4)),
    left:Math.max(0,p.budget-b.spent),
    openIssues:openIssues(p).length,
    kpis:p.kpis.map(k=>({name:k.name, value:kpiValue(p,k), target:k.target})),
    byCat:Object.fromEntries(Object.entries(byCat).sort()),
  };
});
process.stdout.write(JSON.stringify(out,null,2));
