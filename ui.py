
import sys
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QKeySequence
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFileDialog, QShortcut,
    QTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox, QLineEdit,
    QListWidget, QListWidgetItem, QFrame, QGridLayout, QProgressBar,
    QGraphicsDropShadowEffect, QComboBox, QMenu
)

from core import (
    DisguiseEngine, DisguiseError, collect_files_from_paths,
    PathManager, magic_to_display_text, format_file_size,
)
from themes import PALETTES, THEME_NAMES, build_qss, parse_shadow_color


# =================== 通用异步工作线程 ===================

class EngineWorker(QThread):
    """通用引擎工作线程，通过传入 callable 复用于不同任务。"""
    log_sig = pyqtSignal(str)
    prog_sig = pyqtSignal(int, int, str, str)
    done_sig = pyqtSignal(object)
    err_sig = pyqtSignal(str)

    def __init__(self, task_fn, *args):
        super().__init__()
        self.task_fn = task_fn
        self.extra_args = args

    def run(self):
        try:
            result = self.task_fn(
                self.prog_sig.emit,
                self.log_sig.emit,
                *self.extra_args,
            )
            self.done_sig.emit(result)
        except Exception as e:
            self.err_sig.emit(str(e))


# =================== 现代化 UI 组件 ===================

class CustomTitleBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(48)
        self.setObjectName("titleBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)
        
        title_label = QLabel("✨ APLUSE ENGINE v3.4")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEME_NAMES)
        self.theme_combo.setObjectName("themeCombo")
        self.theme_combo.currentIndexChanged.connect(self.parent.change_theme)
        layout.addWidget(self.theme_combo)
        
        layout.addSpacing(16)
        
        self.btn_min = QPushButton()
        self.btn_min.setObjectName("macMin")
        self.btn_min.clicked.connect(self.parent.showMinimized)
        self.btn_min.setToolTip("最小化")
        
        self.btn_max = QPushButton()
        self.btn_max.setObjectName("macMax")
        self.btn_max.clicked.connect(self.toggle_maximize)
        self.btn_max.setToolTip("最大化/还原")

        self.btn_close = QPushButton()
        self.btn_close.setObjectName("macClose")
        self.btn_close.clicked.connect(self.parent.close)
        self.btn_close.setToolTip("关闭")
        
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent.dragPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if self.parent.isMaximized():
                self.parent.showNormal()
            self.parent.move(self.parent.pos() + event.globalPos() - self.parent.dragPos)
            self.parent.dragPos = event.globalPos()


class CustomDropList(QListWidget):
    def __init__(self, placeholder_text, drop_type, window_ref):
        super().__init__()
        self.placeholder_text = placeholder_text
        self.drop_type = drop_type
        self.window_ref = window_ref
        self.placeholder_color = "#52525B"
        
        self.setAcceptDrops(True)
        self.setObjectName("darkList")
        self.setSelectionMode(QListWidget.ExtendedSelection)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWordWrap(True)

    def set_placeholder_color(self, hex_color):
        self.placeholder_color = hex_color
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setProperty("drag", "active")
            self.style().unpolish(self); self.style().polish(self)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("drag", "none")
        self.style().unpolish(self); self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("drag", "none")
        self.style().unpolish(self); self.style().polish(self)
        paths =[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            if self.drop_type == "target": 
                self.window_ref.ui_add_target_paths(paths)
            elif self.drop_type == "mask": 
                self.window_ref.ui_add_mask_paths(paths)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.setPen(QColor(self.placeholder_color))
            font = self.font()
            font.setPointSize(13)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self.placeholder_text)


