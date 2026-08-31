"""
E: Minimal CLI i18n helper — language chosen once at startup, all CLI text
   rendered purely in the chosen language (zh or en).
C: 极简 CLI 国际化辅助 — 启动时选定一次语言，全部 CLI 文案以所选语言
   纯单语渲染（zh 或 en）。
"""
LANG = 'zh'  # 'zh' | 'en'


def set_lang(lang: str) -> None:
    """E: Set the CLI interface language / C: 设置 CLI 界面语言"""
    global LANG
    LANG = 'zh' if lang == 'zh' else 'en'


def T(zh: str, en: str) -> str:
    """E: Pick the text in the active language / C: 按当前语言取文案"""
    return zh if LANG == 'zh' else en
