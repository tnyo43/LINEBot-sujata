
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage, StickerSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ImageCarouselTemplate, ImageCarouselColumn, PostbackAction, ConfirmTemplate, MessageTemplateAction
)

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
    text = other.name + "さんとマッチングします\nよろしいですか？"
    return TemplateSendMessage(
            alt_text='matching comfirmation',
            template=ConfirmTemplate(text = text, actions=[
                MessageTemplateAction(label='マッチングする', text='マッチング'),
                MessageTemplateAction(label='断る', text='ごめんなさい')
            ])
        )


