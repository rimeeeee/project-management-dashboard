import { useCallback, useEffect, useState } from "react";
import { api } from "./lib/api";
import Login from "./pages/Login";
import Shell from "./pages/Shell";

type Status = "checking" | "out" | "in";

export default function App() {
  const [status, setStatus] = useState<Status>("checking");
  const [usingDefaultPassword, setUsingDefaultPassword] = useState(false);

  // 새로고침해도 쿠키가 살아 있으면 다시 로그인하지 않아도 됩니다.
  useEffect(() => {
    let alive = true;
    api
      .session()
      .then((info) => {
        if (!alive) return;
        setUsingDefaultPassword(info.using_default_password);
        setStatus(info.authenticated ? "in" : "out");
      })
      .catch(() => alive && setStatus("out"));
    return () => {
      alive = false;
    };
  }, []);

  const onSuccess = useCallback((dev: boolean) => {
    setUsingDefaultPassword(dev);
    setStatus("in");
  }, []);

  const onLogout = useCallback(() => setStatus("out"), []);

  // 세션을 확인하는 아주 짧은 순간입니다.
  // 여기서 로그인 화면을 먼저 그리면, 이미 로그인한 사람에게도 로그인 화면이
  // 한 번 번쩍이고 사라집니다. 그래서 아무것도 그리지 않고 기다립니다.
  if (status === "checking") return <div style={{ minHeight: "100vh" }} />;

  return status === "in" ? (
    <Shell usingDefaultPassword={usingDefaultPassword} onLogout={onLogout} />
  ) : (
    <Login onSuccess={onSuccess} />
  );
}
