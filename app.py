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
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ImageCarouselTemplate, ImageCarouselColumn, PostbackAction, ConfirmTemplate, MessageTemplateAction
)
from utils.states import *
from utils.send import *
from utils.image_handler import *
from models.user import User, Server, Receiver
from models.psudeDB import PsudeDB
from models.DB import DB
import matching
import carousel_template as carousel_temp


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
#FIXME:DBAdapterクラスを作成し，メンバにIS_TEST，DB,PsudeDBインスタンスを持って管理.
db = DB()

def receive_name(userId, received_text):
    if not IS_TESTING:
        db.save_value(userId, NAME, received_text)
    if len(received_text) <= 20:
        if not IS_TESTING:
            db.set_state(userId, sZIP)
        return send_message(userId, received_text+"さんですね。郵便番号を教えてください")
    else:
        return send_message(userId, "名前が長すぎます。入力し直してください")

def receive_zip(userId, zipcode):
    if len(zipcode) != 7 or not zipcode.isnumeric():
        return send_message(userId, "郵便番号を正しく入力してください")
    else:
        db.save_value(userId, ZIP, zipcode)
        # DBに保存して登録
        if not IS_TESTING:
            name = db.get_value(userId, NAME)
            user = User(userId, name, zipcode)
            db.register_user(user, NAME, ZIP)

            user_info = user.show_info()
            db.delete_state(userId)
            send_message(userId, user_info + "\nで登録しました")
        else:
            return send_message(userId, zipcode + "登録完了")

def match_userId(userId, received_text, state=None):
    """
    userIdのstateを取り出して、そのコメントごとに処理を分岐させる
    stateはredisで管理
    """
    user = None
    if IS_TESTING:
        user = psude_db.get_user(userId)
    else:
        user = db.get_user(userId)

    if state is None:
        state = db.get_state(userId, delete=True)
    if state == sNAME:
        return receive_name(userId, received_text)
    elif state == sZIP:
        return receive_zip(userId, received_text)
    elif state == sMENU:
        menu = received_text
        db.save_value(userId, MENU, menu)
        db.set_state(userId, sPHOTO)
        send_message(userId, "料理の写真を送ってください")
    elif state == sMENU_NOT_COOKED_YET:
        menu = received_text
        db.save_value(userId, MENU, menu)
        send_message(userId, "完成予定時刻を教えてください\n（例）午後6時14分→18:14\n　　　午前9時5分→09:05")
        db.set_state(userId, sCOMPLETE_AT)
    elif state == sCOMPLETE_AT:
        complete_at = received_text
        db.save_value(userId, COMPLETE_AT, complete_at)
        register_server_not_cooked_yet(userId)
    elif state == sSERVER_REGISTER:
        menu = db.get_value(userId, MENU, delete=True)
        completeAt = db.get_value(userId, COMPLETE_AT, delete=True)
        print(received_text)
        if received_text == "はい":
            user = Server(userId)
            user.menu = menu

            # 時間完成時間
            user.done = (completeAt == None)
            if not user.done:
                hour = int(completeAt[:2])
                minute = int(completeAt[3:])
                compAt = datetime.now().replace(hour=hour, minute=minute)
                user.completeAt = compAt
            db.register_role(user)

            send_message(userId, "登録完了しました")
            matching.matching(user)
        else:
            send_message(userId, "登録し直してください")
    elif state == sSERVER_CONFIRM:
        answer = received_text
        server = db.get_user(userId, "server")
        receiver = db.get_other(server)
        if answer == "マッチング":
            send_message(userId, "相手の返信があるまでお待ちください")
            matching.matching_ask_receiver(receiver=receiver, server=server)
        else:
            send_message(userId, "次にマッチングするまでお待ちください")

def encourage_register(userId):
    text="ユーザーが見つかりません。\n「ユーザー登録」と話しかけてください"
    return send_message(userId, text)

def registration(userId):
    if not IS_TESTING:
        db.set_state(userId, sNAME)
    return send_message(userId, "ユーザー登録をします。\nニックネームを教えてください")

def get_user_info(userId, void=True):
    user = db.get_user(userId)
    if not user:
        return encourage_register(userId)
    text = "ユーザー名：" + user.name + "\n"
    text += "郵便番号：\u3012" + user.zipcode
    
    if not void:#REVIEW:テストかどうかの判定ならいらない?.
        return text
    else:
        return send_message(user.userId, text)

def register_role(userId, role, menu=None, cooked=True, completeAt=None):
    user = db.get_user(userId, role)

    if not user:
        encourage_register(userId)
        return

    if role == "server":
        user.menu = menu
        user.done = cooked
        if not cooked:
            hour = int(completeAt[:2])
            minute = int(completeAt[3:])
            compAt = datetime.now().replace(hour=hour, minute=minute)
            user.completeAt = compAt
        carousel = carousel_temp.server_register_confirmation_carousel(user)
        send_carousel(userId, carousel)
        db.set_state(userId, sSERVER_REGISTER)
        """
        text = user.wait_matching_message()
        send_message(userId, text)
        """

    else:
        # receiverなら無条件で登録できる
        db.register_role(user)
        send_message(userId, "マッチングするまでお待ちください")
        matching.matching(user)
    """
    if IS_TESTING:
        psude_db.store_role(user, role)
        return psude_db.matching(user, role)
    else:
        file_name = get_user_image(userId)
        if not file_name:
            threading.Thread(target=matching.access_database(user,db,file_name)).start()
    """

def register_receiver(userId):
    return register_role(userId, "receiver")

def register_server(userId, cooked=True, completeAt=None):
    menu = db.get_value(userId, MENU)
    if menu == None:
        db.set_state(userId, sMENU if cooked else sMENU_NOT_COOKED_YET)
        send_message(userId, "メニューを教えてください")
    else:
        return register_role(userId, "server", menu, cooked=cooked, completeAt=completeAt)

def register_server_not_cooked_yet(userId):
    completeAt = db.get_value(userId, COMPLETE_AT)
    register_server(userId, cooked=False, completeAt=completeAt)

func_dic = {
    "ユーザー登録":registration,
    "ユーザー情報":get_user_info,
    "お腹すいた":register_receiver,
    "料理を作るよ":register_server_not_cooked_yet,
    "り":register_server_not_cooked_yet,
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

    db.save_value(userId, MESSAGE, "NOT_YET")

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

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

    state = db.get_state(userId)
    if state == sPHOTO:
        image.save(url, 'JPEG', quality=100, optimize=True)
        register_server(userId)

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    line_bot_api.reply_message(
            event.reply_token,
            StickerSendMessage(package_id='1',sticker_id='1'))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    userId = event.source.user_id
    received_text = event.message.text

    if not match_function(userId, received_text):
        match_userId(userId, received_text)

    value = db.get_value(userId, MESSAGE)
    if value != "SENT":
        text = "Hello, Linebot sujata\uD83C\uDF7C"
        db.delete_value(userId, MESSAGE)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=text))

if __name__ == "__main__":
    set_line_api(line_bot_api, db)
    matching.set_line_api(line_bot_api, db)
    app.run()
