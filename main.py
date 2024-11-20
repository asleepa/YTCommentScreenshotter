# region introduction
"""
    YT (YouTube) Comments Screenshotter v1.00
    A side project which saves each comment of a YouTube video in screenshots and data.json.
    
    @asleepa | Discord
    My contacts are above if you need assistance.

    This code has been open-sourced for educational purposes.
    The code seen was originally used for a DougDougDoug video, hence the youtube_video URL.
"""

from colorama import Fore, Style, init
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from PIL import Image
import os
import io
import uuid
import time
import json

# Either save_json, save_screenshot, or both must be True; they can't both be False
config = {
    "youtube_video": "https://www.youtube.com/watch?v=S32kpwRKJgI", # Youtube video URL
    "element_timeout": 30, # Default timeout in seconds when searching for an element
    "save_json": True, # Enable this if you want the comments to be stored in data.json
    "save_screenshot": True, # Whether to save screenshots to screenshots folder or not take them at all
    "screenshot_bg_color": (15, 15, 15), # Background color of the screenshot, default #0f0f0f or 15, 15, 15 - youtube dark mode background color
    "max_comments": 0, # Max comments to parse, set to 0 to parse every comment
    "headless": False, # Run headless mode on the browser - open the browser in the background
    "force_dark_theme": False # Force dark theme on pages for screenshots, headless doesn't detect system theme
}

#endregion
#region functions

init(autoreset = True)

def get_current_ms():
    """
    :return: Current timestamp in milliseconds using the time module in python
    """
    return round(time.time() * 1000)

# I hate using pure uuid4, I know the chances are impossibly low but I just have to append the timestamp, too scary
def screenshot_name():
    """
    Generate a random name to use for screenshots in the screenshots folder. This is not the path name.
    
    :return: A string in the format (current timestamp in milliseconds)-(random uuid4)
    """
    return f"{get_current_ms()}-" + str(uuid.uuid4())

# Code is sys._ExitCode but I'm not importing allat
def exit_failure(msg: str = None, code: any = None):
    """
    Exits the code alongside an optional custom message and/or code.
    """
    if isinstance(msg, str): print("[FATAL] " + Fore.RED + Style.BRIGHT + msg)
    exit(code if code != None else None)

def hide_element(element):
    if element == None: return
    driver.execute_script("arguments[0].style.display = 'none';", element)

# If you can't understand this I think it's better off that way
if config["save_json"] == False and config["save_screenshot"] == False: exit_failure("save_json or save_screenshot needs to be True")

options = webdriver.ChromeOptions()
if config["headless"] == True:
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu") # If you use headless without --disable-gpu you're weird
if config["force_dark_theme"] == True: options.add_argument("--force-dark-mode")

driver = webdriver.Chrome(options)
driver.get(url = config["youtube_video"])

def locate_element(locator: tuple[str, str], timeout: int = config["element_timeout"], parent = None):
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

def get_comment_elements(parentComment, isReply: bool = False):
    commentInfo = locate_element(locator = (By.ID, "comment"), parent = parentComment, timeout = 1) if isReply == False else parentComment
    commentInfoBody = None
    commentMain = None
    commentAuthor = None
    commentExpander = None

    # If parent is None it's going to search the entire page, so this is a safeguard since im lazy
    try:
        commentInfoBody = commentInfo.find_element(by = By.ID, value = "body")
        commentMain = commentInfoBody.find_element(by = By.ID, value = "main")
        commentAuthor = commentInfoBody.find_element(by = By.ID, value = "author-thumbnail")
        commentExpander = commentMain.find_element(by = By.ID, value = "expander")
    except Exception:
        pass # Do nothing

    return commentInfo, commentInfoBody, commentMain, commentAuthor, commentExpander

