# coding=utf

# 1. Проходить по всему проекту с форматом xaml (обход по дереву)
# 2. Находить слова по регулярному выражению
# 3. Создать по пути в настройках файлы resx
# Имя=Перевод
# 4. Используя Yandex API переводить %s

import os
import re
import settings


def find_words_to_translate():
    """
    Проходит по дереву, начиная из каталога settings.rootpath и парсит файлы xaml в поисках регулярного выражения
    settings.parse_regexp
    :return: list найденных слов
    """
    regexps = settings.parse_regexp
    formats = settings.parse_regexp.keys()
    path_to_find = settings.rootpath
    # компилируем регулярные выражения
    regexps = {form: re.compile(regexp, re.I | re.U) for form, regexp in regexps.items()}
    result = set()
    for root, dirs, files in os.walk(path_to_find):
        for file_name in files:
            # опеределение формата, если находим, то будем иметь опред. регулярное выражение, иначе пропустим
            current_format = None
            for form in formats:
                if form in file_name:
                    current_format = form
                    break
            if not current_format:
                continue
            # прочитываем файлы и по регулярке набираем слова для перевода
            with open(os.path.join(root, file_name)) as file:
                file_text_lines = file.readlines()
                for line in file_text_lines:
                    result |= set(regexps[current_format].findall(line))
    return list(result)


def translate_yandex(words, lang):
    """
    Используя settings.apikey подключается к Yandex Translate API и переводит слова
    :param words: list слов которые нужно перевести
    :param lang: string код языка, на который будет происходить перевод
    :return: list переведенных слов
    """
    import requests
    import json
    api = settings.apikey
    request_url = "https://translate.yandex.net/api/v1.5/tr.json/translate?key={0}&lang={1}".format(api, lang)
    request_url += ('&text=%s' * len(words)) % tuple(words)
    result = requests.post(request_url)
    result = json.loads(result.text)
    return map(lambda x: x.strip(), result['text'])


def translate_google(words, lang):
    """
    Используя settings.apikey подключается к Google Translate API и переводит слова
    :param words: list слов которые нужно перевести
    :param lang: string код языка, на который будет происходить перевод
    :return: list переведенных слов
    """
    import requests
    import json
    api = settings.apikey
    request_url = "https://translation.googleapis.com/language/translate/v2?key={0}&target={1}".format(api, lang)
    request_url += ('&q=%s' * len(words)) % tuple(words)
    result = requests.post(request_url)
    result = json.loads(result.text)
    return map(lambda x: x['translatedText'].strip(), result['data']['translations'])


def translate(words, lang):
    """
    Используя settings.apiservice подключается к определённому API и переводит слова
    :param words: list слов которые нужно перевести
    :param lang: string код языка, на который будет происходить перевод
    :return: list переведенных слов
    """
    service = settings.apiservice
    return {
        'yandex': translate_yandex,
        'google': translate_google,
    }[service](words, lang)


def _create_path(resource_path):
    """
    Создаёт путь resource_path если он не существует
    :param resource_path: string
    """
    if not os.path.exists(resource_path):
        os.makedirs(resource_path)


def _generate_resource_file(words, translated_words, coding_name):
    """
    Создаёт resx-файл, формат main_language_word=translated_word с именем main_lang-to_lang.resx
    :param words: list слов первого языка
    :param translated_words: list слов второго языка
    :param coding_name: string имя файла
    """
    with open(os.path.join(settings.resource_path, '%s.resx' % coding_name), 'w', encoding='utf-8') as resource_file:
        for _from, _to in zip(words, translated_words):
            resource_file.write('%s=%s\n' % (_from, _to))


def generate_resource_files(words):
    """
    Функция создающая все resx файлы на перведенные языки.
    :param words: list слов, которые нужно перевести и создать файлы
    """
    from_lang = settings.main_lang
    to_langs = settings.to_langs
    _create_path(settings.resource_path)
    for to_lang in to_langs:
        coding_name = '%s-%s' % (from_lang, to_lang)
        translated_words = translate(words, coding_name)
        _generate_resource_file(words, translated_words, coding_name)
    _generate_resource_file(words, words, '%s-%s' % (from_lang, from_lang))  # создаёт файл и на основной язык


def process():
    """
    Главная функция локализации
    в результате функция создаст .resx-файлы
    """
    words_to_translate = find_words_to_translate()
    generate_resource_files(words_to_translate)


if __name__ == '__main__':
    process()
