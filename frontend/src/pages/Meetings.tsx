/* 회의록 — 사업비 지출 증빙(감사·정산)에 쓰는 문서.

   사업 안에 있습니다. 회의록은 그 사업 예산을 쓴 근거라, 사업과 떨어지면
   '어느 사업 회의비인지' 가 사라져 증빙 구실을 못 합니다.

   AI 는 초안만 만듭니다. 만든 내용은 저장되지 않고 화면에만 올라오며,
   사람이 고쳐서 저장을 눌러야 남습니다. */
import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../lib/api";
import { dots, fmtMoney, fmtWon } from "../lib/format";
import { meetingApi, type Meeting, type MeetingIn, type MeetingPhoto } from "../lib/meetingApi";
import { todayISO } from "../lib/format";

interface Props {
  projectId: string;
  onModal: (msg: string, sub?: string, onOk?: () => void, danger?: boolean) => void;
}

const 빈값 = (): MeetingIn => ({
  title: "", metOn: todayISO(), place: "", attendees: [], bullets: [], memo: "", amount: 0,
});

const onlyDigits = (s: string) => s.replace(/[^\d]/g, "");
const commas = (s: string) => (s ? Number(s).toLocaleString("ko-KR") : "");

export default function Meetings({ projectId, onModal }: Props) {
  const [list, setList] = useState<Meeting[] | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [v, setV] = useState<MeetingIn>(빈값);
  const [amountText, setAmountText] = useState("");
  const [attendeeText, setAttendeeText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // AI 관련
  const [aiBusy, setAiBusy] = useState(false);
  const [titleChips, setTitleChips] = useState<string[]>([]);
  /* 다시 생성할 때 앞의 결과를 옆에 두고 견줍니다. 새로 만든 것이 늘 나은
     것은 아니라서, 바로 덮어쓰면 좋았던 문장을 잃습니다. */
  const [prevBullets, setPrevBullets] = useState<string[] | null>(null);

  /* 이미 저장된 회의록에 붙어 있는 사진 */
  const [photos, setPhotos] = useState<MeetingPhoto[]>([]);
  /* 아직 저장하지 않은 회의록에 붙일 사진.
     사진은 회의록 번호가 있어야 올릴 수 있는데, 저장 전에는 번호가 없습니다.
     그렇다고 '먼저 저장하세요' 라고만 하면 회의록을 쓰다 말고 저장부터 해야
     해서 흐름이 끊깁니다. 그래서 파일을 들고 있다가 저장할 때 함께 올립니다. */
  const [pending, setPending] = useState<{ file: File; url: string }[]>([]);
  const [dragOver, setDragOver] = useState(false);

  const load = useCallback(async () => {
    try {
      setList(await meetingApi.list(projectId));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "회의록을 불러오지 못했습니다.");
    }
  }, [projectId]);

  useEffect(() => { void load(); }, [load]);

  function reset() {
    setV(빈값()); setAmountText(""); setAttendeeText("");
    setEditingId(null); setTitleChips([]); setPrevBullets(null); setErr("");
    setPhotos([]);
    pending.forEach((x) => URL.revokeObjectURL(x.url));
    setPending([]);
  }

  function edit(m: Meeting) {
    setV({
      title: m.title, metOn: m.metOn, place: m.place,
      attendees: [...m.attendees], bullets: [...m.bullets],
      memo: m.memo, amount: m.amount,
    });
    setAmountText(m.amount ? m.amount.toLocaleString("ko-KR") : "");
    setEditingId(m.id); setTitleChips([]); setPrevBullets(null); setErr("");
    setPhotos(m.photos);
    pending.forEach((x) => URL.revokeObjectURL(x.url));
    setPending([]);
  }

  // ── 참석자 칩 ────────────────────────────────────────────────
  function addAttendee() {
    const nm = attendeeText.trim();
    if (!nm) return;
    // 쉼표로 여러 명을 한 번에 붙여 넣는 경우가 많습니다.
    const 이름들 = nm.split(",").map((x) => x.trim()).filter(Boolean);
    setV({ ...v, attendees: [...new Set([...v.attendees, ...이름들])] });
    setAttendeeText("");
  }

  // ── AI ───────────────────────────────────────────────────────
  async function 초안만들기() {
    if (!v.title.trim()) { setErr("회의명을 먼저 입력하세요."); return; }
    if (v.bullets.length > 0 && !prevBullets) {
      // 이미 내용이 있으면 한 번 물어봅니다.
      onModal("다시 생성하시겠습니까?", "지금 내용은 아래에 남겨 두고 견줄 수 있습니다.",
        () => void 실행하기(true));
      return;
    }
    void 실행하기(false);
  }

  async function 실행하기(비교: boolean) {
    setAiBusy(true); setErr("");
    try {
      const r = await meetingApi.draft(projectId, {
        title: v.title, memo: v.memo, place: v.place,
      });
      if (비교) setPrevBullets(v.bullets);
      setV((x) => ({ ...x, bullets: r.bullets }));
    } catch (e) {
      setErr(e instanceof ApiError && e.status === 503
        ? e.message
        : "AI 초안을 만들지 못했습니다.");
    } finally {
      setAiBusy(false);
    }
  }

  async function 제목제안() {
    if (!v.title.trim()) return;
    setAiBusy(true);
    try {
      setTitleChips((await meetingApi.titleSuggestions(projectId, v.title)).titles);
    } catch {
      setTitleChips([]);
    } finally {
      setAiBusy(false);
    }
  }

  // ── 사진 ─────────────────────────────────────────────────────
  async function 사진올리기(files: FileList | File[]) {
    setErr("");
    const 목록 = Array.from(files).filter((f) => f.type.startsWith("image/"));
    if (목록.length !== files.length) setErr("그림 파일만 붙일 수 있습니다.");

    if (!editingId) {
      // 아직 저장 전 — 들고만 있다가 저장할 때 함께 올립니다.
      setPending((x) => [...x, ...목록.map((f) => ({ file: f, url: URL.createObjectURL(f) }))]);
      return;
    }
    for (const f of 목록) {
      try {
        const ph = await meetingApi.uploadPhoto(projectId, editingId, f);
        setPhotos((x) => [...x, ph]);
      } catch (e) {
        setErr(e instanceof Error ? e.message : "사진을 올리지 못했습니다.");
      }
    }
    await load();
  }

  async function 사진지우기(ph: MeetingPhoto) {
    if (!editingId) return;
    await meetingApi.removePhoto(projectId, editingId, ph.id);
    setPhotos((x) => x.filter((y) => y.id !== ph.id));
    await load();
  }

  // ── 저장 ─────────────────────────────────────────────────────
  async function save() {
    if (busy) return;
    setBusy(true); setErr("");
    const body: MeetingIn = { ...v, amount: Number(onlyDigits(amountText)) || 0 };
    try {
      const saved = editingId
        ? await meetingApi.update(projectId, editingId, body)
        : await meetingApi.create(projectId, body);

      // 저장 전에 골라 둔 사진을 이제 붙입니다(회의록 번호가 생겼습니다).
      for (const x of pending) {
        try {
          await meetingApi.uploadPhoto(projectId, saved.id, x.file);
        } catch {
          setErr("일부 사진을 올리지 못했습니다. 수정에서 다시 붙여 주세요.");
        }
      }
      await load();
      reset();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "저장하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  function remove(m: Meeting) {
    onModal(`'${m.title}' 회의록을 지울까요?`, "되돌릴 수 없습니다.", () => {
      void (async () => {
        await meetingApi.remove(projectId, m.id);
        await load();
        if (editingId === m.id) reset();
      })();
    }, true);
  }

  /* 저장 단추는 회의내용이 있어야 눌립니다. 빈 회의록은 증빙이 되지 않습니다. */
  const 저장가능 = v.title.trim() !== "" && v.bullets.length > 0;

  // 파일 이름 미리보기 — 서버와 같은 규칙입니다.
  const 미리보기이름 = (() => {
    const d = (v.metOn || todayISO()).replaceAll("-", "").slice(2);
    const t = v.title.trim().replace(/[\\/:*?"<>|]/g, "") || "회의";
    const amt = Number(onlyDigits(amountText)) || 0;
    return amt > 0 ? `${d}_회의록_${t}_${amt.toLocaleString("ko-KR")}원.docx`
                   : `${d}_회의록_${t}.docx`;
  })();

  return (
    <section className="view on">
      <div className="mt-grid">
        {/* ── 작성 ── */}
        <div className="card">
          <h2>{editingId ? "회의록 수정" : "새 회의록"}
            {editingId && (
              <button type="button" className="mini-btn" style={{ marginLeft: "auto" }}
                      onClick={reset}>새로 작성</button>
            )}
          </h2>

          <div className="mt-form">
            <div className="f">
              <label htmlFor="mtTitle">회의명 *</label>
              <div className="mt-title-row">
                <input id="mtTitle" value={v.title} placeholder="예: 1차 콘텐츠 기획 회의"
                       onChange={(e) => setV({ ...v, title: e.target.value })} />
                <button type="button" className="mini-btn" disabled={aiBusy || !v.title.trim()}
                        onClick={() => void 제목제안()}>제목 다듬기</button>
              </div>
              {titleChips.length > 0 && (
                <div className="chips sug">
                  {titleChips.map((c) => (
                    <button key={c} type="button" className="chip pick"
                            onClick={() => { setV({ ...v, title: c }); setTitleChips([]); }}>
                      {c}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="f2">
              <div className="f">
                <label htmlFor="mtDate">일시 *</label>
                <input id="mtDate" type="date" value={v.metOn}
                       onChange={(e) => setV({ ...v, metOn: e.target.value })} />
              </div>
              <div className="f">
                <label htmlFor="mtPlace">장소</label>
                <input id="mtPlace" value={v.place} placeholder="예: 본관 3층 회의실"
                       onChange={(e) => setV({ ...v, place: e.target.value })} />
              </div>
            </div>

            <div className="f">
              <label htmlFor="mtAtt">참석자</label>
              <div className="mt-title-row">
                <input id="mtAtt" value={attendeeText} placeholder="이름을 적고 Enter (쉼표로 여러 명)"
                       onChange={(e) => setAttendeeText(e.target.value)}
                       onKeyDown={(e) => {
                         if (e.key === "Enter") { e.preventDefault(); addAttendee(); }
                       }}
                       onBlur={addAttendee} />
              </div>
              {v.attendees.length > 0 && (
                <div className="chips">
                  {v.attendees.map((nm) => (
                    <span key={nm} className="chip">
                      {nm}
                      <button type="button" aria-label={`${nm} 빼기`}
                              onClick={() => setV({ ...v, attendees: v.attendees.filter((x) => x !== nm) })}>
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="f">
              <label htmlFor="mtMemo">추가 메모 <span className="hint">AI 가 이 낱말을 녹여서 씁니다</span></label>
              <input id="mtMemo" value={v.memo} placeholder="예: 초등 저학년, 2학기 일정, 보건교사 협조"
                     onChange={(e) => setV({ ...v, memo: e.target.value })} />
            </div>

            <div className="f">
              <label htmlFor="mtAmt">금액 (원)</label>
              <input id="mtAmt" inputMode="numeric" value={amountText}
                     placeholder="없으면 비워 둡니다"
                     onChange={(e) => setAmountText(commas(onlyDigits(e.target.value)))} />
              {Number(onlyDigits(amountText)) > 0 && (
                <div className="hint">{fmtMoney(Number(onlyDigits(amountText)))}</div>
              )}
            </div>
          </div>

          {/* ── 회의내용 ── */}
          <div className="mt-bullets">
            <div className="mt-bullets-head">
              <b>회의내용</b>
              <span className="hint">{v.bullets.length}줄 · 눌러서 고칩니다</span>
              <button type="button" className="btn-ai" disabled={aiBusy || !v.title.trim()}
                      onClick={() => void 초안만들기()}>
                {aiBusy ? "만드는 중…" : "AI 생성"}
              </button>
            </div>

            {v.bullets.length === 0 && !aiBusy && (
              <div className="empty">회의명을 적고 [AI 생성] 을 누르거나, 아래에서 직접 적으세요.</div>
            )}

            {v.bullets.map((b, i) => (
              <div key={i} className="mt-bullet">
                <span className="dot" aria-hidden="true">•</span>
                <input value={b}
                       onChange={(e) => setV({
                         ...v, bullets: v.bullets.map((x, j) => (j === i ? e.target.value : x)),
                       })} />
                <button type="button" className="rm" aria-label="줄 지우기"
                        onClick={() => setV({ ...v, bullets: v.bullets.filter((_, j) => j !== i) })}>×</button>
              </div>
            ))}

            <button type="button" className="btn-add"
                    onClick={() => setV({ ...v, bullets: [...v.bullets, ""] })}>+ 줄 추가</button>

            {/* 다시 생성했을 때 앞의 결과를 옆에 둡니다 */}
            {prevBullets && (
              <div className="mt-prev">
                <div className="mt-prev-head">
                  <b>이전 내용</b>
                  <span className="hint">되돌리거나, 필요한 줄만 가져올 수 있습니다</span>
                  <button type="button" className="mini-btn"
                          onClick={() => { setV({ ...v, bullets: prevBullets }); setPrevBullets(null); }}>
                    되돌리기
                  </button>
                  <button type="button" className="mini-btn" onClick={() => setPrevBullets(null)}>닫기</button>
                </div>
                {prevBullets.map((b, i) => (
                  <div key={i} className="mt-prev-row">
                    <span>• {b}</span>
                    <button type="button" className="mini-btn"
                            onClick={() => setV({ ...v, bullets: [...v.bullets, b] })}>가져오기</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 사진 — 문서 뒤에 원본 비율 그대로 들어갑니다 */}
          <div className="mt-photos">
            <div className="mt-bullets-head">
              <b>회의 사진</b>
              <span className="hint">
                {photos.length + pending.length}장 · 문서 뒤에 붙습니다
                {pending.length > 0 && " (저장할 때 함께 올라갑니다)"}
              </span>
            </div>

            <div className={"mt-drop" + (dragOver ? " over" : "")}
                 onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                 onDragLeave={() => setDragOver(false)}
                 onDrop={(e) => {
                   e.preventDefault(); setDragOver(false);
                   if (e.dataTransfer.files.length) void 사진올리기(e.dataTransfer.files);
                 }}>
              <input id="mtPhoto" type="file" accept="image/*" multiple hidden
                     onChange={(e) => {
                       if (e.target.files?.length) void 사진올리기(e.target.files);
                       e.target.value = "";
                     }} />
              <label htmlFor="mtPhoto">여기에 끌어다 놓거나 눌러서 고릅니다</label>
            </div>

            {(photos.length > 0 || pending.length > 0) && (
              <div className="mt-thumbs">
                {photos.map((ph) => (
                  <div key={ph.id} className="mt-thumb">
                    <img src={ph.url} alt={ph.name} />
                    <button type="button" aria-label="사진 빼기"
                            onClick={() => void 사진지우기(ph)}>×</button>
                  </div>
                ))}
                {/* 아직 저장 전이라 서버에 없는 사진 — 테두리로 구분합니다 */}
                {pending.map((x, i) => (
                  <div key={`p${i}`} className="mt-thumb wait">
                    <img src={x.url} alt={x.file.name} />
                    <button type="button" aria-label="사진 빼기"
                            onClick={() => {
                              URL.revokeObjectURL(x.url);
                              setPending((y) => y.filter((_, j) => j !== i));
                            }}>×</button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mt-file">
            <span className="k">저장될 파일 이름</span>
            <span className="v">{미리보기이름}</span>
          </div>

          {err && <div className="err on">{err}</div>}

          <div className="mt-actions">
            <button type="button" className="btn-primary" disabled={!저장가능 || busy}
                    title={저장가능 ? "" : "회의명과 회의내용을 채워 주세요"}
                    onClick={() => void save()}>
              {/* 잠금 표시는 이모지 대신 선으로 그립니다. 다른 화면이 모두
                  이 방식이라 회의록만 이모지를 쓰면 튑니다. */}
              {!저장가능 && (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="4" y="11" width="16" height="10" rx="2" />
                  <path d="M8 11V7a4 4 0 018 0v4" />
                </svg>
              )}
              {editingId ? "수정 저장" : "회의록 저장"}
            </button>
            {editingId && (
              <button type="button" className="btn-ghost" onClick={reset}>취소</button>
            )}
          </div>
        </div>

        {/* ── 목록 ── */}
        <div className="card">
          <h2>회의록 <span className="hint">{list?.length ?? 0}건</span></h2>
          {list === null && <div className="empty">불러오는 중입니다.</div>}
          {list?.length === 0 && <div className="empty">아직 작성한 회의록이 없습니다.</div>}
          <div className="mt-list">
            {list?.map((m) => (
              <div key={m.id} className={"mt-item" + (editingId === m.id ? " on" : "")}>
                <div className="mt-item-top">
                  <b>{m.title}</b>
                  {m.amount > 0 && <span className="mt-amt">{fmtWon(m.amount)}원</span>}
                </div>
                <div className="mt-item-sub">
                  {dots(m.metOn)}{m.place ? ` · ${m.place}` : ""}
                  {m.attendees.length > 0 ? ` · 참석 ${m.attendees.length}명` : ""}
                  {` · 내용 ${m.bullets.length}줄`}
                </div>
                <div className="mt-item-acts">
                  <a className="mini-btn" href={meetingApi.docxUrl(projectId, m.id)}>문서 받기</a>
                  <button type="button" className="mini-btn" onClick={() => edit(m)}>수정</button>
                  <button type="button" className="mini-btn danger" onClick={() => remove(m)}>삭제</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
