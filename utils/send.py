
import models.DB as DB
from utils.states import *

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ImageCarouselTemplate, ImageCarouselColumn, PostbackAction, ConfirmTemplate, MessageTemplateAction
)

line_bot_api = None
db = None

def set_line_api(_line_bot_api, _db):
    global line_bot_api
    line_bot_api = _line_bot_api
    global db
    db = _db

def send_image(userId, url):
    line_bot_api.push_message(userId, ImageSendMessage(
        original_content_url=SUJATA_URL+url,
        preview_image_url=SUJATA_URL+url
    ))

def send_message(userId, text):
    line_bot_api.push_message(userId, TextSendMessage(text))
    db.save_value(userId, MESSAGE, "SENT")

def send_carousel(userId, carousel):
    line_bot_api.push_message(userId, carousel)
    db.save_value(userId, MESSAGE, "SENT")

