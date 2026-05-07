"""
APLUSE ENGINE - 主题配置模块
将主题配色数据与 QSS 模板分离，采用现代化的 UI 色彩系统设计。
"""

# 主题名称列表（与 palettes 列表索引一一对应）
THEME_NAMES =[
    "暗色极客 (Geek Zinc)",
    "亮色极简 (Clean Light)",
    "渐变幽蓝 (Deep Ocean)",
    "暗金奢华 (Obsidian Gold)",
    "猛男猛粉 (Cyber Neon)",
    "辐射废土 (Wasteland)",
    "低调暗紫 (Dark Violet)",
]

# 主题配色方案列表
PALETTES =[
    {  # 0: 暗色极客 - 采用深灰(Zinc)和低饱和度靛蓝，适合长期凝视的护眼黑客主题
        "BG_MAIN": "#09090B", "BG_CARD": "#18181B", "BORDER": "#27272A",
        "TEXT_MAIN": "#F4F4F5", "TEXT_SUB": "#A1A1AA", "TEXT_TITLE": "#FAFAFA",
        "BTN_SEC": "#27272A", "BTN_SEC_HOVER": "#3F3F46", "BTN_SEC_TEXT": "#E4E4E7",
        "PRI_START": "#4F46E5", "PRI_END": "#7C3AED", "PRI_H_START": "#6366F1", "PRI_H_END": "#8B5CF6",
        "LIST_BG": "#09090B", "LIST_ITEM": "#18181B", "LIST_HOVER": "#27272A", "LIST_SEL": "#4F46E5",
        "TERM_BG": "#050505", "TERM_TEXT": "#34D399", "SHADOW": "rgba(0,0,0,80)",
        "DIS_BG": "rgba(255, 255, 255, 0.03)", "DIS_TEXT": "rgba(255, 255, 255, 0.2)",
        "DIS_BORDER": "rgba(255, 255, 255, 0.08)", "DIS_PRI_BG": "rgba(255, 255, 255, 0.05)",
        "INPUT_DIS_BG": "rgba(255, 255, 255, 0.02)",
    },
    {  # 1: 亮色极简 - 类似 macOS 的冷白色调，阴影柔和，UI元素边缘清爽
        "BG_MAIN": "#F8FAFC", "BG_CARD": "#FFFFFF", "BORDER": "#E2E8F0",
        "TEXT_MAIN": "#0F172A", "TEXT_SUB": "#64748B", "TEXT_TITLE": "#020617",
        "BTN_SEC": "#F1F5F9", "BTN_SEC_HOVER": "#E2E8F0", "BTN_SEC_TEXT": "#334155",
        "PRI_START": "#3B82F6", "PRI_END": "#6366F1", "PRI_H_START": "#60A5FA", "PRI_H_END": "#818CF8",
        "LIST_BG": "#F8FAFC", "LIST_ITEM": "#FFFFFF", "LIST_HOVER": "#F1F5F9", "LIST_SEL": "#3B82F6",
        "TERM_BG": "#F1F5F9", "TERM_TEXT": "#0369A1", "SHADOW": "rgba(0,0,0,20)",
        "DIS_BG": "rgba(0, 0, 0, 0.03)", "DIS_TEXT": "rgba(0, 0, 0, 0.3)",
        "DIS_BORDER": "rgba(0, 0, 0, 0.1)", "DIS_PRI_BG": "rgba(0, 0, 0, 0.06)",
        "INPUT_DIS_BG": "rgba(0, 0, 0, 0.02)",
    },
    {  # 2: 渐变幽蓝 - 午夜深蓝底色搭配青蓝(Cyan)色渐变发光，富有科幻质感
        "BG_MAIN": "#020617", "BG_CARD": "#0F172A", "BORDER": "#1E293B",
        "TEXT_MAIN": "#F8FAFC", "TEXT_SUB": "#94A3B8", "TEXT_TITLE": "#38BDF8",
        "BTN_SEC": "#1E293B", "BTN_SEC_HOVER": "#334155", "BTN_SEC_TEXT": "#E2E8F0",
        "PRI_START": "#0EA5E9", "PRI_END": "#2563EB", "PRI_H_START": "#38BDF8", "PRI_H_END": "#3B82F6",
        "LIST_BG": "#020617", "LIST_ITEM": "#0F172A", "LIST_HOVER": "#1E293B", "LIST_SEL": "#0284C7",
        "TERM_BG": "#000000", "TERM_TEXT": "#38BDF8", "SHADOW": "rgba(14,165,233,40)",
        "DIS_BG": "rgba(255, 255, 255, 0.04)", "DIS_TEXT": "rgba(255, 255, 255, 0.3)",
        "DIS_BORDER": "rgba(255, 255, 255, 0.1)", "DIS_PRI_BG": "rgba(255, 255, 255, 0.08)",
        "INPUT_DIS_BG": "rgba(255, 255, 255, 0.02)",
    },
    {  # 3: 暗金奢华 - 黑曜石底色与拉丝香槟金搭配，高贵内敛
        "BG_MAIN": "#0E0E0E", "BG_CARD": "#171717", "BORDER": "#2D281F",
        "TEXT_MAIN": "#EAE6E1", "TEXT_SUB": "#A39A88", "TEXT_TITLE": "#E2C881",
        "BTN_SEC": "#24221E", "BTN_SEC_HOVER": "#36332C", "BTN_SEC_TEXT": "#E2C881",
        "PRI_START": "#CBA358", "PRI_END": "#A67C2E", "PRI_H_START": "#E5C27C", "PRI_H_END": "#B88B35",
        "LIST_BG": "#0E0E0E", "LIST_ITEM": "#171717", "LIST_HOVER": "#24221E", "LIST_SEL": "#4A3A1C",
        "TERM_BG": "#080808", "TERM_TEXT": "#D1B570", "SHADOW": "rgba(203,163,88,25)",
        "DIS_BG": "rgba(255, 255, 255, 0.03)", "DIS_TEXT": "rgba(226, 200, 129, 0.3)",
        "DIS_BORDER": "rgba(203, 163, 88, 0.15)", "DIS_PRI_BG": "rgba(203, 163, 88, 0.1)",
        "INPUT_DIS_BG": "rgba(255, 255, 255, 0.02)",
    },
    {  # 4: 猛男猛粉 - 纯粹的 Outrun 赛博黑粉系，极高的对比与视觉冲击力
        "BG_MAIN": "#0D0208", "BG_CARD": "#1A0B16", "BORDER": "#4A1535",
        "TEXT_MAIN": "#FCE7F3", "TEXT_SUB": "#F472B6", "TEXT_TITLE": "#F9A8D4",
        "BTN_SEC": "#331024", "BTN_SEC_HOVER": "#4D1B37", "BTN_SEC_TEXT": "#FBCFE8",
        "PRI_START": "#D946EF", "PRI_END": "#BE185D", "PRI_H_START": "#E879F9", "PRI_H_END": "#E11D48",
        "LIST_BG": "#0D0208", "LIST_ITEM": "#1A0B16", "LIST_HOVER": "#331024", "LIST_SEL": "#9D174D",
        "TERM_BG": "#050003", "TERM_TEXT": "#F472B6", "SHADOW": "rgba(217,70,239,35)",
        "DIS_BG": "rgba(255, 255, 255, 0.04)", "DIS_TEXT": "rgba(244, 114, 182, 0.4)",
        "DIS_BORDER": "rgba(217, 70, 239, 0.2)", "DIS_PRI_BG": "rgba(217, 70, 239, 0.12)",
        "INPUT_DIS_BG": "rgba(255, 255, 255, 0.02)",
    },
    {  # 5: 辐射废土 - 废土灰褐色 + 经典 PIP-Boy 绿色荧光
        "BG_MAIN": "#1A1C19", "BG_CARD": "#242722", "BORDER": "#3B4236",
        "TEXT_MAIN": "#D1D6CD", "TEXT_SUB": "#9AA096", "TEXT_TITLE": "#A3E635",
        "BTN_SEC": "#32382F", "BTN_SEC_HOVER": "#454C41", "BTN_SEC_TEXT": "#D1D6CD",
        "PRI_START": "#65A30D", "PRI_END": "#4D7C0F", "PRI_H_START": "#84CC16", "PRI_H_END": "#65A30D",
        "LIST_BG": "#1A1C19", "LIST_ITEM": "#242722", "LIST_HOVER": "#32382F", "LIST_SEL": "#4D7C0F",
        "TERM_BG": "#0D0E0C", "TERM_TEXT": "#84CC16", "SHADOW": "rgba(101,163,13,30)",
        "DIS_BG": "rgba(255, 255, 255, 0.03)", "DIS_TEXT": "rgba(163, 230, 53, 0.3)",
        "DIS_BORDER": "rgba(101, 163, 13, 0.2)", "DIS_PRI_BG": "rgba(101, 163, 13, 0.1)",
        "INPUT_DIS_BG": "rgba(255, 255, 255, 0.02)",
    },
    {  # 6: 低调暗紫 - Discord / Vercel 风格的优雅紫黑色体系
        "BG_MAIN": "#0A0118", "BG_CARD": "#130927", "BORDER": "#2A1654",
        "TEXT_MAIN": "#F5F3FF", "TEXT_SUB": "#A78BFA", "TEXT_TITLE": "#C4B5FD",
        "BTN_SEC": "#20103E", "BTN_SEC_HOVER": "#311A5C", "BTN_SEC_TEXT": "#EDE9FE",
        "PRI_START": "#8B5CF6", "PRI_END": "#6D28D9", "PRI_H_START": "#A78BFA", "PRI_H_END": "#7C3AED",
        "LIST_BG": "#0A0118", "LIST_ITEM": "#130927", "LIST_HOVER": "#20103E", "LIST_SEL": "#5B21B6",
        "TERM_BG": "#05000A", "TERM_TEXT": "#D8B4FE", "SHADOW": "rgba(139,92,246,30)",
        "DIS_BG": "rgba(255, 255, 255, 0.03)", "DIS_TEXT": "rgba(167, 139, 250, 0.3)",
        "DIS_BORDER": "rgba(139, 92, 246, 0.2)", "DIS_PRI_BG": "rgba(139, 92, 246, 0.1)",
        "INPUT_DIS_BG": "rgba(255, 255, 255, 0.02)",
    },
]


