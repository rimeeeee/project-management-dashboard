/* 알림 · 확인 팝업 — 프로토타입의 showModal() / askConfirm() 을 옮겼습니다.
   마크업(.scrim > .modal > .ic/.msg/.sub/.acts)도 원본 그대로입니다. */
import { useEffect, useRef } from "react";

export interface ModalState {
  msg: string;
  sub?: string;
  onOk?: () => void;      // 있으면 '취소' 버튼이 함께 나옵니다 (확인 팝업)
  okLabel?: string;
  /* 삭제처럼 되돌리기 어려운 동작의 확인창.
     초록 체크 대신 경고 아이콘, 실행 버튼은 빨강 + '삭제' 글자가 됩니다. */
  danger?: boolean;
}

interface Props {
  state: ModalState | null;
  onClose: () => void;
}

export default function Modal({ state, onClose }: Props) {
  const okRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (state) okRef.current?.focus();
  }, [state]);

  useEffect(() => {
    if (!state) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, [state, onClose]);

  if (!state) return null;

  const confirm = !!state.onOk;

  return (
    <div className="scrim on" id="scrim" role="dialog" aria-modal="true" aria-labelledby="modalMsg">
      <div className="modal">
        <div className={"ic" + (state.danger ? " danger" : "")} id="modalIc">
          {state.danger ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.3 3.9L2.6 17a2 2 0 001.7 3h15.4a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/>
              <path d="M12 9v4M12 17h.01"/>
            </svg>
          ) : (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
          )}
        </div>
        <div className="msg" id="modalMsg">{state.msg}</div>
        <div className="sub" id="modalSub">{state.sub || ""}</div>
        <div className="acts">
          <button type="button" className="no" id="modalNo"
                  style={{ display: confirm ? "block" : "none" }}
                  onClick={onClose}>취소</button>
          <button type="button" className={"ok" + (state.danger ? " danger" : "")} id="modalOk" ref={okRef}
                  onClick={() => { const fn = state.onOk; onClose(); fn?.(); }}>
            {state.okLabel || (state.danger && confirm ? "삭제" : "확인")}
          </button>
        </div>
      </div>
    </div>
  );
}
