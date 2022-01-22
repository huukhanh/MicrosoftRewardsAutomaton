from enum import Enum
import json
import logging
import random
import time
import os, sys
import argparse
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from MicrosoftDailies import iter_dailies
from SeleniumHelper import wait_until_clickable, click_by_id, wait_until_visible, send_key_by_name

"""
Automated Binq Query searching and Quiz Completion to maximize daily Microsoft Bing rewards points

V2 updated based on https://github.com/dajoen/Microsoft-Rewards-Bot?ref=https://githubhelp.com
Added Quizzes, Checking points, SeleniumHelper, etc.

OG was apparently: https://github.com/blackluv/Microsoft-Rewards-Bot
Latest? is https://github.com/tmxkn1/Microsoft-Rewards-Bot/tree/master

For running in `Task Scheduler` without a window popping up and stealing focus See: https://www.howtogeek.com/tips/how-to-run-a-scheduled-task-without-a-command-window-appearing/
"""


#TODO: mobile cant get points: better to get rewards from modal of `Points breakdown` on rewards dashboard. Then could also get the total available points to spend
#TODO: headless mobile is super damn finicky... Add a retry if we don't have the points (get_points should return how many we need)

#TODO: clean everything up, especially with selenium v4 and the browser spoofing

# TODO: add the auto-update drivers functionality (probably to SeleniumHelper and move the driver spoofing too)
    
BING_SEARCH_URL = "https://www.bing.com/search"
DASHBOARD_URL = "https://rewards.microsoft.com/"
POINT_TOTAL_URL = "http://www.bing.com/rewardsapp/bepflyoutpage?style=chromeextension"

verbose_log_format = "%(levelname)s %(asctime)s - %(message)s"
no_log_format = "%(message)s"
logging.basicConfig(# filename="logfile.log",
                    stream=sys.stdout,
                    filemode="w",
                    format=no_log_format,
                    level=logging.INFO)


class Device(Enum):
    PC = 1
    Mobile = 2


CURRENT_DEVICE = Device.PC


def get_login_info() -> dict:
    with open('login.json', 'r') as f:
        return json.load(f)


def setupOpts(parser = None):
    if not parser:
        parser = argparse.ArgumentParser(description="Search Bing News")
    
    parser.add_argument(
        '--drivers',
        '-d',
        nargs='+', type=int,  # nargs='+' lets us specify an array of inputs separated by spaces (eg 1 2 3)
        choices=list([e.value for e in Device]),
        default=[1, 2],
        help='Which drivers do you want to test. comma separated (options: 1 (pc), 2 (mobile)). default is %(default)s',
        dest='drivers')
    parser.add_argument(
        '--numWords',
        '-n',
        default=40, type=int,  # Requirement fopr max points is 30 for PC and 20 for Mobile... but it doesn't always work, so best to run it extra
        help='How many words to search. default is %(default)s',
        dest='numWords')
    parser.add_argument(
        '--headless',
        action='store_true',
        dest='headless',
        default=False,
        help='Activates headless mode, default is off.')
    parser.add_argument(
        '--quiz',
        '-q',
        action='store_true',
        dest='quiz_mode',
        default=False,
        help='Activates pc quiz search if pc driver is selected, default is off.')
        
    return parser


def wait_for(sec=2):
    time.sleep(sec)


