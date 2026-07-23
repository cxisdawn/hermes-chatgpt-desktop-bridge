param(
    [Parameter(Mandatory = $true)]
    [string]$InputFile,

    [int]$TimeoutSeconds = 600,

    [string]$ProjectTitle = "",

    [string]$ChatTitle = "",

    [switch]$NoFocusFallback
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName System.Windows.Forms

# Keep this source file ASCII-only for Windows PowerShell 5.1. Localized UI
# labels are decoded at runtime so the script does not depend on a code page.
function ConvertFrom-Utf8Base64 {
    param([string]$Value)

    return [System.Text.Encoding]::UTF8.GetString(
        [Convert]::FromBase64String($Value)
    )
}

$CopyLabels = @(
    "Copy",
    (ConvertFrom-Utf8Base64 "5aSN5Yi2")
)
$ComposerLabels = @(
    "Message ChatGPT",
    (ConvertFrom-Utf8Base64 "57uZIENoYXRHUFQg5Y+R5raI5oGv")
)
$StopLabels = @(
    "Stop",
    "Stop generating",
    "Stop response",
    "Stop streaming",
    (ConvertFrom-Utf8Base64 "5YGc5q2i"),
    (ConvertFrom-Utf8Base64 "5YGc5q2i55Sf5oiQ")
)
$StopLabelZhPrefix = ConvertFrom-Utf8Base64 "5YGc5q2i"
$SendLabels = @(
    "Send",
    "Send prompt",
    "Send message",
    (ConvertFrom-Utf8Base64 "5Y+R6YCB"),
    (ConvertFrom-Utf8Base64 "5Y+R6YCB5raI5oGv"),
    (ConvertFrom-Utf8Base64 "5Y+R6YCB5o+Q56S6")
)

if (-not ("HermesCgNative" -as [type])) {
    Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class HermesCgNative {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
}

function Get-AllElements {
    param([System.Windows.Automation.AutomationElement]$Root)

    return $Root.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition
    )
}

function Normalize-BridgeText {
    param([AllowNull()][string]$Text)

    if ($null -eq $Text) {
        return $null
    }
    return $Text.Replace("`r`n", "`n").Replace("`r", "`n")
}

function Normalize-ComposerPayload {
    param([AllowNull()][string]$Text)

    $normalized = Normalize-BridgeText $Text
    if ($null -eq $normalized) {
        return $null
    }

    # Chromium TextPattern adds a terminal LF to the content-editable Group.
    # Ignore only terminal line feeds for transport verification. Internal
    # whitespace and all other characters must still match exactly.
    return $normalized.TrimEnd([char[]]@([char]10))
}

function Get-ComposerVerificationKey {
    param([AllowNull()][string]$Text)

    $payload = Normalize-ComposerPayload $Text
    if ($null -eq $payload) {
        return $null
    }

    # Chromium TextPattern may collapse consecutive paragraph line feeds.
    # Compare every non-line-break character exactly while ignoring only the
    # accessibility layer's CR/LF representation.
    return $payload.Replace("`n", "")
}

function Get-ControlText {
    param([System.Windows.Automation.AutomationElement]$Element)

    try {
        $pattern = $Element.GetCurrentPattern(
            [System.Windows.Automation.ValuePattern]::Pattern
        )
        return [string]$pattern.Current.Value
    } catch {
        # Some Chromium content-editable controls expose TextPattern instead.
    }

    try {
        $pattern = $Element.GetCurrentPattern(
            [System.Windows.Automation.TextPattern]::Pattern
        )
        return [string]$pattern.DocumentRange.GetText(-1)
    } catch {
        return $null
    }
}

function Get-ComposerText {
    param([System.Windows.Automation.AutomationElement]$Composer)

    $text = Get-ControlText $Composer
    if ($null -eq $text) {
        return $null
    }

    # Chromium's Group/TextPattern appends a newline to the empty composer
    # placeholder. Compare a trimmed copy only for placeholder detection;
    # return the original text for every real draft.
    $placeholderCandidate = (Normalize-BridgeText $text).Trim()
    if ($placeholderCandidate -in $ComposerLabels) {
        return ""
    }
    return $text
}

function Get-CopyButtons {
    param($Elements)

    $result = @()
    foreach ($element in $Elements) {
        try {
            if (
                $element.Current.ControlType.ProgrammaticName -eq "ControlType.Button" -and
                $element.Current.Name -in $CopyLabels
            ) {
                $result += $element
            }
        } catch {
            # Chromium can invalidate controls while rebuilding the page.
        }
    }
    return @($result)
}

function Get-BottomCopyButton {
    param($Elements)

    $visible = @()
    foreach ($button in @(Get-CopyButtons -Elements $Elements)) {
        try {
            $rect = $button.Current.BoundingRectangle
            if (
                -not $button.Current.IsOffscreen -and
                $rect.Width -gt 0 -and
                $rect.Height -gt 0
            ) {
                $visible += $button
            }
        } catch {
            # Ignore controls invalidated while ChatGPT updates the page.
        }
    }

    return $visible |
        Sort-Object { $_.Current.BoundingRectangle.Top } -Descending |
        Select-Object -First 1
}

function Read-CopyButtonText {
    param([System.Windows.Automation.AutomationElement]$Button)

    if (-not $Button) {
        return $null
    }

    $sentinel = "HERMES_CG_WAITING_FOR_COPY"
    [System.Windows.Forms.Clipboard]::SetText($sentinel)
    $invoke = $Button.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
    )
    $invoke.Invoke()

    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 100
        try {
            if ([System.Windows.Forms.Clipboard]::ContainsText()) {
                $candidate = [System.Windows.Forms.Clipboard]::GetText()
                if ($candidate -and $candidate -ne $sentinel) {
                    return $candidate
                }
            }
        } catch {
            # Clipboard can be briefly locked by the desktop app.
        }
    }
    return $null
}

