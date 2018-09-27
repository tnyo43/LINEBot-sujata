import os
import redis
import psycopg2
from models.user import User

#REVIEW:privateにできないのでクラス変数よりグローバル変数がいい？
POSTGRE_HOST = os.getenv("DB_HOST", None)
POSTGRE_NAME = os.getenv("DB_NAME", None)
POSTGRE_USER = os.getenv("POSTGRE_USER", None)
POSTGRE_PASS = os.getenv("POSTGRE_PASS", None)
if POSTGRE_HOST is None or POSTGRE_NAME is None or \
    POSTGRE_USER is None or POSTGRE_PASS is None:
    print('Specify environment variable on DB.py.')
    sys.exit()

# redisの接続
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
DATABASE_INDEX = 0
pool = redis.ConnectionPool.from_url(REDIS_URL, db=DATABASE_INDEX)
r = redis.StrictRedis(connection_pool=pool)

# postgreの接続
connection_config = {
    'host': POSTGRE_HOST,
    'port': '5432',
    'database': POSTGRE_NAME,
    'user': POSTGRE_USER,
    'password': POSTGRE_PASS
}
connection = psycopg2.connect(**connection_config, sslmode='require')
cur = connection.cursor()


class DB:

    def set_state(self, userId, state):
        r.set(userId, state)

    def get_state(self, userId, delete=False):
        user_state = r.get(userId)
        if user_state is None:
            return None
        if delete:
            r.delete(userId)
        return int(user_state)

    def save_value(self, userId, key, value):
        r.set(key+userId, value)

    def get_value(self, userId, key, delete=False):
        value = r.get(key+userId)
        if value:
            value = value.decode('utf-8')
        if delete:
            r.delete(key+userId)
        return value

    def get_values(self, userId, keys, delete=False):
        dic = {}
        for key in keys:
            value = r.get(key+userId)
            dic[key] = value.decode('utf-8') if value else None
            if delete:
                r.delete(key+userId)
        return dic

    def delete_state(self, userId):
        r.delete(userId)

    def delete_value(self, userId, key):
        r.delete(key+userId)

    # PostgreSQL
    def register_user(self, user, NAME, ZIP):
        dic = self.get_values(user.userId, [NAME, ZIP], delete=True)
        user.name = dic[NAME]
        user.zipcode = dic[ZIP]
        query = user.register_query()
        try:
            cur.execute(query)
        except Exception as e:
            print("register_user",e)
        connection.commit()

    def register_role(self, user):
        # 同じユーザの古い登録データを削除
        query = user.unregister_query()
        cur.execute(query)
        query = user.register_query()
        try:
            cur.execute(query)
        except Exception as e:
            print("register_role",e)
        connection.commit()

    def get_user(self, userId, role=""):
        query = User.find_query(userId)
        try:
            cur.execute(query)
        except Exception as e:
            # userIDがないとき
            print("Exception",e)
            return None
        for x in cur:
            return User.new(x, role)

    #FIXME:あとで消す.
    def exe_query(self, query):
        try:
            cur.execute(query)
            connection.commit()
        except Exception as e:
            print(e)
            return False
        return True

    def get_other(self, user):
        other = None
        try:
            for row in cur:
                other = User.new(row, user.other)
                if other.role == "server":
                    other.menu = row[-1]
                break
        except Exception as e:
            print(e)
        return other
