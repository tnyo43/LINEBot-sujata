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

    def __str__(self):
        res = self.__class__.__name__ + " : " + self.name + ", ZIP code : " + self.zipcode + "\n"
        res += "ID : " + self.userId + "\n"
        return res

    def __repr__(self):
        return str(self)

    def show_info(self):
        res = "ニックネーム：" + self.name
        res += "\n郵便番号：" + self.zipcode
        return res

    def register_query(self):
        query = "delete from users where userid='" + self.userId + "';"
        query += "insert into users values ('"
        query += self.userId + "', '"
        query += self.name + "', '"
        query += self.zipcode + "', "
        query += "0, 0, 0);"
        return query

    def unregister_query(self):
        if self.__class__ == User:
            return None
        return "delete from " + self.role + "s where userId='" + self.userId + "';"

    @staticmethod
    def find_query(userId):
        return "select *from users where userid='" + userId + "';"

    @staticmethod
    def new(args, role):
        if role == "":
            return User._new(args)
        if role == "server":
            return Server._new(args)
        else:
            return Receiver._new(args)

    @classmethod
    def _new(cls, args):
        """
        DBから得た情報からServerのオブジェクトを作成
        """
        return cls(args[0], args[1], args[2])

class Server(User):
    def __init__(self, userId, name=None, zipcode=None):
        super().__init__(userId, name, zipcode)
        self.role = "server"
        self.other = "receiver"
        self.menu = ""

    def __str__(self):
        res = super().__str__()[:-1]
        res += ", メニュー：" + self.menu
        return res

    def register_query(self):
        return "insert into servers values('" + self.userId + "', '" + self.menu + "', now());"

    def matching_query(self):
        return "select users.*, from users inner join receivers as x on x.userId=users.userId where users.zipcode in (select zipcode from users where userId='"+self.userId+"') and users.userId<>'"+self.userId+"' order by x.at ASC;"

    def match_with(self):
        return self.name + "さんとマッチングしました。\nメニューは" + self.menu + "です！"

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
        self.other = "server"

    def register_query(self):
        return  "insert into receivers values('" + self.userId + "', now());"

    def matching_query(self):
        return "select users.*, servers.menu from users inner join servers on servers.userId=users.userId where users.zipcode in (select zipcode from users where userId='"+self.userId+"') and users.userId<>'"+self.userId+"' order by servers.at ASC;"

    def match_with(self):
        return self.name + "さんとマッチングしました。"

    def request(self):
        """
        serverを募る
        """
        pass
