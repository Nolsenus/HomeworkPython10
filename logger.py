import datetime


indentation = ''


def log_return(message: str):
    log(message)
    return message


def log(message: str):
    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    global indentation
    if message.startswith('Успех') or message.startswith('Ошибка'):
        indentation = indentation.removeprefix('....')
    string = f'{now} {indentation}{message}\n'
    if message.endswith('...'):
        indentation += '....'
    with open('log.txt', 'a', encoding='utf-8') as file:
        file.write(string)
