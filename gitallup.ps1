# gitallup.ps1 run by gitup.cmd, which sets 'bypass execution policy'
# Automatically commit & push with current date/time as commit message

# Change to the current directory where the command is run
Set-Location $PWD

# Generate date string in format YYYY-MM-DD-hh-mm
$dateString = Get-Date -Format "yyyy-MM-dd-HH-mm"

# Run git commands
git add -A
git commit -m "herbUpdate $dateString"
git push
