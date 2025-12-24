param(
    [string]$AppUrl = "https://enxovaisapp.streamlit.app/"
)

$pages = @(
    "",
    "?page=Administra%C3%A7%C3%A3o",
    "?page=Relat%C3%B3rios",
    "?page=02_Produtos_Comuns",
    "?page=10_Administra%C3%A7%C3%A3o"
)

Write-Host "Smoke test para: $AppUrl" -ForegroundColor Cyan
foreach ($p in $pages) {
    $suffix = $p
n    if ($suffix -ne "") { $url = "$AppUrl`$suffix" } else { $url = $AppUrl }
    Write-Host "\n--- Testando: $url" -ForegroundColor Yellow
    try {
        # Disable automatic redirect to detect auth redirects
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -MaximumRedirection 0 -ErrorAction Stop
        Write-Host "StatusCode: $($resp.StatusCode)" -ForegroundColor Green
        $len = ($resp.RawContent).Length
        Write-Host "Conteúdo (bytes): $len"
    }
    catch [System.Net.WebException] {
        $ex = $_.Exception
        if ($ex.Response -ne $null) {
            $status = $ex.Response.StatusCode.value__
            Write-Host "HTTP status: $status" -ForegroundColor Magenta
            $loc = $ex.Response.Headers['Location']
            if ($loc) { Write-Host "Location: $loc" -ForegroundColor Cyan }
        } else {
            Write-Host "Erro de rede: $($ex.Message)" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "\nTeste finalizado. Se aparecer redirect para share.streamlit.io, abra a app no navegador para autenticar." -ForegroundColor Cyan
