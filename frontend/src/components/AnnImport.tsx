/* 수집 데이터 불러오기.

   서버가 정기적으로 수집하므로 평소에는 쓸 일이 없습니다.
   서버가 바깥 인터넷에 나갈 수 없는 것으로 판명될 경우의 대비책으로 남겨 둡니다.
   인터넷이 되는 PC 에서 공고수집 스크립트를 돌려 결과만 여기에 붙여넣습니다. */
import { useState } from "react";
import { annApi } from "../lib/annApi";

interface Props {
  onDone: (msg: string, sub: string) => void;
  onClose: () => void;
}

export default function AnnImport({ onDone, onClose }: Props) {
  const [text, setText] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      setErr("형식이 올바르지 않습니다. 공고데이터.json 내용 전체를 붙여넣었는지 확인하세요.");
      return;
    }
    const list = Array.isArray(parsed)
      ? parsed
      : (parsed as { announcements?: unknown[] })?.announcements;
    if (!Array.isArray(list)) {
      setErr("공고 목록을 찾을 수 없습니다. 수집 스크립트가 만든 파일인지 확인하세요.");
      return;
    }
    setBusy(true);
    try {
      const r = await annApi.importJson(list);
      onDone("불러왔습니다",
        `새 공고 ${r.added}건 · 갱신 ${r.updated}건` + (r.kept ? ` · 직접 등록 유지 ${r.kept}건` : ""));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "불러오지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="scrim on" role="dialog" aria-modal="true">
      <div className="modal form" style={{ maxWidth: 620 }}>
        <h3>수집 데이터 불러오기</h3>
        <p style={{ fontSize: "14.4px", color: "var(--ink-2)", marginBottom: 10 }}>
          평소에는 서버가 알아서 수집합니다. 이 창은 서버가 바깥 인터넷에 나갈 수 없을 때
          쓰는 대비책입니다. 인터넷이 되는 PC 에서 공고수집 스크립트를 돌린 뒤,
          만들어진 <b>공고데이터.json</b> 내용 전체를 붙여넣으세요.
        </p>
        <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false}
                  placeholder={'{"announcements": [ ... ]}'} aria-label="수집 데이터"
                  style={{ minHeight: 220, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }} />
        <div className={"form-err" + (err ? " on" : "")}>{err}</div>
        <div className="acts" style={{ marginTop: 16 }}>
          <button type="button" className="no" onClick={onClose}>취소</button>
          <button type="button" className="ok" onClick={run} disabled={busy}>
            {busy ? "불러오는 중…" : "불러오기"}
          </button>
        </div>
      </div>
    </div>
  );
}
