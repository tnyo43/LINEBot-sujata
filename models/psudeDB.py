class PsudeDB:

    def __init__(self):
        self.users = []
        self.receivers = []
        self.servers = []

    def store_user(self, user):
        self.users.append(user)
        self.users.sort(key=lambda x: x.userId)

    def get_user(self, userId):
        for i in range(len(self.users)):
            if self.users[i].userId == userId:
                return self.users[i]

    def store_role(self, user, role):
        (self.servers if role == "server" else self.receivers).append(user)

    def matching(self, user, role):
        """
        郵便番号が同じペアを返す、(server, receiver)の順
        もしペアがないならNoneを返す
        """
        others = self.receivers if role == "server" else self.servers
        for o in others:
            if (o.zipcode == user.zipcode):
                user2 = o
                break
        else:
            return None

        if role == "server":
            user, user2 = user2, user

        return (user, user2)


