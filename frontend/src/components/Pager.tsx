/* 쪽 나누기.

   공고가 수천 건이 되면 쪽 번호를 다 늘어놓을 수 없으므로,
   지금 쪽 주변만 보이고 나머지는 … 로 접습니다.
   버튼은 다른 곳과 같은 큰 글씨로, 누르는 영역을 넉넉히 잡습니다. */

interface Props {
  page: number;
  pages: number;
  onGo: (p: number) => void;
}

function windowed(page: number, pages: number): (number | "gap")[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  const around = new Set<number>([1, pages, page]);
  for (let d = 1; d <= 2; d++) {
    if (page - d > 1) around.add(page - d);
    if (page + d < pages) around.add(page + d);
  }
  const sorted = [...around].sort((a, b) => a - b);
  const out: (number | "gap")[] = [];
  let prev = 0;
  for (const n of sorted) {
    if (prev && n - prev > 1) out.push("gap");
    out.push(n);
    prev = n;
  }
  return out;
}

export default function Pager({ page, pages, onGo }: Props) {
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="쪽 이동">
      <button type="button" className="pg" disabled={page <= 1}
              onClick={() => onGo(page - 1)}>‹ 이전</button>
      {windowed(page, pages).map((n, i) =>
        n === "gap"
          ? <span key={`g${i}`} className="gap">…</span>
          : <button key={n} type="button" className={"pg" + (n === page ? " on" : "")}
                    aria-current={n === page ? "page" : undefined}
                    onClick={() => onGo(n)}>{n}</button>
      )}
      <button type="button" className="pg" disabled={page >= pages}
              onClick={() => onGo(page + 1)}>다음 ›</button>
    </nav>
  );
}
