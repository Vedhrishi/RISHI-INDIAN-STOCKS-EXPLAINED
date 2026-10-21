# Keeps the live website in sync with whatever's actually public, on its own schedule.
# Regenerates data (picks up newly-public YouTube videos via the oEmbed check already in
# build_data.py), commits only if something changed, and deploys to production.
# Safe to run as often as you like - it's a no-op if nothing is new.
$ErrorActionPreference = 'Stop'
Set-Location 'R:\INSTA\website'
python tools\build_data.py
git add data\videos.json supabase\seed.sql thumbs\
git diff --cached --quiet
$hasChanges = ($LASTEXITCODE -ne 0)
if ($hasChanges) {
  git -c user.name="Vedhrishi" -c user.email="148317616+Vedhrishi@users.noreply.github.com" commit -q -m "Auto-sync: pick up newly-public videos ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))"
  git push origin master
  npx --yes vercel --prod
  Write-Host "Deployed - new content was found." -ForegroundColor Green
} else {
  Write-Host "Nothing new - skipped commit/deploy." -ForegroundColor DarkGray
}
