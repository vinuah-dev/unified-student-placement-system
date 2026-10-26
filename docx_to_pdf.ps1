# Converts a .docx to .pdf using Microsoft Word.  Usage: docx_to_pdf.ps1 <input.docx> <output.pdf>
param([string]$InputPath, [string]$OutputPath)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open((Resolve-Path $InputPath).Path, $false, $true)
    $doc.ExportAsFixedFormat($OutputPath, 17)
    $doc.Close($false)
} finally {
    $word.Quit()
}
Write-Output "PDF written: $OutputPath"
