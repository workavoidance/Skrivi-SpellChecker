$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesisStream, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$speaker = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::new()
$stream = $null
try {
    $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $voices = @([Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.Language -match '^(nb|nn|no)(-|$)' })
    if ($request.action -eq 'voices') {
        $names = @($voices | ForEach-Object { @{ name = $_.DisplayName; language = $_.Language } })
        @{ voices = $names; local = $true } | ConvertTo-Json -Depth 4 -Compress
        exit 0
    }
    if ($voices.Count -eq 0) { throw 'No local Norwegian voice is installed.' }
    $textToSpeak = [string]$request.text
    if ($textToSpeak.Length -eq 0 -or $textToSpeak.Length -gt 800) { throw 'Invalid speech text length.' }
    $speaker.Voice = $voices[0]
    $speaker.Options.SpeakingRate = 0.9
    $stream = [System.IO.MemoryStream]::new()
    # Plain text only. Input is data, never SSML or PowerShell code.
    $operation = $speaker.SynthesizeTextToStreamAsync($textToSpeak)
    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    $task = $asTask.MakeGenericMethod([Windows.Media.SpeechSynthesis.SpeechSynthesisStream]).Invoke($null, @($operation))
    $task.Wait()
    $speechStream = $task.Result
    $reader = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($speechStream)
    try { $reader.CopyTo($stream) } finally { $reader.Dispose(); $speechStream.Dispose() }
    @{ audio = [Convert]::ToBase64String($stream.ToArray()); voice = $voices[0].DisplayName; local = $true } | ConvertTo-Json -Compress
} finally {
    if ($null -ne $stream) { $stream.Dispose() }
    $speaker.Dispose()
}
