
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ImageCarouselTemplate, ImageCarouselColumn, PostbackAction, ConfirmTemplate, MessageTemplateAction, ButtonsTemplate, URITemplateAction, PostbackTemplateAction
)
from utils.image_handler import *

def server_register_confirmation_carousel(user):
    text = "料理を" + ("作った" if user.done else "これから作る") + "\n"
    text += "料理名：" + user.menu
    if not user.done:
        text += "\n完成予定時刻：" + user.completeAt_string()

    return TemplateSendMessage(
            alt_text='server register comfirmation register',
            template=ConfirmTemplate(text=text, actions=[
                MessageTemplateAction(label='Yes', text='はい'),
                MessageTemplateAction(label='No', text='いいえ')
            ])
        )

def server_match_carousel(user, other):
    """
    マッチングした時にまずserverに確認を送る
    確認する内容は相手の名前と過去の受け取り回数（必要？）
    """
    text = user.menu + "で\n" + other.name + "さんとマッチングします\nよろしいですか？"
    return TemplateSendMessage(
            alt_text='matching comfirmation',
            template=ConfirmTemplate(text = text, actions=[
                MessageTemplateAction(label='マッチング', text='マッチング'),
                MessageTemplateAction(label='断る', text='断る')
            ])
    )

def receiver_match_carousel(receiver, server):
    print(server.done)
    print(server.completeAt)
    text = server.name + "さんとマッチングしました。\nメニューは" + server.menu + "です。"
    if server.done:
        return TemplateSendMessage(
                alt_text='matching confirmation receiver',
                template = ButtonsTemplate(
                    text=text,
                    thumbnail_image_url=get_user_image(server.userId, full=True),
                    actions=[
                        MessageTemplateAction(label='マッチング',text='マッチング'),
                        MessageTemplateAction(label='断る',text='断る'),
                    ]
                )
            )
    else:
        text += "\n" + server.completeAt.strftime("%H:%M") + "に完成予定です"
        return TemplateSendMessage(
                alt_text='matching confirmation receiver',
                template = ButtonsTemplate(
                    text=text,
                    actions=[
                        MessageTemplateAction(label='マッチング',text='マッチング'),
                        MessageTemplateAction(label='断る',text='断る'),
                    ]
                )
            )

