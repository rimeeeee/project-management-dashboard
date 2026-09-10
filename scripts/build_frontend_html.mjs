import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repository = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(repository, "frontend", "dist");
const source = join(dist, "index.html");
const output = join(repository, "docs", "사업관리_대시보드_현재.html");
const offlinePreviewOutput = join(repository, "docs", "사업관리_대시보드_오프라인미리보기.html");

let html = readFileSync(source, "utf8");

const cssMatch = html.match(/<link rel="stylesheet"[^>]+href="\/assets\/([^"]+\.css)"[^>]*>/);
const jsMatch = html.match(/<script type="module"[^>]+src="\/assets\/([^"]+\.js)"[^>]*><\/script>/);

if (!cssMatch || !jsMatch) {
  throw new Error("frontend/dist/index.html에서 빌드된 CSS 또는 JavaScript를 찾지 못했습니다.");
}

const css = readFileSync(join(dist, "assets", cssMatch[1]), "utf8");
const js = readFileSync(join(dist, "assets", jsMatch[1]), "utf8")
  .replace(/<\/script/gi, "<\\/script");

html = html
  // 함수 치환을 써야 번들 안의 `$&`, `$1` 같은 문자열이 replace 치환식으로
  // 해석되지 않고 JavaScript 원문 그대로 들어갑니다.
  .replace(cssMatch[0], () => `<style>\n${css}\n</style>`)
  .replace(jsMatch[0], () => `<script type="module">\n${js}\n</script>`)
  .replace(
    "<body>",
    "<!-- 현재 React 프런트엔드의 단일 HTML 내보내기입니다. 실제 데이터는 같은 서버의 /api를 사용합니다. -->\n<body>",
  );

if (!html.includes(css) || !html.includes(js) || /<(?:script|link)[^>]+(?:src|href)="\/assets\//.test(html)) {
  throw new Error("빌드 자산을 단일 HTML에 정상적으로 포함하지 못했습니다.");
}

writeFileSync(output, html, "utf8");
console.log(output);

const months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"];
const monthlyRows = [
  { cat: "인건비", values: [15, 15, 15, 15, 15, 15, 15, 15, 0] },
  { cat: "연구활동비", values: [0, 10, 5, 10, 5, 8, 10, 5, 5] },
  { cat: "장비재료비", values: [0, 5, 5, 15, 0, 10, 12, 0, 8] },
  { cat: "기타", values: [0, 0, 0, 5, 0, 5, 5, 5, 5] },
].map(({ cat, values }) => ({
  cat,
  byMonth: Object.fromEntries(months.map((month, index) => [month, values[index] * 1_000_000])),
  total: values.reduce((sum, value) => sum + value, 0) * 1_000_000,
}));
const monthlyTotals = Object.fromEntries(months.map((month) => [
  month,
  monthlyRows.reduce((sum, row) => sum + row.byMonth[month], 0),
]));
const summary = {
  id: "preview-project",
  name: "연구중심병원 육성(R&D) 협력지원 과제",
  agency: "보건복지부 · 한국보건산업진흥원",
  start: "2026-01-01",
  end: "2026-12-31",
  budget: 950_000_000,
  cycle: "주간",
  cycleWord: "주간",
  dday: { txt: "D-112", cls: "open" },
  latestIssue: "협력기관 일정 확정 필요",
  actual: 60,
  planned: 70,
  diff: -10,
  status: { key: "w", label: "점검 필요" },
  progressColor: "w",
  tasksDone: 3,
  tasksTotal: 5,
  spent: 258_000_000,
  rate: 27.2,
  left: 692_000_000,
};
const categories = [
  { name: "인건비", allocated: 380_000_000, gov: 320_000_000, own: 60_000_000, basis: "월 38,000,000원 × 10개월" },
  { name: "연구활동비", allocated: 210_000_000, gov: 180_000_000, own: 30_000_000, basis: "연구활동 및 전문가 활용비" },
  { name: "장비재료비", allocated: 180_000_000, gov: 150_000_000, own: 30_000_000, basis: "연구장비 및 재료 구입" },
  { name: "기타", allocated: 60_000_000, gov: 50_000_000, own: 10_000_000, basis: "회의·출장 등 운영비" },
];
const entries = months.map((month, index) => {
  const spends = monthlyRows
    .map((row) => ({ cat: row.cat, amt: row.byMonth[month], on: `${month}-15` }))
    .filter((spend) => spend.amt > 0);
  return {
    periodKey: `${month}-15`, date: `${month}-15`,
    periodLabel: `${Number(month.slice(5))}월`, periodFull: `2026년 ${Number(month.slice(5))}월 입력`,
    spends, spendTotal: monthlyTotals[month], catSummary: spends.map((spend) => spend.cat).join(" · "),
    kpi: {}, act: index === 8 ? "협력기관 실무회의 및 연구자료 정리" : "월별 연구과제 수행",
    issue: index === 8 ? "협력기관 일정 확정 필요" : "", plan: index === 8 ? "다음 주 중 일정 재협의" : "",
    issueDone: false, enteredBy: "미리보기", updatedBy: "미리보기",
    updatedAt: `${month}-15T14:00:00+09:00`, version: 1,
  };
});
const project = {
  ...summary,
  folderUrl: "",
  stage: 2,
  stages: ["기획", "착수", "진행", "마무리", "완료"],
  stageNotes: ["사업계획 수립 완료", "협약 체결 완료", "연구 수행 중", "", ""],
  categories,
  catRows: categories.map((category) => ({
    ...category,
    used: monthlyRows.find((row) => row.cat === category.name)?.total ?? 0,
  })),
  account: "연구개발비",
  monthly: { months, rows: monthlyRows, totals: monthlyTotals, grand: 258_000_000 },
  tasks: [
    { name: "협약 체결 및 연구비 계좌 개설", done: true, stage: 1 },
    { name: "연구개발계획서 확정", done: true, stage: 1 },
    { name: "연구 데이터 수집", done: true, stage: 2 },
    { name: "중간 진도보고서 제출", done: false, stage: 3 },
    { name: "연차 실적·정산 보고", done: false, stage: 4 },
  ],
  stageRows: [
    { name: "기획", done: 0, total: 0, rate: 0, current: false },
    { name: "착수", done: 2, total: 2, rate: 100, current: false },
    { name: "진행", done: 1, total: 1, rate: 100, current: false },
    { name: "마무리", done: 0, total: 1, rate: 0, current: true },
    { name: "완료", done: 0, total: 1, rate: 0, current: false },
  ],
  kpis: [
    { name: "SCI(E) 논문 게재", unit: "건", target: 2, value: 1 },
    { name: "특허 출원", unit: "건", target: 2, value: 1 },
    { name: "공동 워크숍", unit: "회", target: 2, value: 1 },
  ],
  todos: [
    { id: "todo-1", text: "중간 진도보고서 초안 작성", due: "2026-09-18", done: false },
    { id: "todo-2", text: "협력기관 회의 일정 확정", due: "2026-09-14", done: false },
  ],
  entries,
};
const periods = months.map((month) => ({
  key: `${month}-15`, label: `${Number(month.slice(5))}월`, full: `2026년 ${Number(month.slice(5))}월 입력`,
  date: `${month}-15`, hasEntry: true, version: 1,
}));