function Test-GenerationActive {
    param($Elements)

    foreach ($element in $Elements) {
        try {
            $name = $element.Current.Name
            $isStopControl = (
                $name -in $StopLabels -or
                $name -match "^(?i:Stop\b)" -or
                $name.StartsWith($StopLabelZhPrefix)
            )
            if (
                $element.Current.ControlType.ProgrammaticName -eq "ControlType.Button" -and
                $isStopControl -and
                $element.Current.IsEnabled
            ) {
                return $true
            }
        } catch {
            # Ignore controls invalidated while streaming.
        }
    }
    return $false
}

function Get-SendButton {
    param($Elements)

    $matches = @()
    foreach ($element in $Elements) {
        try {
            if (
                $element.Current.ControlType.ProgrammaticName -eq "ControlType.Button" -and
                $element.Current.Name -in $SendLabels -and
                $element.Current.IsEnabled -and
                -not $element.Current.IsOffscreen
            ) {
                $matches += $element
            }
        } catch {
            # Ignore controls invalidated while the composer changes.
        }
    }

    return $matches |
        Sort-Object { $_.Current.BoundingRectangle.Top } -Descending |
        Select-Object -First 1
}

function Set-WindowAndComposerFocus {
    param(
        [System.Diagnostics.Process]$Process,
        [System.Windows.Automation.AutomationElement]$Composer
    )

    [HermesCgNative]::ShowWindow($Process.MainWindowHandle, 9) | Out-Null
    for ($i = 0; $i -lt 20; $i++) {
        [HermesCgNative]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
        try {
            $Composer.SetFocus()
        } catch {
            return $false
        }
        Start-Sleep -Milliseconds 100
        try {
            if (
                [HermesCgNative]::GetForegroundWindow() -eq $Process.MainWindowHandle -and
                $Composer.Current.HasKeyboardFocus
            ) {
                return $true
            }
        } catch {
            return $false
        }
    }
    return $false
}

