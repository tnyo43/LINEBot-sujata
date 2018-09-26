
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