def spoof_broswer(driver_type, args):
    dir = os.path.dirname(__file__)

    options = ChromeOptions() if driver_type == Device.Mobile.value else EdgeOptions()
    if args.headless:
        options.headless = True

    # This stops us from failing the bluetooth check, other weird errors due to headless and random logging
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    if driver_type == Device.PC.value:
        # Open up Edge on desktop (no spoofing user agent required)

        # THis method I couldn't figure out how to get headless options (and also had issue with Edge instances in startup)
        # edge_path = os.path.join(dir, 'msedgedriver.exe')
        # driver = webdriver.Edge(options=driveroptions, executable_path=edge_path)

        # see https://docs.microsoft.com/en-us/microsoft-edge/webdriver-chromium?tabs=python

        options.use_chromium = True
        options.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

        driver = webdriver.Edge(options=options)
    elif driver_type == Device.Mobile.value:
        # Spoof my user agent as my phone (Just google my user agent via my mobile device for the exact agent string)
        # The user agent needs to be updated every time my phone updates chrome...
            # One way would be to somehow access my phone and query my user agent via web browser (https://www.makeuseof.com/tag/can-i-control-a-phone-with-my-computer-android/)
                # Not really sure this would work...
            # I could also write a quick web crawler to query https://chromereleases.googleblog.com/ for the latest "Chrome for Android Update" and parse out the string
                # ALT: http://omahaproxy.appspot.com/ (search os: android; channel: stable; get the current_version (can also get previous version here)
                    # THis genius did it for me: https://github.com/twkrol/vergrabber
                    # https://github.com/twkrol/vergrabber/blob/master/clients/chrome.py
                # This doesn't gaurantee that my phone has updated to the latest just yet...
            # I could stop auyo-updating chrome on my phone (nah)
            # I could write a follow up script to verify I've gotten my mobile points for the day (delay by x minutes or hours)
                # I'd then need to notice a warning that occurs (and manuallu update and re-run) or just re-submit this script with a different parsed agent
        chrome_path = os.path.join(dir, 'chromedriver.exe')

        options.add_argument('--user-agent="Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.87 Mobile Safari/537.36"')
        driver = webdriver.Chrome(options=options, service=Service(chrome_path))

    driver.set_page_load_timeout(20)

    return driver


def get_search_terms(num):
    # This request doesn't always work -> So I just took the data and made a txt file for perpetuity
    # randomlists_url = "https://www.randomlists.com/data/words.json"
    # response = requests.get(randomlists_url)
    # words_list = random.sample(json.loads(response.text)['data'], num)
    # print('{0} words selected from {1}'.format(len(words_list), randomlists_url))
    dir = os.path.dirname(__file__)
    wordsPath = os.path.join(dir, "wordsList.txt")
    with open(wordsPath) as json_file:
        data = json.load(json_file)
    words_list = random.sample(data['data'], num)
    logging.info(f"{len(words_list)} words selected from {wordsPath}")
    return words_list


def sign_into_microsoft(driver, credentials):
    driver.get("https://login.live.com")
    wait_for(0.5)

    logged_in = True
    if wait_until_visible(driver, By.NAME, 'loginfmt', 5):  # Check if we are not already logged in
        wait_until_clickable(driver, By.NAME, 'loginfmt', 5)
        send_key_by_name(driver, 'loginfmt', credentials["email"])  # add your login email id
        wait_for(0.5)
        send_key_by_name(driver, 'loginfmt', Keys.RETURN)
        wait_for(5)

        wait_until_clickable(driver, By.NAME, 'passwd', 5)
        send_key_by_name(driver, 'passwd', credentials["password"])  # authenticate
        time.sleep(0.5)
        send_key_by_name(driver, 'passwd', Keys.RETURN)
        time.sleep(0.5)
    else:
        logging.info("Should be already logged in")

    if CURRENT_DEVICE == Device.PC:
        logged_in = ensure_pc_mode_logged_in(driver)
    
    return logged_in


def ensure_pc_mode_logged_in(browser):
    """
    Navigates to www.bing.com and clicks on ribbon to ensure logged in
    PC mode for some reason sometimes does not fully recognize that the user is logged in
    :return: True if logged in
    """
    browser.get(BING_SEARCH_URL)
    wait_for(0.1)
    # click on ribbon to ensure logged in
    wait_until_clickable(browser, By.ID, 'id_l', 10)
    click_by_id(browser, 'id_l')
    wait_for(0.1)

    # Ensure that the name id exists and is not hidden (this indicates you are signed in)
    wait_until_visible(driver, By.ID, 'id_n', 10)
    elem = driver.find_element(By.ID, 'id_n')
    return elem.get_attribute("aria-hidden") == "false"


