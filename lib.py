from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from colorama import Fore, Style
import time

# Either save_json, save_screenshot, or both must be True; they can't both be False
config = {
    "youtube_video": "https://www.youtube.com/watch?v=uac9vWs3Lc0", # Youtube video URL
    "element_timeout": 30, # Default timeout in seconds when searching for an element
    "reply_timeout": 10, # Default timeout in seconds when checking if replies have loaded
    "save_json": True, # Enable this if you want the comments to be stored in data.json
    "save_screenshot": False, # Whether to save screenshots to screenshots folder or not take them at all
    "screenshot_bg_color": (15, 15, 15), # Background color of the screenshot, default #0f0f0f or 15, 15, 15 - youtube dark mode background color
    "max_comments": 0, # Max comments to parse, set to 0 to parse every comment
    "headless": False, # Run headless mode on the browser - open the browser in the background
    "force_dark_theme": False, # Force dark theme on pages for screenshots, headless doesn't detect system theme

    # [ms] = Current timestamp in milliseconds
    # [guid] = Random GUID
    # [id] - Selenium internal ID for elements, always unique but long like guid
    
    # * Following requires save_json to also be enabled:
    # [author] = Author username (removes the @ as a safeguard)
    # [date] = Comment published ago

    # e.g. [ms]-[guid]
    "screenshot_name_format": "[author],[guid]" # WARNING! You should always put [guid] or [id] somewhere in the name to prevent duplicates.
    # Also, try not to make the path to the file too long. Windows may prevent the file from being added if it is.
}

def get_current_ms():
    """
    :return: Current timestamp in milliseconds using the time module in python
    """
    return round(time.time() * 1000)

def exit_failure(msg: str = None, code: int | str = None):
    """
    Exits the code alongside an optional custom message and/or code.
    """
    if isinstance(msg, str): print("[FATAL] " + Fore.RED + Style.BRIGHT + msg)
    exit(code or None)

def hide_element(driver: ChromiumDriver, element: WebElement):
    if element == None: return
    driver.execute_script("arguments[0].style.display = 'none';", element)

def locate_element(driver: ChromiumDriver, locator: tuple[str, str], timeout: int = config["element_timeout"], parent: WebElement = None) -> WebElement:
    """
    Locate an element on the page or within a parent element.
    
    :param locator: By strategy (param 1) and value (param 2) inside a tuple
    :param timeout: How much maximum time is given for locating an element (default 60s)
    :param parent: WebElement to search in. None = entire page
    :return: WebElement or None if locate_element times out
    """
    print("Locating element with locator", locator)
    start_time = get_current_ms()
    while True:
        try:
            context = parent if parent else driver

            # Wait until the element exists
            element = WebDriverWait(context, timeout).until(EC.presence_of_element_located(locator))
            if element:
                width, height = element.size["width"], element.size["height"]
                if width > 0 and height > 0: # Check that the width and height of the element is > 0 so that it doesn't error when screenshotting
                    return element
        except Exception:
            pass # Do nothing

        # Check if timed out by checking if the difference between now and when the function was ran is greater than timeout * 1000 (sec -> ms)
        if get_current_ms() - start_time > timeout * 1000:
            break # Stop running the "while True" loop

    print(Fore.RED + "Could not find element")
    return None

def get_comment_elements(driver: ChromiumDriver, parentComment: WebElement, isReply: bool = False):
    commentInfo = locate_element(driver, locator = (By.ID, "comment"), parent = parentComment, timeout = 1) if isReply == False else parentComment
    commentInfoBody = None
    commentMain = None
    commentAuthor = None
    commentExpander = None

    # Find elements in the located commentInfo
    try:
        commentInfoBody = commentInfo.find_element(by = By.ID, value = "body")
        commentMain = commentInfoBody.find_element(by = By.ID, value = "main")
        commentAuthor = commentInfoBody.find_element(by = By.ID, value = "author-thumbnail")
        commentExpander = commentMain.find_element(by = By.ID, value = "expander")
    except Exception:
        pass # Do nothing

    return commentInfo, commentInfoBody, commentMain, commentAuthor, commentExpander

