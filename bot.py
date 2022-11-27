import re
from pathlib import Path

import telebot
from telebot.types import InputFile
from logger import log, log_return
from phones_db import init
from phones_db import add
from phones_db import delete
from phones_db import update
from phones_db import lookup
from phones_db import table_as_list_of_tuples

API_TOKEN = '5735432738:AAEFavJj4lXZytjt-PuioVvTcsKH1dKfZis'

bot = telebot.TeleBot(API_TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    log(f'Запуск бота в чате {message.chat.id}.')
    bot.send_message(message.chat.id, 'Бот готов к работе. Для вывода списка команд введите "/help".')


@bot.message_handler(commands=['help'])
def show_commands(message):
    log(f'В чате {message.chat.id} вызвана команда /help.')
    bot.send_message(message.chat.id, '/help - Вывод списка команд.\n'
                                      '/info <команда> - Вывод подробной информации о команде.\n'
                                      '/symbols - Пояснение специальных символов (<>...)')


@bot.message_handler(commands=['symbols'])
def show_symbol_explanation(message):
    log(f'В чате {message.chat.id} вызвана команда /symbols.')
    bot.send_message(message.chat.id, 'В описании команд могут встречаться слова, помеченные специальными символами:\n'
                                      '<abc> - Обязательный параметр.\n'
                                      '*abc* - Необязательный параметр.\n'
                                      '-abc в конце команды - Флаги.\n')


@bot.message_handler(commands=['info'])
def info(message):
    chat = message.chat.id
    log(f'В чате {chat} вызвана команда /info.')
    command = message.text.split(' ')
    if len(command) == 1:
        log('Параметр не указан.')
        reply = 'После команды "/info" необходимо указать название команды, информацию о которой хотите получить.'
    else:
        command = command[1]
        command = command.lower().removeprefix('/')
        log(f'Параметр: {command}.')
        match command:
            case 'info':
                reply = '/info <команда> - Вывод подробной информации о команде.'
            case 'help':
                reply = '/help - Вывод списка команд.'
            case 'symbols':
                reply = '/symbols - Пояснение специальных символов (<>...)'
            case 'add':
                reply = '/add <"имя контакта"> *номер телефона* - Добавление нового контакта в базу данных.\n' \
                        'Можно использовать без номера телефона.\n' \
                        'Кавычки вокруг имени контакта обязательны.'
            case 'remove':
                reply = '/remove <contact/phone> <запись> - Удаление из базы данных контакта со всеми, ' \
                        'привязанными к нему номерами телефонов (если за /remove следует contact) ' \
                        'или номера телефона (если за /remove следует phone).'
            case 'update':
                reply = '/update <contact/phone> <старое значение> <новое значение> - ' \
                        'Замена в базе данных значения на другое.\n' \
                        'Если заменяются контакты, то и старое и новое значение необходимо взять в кавычки.'
            case 'search':
                reply = '/search <contact/phone> <запись> - ' \
                        'Поиск в базе данных контакта по номеру телефона (если за /search следует contact)' \
                        ' или всех телефонов привязанных к контакту (если за /search следует phone).'
            case 'show':
                reply = '/show *contact/phone* - Вывод содержания базы данных. ' \
                        'Если указать contact будет выведен список контактов без номеров телефона, ' \
                        'если указать phone будет выведен список номеров телефона без контактов,' \
                        'если ничего не указывать, будет выведена вся информация.'
            case 'export':
                reply = '/export - Отправка .db файла, содержащего в себе базу данных.'
            case _:
                reply = f'Неизвестная команда "{command}".'
        log(f'Ответ: {reply}.')
    bot.send_message(chat, reply)


def check_number(string):
    pattern = re.compile('\\+?[0-9]+(\\([0-9]+\\))?([0-9]+-?)+[0-9]+')
    return bool(re.fullmatch(pattern, string))


def split_args(string):
    if ' ' not in string:
        return False
    first_space = string.find(' ')
    return string[:first_space], string[first_space + 1:]


@bot.message_handler(commands=['add'])
def db_add(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    log(f'Пользователем с id {user_id} вызвана команда add...')
    text = message.text
    text = text.removeprefix('/add ')
    if text.startswith('"'):
        text = text[1:]
        if '"' in text:
            last_quot_mark = text.rfind('"')
            contact = text[:last_quot_mark]
            text = text[last_quot_mark + 1:]
            if text.startswith(' '):
                text = text[1:]
            elif text:
                bot.send_message(chat_id, log_return('Ошибка: между закрывающей кавычкой имени контакта '
                                                     'и началом номера необходим пробел.'))
                return
            number = False
            if text:
                if check_number(text):
                    number = text
                else:
                    bot.send_message(chat_id, log_return('Ошибка: неправильный номер.'))
                    return
            db_path = f'./phone_databases/{str(user_id)}.db'
            if not Path(db_path).is_file():
                init(db_path)
            res = add(db_path, {'contact_name': f'"{contact}"'}, 'contacts')
            if isinstance(res, str):
                log('Контакт уже существует.')
            if number is not False:
                cont_id = lookup(db_path, ['contact_id'], 'contacts', [f'contact_name="{contact}"'])[0][0]
                res = add(db_path, {'phone_number': f'"{number}"', 'contact': f'{cont_id}'}, 'phones')
                if isinstance(res, str):
                    bot.send_message(chat_id, log_return('Номер уже добавлен.'))
            bot.send_message(chat_id, log_return('Успех.'))
        else:
            bot.send_message(chat_id, log_return('Ошибка: не хватает закрывающей кавычки.'))
    else:
        bot.send_message(chat_id, log_return('Ошибка: имя контакта должно быть обёрнуто кавычками.'))


@bot.message_handler(commands=['remove'])
def db_remove(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    log(f'Пользователем с id {user_id} вызвана команда add...')
    text = message.text.removeprefix('/remove ')
    args = split_args(text)
    if not args:
        bot.send_message(chat_id, log_return('Ошибка: неверное количество аргументов.'))
        return
    mode, value = args
    delete_cont = None
    if mode == 'contact':
        delete_cont = True
    elif mode == 'phone':
        delete_cont = False
    if delete_cont is not None:
        db_path = f'./phone_databases/{str(user_id)}.db'
        if not Path(db_path).is_file():
            bot.send_message(chat_id, log_return('Ошибка: база данных не инициализирована') +
                             ' чтобы инициализировать её добавьте в неё какую-либо запись '
                             'с помощью команды /add (/info add)')
            return
        if delete_cont:
            cont_id = lookup(db_path, ['contact_id'], 'contacts', [f'contact_name="{value}"'])
            if cont_id:
                cont_id = cont_id[0][0]
                res = delete(db_path, 'phones', [f'contact={cont_id}'])
            else:
                res = f'Нет контакта {value}'
            if isinstance(res, str):
                bot.send_message(chat_id, log_return(res))
                return
            res = delete(db_path, 'contacts', [f'contact_name="{value}"'])
            if isinstance(res, str):
                bot.send_message(chat_id, log_return(res))
                return
        else:
            res = delete(db_path, 'phones', [f'phone_number={value}'])
            if isinstance(res, str):
                bot.send_message(chat_id, log_return(res))
                return
        bot.send_message(chat_id, log_return('Успех.'))
    else:
        bot.send_message(chat_id, log_return('Ошибка: первым аргументом должно быть "contact" или "phone"')
                         + ' (/info delete).')


def lookup_to_str(lookup_res):
    if not lookup_res:
        return ''
    res = ''
    for row in lookup_res:
        temp = []
        for item in row:
            temp.append(str(item))
        res += f"{' - '.join(temp)}\n"
    return res


@bot.message_handler(commands=['search'])
def db_search(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    log(f'Пользователем с id {user_id} вызвана команда search...')
    text = message.text.removeprefix('/search ')
    args = split_args(text)
    if args:
        first_arg, second_arg = args
        db_path = f'./phone_databases/{str(user_id)}.db'
        if not Path(db_path).is_file():
            bot.send_message(chat_id, log_return('Ошибка: база данных не инициализирована') +
                             ' чтобы инициализировать её добавьте в неё какую-либо запись '
                             'с помощью команды /add (/info add)')
            return
        if first_arg == 'contact' or first_arg == 'phone':
            if first_arg[0] == 'c':
                cont_id = lookup(db_path, ['contact'], 'phones', [f'phone_number="{second_arg}"'])
                if cont_id:
                    cont_id = cont_id[0][0]
                    res = lookup(db_path, ['contact_name'], 'contacts', [f'contact_id={cont_id}'])
                else:
                    res = 'Результатов не найдено.'
            else:
                cont_id = lookup(db_path, ['contact_id'], 'contacts', [f'contact_name="{second_arg}"'])
                if cont_id:
                    cont_id = cont_id[0][0]
                    res = lookup(db_path, ['phone_number'], 'phones', [f'contact={cont_id}'])
                else:
                    res = 'Результатов не найдено.'
            if isinstance(res, str):
                bot.send_message(chat_id, log_return(res))
            else:
                bot.send_message(chat_id, f'{log_return("Успех")}, результат:\n{lookup_to_str(res)}')
        else:
            bot.send_message(chat_id, log_return('Ошибка: первый аргумент должен быть contact или phone.'))
    else:
        bot.send_message(chat_id, log_return('Ошибка: аргументы должны быть разделены пробелом.'))


@bot.message_handler(commands=['update'])
def db_update(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    log(f'Пользователем с id {user_id} вызвана команда update...')
    text = message.text.removeprefix('/update ')
    args = split_args(text)
    if args:
        first_arg, other_args = args
        if first_arg == 'contact':
            if other_args[0] == '"':
                other_args = other_args[1:]
                if '"' in other_args:
                    first_quot = other_args.find('"')
                    old = other_args[:first_quot]
                    other_args = other_args[first_quot + 1:]
                    if other_args.startswith(' "'):
                        other_args = other_args[2:]
                        if '"' in other_args:
                            new = other_args[:other_args.find('"')]
                            db_path = f'./phone_databases/{str(user_id)}.db'
                            if not Path(db_path).is_file():
                                bot.send_message(chat_id, log_return('Ошибка: база данных не инициализирована')
                                                 + 'чтобы инициализировать, добавьте любую запись '
                                                   'с помощью команды /add')
                                return
                            res = update(db_path, 'contacts', ['contact_name'], [f'"{new}"'], [f'contact_name="{old}"'])
                            if isinstance(res, str):
                                bot.send_message(chat_id, log_return(res))
                            else:
                                bot.send_message(chat_id, log_return('Успех.'))
                        else:
                            bot.send_message(chat_id, log_return('Ошибка: не хватает закрывающих кавычек '
                                                                 'нового значения.'))
                    else:
                        bot.send_message(chat_id, log('Ошибка: новое значение должно идти через пробел после старого '
                                                      'и быть заключено в кавычки.'))
                else:
                    bot.send_message(chat_id, log_return('Ошибка: при изменении имён контактов и старое и '
                                                         'новое значение должны быть заключены в кавычки.'))
            else:
                bot.send_message(chat_id, log_return('Ошибка: при изменении имён контактов старое значение '
                                                     'должно быть заключено в кавычки.'))
        elif first_arg == 'phone':
            args = split_args(other_args)
            if args:
                old, new = args
                if check_number(new):
                    db_path = f'./phone_databases/{str(user_id)}.db'
                    if not Path(db_path).is_file():
                        bot.send_message(chat_id, log_return('Ошибка: база данных не инициализирована')
                                         + ' чтобы инициализировать добавьте любую запись с помощью команды /add.')
                        return
                    res = update(db_path, 'phones', ['phone_number'], [f'"{new}"'], [f'phone_number="{old}"'])
                    if isinstance(res, str):
                        bot.send_message(chat_id, log_return(res))
                    else:
                        bot.send_message(chat_id, log_return('Успех.'))
                else:
                    bot.send_message(chat_id, 'Ошибка: некорректный новый номер.')
            else:
                bot.send_message(chat_id, log_return('Ошибка: не хватает аргументов')
                                 + 'для справки введите /info update')
        else:
            bot.send_message(chat_id, log_return('Ошибка: первый аргумент должен быть contact или phone.'))
    else:
        bot.send_message(chat_id, log_return('Ошибка: не хватает аргументов')
                         + 'чтобы получить информацию об использовании команды введите /info update.')


@bot.message_handler(commands=['show'])
def show(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    log(f'Пользователем с id {user_id} вызвана команда show...')
    text = message.text.removeprefix('/show')
    if text == ' contact' or text == ' phone' or not text:
        db_path = f'./phone_databases/{str(user_id)}.db'
        if not Path(db_path).is_file():
            bot.send_message(chat_id, log_return('Ошибка: база данных не инициализирована')
                             + ' чтобы инициализировать добавьте любую запись с помощью /add.')
            return
        if text == ' contact':
            table = 'contacts'
        elif text == ' phone':
            table = 'phones'
        else:
            table = 'contacts LEFT JOIN phones ON phones.contact = contacts.contact_id'
        res = table_as_list_of_tuples(db_path, table)
        if isinstance(res, str):
            bot.send_message(chat_id, log_return(res))
        else:
            bot.send_message(chat_id, f'{log_return("Успех")} результат:\n{lookup_to_str(res)}')
    else:
        bot.send_message(chat_id, log_return('Ошибка: некорректный аргумент.'))


@bot.message_handler(commands=['export'])
def export(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    log(f'Пользователем с id {user_id} вызвана команда export...')
    db_path = f'./phone_databases/{str(user_id)}.db'
    if Path(db_path).is_file():
        bot.send_document(chat_id, InputFile(db_path))
    else:
        bot.send_message(chat_id, log_return('Ошибка: база данных не инициализирована')
                         + ' чтобы инициализировать добавьте любую запись с помощью /add.')


def launch():
    Path("./phone_databases").mkdir(exist_ok=True)
    log('Бот запущен.')
    bot.polling()


def test():
    print(lookup('./phone_databases/520093936.db', [], 'contacts', ['ROWID=12']))


if __name__ == '__main__':
    launch()
