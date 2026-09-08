/* 서버가 내려주는 모양. 계산은 서버(backend/app/core/calc.py)에서 끝내고
   화면은 표시만 합니다. 규칙이 두 군데 있으면 한쪽만 고쳐져 숫자가 어긋납니다. */

export interface Status {
  key: "g" | "w" | "c";
  label: string;              // 정상 / 점검 필요 / 조치 필요
}

export interface DDay {
  txt: string;
  cls: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  agency: string;
  start: string;
  end: string;
  budget: number;
  cycle: string;
  cycleWord: string;
  dday: DDay;
  latestIssue: string;
  actual: number;
  planned: number;
  diff: number;
  status: Status;
  // 진행률 숫자·게이지 색. 상태 배지와 달리 확인사항은 반영하지 않습니다.
  progressColor: "" | "w" | "c";
  tasksDone: number;
  tasksTotal: number;
  spent: number;
  rate: number;
  left: number;
}

export interface Spend {
  cat: string;               // 세목 이름
  amt: number;
  on: string;                // 지출일 YYYY-MM-DD. 월별 합산의 기준입니다
}

/** 월별 × 세목 집행액. months 는 "YYYY-MM" 이 이어진 목록입니다. */
export interface Monthly {
  months: string[];
  rows: { cat: string; byMonth: Record<string, number>; total: number }[];
  totals: Record<string, number>;
  grand: number;
}

export interface Entry {
  periodKey: string;
  date: string;
  periodLabel: string;
  periodFull: string;
  spends: Spend[];
  spendTotal: number;
  catSummary: string;
  kpi: Record<string, number>;
  act: string;
  issue: string;
  plan: string;
  issueDone: boolean;
  enteredBy: string;
  updatedBy: string;
  updatedAt: string;
  version: number;
}

export interface Todo {
  id: string;
  text: string;
  due: string;
  done: boolean;
}

/* 세목 한 줄.

     사업 (계정과목: 인건비)
       └ 세목 (연구수당 · 4대보험)
           └ 집행 내역

   계정과목은 사업마다 하나라 ProjectDetail.account 에 있습니다. */
export interface CatRow {
  name: string;
  used: number;
  allocated: number;
  gov: number;
  own: number;
  /** 편성액 산출 근거 쪽지. "단가 2,000,000 × 5명 × 8개월" 처럼 적습니다. */
  basis: string;
}

export interface Kpi {
  name: string;
  unit: string;
  target: number;
  value: number;
}

export interface ProjectDetail extends ProjectSummary {
  folderUrl: string;
  stage: number;
  stages: string[];
  stageNotes: string[];
  /* allocated 는 gov + own 입니다. 화면 숫자는 이 합계를 쓰고,
     나눈 둘은 사업을 고칠 때 입력칸을 다시 채우는 데 씁니다. */
  categories: {
    name: string; allocated: number; gov: number; own: number; basis: string;
  }[];
  catRows: CatRow[];
  /** 계정과목. 사업마다 하나이고, 이 사업에서 쓴 돈은 모두 이 과목으로 잡힙니다. */
  account: string;
  monthly: Monthly;
  tasks: { name: string; done: boolean; stage: number }[];
  /* 단계별 완료 집계. current 는 '아직 끝나지 않은 과제가 처음 나오는 단계' 로
     서버가 계산합니다(손으로 고르지 않습니다). */
  stageRows: { name: string; done: number; total: number; rate: number; current: boolean }[];
  kpis: Kpi[];
  todos: Todo[];
  entries: Entry[];
}

export interface AppSettings {
  ann_filter: { include: string[]; ministries: string[]; amount: string };
  manual_url: { url: string };
}

export interface PeriodOption {
  key: string;
  label: string;
  full: string;
  date: string;
  hasEntry: boolean;
  version: number;
}