function Set-ComposerText {
    param(
        [System.Diagnostics.Process]$Process,
        [System.Windows.Automation.AutomationElement]$Composer,
        [string]$Text,
        [switch]$AllowForegroundFallback
    )

    $expected = Get-ComposerVerificationKey $Text
    try {
        $valuePattern = $Composer.GetCurrentPattern(
            [System.Windows.Automation.ValuePattern]::Pattern
        )
        if (-not $valuePattern.Current.IsReadOnly) {
            $valuePattern.SetValue($Text)
            Start-Sleep -Milliseconds 400
            $actual = Get-ComposerVerificationKey (Get-ComposerText $Composer)
            if ($actual -ceq $expected) {
                return "ValuePattern"
            }
        }
    } catch {
        # Try another background-capable accessibility pattern below.
    }

    try {
        $legacyPattern = $Composer.GetCurrentPattern(
            [System.Windows.Automation.LegacyIAccessiblePattern]::Pattern
        )
        $legacyPattern.SetValue($Text)
        Start-Sleep -Milliseconds 400
        $actual = Get-ComposerVerificationKey (Get-ComposerText $Composer)
        if ($actual -ceq $expected) {
            return "LegacyIAccessiblePattern"
        }
    } catch {
        # Some Chromium builds expose only read-only TextPattern.
    }

    if (-not $AllowForegroundFallback) {
        throw "Background composer input is unavailable in this ChatGPT build; --no-focus refused to activate the app"
    }

    if (-not (Set-WindowAndComposerFocus -Process $Process -Composer $Composer)) {
        throw "Cannot focus the ChatGPT composer; no keyboard input was sent"
    }

    [System.Windows.Forms.Clipboard]::SetText($Text)
    [System.Windows.Forms.SendKeys]::SendWait("^a")
    Start-Sleep -Milliseconds 100
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Start-Sleep -Milliseconds 500

    $actual = Get-ComposerVerificationKey (Get-ComposerText $Composer)
    if ($actual -cne $expected) {
        $actualLength = if ($null -eq $actual) { -1 } else { $actual.Length }
        throw "ChatGPT composer verification failed after paste (expected length $($expected.Length), actual length $actualLength); message was not submitted"
    }
    return "VerifiedClipboard"
}

function Invoke-NavigationElement {
    param(
        [System.Windows.Automation.AutomationElement]$Element,
        [string]$Description
    )

    try {
        $pattern = $Element.GetCurrentPattern(
            [System.Windows.Automation.InvokePattern]::Pattern
        )
        $pattern.Invoke()
        return
    } catch {
        # Some Chromium navigation rows expose SelectionItem instead.
    }

    try {
        $pattern = $Element.GetCurrentPattern(
            [System.Windows.Automation.SelectionItemPattern]::Pattern
        )
        $pattern.Select()
        return
    } catch {
        throw "Cannot open ${Description}; no safe UI Automation action is available"
    }
}

function Open-NamedItem {
    param(
        [System.Windows.Automation.AutomationElement]$Root,
        [string]$Title,
        [string]$Description
    )

    $elements = Get-AllElements -Root $Root
    $matches = @()
    foreach ($element in $elements) {
        try {
            $type = $element.Current.ControlType.ProgrammaticName
            if (
                $element.Current.Name -ceq $Title -and
                $type -in @("ControlType.Button", "ControlType.ListItem")
            ) {
                $matches += $element
            }
        } catch {
            # Ignore elements invalidated during navigation.
        }
    }

    if ($matches.Count -eq 0) {
        throw "Cannot find ${Description} '$Title'. Make sure the exact title is visible in the ChatGPT sidebar."
    }

    $preferredType = if ($Description -eq "chat") {
        "ControlType.ListItem"
    } else {
        "ControlType.Button"
    }
    $preferredMatches = @(
        $matches | Where-Object {
            $_.Current.ControlType.ProgrammaticName -eq $preferredType
        }
    )
    $targets = if ($preferredMatches.Count -gt 0) {
        $preferredMatches
    } else {
        $matches
    }

    if ($targets.Count -gt 1) {
        throw "Multiple ${Description} items are named '$Title'. Rename one or open the intended conversation manually."
    }
    Invoke-NavigationElement -Element $targets[0] -Description $Description
}

function Find-ChatWindow {
    $processes = Get-Process ChatGPT -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 }
    $chatWindows = @()

    foreach ($process in $processes) {
        try {
            $candidateRoot = [System.Windows.Automation.AutomationElement]::FromHandle(
                $process.MainWindowHandle
            )
            $candidateElements = Get-AllElements -Root $candidateRoot
            $composer = $candidateElements |
                Where-Object {
                    $_.Current.Name -in $ComposerLabels -and
                    $_.Current.IsKeyboardFocusable
                } |
                Select-Object -First 1

            if ($composer) {
                $chatWindows += [pscustomobject]@{
                    Process  = $process
                    Root     = $candidateRoot
                    Elements = $candidateElements
                    Composer = $composer
                }
            }
        } catch {
            # Try the next top-level ChatGPT window.
        }
    }

    if ($chatWindows.Count -gt 1) {
        throw "Multiple ChatGPT windows expose a Chat composer. Close extra windows and retry."
    }
    if ($chatWindows.Count -eq 1) {
        return $chatWindows[0]
    }
    return $null
}

