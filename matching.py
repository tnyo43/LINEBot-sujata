from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage, ImageMessage, ImageSendMessage
)
from utils.send import send_message, send_image, send_carousel, set_line_api
from models.user import User, Server, Receiver
from models.psudeDB import PsudeDB
from carousel_template import server_match_carousel
from models.DB import DB
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
    query = user.matching_query(True)
    db.exe_query(query)#FIXME

    other = db.get_other(user)

    """
    push_message = lambda a, b: line_bot_api.push_message(a.userId, TextSendMessage(text=b.match_with_message()))
    users = [user, other]
    for a, b in zip(users, users[::-1]):
        try:
            push_message(a, b)
            print(a)
            if a.role == "receiver":
                print(get_user_image(b.userId))
                app.send_image(a.userId, get_user_image(b.userId))
        except Exception as e:
            print(e)
    """
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
