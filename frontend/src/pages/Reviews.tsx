/* 검토중 사업 — 지원할지 말지 따져 보는 단계.

   공고를 보고 바로 '내 사업' 으로 올리면 실제로 지원하지 않은 것까지 섞여
   진행률·예산이 엉킵니다. 그래서 한 단계를 둡니다.

       공고  →  검토중  →  [지원완료]  →  내 사업
                  └ 참여가능 / 부적합·불확실(사유)

   부적합 사유를 남기는 것이 이 화면의 핵심입니다. 비슷한 공고가 또 왔을 때
   '그때 왜 안 했더라' 를 처음부터 다시 따지지 않기 위해서입니다. */
import { useCallback, useEffect, useState } from "react";
import { dots, fmtWon } from "../lib/format";
import { reviewApi, type Review, type Verdict } from "../lib/reviewApi";

interface Props {
  /** [지원완료] — 사업 등록 화면으로 넘깁니다. */
  onToProject: (r: Review) => void;
  onModal: (msg: string, sub?: string, onOk?: () => void, danger?: boolean) => void;
  /** 공고에서 검토 목록으로 넣은 뒤 새로 읽어 오게 하는 신호 */
  reloadToken?: number;
}

type Tab = "all" | "ok" | "no";

const TABS: { key: Tab; label: string }[] = [
  { key: "all", label: "전체" },
  { key: "ok", label: "참여가능" },
  { key: "no", label: "부적합·불확실" },
];