def get_comment_json(commentMain: WebElement, commentAuthor: WebElement, commentExpander: WebElement):
    """
    Get the JSON data of a comment or reply.
    
    :return: (tuple) Author Profile Image, Author Name, Comment Text, Comment Publish Date, Like Count, Heart, Pin, Author Badge SVG
    """
    aImg = "" # Author Profile Image
    aName = "" # Author Name
    cTxt = "" # Comment Text
    cPublished = "" # Comment Publish Date

    cLikes = "" # Like Count (text because API would make it take longer, same reason why theres no dislikes)
    cHeart = False # Was the comment hearted by the creator?
    cPinned = "" # Did the creator pin the comment? e.g. "Pinned by YouTube Channel"
    aBadgeSVG = None # SVG element in text if the author of the comment has a badge e.g. verified, music, subscription - otherwise None
    aCreator = False # Whether the comment author has a creator badge around their name (made the video)

    if commentAuthor:
        # Author Name & Profile Picture Image
        try:
            pfpButton = commentAuthor.find_element(by = By.TAG_NAME, value = "a")
            aName = pfpButton.get_attribute("aria-label") # Author Name

            pfpShadow = pfpButton.find_element(by = By.TAG_NAME, value = "yt-img-shadow")
            pfpImg = pfpShadow.find_element(by = By.TAG_NAME, value = "img")

            aImg = pfpImg.get_attribute("src") # Profile Picture Image
        except Exception:
            pass # Do nothing

    if commentMain:
        # Comment Text
        if commentExpander:
            try:
                # commentExpander and repliesExpander are not the same!
                content = commentExpander.find_element(by = By.ID, value = "content")
                contentText = content.find_element(by = By.ID, value = "content-text")
                text = contentText.find_element(by = By.TAG_NAME, value = "span")

                cTxt = text.get_attribute("innerHTML")
            except Exception:
                pass # Do nothing

    # Likes & Heart
    try:
        actionButtons = commentMain.find_element(by = By.ID, value = "action-buttons")
        toolbar = actionButtons.find_element(by = By.ID, value = "toolbar")

        # Heart
        try:
            creatorHeart = toolbar.find_element(by = By.ID, value = "creator-heart") # Appears even if the comment isn't hearted
            creatorHeart.find_element(by = By.TAG_NAME, value = "ytd-creator-heart-renderer") # Only appears if the comment was actually hearted

            cHeart = True
        except Exception:
            pass

        voteCount = toolbar.find_element(by = By.ID, value = "vote-count-middle")

        cLikes = voteCount.get_attribute("innerHTML").strip()
    except Exception:
        pass # Do nothing

    # Published Time, Pin, Author Badge, & Creator Badge
    try:
        header = commentMain.find_element(by = By.ID, value = "header")

        # Pin
        try:
            pinnedBadge = header.find_element(by = By.ID, value = "pinned-comment-badge")
            pinnedRenderer = pinnedBadge.find_element(by = By.TAG_NAME, value = "ytd-pinned-comment-badge-renderer")
            pinnedText = pinnedRenderer.find_element(by = By.ID, value = "label")

            cPinned = pinnedText.get_attribute("innerHTML")
        except Exception:
            pass # Do nothing

        headerAuthor = header.find_element(by = By.ID, value = "header-author")

        # Badge & Creator Badge
        try:
            badge = headerAuthor.find_element(by = By.ID, value = "author-comment-badge")
            badgeRenderer = badge.find_element(by = By.TAG_NAME, value = "ytd-author-comment-badge-renderer")

            # Creator Badge
            try:
                aCreator = badgeRenderer.get_attribute("creator") == "true"
            except Exception:
                pass # Do nothing

            badgeIcon = badgeRenderer.find_element(by = By.TAG_NAME, value = "yt-icon") # or by = By.ID, value = icon
            shape = badgeIcon.find_element(by = By.TAG_NAME, value = "span")
            container = shape.find_element(by = By.TAG_NAME, value = "div")
            svg = container.find_element(by = By.TAG_NAME, value = "svg")

            aBadgeSVG = svg.get_attribute("outerHTML")
        except Exception:
            pass # Do nothing

        publishedTime = headerAuthor.find_element(by = By.ID, value = "published-time-text")
        date = publishedTime.find_element(by = By.TAG_NAME, value = "a")

        cPublished = date.get_attribute("innerHTML").strip()
    except Exception:
        pass # Do nothing

    return aImg, aName, cTxt, cPublished, cLikes, cHeart, cPinned, aBadgeSVG, aCreator