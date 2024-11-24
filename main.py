# region introduction
"""
    YT (YouTube) Comments Screenshotter
    A side project which saves each comment of a YouTube video in screenshots and data.json.
    
    @asleepa | Discord
    My contacts are above if you need assistance.

    This code has been open-sourced for educational purposes.
    The code seen was originally used for a DougDougDoug video, hence the youtube_video URL.
"""

from lib import get_current_ms, exit_failure, hide_element, locate_element, get_comment_elements, get_comment_json
from lib import config

from colorama import Fore, init
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from PIL import Image
import os
import io
import time
import uuid
import json

#endregion
#region init

init(autoreset = True)

# If you can't understand this I think it's better off that way
if config["save_json"] == False and config["save_screenshot"] == False: exit_failure("save_json or save_screenshot needs to be True")

options = webdriver.ChromeOptions()
if config["headless"] == True:
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu") # If you use headless without --disable-gpu you're weird
if config["force_dark_theme"] == True: options.add_argument("--force-dark-mode")

driver = webdriver.Chrome(options)
driver.get(url = config["youtube_video"])

#endregion
#region code

# YouTube doesn't necessarily respond to system themes like other sites so we'll set it ourselves alongside --force-dark-mode
if config["force_dark_theme"] == True:
    body = locate_element(driver, locator = (By.TAG_NAME, "body"))

    if body != None:
        # Set YouTube preference cookie (PREF)
        driver.execute_script("document.cookie = \"PREF=f6=400; path=/; domain=.youtube.com\";")
        driver.refresh()

commentsContainer = locate_element(driver, locator = (By.ID, "comments"))
if commentsContainer != None: ActionChains(driver).move_to_element(commentsContainer).perform() # Scroll/teleport to comments container to load it

commentSection = None
comments = None

if commentsContainer != None: commentSection = locate_element(driver, locator = (By.ID, "sections"), parent = commentsContainer)
if commentSection != None: comments = locate_element(driver, locator = (By.ID, "contents"), parent = commentSection)

if comments == None: exit_failure("Comment section could not be found")

# execute_script executes code into the developer console, be careful
try:
    popupContainer = driver.find_element(by = By.TAG_NAME, value = "ytd-popup-container")
    hide_element(driver, popupContainer) # Hide the YouTube popup container from interfering with screenshots
except Exception:
    pass # Do nothing

try:
    topbar = driver.find_element(by = By.ID, value = "masthead-container")
    hide_element(driver, topbar) # Incase the comment appears at the top, hide the topbar
except Exception:
    pass # Do nothing

try:
    recommended = driver.find_element(by = By.ID, value = "secondary")
    hide_element(driver, recommended) # Hide recommended videos, chat, etc. on the right
except Exception:
    pass # Do nothing

# I DIDN'T KNOW ELEMENT.ID WAS INTERNAL I WAS DOING IT WRONG THE ENTIRE TIME USE GET_ATTRIBUTE NOOOO
try:
    primary = driver.find_element(by = By.ID, value = "primary-inner")
    player = primary.find_element(by = By.ID, value = "player")
    below = primary.find_element(by = By.ID, value = "below")

    hide_element(driver, player) # More room for comments which appear at the top

    belowItems = below.find_elements(by = By.XPATH, value = "./child::*")

    for element in belowItems:
        if element.get_attribute("id") == "comments": continue
        hide_element(driver, element)
except Exception:
    pass # Do nothing

try:
    commentsHeader = commentSection.find_element(by = By.ID, value = "header")
    hide_element(driver, commentsHeader) # Hide the comments header (add a comment, sort by, comment count etc)
except Exception:
    pass # Do nothing

commentsParsed = 0
pagesParsed = 0

