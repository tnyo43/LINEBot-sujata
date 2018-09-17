import os
import json
import threading
from io import BytesIO
from datetime import datetime
from PIL import Image
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage, ImageMessage, ImageSendMessage
)
from models.user import User, Server, Receiver
from models.psudeDB import PsudeDB
from models.DB import DB


app = Flask(__name__)
SUJATA_URL = os.getenv('SUJATA_URL', 'https://sujata-linebot.herokuapp.com') + '/'
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

# for unittest
IS_TESTING = False
def set_is_testing(b):
    global IS_TESTING
    IS_TESTING = b

psude_db = None
def set_psude_db():
    global psude_db
    psude_db = PsudeDB()
db = DB()#TODO:IS_TESTで変数dbの中身を分ける.

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
        db.save_value(userId, MESSAGE, "SENT")

def send_image(userId, url):
    line_bot_api.push_message(userId, ImageSendMessage(
        original_content_url=SUJATA_URL+url,
        preview_image_url=SUJATA_URL+url
    ))

def ask_name(userId, received_text):
    ask_text = ""

    if not IS_TESTING:
        db.save_value(userId, NAME, received_text)
    
    if len(received_text) <= 20:
        if not IS_TESTING:
            db.set_state(userId, sZIP)
        ask_text = received_text+"さんですね。郵便番号を教えてください"
    else:
        ask_text = "名前が長すぎます。入力し直してください"
    return ask_text

def ask_zip(userId, received_text):
    ask_text = ""

    if len(received_text) != 7 or not received_text.isnumeric():
        ask_text = "郵便番号を正しく入力してください"
    else:
        zipcode = received_text
        db.save_value(userId, ZIP, zipcode)
        # DBに保存して登録
        if not IS_TESTING:
            name = db.get_value(userId, NAME)
            user = User(userId, name, zipcode)
            db.register_user(user, NAME, ZIP)
            received_text = user.show_info()
            db.set_state(userId, sMENU)
            ask_text = received_text + "\nで登録しました"
        else:
            psude_db.store_user(user)
            ask_text =  message + "登録完了"
        delete = True
    return ask_text

def match_userId(userId, received_text, state=None):
    user = None
    if IS_TESTING:
        user = psude_db.get_user(userId)
    else:
        user = db.get_user(userId)

    if state == None:
        state = db.get_state(userId)
    if state == None:
        return None
    
    if state == sNAME:
        return ask_name(userId, received_text)
    elif state == sZIP:
        return ask_zip(userId, received_text)
    elif state == sMENU:
        menu = received_text
        db.save_value(userId, MENU, menu)
        return register_server(userId)


def encourage_register(userId):
    text="ユーザーが見つかりません。\n「ユーザー登録」と話しかけてください"
    return text

def registration(userId):
    if not IS_TESTING:
        db.set_state(userId, sNAME)
        print("chk", db.get_state(userId))
    return "ユーザー登録をします。\nニックネームを教えてください"

def register_role(userId, role, menu=None):
    user = db.get_user(userId, role)
    other = "receiver" if(role == "server") else "server"

    if not user:
        print("no user")
        return encourage_register(userId)

    if role == "server":
        user.menu = menu

    text = user.wait_matching_message()

    send_message(userId, text)

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
    menu = db.get_value(userId, MENU, delete=True)
    if menu == None:
        db.set_state(userId, sMENU)
        return "メニューを教えてください"
    else:
        return register_role(userId, "server", menu)

def get_user_info(userId, void=True):
    user = db.get_user(userId)
    if not user:
        return encourage_register(userId)
    text = "ユーザー名：" + user.name + "\n"
    text += "郵便番号：\u3012" + user.zipcode
    return text

def matching(user):
    # serversテーブルで同じ街の人を検索する。()内のTrueをのぞけば自分自信を検索しない
    query = user.matching_query()
    cur.execute(query)
    connection.commit()
    other = None
    for row in cur:
        other = User.new(row, user.other)
        if other.role == "server":
            other.menu = row[-1]
        break

    if IS_TESTING:
        return True
    push_message = lambda a, b: line_bot_api.push_message(a.userId, TextSendMessage(text=b.match_with_message()))
    users = [user, other]
    for a, b in zip(users, users[::-1]):
        try:
            push_message(a, b)
            print(a)
            if a.role == "receiver":
                print("send")
                print(get_user_image(b.userId))
                send_image(a.userId, get_user_image(b.userId))
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
        return func_dic[text](userId)
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

    db.save_value(userId, MESSAGE, "NOT_YET")

    # handle webhook body
    try:
        value = db.get_value(userId, MESSAGE)
        # if value != "SENT":
        handler.handle(body, signature)
        # else:
            # print("is sent.\n")
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def get_user_image(userId):
    filenames = [f for f in os.listdir('static') if userId in f]
    if len(filenames) == 0:
        return None
    return 'static/' + filenames[0]

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    userId = event.source.user_id

    def content_to_image(userId, content):
        image = Image.open(BytesIO(message_content.content))
        ratio = max(min(600, image.width)/image.width, min(600, image.height)/image.height)

        same_userId_filenames = [f for f in os.listdir('static') if userId in f]
        for filename in same_userId_filenames:
            os.remove('static/'+filename)

        url = "static/" + userId + "-" + datetime.now().strftime("%Y%m%d%H%M%S") + ".jpg"
        return (image.resize((int(image.width*ratio), int(image.height*ratio))), url)

    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)
    image, url = content_to_image(userId, message_content.content)

    image.save(url, 'JPEG', quality=100, optimize=True)

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    line_bot_api.reply_message(
            event.reply_token,
            StickerSendMessage(package_id='1',sticker_id='1'))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    userId = event.source.user_id
    received_text = event.message.text
    send_text = ""

    send_text = match_function(userId, received_text)
    if not send_text:
        send_text = match_userId(userId, received_text)
    
    if not send_text:
        send_text = "Hello, Linebot sujata\uD83C\uDF7C"
        db.delete_value(userId, MESSAGE)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=send_text))

if __name__ == "__main__":
    app.run()
