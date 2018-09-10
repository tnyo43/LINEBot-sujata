import random
import string

class User:
    def __init__(self, userId, name, zipcode):
        # テスト用
        if userId == None:
            userId = ''.join([random.choice(string.ascii_letters) for _ in range(33)])

        self.userId = userId
        self.name = name
        self.zipcode = zipcode
        self.role = None

    def __str__(self):
        res = "User : " + self.name + ", ZIP code : " + self.zipcode + "\n"
        res += "ID : " + self.userId + "\n"
        return res

    def __repr__(self):
        return str(self)

class Server(User):
    def __init__(self, userId, name, zipcode):
        super().__init__(userId, name, zipcode)
        self.role = "server"

    def request(self):
        """
        receiverを募る
        """
        pass

    def upload(self):
        """
        写真をアップロードする
        """
        pass

class Receiver(User):
    def __init__(self, userId, name, zipcode):
        super().__init__(userId, name, zipcode)
        self.role = "receiver"

    def request(self):
        """
        serverを募る
        """
        pass

