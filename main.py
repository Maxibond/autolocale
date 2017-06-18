# coding=utf
import os
import sys
import time
import re
import settings
import requests
import json

REGEXP = re.compile(settings.parse_regexp[settings.file_format], re.I | re.U)


def detect_modified_files(path, cash=None):
    """
    Обнаруживает изменённые файлы
    :param path: string путь, где искать файлы
    :param cash: dict <key имя файла, value время последнего изменения> 
    :return: tuple <list изменённых имён файлов, type param cash>
    """
    if cash is None:
        cash = {}
    modified = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if not name.endswith(settings.file_format):
                continue
            file_name = os.path.join(root, name)
            mtime = os.stat(file_name).st_mtime
            if cash.get(file_name) != mtime:
                modified.append(file_name)
            cash[file_name] = mtime
    return modified, cash


def exclude_cashed(blocks, cash):
    """
    Исключает из блоков, те которые есть в кэше, а в кэше исключает те, которых больше нет в блоках
    :param blocks: list of dict <lang, <block, key, value>>
    :param cash: список сохранённых блоков
    :return: обновлённые блоки и кэш
    Example:
        Input
        # cash 1 2 3 4 5 , blocks 5 6 1 3 4 7
        Output
        # cash 1 3 4 5, blocks 6 7
    """
    main_lang_cash = list(cash[settings.main_lang])

    # обновление блоков
    for idx_block, block in enumerate(list(blocks)):
        for idx_cash_block, cash_block in enumerate(main_lang_cash):
            if block['key'] == cash_block['key'] and block['value'] == cash_block['value']:
                del blocks[idx_block]
                del main_lang_cash[idx_cash_block]
                continue

    # очистка неактуальных блоков в кэше
    for cash_block in main_lang_cash:
        for lang in cash:
            idx = cash[lang].index(cash_block)
            del cash[lang][idx]

    return blocks, cash


def update_cash(blocks, cash):
    """
    Обновление кэша переведёнными блоками 
    """
    for lang in blocks:
        cash[lang].append(blocks[lang])
    return cash


def run_watcher():
    """
    Запускает наблюдателя, который следит за изменениями необходимых файлов и запускает перевод
    """
    WATCHER_DELAY = 2
    root_path = settings.rootpath
    cash_files = {}
    cash_words = {}
    while True:
        modified, cash_files = detect_modified_files(root_path, cash_files)
        cash_words = process(modified, cash_words)
        time.sleep(WATCHER_DELAY)


def find_words_to_translate(files):
    """
    :param files: список файлов, где нужно искать слова
    Проходит по дереву, начиная из каталога settings.rootpath и парсит файлы формата,
     указанного в настройках при помощи регулярного выражения
    :return: dict найденного блока, ключа и значения
    """
    result = []
    for file_name in files:
        with open(file_name) as file:
            file_text = file.read()
            # в файле находим текст по регулярному выражению
            result = [m.groupdict() for m in REGEXP.finditer(file_text)]
    return result


###############
#
#   API
#
###############


#
#  Yandex
#

def check_code(fn):
    def wrapper(*args, **kwargs):
        code, result = fn(*args, **kwargs)
        if code == '401':
            raise Exception('Yandex: Invalid API key.')
        elif code == '402':
            raise Exception('Yandex: API key have banned.')
        elif code == '404':
            raise Exception('Yandex: Daily volume limit exceeded.')
        elif code == '413':
            raise Exception('Yandex: Text has a very big size.')
        elif code == '422':
            raise Exception('Yandex: Text can\'n be translated.')
        elif code == '501':
            raise Exception('Yandex: Specified translation direction is not supported.')
        return result

    return wrapper


class Yandex:

    @staticmethod
    @check_code
    def translate(words, lang):
        """
        Используя settings.apikey подключается к Yandex Translate API и переводит слова
        :param words: list слов которые нужно перевести
        :param lang: string код языка, на который будет происходить перевод
        :return: tuple: code, list переведенных слов
        """
        api = settings.apikey
        request_url = requests.get('https://translate.yandex.net/api/v1.5/tr.json/translate'
                                   f'?key={api}&lang={lang}')
        request_url += ''.join(f'&text={word}' for word in words)
        result = requests.get(request_url)
        result = json.loads(result.text)
        return result['code'], map(lambda x: x.strip(), result['text'])

    @staticmethod
    @check_code
    def detect_lang(words):
        """
        Используя settings.apikey подключается к Yandex Translate API и определяет язык
        :param words: list слов, для которых нужно определить язык
        :return: tuple: code, str код языка
        """
        api = settings.apikey
        request_url = requests.get("https://translate.yandex.net/api/v1.5/tr.json/detect"
                                   f"?key={api}")
        request_url += "&text=%s" % ''.join(words)
        result = requests.get(request_url)
        result = json.loads(result.text)
        if not result['lang']:
            raise Exception("Can't detect a language. Please, set up a language in settings.")
        return result['code'], result['lang']


