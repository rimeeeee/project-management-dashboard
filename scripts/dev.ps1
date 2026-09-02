# 개발용 — 백엔드(8000)와 프론트엔드(5173)를 함께 띄웁니다. (Windows / PowerShell)
# 화면은 http://localhost:5173 에서 봅니다.
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
#
# macOS·Linux 는 scripts/dev.sh 를 쓰세요. 하는 일은 같습니다.

$ErrorActionPreference = "Stop"
# 이 스크립트가 찍는 한글이 콘솔(cp949)에서 깨지지 않게 합니다.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env 파일이 없어 .env.example 을 복사해 만들었습니다."
}

$py = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host ".venv 가 없습니다. docs/개발.md 의 '개발 환경 준비' 를 먼저 해 주세요."
    exit 1
}

# 콘솔 기본이 cp949 라 이걸 켜지 않으면 한글 로그에서 서버가 멈춥니다.
$env:PYTHONUTF8 = "1"

$back = Start-Process -FilePath $py `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory (Join-Path $PWD "backend") -NoNewWindow -PassThru
$front = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" `
    -WorkingDirectory (Join-Path $PWD "frontend") -NoNewWindow -PassThru

Write-Host ""
Write-Host "백엔드 http://localhost:8000  ·  화면 http://localhost:5173"
Write-Host "멈추려면 Ctrl+C 를 누르세요."
Write-Host ""

try {
    Wait-Process -Id $back.Id, $front.Id
}
finally {
    # npm 은 node 를 자식으로 띄우므로 /T 로 자식까지 함께 정리합니다.
    foreach ($p in $back, $front) {
        if ($p -and -not $p.HasExited) {
            & taskkill /PID $p.Id /T /F 2>$null | Out-Null
        }
    }
}
