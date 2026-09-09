import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repository = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(repository, "frontend", "dist");
const source = join(dist, "index.html");
const output = join(repository, "docs", "사업관리_대시보드_현재.html");

let html = readFileSync(source, "utf8");

const cssMatch = html.match(/<link rel="stylesheet"[^>]+href="\/assets\/([^"]+\.css)"[^>]*>/);
const jsMatch = html.match(/<script type="module"[^>]+src="\/assets\/([^"]+\.js)"[^>]*><\/script>/);

if (!cssMatch || !jsMatch) {
  throw new Error("frontend/dist/index.html에서 빌드된 CSS 또는 JavaScript를 찾지 못했습니다.");
}

const css = readFileSync(join(dist, "assets", cssMatch[1]), "utf8");
const js = readFileSync(join(dist, "assets", jsMatch[1]), "utf8")
  .replace(/<\/script/gi, "<\\/script");

html = html
  // 함수 치환을 써야 번들 안의 `$&`, `$1` 같은 문자열이 replace 치환식으로
  // 해석되지 않고 JavaScript 원문 그대로 들어갑니다.
  .replace(cssMatch[0], () => `<style>\n${css}\n</style>`)
  .replace(jsMatch[0], () => `<script type="module">\n${js}\n</script>`)
  .replace(
    "<body>",
    "<!-- 현재 React 프런트엔드의 단일 HTML 내보내기입니다. 실제 데이터는 같은 서버의 /api를 사용합니다. -->\n<body>",
  );

if (!html.includes(css) || !html.includes(js) || /<(?:script|link)[^>]+(?:src|href)="\/assets\//.test(html)) {
  throw new Error("빌드 자산을 단일 HTML에 정상적으로 포함하지 못했습니다.");
}

writeFileSync(output, html, "utf8");
console.log(output);
