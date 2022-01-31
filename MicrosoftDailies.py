import logging
import random
import time

from selenium.common.exceptions import WebDriverException, TimeoutException, \
    ElementClickInterceptedException, ElementNotVisibleException, \
    ElementNotInteractableException

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from SeleniumHelper import wait_until_clickable, wait_until_visible, main_window, latest_window, click_element

"""
This file handles logic for iterating through daily offers in microsoft rewards dashboard.
Quizzes, click to search offers, etc.
"""

DASHBOARD_URL = "https://rewards.microsoft.com/"


def iter_dailies(browser):
    """
    Iterates through all outstanding dailies on microsoft rewards dashboard
    :return: None
    """
    time.sleep(1)
    logging.info(f"loading: {DASHBOARD_URL}")
    browser.get(DASHBOARD_URL)
    time.sleep(2)
    sign_in_link = browser.find_elements(By.ID, 'raf-signin-link-id')
    if sign_in_link:
        logging.info(msg="clicking sign_in link to go to rewards")
        sign_in_link[0].click()
        time.sleep(2)

    open_offers = browser.find_elements_by_xpath('//span[contains(@class, "mee-icon-AddMedium")]')
    if not open_offers:
        logging.info('No dailies found.')
        return

    attempts = 0
    while open_offers and attempts < 3:
        attempts += 1
        logging.info(f'Number of open offers: {len(open_offers)}')

        # get common parent element of open_offers
        parent_elements = [open_offer.find_element(By.XPATH, '..//..//..//..') for open_offer in open_offers]
        # get points links from parent, # finds link (a) descendant of selected node
        offer_links = [
            parent.find_element(By.XPATH,
                'div[contains(@class,"actionLink")]//descendant::span')
            for parent in parent_elements
        ]
        # iterate through the dailies
        for offer in offer_links:
            time.sleep(3)
            logging.debug(msg='Detected offer.')
            # click and switch focus to latest window
            offer.click()
            latest_window(browser)
            time.sleep(5)
            # check for sign-in prompt
            sign_in_prompt(browser)
            # check for poll by ID
            if browser.find_elements(By.ID, 'btoption0'):
                logging.info('Poll identified.')
                daily_poll(browser)
            # check for quiz by checking for ID
            elif browser.find_elements(By.ID, 'rqStartQuiz'):
                click_element(browser, By.ID, 'rqStartQuiz')
                # test for drag or drop or regular quiz
                if browser.find_elements(By.ID, 'rqAnswerOptionNum0'):
                    logging.info('Drag and Drop Quiz identified.')
                    drag_and_drop_quiz(browser)
                # look for lightning quiz indicator
                elif browser.find_elements(By.ID, 'rqAnswerOption0'):
                    logging.info('Lightning Quiz identified.')
                    lightning_quiz(browser)
            elif browser.find_elements(By.CLASS_NAME, 'wk_Circle'):
                logging.info('Click Quiz identified.')
                click_quiz(browser)
            # else do scroll for exploring pages
            else:
                #TODO: if we fail to get any answers correct on a quiz it may show an input of type button with value "Join now for free*"
                # Appears to be a bug. I don't see it clicking myself. It also counts for the daily streak

                logging.info('Explore Daily identified.')
                explore_daily(browser)
        # check at the end of the loop to log if any offers are remaining
        browser.get(DASHBOARD_URL)
        time.sleep(0.1)
        wait_until_visible(browser, By.TAG_NAME, 'body', 10)  # checks for page load
        open_offers = browser.find_elements_by_xpath('//span[contains(@class, "mee-icon-AddMedium")]')
        logging.info(f'Number of incomplete offers remaining: {len(open_offers)}')


def explore_daily(browser):
    # needs try/except bc these functions don't have exception handling built in.
    try:
        # select html to send commands to
        html = browser.find_element(By.TAG_NAME, 'html')
        # scroll up and down to trigger points
        for i in range(3):
            html.send_keys(Keys.END)
            html.send_keys(Keys.HOME)
        # exit to main window
        main_window(browser)
    except TimeoutException:
        logging.exception(msg='Explore Daily Timeout Exception.')
    except (ElementNotVisibleException, ElementClickInterceptedException, ElementNotInteractableException):
        logging.exception(msg='Element not clickable or visible.')
    except WebDriverException:
        logging.exception(msg='Error.')


