# Script para iniciar o aplicativo Estoque Exonvais
# Ativa o ambiente virtual e executa o Streamlit

Write-Host "🧵 Iniciando Estoque Exonvais..." -ForegroundColor Cyan

# Verifica se o ambiente virtual existe
if (-Not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "❌ Ambiente virtual não encontrado!" -ForegroundColor Red
    Write-Host "Criando ambiente virtual..." -ForegroundColor Yellow
    python -m venv .venv
    
    Write-Host "Instalando dependências..." -ForegroundColor Yellow
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

# Executa o aplicativo Streamlit
Write-Host "✅ Iniciando aplicativo..." -ForegroundColor Green
Write-Host ""
.\.venv\Scripts\python.exe -m streamlit run app.py
