from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage, ImageMessage, ImageSendMessage
)
from utils.send import send_message, send_image, send_carousel, set_line_api
from models.user import User, Server, Receiver
from models.psudeDB import PsudeDB
from carousel_template import server_match_carousel, receiver_match_carousel
from models.DB import DB
from utils.states import *
import sys

line_bot_api = None
db = None

def set_line_api(_line_bot_api, _db):
    global line_bot_api
    line_bot_api = _line_bot_api
    global db
    db = _db

def access_database(user, db, file_name, IS_TESTING):
    # 同じユーザーが登録しているなら更新
    query = user.unregister_query()
    db.exe_query(query)# FIXME
    matching(user, db, file_name, IS_TESTING)
    # 現在時刻と一緒に更新
    query = user.register_query()
    db.exe_query(query)

def matching(user):
    # serversテーブルで同じ街の人を検索する。()内のTrueをのぞけば自分自信を検索しない
    other = db.get_other(user)

    if other == None:
        return

    server = None
    receiver = None
    if user.role=="server":
        server = user
        receiver = other
    else:
        server = other
        receiver = user

    # まずはserverだけに送って確認してもらう
    send_carousel(server.userId, server_match_carousel(server, receiver))
    db.set_state(server.userId, sSERVER_CONFIRM)

def matching_ask_receiver(receiver, server):
    send_carousel(receiver.userId, receiver_match_carousel(receiver, server))
    db.set_state(receiver.userId, sRECEIVER_CONFIRM)
