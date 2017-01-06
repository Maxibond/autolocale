# coding=utf

# 1. Проходить по всему проекту с форматом xaml (обход по дереву)
# 2. Находить Text="{local:Translate %s}"
# 3. Создать по пути в настройках файлы resx
# Имя=Перевод
# 4. Используя Yandex API переводить %s

import os
import re
import settings

def find_words_to_translate():
    path_to_find = settings.rootpath
    regexp = re.compile(r'Text="{local:Translate (\w+)}"', re.I | re.U)
    result = set()
    for root, dirs, files in os.walk(path_to_find):
        for file_name in files:
            if '.xaml' not in file_name:
                continue
            # прочитываем файлы и по регулярке набираем слова для перевода
            with open(os.path.join(root, file_name)) as file:
                file_text_lines = file.readlines()
                for line in file_text_lines:
                    result |= set(regexp.findall(line))
    return list(result)


def translate(api, words, lang):
    import requests
    import json
    request_url = "https://translate.yandex.net/api/v1.5/tr.json/translate?key={0}&lang={1}".format(api, lang)
    request_url += ('&text=%s' * len(words)) % tuple(words)
    result = requests.post(request_url)
    result = json.loads(result.text)
    return map(lambda x: x.strip(), result['text'])


def _create_path(resource_path):
    if not os.path.exists(resource_path):
        os.makedirs(resource_path)


def _generate_resource_file(words, translated_words, coding_name):
    with open(os.path.join(settings.resource_path, '%s.resx' % coding_name), 'w', encoding='utf-8') as resource_file:
        for _from, _to in zip(words, translated_words):
            resource_file.write('%s=%s\n' % (_from, _to))


def generate_resource_files(words):
    from_lang = settings.main_lang
    to_langs = settings.to_langs
    _create_path(settings.resource_path)
    for to_lang in to_langs:
        coding_name = '%s-%s' % (from_lang, to_lang)
        translated_words = translate(settings.apikey, words, coding_name)
        _generate_resource_file(words, translated_words, coding_name)


# главная функция локализации
# в результате функция создаст .resx-файлы [и вернёт статистику выполнения]
def process():
    words_to_translate = find_words_to_translate()
    generate_resource_files(words_to_translate)


if __name__ == '__main__':
    process()