while True if config["max_comments"] < 1 else commentsParsed < config["max_comments"]:
    commentList = None
    try:
        commentList = comments.find_elements(by = By.TAG_NAME, value = "ytd-comment-thread-renderer")
    except Exception:
        pass # Do nothing

    if commentList == None or len(commentList) < 1: continue # Redo the loop because comments are still not loaded

    localCommentsParsed = 0
    for comment in commentList:
        if "display: none" in comment.get_attribute("style"): continue
        commentInfo, commentInfoBody, commentMain, commentAuthor, commentExpander = get_comment_elements(driver, comment)
        commentReplies = None

        try:
            commentReplies = comment.find_element(by = By.ID, value = "replies")
        except Exception:
            pass # Do nothing

        if config["save_screenshot"] == True and commentExpander:
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

        if commentReplies != None:
            try:
                repliesRenderer = commentReplies.find_element(by = By.TAG_NAME, value = "ytd-comment-replies-renderer")
                repliesExpander = repliesRenderer.find_element(by = By.ID, value = "expander")
            except Exception:
                pass # Do nothing

        if repliesExpander != None:
            try:
                repliesExpanderContents = repliesExpander.find_element(by = By.ID, value = "expander-contents")

                for element in repliesExpander.find_elements(by = By.TAG_NAME, value = "div"):
                    if "expander-header" in element.get_attribute("class"):
                        repliesExpanderHeader = element

                if repliesExpanderHeader:
                    # Scroll to the replies button to load it
                    driver.execute_script("arguments[0].scrollIntoView({ block: 'center' });", repliesExpanderHeader)

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
                        start_time = get_current_ms()

                        # Wait until the spinner appears, its unrealistic that it'd instantly load
                        # It'd also probably skip if it only checked if it was hidden
                        while True:
                            if get_current_ms() - start_time >= config["reply_timeout"] * 1000: break # Prevent infinite loop
                            try:
                                spinner = continueRepliesRenderer.find_element(by = By.ID, value = "spinner")
                                if spinner.get_attribute("hidden") != "true": break # Break if the spinner is visible
                            except Exception:
                                pass # Do nothing

                        # Wait until replies are finished loading
                        while True:
                            if get_current_ms() - start_time >= config["reply_timeout"] * 1000: break # Prevent infinite loop
                            try:
                                spinner = continueRepliesRenderer.find_element(by = By.ID, value = "spinner")
                                if spinner.get_attribute("hidden") == "true": break # Break if the spinner is hidden
                            except Exception:
                                break # The spinner doesn't exist

                    time.sleep(0.1)
                    replyList = contents.find_elements(by = By.TAG_NAME, value = "ytd-comment-view-model")

                    for reply in replyList:
                        if "display: none" in reply.get_attribute("style"): continue
                        _, _, replyMain, replyAuthor, replyExpander = get_comment_elements(driver, parentComment = reply, isReply = True)

                        if config["save_screenshot"] == True and replyExpander:
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
                            aImg, aName, cTxt, cPublished, cLikes, cHeart, _, aBadgeSVG, aCreator = get_comment_json(replyMain, replyAuthor, replyExpander)

                            newReply = {
                                "Content": cTxt,
                                "Published": cPublished,
                                "Author": {
                                    "Image": aImg,
                                    "Name": aName,
                                    "Badge": aBadgeSVG,
                                    "Creator": aCreator
                                },
                                "Stats": {
                                    "Likes": cLikes,
                                    "Heart": cHeart
                                }
                            }

                            cReplies.append(newReply)

                        if config["save_screenshot"] == True: cReplyBinaries.append(reply.screenshot_as_png)
                        hide_element(driver, reply)

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
                pass # Do nothing - also probably no replies if theres no button=

        aImg, aName, cTxt, cPublished, cLikes, cHeart, cPinned, aBadgeSVG, aCreator = "", "", "", "", "", False, "", "", False
        if config["save_json"] == True:
            # Get the comment's stats
            aImg, aName, cTxt, cPublished, cLikes, cHeart, cPinned, aBadgeSVG, aCreator = get_comment_json(commentMain, commentAuthor, commentExpander)

        def save_json(screenshotPath):
            """
            Saves the comment's data into data.json.
            """

            # Create the dictionary to append to "comments" in data.json using the variables we set earlier
            newComment = {
                "Screenshot": screenshotPath,
                "Content": cTxt,
                "Published": cPublished,
                "Author": {
                    "Image": aImg,
                    "Name": aName,
                    "Badge": aBadgeSVG,
                    "Creator": aCreator
                },
                "Stats": {
                    "Likes": cLikes,
                    "Heart": cHeart,
                    "Pinned": cPinned
                },
                "Replies": cReplies
            }

            data = None
            with open("data.json", "r") as file:
                data = json.load(file)

            if data == None: return
            data["comments"].append(newComment)

            # Apply extra data now instead of when the code is completed if you decide to terminate the process early
            # pagesParsed is also updated towards the end of the code
            data["data"]["youtubeUrl"] = config["youtube_video"]
            data["data"]["commentsParsed"] = commentsParsed + 1
            data["data"]["pagesParsed"] = pagesParsed

            with open("data.json", "w") as file:
                json.dump(data, file, indent = 1)

            print(Fore.GREEN + f"[SUCCESS] Wrote new comment entry for comment {commentsParsed + 1} to data.json")

        def save_screenshot(screenshotPath: str = f"screenshots/{str(uuid.uuid4())}.png"):
            """
            Saves the comment's binary PNG data as a PNG file in the screenshots folder.
            """
            if commentInfo == None: return

            start_time = get_current_ms()
            print(Fore.BLUE + "Creating screenshot")

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

            finalImg.save(fp = screenshotPath)
            print(Fore.GREEN + f"[SUCCESS] Saved comment {commentsParsed + 1} to screenshots folder (elapsed {get_current_ms() - start_time}ms)")

        # Scroll until the comment is vertically centered so it gets a good view of the comment.
        driver.execute_script("arguments[0].scrollIntoView({ block: 'center' });", commentInfo) # comment, not commentInfo - or it'll include the replies

        replacements = {
            "[ms]": str(get_current_ms()),
            "[guid]": str(uuid.uuid4()),
            "[id]": comment.id,
            "[author]": aName,
            "[date]": cPublished
        }

        if isinstance(replacements["[author]"], str) and len(replacements["[author]"]) > 0:
            replacements["[author]"] = replacements["[author]"].replace("@", "") # Remove @'s as a safeguard

        def text_replacements(text: str):
            for key, value in replacements.items():
                if isinstance(value, str) and len(value) > 0:
                    text = text.replace(key, value)
            return text
        
        screenshotPath = None
        if config["save_screenshot"] == True:
            screenshotPath = f"screenshots/{text_replacements(config["screenshot_name_format"])}.png"
            save_screenshot(screenshotPath)

        if config["save_json"] == True: save_json(screenshotPath) # File will be None if save_screenshot is False

        # Hide the comment last so that we can actually take a screenshot of it
        hide_element(driver, comment)
        commentsParsed += 1
        localCommentsParsed += 1

    if localCommentsParsed < 1: break

    pagesParsed += 1
    print(Fore.MAGENTA + f"Finished page {pagesParsed}, {commentsParsed} comments parsed so far")

data = None
with open("data.json", "r") as file:
    data = json.load(file)

# Apply some (final) extra data to help web scrapers or just viewers who are looking at the json
if data != None:
    data["data"]["pagesParsed"] = pagesParsed

    with open("data.json", "w") as file:
        json.dump(data, file, indent = 1)

print(Fore.CYAN + "Finished!")
#endregion