function Submit-Composer {
    param(
        [System.Diagnostics.Process]$Process,
        [System.Windows.Automation.AutomationElement]$Root,
        [System.Windows.Automation.AutomationElement]$Composer,
        [string]$ExpectedText,
        [switch]$AllowForegroundFallback
    )

    $elements = Get-AllElements -Root $Root
    $sendButton = Get-SendButton -Elements $elements
    if ($sendButton) {
        $invoke = $sendButton.GetCurrentPattern(
            [System.Windows.Automation.InvokePattern]::Pattern
        )
        $invoke.Invoke()
    } else {
        if (-not $AllowForegroundFallback) {
            throw "No background Send control is available; --no-focus refused to activate the app"
        }
        if (-not (Set-WindowAndComposerFocus -Process $Process -Composer $Composer)) {
            throw "Cannot focus the ChatGPT composer to submit; Enter was not sent"
        }
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    }

    $expected = Normalize-BridgeText $ExpectedText
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 250
        $freshChat = Find-ChatWindow
        if (-not $freshChat) {
            continue
        }
        $composerText = Normalize-BridgeText (Get-ComposerText $freshChat.Composer)
        if ($null -ne $composerText -and [string]::IsNullOrWhiteSpace($composerText)) {
            return $freshChat
        }
    }
    throw "ChatGPT submission could not be verified; response polling was not started"
}

$originalWindow = [HermesCgNative]::GetForegroundWindow()
$oldClipboardData = $null
$clipboardCaptured = $false
$bridgeMutex = [System.Threading.Mutex]::new($false, "Local\HermesCgBridge")
$mutexHeld = $false

