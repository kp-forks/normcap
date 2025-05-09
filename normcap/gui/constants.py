"""Global constant strings."""

from normcap.gui.localization import _
from normcap.gui.models import Urls

URLS = Urls(
    releases="https://github.com/dynobo/normcap/releases",
    changelog="https://github.com/dynobo/normcap/blob/main/CHANGELOG",
    pypi="https://pypi.org/pypi/normcap",
    github="https://github.com/dynobo/normcap",
    issues="https://github.com/dynobo/normcap/issues",
    faqs="https://dynobo.github.io/normcap/#faqs",
    website="https://dynobo.github.io/normcap",
    buymeacoffee="https://buymeacoffee.com/dynobo",
)

TESSDATA_REPO = "https://github.com/tesseract-ocr/tessdata_fast"
TESSDATA_BASE_URL = f"{TESSDATA_REPO}/raw/4.1.0/"


# TODO: Link to webpage instead!
CMD_WAYLAND_PERMISSION = (
    "<p><code>"
    "dbus-send --session --print-reply=literal \\<br>"
    "--dest=org.freedesktop.impl.portal.PermissionStore \\<br>"
    "/org/freedesktop/impl/portal/PermissionStore \\<br>"
    "org.freedesktop.impl.portal.PermissionStore.DeletePermission \\<br>"
    "string:'screenshot' string:'screenshot' string:''"
    "</code></p>"
)

CMD_FLATPAK_PERMISSION = (
    "<p><code>"
    "flatpak permission-set screenshot screenshot com.github.dynobo.normcap yes"
    "</code></p>"
)

# L10N: Headline of the missing permissions dialog
PERMISSION_DIALOG_HEADLINE = _(
    "<h3>NormCap is missing the permission for screen capture.</h3>"
)

# L10N: Info at the bottom of the missing permissions dialog
# # Do NOT translate the variables in curly brackets "{some_variable}"!
OPEN_ISSUE_TEXT = _(
    "<small>"
    "If this doesn't resolve the issue, please "
    "<a href='{issues_url}'>report it as a bug</a> on GitHub."
    "</small>"
).format(issues_url=URLS.issues)

# L10N: Error message box on Linux with Wayland only.
# Do NOT translate the variables in curly brackets "{some_variable}"!
PERMISSIONS_TEXT_WAYLAND = _(
    "{headline}"
    "<p>"
    "When launching NormCap for the first time, you should be prompted to grant "
    "permissions for taking or sharing a screenshot."
    "</p><p>"
    "If you declined or the prompt didn't appear, you can try to reset screenshot "
    "permissions for <b><u>all</u></b> applications by running the following "
    "command in a terminal:"
    "</p>"
    "{command}"
).format(
    headline=PERMISSION_DIALOG_HEADLINE,
    command=CMD_WAYLAND_PERMISSION,
)

# L10N: Error message box on Linux for FlatPak package only.
# Do NOT translate the variables in curly brackets "{some_variable}"!
PERMISSIONS_TEXT_FLATPAK = _(
    "{headline}<p>Grant it by running the following command in a terminal:</p>{command}"
).format(
    headline=PERMISSION_DIALOG_HEADLINE,
    command=CMD_FLATPAK_PERMISSION,
)

# L10N: Error message box on macOS only.
# Do NOT translate the variables in curly brackets "{some_variable}"!
PERMISSIONS_TEXT_MACOS = _(
    "<h3>'{application}' is missing the permission for 'Screen Recording'.</h3>"
    "<p>"
    "Grant it via 'System Settings' → "
    "'<a href='x-apple.systempreferences:com.apple.preference.security?"
    "Privacy_ScreenCapture'>Privacy & Security'</a>."
    "</p>"
)

