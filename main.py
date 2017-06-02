# coding=utf

# 1. Проходить по всему проекту с форматом xaml (обход по дереву)
# 2. Находить слова по регулярному выражению
# 3. Создать по пути в настройках файлы resx
# Имя=Перевод
# 4. Используя Yandex API переводить %s

import os
import sys
import time
import re
import settings
import requests
import json


def detect_modified_files(path, formats, cash=None):
    if cash is None:
        cash = {}
    modified = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith(settings.file_format):
                continue
            file_name = os.path.join(root, name)
            mtime = os.stat(file_name).st_mtime
            if cash.get(file_name) != mtime:
                modified.append(file_name)
            cash[file_name] = mtime
    return modified, cash


def run_watcher():
    """
    Запускает наблюдателя, который следит за изменениями необходимых файлов и запускает перевод
    """
    WATCHER_DELAY = 2
    root_path = settings.rootpath
    formats = settings.parse_regexp.keys()
    cash_files = {}  # ключ: имя файла, значение: время изменения
    cash_words = {}  # ключ: имя файла, значение: словарь ключ и слово
    while True:
        modified, cash_files = detect_modified_files(root_path, formats, cash_files)
        # process(modified)
        print(modified)
        # datetime.fromtimestamp(int(os.stat('main.py').st_mtime))
        time.sleep(WATCHER_DELAY)


def find_words_to_translate(files):
    """
    :param files: список файлов, где нужно искать слова
    Проходит по дереву, начиная из каталога settings.rootpath и парсит файлы xaml в поисках регулярного выражения
    settings.parse_regexp
    :return: dict найденного блока, ключа и значения
    """
    regexps = {form: re.compile(regexp, re.I | re.U) for form, regexp in settings.parse_regexp.items()}
    # прочитываем файлы и по регулярке набираем слова для перевода
    result = []
    for file_name in files:
        file_format = settings.file_format
        with open(file_name) as file:
            file_text = file.read()
            result = [m.groupdict() for m in regexps[file_format].finditer(file_text)]
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
    # todo: add from_lang for translating
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
    words = [x['value'] for x in blocks][:5]
    return API_SERVICES[service].detect_lang(words)


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
        block['block'] = block['block'].replace(f"msgstr {block['value']}", f"msgstr {new_value}")
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


def process(files=None):
    """
    :param files: список файлов или None, если нужно искать все
    Главная функция локализации
    в результате функция создаст .resx-файлы
    """
    if files is None:
        files, _ = detect_modified_files(settings.rootpath, settings.parse_regexp.keys())
    blocks_to_translate = find_words_to_translate(files)
    translated_blocks = translate_blocks(blocks_to_translate)
    generate_resource_files(translated_blocks)

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '--watcher':
        run_watcher()
    process()
