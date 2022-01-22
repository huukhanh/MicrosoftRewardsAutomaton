from datetime import datetime
import logging
import os
import time

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException, ElementClickInterceptedException, ElementNotVisibleException, \
    ElementNotInteractableException, NoSuchElementException, UnexpectedAlertPresentException
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait


"""
Provides helpers for selenium... I didn't write this... could use some improvements.
Maybe uncomment the screenshot ability later to help debug
https://github.com/dajoen/Microsoft-Rewards-Bot?ref=https://githubhelp.com
"""


def wait_until_clickable(browser, by_, selector, time_to_wait=10):
    """
    Waits time_to_wait seconds for element to be clickable
    :param by_:  BY module args to pick a selector
    :param selector: string of xpath, css_selector or other
    :param time_to_wait: Int time to wait
    :return: None
    """
    try:
        WebDriverWait(browser, time_to_wait).until(ec.element_to_be_clickable((by_, selector)))
    except TimeoutException:
        logging.exception(msg=f'{selector} element Not clickable - Timeout Exception', exc_info=False)
        screenshot(browser, selector)
    except UnexpectedAlertPresentException:
        # FIXME
        browser.switch_to.alert.dismiss()
        # logging.exception(msg=f'{selector} element Not Visible - Unexpected Alert Exception', exc_info=False)
        # screenshot(browser, selector)
        # browser.refresh()
    except WebDriverException:
        logging.exception(msg=f'Webdriver Error for {selector} object')
        screenshot(browser, selector)


def click_by_class(browser, selector):
    """
    Clicks on node object selected by class name
    :param selector: class attribute
    :return: None
    """
    try:
        browser.find_element(By.CLASS_NAME, selector).click()
    except (ElementNotVisibleException, ElementClickInterceptedException, ElementNotInteractableException):
        logging.exception(msg=f'Send key by class to {selector} element not visible or clickable.')
    except WebDriverException:
        logging.exception(msg=f'Webdriver Error for send key by class to {selector} object')


def click_by_id(browser, obj_id):
    """
    Clicks on object located by ID
    :param obj_id: id tag of html object
    :return: None
    """
    try:
        browser.find_element(By.ID, obj_id).click()
    except (ElementNotVisibleException, ElementClickInterceptedException, ElementNotInteractableException):
        logging.exception(msg=f'Click by ID to {obj_id} element not visible or clickable.')
    except WebDriverException:
        logging.exception(msg=f'Webdriver Error for click by ID to {obj_id} object')


def wait_until_visible(browser, by_, selector, time_to_wait=10):
    """
    Searches for selector and if found, end the loop
    Else, keep repeating every 2 seconds until time elapsed, then refresh page
    :param by_: string which tag to search by
    :param selector: string selector
    :param time_to_wait: int time to wait
    :return: Boolean if selector is found
    """
    start_time = time.time()
    while (time.time() - start_time) < time_to_wait:
        if browser.find_elements(by=by_, value=selector):
            return True
        browser.refresh()  # for other checks besides points url
        time.sleep(2)
    return False


def send_key_by_name(browser, name, key):
    """
    Sends key to target found by name
    :param name: Name attribute of html object
    :param key: Key to be sent to that object
    :return: None
    """
    try:
        browser.find_element(By.NAME, name).send_keys(key)
    except (ElementNotVisibleException, ElementClickInterceptedException, ElementNotInteractableException):
        logging.exception(msg=f'Send key by name to {name} element not visible or clickable.')
    except NoSuchElementException:
        logging.exception(msg=f'Send key to {name} element, no such element.')
        screenshot(browser, name)
        browser.refresh()
    except WebDriverException:
        logging.exception(msg=f'Webdriver Error for send key to {name} object')


def find_by_id(browser, obj_id):
    """
    Searches for elements matching ID
    :param obj_id:
    :return: List of all nodes matching provided ID
    """
    return browser.find_elements_by_id(obj_id)


def find_by_xpath(browser, selector):
    """
    Finds elements by xpath
    :param selector: xpath string
    :return: returns a list of all matching selenium objects
    """
    return browser.find_elements_by_xpath(selector)


def find_by_class(browser, selector):
    """
    Finds elements by class name
    :param selector: Class selector of html obj
    :return: returns a list of all matching selenium objects
    """
    return browser.find_elements_by_class_name(selector)


def find_by_css(browser, selector):
    """
    Finds nodes by css selector
    :param selector: CSS selector of html node obj
    :return: returns a list of all matching selenium objects
    """
    return browser.find_elements_by_css_selector(selector)


def main_window(browser):
    """
    Closes current window and switches focus back to main window
    :return: None
    """
    try:
        for i in range(1, len(browser.window_handles)):
            browser.switch_to.window(browser.window_handles[i])
            browser.close()
    except WebDriverException:
        logging.error('Error when switching to main_window')
    finally:
        browser.switch_to.window(browser.window_handles[0])


def latest_window(browser):
    """
    Switches to newest open window
    :return:
    """
    browser.switch_to.window(browser.window_handles[-1])


def screenshot(browser, selector):
    """
    Snaps screenshot of webpage when error occurs
    :param selector: The name, ID, class, or other attribute of missing node object
    :return: None
    """
    screenshot_file_name = f'{datetime.now().strftime("%Y%m%d%H%M%S")}_{selector}.png'
    screenshot_file_path = os.path.join('logs', screenshot_file_name)
    logging.error(f'{selector} cannot be located. Saving screenshot at {screenshot_file_path}')
    browser.save_screenshot(screenshot_file_path)