#
#  Google
#

class Google:

    @staticmethod
    def translate(words, lang):
        """
        Используя settings.apikey подключается к Google Translate API и переводит слова
        :param words: list слов которые нужно перевести
        :param lang: string код языка, на который будет происходить перевод
        :return: list переведенных слов
        """
        api = settings.apikey
        request_url = "https://translation.googleapis.com/language/translate/v2" \
                      f"?key={api}&target={lang}"
        request_url += ''.join(f'&q={word}' for word in words)
        result = requests.post(request_url)
        result = json.loads(result.text)
        return map(lambda x: x['translatedText'].strip(), result['data']['translations'])

    @staticmethod
    def detect_lang(words):
        """
        Используя settings.apikey подключается к Google Translate API и определяет язык
        :param words: list слов, для которых нужно определить язык
        :return: str код языка
        """
        api = settings.apikey
        request_url = "POST https://translation.googleapis.com/language/translate/v2/detect" \
                      f"?key={api}"
        request_url += '&q=%s' % ', '.join(words)
        result = requests.post(request_url)
        result = json.loads(result.text)
        return result['data']['detections']['language'].strip()


API_SERVICES = {
    'yandex': Yandex,
    'google': Google,
    # При желании можно добавить сюда новый сервис перевода,
    #  а выше реализовать класс с методами translate и detect_lang
}

###############
#
#  END API
#
###############


def translate_blocks(blocks):
    """
    Переводит блоки
    :param blocks: list of dict <block, key, value>
    :return: translated_blocks: dict <lang> of list of dict <block, key, value>
    """
    from_lang = settings.main_lang
    if not from_lang:
        settings.main_lang = detect_lang(blocks)
    to_langs = settings.to_langs
    translated_blocks = {}
    for to_lang in to_langs:
        translated_blocks[to_lang] = translate(blocks, to_lang)
    return translated_blocks


def detect_lang(blocks):
    """
    Используя settings.apiservice подключается к определённому API и определяет язык
    :param blocks: list блоков, для которых нужно определить язык
    :return: str код языка
    """
    service = settings.apiservice
    words = [x['value'] for x in blocks][:5]  # берётся небольшой и достаточный кусок данных для определения языка
    return API_SERVICES[service].detect_lang(words)


def _update_block(block, new_value):
    """
    Обновить блок новым значением
    :param block: dict <block, key, value>
    :param new_value: string
    :return: type param block
    """
    block['block'] = re.sub(REGEXP, new_value, block['block'])
    return block


def translate(blocks, lang):
    """
    Используя settings.apiservice подключается к определённому API и переводит слова
    :param blocks: list блоков которые нужно перевести
    :param lang: string код языка, на который будет происходить перевод
    :return: list переведенных блоков
    """
    service = settings.apiservice
    words = [x['value'] for x in blocks]
    translated_words = API_SERVICES[service].translate(words, lang)
    translated_blocks = list(blocks)
    for block, new_value in zip(translated_blocks, translated_words):
        _update_block(block, new_value)
    return blocks


def _create_path(resource_path):
    """
    Создаёт путь resource_path если он не существует
    :param resource_path: string
    """
    if not os.path.exists(resource_path):
        os.makedirs(resource_path)


def _generate_resource_file(blocks, coding_name):
    """
    Создаёт файл того же формата
    :param blocks: list блоков
    :param coding_name: string имя файла
    """
    with open(os.path.join(settings.resource_path, f'{coding_name}.{settings.file_format}'),
              'w', encoding='utf-8') as resource_file:
        for block in blocks:
            resource_file.write(block['block'])


def generate_resource_files(blocks):
    """
    Функция создающая все файлы локализации на перведенные языки.
    :param blocks: list блоков, которые нужно перевести и создать файлы
    """
    from_lang = settings.main_lang
    to_langs = settings.to_langs
    _create_path(settings.resource_path)
    for to_lang in to_langs:
        coding_name = '%s-%s' % (from_lang, to_lang)
        _generate_resource_file(blocks, coding_name)


def process(files=None, cash=None):
    """
    :param files: список файлов или None, если нужно искать все
    :param cash: список сохранённых блоков
    Главная функция локализации
    в результате функция создаст файлы локализации
    """
    if files is None:
        files, _ = detect_modified_files(settings.rootpath)
    blocks_to_translate = find_words_to_translate(files)
    if isinstance(cash, dict):
        blocks_to_translate, cash = exclude_cashed(blocks_to_translate, cash)
    translated_blocks = translate_blocks(blocks_to_translate)
    if isinstance(cash, dict):
        translated_blocks = update_cash(translated_blocks, cash)
    generate_resource_files(translated_blocks)
    return cash


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--watcher':
        run_watcher()
    process()