def build_qss(p: dict) -> str:
    """根据配色字典生成完整的 QSS 样式表。"""
    return f"""
        QWidget {{ font-family: "Segoe UI", "Microsoft YaHei", sans-serif; font-size: 13px; color: {p['TEXT_MAIN']}; }}

        QMessageBox {{ background-color: {p['BG_CARD']}; }}
        QMessageBox QLabel {{ color: {p['TEXT_MAIN']}; background: transparent; font-size: 13px; }}
        QMessageBox QPushButton {{ min-width: 72px; padding: 6px 16px; }}

        ::selection {{ background-color: {p['PRI_H_START']}; color: white; }}

        QFrame#mainContainer {{ background-color: {p['BG_MAIN']}; border: 1px solid {p['BORDER']}; border-radius: 12px; }}
        QFrame#titleBar {{ background-color: {p['BG_MAIN']}; border-top-left-radius: 12px; border-top-right-radius: 12px; border-bottom: 1px solid {p['BORDER']}; }}
        QLabel#titleLabel {{ color: {p['TEXT_TITLE']}; font-size: 13px; font-weight: bold; letter-spacing: 0.5px; }}

        QPushButton#toolboxHeader {{
            background: {p['BG_CARD']}; color: {p['TEXT_SUB']}; border: 1px solid {p['BORDER']};
            border-radius: 8px; text-align: left; padding: 6px 14px; font-size: 13px; font-weight: 600;
        }}
        QPushButton#toolboxHeader:hover {{ background: {p['LIST_HOVER']}; color: {p['TEXT_MAIN']}; }}
        QFrame#toolboxContent {{ background: {p['BG_CARD']}; border: 1px solid {p['BORDER']}; border-top: none; border-radius: 0 0 8px 8px; }}

        QPushButton#macClose, QPushButton#macMin, QPushButton#macMax {{
            padding: 0px !important; margin: 0px !important;
            border-radius: 7px;
            min-width: 14px; min-height: 14px; max-width: 14px; max-height: 14px;
        }}
        QPushButton#macMin {{ background-color: #F59E0B; border: 1px solid #D97706; }}
        QPushButton#macMin:hover {{ background-color: #FBBF24; }}
        QPushButton#macMax {{ background-color: #22C55E; border: 1px solid #16A34A; }}
        QPushButton#macMax:hover {{ background-color: #4ADE80; }}
        QPushButton#macClose {{ background-color: #EF4444; border: 1px solid #DC2626; }}
        QPushButton#macClose:hover {{ background-color: #F87171; }}

        QComboBox#themeCombo {{ background-color: {p['BTN_SEC']}; color: {p['TEXT_MAIN']}; border: 1px solid {p['BORDER']}; border-radius: 6px; padding: 4px 10px; font-weight: bold; }}
        QComboBox#themeCombo:hover {{ background-color: {p['BTN_SEC_HOVER']}; }}
        QComboBox#themeCombo::drop-down {{ border: none; }}
        QComboBox#themeCombo QAbstractItemView {{ background-color: {p['BG_CARD']}; color: {p['TEXT_MAIN']}; border: 1px solid {p['BORDER']}; selection-background-color: {p['PRI_START']}; border-radius: 6px; }}

        QFrame#card {{ background-color: {p['BG_CARD']}; border: 1px solid {p['BORDER']}; border-radius: 10px; }}
        QLabel#cardTitle {{ color: {p['TEXT_MAIN']}; font-size: 15px; font-weight: bold; }}
        QLabel#subText {{ color: {p['TEXT_SUB']}; font-size: 12px; }}
        QLabel#badge {{ background: {p['BORDER']}; color: {p['TEXT_MAIN']}; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; }}

        QListWidget#darkList {{
            background: {p['LIST_BG']}; border: 1px dashed {p['BORDER']}; border-radius: 8px; outline: none; padding: 6px; color: {p['TEXT_MAIN']}; font-size: 13px;
        }}
        QListWidget#darkList[drag="active"] {{ border: 2px dashed {p['PRI_H_START']}; background: {p['LIST_HOVER']}; }}
        QListWidget#darkList::item {{ padding: 8px 10px; border-radius: 6px; margin-bottom: 3px; background: {p['LIST_ITEM']}; border: 1px solid transparent; }}
        QListWidget#darkList::item:hover {{ background: {p['LIST_HOVER']}; border-color: {p['BORDER']}; }}
        QListWidget#darkList::item:selected {{ background: {p['LIST_SEL']}; color: white; border-color: {p['PRI_H_START']}; }}

        QLineEdit#neonInput {{
            background: {p['LIST_BG']}; border: 1px solid {p['BORDER']}; border-radius: 6px; padding: 8px 12px; color: {p['PRI_H_START']}; font-family: "Consolas", monospace; font-weight: bold;
        }}
        QLineEdit#neonInput:focus {{ border: 1px solid {p['PRI_H_START']}; background: {p['LIST_ITEM']}; }}

        QTextEdit#terminal {{
            background: {p['TERM_BG']}; color: {p['TERM_TEXT']}; border: 1px solid {p['BORDER']};
            font-family: "Consolas", monospace; font-size: 13px; border-radius: 8px; line-height: 1.5; padding: 10px;
        }}

        QProgressBar#neonProgress {{ background: {p['BORDER']}; border: none; border-radius: 3px; }}
        QProgressBar#neonProgress::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['PRI_START']}, stop:1 {p['PRI_END']}); border-radius: 3px; }}

        QPushButton {{ border: none; border-radius: 6px; padding: 8px 14px; font-weight: 600; }}

        QPushButton[role="primary"] {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['PRI_START']}, stop:1 {p['PRI_END']});
            color: white; font-size: 14px; letter-spacing: 1px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        QPushButton[role="primary"]:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['PRI_H_START']}, stop:1 {p['PRI_H_END']});
            border: 1px solid rgba(255, 255, 255, 0.25);
        }}

        QPushButton[role="secondary"] {{ background: {p['BTN_SEC']}; color: {p['BTN_SEC_TEXT']}; border: 1px solid {p['BORDER']}; }}
        QPushButton[role="secondary"]:hover {{ background: {p['BTN_SEC_HOVER']}; border: 1px solid {p['TEXT_SUB']}; }}

        QPushButton[role="accent"] {{ background: transparent; color: {p['PRI_H_START']}; border: 1px solid {p['PRI_START']}; }}
        QPushButton[role="accent"]:hover {{ background: {p['PRI_START']}; color: white; }}

        QPushButton[role="danger"] {{ background: transparent; color: #F43F5E; border: 1px solid #E11D48; }}
        QPushButton[role="danger"]:hover {{ background: #E11D48; color: white; }}

        QPushButton:disabled {{
            background: {p['DIS_BG']}; color: {p['DIS_TEXT']}; border: 1px dashed {p['DIS_BORDER']};
        }}
        QPushButton[role="primary"]:disabled {{
            background: {p['DIS_PRI_BG']}; color: {p['DIS_TEXT']}; border: 1px solid {p['DIS_BORDER']};
        }}
        QLineEdit:disabled {{
            background: {p['INPUT_DIS_BG']}; color: {p['DIS_TEXT']}; border: 1px solid {p['DIS_BORDER']};
        }}

        QScrollBar:horizontal {{ border: none; background: transparent; height: 0px; margin: 0px; }}
        QScrollBar::handle:horizontal {{ background: transparent; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

        QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {p['BORDER']}; border-radius: 3px; }}
        QScrollBar::handle:vertical:hover {{ background: {p['TEXT_SUB']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    """


def parse_shadow_color(shadow_str: str):
    """从 rgba 字符串中解析 QColor 参数，返回 (r, g, b, a) 或 None。"""
    rgb = shadow_str.replace("rgba(", "").replace(")", "").split(",")
    if len(rgb) == 4:
        return int(rgb[0]), int(rgb[1]), int(rgb[2]), int(rgb[3])
    return None