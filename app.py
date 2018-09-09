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
import redis
import psycopg2

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
r = redis.StrictRedis(host='localhost', port=6379, db=0)

# postgreの接続
connection_config = {
    'host': 'localhost',
    'port': '5432',
    'database': 'sujata',
    'user': os.getenv("POSTGRE_USER", None),
    'password': os.getenv("POSTGRE_PASS", None)
}
connection = psycopg2.connect(**connection_config)
cur = connection.cursor()

# state
sNAME, sZIP = range(2)
MESSAGE = "message"
NAME = "name"
ZIP = "zip"

@app.route("/")
def index():
    return "Hello, LineBot sujata"

def send_message(userId, text):
    r.set(MESSAGE+userId, text)

def set_state(userId, state):
    r.set(userId, state)

def get_state(userId):
    return int(r.get(userId))

def save_value(userId, key, value):
    r.set(key+userId, value)

def get_value(userId, keys):
    dic = {}
    for key in keys:
        print(key)
        dic[key] = r.get(key+userId).decode('utf-8')
    return dic

def resister_user(userId):
    dic = get_value(userId, [NAME, ZIP])
    query = "delete from users where userid='" + userId + "';"
    cur.execute(query)
    print(dic)
    query = "insert into users values ('"
    query += userId + "', '"
    query += dic[NAME] + "', '"
    query += dic[ZIP] + "', "
    query += "0, 0, 0);"
    print(query)
    try:
        cur.execute(query)
    except:
        pass
    connection.commit()

def get_user_info(userId, void=True):
    query = "select * from users where userid='" + userId + "';"
    cur.execute(query)
    for x in cur:
        text = "ユーザー名：" + x[1] + "\n"
        text += "郵便番号：\u3012" + x[2]
        if not void:
            return text
        else:
            send_message(userId, text)
        break

def match_userId(userId, message):
    print("match user id")
    try:
        state = get_state(userId)
        print(state)
        text = None
        if message["type"] == "text":
            text = message["text"]

        delete = False
        if int(state) == sNAME:
            save_value(userId, NAME, text)
            if len(text) <= 20:
                send_message(userId, text+"さんですね。郵便番号を教えてください")
                # 次は郵便番号を尋ねる
                set_state(userId, sZIP)
            else:
                send_message(userId, "名前が長すぎます。入力し直してください")
        elif int(state) == sZIP:
            print(text, len(text))
            if len(text) != 7 or not text.isnumeric():
                send_message(userId, "郵便番号を正しく入力してください")
            else:
                save_value(userId, ZIP, text)
                # DBに保存して登録
                resister_user(userId)
                text = get_user_info(userId, void=False)
                send_message(userId, text + "\nで登録しました")
                delete = True
        if delete:
            r.delete(userId)
    except TypeError:
        pass

def registration(userId):
    print("registration")
    send_message(userId, "ユーザー登録をします。\nニックネームを教えてください")
    set_state(userId, sNAME)

func_dic = {
    "ユーザー登録":registration,
    "ユーザー情報":get_user_info,
}

def match_function(userId, text):
    if text in func_dic.keys():
        func_dic[text](userId)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    dic = json.loads(body)
    userId = dic["events"][0]["source"]["userId"]
    match_userId(userId, dic["events"][0]["message"])
    if dic["events"][0]["message"]["type"] == "text":
        match_function(userId, dic["events"][0]["message"]["text"])

    # handle webhook body
    try:
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
    try:
        text = r.get(MESSAGE+userId).decode('utf-8')
    except AttributeError:
        text = "Hello, Linebot sujata\uD83C\uDF7C"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text))
    r.delete(MESSAGE+userId)

if __name__ == "__main__":
    app.run()
