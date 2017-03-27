apikey = 'Type your api key here'
rootpath = 'files_to_translate'
resource_path = 'resources'
# you can look languages codes here - https://tech.yandex.ru/translate/doc/dg/concepts/api-overview-docpage/
main_lang = 'en'
to_langs = ['ru', 'tt', 'ja']
parse_regexp = {
    '.xaml': r'Text="{local:Translate (\w+)}"',
    '.txt': r'(\w+)'
}
