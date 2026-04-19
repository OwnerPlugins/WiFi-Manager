# -*- coding: utf-8 -*-

import gettext
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

__author__ = "Lululla"
__email__ = "ekekaz@gmail.com"
__copyright__ = "Copyright (c) 2024 Lululla"
__license__ = "GPL-v2"
__version__ = "1.2"

PluginLanguageDomain = "WiFiManager"
PluginLanguagePath = "Extensions/WiFiManager/locale"


def localeInit():
    if PluginLanguageDomain and PluginLanguagePath:
        gettext.bindtextdomain(
            PluginLanguageDomain,
            resolveFilename(
                SCOPE_PLUGINS,
                PluginLanguagePath))


def _(txt):
    translated = gettext.dgettext(PluginLanguageDomain, txt)
    if translated:
        return translated
    else:
        print(
            "[%s] fallback to default translation for %s" %
            (PluginLanguageDomain, txt))
        return gettext.gettext(txt)


localeInit()
language.addCallback(localeInit)
