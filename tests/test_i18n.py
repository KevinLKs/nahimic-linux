"""Translation completeness, locale matching and persistent language choices."""
import sys
from pathlib import Path
from string import Formatter
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from i18n import CATALOGS, LANGUAGES, Translations, resolve_locale

class TranslationsTest(unittest.TestCase):
    def test_catalogs_preserve_messages_and_placeholders(self):
        source = CATALOGS['en']
        placeholders = lambda text: {field for _,field,_,_ in Formatter().parse(text) if field is not None}
        for code, catalog in CATALOGS.items():
            self.assertEqual(set(source), set(catalog), code)
            for key, text in catalog.items():
                self.assertTrue(text.strip(), (code,key))
                self.assertEqual(placeholders(key), placeholders(text), (code,key))

    def test_system_language_variants_and_fallback(self):
        for names, expected in [(['zh-Hant-HK'],'zh_TW'),(['zh_TW'],'zh_TW'),
                                (['zh-Hans-CN'],'zh_CN'),(['en-GB'],'en'),
                                (['pt-BR'],'pt'),(['ru-RU'],'ru'),
                                (['xx-ZZ','de-DE'],'de'),(['C'],'en')]:
            self.assertEqual(resolve_locale(names),expected)

    def test_selection_survives_new_instance(self):
        with TemporaryDirectory(prefix='nahimic-i18n-', dir='/tmp') as directory:
            path = Path(directory) / 'interface.ini'
            translator = Translations(path)
            self.assertEqual(translator.choice, 'system')
            for code in LANGUAGES:
                translator.select(code)
                restored=Translations(path)
                self.assertEqual(restored.code,code)
                self.assertEqual(restored.text('Audio'), CATALOGS[code]['Audio'])
            translator.select('system')
            self.assertEqual(Translations(path).choice,'system')

if __name__ == '__main__': unittest.main()
