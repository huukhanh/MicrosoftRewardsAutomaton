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
Provides helpers for selenium with error handling
"""


def wait_until_(browser, condition_func, by_, selector, time_to_wait=10, poll_frequency=0.5, ignore_timeout=True):
    """
    Waits time_to_wait seconds for element to meet specified condition

    :param browser:  web driver
    :param condition_func:  selenium.webdriver.support.expected_conditions class implementation to wait for
    :param by_:  BY module args to pick a selector
    :param selector: string of xpath, css_selector or other
    :param time_to_wait: Int time to wait
    :param ignore_timeout: if True, ignores TimeoutException (doesn't require condition to be met)
    :return: None
    """
    try:
        return WebDriverWait(browser, time_to_wait, poll_frequency).until(condition_func((by_, selector)))
    except TimeoutException:
        if not ignore_timeout:
            logging.exception(f'{selector} element conditon ({condition_func}) not met. Timeout Exception')
            screenshot(browser, selector)
            raise
    except UnexpectedAlertPresentException:
        browser.switch_to.alert.dismiss()
        logging.exception('Unexpected Alert Exception')
        screenshot(browser, selector)
        browser.refresh()
        raise
    except WebDriverException:
        logging.exception(f'Webdriver Error for {selector} object')
        screenshot(browser, selector)
        raise


def wait_until_clickable(browser, by_, selector, time_to_wait=10, ignore_timeout=False, **kwargs):
    """
    Wrapper for wait_until_ for clickable condition. By default, allows timeout -> requiring condition to be met.
    """
    func = ec.element_to_be_clickable
    return wait_until_(browser, func, by_, selector, time_to_wait=time_to_wait, ignore_timeout=ignore_timeout, **kwargs)


def wait_until_visible(browser, by_, selector, time_to_wait=10, ignore_timeout=True, **kwargs):
    """
    Wrapper for wait_until_ for visible condition. By default, ignores timeout -> not requiring condition to be met.
    """
    func = ec.visibility_of_element_located
    return wait_until_(browser, func, by_, selector, time_to_wait=time_to_wait, ignore_timeout=ignore_timeout, **kwargs)


def click_element(browser, by_, selector, ignore_no_such_element=False) -> bool:
    try:
        browser.find_element(by_, selector).click()
        return True
    except (ElementNotVisibleException, ElementClickInterceptedException, ElementNotInteractableException):
        logging.exception(f'Found {selector} element by {by_}, but it is not visible or interactable. Attempting JS Click', exc_info=False)
        return browser.js_click(browser.find_element(by_, selector))
    except NoSuchElementException:
        if not ignore_no_such_element:
            logging.exception(f'Element not found when searched for {selector} by {by_}.', exc_info=False, )
            browser.screenshot(selector)
            browser.refresh()
    except WebDriverException:
        logging.exception(f'Webdriver Error in clicking. Searched by {by_} for {selector}.')
    finally:
        return False


def js_click(browser, element):
    """Click any given element"""
    try:
        browser.execute_script("arguments[0].click();", element)
        return True
    except Exception:
        logging.exception(f'Exception when JS click')


def send_key(browser, by_, selector, key, ignore_no_such_element=False) -> bool:
    try:
        browser.find_element(by_, selector).send_keys(key)
        return True
    except (ElementNotVisibleException, ElementClickInterceptedException, ElementNotInteractableException):
        logging.exception(msg=f'Found {selector} element by {by_}, but it is not visible or interactable.', exc_info=False)
    except NoSuchElementException:
        if not ignore_no_such_element:
            logging.exception(f'Element not found when searched for {selector} by {by_}.', exc_info=False, )
            browser.screenshot(selector)
            browser.refresh()
    except WebDriverException:
        logging.exception(msg=f'Webdriver Error in sending key. Searched by {by_} for {selector}')
    finally:
        return False


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
    screenshot_file_path = os.path.join(os.path.dirname(__file__), 'logs', screenshot_file_name)
    logging.error(f'{selector} cannot be located. Saving screenshot at {screenshot_file_path}')
    browser.save_screenshot(screenshot_file_path)
