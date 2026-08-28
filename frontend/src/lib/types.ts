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
  cat: string;
  amt: number;
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

export interface CatRow {
  name: string;
  used: number;
  allocated: number;
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
  categories: { name: string; allocated: number }[];
  catRows: CatRow[];
  tasks: { name: string; done: boolean }[];
  kpis: Kpi[];
  todos: Todo[];
  entries: Entry[];
}

export interface AppSettings {
  ann_filter: { include: string[]; ministries: string[]; amount: string };
  manual_url: { url: string };
}
