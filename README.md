# MicrosoftRewards
For Research Purposes Only (of course).

Automate collection of [Microsoft Bing Rewards](https://rewards.microsoft.com/) points 
- Searches Bing in PC, MS Edge and Mobile
- Completes daily quizzes / offers
- Auto-updates web drivers to ensure Microsoft registers queries and provides points
  - Retries 3 times if points not registered

## Install

1. Clone repo
2. Create `login.json` file at root directory with your account name and password
   1. See `login.example.json` for example
3. Install dependencies: `python -m pip install -r requirements.txt`

### Dependencies
- Requires python 3.7+ (Tested with python 3.10.x)
- Tested on Windows 10 (should work in mac/linux)

## Run

### Locally
`cd` to `MicrosoftRewards` from root or use `python MicrosoftRewards/SearchBingNews.py`.

Examples:
- Get all command arguments / more info
  - `python SearchBingNews.py -h` or `--help`
- Run everything headless (should be default daily for all runs)
  - `python SearchBingNews.py -q --headless`
- Run 1 search (-n 1), in PC mode (-d 1), with debug on to save screenshots:
  - `python SearchBingNews.py -d 1 -n 1 --debug`
  
### Automated Daily

#### Windows Task Scheduler
Google how to set up a task in the scheduler. Reference [WindowsTaskScheduler_Example.xml](WindowsTaskScheduler_Example.xml) for correct settings for windows 10

Make sure it is executing `python SearchBingNews.py -q --headless` to get all points

For running in `Task Scheduler` without a window popping up and stealing focus
See: https://www.howtogeek.com/tips/how-to-run-a-scheduled-task-without-a-command-window-appearing/

#### Linux
use crontab -> figure it out yourself.
Can use a docker container if desired.

## Troubleshooting
If mobile doesn't register points, you may need to update/change the user agent. 
On your personal phone, google "My User Agent" and update `spoof_browser` function of [Driver.py](MicrosoftRewards/Driver.py)

## Inspiration / Credit
- Microsoft-Rewards-Bot: [Latest](https://github.com/tmxkn1/Microsoft-Rewards-Bot/tree/master) | [OG](https://github.com/blackluv/Microsoft-Rewards-Bot)
- [medium article](https://medium.com/@prateekrm/earn-500-daily-microsoft-rewards-points-automatically-with-a-simple-python-program-38fe648ff2a9)
