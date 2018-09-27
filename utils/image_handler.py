
import os
SUJATA_URL = os.getenv('SUJATA_URL', 'https://sujata-linebot.herokuapp.com') + '/'

def get_user_image(userId, full=False):
    filenames = [f for f in os.listdir('static') if userId in f]
    if len(filenames) == 0:
        return None
    url = 'static/' + filenames[0]
    if full:
        url = SUJATA_URL + url
    return url