const offlineMockCode = `
/* 오프라인 미리보기: 서버 요청 대신 아래 예시 데이터를 반환합니다. 저장 내용은 유지되지 않습니다. */
(function(){
  var project = ${JSON.stringify(project)};
  var summary = ${JSON.stringify(summary)};
  var periods = ${JSON.stringify(periods)};
  var settings = {ann_filter:{include:[],ministries:[],amount:"all"},manual_url:{url:""}};
  function json(value, status){
    return Promise.resolve(new Response(JSON.stringify(value), {
      status: status || 200, headers:{"Content-Type":"application/json"}
    }));
  }
  window.fetch = function(input){
    var raw = typeof input === "string" ? input : input.url;
    var path = new URL(raw, "https://offline.preview").pathname;
    if(path === "/api/auth/session") return json({authenticated:true,using_default_password:false});
    if(path === "/api/projects") return json([summary]);
    if(path === "/api/projects/preview-project") return json(project);
    if(path === "/api/projects/preview-project/periods") return json(periods);
    if(path === "/api/settings") return json(settings);
    if(path === "/api/reviews") return json([]);
    if(path === "/api/collector/status") return json({last:null});
    if(path === "/api/announcements") return json({items:[],total:0,page:1,pages:1,size:40,from:0,to:0,facets:{ministries:[],tabs:{all:0,upcoming:0,open:0,closed:0,fav:0}}});
    if(path === "/api/projects/preview-project/meetings") return json([]);
    return json({detail:"오프라인 미리보기에서는 저장 기능을 사용할 수 없습니다."}, 400);
  };
})();
`;
// 생성 단계에서 목 데이터 스크립트의 문법도 확인합니다.
new Function(offlineMockCode);
const offlineMock = `<script>${offlineMockCode}</script>`;
const offlinePreview = html
  .replace("<title>사업관리 대시보드</title>", "<title>사업관리 대시보드 · 오프라인 미리보기</title>")
  .replace('<script type="module">', `${offlineMock}\n<script type="module">`);

writeFileSync(offlinePreviewOutput, offlinePreview, "utf8");
console.log(offlinePreviewOutput);
