from bs4 import BeautifulSoup

import json
import requests
import time
import datetime
import urllib
import pickle
from os import listdir

TOKEN = "503124568:AAFgKJSCKcwqplnSTjGTVtHDX6Zq-omrc-w"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
TODAY = time.time() // 86400
trees = ['ольха', 'орешник', 'береза', 'вяз', 'клен', 'ясень', 'ива', 'дуб', 'кипарис', 'бук', 'граб']


def save(stats, chat):
    with open('users/{}.pickle'.format(chat), 'wb') as f:
        pickle.dump(stats, f)



def parse_allergy_info():
    try:
        url = "https://7days.ru/allergy/pyltsevoi-monitoring.htm"

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}

        html = requests.get(url, headers=headers).text
        soup = BeautifulSoup(html, "html5lib")
        table = soup.find(class_='table__data')
        strings = table.find_all('tr')
        info = {'time': datetime.date.today().strftime("%Y.%m.%d"),
                'real_time': time.time()}
        for string in strings[2:]:
            name = string.find(class_='table__data_td-title').text
            concentration = string.find(class_='table__data_td-center').text
            conclusion = string.find(class_='table__levels_grade-text').text
            info[name] = {'conclusion': conclusion, 'concentration': concentration}

        with open('allergy.pickle', 'wb') as file:
            pickle.dump(info, file)

        return info

    except Exception as e:
        print("Exception in parse_allergy_info() function." + str(e))
        return []


def send_notifications():
    try:
        users = listdir('users/')
        with open('allergy.pickle', 'rb') as file:
            info = pickle.load(file)

        for user in users:
            with open('users/' + user, 'rb') as f:
                stats = pickle.load(f)

            if not(stats['warnings']):
                continue

            else:
                msg = ''
                for warning in stats['warnings']:
                    s_info = info[warning.title()]
                    msg += ('{0} - {1} ({2})\n'.format(warning, s_info['conclusion'], s_info['concentration']))

                send_message('Доброе утро! Сегодня такая картина:\n {}'.format(msg), user.strip('.pickle'))

    except ValueError as e:
        print('Exception in send_notification() function. {}'.format(str(e)))


def get_allergy_info(step=0):
    try:
        with open('allergy.pickle', 'rb') as file:
            info = pickle.load(file)

        if time.time() - info['real_time'] > 10000 and step < 3:
            parse_allergy_info()
            return get_allergy_info(step=step+1)

        allergy_msg = "Вот данные на {}\n\n".format(info['time'])

        for key in info:
            if key.lower() in trees:
                s_info = info[key]
                allergy_msg += ('{0} - {1} ({2})\n'.format(key, s_info['conclusion'], s_info['concentration']))

        return allergy_msg

    except Exception as e:
        print("Exception in get_allergy_info() function." + str(e))
        return 'Бот сейчас недоступен, ведутся технические работы :('


def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates"
    if offset:
        url += "?offset={}".format(offset)
    js = get_json_from_url(url)
    return js


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def handle_updates(updates):
    global TODAY

    for update in updates["result"]:
        text = update["message"]["text"]
        chat = update["message"]["chat"]["id"]

        if time.time() % 86400 > 32400:
            if (time.time()//86400) - TODAY != 0:
                send_notifications()
                TODAY += 1

        try:
            with open('users/{}.pickle'.format(chat), 'rb') as f:
                stats = pickle.load(f)

        except Exception as e:
            if 'No such file or directory:' in str(e):
                send_message('У нас новый пользователь! Приветствуем {}.'.format(chat), chat_id='267399865')
            else:
                send_message('Ярик, блядь. {} \n  юзер {}'.format(str(e), chat), chat_id='267399865')
            stats = {'warnings': []}
            with open('users/{}.pickle'.format(chat), 'wb') as f:
                pickle.dump(stats, f)

        if text == "/start":
            kb = get_keyboard([['Актуальная информация'], ['Настроить напоминания']])
            send_message(
                "Привет, я бот, присылающий статистику о пыльце и заранее предупреждающий о вспышках цветения.",
                chat, reply_markup=kb)

        elif text.lower() == 'готово':
            kb = get_keyboard([['Актуальная информация'], ['Настроить напоминания']])
            send_message('Отлично.', chat_id=chat, reply_markup=kb)

        elif text == "Настроить напоминания":
            kb = get_keyboard([['Готово'], ['Ольха', 'Орешник'], ['Береза', 'Вяз'], ['Клен', 'Ясень'],
                               ['Ива', 'Дуб'], ['Кипарис', 'Бук'], ['Граб']])
            send_message('Выбери растения, на которые у тебя аллергия. Я буду присылать уведомления, когда '
                         'уровень их частиц в воздухе будет высоким.', chat_id=chat, reply_markup=kb)

        elif text.lower() in trees:
            tree = text.lower()
            if tree in stats['warnings']:
                stats['warnings'].remove(tree)
                kb = get_keyboard([['Готово'], ['Ольха', 'Орешник'], ['Береза', 'Вяз'], ['Клен', 'Ясень'],
                                   ['Ива', 'Дуб'], ['Кипарис', 'Бук'], ['Граб']])
                send_message('Теперь тебе не будут приходить уведомления о {}.'
                             '\n Сейчас ты следишь за {}'.format(tree, ', '.join(stats['warnings'])),
                             chat_id=chat, reply_markup=kb)
                save(stats, chat)

            else:
                stats['warnings'].append(tree)
                kb = get_keyboard([['Готово'], ['Ольха', 'Орешник'], ['Береза', 'Вяз'], ['Клен', 'Ясень'],
                                   ['Ива', 'Дуб'], ['Кипарис', 'Бук'], ['Граб']])
                send_message('Теперь я буду писать об уровне пыльцы {}.'
                             '\n Сейчас ты следишь за {}\n Еще что-нибудь?'.format(tree, ', '.join(stats['warnings'])),
                             chat_id=chat, reply_markup=kb)
                save(stats, chat)

        else:
            send_message(get_allergy_info(), chat)


def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return text, chat_id


def get_keyboard(items):
    reply_markup = {"keyboard": items, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


def main():
    last_update_id = None
    last_update_time = time.time()
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handle_updates(updates)

        if time.time() - last_update_time > 25000:
            parse_allergy_info()
            last_update_time = time.time()

        time.sleep(0.3)


if __name__ == '__main__':
    main()