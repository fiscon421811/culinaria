# Grava o token do Turso no arquivo .env do app Python, testando antes.
# Uso (PowerShell, dentro da pasta python-app):  .\configurar_token.ps1
$base    = "https://receitas-recuperado-fiscon.aws-us-east-2.turso.io"
$envFile = Join-Path $PSScriptRoot ".env"

if ($env:TURSO_AUTH_TOKEN) {
    Write-Host "Aviso: existe a variavel de ambiente TURSO_AUTH_TOKEN no Windows. O app usa o .env no lugar dela."
}

$sec = Read-Host "Cole o token do banco receitas-recuperado (nao aparece na tela)" -AsSecureString
$tok = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$tok = $tok.Trim().Trim('"')

if ($tok.Length -lt 100 -or -not $tok.StartsWith("eyJ")) {
    Write-Host "Isso nao parece um token do Turso (deve comecar com eyJ e ser longo). Nada foi gravado."
    exit 1
}

$body = '{"requests":[{"type":"execute","stmt":{"sql":"SELECT COUNT(*) FROM receitas"}},{"type":"close"}]}'
try {
    $r = Invoke-RestMethod -Method Post -Uri "$base/v2/pipeline" -Headers @{ Authorization = "Bearer $tok" } -ContentType "application/json" -Body $body
    $n = $r.results[0].response.result.rows[0][0].value
} catch {
    Write-Host "O Turso recusou este token: $($_.Exception.Message)"
    Write-Host "Gere um token Read & Write do banco receitas-recuperado e tente de novo. Nada foi gravado."
    exit 1
}

$linhas = @()
if (Test-Path $envFile) { $linhas = @(Get-Content $envFile | Where-Object { $_ -notmatch '^\s*TURSO_AUTH_TOKEN=' }) }
$linhas += "TURSO_AUTH_TOKEN=$tok"
[IO.File]::WriteAllLines($envFile, $linhas, (New-Object Text.UTF8Encoding $false))

Write-Host "Token OK. O banco tem $n receitas. Salvo em $envFile"