def get_comment_json(commentMain, commentAuthor, commentExpander):
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
    cPinned = False # Did the creator pin the comment?
    aBadgeSVG = None # SVG element in text if the author of the comment has a badge e.g. verified, music, subscription - otherwise None

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

    # Published Time, Pin, & Author Badge
    try:
        header = commentMain.find_element(by = By.ID, value = "header")

        # Pin
        try:
            pinnedBadge = header.find_element(by = By.ID, value = "pinned-comment-badge")
            pinnedBadge.find_element(by = By.TAG_NAME, value = "ytd-pinned-comment-badge-renderer")

            cPinned = True
        except Exception:
            pass # Do nothing

        headerAuthor = header.find_element(by = By.ID, value = "header-author")

        # Badge
        try:
            badge = headerAuthor.find_element(by = By.ID, value = "author-comment-badge")
            badgeRenderer = badge.find_element(by = By.TAG_NAME, value = "ytd-author-comment-badge-renderer")
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

    return aImg, aName, cTxt, cPublished, cLikes, cHeart, cPinned, aBadgeSVG

#endregion
#region code

# YouTube doesn't necessarily respond to system themes like other sites so we'll set it ourselves alongside --force-dark-mode
if config["force_dark_theme"] == True:
    body = locate_element(locator = (By.TAG_NAME, "body"))

    if body != None:
        driver.execute_script("""
            document.cookie = "PREF=f6=400; path=/; domain=.youtube.com";
            location.reload();
        """)

commentsContainer = locate_element(locator = (By.ID, "comments"))
if commentsContainer != None: ActionChains(driver).move_to_element(commentsContainer).perform() # Scroll/teleport to comments container to load it

commentSection = None
comments = None

if commentsContainer != None: commentSection = locate_element(locator = (By.ID, "sections"), parent = commentsContainer)
if commentSection != None: comments = locate_element(locator = (By.ID, "contents"), parent = commentSection)

if comments == None: exit_failure("Comment section could not be found")

# execute_script executes code into the developer console, be careful
try:
    popupContainer = driver.find_element(by = By.TAG_NAME, value = "ytd-popup-container")
    hide_element(popupContainer) # Hide the YouTube popup container from interfering with screenshots
except Exception:
    pass # Do nothing

try:
    topbar = driver.find_element(by = By.ID, value = "masthead-container")
    hide_element(topbar) # Incase the comment appears at the top, hide the topbar
except Exception:
    pass # Do nothing

try:
    recommended = driver.find_element(by = By.ID, value = "secondary")
    hide_element(recommended) # Hide recommended videos, chat, etc. on the right
except Exception:
    pass # Do nothing

# I DIDN'T KNOW ELEMENT.ID WAS INTERNAL I WAS DOING IT WRONG THE ENTIRE TIME USE GET_ATTRIBUTE NOOOO
try:
    primary = driver.find_element(by = By.ID, value = "primary-inner")
    player = primary.find_element(by = By.ID, value = "player")
    below = primary.find_element(by = By.ID, value = "below")

    hide_element(player) # More room for comments which appear at the top

    belowItems = below.find_elements(by = By.XPATH, value = "./child::*")

    for element in belowItems:
        if element.get_attribute("id") == "comments": continue
        hide_element(element)
except Exception:
    pass # Do nothing

try:
    commentsHeader = commentSection.find_element(by = By.ID, value = "header")
    hide_element(commentsHeader) # Hide the comments header (add a comment, sort by, comment count etc)
except Exception:
    pass # Do nothing

commentsParsed = 0
pagesParsed = 0

