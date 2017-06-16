############
# SETTINGS #
############

# api cloud translating
apiservice = 'yandex'  # 'google', 'yandex'
# get api key
# yandex: https://translate.yandex.ru/developers/keys
# google: https://support.google.com/cloud/answer/6158862?hl=en
apikey = '<Type your api key here>'

# i/o directories
rootpath = '.'
resource_path = 'i18n'
file_format = '.po'

# You can see the codes of the supported languages for the api services here.
# yandex: https://tech.yandex.ru/translate/doc/dg/concepts/api-overview-docpage/
# google: https://cloud.google.com/translate/docs/languages
main_lang = 'en'  # it's can be empty string or None. In this case, language will have determined by cloud translating service.
to_langs = ['ru', 'tt', 'ja']

# regular expressions for different format types. <block, key, value> groups must be set
parse_regexp = {
    '.po': r'(?P<block>(#.*\n)*msgid (?P<key>\".*\"\n(?:\".*\"\n)*)msgstr (?P<value>\".*\"\n(?:\".*\"\n)*))',
}
