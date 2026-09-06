param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $Python "$PSScriptRoot\tools\auto_run.py" @CommandArgs
exit $LASTEXITCODE
