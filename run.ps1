$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$retailPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $retailPython)) {
    $retailPython = (Get-Command python).Source
}
& $retailPython -c "import streamlit, pandas, openpyxl, pyarrow"
if ($LASTEXITCODE -ne 0) {
    throw 'Install the dependencies first: python -m pip install -r requirements.txt'
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'data\processed\retail.sqlite'))) {
    & $retailPython -m retail_ops.pipeline
    if ($LASTEXITCODE -ne 0) { throw 'Data build failed. Read the error above.' }
}
& $retailPython -m streamlit run app.py