# Info for Language Manager
LANGUAGES = (
    ("afr", "2.5 MB", "Afrikaans", "Afrikaans"),
    ("amh", "5.2 MB", "Amharic", "አማርኛ"),
    ("ara", "1.3 MB", "Arabic", "العربية"),
    ("asm", "1.9 MB", "Assamese", "অসমীয়া"),
    ("aze", "3.3 MB", "Azerbaijani", "آذربایجان دیلی"),
    ("aze_cyrl", "1.8 MB", "Azerbaijani (cyrillic)", "Азәрбајҹан дили"),
    ("bel", "3.5 MB", "Belarusian", "беларуская мова"),
    ("ben", "0.8 MB", "Bengali", "বাংলা"),
    ("bod", "1.8 MB", "Tibetan", "བོད་ཡིག"),
    ("bos", "2.3 MB", "Bosnian", "bosanski jezik"),
    ("bre", "6.0 MB", "Breton", "brezhoneg"),
    ("bul", "1.6 MB", "Bulgarian", "български език"),
    ("cat", "1.0 MB", "Catalan; Valencian", "català"),
    ("ceb", "0.6 MB", "Cebuano", "Sinugbuanong Binisayâ"),
    ("ces", "3.6 MB", "Czech", "čeština; český jazyk"),
    ("chi_sim", "2.3 MB", "Chinese, simplified", "中文; 汉语; 漢語"),
    ("chi_sim_vert", "1.8 MB", "Chinese, simplified (vertical)", "中文; 汉语; 漢語"),
    ("chi_tra", "2.2 MB", "Chinese, traditional", "中文; 汉语; 漢語"),
    ("chi_tra_vert", "1.7 MB", "Chinese, traditional (vertical)", "中文; 汉语; 漢語"),
    ("chr", "0.3 MB", "Cherokee", "ᏣᎳᎩ ᎦᏬᏂᎯᏍᏗ"),
    ("cos", "2.1 MB", "Corsican", "corsu"),
    ("cym", "2.1 MB", "Welsh", "Cymraeg"),
    ("dan", "2.4 MB", "Danish", "dansk"),
    ("dan_frak", "1.6 MB", "Danish (fraktur)", "dansk"),
    ("deu", "1.4 MB", "German", "Deutsch"),
    ("deu_frak", "2.0 MB", "German (fraktur)", "Deutsch"),
    ("div", "1.6 MB", "Divehi; Dhivehi; Maldivian", "ދިވެހި"),
    ("dzo", "0.4 MB", "Dzongkha", "རྫོང་ཁ"),
    ("ell", "1.3 MB", "Greek", "ελληνικά"),
    ("eng", "3.9 MB", "English", "English"),
    ("enm", "2.9 MB", "Middle English (1100-1500)", ""),
    ("epo", "4.5 MB", "Esperanto", "Esperanto"),
    ("equ", "2.1 MB", "Equations; Math", ""),
    ("est", "4.2 MB", "Estonian", "eesti keel"),
    ("eus", "4.9 MB", "Basque", "euskara; euskera"),
    ("fao", "3.2 MB", "Faroese", "føroyskt"),
    ("fas", "0.4 MB", "Persian; Farsi", "فارسی"),
    ("fil", "1.7 MB", "Filipino", "wikang filipino"),
    ("fin", "7.5 MB", "Finnish", "suomen kieli"),
    ("fra", "1.0 MB", "French", "français"),
    ("frk", "6.1 MB", "Frankish", ""),
    ("frm", "1.9 MB", "Middle French (1400-1600)", ""),
    ("fry", "1.8 MB", "Western Frisian", "Frysk"),
    ("gla", "2.9 MB", "Gaelic", "Gàidhlig"),
    ("gle", "1.1 MB", "Irish", "Gaeilge"),
    ("glg", "2.4 MB", "Galician", "galego"),
    ("grc", "2.1 MB", "Ancient Greek (to 1453)", ""),
    ("guj", "1.3 MB", "Gujarati", "ગુજરાતી"),
    ("hat", "1.8 MB", "Haitian", "Kreyòl ayisyen"),
    ("heb", "0.9 MB", "Hebrew", "עברית"),
    ("hin", "1.0 MB", "Hindi", "हिन्दी; हिंदी"),
    ("hrv", "3.9 MB", "Croatian", "hrvatski jezik"),
    ("hun", "5.0 MB", "Hungarian", "magyar"),
    ("hye", "3.3 MB", "Armenian", "Հայերեն"),
    ("iku", "2.6 MB", "Inuktitut", "ᐃᓄᒃᑎᑐᑦ"),
    ("ind", "1.0 MB", "Indonesian", "Bahasa Indonesia"),
    ("isl", "2.1 MB", "Icelandic", "Íslenska"),
    ("ita", "2.5 MB", "Italian", "italiano"),
    ("ita_old", "3.1 MB", "Italian (old)", ""),
    ("jav", "2.8 MB", "Javanese", "ꦧꦱꦗꦮ"),
    ("jpn", "2.3 MB", "Japanese", "日本語; にほんご"),
    ("jpn_vert", "2.9 MB", "Japanese (vertical)", "日本語; にほんご"),
    ("kan", "3.4 MB", "Kannada", "ಕನ್ನಡ"),
    ("kat", "2.4 MB", "Georgian", "ქართული"),
    ("kat_old", "0.4 MB", "Georgian (old)", "ქართული"),
    ("kaz", "4.5 MB", "Kazakh", "қазақ тілі"),
    ("khm", "1.3 MB", "Khmer", "ខ្មែរ; ខេមរភាសា; ភាសាខ្មែរ"),
    ("kir", "9.4 MB", "Kirghiz", "Кыргыз тили"),
    ("kmr", "3.4 MB", "Northern Kurdish", ""),
    ("kor", "1.6 MB", "Korean", "한국어"),
    ("kor_vert", "1.0 MB", "Korean (vertical)", "한국어"),
    ("lao", "6.0 MB", "Lao", "ພາສາລາວ"),
    ("lat", "3.0 MB", "Latin", "lingua latina"),
    ("lav", "2.5 MB", "Latvian", "latviešu valoda"),
    ("lit", "3.0 MB", "Lithuanian", "lietuvių kalba"),
    ("ltz", "2.4 MB", "Luxembourgish", "Lëtzebuergesch"),
    ("mal", "5.0 MB", "Malayalam", "മലയാളം"),
    ("mar", "2.0 MB", "Marathi", "मराठी"),
    ("mkd", "1.5 MB", "Macedonian", "македонски јазик"),
    ("mlt", "2.2 MB", "Maltese", "Malti"),
    ("mon", "2.0 MB", "Mongolian", "Монгол хэл"),
    ("mri", "0.8 MB", "Maori", "te reo Māori"),
    ("msa", "1.6 MB", "Malay", "bahasa Melayu; بهاس ملايو\u200e"),
    ("mya", "4.4 MB", "Burmese", "ဗမာစာ"),
    ("nep", "0.9 MB", "Nepali", "नेपाली"),
    ("nld", "5.7 MB", "Dutch; Flemish", "Nederlands; Vlaams"),
    ("nor", "3.4 MB", "Norwegian", "Norsk"),
    ("oci", "6.0 MB", "Occitan (post 1500)", "lenga d'òc"),
    ("ori", "1.4 MB", "Oriya", "ଓଡ଼ିଆ"),
    ("osd", "10 MB", "Orientation & Script", ""),
    ("pan", "0.4 MB", "Panjabi; Punjabi", "ਪੰਜਾਬੀ; پنجابی\u200e"),
    ("pol", "4.5 MB", "Polish", "język polski"),
    ("por", "1.8 MB", "Portuguese", "português"),
    ("pus", "1.6 MB", "Pushto; Pashto", "پښتو"),
    ("que", "4.7 MB", "Quechua", "Runa Simi; Kichwa"),
    ("ron", "2.2 MB", "Romanian; Moldavian", "limba română"),
    ("rus", "3.6 MB", "Russian", "Русский"),
    ("san", "11 MB", "Sanskrit; Saṁskṛta", "संस्कृतम्"),
    ("sin", "1.6 MB", "Sinhala; Sinhalese", "සිංහල"),
    ("slk", "4.2 MB", "Slovak", "slovenský jazyk"),
    ("slk_frak", "0.8 MB", "Slovak (fraktur)", "slovenský jazyk"),
    ("slv", "2.8 MB", "Slovenian", "slovenski jezik"),
    ("snd", "1.6 MB", "Sindhi", "सिन्धी; سنڌي، سندھی\u200e"),
    ("spa", "2.1 MB", "Spanish; Castilian", "español"),
    ("spa_old", "2.7 MB", "Spanish; Castilian (old)", ""),
    ("sqi", "1.7 MB", "Albanian", "Shqip"),
    ("srp", "2.0 MB", "Serbian", "српски језик"),
    ("srp_latn", "3.1 MB", "Serbian (latin)", "српски језик"),
    ("sun", "1.3 MB", "Sundanese", "Basa Sunda"),
    ("swa", "2.0 MB", "Swahili", "Kiswahili"),
    ("swe", "3.9 MB", "Swedish", "svenska"),
    ("syr", "2.1 MB", "Syriac", "ܠܫܢܐ ܣܘܪܝܝܐ"),
    ("tam", "3.0 MB", "Tamil", "தமிழ்"),
    ("tat", "1.0 MB", "Tatar", "татар теле"),
    ("tel", "2.6 MB", "Telugu", "తెలుగు"),
    ("tgk", "2.4 MB", "Tajik", "тоҷикӣ; toçikī; تاجیکی\u200e"),
    ("tgl", "7.3 MB", "Tagalog", "Wikang Tagalog"),
    ("tha", "1.0 MB", "Thai", "ไทย"),
    ("tir", "0.3 MB", "Tigrinya", "ትግርኛ"),
    ("ton", "0.9 MB", "Tonga", "faka Tonga"),
    ("tur", "4.3 MB", "Turkish", "Türkçe"),
    ("uig", "2.6 MB", "Uighur", "ئۇيغۇرچە\u200e"),
    ("ukr", "3.6 MB", "Ukrainian", "Українська"),
    ("urd", "1.3 MB", "Urdu", "اردو"),
    ("uzb", "6.1 MB", "Uzbek", "أۇزبېك\u200e"),
    ("uzb_cyrl", "1.4 MB", "Uzbek (cyrillic)", "Ўзбек"),
    ("vie", "0.5 MB", "Vietnamese", "Tiếng Việt"),
    ("yid", "0.5 MB", "Yiddish", "ייִדיש"),
    ("yor", "0.9 MB", "Yoruba", "Yorùbá"),
)
