# 诊断并创建 venv - 请用 PowerShell 运行: .\create_venv_check.ps1
$projectRoot = "C:\Users\huang\Desktop\MDP_imgrec"
$venvPath = Join-Path $projectRoot "MDP"

Write-Host "=== 1. 当前目录 ===" -ForegroundColor Cyan
Get-Location
Write-Host ""

Write-Host "=== 2. Python 命令位置 ===" -ForegroundColor Cyan
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    Write-Host "python: $($pythonCmd.Source)"
    & python --version
} else {
    Write-Host "未找到 python，尝试 py..."
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) { Write-Host "py: $($pyCmd.Source)"; & py --version }
}
Write-Host ""

Write-Host "=== 3. 创建虚拟环境（绝对路径）===" -ForegroundColor Cyan
Set-Location $projectRoot
if (Test-Path $venvPath) {
    Write-Host "MDP 已存在，跳过创建。路径: $venvPath"
} else {
    try {
        & python -m venv $venvPath 2>&1
        if ($LASTEXITCODE -ne 0) { Write-Host "退出码: $LASTEXITCODE" }
    } catch {
        Write-Host "python -m venv 报错，尝试 py -m venv..."
        & py -m venv $venvPath 2>&1
    }
}
Write-Host ""

Write-Host "=== 4. 检查结果 ===" -ForegroundColor Cyan
if (Test-Path (Join-Path $venvPath "Scripts\Activate.ps1")) {
    Write-Host "成功: MDP 已创建。激活: .\MDP\Scripts\Activate.ps1" -ForegroundColor Green
} elseif (Test-Path $venvPath) {
    Write-Host "MDP 文件夹存在但缺少 Scripts\Activate.ps1，可能创建不完整。" -ForegroundColor Yellow
    Get-ChildItem $venvPath -Recurse -Depth 1 | Format-Table Name, FullName -AutoSize
} else {
    Write-Host "失败: MDP 仍未创建。请检查上方是否有报错。" -ForegroundColor Red
}
