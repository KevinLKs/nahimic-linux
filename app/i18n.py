"""UI translations and per-user language preferences."""
import json
from pathlib import Path
from PySide6.QtCore import QLocale, QSettings
from PySide6.QtWidgets import QWidget

LANGUAGES = {
    'zh_CN': '简体中文', 'zh_TW': '繁體中文', 'en': 'English', 'ja': '日本語',
    'ko': '한국어', 'de': 'Deutsch', 'fr': 'Français', 'es': 'Español',
    'pt': 'Português', 'it': 'Italiano', 'ru': 'Русский', 'tr': 'Türkçe',
}
CATALOGS = {code: json.loads((Path(__file__).with_name('locales') / (code + '.json')).read_text())
            for code in LANGUAGES}

def resolve_locale(names):
    for name in names:
        parts = name.replace('-', '_').split('_')
        base = parts[0].lower()
        if base == 'zh':
            return 'zh_TW' if any(p.lower() in ('hant', 'tw', 'hk', 'mo') for p in parts[1:]) else 'zh_CN'
        if base in LANGUAGES:
            return base
    return 'en'

class Translations:
    def __init__(self, path):
        self.settings = QSettings(str(path), QSettings.IniFormat)
        self.choice = self.settings.value('language', 'system')
        self.code = self.resolve(self.choice)
        self.bindings = {}

    def resolve(self, choice):
        if choice == 'system':
            return resolve_locale(QLocale.system().uiLanguages())
        if choice not in LANGUAGES:
            raise ValueError('Unknown interface language: ' + str(choice))
        return choice

    def text(self, source, **values):
        return CATALOGS[self.code][source].format(**values)

    def bind(self, widget, attribute, source, **values):
        self.bindings[(widget, attribute)] = (source, values)
        getattr(widget, 'set' + attribute[0].upper() + attribute[1:])(self.text(source, **values))

    def capture(self, root):
        # Capture only static, catalogued strings; dynamic labels bind explicitly.
        for widget in [root] + root.findChildren(QWidget):
            for attribute in ('text', 'windowTitle', 'toolTip', 'accessibleName'):
                getter = getattr(widget, attribute, None)
                if getter:
                    value = getter()
                    if value in CATALOGS['zh_CN'] and (widget, attribute) not in self.bindings:
                        self.bind(widget, attribute, value)

    def select(self, choice):
        code = self.resolve(choice)
        self.settings.setValue('language', choice)
        self.settings.sync()
        if self.settings.status() != QSettings.NoError:
            self.settings.setValue('language', self.choice)
            raise OSError(self.text('无法保存语言设置'))
        self.choice, self.code = choice, code
        self.retranslate()

    def retranslate(self):
        for (widget, attribute), (source, values) in self.bindings.items():
            getattr(widget, 'set' + attribute[0].upper() + attribute[1:])(self.text(source, **values))