try {
    try {
        $mutexHeld = $bridgeMutex.WaitOne(0, $false)
    } catch [System.Threading.AbandonedMutexException] {
        $mutexHeld = $true
    }
    if (-not $mutexHeld) {
        throw "Another /cg bridge is already running"
    }

    if (-not (Test-Path -LiteralPath $InputFile)) {
        throw "Input file does not exist: $InputFile"
    }
    $prompt = [System.IO.File]::ReadAllText(
        $InputFile,
        [System.Text.UTF8Encoding]::new($false)
    )
    if ([string]::IsNullOrWhiteSpace($prompt)) {
        throw "The ChatGPT prompt is empty"
    }

    $chat = Find-ChatWindow
    if (-not $chat) {
        throw "Cannot find the Chat composer. Open ChatGPT > Chat and launch the app with --force-renderer-accessibility."
    }
    $process = $chat.Process
    $root = $chat.Root

    if (-not [string]::IsNullOrWhiteSpace($ProjectTitle)) {
        Open-NamedItem -Root $root -Title $ProjectTitle -Description "project"
        if (
            $originalWindow -ne [IntPtr]::Zero -and
            [HermesCgNative]::GetForegroundWindow() -ne $originalWindow
        ) {
            [HermesCgNative]::SetForegroundWindow($originalWindow) | Out-Null
        }
        Start-Sleep -Seconds 2
    }
    if (-not [string]::IsNullOrWhiteSpace($ChatTitle)) {
        $chat = Find-ChatWindow
        Open-NamedItem -Root $chat.Root -Title $ChatTitle -Description "chat"
        if (
            $originalWindow -ne [IntPtr]::Zero -and
            [HermesCgNative]::GetForegroundWindow() -ne $originalWindow
        ) {
            [HermesCgNative]::SetForegroundWindow($originalWindow) | Out-Null
        }
        Start-Sleep -Seconds 2
    }

    $chat = Find-ChatWindow
    if (-not $chat) {
        throw "The Chat composer disappeared after opening the selected chat"
    }
    $process = $chat.Process
    $root = $chat.Root
    $composer = $chat.Composer

    $existingDraft = Get-ComposerText $composer
    if ($null -eq $existingDraft) {
        throw "The ChatGPT composer does not expose a readable value; refusing unverified input"
    }
    if (-not [string]::IsNullOrWhiteSpace($existingDraft)) {
        throw "The ChatGPT composer already contains a draft. Save or clear it before running /cg"
    }

    try {
        $oldClipboardData = [System.Windows.Forms.Clipboard]::GetDataObject()
        $clipboardCaptured = $true
    } catch {
        throw "Cannot preserve the Windows clipboard; bridge stopped before sending"
    }

    # Observe the existing response structure without clicking any historical
    # Copy control. A /cg run must invoke exactly one Copy control, and only
    # after the new response has finished.
    $baselineCopyCount = @(Get-CopyButtons -Elements $chat.Elements).Count

    $inputMethod = Set-ComposerText `
        -Process $process `
        -Composer $composer `
        -Text $prompt `
        -AllowForegroundFallback:(-not $NoFocusFallback)
    $chat = Find-ChatWindow
    if (-not $chat) {
        throw "The ChatGPT composer disappeared after verified input"
    }
    $composerAfterInput = Get-ComposerVerificationKey (Get-ComposerText $chat.Composer)
    if ($composerAfterInput -cne (Get-ComposerVerificationKey $prompt)) {
        $afterLength = if ($null -eq $composerAfterInput) { -1 } else { $composerAfterInput.Length }
        throw "The ChatGPT composer changed after input verification (actual length $afterLength); message was not submitted"
    }
    $chat = Submit-Composer `
        -Process $chat.Process `
        -Root $chat.Root `
        -Composer $chat.Composer `
        -ExpectedText $prompt `
        -AllowForegroundFallback:(-not $NoFocusFallback)
    $root = $chat.Root

    # Keyboard fallback may need ChatGPT in the foreground for less than a
    # second. Return to the original Hermes terminal immediately after the
    # verified submit instead of leaving ChatGPT visible while it generates.
    if (
        $originalWindow -ne [IntPtr]::Zero -and
        [HermesCgNative]::GetForegroundWindow() -ne $originalWindow
    ) {
        [HermesCgNative]::SetForegroundWindow($originalWindow) | Out-Null
    }

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $generationSeen = $false
    $completionReadyAt = $null
    $replyButton = $null

    while ([DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 250
        try {
            $elements = Get-AllElements -Root $root
            $generationActive = Test-GenerationActive -Elements $elements
            if ($generationActive) {
                $generationSeen = $true
                $completionReadyAt = $null
                continue
            }

            $copyButtons = @(Get-CopyButtons -Elements $elements)
            $structureChanged = $copyButtons.Count -gt $baselineCopyCount
            $now = [DateTime]::UtcNow
            $completionSignal = $generationSeen -or $structureChanged
            if (-not $completionSignal) {
                continue
            }

            # The action row can be rebuilt for a short time after streaming
            # stops. Let it settle before resolving the one button we invoke.
            if ($null -eq $completionReadyAt) {
                $completionReadyAt = $now.AddMilliseconds(2000)
                continue
            }
            if ($now -lt $completionReadyAt) {
                continue
            }

            $settledElements = Get-AllElements -Root $root
            if (Test-GenerationActive -Elements $settledElements) {
                $generationSeen = $true
                $completionReadyAt = $null
                continue
            }

            $replyButton = Get-BottomCopyButton -Elements $settledElements
            if ($replyButton) {
                break
            }
        } catch {
            # Chromium may briefly invalidate controls while settling. No Copy
            # control has been invoked yet, so a read-only retry is safe.
        }
    }

    if (-not $replyButton) {
        throw "Timed out after $TimeoutSeconds seconds waiting for a completed new assistant response"
    }

    # This is the only response Copy invocation in the entire /cg run. Do not
    # re-resolve the button after it changes to Copied, because that can select
    # a historical response and copy multiple conversations.
    $reply = Read-CopyButtonText -Button $replyButton
    if ([string]::IsNullOrWhiteSpace($reply)) {
        throw "The completed ChatGPT response Copy control returned no text"
    }

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($reply)
    $base64 = [Convert]::ToBase64String($bytes)
    Write-Output "CG_BRIDGE_B64:$base64"
}
finally {
    if ($clipboardCaptured) {
        try {
            if ($null -ne $oldClipboardData) {
                [System.Windows.Forms.Clipboard]::SetDataObject(
                    $oldClipboardData,
                    $true
                )
            } else {
                [System.Windows.Forms.Clipboard]::Clear()
            }
        } catch {
            # Clipboard restoration is best-effort.
        }
    }

    if ($originalWindow -ne [IntPtr]::Zero) {
        [HermesCgNative]::SetForegroundWindow($originalWindow) | Out-Null
    }
    if ($mutexHeld) {
        try {
            $bridgeMutex.ReleaseMutex()
        } catch {
            # Process termination also releases the named mutex.
        }
    }
    $bridgeMutex.Dispose()
}
