# Running it on autopilot

Pick one. Both run `python main.py` from `automation/youtube_pipeline` once a day.

## A. Your own Windows PC (Task Scheduler)
```powershell
$dir = "C:\path\to\automation\youtube_pipeline"
python -m venv "$dir\venv"; & "$dir\venv\Scripts\pip" install -r "$dir\requirements.txt"
& "$dir\venv\Scripts\python" "$dir\doctor.py"      # every line must say [ OK ]
$action   = New-ScheduledTaskAction -Execute "$dir\venv\Scripts\python.exe" -Argument "main.py" -WorkingDirectory $dir
$trigger  = New-ScheduledTaskTrigger -Daily -At 2:00PM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "YT Autopilot Daily" -Action $action -Trigger $trigger -Settings $settings
```
`-StartWhenAvailable` runs a missed job when the PC wakes. **Allow it on battery**; the default setting is the usual reason a laptop's task fails with `0x800710E0`.
The PC has to be on, and any drive the project lives on must be mounted at that time.

## B. A small cloud server (AWS EC2 / any Linux VPS)
Heroku is a poor fit (ephemeral disk, request time limits, heavy video rendering). Use a VM with 2 vCPU / 4 GB RAM.
```bash
sudo apt update && sudo apt install -y python3-venv ffmpeg fonts-dejavu-core git
git clone https://github.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED.git && cd RISHI-INDIAN-STOCKS-EXPLAINED/automation/youtube_pipeline
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
# copy .env, client_secret.json and token.json up with scp, then:
chmod 600 .env token.json client_secret.json && ./venv/bin/python doctor.py && ./venv/bin/python main.py
crontab -e   # then add (server time is UTC):
0 14 * * * cd /home/ubuntu/RISHI-INDIAN-STOCKS-EXPLAINED/automation/youtube_pipeline && ./venv/bin/python main.py >> cron.log 2>&1
```
Set `NOTIFY_WEBHOOK` in `.env` (Slack or Discord incoming webhook) to get a message on every success or failure.

## Before you stop watching it
- Run it by hand for several days with `YOUTUBE_PRIVACY=private` and read what it produces.
- YouTube's policy on mass-produced or repetitive content can demonetise or remove channels that post unreviewed, templated videos. Keep a human in the loop for a few minutes a day.
- Disclose AI-generated voice or visuals (the uploader sets the synthetic-media flag for you).
- Only scrape feeds you are allowed to use, and keep the source credit in the description.