def query_bing(driver, words_list):
    url_base = f"{BING_SEARCH_URL}?q="
    wait_for(5)
    for num, word in enumerate(words_list):
        search_url = url_base + word
        logging.info(f"Search #{str(num + 1)}. URL: {search_url}")
        try:
            driver.get(search_url)
            wait_for(0.1)
            logging.info('\t' + driver.find_element(By.TAG_NAME, 'h2').text)
        except Exception as e1:
            logging.error(e1)

        wait_for(random.uniform(1, 3))  # Try Not to get caught


def get_point_total(browser, pc=False, mobile=False, log=False):
    """
    Checks for points for pc/edge and mobile, logs if flag is set
    :return: Boolean for either pc/edge or mobile points met
    """
    logging.info(msg="Querying for point totals.")
    browser.get(POINT_TOTAL_URL)

    if not wait_until_visible(browser, By.CLASS_NAME, 'earn', 10):  # if object not found, return False
        logging.info(msg=f"Exiting get_point_total: could not find any elements with class 'earn'")
        return False

    try:
        # NOTE: CSS doesn't do regular expressions at all.
        # $= is a tail-string match. Similarly *= is a partial-substring match, and ^= is a head-string match.
        current_pc_points, max_pc_points = map(
            int, driver.find_element(By.CSS_SELECTOR, "div[aria-label*=PC]").text.split('/'))
        current_mobile_points, max_mobile_points = map(
            int, driver.find_element(By.CSS_SELECTOR, "div[aria-label*=Mobile]").text.split('/'))
    except ValueError as e:
        logging.info(msg=f'failed grabbing the points: ')
        logging.info(msg=e)
        return False

    # if log flag is provided, log the point totals
    if log:
        logging.info(msg=f'PC points = {current_pc_points}/{max_pc_points}')
        logging.info(msg=f'Mobile points = {current_mobile_points}/{max_mobile_points}')

    # if pc flag, check if pc and edge points met
    if pc:
        if current_pc_points < max_pc_points:
            return False
        return True
    # if mobile flag, check if mobile points met
    if mobile:
        if current_mobile_points < max_mobile_points:
            return False
        return True


if __name__ == "__main__":
    parser = setupOpts()
    args = parser.parse_args()

    logging.info(f"CLI arguments: {args}")

    completed_quizzes = False
    for i in sorted(args.drivers, reverse=True):  # Do mobile first since it can't get_point_total
        try:
            # Get our driver (mobile or desktop edge)
            CURRENT_DEVICE = Device(i)
            logging.info(f"Opening driver type: {CURRENT_DEVICE}")
            driver = spoof_broswer(i, args)

            # Login to Microsoft rewards
            if not sign_into_microsoft(driver, get_login_info()):
                logging.error("Please Sign in to get the rewards. Some error occurred")
                driver.close()
                driver.quit()
                sys.exit(1)

            if args.numWords > 0:
                words_list = get_search_terms(args.numWords)
                query_bing(driver, words_list)

            if not completed_quizzes and args.quiz_mode and CURRENT_DEVICE == Device.PC:
                try:
                    logging.info(f'Attempting daily quizzes.')
                    iter_dailies(driver)
                    completed_quizzes = True
                except Exception as e:
                    logging.error(f'Failed to complete quizzes: {e}')
                    logging.error(traceback.format_exc())

            if CURRENT_DEVICE == Device.PC:  # Doesn't work with mobile currently
                get_point_total(driver, log=True)

        except KeyboardInterrupt:
            logging.error('Stopping Script...')
        finally:
            # https://www.zyxware.com/articles/5552/what-is-close-and-quit-commands-in-selenium-webdriver#:~:text=quit()%20is%20a%20webdriver,not%20be%20cleared%20off%20memory.
            driver.close()  # This just closes the browser window which is currently in focus
            driver.quit()  # Closes all browser windows and terminates the webDriver session
            wait_for(1)

    logging.info("We have reached the exit of the script.")
    sys.exit(0)
