import shutil
from enum import Enum
import logging
import os
import platform
import zipfile
from typing import Optional

import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webdriver import WebDriver

DRIVERS_PATH = os.path.join(os.path.dirname(__file__), "drivers")


class Driver(Enum):
    EDGE = "msedgedriver"
    CHROME = "chromedriver"


def spoof_browser(driver: Driver, headless: bool, drivers_path: str = DRIVERS_PATH, allow_screenshots: bool = False) -> WebDriver:
    """
    Returns appropriate WebDriver...
    CHROME device is spoofed with specified user agent for mobile
    """
    if driver_update_available(driver, drivers_path):
        download_driver(driver, drivers_path)

    browser = _get_webdriver(driver, headless, drivers_path)

    browser.set_page_load_timeout(30)

    if not allow_screenshots:
        def do_nothing(*args, **kwargs):
            pass
        browser.save_screenshot = do_nothing

    return browser


def _get_webdriver(driver: Driver, headless: bool, drivers_path: str):
    options = ChromeOptions() if driver == Driver.CHROME else EdgeOptions()
    options.headless = headless
    # This stops us from failing the bluetooth check, other weird errors due to headless and random logging
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver_path = os.path.join(drivers_path, _get_driver_executable_name(driver))
    if driver == Driver.EDGE:
        # Open up Edge on desktop (no spoofing user agent required)
        options.use_chromium = True
        browser = webdriver.Edge(options=options, service=Service(driver_path))
    elif driver == Driver.CHROME:
        # Spoof user agent as phone (Google 'my user agent' via personal mobile device for the exact agent string)
        # TODO: The user agent needs to be updated every time my phone updates chrome...
        options.add_argument('--user-agent="Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.98 Mobile Safari/537.36"')
        browser = webdriver.Chrome(options=options, service=Service(driver_path))
    else:
        raise Exception(f"Unsupported driver: {driver}")

    return browser


def driver_update_available(driver: Driver, drivers_path: str = DRIVERS_PATH) -> bool:
    """Returns True if no downloaded driver exists which matches latest release"""
    if not os.path.exists(os.path.join(drivers_path, _get_driver_executable_name(driver))):
        return True

    installed = _get_downloaded_version(driver, drivers_path)
    return not installed == _get_latest_version(driver)


def _get_platform_ext() -> str:
    system = platform.system()

    if system == "Windows":
        system_ext = "win32"  # NOTE: win is the OS and 32 is the architecture
    elif system == "Darwin":
        system_ext = "mac64"
    elif system == "Linux":
        system_ext = "linux64"
    else:
        raise Exception(f"Unknown platform system: {system}")

    return system_ext


def _get_driver_executable_name(driver: Driver) -> str:
    system = platform.system()
    executable_ext = ".exe" if system == "Windows" else ""
    return f"{driver.value}{executable_ext}"


def _get_latest_version(driver: Driver) -> str:
    """Query API for latest version of driver"""
    url = ("https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
           if driver == Driver.CHROME else
           "https://msedgedriver.azureedge.net/LATEST_STABLE")

    r = requests.get(url)
    if r.encoding is None:
        r.encoding = "utf_16"  # msedgedriver download doesn't set it's encoding... this prevents unwanted logs

    latest_version = r.text.strip()

    return latest_version


def _get_downloaded_version(driver: Driver, drivers_path: str = DRIVERS_PATH) -> Optional[str]:
    """Returns None if no version is found, otherwise reads and returns version"""
    version_path = os.path.join(drivers_path, f"{driver.value}_version.txt")
    if os.path.exists(version_path):
        with open(os.path.join(version_path), "r") as version_file:
            installed = version_file.read()
            return installed

    return None


def download_driver(driver: Driver, drivers_path=DRIVERS_PATH):
    """Deletes any existing Driver, downloads driver to drivers_path. Writes {driver}_version.txt file for reference"""
    latest_version = _get_latest_version(driver)
    driver_file_name = _get_driver_executable_name(driver)
    logging.info(f"Downloading latest {driver_file_name} version: {latest_version}")

    driver_file_path = os.path.join(drivers_path, driver_file_name)
    backup_driver_file_path = os.path.join(drivers_path, f"old_{driver_file_name}")
    if os.path.exists(driver_file_path):
        _remove_file_if_exists(backup_driver_file_path)
        os.rename(driver_file_path, backup_driver_file_path)

    try:
        system_ext = _get_platform_ext()
        url = (f"https://chromedriver.storage.googleapis.com/{latest_version}/{driver.value}_{system_ext}.zip"
               if driver == Driver.CHROME else
               f"https://msedgedriver.azureedge.net/{latest_version}/{driver.value.replace('ms', '')}_{system_ext}.zip")

        response = requests.get(url, stream=True)

        zip_file_path = os.path.join(os.path.dirname(driver_file_path), os.path.basename(url))
        with open(zip_file_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=512):
                if chunk:  # filter out keep alive chunks
                    handle.write(chunk)

        extracted_dir = os.path.splitext(zip_file_path)[0]
        with zipfile.ZipFile(zip_file_path, "r") as zip_file:
            zip_file.extractall(extracted_dir)
        os.remove(zip_file_path)

        # Copy driver out of extracted directory and delete extracted directory
        assert driver_file_name in os.listdir(extracted_dir), f"{driver_file_path} not in {os.listdir(extracted_dir)}"
        os.rename(os.path.join(extracted_dir, driver_file_name), driver_file_path)
        shutil.rmtree(extracted_dir)

        os.chmod(driver_file_path, 0o755)
        _ = _get_webdriver(driver, True, drivers_path)  # Test that we can launch a webdriver with new driver executable

        # Update the versions file with new version
        with open(os.path.join(os.path.dirname(driver_file_path), f"{driver.value}_version.txt"), "w") as version_file:
            version_file.write(latest_version)

        _remove_file_if_exists(backup_driver_file_path)
    except Exception as e:
        if os.path.exists(backup_driver_file_path):
            logging.info(f"Error occurred downloading driver `{e}` -> rolling back to existing driver")
            _remove_file_if_exists(driver_file_path)

            os.rename(backup_driver_file_path, driver_file_path)
        else:
            raise


def _remove_file_if_exists(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)
