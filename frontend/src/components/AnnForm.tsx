/* 공고 직접 등록 · 수정 — 프로토타입의 공고 폼 팝업을 옮겼습니다.
   수집으로는 채워지지 않는 공고금액·문의처를 손으로 보완할 때 씁니다.
   한 번 손대면 source 가 'manual' 이 되어 다음 수집에 덮어쓰이지 않습니다. */
import { useEffect, useState } from "react";
import { annApi, type Ann, type AnnInput } from "../lib/annApi";

interface Props {
  ann: Ann | null;              // null 이면 신규 등록
  ministries: string[];
  onDone: () => void;
  onClose: () => void;
}

export default function AnnForm({ ann, ministries, onDone, onClose }: Props) {
  const [v, setV] = useState<AnnInput>({
    title: "", ministry: "", agency: "", program: "", no: "",
    posted: "", openFrom: "", due: "", dueTime: "18:00",
    amountEok: 0, contact: "", url: "",
  });
  const [amountText, setAmountText] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ann) {
      setV({
        title: ann.title, ministry: ann.ministry, agency: ann.agency,
        program: ann.program, no: ann.no, posted: ann.posted,
        openFrom: ann.openFrom, due: ann.due, dueTime: ann.dueTime || "18:00",
        amountEok: ann.amount / 1e8, contact: ann.contact, url: ann.url,
      });
      setAmountText(ann.amount ? String(ann.amount / 1e8) : "");
    }
  }, [ann]);

  const set = (k: keyof AnnInput, val: string) => setV({ ...v, [k]: val });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setErr("");
    const body = { ...v, amountEok: Number(amountText.replace(/,/g, "")) || 0 };
    try {
      if (ann) await annApi.update(ann.id, body);
      else await annApi.create(body);
      onDone();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "저장하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="scrim on" role="dialog" aria-modal="true">
      <form className="modal form" onSubmit={submit} autoComplete="off">
        <h3>{ann ? "공고 수정" : "공고 추가"}</h3>
        <div className="f-grid">
          <div className="f" style={{ gridColumn: "1/-1" }}>
            <label htmlFor="anTitle">공고명 *</label>
            <input id="anTitle" placeholder="예: 2026년도 ○○사업 신규지원 대상과제 공고"
                   value={v.title} onChange={(e) => set("title", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anMinistry">부처</label>
            <input id="anMinistry" list="ministryList" placeholder="예: 보건복지부"
                   value={v.ministry} onChange={(e) => set("ministry", e.target.value)} />
            <datalist id="ministryList">
              {ministries.map((m) => <option key={m} value={m} />)}
            </datalist>
          </div>
          <div className="f">
            <label htmlFor="anAgency">전문기관</label>
            <input id="anAgency" placeholder="예: 한국보건산업진흥원"
                   value={v.agency} onChange={(e) => set("agency", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anProgram">사업명</label>
            <input id="anProgram" placeholder="예: 연구중심병원육성(R&D)"
                   value={v.program} onChange={(e) => set("program", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anNo">공고번호</label>
            <input id="anNo"
                   value={v.no} onChange={(e) => set("no", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anPosted">공고일</label>
            <input id="anPosted" type="date" value={v.posted} onChange={(e) => set("posted", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anAmount">공고금액 (억원)</label>
            <input id="anAmount" type="text" inputMode="decimal" placeholder="예: 38"
                   value={amountText} onChange={(e) => setAmountText(e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anFrom">접수 시작일 *</label>
            <input id="anFrom" type="date" value={v.openFrom} onChange={(e) => set("openFrom", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anDue">접수 마감일 *</label>
            <input id="anDue" type="date" value={v.due} onChange={(e) => set("due", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anDueTime">마감 시각</label>
            <input id="anDueTime" type="time" value={v.dueTime} onChange={(e) => set("dueTime", e.target.value)} />
          </div>
          <div className="f">
            <label htmlFor="anContact">문의처</label>
            <input id="anContact"
                   value={v.contact} onChange={(e) => set("contact", e.target.value)} />
          </div>
          <div className="f" style={{ gridColumn: "1/-1" }}>
            <label htmlFor="anUrl">공고 원문 주소</label>
            <input id="anUrl" type="url" placeholder="https://"
                   value={v.url} onChange={(e) => set("url", e.target.value)} />
          </div>
        </div>
        <div className={"form-err" + (err ? " on" : "")}>{err}</div>
        <div className="acts" style={{ marginTop: 16 }}>
          <button type="button" className="no" onClick={onClose}>취소</button>
          <button type="submit" className="ok" disabled={busy}>{busy ? "저장 중…" : (ann ? "저장" : "등록")}</button>
        </div>
      </form>
    </div>
  );
}
