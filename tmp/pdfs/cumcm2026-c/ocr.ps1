Add-Type -AssemblyName System.Runtime.WindowsRuntime

function Await-WinRT($Operation, $ResultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and
            $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1
        } |
        Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    $task.Result
}

[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap,Windows.Graphics.Imaging,ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime] | Out-Null

$language = [Windows.Globalization.Language]::new('zh-Hans-CN')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if (-not $engine) { throw 'Chinese Windows OCR is unavailable.' }

Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'page-*.png' |
    Sort-Object Name |
    ForEach-Object {
        $storage = Await-WinRT `
            ([Windows.Storage.StorageFile]::GetFileFromPathAsync($_.FullName)) `
            ([Windows.Storage.StorageFile])
        $stream = Await-WinRT `
            ($storage.OpenAsync([Windows.Storage.FileAccessMode]::Read)) `
            ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await-WinRT `
            ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) `
            ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await-WinRT `
            ($decoder.GetSoftwareBitmapAsync()) `
            ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result = Await-WinRT `
            ($engine.RecognizeAsync($bitmap)) `
            ([Windows.Media.Ocr.OcrResult])
        Write-Output "--- $($_.Name) ---"
        Write-Output $result.Text
    }
