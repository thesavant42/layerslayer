# Python Modules should not be greater than bout 100 lines, or they become hard to see, and hard to work with.
# This script identifies all python scripts that are 100 lines of code or greater as violations of the style guide.
# It also lists files that are in danger of soon becoming too big, so that they are not chosen as destinations for 
# code refactoring.

# Initialize arrays to hold the classified files
$violators = @()
$dangerZone = @()

# Get all python files recursively
Get-ChildItem -Path . -Filter *.py -Recurse | ForEach-Object {
    # Count lines
    $lines = (Get-Content $_.FullName | Measure-Object -Line).Lines

    # 1. Print ALL files as they are processed
    "{0} - {1} lines" -f $_.FullName, $lines

    # 2. Categorize the file based on line count
    if ($lines -gt 100) {
        $violators += [PSCustomObject]@{
            File  = $_.FullName
            Lines = $lines
        }
    }
    elseif ($lines -ge 80) {
        $dangerZone += [PSCustomObject]@{
            File  = $_.FullName
            Lines = $lines
        }
    }
}

# 3. Print the Summaries
Write-Host "`n================ SUMMARY ================" -ForegroundColor Cyan

# Print Violators
if ($violators.Count -gt 0) {
    Write-Host "`n[!] VIOLATORS (> 100 lines)" -ForegroundColor Red
    $violators | Sort-Object Lines -Descending | Format-Table -AutoSize
} else {
    Write-Host "`n[!] VIOLATORS: None." -ForegroundColor Gray
}

# Print Danger Zone
if ($dangerZone.Count -gt 0) {
    Write-Host "`n[!] DANGER ZONE (80 - 100 lines)" -ForegroundColor Yellow
    $dangerZone | Sort-Object Lines -Descending | Format-Table -AutoSize
} else {
    Write-Host "`n[!] DANGER ZONE: None." -ForegroundColor Gray
}