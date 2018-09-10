import os
import unittest
import tempfile
import json
import responses
import random

import unittest
from app import *
from models.user import Server, Receiver
from models.psudeDB import PsudeDB

from linebot import LineBotApi
from linebot.models import TextSendMessage

class TestSujata(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.users = [
            Server(None, "いちろう", "0000000"),
            Server(None, "じろう", "1111111"),
            Receiver(None, "さぶろう", "1111111"),
            Receiver(None, "しろう", "0000002"),
            Server(None, "ごろう", "0000002"),
            Server(None, "ろくろう", "0000000"),
        ]
        for user in self.users:
            register_user(user)

    def setUp(self):
        self.app = app.test_client()
        self.tested = LineBotApi(os.getenv("LINE_CHANNEL_SECRET"))
        self.text = "ユーザー登録"
        self.userId = "123456789012345678901234567879012"
        self.text_message = TextSendMessage(text=self.text)
        self.message = [{"type":"text", "text":self.text}]

    """
    def test_access_index(self):
        response = self.app.get('/')
        assert response.status_code == 200
        assert response.data.decode('utf-8') == 'Hello, LineBot sujata'

    def test_registeration(self):
        toolongname = "あいうえおかきくけこさしすせそたちつてとな"
        invalid_zip1 = "12345678" # 長すぎ
        invalid_zip2 = "12x4567"  # 数字でない

        assert "名前が長すぎます。入力し直してください" == match_userId(self.userId, toolongname, sNAME)
        assert "たろうさんですね。郵便番号を教えてください" == match_userId(self.userId, "たろう", sNAME)
        assert "郵便番号を正しく入力してください" == match_userId(self.userId, invalid_zip1, sZIP)
        assert "郵便番号を正しく入力してください" == match_userId(self.userId, invalid_zip2, sZIP)
        assert "1234567登録完了" == match_userId(self.userId, "1234567", sZIP)
    """

    def test_matching(self):
        """
        ユーザーを順番に登録する
        3人目、5人目を登録したときにマッチングが起こる
        """
        res = []
        for i, user in enumerate(self.users):
            r = None
            if user.__class__ == Server:
                r = register_server(user.userId)
            else:
                r = register_receiver(user.userId)
            if r:
                res.append(r)

        assert len(res) == 2
        assert res[0][0] == self.users[2]
        assert res[0][1] == self.users[1]


if __name__ == '__main__':
    set_is_testing(True)
    set_psude_db()
    unittest.main()
