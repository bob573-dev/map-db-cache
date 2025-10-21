import sys, subprocess
from pathlib import Path

from consts import LOCALES_DOMAIN

try:
    from deep_translator import GoogleTranslator
except:
    GoogleTranslator = None

MSGFMT = ['/usr/bin/msgfmt']
GETTEXT = ['/usr/bin/xgettext']
if sys.platform.startswith('win'):
    MSGFMT = [sys.prefix + '/python', sys.prefix + '/Tools/i18n/msgfmt.py']
    GETTEXT = [sys.prefix + '/python', sys.prefix + '/Tools/i18n/pygettext.py']

TRANSLATOR_ALIASES = {
    'ua': 'uk',
}
INCLUDED_FOLDERS = ('uix',)
ENCODING = 'utf-8'


print(f'Collecting strings ...')
files = [path for path in Path('.').glob("../*.py")]
for folder in INCLUDED_FOLDERS:
    files.extend([path for path in (Path('..') / folder).rglob("*.py")])
subprocess.run([*GETTEXT, '-d', LOCALES_DOMAIN, '-o', f'{LOCALES_DOMAIN}.pot', *files])

for loc in Path('.').glob('*/LC_MESSAGES/*.po'):
    lang = str(loc.parents[1])
    tr = GoogleTranslator(source='en', target=TRANSLATOR_ALIASES.get(lang, lang)) if GoogleTranslator and lang != 'en' else None
    print(f'Merging {lang} @ {loc} {"with auto translation" if tr else ""}...')
    existing = set([s for s in open(loc, encoding=ENCODING).readlines() if s.startswith('msgid ')])
    with open(loc, 'a', encoding=ENCODING) as f:
        for s in open(f'{LOCALES_DOMAIN}.pot', encoding=ENCODING).readlines():
            if s.startswith('msgid ') and s not in existing:
                try:
                    t = tr.translate(s[7:-2]) if tr else ''
                    if t:
                        f.writelines(['\n', "# auto translated\n", s, f'msgstr "{t}"\n'])
                    else:
                        f.writelines(['\n', s, 'msgstr ""\n'])
                except Exception as e:
                    print(f'ERROR:\tfailed {s}\n\t{e}')

for loc in Path('.').glob('*/LC_MESSAGES/*.po'):
    print(f'Compiling {loc} ...')
    subprocess.run([*MSGFMT, '-o', str(loc.with_suffix('.mo')), str(loc)])
