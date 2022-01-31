# MicrosoftRewards
For Research Purposes Only (of course): Automate collection of [Microsoft Bing Rewards](https://rewards.microsoft.com/) points 
- Searches Bing in PC, MS Edge and Mobile
- Completes daily quizzes / offers

## Install
- Requires python 3.7+ (Tested with python 3.10.x)
- Tested on Windows 10 (should work in mac/linux)

1. Clone repo
2. Create `login.json` file at root directory with your account name and password
   1. See `login.example.json` for example
3. Install dependencies: `python -m pip install -r requirements.txt`

## Run

###Locally
`python SearchBingNews.py -h` or `--help` for command arguments / more info

###Automated Daily

## Troubleshooting
If mobile doesn't work, you may need to update/change the user agent. 
On your personal phone, google "My User Agent". Update #TODO -> link

## Inspiration / Credit
- Microsoft-Rewards-Bot: [Latest](https://github.com/tmxkn1/Microsoft-Rewards-Bot/tree/master) | [OG](https://github.com/blackluv/Microsoft-Rewards-Bot)
- [medium article](https://medium.com/@prateekrm/earn-500-daily-microsoft-rewards-points-automatically-with-a-simple-python-program-38fe648ff2a9)
