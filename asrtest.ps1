param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if ($CommandArgs.Count -gt 0 -and $CommandArgs[0] -eq "bind") {
    $Rest = @()
    if ($CommandArgs.Count -gt 1) {
        $Rest = $CommandArgs[1..($CommandArgs.Count - 1)]
    }
    & $Python "$PSScriptRoot\tools\hardware_bind.py" @Rest
    exit $LASTEXITCODE
}

& $Python "$PSScriptRoot\tools\auto_run_ext.py" @CommandArgs
exit $LASTEXITCODE
