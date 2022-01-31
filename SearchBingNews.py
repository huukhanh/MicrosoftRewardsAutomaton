from enum import Enum
import json
import logging
import random
import time
import os, sys
import argparse
import re
import traceback
from typing import List

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from Driver import spoof_browser, Driver
from MicrosoftDailies import iter_dailies
from SeleniumHelper import wait_until_clickable, wait_until_visible, click_element, send_key

"""
Automated Binq Query searching and Quiz Completion to maximize daily Microsoft Bing rewards points

V2 updated based on https://github.com/dajoen/Microsoft-Rewards-Bot?ref=https://githubhelp.com
Added Quizzes, Checking points, SeleniumHelper, etc.

OG was apparently: https://github.com/blackluv/Microsoft-Rewards-Bot
Latest? is https://github.com/tmxkn1/Microsoft-Rewards-Bot/tree/master

For running in `Task Scheduler` without a window popping up and stealing focus See: https://www.howtogeek.com/tips/how-to-run-a-scheduled-task-without-a-command-window-appearing/
"""

#TODO: headless mobile is super damn finicky... Add a retry if we don't have the points (get_points should return how many we need)

#TODO: Add README and requirements.txt and way to easily install

#TODO: add with-context for driver to auto-cleanup??

#TODO: how do I add a release in github??

# Should send an email if it fails to get all of the points???

# Screenshot mode should only be enabled if debug is on... otherwise would need to clean out the folder periodically.
# Would require re-write

BING_SEARCH_URL = "https://www.bing.com/search"
DASHBOARD_URL = "https://rewards.microsoft.com/"
POINT_TOTAL_URL = "http://www.bing.com/rewardsapp/bepflyoutpage?style=chromeextension"

verbose_log_format = "%(levelname)s %(asctime)s - %(message)s"
no_log_format = "%(message)s"
log_path = os.path.join('logs', 'ms_rewards.log')
logging.basicConfig(format=no_log_format,
                    level=logging.INFO,
                    handlers=[
                        logging.FileHandler(log_path, mode="w"),
                        logging.StreamHandler()
                    ])

class Device(Enum):
    PC = 1
    Mobile = 2


def setup_opts(parser=None):
    if not parser:
        parser = argparse.ArgumentParser(description="Search Bing News")
    
    parser.add_argument(
        '--drivers',
        '-d',
        nargs='+', type=int,  # nargs='+' lets us specify an array of inputs separated by spaces (eg 1 2 3)
        choices=list([e.value for e in Device]),
        default=[1, 2],
        help='Which comma separated drivers to run (options: 1 (pc - edge), 2 (mobile)). default is %(default)s',
        dest='drivers')
    parser.add_argument(
        '--numWords',
        '-n',
        default=40, type=int,  # Requirement for max points is 30 for PC and 20 for Mobile... but it doesn't always work, so best to run it extra times
        help='How many words to search. default is %(default)s',
        dest='numWords')
    parser.add_argument(
        '--headless',
        action='store_true',
        dest='headless',
        default=False,
        help='Activates "silent" headless mode (no browser will pop up, runs in background), default is off.')
    parser.add_argument(
        '--quiz',
        '-q',
        action='store_true',
        dest='quiz_mode',
        default=False,
        help='Activates pc quiz search if pc driver is selected, default is off.')
    parser.add_argument(
        '--debug',
        action='store_true',
        dest='debug',
        default=False,
        help='Permits screenshots saved to log folder on exception if True, default is off.')
        
    return parser


def main(args):
    completed_quizzes = False
    browser = None
    for i in sorted(args.drivers, reverse=True):  # Do mobile first since it can't get_point_total
        try:
            # Get our driver (mobile or desktop edge)
            device = Device(i)
            logging.info(f"Opening driver type: {device}")
            driver = Driver.CHROME if device == Device.Mobile else Driver.EDGE
            browser = spoof_browser(driver, args.headless, allow_screenshots=args.debug)

            # Login to Microsoft rewards
            if not sign_into_microsoft(browser, device, get_login_info()):
                logging.error("Please Sign in to get the rewards. Some error occurred")
                if browser:
                    browser.close()
                    browser.quit()
                    sys.exit(1)

            if args.numWords > 0:
                words_list = get_search_terms(args.numWords)
                query_bing(browser, words_list)

            if not completed_quizzes and args.quiz_mode and device == Device.PC:
                try:
                    logging.info(f'Attempting daily quizzes.')
                    iter_dailies(browser)
                    completed_quizzes = True
                except Exception as e:
                    logging.error(f'Failed to complete quizzes.')
                    logging.error(traceback.format_exc())

            get_point_total(browser, device, log=True)

        except KeyboardInterrupt:
            logging.error('Stopping Script...')
        finally:
            # https://www.zyxware.com/articles/5552/what-is-close-and-quit-commands-in-selenium-webdriver#:~:text=quit()%20is%20a%20webdriver,not%20be%20cleared%20off%20memory.
            if browser:
                browser.close()  # This just closes the browser window which is currently in focus
                browser.quit()  # Closes all browser windows and terminates the webDriver session
                time.sleep(1)


