import os
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage
)

import json
import threading
import redis
import psycopg2

from models.user import User, Server, Receiver
from models.psudeDB import PsudeDB

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', None)

if CHANNEL_ACCESS_TOKEN is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit()
if CHANNEL_SECRET is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit()

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# redisの接続
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
DATABASE_INDEX = 0
pool = redis.ConnectionPool.from_url(REDIS_URL, db=DATABASE_INDEX)
r = redis.StrictRedis(connection_pool=pool)

# postgreの接続
connection_config = {
    'host': os.getenv("DB_HOST", None),
    'port': '5432',
    'database': os.getenv("DB_NAME", None),
    'user': os.getenv("POSTGRE_USER", None),
    'password': os.getenv("POSTGRE_PASS", None)
}
connection = psycopg2.connect(**connection_config, sslmode='require')
cur = connection.cursor()

# for unittest
IS_TESTING = False
def set_is_testing(b):
    global IS_TESTING
    IS_TESTING = b

psude_db = None
def set_psude_db():
    global psude_db
    psude_db = PsudeDB()

# state
sNAME, sZIP, sMENU = range(3)
MENU = "menu"
MESSAGE = "message"
NAME = "name"
ZIP = "zip"

def send_message(userId, text):
    if IS_TESTING:
        return text
    else:
        line_bot_api.push_message(userId, TextSendMessage(text))
        r.set(MESSAGE+userId, "SENT")

def set_state(userId, state):
    if not IS_TESTING:
        r.set(userId, state)

def get_state(userId):
    return int(r.get(userId))

def save_value(userId, key, value):
    r.set(key+userId, value)

def get_value(userId, key, delete=False):
    value = r.get(key+userId)
    if value:
        value = value.decode('utf-8')
    if delete:
        r.delete(key+userId)
    return value

def get_values(userId, keys, delete=False):
    dic = {}
    for key in keys:
        value = r.get(key+userId)
        dic[key] = value.decode('utf-8') if value else None
        if delete:
            r.delete(key+userId)
    return dic

def register_user(user):
    global psude_db
    if IS_TESTING:
        psude_db.store_user(user)
        return
    dic = get_values(user.userId, [NAME, ZIP], delete=True)
    user.name = dic[NAME]
    user.zipcode = dic[ZIP]
    query = user.register_query()
    try:
        cur.execute(query)
    except:
        pass
    connection.commit()

def get_user(userId, role=""):
    if IS_TESTING:
        return psude_db.get_user(userId)

    query = User.find_query(userId)
    cur.execute(query)
    for x in cur:
        return User.new(x, role)

def get_user_info(userId, void=True):
    user = get_user(userId)
    if not user:
        encourage_register(userId)
        return
    text = "ユーザー名：" + user.name + "\n"
    text += "郵便番号：\u3012" + user.zipcode
    if not void:
        return text
    else:
        send_message(user.userId, text)

def match_userId(userId, message, state=None):
    try:
        user = None
        user = get_user(userId)
        if state == None:
            state = int(get_state(userId))
        text = message

        delete = False
        if state == sNAME:
            if not IS_TESTING:
                save_value(userId, NAME, text)
            if len(text) <= 20:
                set_state(userId, sZIP)
                return send_message(userId, text+"さんですね。郵便番号を教えてください")
            else:
                return send_message(userId, "名前が長すぎます。入力し直してください")
        elif state == sZIP:
            zipcode = text
            if len(text) != 7 or not text.isnumeric():
                return send_message(userId, "郵便番号を正しく入力してください")
            else:
                save_value(userId, ZIP, zipcode)
                # DBに保存して登録
                if not IS_TESTING:
                    name = get_value(userId, NAME)
                    user = User(userId, name, zipcode)
                    register_user(user)
                    text = user.show_info()
                    send_message(userId, text + "\nで登録しました")
                else:
                    return send_message(userId, message + "登録完了")
                delete = True
        elif state == sMENU:
            menu = text
            save_value(userId, MENU, menu)
            register_server(userId)
        if delete:
            r.delete(userId)
    except TypeError as e:
        print(e)

def encourage_register(userId):
    text="ユーザーが見つかりません。\n「ユーザー登録」と話しかけてください"
    send_message(userId, text)

def registration(userId):
    if not IS_TESTING:
        set_state(userId, sNAME)
    return send_message(userId, "ユーザー登録をします。\nニックネームを教えてください")

def register_role(userId, role, menu=None):
    user = get_user(userId, role)
    other = "receiver" if(role == "server") else "server"

    if not user:
        encourage_register(userId)
        print("no user")
        return

    text = ""
    if role == "server":
        user.menu = menu
        text += user.menu + "で登録しました。\n"

    send_message(userId, text+"マッチングするまでお待ちください")

    def access_database():
        # 同じユーザーが登録しているなら更新
        query = user.unregister_query()
        cur.execute(query)
        matching(user)
        # 現在時刻と一緒に更新
        query = user.register_query()
        cur.execute(query)
        connection.commit()

    if IS_TESTING:
        psude_db.store_role(user, role)
        return psude_db.matching(user, role)
    else:
        threading.Thread(target=access_database).start()

def register_receiver(userId):
    return register_role(userId, "receiver")

def register_server(userId):
    menu = get_value(userId, MENU, delete=True)
    if menu == None:
        set_state(userId, sMENU)
        send_message(userId, "メニューを教えてください")
    else:
        return register_role(userId, "server", menu)

def matching(user):
    # serversテーブルで同じ街の人を検索する
    query = user.matching_query()
    print(query)
    cur.execute(query)
    connection.commit()
    other = None
    for row in cur:
        print(row)
        other = User.new(row, user.other)
        if other.role == "server":
            other.menu = row[-1]
        break

    print(user, other)
    if IS_TESTING:
        return True
    push_message = lambda a, b: line_bot_api.push_message(a.userId, TextSendMessage(text=b.match_with()))
    users = [user, other]
    for a, b in zip(users, users[::-1]):
        try:
            push_message(a, b)
        except:
            pass

func_dic = {
    "ユーザー登録":registration,
    "ユーザー情報":get_user_info,
    "お腹すいた":register_receiver,
    "料理ができた":register_server,
    "へいお待ち！てやんでい":register_server,
}

def match_function(userId, text):
    if text in func_dic.keys():
        func_dic[text](userId)
        return True
    return False

@app.route("/")
def index():
    return "Hello, LineBot sujata"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    dic = json.loads(body)
    userId = dic["events"][0]["source"]["userId"]
    r.set(MESSAGE+userId, "NOT_YET")
    if dic["events"][0]["message"]["type"] == "text":
        text = dic["events"][0]["message"]["text"]
        print(text)
        if not match_function(userId, text):
            match_userId(userId,text)

    # handle webhook body
    try:
        if r.get(MESSAGE+userId).decode('utf-8') != "SENT":
            handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    line_bot_api.reply_message(
            event.reply_token,
            StickerSendMessage(package_id='1',sticker_id='1'))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    userId = event.source.user_id
    text = "Hello, Linebot sujata\uD83C\uDF7C"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text))
    r.delete(MESSAGE+userId)

if __name__ == "__main__":
    app.run()
