const pad2=(n)=>String(n).padStart(2,"0");
const isoOf=(d)=>`${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
const mdOf=(d)=>`${pad2(d.getMonth()+1)}.${pad2(d.getDate())}`;
function startOfWeek(d){
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7));   // 월요일로 이동
  return x;
}
// 그 달의 몇 번째 주인지 (해당 주의 월요일이 그 달의 n번째 월요일)
function weekOfMonth(monday){
  return Math.floor((monday.getDate() - 1) / 7) + 1;
}
/* 반환값
   key   : 저장·비교용 고유 키
   label : 짧은 표기 (로그·확인사항)      예) 08.24 ~ 08.30
   full  : 주차를 포함한 표기 (드롭다운·입력 내역) 예) 8월 4주차 · 08.24 ~ 08.30 */
function periodOf(p, dateISO){
  const d = new Date(dateISO + "T00:00:00");
  if(p.cycle === "월간"){
    const s = new Date(d.getFullYear(), d.getMonth(), 1);
    const e = new Date(d.getFullYear(), d.getMonth()+1, 0);
    const label = `${s.getFullYear()}년 ${s.getMonth()+1}월`;
    return { key:`M${s.getFullYear()}-${pad2(s.getMonth()+1)}`, start:s, end:e, label, full:label };
  }
  if(p.cycle === "격주"){
    const anchor = new Date(p.start + "T00:00:00");
    const idx = Math.floor((d - anchor) / (14 * 86400000));
    const s = new Date(anchor); s.setDate(anchor.getDate() + idx * 14);
    const e = new Date(s); e.setDate(s.getDate() + 13);
    const label = `${mdOf(s)} ~ ${mdOf(e)}`;
    return { key:`B${idx}`, start:s, end:e, label, full:`${idx + 1}회차 · ${label}` };
  }
  const s = startOfWeek(d);
  const e = new Date(s); e.setDate(s.getDate() + 6);
  const label = `${mdOf(s)} ~ ${mdOf(e)}`;
  return { key:`W${isoOf(s)}`, start:s, end:e, label,
           full:`${s.getMonth()+1}월 ${weekOfMonth(s)}주차 · ${label}` };
}
// 오늘 회차부터 과거로 n개
const out=[];
for(const cycle of ["주간","격주","월간"]){
  const p={cycle, start:"2026-06-01"};
  // 2026-01-01 부터 900일치 전부 비교
  for(let i=0;i<900;i++){
    const d=new Date(2026,0,1+i);
    const o=periodOf(p, isoOf(d));
    out.push([cycle, isoOf(d), o.key, isoOf(o.start), isoOf(o.end), o.label, o.full].join("\t"));
  }
}
process.stdout.write(out.join("\n"));