def daily_poll(browser):
    """
    Randomly clicks a poll answer, returns to main window
    :return: None
    """
    time.sleep(3)
    # click poll option
    choices = ['btoption0', 'btoption1']  # new poll format
    click_element(browser, By.ID, random.choice(choices))
    time.sleep(2)
    # close window, switch to main
    main_window(browser)


def lightning_quiz(browser):
    for question_round in range(10):
        logging.debug(msg=f'Round# {question_round}')
        if browser.find_elements(By.ID, 'rqAnswerOption0'):
            first_page = browser.find_element(By.ID, 'rqAnswerOption0').get_attribute("data-serpquery")
            browser.get(f"https://www.bing.com{first_page}")
            time.sleep(3)
            for i in range(10):
                if browser.find_elements(By.ID, f'rqAnswerOption{i}'):
                    browser.execute_script(f"document.querySelector('#rqAnswerOption{i}').click();")
                    logging.debug(msg=f'Clicked {i}')
                    time.sleep(2)
        # let new page load
        time.sleep(2)
        if browser.find_elements(By.ID, 'quizCompleteContainer'):
            break
    # close the quiz completion splash
    quiz_complete = browser.find_elements(By.CSS_SELECTOR, '.cico.btCloseBack')
    if quiz_complete:
        quiz_complete[0].click()
    time.sleep(2)
    main_window(browser)


def click_quiz(browser):
    """
    Start the quiz, iterates 10 times
    """
    for i in range(10):
        if browser.find_elements(By.CSS_SELECTOR, '.cico.btCloseBack'):
            browser.find_elements(By.CSS_SELECTOR, '.cico.btCloseBack')[0].click()[0].click()
            logging.debug(msg='Quiz popped up during a click quiz...')
        choices = browser.find_elements(By.CLASS_NAME, 'wk_Circle')
        # click answer
        if choices:
            random.choice(choices).click()
            time.sleep(3)
        # click the 'next question' button
        wait_until_clickable(browser, By.CLASS_NAME, 'wk_buttons', 10)
        click_element(browser, By.CLASS_NAME, 'wk_buttons')
        time.sleep(2)

        # if the green check mark reward icon is visible, end loop
        if browser.find_elements(By.CSS_SELECTOR, 'span[class="rw_icon"]'):
            break

    main_window(browser)


def drag_and_drop_quiz(browser):
    """
    Checks for drag quiz answers and exits when none are found.
    :return: None
    """
    for _ in range(100):
        try:
            # find possible solution buttons
            drag_option = browser.find_elements(By.CLASS_NAME, 'rqOption')
            # find any answers marked correct with correctAnswer tag
            right_answers = browser.find_elements(By.CLASS_NAME, 'correctAnswer')
            # remove right answers from possible choices
            if right_answers:
                drag_option = [x for x in drag_option if x not in right_answers]

            if drag_option:
                # select first possible choice and remove from options
                choice_a = random.choice(drag_option)
                drag_option.remove(choice_a)
                # select second possible choice from remaining options
                choice_b = random.choice(drag_option)
                ActionChains(browser).drag_and_drop(choice_a, choice_b).perform()
        except (WebDriverException, TypeError):
            logging.debug(msg='Unknown Error.')
            continue
        finally:
            time.sleep(3)
            if browser.find_elements(By.ID, 'quizCompleteContainer'):
                break

    # close the quiz completion splash
    time.sleep(3)
    quiz_complete = browser.find_elements(By.CSS_SELECTOR, '.cico.btCloseBack')
    if quiz_complete:
        quiz_complete[0].click()
    time.sleep(3)
    main_window(browser)


def sign_in_prompt(browser):
    time.sleep(3)
    sign_in_prompt_msg = browser.find_elements(By.CLASS_NAME, 'simpleSignIn')
    if sign_in_prompt_msg:
        logging.info(msg='Detected sign-in prompt')
        browser.find_element(By.LINK_TEXT, 'Sign in').click()
        logging.info(msg='Clicked sign-in prompt')
        time.sleep(4)