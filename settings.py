############
# SETTINGS #
############

# api auth
apiservice = 'yandex'  # 'google', 'yandex'
apikey = 'Type your api key here'

# i/o directories
rootpath = '.'
resource_path = 'resources'
file_format = '.po'

# you can look supported languages codes of api services at here -
# yandex: https://tech.yandex.ru/translate/doc/dg/concepts/api-overview-docpage/
# google: https://cloud.google.com/translate/docs/languages
main_lang = 'en'  # it's can be empty or None. In this case, language will have determined.
to_langs = ['ru', 'tt', 'ja']

# regular expressions for different format types. <block, key, value> groups must be set
parse_regexp = {
    '.po': r'(?P<block>(#.*\n)*msgid (?P<key>\".*\"\n(?:\".*\"\n)*)msgstr (?P<value>\".*\"\n(?:\".*\"\n)*))',
    # '.xaml': r'Text="{local:Translate (\w+)}"',
    # '.txt': r'(\w+)'
}