export default function Reviews({ onToProject, onModal, reloadToken }: Props) {
  const [list, setList] = useState<Review[] | null>(null);
  const [tab, setTab] = useState<Tab>("all");
  const [err, setErr] = useState("");
  /* 사유는 그 자리에서 고칩니다. 다른 화면으로 넘어갔다 오면 흐름이 끊겨
     결국 안 적게 됩니다. */
  const [editing, setEditing] = useState<number | null>(null);
  const [reasonText, setReasonText] = useState("");

  const load = useCallback(async () => {
    try {
      setList(await reviewApi.list());
      setErr("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "검토 목록을 불러오지 못했습니다.");
    }
  }, []);

  useEffect(() => { void load(); }, [load, reloadToken]);

  const 보일것 = (list ?? []).filter((r) => tab === "all" || r.verdict === tab);
  const 셈 = {
    all: list?.length ?? 0,
    ok: list?.filter((r) => r.verdict === "ok").length ?? 0,
    no: list?.filter((r) => r.verdict === "no").length ?? 0,
  };

  async function 저장(r: Review, 바꿀것: Partial<Review>) {
    try {
      await reviewApi.update(r.id, {
        name: r.name, agency: r.agency, amount: r.amount, due: r.due, url: r.url,
        verdict: r.verdict, reason: r.reason, note: r.note,
        announcementId: r.announcementId,
        ...바꿀것,
      });
      await load();
      setErr("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "저장하지 못했습니다.");
    }
  }

  function 결과바꾸기(r: Review, v: Verdict) {
    if (v === "no" && !r.reason.trim()) {
      // 사유 없이 부적합으로 두면 서버가 막습니다. 여기서 바로 적게 합니다.
      setEditing(r.id);
      setReasonText("");
      return;
    }
    void 저장(r, { verdict: v });
  }

  function 지원완료(r: Review) {
    onModal(`'${r.name}' 을(를) 내 사업으로 옮길까요?`,
      "사업 등록 화면으로 넘어갑니다. 등록을 마치면 검토 목록에서 내려갑니다.",
      () => onToProject(r));
  }

  function 지우기(r: Review) {
    onModal(`'${r.name}' 을(를) 검토 목록에서 지울까요?`, "되돌릴 수 없습니다.", () => {
      void (async () => { await reviewApi.remove(r.id); await load(); })();
    }, true);
  }

  return (
    <section className="view on">
      <div className="page-title">검토중 사업</div>

      <div className="rv-bar">
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t.key} type="button"
                    className={"tab" + (tab === t.key ? " on" : "")}
                    onClick={() => setTab(t.key)}>
              {t.label} {셈[t.key]}
            </button>
          ))}
        </div>
        <span className="hint">
          공고 화면에서 [검토 목록에 넣기] 를 누르면 여기로 들어옵니다
        </span>
      </div>

      {err && <div className="err on">{err}</div>}

      <div className="card">
        <div className="tbl-wrap"><table className="tbl">
          <thead><tr>
            <th style={{ width: 152 }}>검토 결과</th>
            <th>사업명</th>
            <th style={{ width: 150 }}>발주처</th>
            <th className="num" style={{ width: 124 }}>공고금액</th>
            <th style={{ width: 110 }}>접수 마감</th>
            <th style={{ width: 260 }} />
          </tr></thead>
          <tbody>
            {보일것.map((r) => (
              <tr key={r.id}>
                <td>
                  <select className="rv-verdict" aria-label="검토 결과"
                          value={editing === r.id ? "no" : r.verdict}
                          data-v={editing === r.id ? "no" : r.verdict}
                          onChange={(e) => 결과바꾸기(r, e.target.value as Verdict)}>
                    <option value="ok">참여가능</option>
                    <option value="no">부적합·불확실</option>
                  </select>
                </td>
                <td>
                  {r.url
                    ? <a href={r.url} target="_blank" rel="noopener noreferrer">{r.name} ↗</a>
                    : r.name}

                </td>
                <td className="cellsub">{r.agency || "-"}</td>
                <td className="num cellnum">{r.amount ? `${fmtWon(r.amount)}원` : "-"}</td>
                <td className="cellsub">{r.due ? dots(r.due) : "-"}</td>
                <td>
                  {/* 부적합·불확실이면 [지원완료] 를 두지 않습니다. 접기로 한
                      사업을 그대로 올릴 수 있으면 분류가 뜻을 잃습니다.
                      참여가능으로 되돌려야 올릴 수 있습니다.
                      그 자리에는 대신 왜 접었는지를 보여 줍니다. */}
                  {(r.verdict === "no" || editing === r.id) ? (
                    editing === r.id ? (
                      <div className="rv-reason-edit">
                        <input autoFocus value={reasonText} placeholder="사유"
                               onChange={(e) => setReasonText(e.target.value)}
                               onKeyDown={(e) => {
                                 if (e.key === "Enter" && reasonText.trim()) {
                                   void 저장(r, { verdict: "no", reason: reasonText });
                                   setEditing(null);
                                 }
                                 if (e.key === "Escape") setEditing(null);
                               }} />
                        <button type="button" className="mini-btn"
                                disabled={!reasonText.trim()}
                                onClick={() => {
                                  void 저장(r, { verdict: "no", reason: reasonText });
                                  setEditing(null);
                                }}>저장</button>
                        <button type="button" className="mini-btn"
                                onClick={() => setEditing(null)}>취소</button>
                      </div>
                    ) : (
                      <div className="rv-acts">
                        <button type="button" className="rv-reason"
                                title="눌러서 고칩니다"
                                onClick={() => { setEditing(r.id); setReasonText(r.reason); }}>
                          {r.reason || "사유"}
                        </button>
                        <button type="button" className="mini-btn danger"
                                onClick={() => 지우기(r)}>삭제</button>
                      </div>
                    )
                  ) : (
                    <div className="rv-acts">
                      <button type="button" className="mini-btn go"
                              onClick={() => 지원완료(r)}>지원완료 →</button>
                      <button type="button" className="mini-btn danger"
                              onClick={() => 지우기(r)}>삭제</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}

            {list !== null && 보일것.length === 0 && (
              <tr><td colSpan={6}><div className="empty">
                {list.length === 0
                  ? "검토중인 사업이 없습니다. 공고 화면에서 [검토 목록에 넣기] 를 눌러 담아 두세요."
                  : "이 분류에 해당하는 사업이 없습니다."}
              </div></td></tr>
            )}
            {list === null && (
              <tr><td colSpan={6}><div className="empty">불러오는 중입니다.</div></td></tr>
            )}
          </tbody>
        </table></div>
      </div>
    </section>
  );
}