while True if config["max_comments"] < 1 else commentsParsed < config["max_comments"]:
    # We're not actually going to check for if the spinner is there because sometimes it appears despite comments being loaded
    commentList = None
    try:
        commentList = comments.find_elements(by = By.TAG_NAME, value = "ytd-comment-thread-renderer")
    except Exception:
        pass # Do nothing

    if commentList == None or len(commentList) < 1: continue # Redo the loop because comments are still not loaded

    for comment in commentList:
        if "display: none" in comment.get_attribute("style"): continue
        commentInfo, commentInfoBody, commentMain, commentAuthor, commentExpander = get_comment_elements(comment)
        commentReplies = locate_element(locator = (By.ID, "replies"), parent = comment, timeout = 1)

        if commentExpander:
            try:
                readMoreButton = commentExpander.find_element(by = By.ID, value = "more")
                if readMoreButton.get_attribute("hidden") != "true":
                    driver.execute_script("arguments[0].click();", readMoreButton)
                    time.sleep(0.05)
            except Exception:
                pass # Do nothing

        repliesRenderer = None
        repliesExpander = None
        repliesExpanderHeader = None
        
        cReplies = []
        cReplyBinaries = []

        if commentReplies:
            try:
                repliesRenderer = commentReplies.find_element(by = By.TAG_NAME, value = "ytd-comment-replies-renderer")
                repliesExpander = repliesRenderer.find_element(by = By.ID, value = "expander")
                repliesExpanderContents = repliesExpander.find_element(by = By.ID, value = "expander-contents")

                for element in repliesExpander.find_elements(by = By.TAG_NAME, value = "div"):
                    if "expander-header" in element.get_attribute("class"):
                        repliesExpanderHeader = element

                moreReplies = None
                for element in repliesExpanderHeader.find_elements(by = By.TAG_NAME, value = "div"):
                    if "more-button" in element.get_attribute("class"):
                        moreReplies = element

                if moreReplies.get_attribute("hidden") != "true":
                    driver.execute_script("arguments[0].click();", moreReplies)

                contents = repliesExpanderContents.find_element(by = By.ID, value = "contents")
                continueRepliesRenderer = None

                try:
                    continueRepliesRenderer = contents.find_element(by = By.TAG_NAME, value = "ytd-continuation-item-renderer")
                except Exception:
                    pass # Do nothing

                repliesParsed = 0
                replyPages = 1

                while True:
                    if continueRepliesRenderer != None:
                        # Wait until the spinner appears, its unrealistic that it'd instantly load
                        # It'd also probably skip if it only checked if it was hidden
                        while True:
                            try:
                                spinner = continueRepliesRenderer.find_element(by = By.ID, value = "spinner")
                                if spinner.get_attribute("hidden") != "true": break # Break if the spinner is visible
                            except Exception:
                                pass # Do nothing

                        # Wait until replies are finished loading
                        while True:
                            try:
                                spinner = continueRepliesRenderer.find_element(by = By.ID, value = "spinner")
                                if spinner.get_attribute("hidden") == "true": break # Break if the spinner is hidden
                            except Exception:
                                break # The spinner doesn't exist

                    time.sleep(0.1)
                    replyList = contents.find_elements(by = By.TAG_NAME, value = "ytd-comment-view-model")

                    for reply in replyList:
                        if "display: none" in reply.get_attribute("style"): continue
                        _, _, replyMain, replyAuthor, replyExpander = get_comment_elements(parentComment = reply, isReply = True)

                        if replyExpander:
                            try:
                                readMoreButton = replyExpander.find_element(by = By.ID, value = "more")
                                if readMoreButton.get_attribute("hidden") != "true":
                                    driver.execute_script("arguments[0].click();", readMoreButton)
                                    time.sleep(0.05)
                            except Exception:
                                pass # Do nothing

                        # Scroll until the comment is vertically centered so it gets a good view of the reply.
                        driver.execute_script("arguments[0].scrollIntoView({ block: 'center' });", reply)

                        if config["save_json"] == True:
                            # Get the reply's stats
                            aImg, aName, cTxt, cPublished, cLikes, cHeart, _, aBadgeSVG = get_comment_json(replyMain, replyAuthor, replyExpander)

                            newReply = {
                                "Content": cTxt,
                                "Published": cPublished,
                                "Author": {
                                    "Image": aImg,
                                    "Name": aName,
                                    "Badge": aBadgeSVG
                                },
                                "Stats": {
                                    "Likes": cLikes,
                                    "Heart": cHeart
                                }
                            }

                            cReplies.append(newReply)

                        if config["save_screenshot"] == True:
                            cReplyBinaries.append(reply.screenshot_as_png)

                        hide_element(reply)

                        repliesParsed += 1
                        print(f"Saved reply {repliesParsed}, page {replyPages} of comment {commentsParsed + 1}")
                    try:
                        continueRepliesRenderer = contents.find_element(by = By.TAG_NAME, value = "ytd-continuation-item-renderer")
                        continueRepliesButton = continueRepliesRenderer.find_element(by = By.ID, value = "button")
                        buttonRenderer = continueRepliesButton.find_element(by = By.TAG_NAME, value = "ytd-button-renderer")
                        buttonShape = buttonRenderer.find_element(by = By.TAG_NAME, value = "yt-button-shape")
                        button = buttonShape.find_element(by = By.TAG_NAME, value = "button")

                        driver.execute_script("arguments[0].click();", button)
                    except NoSuchElementException:
                        break

                    replyPages += 1

            except Exception as e:
                print(Fore.RED + "[ERROR] An exception occured while checking a comment's replies:", e)
                pass # Do nothing - also probably no replies if theres no button

        def save_json():
            """
            Saves the comment's data into data.json.
            """

            # Get the comment's stats
            aImg, aName, cTxt, cPublished, cLikes, cHeart, cPinned, aBadgeSVG = get_comment_json(commentMain, commentAuthor, commentExpander)

            # Create the dictionary to append to "comments" in data.json using the variables we set earlier
            newComment = {
                "Content": cTxt,
                "Published": cPublished,
                "Author": {
                    "Image": aImg,
                    "Name": aName,
                    "Badge": aBadgeSVG
                },
                "Stats": {
                    "Likes": cLikes,
                    "Heart": cHeart,
                    "Pinned": cPinned
                },
                "Replies": cReplies
            }

            def write_json():
                """
                Writes comment to data.json.
                """

                data = None
                with open("data.json", "r") as file:
                    data = json.load(file)

                if data == None: return
                data["comments"].append(newComment)

                with open("data.json", "w") as file:
                    json.dump(data, file, indent = 1)

            write_json()
            print(Fore.GREEN + f"[SUCCESS] Wrote new comment entry for comment {commentsParsed + 1} to data.json")

        def save_screenshot():
            """
            Saves the comment's binary PNG data as a PNG file in the screenshots folder.
            """
            if commentInfo == None: return

            start_time = get_current_ms()
            print(Fore.BLUE + "Creating screenshot")

            screenshotName = screenshot_name()

            # Change this in a pull request in the future if the margin is changed on YouTube please
            marginY = 8 # The Y pixels of margin at the bottom of each comment and reply, seperating them

            binary = commentInfo.screenshot_as_png # If you were to screenshot comment, it'd include a small part of the replies - we do not want this
            img = Image.open(fp = io.BytesIO(initial_bytes = binary))
            
            finalImg = img
            if repliesExpanderHeader:
                imgW, imgH = img.size

                expanderBinary = repliesExpanderHeader.screenshot_as_png
                expanderImg = Image.open(fp = io.BytesIO(initial_bytes = expanderBinary))

                expanderW, expanderH = expanderImg.size

                finalImg = Image.new("RGB", (max(imgW, expanderW), imgH + expanderH), color = config["screenshot_bg_color"])
                finalImg.paste(img, (0, 0))
                finalImg.paste(expanderImg, ((max(imgW, expanderW) - expanderW, imgH)))

            for replyBinary in cReplyBinaries:

                # Append reply PNG binaries to the bottom of the final image/screenshot
                finalW, finalH = finalImg.size

                replyImg = Image.open(fp = io.BytesIO(initial_bytes = replyBinary))
                replyW, replyH = replyImg.size

                newImg = Image.new("RGB", (max(finalW, replyW), finalH + replyH + marginY), color = config["screenshot_bg_color"])
                newImg.paste(finalImg, (0, 0))
                newImg.paste(replyImg, (max(finalW, replyW) - replyW, finalH))

                finalImg = newImg

            os.makedirs(name = "screenshots", exist_ok = True)

            finalImg.save(fp = f"screenshots/{screenshotName}.png")
            print(Fore.GREEN + f"[SUCCESS] Saved comment {commentsParsed + 1} to screenshots folder (elapsed {get_current_ms() - start_time}ms)")

        # Scroll until the comment is vertically centered so it gets a good view of the comment.
        driver.execute_script("arguments[0].scrollIntoView({ block: 'center' });", comment)

        if config["save_json"] == True: save_json()
        if config["save_screenshot"] == True: save_screenshot()

        # Hide the comment last so that we can actually take a screenshot of it
        hide_element(comment)
        commentsParsed += 1

    pagesParsed += 1
    print(Fore.MAGENTA + f"Finished page {pagesParsed}, {commentsParsed} comments parsed so far")

#endregion