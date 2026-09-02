# 서버에 올릴 준비를 합니다. (Windows / PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File scripts\release.ps1
#
# 하는 일
#   1. 백엔드 테스트
#   2. 디자인 시안 대조
#   3. 화면 빌드 (frontend/dist)
#   4. 바뀐 화면을 커밋 대상에 올려 둠
#
# 화면 빌드를 깜빡하고 커밋하면 서버는 새 코드에 옛날 화면을 쓰게 됩니다.
# 그 일이 없도록 한 번에 묶어 둔 것입니다.

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Join-Path $PSScriptRoot "..")

$py = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host ".venv 가 없습니다. docs/개발.md 의 '개발 환경 준비' 를 먼저 해 주세요."
    exit 1
}

$env:PYTHONUTF8 = "1"

Write-Host ""
Write-Host "[1/4] 백엔드 테스트"
Push-Location backend
& $py -m pytest -q
$ok = $LASTEXITCODE
Pop-Location
if ($ok -ne 0) { Write-Host "`n테스트가 실패했습니다. 고친 뒤 다시 돌려 주세요."; exit 1 }

Write-Host ""
Write-Host "[2/4] 디자인 시안 대조"
& $py scripts\verify\run.py
if ($LASTEXITCODE -ne 0) { Write-Host "`n시안 대조가 실패했습니다. 계산 규칙을 확인해 주세요."; exit 1 }

Write-Host ""
Write-Host "[3/4] 화면 빌드"
Push-Location frontend
# 항상 비운 자리에 새로 만듭니다. 두 가지 이유가 있습니다.
#   · dist 가 남아 있으면 이 환경에서 vite 가 그 폴더를 비우다 죽습니다
#     (Node 24 + Vite 5 조합, 종료코드 0xC0000409)
#   · dist 를 git 에 넣으므로, 지난 빌드 찌꺼기가 남으면 그대로 서버까지 갑니다
if (Test-Path "node_modules\.vite") { Remove-Item -Recurse -Force "node_modules\.vite" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
& npm.cmd run build
$ok = $LASTEXITCODE
Pop-Location
if ($ok -ne 0) { Write-Host "`n화면 빌드가 실패했습니다."; exit 1 }

Write-Host ""
Write-Host "[4/4] 바뀐 화면을 커밋 대상에 올립니다"
& git add frontend/dist

Write-Host ""
Write-Host "준비가 끝났습니다. 이제 커밋하고 올리세요."
Write-Host ""
Write-Host "    git add -A"
Write-Host "    git commit -m ""무엇을 고쳤는지"""
Write-Host "    git push"
Write-Host ""
Write-Host "서버에서는 git pull 후 서비스만 다시 시작하면 됩니다."
Write-Host "(표 구조를 바꿨다면 서버에서 alembic upgrade head 도 함께)"
Write-Host ""
