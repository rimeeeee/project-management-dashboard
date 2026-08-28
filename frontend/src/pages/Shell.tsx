/* 로그인 뒤에 나오는 화면.
   3단계에서 프로토타입의 전체 화면(메인·대시보드·달력·공고)을 여기에 옮깁니다.
   지금은 1단계라 로그인이 실제로 지켜지는지 확인할 수 있는 만큼만 있습니다. */
import { useState } from "react";
import { api } from "../lib/api";
import { currentTheme, themeButtonLabel, toggleTheme, type Theme } from "../lib/theme";

interface Props {
  usingDefaultPassword: boolean;
  onLogout: () => void;
}

export default function Shell({ usingDefaultPassword, onLogout }: Props) {
  const [theme, setTheme] = useState<Theme>(() => currentTheme());

  async function logout() {
    try {
      await api.logout();
    } finally {
      onLogout();
    }
  }

  return (
    <div style={{ padding: "32px 28px", maxWidth: 820, margin: "0 auto" }}>
      <div className="page-title">사업관리 대시보드</div>

      {usingDefaultPassword && (
        <div className="login-notice" style={{ marginBottom: 18 }}>
          지금은 개발용 기본 비밀번호로 동작하고 있습니다. 실제로 쓰기 전에{" "}
          <code>.venv/bin/python scripts/set_password.py</code> 로 비밀번호를 정해 주세요.
        </div>
      )}

      <div className="card">
        <h2>1단계 확인</h2>
        <p style={{ color: "var(--ink-2)" }}>
          비밀번호 게이트를 통과했습니다. 이 화면은 로그인한 사람만 볼 수 있습니다.
        </p>
        <p style={{ color: "var(--muted)", fontSize: "14.4px", marginTop: 10 }}>
          2단계에서 데이터베이스와 시드 데이터를, 3단계에서 프로토타입 화면을 이 자리에 옮깁니다.
        </p>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 18 }}>
        <button type="button" className="btn-ghost" onClick={() => setTheme(toggleTheme())}>
          {themeButtonLabel(theme)}
        </button>
        <button type="button" className="btn-ghost" onClick={logout}>
          로그아웃
        </button>
      </div>
    </div>
  );
}
