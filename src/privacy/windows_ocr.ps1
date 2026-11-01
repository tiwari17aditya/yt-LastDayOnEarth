param(
    [string]$FileList = "",
    [string]$OutputFile = ""
)

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
Function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language,Windows.Foundation.UniversalApiContract,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation.UniversalApiContract,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap,Windows.Foundation.UniversalApiContract,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine,Windows.Foundation.UniversalApiContract,ContentType=WindowsRuntime] | Out-Null

$lang = New-Object Windows.Globalization.Language('en-US')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)

$allPaths = @()
if ($FileList -and (Test-Path $FileList)) {
    $allPaths = Get-Content $FileList
}

$results = [ordered]@{}

foreach ($p in $allPaths) {
    $p = $p.Trim()
    if ($p -and (Test-Path $p)) {
        try {
            $targetPath = (Resolve-Path $p).Path
            $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($targetPath)) ([Windows.Storage.StorageFile])
            $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
            $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
            $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
            $ocrResult = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $cleanText = ($ocrResult.Text -replace "[\x00-\x1F\x7F]", " ").Trim()
            $results[$targetPath] = $cleanText
        } catch {
            $results[$p] = ""
        }
    }
}

if ($OutputFile) {
    $results | ConvertTo-Json -Depth 3 | Set-Content -Path $OutputFile -Encoding UTF8
    Write-Output "SAVED_TO_FILE"
} else {
    $results | ConvertTo-Json -Depth 3
}
