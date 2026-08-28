/* 알림 · 확인 팝업 — 프로토타입의 showModal() / askConfirm() 을 옮겼습니다.
   마크업(.scrim > .modal > .ic/.msg/.sub/.acts)도 원본 그대로입니다. */
import { useEffect, useRef } from "react";

export interface ModalState {
  msg: string;
  sub?: string;
  onOk?: () => void;      // 있으면 '취소' 버튼이 함께 나옵니다 (확인 팝업)
  okLabel?: string;
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
        <div className="ic" id="modalIc">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
        </div>
        <div className="msg" id="modalMsg">{state.msg}</div>
        <div className="sub" id="modalSub">{state.sub || ""}</div>
        <div className="acts">
          <button type="button" className="no" id="modalNo"
                  style={{ display: confirm ? "block" : "none" }}
                  onClick={onClose}>취소</button>
          <button type="button" className="ok" id="modalOk" ref={okRef}
                  onClick={() => { const fn = state.onOk; onClose(); fn?.(); }}>
            {state.okLabel || "확인"}
          </button>
        </div>
      </div>
    </div>
  );
}
