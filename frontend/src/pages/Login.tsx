import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import { currentTheme, themeButtonLabel, toggleTheme, type Theme } from "../lib/theme";
import "../styles/login.css";

interface Props {
  onSuccess: (usingDefaultPassword: boolean) => void;
}

export default function Login({ onSuccess }: Props) {
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => currentTheme());
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;

    if (!password) {
      setError("비밀번호를 입력해 주세요.");
      inputRef.current?.focus();
      return;
    }

    setBusy(true);
    setError("");
    try {
      const info = await api.login(password, remember);
      onSuccess(info.using_default_password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인하지 못했습니다.");
      setPassword("");
      inputRef.current?.focus();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-box">
        <div className="login-title">사업관리 대시보드</div>
        <div className="login-sub">디지털전략팀</div>

        <form className="card" onSubmit={submit} autoComplete="on">
          <div className="f">
            <label htmlFor="pw">비밀번호</label>
            <input
              id="pw"
              ref={inputRef}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              spellCheck={false}
            />
          </div>

          <label className="login-remember">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            이 브라우저에서 로그인 유지
          </label>

          <div className={"form-err" + (error ? " on" : "")} role="alert">
            {error}
          </div>

          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "확인 중…" : "들어가기"}
          </button>
        </form>

        <div className="login-foot">
          <button
            type="button"
            onClick={() => setTheme(toggleTheme())}
          >
            {themeButtonLabel(theme)}
          </button>
        </div>
      </div>
    </div>
  );
}
