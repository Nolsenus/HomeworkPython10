import sqlite3
from logger import log
from logger import log_return


def get_tables(db_name):
    log('Попытка получить список таблиц...')
    con = sqlite3.connect(db_name)
    try:
        cur = con.cursor()
        tables = map(lambda x: x[0], cur.execute('SELECT name FROM sqlite_master'))
        tables = list(filter(lambda x: not x.startswith('sqlite'), tables))
        log('Успех.')
    except sqlite3.Error as error:
        tables = log_return(f'Ошибка: {error}')
    finally:
        con.close()
    return tables


def get_column_names(db_name: str, table: str):
    log(f'Попытка получить название столбцов из таблицы {table}...')
    con = sqlite3.connect(db_name)
    try:
        cur = con.cursor()
        result = list(map(lambda x: x[0], cur.execute(f"SELECT name FROM PRAGMA_TABLE_INFO('{table}')")))
        log('Успех.')
    except sqlite3.Error as error:
        result = log_return(f'Ошибка: {error}')
    finally:
        con.close()
    return result


def valid_condition(db_name, table: str, condition: list):
    log(f'Проверка условия {condition}...')
    if not condition:
        log('Успех, условия нет.')
        return True
    modded = []
    for cond in condition:
        mod = cond.replace('>', ';>').replace('<', ';<')
        if ';' not in mod:
            mod = mod.replace('=', ';=')
        modded.append(mod)
    splits = []
    for cond in modded:
        splits.append(cond.split(';'))
    columns = list(map(lambda x: x[0], splits))
    real_columns = get_column_names(db_name, table)
    real_columns.append('ROWID')
    for column in columns:
        if column not in real_columns:
            log('Успех, условие некорректно.')
            return False
    log('Успех, условие корректно.')
    return True


def condition_list_to_str(condition: list):
    return ' '.join(condition)


def add(db_name: str, row: dict, table: str):
    log(f'Попытка добавить строку {row} в таблицу {table}...')
    columns = get_column_names(db_name, table)
    if isinstance(columns, str):
        return log_return(columns)
    columns = columns[1:]
    con = sqlite3.connect(db_name)
    try:
        con.execute('PRAGMA foreign_keys = 1')
        cur = con.cursor()
        last_id = list(cur.execute(f'SELECT ROWID FROM {table} ORDER BY ROWID DESC LIMIT 1'))
        if last_id:
            last_id = last_id[0][0]
        else:
            last_id = 0
        if len(columns) == len(row.keys()):
            full_match = True
            values = [str(last_id + 1)]
            for column in columns:
                if column not in row.keys():
                    full_match = False
                    break
                values.append(row[column])
            if full_match:
                values = ', '.join(values)
                cur.execute(f'INSERT INTO {table} VALUES ({values});')
                con.commit()
                success = True
                log('Успех.')
            else:
                success = log_return('Ошибка: несовпадение столбцов в таблице и полученной строке.')
        else:
            success = log_return('Ошибка: '
                                 'количество столбцов таблицы не совпадает с количеством строк в полученной строке.')
    except sqlite3.Error as error:
        success = log_return(f'Ошибка: {error}.')
    finally:
        con.close()
    return success


def lookup(db_name: str, look_for: list, table: str, condition=None):
    log(f'Попытка поиска ({look_for}, {table}, {condition})...')
    columns = get_column_names(db_name, table)
    columns.append('ROWID')
    if isinstance(columns, str):
        return log_return(columns)
    columns = columns
    can_return = True
    for col in look_for:
        if col not in columns:
            can_return = False
            break
    if condition is None:
        condition = []
    if can_return and valid_condition(db_name, table, condition):
        if not look_for:
            look_for = '*'
        else:
            look_for = ', '.join(look_for)
        query = f'SELECT {look_for} FROM {table}'
        if condition:
            cond = condition_list_to_str(condition)
            query += ' WHERE ' + cond
        con = sqlite3.connect(db_name)
        try:
            cur = con.cursor()
            res = list(cur.execute(query))
            log('Успех.')
        except sqlite3.Error as error:
            res = log_return(f'Ошибка: {error}')
        finally:
            con.close()
    else:
        res = log_return('Ошибка: нельзя выделить указанные столбцы по указанному условию.')
    return res


