import random
import string
import psycopg2
import datetime

class User:
    def __init__(self, userId, name, zipcode):
        # テスト用
        if userId == None:
            userId = ''.join([random.choice(string.ascii_letters) for _ in range(33)])

        self.userId = userId
        self.name = name
        self.zipcode = zipcode
        self.done = False
        self.completeAt = None

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

    def wait_matching_message(self):
        return "マッチングするまでお待ちください"

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
        print(args)
        return cls(args[0], args[1], args[2])

class Server(User):
    def __init__(self, userId, name="", zipcode=""):
        super().__init__(userId, name, zipcode)
        self.role = "server"
        self.other = "receiver"
        self.menu = ""
        self.done = False
        self.completeAt = None

    def __str__(self):
        res = super().__str__()[:-1]
        res += ", メニュー：" + self.menu
        return res

    def completeAt_string(self):
        return self.completeAt.strftime("%H:%M")

    def register_query(self):
        q = "insert into servers values('" + self.userId + "', '" + self.menu + "', now(), " + str(self.done) + ", "
        print("self.done", self.done)
        if self.done:
            q += "now()"
        else:
            print(self.completeAt)
            print(type(self.completeAt))
            q += self.completeAt.strftime("to_timestamp('%Y-%m-%d %H:%M:%S','YYYY-MM-DD HH24:MI:SS')")
        q += ");"
        print(q)
        return q


    def matching_query(self, himself=False):
        query = "select users.* from users inner join receivers as x on x.userId=users.userId where users.zipcode in (select zipcode from users where userId='"+self.userId+"') "
        if not himself:
            query += "and users.userId<>'"+self.userId+"' "
        query += "order by x.at ASC;"
        return query

    def match_with_message(self):
        return self.name + "さんとマッチングしました。\nメニューは" + self.menu + "です！"

    def wait_matching_message(self):
        res = self.menu + "で登録しました。\n"
        res += super().wait_matching_message()
        res += "写真があれば投稿してください"
        return res

    def request(self):
        """
        receiverを募る
        """
        pass

class Receiver(User):
    def __init__(self, userId, name, zipcode):
        super().__init__(userId, name, zipcode)
        self.role = "receiver"
        self.other = "server"

    def register_query(self):
        return  "insert into receivers values('" + self.userId + "', now());"

    def matching_query(self, himself=False):
        query = "select users.*, servers.menu from users inner join servers on servers.userId=users.userId where users.zipcode in (select zipcode from users where userId='"+self.userId+"') "
        if not himself:
            query += " and users.userId<>'"+self.userId+"' "
        query += " order by servers.at ASC;"
        return query

    def match_with_message(self):
        return self.name + "さんとマッチングしました。"

    def request(self):
        """
        serverを募る
        """
        pass

