import time

from selenium.common.exceptions import WebDriverException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.events import EventFiringWebDriver
from selenium.webdriver.support.events import AbstractEventListener

import settings
import image
import logger

LOGGER = logger.Logger(name=__name__).get()


class ScreenshotListener(AbstractEventListener):
    """Automatically screenshots on error, useful for phantomjs errors
    """

    def on_exception(self, exception, driver):
        # TODO: Put exception images with where the build is running
        screenshot_name = "phantomjs_exception_{}.png".format(
            logger.generate_timestamp())
        driver.get_screenshot_as_file(screenshot_name)
        LOGGER.error("Exception screenshot saved as '%s'" % screenshot_name)


class WebDriverType(object):
    PHANTOM_JS = "PHANTOM_JS"
    REMOTE = "REMOTE"


def setup_webdriver(drivertype, capabilities=None, screenshot_on_exception=False):
    if drivertype is WebDriverType.PHANTOM_JS:
        driver = __setup_phantomjs_webriver(screenshot_on_exception)
    elif drivertype is WebDriverType.REMOTE:
        driver = __setup_remote_webdriver(capabilities=capabilities)
    else:
        raise ValueError('Unsupported `drivertype`!  see WebDriverType')

    driver.implicitly_wait(20)
    return driver


def __setup_phantomjs_webriver(screenshot_on_exception=False):
    driver = webdriver.PhantomJS()
    if screenshot_on_exception:
        driver = EventFiringWebDriver(driver, ScreenshotListener())
    driver.set_window_size(1920, 1080)
    return driver


def __setup_remote_webdriver(capabilities):
    if not capabilities:
        raise ValueError("capabilities must be defined for remote runs!")

    # Update capabilities
    capabilities['public'] = 'share'
    user = settings.DEFAULT.get_saucelabs_user()
    key = settings.DEFAULT.get_saucelabs_key()
    remote_webdriver_url = "http://{}:{}@ondemand.saucelabs.com:80/wd/hub".format(
        user, key)
    driver = webdriver.Remote(
        command_executor=remote_webdriver_url,
        desired_capabilities=capabilities)
    remote_url = "http://www.saucelabs.com/jobs/%s" % driver.session_id
    LOGGER.debug("Starting remote webdriver job: %s\n%s",
                 remote_url, capabilities)
    return driver


def check_browser_errors(driver):
    """
    Checks browser for errors, returns a list of errors
    This only works for Chrome
    :param driver:
    :return:
    """
    try:
        browserlogs = driver.get_log('browser')
    except (ValueError, WebDriverException) as e:
        LOGGER.debug("Could not get browser logs for driver %s due to exception: %s",
                     driver, e)
        return []

    errors = []
    for entry in browserlogs:
        if entry['level'] == 'SEVERE':
            errors.append(entry)
    return errors


def __wait_until_element_disappears(driver, locator):
    try:
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located(locator=locator))
    except Exception as e:
        # This happens all the time with phantomjs driver
        LOGGER.debug('Exception while wait_until_element_disappears: %s', e)
        return


def wait_for_tag_load(driver, wait_time=3):
    # TODO: implementation is specific to PaperG creatives
    # Wait until the load spinner goes away
    load_spinner_locator = (By.CSS_SELECTOR, "img[class*='pl-loader-'")
    __wait_until_element_disappears(driver=driver,
                                    locator=load_spinner_locator)

    # Account for animation time and add some buffer for good measure
    time.sleep(settings.TAG_ANIMATION_TIME)
    time.sleep(wait_time)


def display_tag(driver, tag, wait_for_load=True, wait_time=3):
    driver.get("about:blank")  # Clear the page first
    script = _make_script(tag)
    driver.execute_script(script)

    if wait_for_load:
        wait_for_tag_load(driver, wait_time)

    errors = check_browser_errors(driver)
    return errors


def _make_script(tag):
    script = "document.body.innerHTML=\"{}\";".format(tag) \
        .replace('\n', '').replace('\r', '').rstrip()
    LOGGER.debug("_make_script: %s", script)
    return script


def screenshot_element(driver, element, output_path):
    """Take a screenshot of a specific webelement
    """
    size = element.size
    location = element.location

    left = location['x']
    top = location['y']
    right = location['x'] + size['width']
    bottom = location['y'] + size['height']
    cropbox = (left, top, right, bottom)

    f = _screenshot(driver, output_path)
    img = image.crop(f, cropbox)
    return img


def _screenshot(driver, output_path):
    if not output_path.endswith('.png'):
        output_path += ".png"
    LOGGER.debug("capturing screenshot to %s", output_path)
    driver.get_screenshot_as_file(output_path)
    return output_path