def update(db_name: str, table: str, columns: list, values: list, condition=None):
    log(f'Попытка заменить столбцы {columns} в таблице {table} на значения {values} по условию {condition}...')
    if len(columns) != len(values):
        res = log_return('Ошибка: количество заменяемых значений не совпадает с количеством подставляемых значений.')
        return res
    column_names = get_column_names(db_name, table)[1:]
    columns_exist = True
    for column in columns:
        if column not in column_names:
            columns_exist = False
            break
    if condition is None:
        condition = []
    if columns_exist and valid_condition(db_name, table, condition):
        replacements = ', '.join(map(lambda x: '' + columns[x] + ' = ' + values[x], range(len(columns))))
        condition = condition_list_to_str(condition)
        con = sqlite3.connect(db_name)
        try:
            con.execute('PRAGMA foreign_keys = 1')
            cur = con.cursor()
            if condition:
                cur.execute(f'UPDATE {table} SET {replacements} WHERE {condition}')
            else:
                cur.execute(f'UPDATE {table} SET {replacements}')
            con.commit()
            log('Успех.')
            res = True
        except sqlite3.Error as error:
            res = log_return(f'Ошибка: {error}')
        finally:
            con.close()
    elif columns_exist:
        res = log_return(f'Ошибка: некорректное условие {condition}.')
    else:
        res = log_return(f'Ошибка: некорректные столбцы для замены {columns}.')
    return res


def update_ids(db_name: str, table: str):
    log('Обновление id...')
    con = sqlite3.connect(db_name)
    try:
        cur = con.cursor()
        ids = list(map(lambda x: x[0], list(cur.execute(f'SELECT ROWID FROM {table} ORDER BY ROWID ASC'))))
        if not ids:
            log('Успех - не осталось элементов.')
            return True
        if len(ids) == 1:
            if ids[0] != 1:
                if table == 'contacts':
                    cur.execute(f'UPDATE phones SET contact=1 WHERE contact={ids[0]}')
                cur.execute(f'UPDATE {table} SET ROWID = 1')
                log('Успех - id единственного оставшегося элемента установлен на 1.')
            else:
                log('Успех - id единственного оставшегося элемента уже 1.')
        else:
            correct_ids = list(range(1, 1 + len(ids)))
            if not correct_ids == ids:
                for i in range(len(ids)):
                    if ids[i] != correct_ids[i]:
                        if table == 'contacts':
                            cur.execute(f'UPDATE phones SET contact = {correct_ids[i]} WHERE contact = {ids[i]}')
                        cur.execute(f'UPDATE {table} SET ROWID = {correct_ids[i]} WHERE ROWID = {ids[i]}')
                log('Успех - все id установлены на корректные значения.')
            else:
                log('Успех - все id уже установлены на корректные значения.')
        con.commit()
        res = True
    except sqlite3.Error as error:
        res = log_return(f'Ошибка: {error}')
    finally:
        con.close()
    return res


def delete(db_name: str, table: str, condition: list):
    log(f'Попытка удалить записи из таблицы {table} по условию {condition}...')
    if condition == ['']:
        condition = []
    if valid_condition(db_name, table, condition):
        con = sqlite3.connect(db_name)
        try:
            con.execute('PRAGMA foreign_keys = 1')
            cur = con.cursor()
            if condition:
                condition = condition_list_to_str(condition)
                cur.execute(f'DELETE FROM {table} WHERE {condition}')
            else:
                cur.execute(f'DELETE FROM {table}')
            con.commit()
            update_ids(db_name, table)
            log('Успех.')
            res = True
        except sqlite3.Error as error:
            res = log_return(f'Ошибка: {error}')
        finally:
            con.close()
    else:
        res = log_return(f'Ошибка: некорректное условие: {condition}')
    return res


def table_as_list_of_tuples(db_name: str, table: str):
    log(f'Попытка передать таблицу {table}...')
    con = sqlite3.connect(db_name)
    try:
        cur = con.cursor()
        res = list(cur.execute(f'SELECT * FROM {table}'))
        log('Успех.')
    except sqlite3.Error as error:
        res = log_return(f'Ошибка: {error}')
    finally:
        con.close()
    return res


def init(db_name):
    log('Инициализация базы данных...')
    connection = sqlite3.connect(db_name)
    try:
        cursor = connection.cursor()
        cursor.execute('''CREATE TABLE contacts(
                           contact_id INTEGER PRIMARY KEY,
                           contact_name TEXT NOT NULL UNIQUE);''')
        cursor.execute('''CREATE TABLE phones(
                               phone_id INTEGER PRIMARY KEY,
                               phone_number TEXT NOT NULL UNIQUE,
                               contact INTEGER NOT NULL,
                               FOREIGN KEY (contact) REFERENCES contacts(contact_id));''')
        log('Успех.')
        res = True
    except sqlite3.Error as error:
        res = f'Ошибка - {str(error)}.'
    finally:
        connection.close()
    return res