def sign_into_microsoft(browser, device: Device, credentials: dict):
    browser.get("https://login.live.com")
    time.sleep(0.5)

    logged_in = True
    if wait_until_visible(browser, By.NAME, 'loginfmt', 5):  # Check if we are not already logged in
        wait_until_clickable(browser, By.NAME, 'loginfmt', 5)
        send_key(browser, By.NAME, 'loginfmt', credentials["email"])  # add your login email id
        time.sleep(0.5)
        send_key(browser, By.NAME, 'loginfmt', Keys.RETURN)
        time.sleep(5)

        wait_until_clickable(browser, By.NAME, 'passwd', 5)
        send_key(browser, By.NAME, 'passwd', credentials["password"])  # authenticate
        time.sleep(0.5)
        send_key(browser, By.NAME, 'passwd', Keys.RETURN)
        time.sleep(0.5)
    else:
        logging.info("Should be already logged in")

    if device == Device.PC:
        logged_in = ensure_pc_mode_logged_in(browser)

    return logged_in


def get_login_info() -> dict:
    with open('login.json', 'r') as f:
        return json.load(f)


def ensure_pc_mode_logged_in(browser):
    """
    Navigates to www.bing.com and clicks on ribbon to ensure logged in
    PC mode for some reason sometimes does not fully recognize that the user is logged in
    :return: True if logged in
    """
    browser.get(BING_SEARCH_URL)
    time.sleep(0.1)
    # click on ribbon to ensure logged in
    wait_until_clickable(browser, By.ID, 'id_l', 10)
    click_element(browser, By.ID, 'id_l')
    time.sleep(0.1)

    # Ensure that the name id exists and is not hidden (this indicates you are signed in)
    wait_until_visible(browser, By.ID, 'id_n', 10)
    elem = browser.find_element(By.ID, 'id_n')
    return elem.get_attribute("aria-hidden") == "false"


def get_search_terms(num: int):
    dir = os.path.dirname(__file__)
    wordsPath = os.path.join(dir, "wordsList.txt")
    with open(wordsPath) as json_file:
        data = json.load(json_file)
    words_list = random.sample(data['data'], num)
    logging.info(f"{len(words_list)} words selected from {wordsPath}")
    return words_list


def query_bing(browser, words: List[str]):
    url_base = f"{BING_SEARCH_URL}?q="
    time.sleep(5)
    for ind, word in enumerate(words):
        search_url = url_base + word
        logging.info(f"Search #{str(ind + 1)}. URL: {search_url}")
        try:
            browser.get(search_url)
            time.sleep(0.1)
            logging.info('\t' + browser.find_element(By.TAG_NAME, 'h2').text)
        except Exception as e1:
            logging.error(e1)

        time.sleep(random.uniform(1, 3))  # Try Not to get caught


def get_point_total(browser, device: Device, log: bool = False):
    """
    Checks for points for pc/edge and mobile, logs if flag is set
    :return: Boolean for either pc/edge or mobile points met
    """
    try:
        logging.info(msg="Querying for point totals:")
        browser.get(DASHBOARD_URL)
        time.sleep(1)

        if click_element(browser, By.XPATH, '//a[contains(@class, "signup-btn welcome")]', ignore_no_such_element=True):
            logging.debug('Welcome page detected.')
            time.sleep(2)

        # Some magical script with user rewards account info
        js = browser.find_elements(By.XPATH, '//script[text()[contains(., "userStatus")]]')
        matches = re.search(r'(?=\{"userStatus":).*(=?\}\};)', js[0].get_attribute('text'))

        # Query the json data for various rewards info
        json_statuses = json.loads(matches[0][:-1])
        status = json_statuses['userStatus']
        counters = status['counters']

        pc_search = counters['pcSearch'][0]
        (pc_pts, pc_max) = (int(pc_search['pointProgress']), int(pc_search['pointProgressMax']))
        edge_bonus = counters['pcSearch'][1]
        (edge_bonus_pts, edge_bonus_max) = (int(edge_bonus['pointProgress']), int(edge_bonus['pointProgressMax']))

        mobile_search = counters['mobileSearch'][0]
        (mobile_pts, mobile_max) = (int(mobile_search['pointProgress']), int(mobile_search['pointProgressMax']))

        daily_points = int(counters["dailyPoint"][0]["pointProgress"])
        (current_points, lifetime_points) = (int(status['availablePoints']), int(status["lifetimePoints"]))

        num_incomplete_quizzes = len([p for p in json_statuses.get("morePromotions", []) if not p["complete"]])

        if log:
            logging.info(f'\n')
            logging.info(f'----------------------------------------------------')
            logging.info(f'PC points = {pc_pts}/{pc_max}')
            logging.info(f'Mobile points = {mobile_pts}/{mobile_max}')
            logging.info(f'Edge Bonus points = {edge_bonus_pts}/{edge_bonus_max}')
            logging.info(f'Points earned today: {daily_points}')
            logging.info(f'Total Points Available/Earned = {current_points}/{lifetime_points}')
            logging.info(f"Number of incomplete quizzes: {num_incomplete_quizzes}")
            logging.info(f'----------------------------------------------------')
            logging.info(f'\n')

        max_points_achieved = pc_pts == pc_max if device == Device.PC else mobile_pts == mobile_max

        return max_points_achieved
    except Exception as e:
        logging.error(f'Failed grabbing the points: \n{traceback.format_exc()}')
        return False


if __name__ == "__main__":
    start = time.time()

    parser = setup_opts()
    args = parser.parse_args()
    logging.info(f"CLI arguments: {args}")

    main(args)

    elapsed = time.time() - start
    elapsed_formatted = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    logging.info(f"We have reached the exit of the script after {elapsed_formatted} h:m:s")
    sys.exit(0)