# =================== 主窗口 ===================

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.engine = DisguiseEngine()
        self.current_worker = None
        self.current_theme_index = 0

        # 初始化日志文件
        self.log_file_path = PathManager.get_persist_dir() / "apluse.log"

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.init_ui()
        self._setup_shortcuts()

        # 从核心配置中读取持久化的主题索引
        saved_theme = self.engine.config.get("theme_index", 0)

        self.title_bar.theme_combo.setCurrentIndex(saved_theme)
        self.change_theme(saved_theme)

        self.refresh_mask_list()
        self.refresh_magic_ui()
        self.cb_log("APLUSE ENGINE 初始化成功")

    def init_ui(self):
        self.resize(1280, 860)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        self.container = QFrame()
        self.container.setObjectName("mainContainer")

        # 更现代、柔和的阴影表现
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(self.shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        container_layout.addWidget(self.title_bar)

        dashboard_layout = QVBoxLayout()
        dashboard_layout.setContentsMargins(24, 20, 24, 24)
        dashboard_layout.setSpacing(16)

        # ==================== 顶行：密钥 + 状态 ====================
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        magic_card = QFrame()
        magic_card.setObjectName("card")
        m_layout = QVBoxLayout(magic_card)
        m_layout.setContentsMargins(20, 16, 20, 16)
        
        m_header = QHBoxLayout()
        m_header.addWidget(self.make_label("🔑 核心密钥 (MAGIC WORD)", "cardTitle"))
        self.magic_info_label = self.make_label("当前状态：未加载", "subText")
        m_header.addStretch()
        m_header.addWidget(self.magic_info_label)
        m_layout.addLayout(m_header)

        m_input_row = QHBoxLayout()
        self.magic_edit = QLineEdit()
        self.magic_edit.setObjectName("neonInput")
        self.magic_edit.setPlaceholderText("输入 ASCII 或 HEX 密钥...")
        m_input_row.addWidget(self.magic_edit, 1)

        btn_apply = self.make_btn("应用", "accent")
        btn_apply.clicked.connect(self.ui_apply_magic)
        btn_rand = self.make_btn("随机", "secondary")
        btn_rand.clicked.connect(self.ui_rand_magic)
        btn_reset = self.make_btn("默认", "danger")
        btn_reset.clicked.connect(self.ui_reset_magic)

        m_input_row.addWidget(btn_apply)
        m_input_row.addWidget(btn_rand)
        m_input_row.addWidget(btn_reset)
        m_layout.addLayout(m_input_row)
        top_row.addWidget(magic_card, 2)

        stat_card = QFrame()
        stat_card.setObjectName("card")
        stat_layout = QVBoxLayout(stat_card)
        stat_layout.setContentsMargins(20, 16, 20, 16)
        stat_layout.addWidget(self.make_label("📡 系统状态", "cardTitle"))
        self.status_label = self.make_label(f"持久化：\n{PathManager.get_persist_dir()}", "subText")
        self.status_label.setWordWrap(True)
        stat_layout.addWidget(self.status_label)
        stat_layout.addStretch()
        top_row.addWidget(stat_card, 1)

        dashboard_layout.addLayout(top_row)

        # ==================== 中行：目标 + 面具 ====================
        file_row = QHBoxLayout()
        file_row.setSpacing(16)

        # 目标卡片
        t_card = QFrame()
        t_card.setObjectName("card")
        t_layout = QVBoxLayout(t_card)
        t_layout.setContentsMargins(20, 16, 20, 16)
        
        t_header = QHBoxLayout()
        t_header.addWidget(self.make_label("🎯 目标执行队列", "cardTitle"))
        self.t_count_label = self.make_label("0 项", "badge")
        t_header.addWidget(self.t_count_label)
        t_header.addStretch()
        
        # 将原有的独立按钮行折叠进 Header，视觉更清爽
        self.btn_t_add = self.make_btn("➕ 文件", "secondary")
        self.btn_t_add.clicked.connect(self.ui_select_targets)
        self.btn_t_add.setToolTip("Ctrl+O")
        self.btn_t_add_dir = self.make_btn("📁 目录", "secondary")
        self.btn_t_add_dir.clicked.connect(self.ui_select_target_folder)
        self.btn_t_rm = self.make_btn("➖ 移除", "secondary")
        self.btn_t_rm.clicked.connect(self.ui_rm_targets)
        self.btn_t_rm.setToolTip("Delete")
        self.btn_t_clr = self.make_btn("🗑️ 清空", "danger")
        self.btn_t_clr.clicked.connect(self.ui_clr_targets)
        
        t_header.addWidget(self.btn_t_add)
        t_header.addWidget(self.btn_t_add_dir)
        t_header.addWidget(self.btn_t_rm)
        t_header.addWidget(self.btn_t_clr)
        t_layout.addLayout(t_header)

        self.target_list = CustomDropList("📥 拖拽目标文件/文件夹至此", "target", self)
        t_layout.addWidget(self.target_list)
        file_row.addWidget(t_card)

        # 面具卡片
        mask_card = QFrame()
        mask_card.setObjectName("card")
        mask_layout = QVBoxLayout(mask_card)
        mask_layout.setContentsMargins(20, 16, 20, 16)
        
        m_header = QHBoxLayout()
        m_header.addWidget(self.make_label("🎭 伪装面具图库", "cardTitle"))
        self.m_count_label = self.make_label("0 项", "badge")
        m_header.addWidget(self.m_count_label)
        m_header.addStretch()
        
        self.btn_m_add = self.make_btn("➕ 文件", "secondary")
        self.btn_m_add.clicked.connect(self.ui_select_masks)
        self.btn_m_add.setToolTip("Ctrl+Shift+O")
        self.btn_m_add_dir = self.make_btn("📁 目录", "secondary")
        self.btn_m_add_dir.clicked.connect(self.ui_select_mask_folder)
        self.btn_m_rm = self.make_btn("➖ 移除", "secondary")
        self.btn_m_rm.clicked.connect(self.ui_rm_masks)
        self.btn_m_rm.setToolTip("Delete")
        self.btn_m_clr = self.make_btn("🗑️ 清空", "danger")
        self.btn_m_clr.clicked.connect(self.ui_clr_masks)
        
        m_header.addWidget(self.btn_m_add)
        m_header.addWidget(self.btn_m_add_dir)
        m_header.addWidget(self.btn_m_rm)
        m_header.addWidget(self.btn_m_clr)
        mask_layout.addLayout(m_header)

        self.mask_list = CustomDropList("🖼️ 拖拽面具文件/文件夹至此", "mask", self)
        mask_layout.addWidget(self.mask_list)
        file_row.addWidget(mask_card)

        dashboard_layout.addLayout(file_row, 1)

        # ==================== 底行：日志 + 操作 ====================
        bot_row = QHBoxLayout()
        bot_row.setSpacing(16)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 16, 20, 20)
        
        log_header = QHBoxLayout()
        log_header.addWidget(self.make_label("📝 运行日志", "cardTitle"))
        log_header.addStretch()
        log_layout.addLayout(log_header)
        
        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("terminal")
        self.log_edit.setReadOnly(True)
        log_layout.addWidget(self.log_edit)
        bot_row.addWidget(log_card, 2)

        act_card = QFrame()
        act_card.setObjectName("card")
        act_layout = QVBoxLayout(act_card)
        act_layout.setContentsMargins(20, 16, 20, 20)
        
        act_layout.addWidget(self.make_label("⚙️ 控制面板", "cardTitle"))
        
        # 进度指示器区
        prog_layout = QVBoxLayout()
        prog_layout.setSpacing(8)
        self.progress_label = self.make_label("等待任务指令...", "subText")
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("neonProgress")
        self.progress_bar.setFixedHeight(6)  # 细版进度条更具现代感
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        prog_layout.addWidget(self.progress_label)
        prog_layout.addWidget(self.progress_bar)
        act_layout.addLayout(prog_layout)

        act_layout.addStretch()

        # 功能网格
        tools_layout = QGridLayout()
        tools_layout.setSpacing(12)
        
        self.btn_detect = self.make_btn("🔍 扫描分析队列", "secondary")
        self.btn_detect.clicked.connect(self.ui_detect)
        self.btn_detect.setToolTip("Ctrl+D")
        tools_layout.addWidget(self.btn_detect, 0, 0)

        # 恢复程序菜单
        self.btn_gen = self.make_btn("📦 生成恢复程序", "secondary")
        gen_menu = QMenu(self)
        act_gen_exe = gen_menu.addAction("🪟 Windows 恢复程序 (.exe)")
        act_gen_apk = gen_menu.addAction("📱 Android 恢复包 (.apk)")
        act_gen_exe.triggered.connect(self.ui_gen_exe)
        act_gen_apk.triggered.connect(self.ui_gen_apk)
        self.btn_gen.setMenu(gen_menu)
        tools_layout.addWidget(self.btn_gen, 0, 1)

        act_layout.addLayout(tools_layout)
        act_layout.addSpacing(12)

        self.btn_toggle = self.make_btn("⚡ 启动引擎", "primary")
        self.btn_toggle.setFixedHeight(50)
        self.btn_toggle.clicked.connect(self.ui_toggle)
        self.btn_toggle.setToolTip("Ctrl+Enter")
        # 使主按钮字体醒目
        font = self.btn_toggle.font()
        font.setBold(True)
        font.setPointSize(11)
        self.btn_toggle.setFont(font)
        
        act_layout.addWidget(self.btn_toggle)

        bot_row.addWidget(act_card, 1)
        dashboard_layout.addLayout(bot_row)

        container_layout.addLayout(dashboard_layout)
        main_layout.addWidget(self.container)

    def _toggle_toolbox(self):
        """展开/收起生成工具栏。"""
        if not hasattr(self, 'toolbox_content'): return
        is_visible = self.toolbox_content.isVisible()
        if is_visible:
            # 收起
            self.toolbox_content.setMaximumHeight(0)
            self.toolbox_content.setVisible(False)
            self.toolbox_header.setText("📦 生成工具  ▸")
        else:
            # 展开
            self.toolbox_content.setVisible(True)
            self.toolbox_content.setMaximumHeight(16777215)
            self.toolbox_header.setText("📦 生成工具  ▾")

    def make_label(self, text, obj_name):
        lbl = QLabel(text)
        lbl.setObjectName(obj_name)
        return lbl

    def make_btn(self, text, role="default"):
        btn = QPushButton(text)
        btn.setProperty("role", role)
        return btn

    def _setup_shortcuts(self):
        """注册全局键盘快捷键。"""
        # Ctrl+O: 添加目标文件
        sc_open = QShortcut(QKeySequence("Ctrl+O"), self)
        sc_open.activated.connect(self.ui_select_targets)

        # Ctrl+Shift+O: 添加面具文件
        sc_open_mask = QShortcut(QKeySequence("Ctrl+Shift+O"), self)
        sc_open_mask.activated.connect(self.ui_select_masks)

        # Delete: 删除选中项（根据焦点所在列表判断）
        sc_del = QShortcut(QKeySequence("Delete"), self)
        sc_del.activated.connect(self._on_delete_key)

        # Ctrl+D: 扫描分析
        sc_detect = QShortcut(QKeySequence("Ctrl+D"), self)
        sc_detect.activated.connect(self.ui_detect)

        # Ctrl+Enter: 启动引擎
        sc_toggle = QShortcut(QKeySequence("Ctrl+Return"), self)
        sc_toggle.activated.connect(self.ui_toggle)

    def _on_delete_key(self):
        """Delete 键按下时，删除焦点列表中的选中项。"""
        focused = self.focusWidget()
        if focused is self.target_list:
            self.ui_rm_targets()
        elif focused is self.mask_list:
            self.ui_rm_masks()

    def change_theme(self, index):
        self.current_theme_index = index

        # 主题切换时，自动保存索引到 JSON 配置文件
        if hasattr(self, 'engine'):
            self.engine.config["theme_index"] = index
            self.engine.save_config()

        p = PALETTES[index]

        self.target_list.set_placeholder_color(p["TEXT_SUB"])
        self.mask_list.set_placeholder_color(p["TEXT_SUB"])

        shadow_rgba = parse_shadow_color(p["SHADOW"])
        if shadow_rgba:
            self.shadow.setColor(QColor(*shadow_rgba))

        self.setStyleSheet(build_qss(p))


    # ======== UI 交互方法 ========

    def set_ui_busy(self, busy: bool):
        controls =[
            self.btn_t_add, self.btn_t_add_dir, self.btn_t_rm, self.btn_t_clr,
            self.btn_detect, self.btn_m_add, self.btn_m_add_dir, self.btn_m_rm,
            self.btn_m_clr, self.btn_gen, self.magic_edit,
            self.btn_toggle, self.title_bar.theme_combo,
        ]
        for c in controls: c.setEnabled(not busy)
        self.target_list.setEnabled(not busy)
        self.mask_list.setEnabled(not busy)
        
        self.btn_toggle.setText("⚡ 引擎高转速处理中..." if busy else "⚡ 启动引擎")

    def cb_log(self, text: str):
        self.log_edit.append(f"> {text}")
        scrollbar = self.log_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 同步写入日志文件
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {text}\n")
        except Exception:
            pass  # 日志写入失败不应影响主流程

    def cb_progress(self, curr, total, title, detail):
        self.progress_bar.setValue(0 if total <= 0 else int((curr / total) * 100))
        self.progress_label.setText(f"{title} | {detail}")

    def refresh_status(self):
        t_count = len(self.engine.target_files)
        m_count = len(self.engine.mask_library)
        # 计算目标文件总大小
        t_total = 0
        for p in self.engine.target_files:
            try:
                t_total += Path(p).stat().st_size
            except Exception:
                pass
        t_size_str = format_file_size(t_total) if t_count > 0 else ""
        self.t_count_label.setText(f"{t_count} 项" + (f"  {t_size_str}" if t_size_str else ""))
        self.m_count_label.setText(f"{m_count} 项")

    def _make_file_item(self, filepath: str) -> QListWidgetItem:
        """创建带文件大小信息的列表项。"""
        try:
            size_str = format_file_size(Path(filepath).stat().st_size)
        except Exception:
            size_str = "?"
        display = f"{filepath}    [{size_str}]"
        item = QListWidgetItem(display)
        item.setData(Qt.UserRole, filepath)  # 存储原始路径，用于后续操作
        return item

    def refresh_target_list(self):
        self.target_list.clear()
        for f in self.engine.target_files:
            self.target_list.addItem(self._make_file_item(f))
        self.refresh_status()

    def refresh_mask_list(self):
        self.mask_list.clear()
        for f in self.engine.mask_library:
            self.mask_list.addItem(self._make_file_item(f))
        self.refresh_status()

    def refresh_magic_ui(self):
        m = self.engine.get_magic_bytes()
        self.magic_edit.setText(m.hex().upper())
        self.magic_info_label.setText(f"生效指令：{magic_to_display_text(m)}")

    def ui_apply_magic(self):
        try:
            magic = self.engine.parse_and_set_magic(self.magic_edit.text())
            self.refresh_magic_ui()
            self.cb_log(f"已覆写系统密钥：{magic.hex().upper()}")
        except Exception as e:
            QMessageBox.warning(self, "密钥异常", str(e))

    def ui_rand_magic(self):
        try:
            self.engine.generate_random_magic()
            self.refresh_magic_ui()
            self.cb_log("已生成动态安全密钥")
        except Exception as e: QMessageBox.warning(self, "异常", str(e))

    def ui_reset_magic(self):
        self.engine.reset_magic()
        self.refresh_magic_ui()
        self.cb_log("已回退至出厂默认密钥")

    def ui_add_target_paths(self, paths):
        added = 0
        for f in collect_files_from_paths(paths):
            if f not in self.engine.target_files:
                self.engine.target_files.append(f)
                added += 1
        self.refresh_target_list()
        self.cb_log(f"目标装载: +{added} 项")

    def ui_select_targets(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择目标文件")
        if paths:
            self.ui_add_target_paths(paths)

    def ui_select_target_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder:
            self.ui_add_target_paths([folder])

    def ui_rm_targets(self):
        selected = self.target_list.selectedItems()
        if not selected:
            return
        sels = {i.data(Qt.UserRole) for i in selected}
        self.engine.target_files = [p for p in self.engine.target_files if p not in sels]
        self.refresh_target_list()
        self.cb_log(f"目标释放: -{len(sels)} 项")

    def ui_clr_targets(self):
        self.engine.target_files.clear()
        self.refresh_target_list()
        self.cb_log("目标队列已格式化")

    def ui_add_mask_paths(self, paths):
        added = 0
        for f in collect_files_from_paths(paths):
            if f not in self.engine.mask_library:
                self.engine.mask_library.append(f)
                added += 1
        self.engine.save_config()
        self.refresh_mask_list()
        self.cb_log(f"面具库扩充: +{added} 项")

    def ui_select_masks(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择面具文件")
        if paths:
            self.ui_add_mask_paths(paths)

    def ui_select_mask_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择面具文件夹")
        if folder:
            self.ui_add_mask_paths([folder])

    def ui_rm_masks(self):
        selected = self.mask_list.selectedItems()
        if not selected:
            return
        sels = {i.data(Qt.UserRole) for i in selected}
        self.engine.mask_library =[p for p in self.engine.mask_library if p not in sels]
        self.engine.save_config()
        self.refresh_mask_list()
        self.cb_log(f"面具库清理: -{len(sels)} 项")

    def ui_clr_masks(self):
        self.engine.mask_library.clear()
        self.engine.save_config()
        self.refresh_mask_list()
        self.cb_log("外观面具库已格式化")

    def ui_detect(self):
        if not self.engine.target_files:
            return self.cb_log("中断: 目标队列为空")
        self.set_ui_busy(True)
        self.current_worker = EngineWorker(self.engine.detect_status)
        self.current_worker.log_sig.connect(self.cb_log)
        self.current_worker.prog_sig.connect(self.cb_progress)
        self.current_worker.done_sig.connect(self._on_detect_done)
        self.current_worker.err_sig.connect(self._on_worker_err)
        self.current_worker.start()

    def _on_detect_done(self, result):
        self.set_ui_busy(False)
        o, d, f = result
        self.cb_progress(1, 1, "分析完毕", f"原装:{o} | 伪装:{d} | 异常:{len(f)}")
        if f:
            for line in f:
                self.cb_log(f"[WARN] {line}")

    def ui_toggle(self):
        if not self.engine.target_files:
            return self.cb_log("中断: 目标队列为空")
        count = len(self.engine.target_files)
        reply = QMessageBox.question(
            self, "确认执行",
            f"即将对 {count} 个文件执行自动伪装/还原操作。\n\n确定继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.set_ui_busy(True)
        self.current_worker = EngineWorker(self.engine.handle_toggle)
        self.current_worker.log_sig.connect(self.cb_log)
        self.current_worker.prog_sig.connect(self.cb_progress)
        self.current_worker.done_sig.connect(self._on_toggle_done)
        self.current_worker.err_sig.connect(self._on_worker_err)
        self.current_worker.start()

    def _on_toggle_done(self, result):
        self.set_ui_busy(False)
        s, f = result
        self.refresh_target_list()
        self.cb_progress(1, 1, "引擎挂起", f"成功:{s} | 失败:{len(f)}")
        self.cb_log(f"执行周期结束。成功:{s} 失败:{len(f)}")

    def ui_gen_exe(self):
        try:
            out_dir = self.engine.get_common_target_parent_dir()
        except Exception as e:
            return self.cb_log(f"中断: {e}")
        self.set_ui_busy(True)

        # generate_restore_exe 签名为 (output_dir, log_cb, process_events_cb)
        # 用 lambda 适配 EngineWorker 的统一调用格式 (progress_cb, log_cb)
        def exe_task(progress_cb, log_cb):
            return self.engine.generate_restore_exe(out_dir, log_cb)

        self.current_worker = EngineWorker(exe_task)
        self.current_worker.log_sig.connect(self.cb_log)
        self.current_worker.prog_sig.connect(self.cb_progress)
        self.current_worker.done_sig.connect(self._on_exe_done)
        self.current_worker.err_sig.connect(self._on_worker_err)
        self.current_worker.start()

    def _on_exe_done(self, exe_path):
        self.set_ui_busy(False)
        self.cb_progress(1, 1, "编译完成", str(Path(exe_path).parent))
        self.cb_log(f"脱壳包导出成功: {exe_path}")

    def ui_gen_apk(self):
        try:
            out_dir = self.engine.get_common_target_parent_dir()
        except Exception as e:
            return self.cb_log(f"中断: {e}")
        self.set_ui_busy(True)

        def apk_task(progress_cb, log_cb):
            return self.engine.generate_restore_apk(out_dir, log_cb)

        self.current_worker = EngineWorker(apk_task)
        self.current_worker.log_sig.connect(self.cb_log)
        self.current_worker.prog_sig.connect(self.cb_progress)
        self.current_worker.done_sig.connect(self._on_apk_done)
        self.current_worker.err_sig.connect(self._on_worker_err)
        self.current_worker.start()

    def _on_apk_done(self, result):
        self.set_ui_busy(False)
        self.cb_progress(1, 1, "安卓恢复包", str(result))
        if Path(result).is_file():
            self.cb_log(f"安卓恢复包已生成: {result}")
        else:
            self.cb_log(f"Android 项目已生成，请用 Android Studio 打开编译: {result}")

    def _on_worker_err(self, err_msg):
        self.set_ui_busy(False)
        self.cb_progress(0, 1, "系统崩溃", "ERR_FATAL")
        self.cb_log(f"[ERROR] 内核异常: {err_msg}")