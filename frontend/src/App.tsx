import { useCallback, useEffect, useState } from "react";
import { api } from "./lib/api";
import Login from "./pages/Login";
import Shell from "./pages/Shell";

type Status = "checking" | "out" | "in";

export default function App() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let alive = true;

    /* 주소 뒤에 ?logout 을 붙이면 로그인 화면으로 돌아갑니다.

       화면에 로그아웃 버튼을 두지 않기로 했는데, 한 번 로그인하면 쿠키가
       12시간(‘로그인 유지’ 를 켰으면 30일) 남아 있어서 로그인 화면을 다시
       보려면 방법이 없습니다. 로그인 화면을 확인해야 할 때,
       그리고 여럿이 쓰는 PC 에서 자리를 뜰 때 쓰라고 남겨 둡니다.

         http://localhost:5173/?logout

       끝나면 주소에서 ?logout 을 지웁니다. 그대로 두면 새로고침할 때마다
       로그인이 풀려서 쓸 수가 없습니다. */
    const wantsLogout = new URLSearchParams(window.location.search).has("logout");
    if (wantsLogout) {
      api.logout().finally(() => {
        window.history.replaceState({}, "", window.location.pathname);
        if (alive) setStatus("out");
      });
      return () => {
        alive = false;
      };
    }

    // 새로고침해도 쿠키가 살아 있으면 다시 로그인하지 않아도 됩니다.
    api
      .session()
      .then((info) => {
        if (!alive) return;
        setStatus(info.authenticated ? "in" : "out");
      })
      .catch(() => alive && setStatus("out"));
    return () => {
      alive = false;
    };
  }, []);

  const onSuccess = useCallback(() => setStatus("in"), []);

  // 세션을 확인하는 아주 짧은 순간입니다.
  // 여기서 로그인 화면을 먼저 그리면, 이미 로그인한 사람에게도 로그인 화면이
  // 한 번 번쩍이고 사라집니다. 그래서 아무것도 그리지 않고 기다립니다.
  if (status === "checking") return <div style={{ minHeight: "100vh" }} />;

  return status === "in" ? <Shell /> : <Login onSuccess={onSuccess} />;
}
