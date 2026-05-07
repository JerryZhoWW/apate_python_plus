import os
import sys
import json
import random
import struct
import subprocess
import shutil
import secrets
import tempfile
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QTextEdit, QVBoxLayout, QHBoxLayout, QMessageBox, QLineEdit,
    QListWidget, QListWidgetItem, QFrame, QGridLayout, QProgressBar,
    QStackedWidget, QGraphicsDropShadowEffect
)

DEFAULT_MAGIC = b"DGSK"
CONFIG_FILE_NAME = "mask_config.json"


class DisguiseError(Exception):
    pass


# =================== 路径 / 配置 ===================
def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_config_path() -> Path:
    return get_app_dir() / CONFIG_FILE_NAME


def normalize_config(data) -> dict:
    if not isinstance(data, dict):
        data = {}

    mask_library = data.get("mask_library", [])
    if not isinstance(mask_library, list):
        mask_library = []

    magic_hex = data.get("magic_hex", DEFAULT_MAGIC.hex())
    if not isinstance(magic_hex, str):
        magic_hex = DEFAULT_MAGIC.hex()

    try:
        magic_bytes = bytes.fromhex(magic_hex)
        if not (1 <= len(magic_bytes) <= 32):
            magic_hex = DEFAULT_MAGIC.hex()
    except Exception:
        magic_hex = DEFAULT_MAGIC.hex()

    return {
        "mask_library": mask_library,
        "magic_hex": magic_hex
    }


def load_config() -> dict:
    config_path = get_config_path()
    if not config_path.exists():
        return normalize_config({})

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return normalize_config(data)
    except Exception:
        return normalize_config({})


def save_config(config: dict):
    config = normalize_config(config)
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_magic_bytes(config: dict = None) -> bytes:
    if config is None:
        config = load_config()
    try:
        magic = bytes.fromhex(config.get("magic_hex", DEFAULT_MAGIC.hex()))
        if not (1 <= len(magic) <= 32):
            return DEFAULT_MAGIC
        return magic
    except Exception:
        return DEFAULT_MAGIC


def magic_to_display_text(magic: bytes) -> str:
    try:
        ascii_part = magic.decode("utf-8")
    except Exception:
        ascii_part = "<非UTF-8字节序列>"
    return f"HEX={magic.hex().upper()} | BYTES={magic!r} | TEXT={ascii_part}"


def build_non_conflicting_path(target_path: Path, tag: str, reserved_paths=None) -> Path:
    """
    生成一个不会覆盖现有文件的安全输出路径。
    例如：
    1.mp4 -> 1_disguised_1.mp4
    1.zip -> 1_restored_1.zip
    """
    target_path = Path(target_path)
    reserved = {str(Path(p).resolve()) for p in (reserved_paths or [])}

    resolved_target = str(target_path.resolve())
    if resolved_target not in reserved and not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    index = 1
    while True:
        candidate = target_path.with_name(f"{stem}_{tag}_{index}{suffix}")
        resolved_candidate = str(candidate.resolve())
        if resolved_candidate not in reserved and not candidate.exists():
            return candidate
        index += 1


def parse_disguised_metadata(file_obj, file_size: int, magic: bytes):
    """
    解析伪装文件尾部元数据。

    当前格式（v2）：
        original_head[::-1] + original_file_name + name_len(1B) + head_len(4B) + original_size(8B) + magic

    兼容旧格式（v1）：
        original_head[::-1] + original_file_name + name_len(1B) + head_len(4B) + magic
        original_head[::-1] + original_suffix + suffix_len(1B) + head_len(4B) + magic
    """
    file_obj.seek(-len(magic), os.SEEK_END)
    if file_obj.read(len(magic)) != magic:
        raise DisguiseError("文件尾标记无效")

    # 先尝试 v2：... + name_len(1) + head_len(4) + original_size(8) + magic
    try:
        if file_size >= len(magic) + 8 + 4 + 1:
            file_obj.seek(-(len(magic) + 8), os.SEEK_END)
            original_size = struct.unpack("<Q", file_obj.read(8))[0]

            file_obj.seek(-(len(magic) + 8 + 4), os.SEEK_END)
            head_len = struct.unpack("<I", file_obj.read(4))[0]

            file_obj.seek(-(len(magic) + 8 + 4 + 1), os.SEEK_END)
            name_len = struct.unpack("B", file_obj.read(1))[0]

            name_pos = file_size - len(magic) - 8 - 4 - 1 - name_len
            head_pos = name_pos - head_len
            if 0 <= name_pos <= file_size and 0 <= head_pos <= file_size:
                file_obj.seek(name_pos)
                raw_name = file_obj.read(name_len)
                decoded = raw_name.decode("utf-8")
                candidate = Path(decoded).name
                if candidate and candidate == decoded and decoded not in (".", ".."):
                    return {
                        "format": "v2",
                        "head_len": head_len,
                        "name_len": name_len,
                        "name_pos": name_pos,
                        "head_pos": head_pos,
                        "original_name": candidate,
                        "original_size": original_size,
                    }
    except Exception:
        pass

    # 回退到 v1：... + name_len/suffix_len(1) + head_len(4) + magic
    file_obj.seek(-(len(magic) + 4), os.SEEK_END)
    head_len = struct.unpack("<I", file_obj.read(4))[0]

    file_obj.seek(-(len(magic) + 4 + 1), os.SEEK_END)
    name_len = struct.unpack("B", file_obj.read(1))[0]

    if name_len > file_size:
        raise DisguiseError("文件结构异常：名称长度非法")

    name_pos = file_size - len(magic) - 4 - 1 - name_len
    if name_pos < 0:
        raise DisguiseError("文件结构异常：name_pos 非法")

    head_pos = name_pos - head_len
    if head_pos < 0:
        raise DisguiseError("文件结构异常：head_pos 非法")

    file_obj.seek(name_pos)
    raw_name = file_obj.read(name_len)
    if len(raw_name) != name_len:
        raise DisguiseError("文件结构异常：名称长度不足")

    try:
        decoded = raw_name.decode("utf-8")
        candidate = Path(decoded).name
        if candidate and candidate == decoded and decoded not in (".", ".."):
            original_name = candidate
        else:
            raise ValueError("不是完整文件名")
    except Exception:
        try:
            original_suffix = raw_name.decode("utf-8")
        except Exception as e:
            raise DisguiseError(f"无法解析原始文件名/后缀：{e}")
        original_name = Path(file_obj.name).stem + original_suffix

    return {
        "format": "v1",
        "head_len": head_len,
        "name_len": name_len,
        "name_pos": name_pos,
        "head_pos": head_pos,
        "original_name": original_name,
        "original_size": head_pos,
    }


# =================== 核心逻辑 ===================
def get_footer_meta_size(magic: bytes, name_len: int) -> int:
    # original_head[::-1] + original_file_name + name_len(1B) + head_len(4B) + original_size(8B) + magic
    return name_len + 1 + 4 + 8 + len(magic)


def is_disguised_file(file_path: str, magic: bytes = None) -> bool:
    if magic is None:
        magic = get_magic_bytes()

    path = Path(file_path)
    if not path.is_file():
        return False

    try:
        # 至少得能容纳 suffix_len(1) + head_len(4) + magic
        if path.stat().st_size < (1 + 4 + len(magic)):
            return False

        with open(path, "rb") as f:
            f.seek(-len(magic), os.SEEK_END)
            return f.read(len(magic)) == magic
    except Exception:
        return False


def read_mask_file(mask_path: str) -> bytes:
    path = Path(mask_path)
    if not path.is_file():
        raise FileNotFoundError(f"面具文件不存在: {mask_path}")

    with open(path, "rb") as f:
        data = f.read()

    if not data:
        raise DisguiseError("面具文件为空")

    return data


def disguise_file(file_path: str, mask_path: str, magic: bytes = None, reserved_output_paths=None) -> str:
    if magic is None:
        magic = get_magic_bytes()

    file_path = Path(file_path)
    mask_path = Path(mask_path)

    if not file_path.is_file():
        raise FileNotFoundError(f"目标文件不存在: {file_path}")

    if is_disguised_file(str(file_path), magic):
        raise DisguiseError("该文件已经是伪装态")

    mask_bytes = read_mask_file(str(mask_path))
    mask_len = len(mask_bytes)
    original_file_name_bytes = file_path.name.encode("utf-8")
    original_name_len = len(original_file_name_bytes)
    mask_suffix = mask_path.suffix

    if original_name_len > 255:
        raise DisguiseError("原始文件名长度超过 255，无法写入单字节长度")

    original_size = file_path.stat().st_size

    with open(file_path, "r+b") as f:
        original_head = f.read(mask_len)
        f.seek(0)
        f.write(mask_bytes)
        f.seek(0, os.SEEK_END)
        f.write(original_head[::-1])
        f.write(original_file_name_bytes)
        f.write(struct.pack("B", original_name_len))
        f.write(struct.pack("<I", len(original_head)))
        f.write(struct.pack("<Q", original_size))
        f.write(magic)

    desired_path = file_path.with_suffix(mask_suffix)
    disguised_path = build_non_conflicting_path(desired_path, "disguised", reserved_output_paths)
    os.replace(str(file_path), str(disguised_path))
    return str(disguised_path)


def reveal_file(file_path: str, magic: bytes = None, reserved_output_paths=None) -> str:
    if magic is None:
        magic = get_magic_bytes()

    file_path = Path(file_path)

    if not is_disguised_file(str(file_path), magic):
        raise DisguiseError("该文件不是当前魔术字对应的伪装文件")

    with open(file_path, "r+b") as f:
        file_size = file_path.stat().st_size
        meta = parse_disguised_metadata(f, file_size, magic)

        f.seek(meta["head_pos"])
        original_head_reversed = f.read(meta["head_len"])
        if len(original_head_reversed) != meta["head_len"]:
            raise DisguiseError("文件结构异常：原始头长度不足")

        original_head = original_head_reversed[::-1]

        # 先恢复开头，再按原始文件大小截断，避免面具文件比原文件大时残留脏字节
        f.seek(0)
        f.write(original_head)
        f.truncate(meta["original_size"])

    desired_path = file_path.parent / meta["original_name"]
    restored_path = desired_path
    if str(desired_path.resolve()) in {str(Path(p).resolve()) for p in (reserved_output_paths or [])}:
        restored_path = build_non_conflicting_path(desired_path, "restored", reserved_output_paths)

    os.replace(str(file_path), str(restored_path))
    return str(restored_path)


def collect_files_from_paths(paths):
    results = []
    seen = set()

    for p in paths:
        path = Path(p)
        if not path.exists():
            continue

        if path.is_file():
            s = str(path.resolve())
            if s not in seen:
                seen.add(s)
                results.append(s)

        elif path.is_dir():
            for sub in path.rglob("*"):
                if sub.is_file():
                    s = str(sub.resolve())
                    if s not in seen:
                        seen.add(s)
                        results.append(s)

    return results


# =================== PyInstaller 打包 ===================
def create_restore_exe(py_script_path: str, exe_output_dir: Path):
    py_script_path = Path(py_script_path).resolve()
    exe_output_dir = Path(exe_output_dir).resolve()
    exe_output_dir.mkdir(parents=True, exist_ok=True)

    build_dir = exe_output_dir / "build_pyinstaller_restore"
    spec_dir = exe_output_dir / "spec_pyinstaller_restore"
    exe_name = py_script_path.stem + ".exe"
    dist_path = exe_output_dir / exe_name

    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--distpath", str(exe_output_dir),
        "--workpath", str(build_dir),
        "--specpath", str(spec_dir),
        str(py_script_path)
    ], check=True)

    if build_dir.exists() and build_dir.is_dir():
        shutil.rmtree(build_dir, ignore_errors=True)

    if spec_dir.exists() and spec_dir.is_dir():
        shutil.rmtree(spec_dir, ignore_errors=True)

    pycache_dir = py_script_path.parent / "__pycache__"
    if pycache_dir.exists() and pycache_dir.is_dir():
        shutil.rmtree(pycache_dir, ignore_errors=True)

    spec_file = spec_dir / f"{py_script_path.stem}.spec"
    if spec_file.exists():
        spec_file.unlink(missing_ok=True)

    return dist_path


# =================== UI 组件 ===================
class SectionCard(QFrame):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("sectionCard")
        self.setGraphicsEffect(build_shadow())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("sectionSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(10)
        layout.addLayout(self.body_layout)


def build_shadow(blur: int = 28, offset_y: int = 8, alpha: int = 28):
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset_y)
    effect.setColor(QColor(25, 42, 70, alpha))
    return effect


class DropLabel(QLabel):
    def __init__(self, title: str, drop_type: str, parent=None):
        super().__init__(parent)
        self.drop_type = drop_type
        self.window_ref = None
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setText(title)
        self.setObjectName("dropZone")
        self._default_text = title

    def set_display_text(self, text: str):
        self.setText(text)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            local_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if local_paths:
                self.setProperty("dragging", True)
                self.style().unpolish(self)
                self.style().polish(self)
                event.acceptProposedAction()
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

        urls = event.mimeData().urls()
        local_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not local_paths:
            event.ignore()
            return

        if self.window_ref:
            if self.drop_type == "target":
                self.window_ref.add_target_paths(local_paths)
            elif self.drop_type == "mask":
                self.window_ref.add_mask_paths(local_paths)

        event.acceptProposedAction()


class FileDropLineEdit(QLineEdit):
    def __init__(self, drop_type: str, parent=None):
        super().__init__(parent)
        self.drop_type = drop_type
        self.window_ref = None
        self.setAcceptDrops(True)
        self.setReadOnly(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            local_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if local_paths:
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        local_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not local_paths:
            event.ignore()
            return

        if self.window_ref and self.drop_type == "mask":
            self.window_ref.add_mask_paths(local_paths)

        event.acceptProposedAction()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.target_files = []
        self.mask_library = []
        self.config = load_config()
        self.init_ui()
        self.load_mask_library_from_config()
        self.refresh_magic_ui()

    def init_ui(self):
        self.setWindowTitle("文件伪装 / 还原工具 v2.7")
        self.resize(1320, 940)
        self.apply_styles()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_card.setGraphicsEffect(build_shadow(42, 12, 40))
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(24, 22, 24, 22)
        header_layout.setSpacing(10)

        title = QLabel("文件伪装 / 还原工具 v2.7")
        title.setObjectName("mainTitle")
        subtitle = QLabel("支持批量目标文件、面具文件库、随机面具伪装、配置持久化、自定义魔术字、生成匹配当前魔术字的恢复 EXE")
        subtitle.setObjectName("mainSubtitle")
        subtitle.setWordWrap(True)
        self.status_label = QLabel(f"程序目录：{get_app_dir()}")
        self.status_label.setObjectName("statusInfo")
        self.status_label.setWordWrap(True)

        stat_row = QHBoxLayout()
        stat_row.setSpacing(10)
        self.target_stat = self.make_stat_chip("目标文件", "0")
        self.mask_stat = self.make_stat_chip("面具文件", "0")
        self.mode_stat = self.make_stat_chip("模式", "伪装 / 还原")
        stat_row.addWidget(self.target_stat)
        stat_row.addWidget(self.mask_stat)
        stat_row.addWidget(self.mode_stat)
        stat_row.addStretch(1)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addWidget(self.status_label)
        header_layout.addLayout(stat_row)
        root.addWidget(header_card)

        body = QHBoxLayout()
        body.setSpacing(16)

        sidebar = QFrame()
        sidebar.setObjectName("sidebarCard")
        sidebar.setFixedWidth(264)
        sidebar.setGraphicsEffect(build_shadow(36, 8, 24))
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 18, 16, 18)
        side.setSpacing(10)
        nav_title = QLabel("导航")
        nav_title.setObjectName("sidebarTitle")
        nav_tip = QLabel("切换不同功能模块 / 在日志中查看详细处理记录")
        nav_tip.setObjectName("sectionSubtitle")
        nav_tip.setWordWrap(True)
        self.nav_magic = self.make_nav_button("M  魔术字设置")
        self.nav_action = self.make_nav_button("A  伪装 / 还原")
        self.nav_log = self.make_nav_button("L  运行日志")
        self.nav_magic.clicked.connect(lambda: self.switch_module(0))
        self.nav_action.clicked.connect(lambda: self.switch_module(1))
        self.nav_log.clicked.connect(lambda: self.switch_module(2))
        side.addWidget(nav_title)
        side.addWidget(nav_tip)
        side.addSpacing(8)
        side.addWidget(self.nav_magic)
        side.addWidget(self.nav_action)
        side.addWidget(self.nav_log)
        side.addStretch(1)
        side_hint = QLabel("建议先设置魔术字，再添加目标文件和面具文件后执行操作")
        side_hint.setObjectName("sidebarHint")
        side_hint.setWordWrap(True)
        side.addWidget(side_hint)
        body.addWidget(sidebar)

        self.content_stack = QStackedWidget()
        body.addWidget(self.content_stack, 1)

        magic_page = QWidget()
        magic_layout = QVBoxLayout(magic_page)
        magic_layout.setContentsMargins(0, 0, 0, 0)
        magic_card = SectionCard("魔术字设置", "用于识别当前伪装文件的尾部标记，可自定义、随机生成或恢复默认值")
        magic_row = QHBoxLayout()
        magic_row.setSpacing(10)
        self.magic_edit = QLineEdit()
        self.magic_edit.setObjectName("infoLine")
        self.magic_edit.setPlaceholderText("请输入魔术字，支持 ASCII，如 DGSK；也支持 HEX，如 44 47 53 4B")
        btn_apply_magic = self.make_button("M 应用魔术字", accent=True)
        btn_apply_magic.clicked.connect(self.apply_magic_from_input)
        btn_random_magic = self.make_button("R 随机生成", secondary=True)
        btn_random_magic.clicked.connect(self.generate_random_magic)
        btn_reset_magic = self.make_button("D 恢复默认", danger=True)
        btn_reset_magic.clicked.connect(self.reset_magic)
        magic_row.addWidget(self.magic_edit, 1)
        magic_row.addWidget(btn_apply_magic)
        magic_row.addWidget(btn_random_magic)
        magic_row.addWidget(btn_reset_magic)
        self.magic_info_label = QLabel("")
        self.magic_info_label.setObjectName("sectionSubtitle")
        self.magic_info_label.setWordWrap(True)
        magic_hint = QLabel("HEX 输入支持带或不带 0x 前缀；普通文本按 UTF-8 编码处理，长度需在 1 到 32 字节之间")
        magic_hint.setObjectName("sectionSubtitle")
        magic_hint.setWordWrap(True)
        magic_card.body_layout.addLayout(magic_row)
        magic_card.body_layout.addWidget(self.magic_info_label)
        magic_card.body_layout.addWidget(magic_hint)
        magic_layout.addWidget(magic_card)
        magic_layout.addStretch(1)
        self.content_stack.addWidget(magic_page)

        action_page = QWidget()
        action_root = QVBoxLayout(action_page)
        action_root.setContentsMargins(0, 0, 0, 0)
        action_cols = QHBoxLayout()
        action_cols.setSpacing(14)
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        left_col.setSpacing(14)
        right_col.setSpacing(14)

        self.target_drop = DropLabel("拖拽目标文件或文件夹到这里\n支持批量添加", "target")
        self.target_drop.window_ref = self
        self.target_list = QListWidget()
        self.target_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.target_list.setObjectName("fileList")
        target_card = SectionCard("目标文件", "可添加多个文件或整个目录，目录会自动递归收集其中所有文件")
        target_card.body_layout.addWidget(self.target_drop)
        target_card.body_layout.addWidget(self.target_list)
        target_grid = QGridLayout()
        target_grid.setHorizontalSpacing(10)
        target_grid.setVerticalSpacing(10)
        btn_select_targets = self.make_button("F 选择目标文件")
        btn_select_targets.clicked.connect(self.select_target_files)
        btn_select_folder = self.make_button("D 选择目标目录")
        btn_select_folder.clicked.connect(self.select_target_folder)
        btn_remove_selected = self.make_button("R 移除选中项", secondary=True)
        btn_remove_selected.clicked.connect(self.remove_selected_targets)
        btn_clear_targets = self.make_button("C 清空目标列表", danger=True)
        btn_clear_targets.clicked.connect(self.clear_target_files)
        btn_detect = self.make_button("S 扫描当前状态", secondary=True)
        btn_detect.clicked.connect(self.detect_status)
        btn_generate_restore_exe = self.make_button("E 生成恢复 EXE", accent=True)
        btn_generate_restore_exe.clicked.connect(self.handle_generate_restore_exe)
        target_grid.addWidget(btn_select_targets, 0, 0)
        target_grid.addWidget(btn_select_folder, 0, 1)
        target_grid.addWidget(btn_remove_selected, 1, 0)
        target_grid.addWidget(btn_clear_targets, 1, 1)
        target_grid.addWidget(btn_detect, 2, 0)
        target_grid.addWidget(btn_generate_restore_exe, 2, 1)
        target_card.body_layout.addLayout(target_grid)
        left_col.addWidget(target_card)

        progress_card = SectionCard("处理进度", "显示当前批处理任务的执行进度和阶段说明")
        self.progress_label = QLabel("等待开始任务")
        self.progress_label.setObjectName("progressText")
        self.progress_detail = QLabel("尚未执行")
        self.progress_detail.setObjectName("sectionSubtitle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_card.body_layout.addWidget(self.progress_label)
        progress_card.body_layout.addWidget(self.progress_bar)
        progress_card.body_layout.addWidget(self.progress_detail)
        left_col.addWidget(progress_card)

        self.mask_drop = DropLabel("拖拽面具文件或文件夹到这里\n可作为伪装外观文件库", "mask")
        self.mask_drop.window_ref = self
        self.mask_edit = FileDropLineEdit("mask")
        self.mask_edit.window_ref = self
        self.mask_edit.setObjectName("infoLine")
        self.mask_edit.setPlaceholderText("显示当前已加载的面具文件数量 / 支持拖拽添加")
        self.mask_list = QListWidget()
        self.mask_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.mask_list.setObjectName("fileList")
        mask_card = SectionCard("面具文件库", "伪装时会从面具文件库中随机选择一个文件作为外观来源")
        mask_card.body_layout.addWidget(self.mask_drop)
        mask_card.body_layout.addWidget(self.mask_edit)
        mask_card.body_layout.addWidget(self.mask_list)
        mask_grid = QGridLayout()
        mask_grid.setHorizontalSpacing(10)
        mask_grid.setVerticalSpacing(10)
        btn_add_mask_files = self.make_button("F 添加面具文件")
        btn_add_mask_files.clicked.connect(self.select_mask_files)
        btn_add_mask_folder = self.make_button("D 添加面具目录")
        btn_add_mask_folder.clicked.connect(self.select_mask_folder)
        btn_remove_selected_masks = self.make_button("R 移除选中项", secondary=True)
        btn_remove_selected_masks.clicked.connect(self.remove_selected_masks)
        btn_clear_masks = self.make_button("C 清空面具库", danger=True)
        btn_clear_masks.clicked.connect(self.clear_mask_library)
        btn_reload_masks = self.make_button("L 重新加载配置", secondary=True)
        btn_reload_masks.clicked.connect(self.load_mask_library_from_config)
        mask_grid.addWidget(btn_add_mask_files, 0, 0)
        mask_grid.addWidget(btn_add_mask_folder, 0, 1)
        mask_grid.addWidget(btn_remove_selected_masks, 1, 0)
        mask_grid.addWidget(btn_clear_masks, 1, 1)
        mask_grid.addWidget(btn_reload_masks, 2, 0, 1, 2)
        mask_card.body_layout.addLayout(mask_grid)
        right_col.addWidget(mask_card)

        action_card = SectionCard("伪装 / 还原", "程序会自动判断文件当前状态：原始文件执行伪装，伪装文件执行还原")
        btn_toggle = self.make_button("T 一键 Toggle：自动伪装 / 还原", primary=True)
        btn_toggle.setMinimumHeight(50)
        btn_toggle.clicked.connect(self.handle_toggle)
        action_card.body_layout.addWidget(btn_toggle)
        right_col.addWidget(action_card)
        right_col.addStretch(1)

        action_cols.addLayout(left_col, 1)
        action_cols.addLayout(right_col, 1)
        action_root.addLayout(action_cols)
        self.content_stack.addWidget(action_page)

        log_page = QWidget()
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_card = SectionCard("运行日志", "显示每一步处理细节、错误信息，以及 EXE 生成过程中的输出")
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setFont(QFont("Consolas", 10))
        log_card.body_layout.addWidget(self.log_edit)
        log_layout.addWidget(log_card)
        self.content_stack.addWidget(log_page)

        root.addLayout(body, 1)
        self.switch_module(1)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: #eef3f9; color: #1f2937; font-size: 14px; font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI"; }
            QFrame#headerCard { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1b5fcf, stop:0.56 #4382eb, stop:1 #79adff); border-radius: 24px; border: 1px solid rgba(255,255,255,0.20); }
            QLabel#mainTitle { color: white; font-size: 30px; font-weight: 700; background: transparent; }
            QLabel#mainSubtitle, QLabel#statusInfo, QLabel#statLabel, QLabel#statValue, QLabel#sectionTitle, QLabel#sectionSubtitle, QLabel#sidebarTitle, QLabel#sidebarHint, QLabel#progressText { background: transparent; }
            QLabel#mainSubtitle { color: rgba(255,255,255,0.92); font-size: 13px; }
            QLabel#statusInfo { color: rgba(255,255,255,0.92); font-size: 12px; }
            QFrame#statChip { background: rgba(255,255,255,0.17); border-radius: 16px; border: 1px solid rgba(255,255,255,0.22); }
            QLabel#statLabel { color: rgba(255,255,255,0.78); font-size: 12px; }
            QLabel#statValue { color: white; font-size: 18px; font-weight: 700; }
            QFrame#sidebarCard { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f9fbff, stop:1 #eef4ff); border: 1px solid rgba(191,205,226,0.9); border-radius: 24px; }
            QLabel#sidebarTitle { font-size: 18px; font-weight: 700; color: #0f172a; }
            QLabel#sidebarHint, QLabel#sectionSubtitle { color: #64748b; line-height: 1.5em; }
            QFrame#sectionCard { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f9fbff); border: 1px solid rgba(208,218,234,0.95); border-radius: 22px; }
            QLabel#sectionTitle { font-size: 18px; font-weight: 700; color: #0f172a; }
            QLabel#dropZone { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #f8fbff, stop:1 #eef4ff); border: 2px dashed #98b7ff; border-radius: 18px; padding: 26px; font-size: 15px; font-weight: 600; color: #3157c8; min-height: 92px; }
            QLabel#dropZone[dragging="true"] { background: #eaf2ff; border: 2px dashed #4b79ff; color: #2141a6; }
            QListWidget#fileList { background: rgba(255,255,255,0.88); border: 1px solid #dbe3f0; border-radius: 16px; padding: 8px; min-height: 200px; outline: none; }
            QListWidget#fileList::item { padding: 8px 10px; border-radius: 10px; margin: 2px 0; }
            QListWidget#fileList::item:selected { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #dfe8ff, stop:1 #edf3ff); color: #183b9b; }
            QLineEdit#infoLine { background: rgba(255,255,255,0.94); border: 1px solid #d3dbe8; border-radius: 14px; padding: 11px 14px; color: #334155; }
            QLineEdit#infoLine:focus { border: 1px solid #75a2ff; background: #ffffff; }
            QTextEdit#logEdit { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #0f172a, stop:1 #111c34); color: #d8f8eb; border: 1px solid #1e293b; border-radius: 18px; padding: 12px; }
            QLabel#progressText { color: #0f172a; font-size: 15px; font-weight: 700; }
            QProgressBar#progressBar { min-height: 16px; background: #e6edf7; border: 1px solid #d4dceb; border-radius: 8px; color: #1e3a8a; text-align: center; font-weight: 700; }
            QProgressBar#progressBar::chunk { border-radius: 7px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #59a9ff, stop:1 #356dff); }
            QPushButton { border: 1px solid rgba(197,209,226,0.95); border-radius: 14px; padding: 10px 14px; font-weight: 600; min-height: 18px; background: rgba(255,255,255,0.92); }
            QPushButton[role="default"] { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #edf4ff); color: #2742b8; }
            QPushButton[role="default"]:hover { background: #e8f0ff; }
            QPushButton[role="secondary"] { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #f1f5f9); color: #374151; }
            QPushButton[role="secondary"]:hover { background: #e8edf4; }
            QPushButton[role="accent"] { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f7f1ff, stop:1 #ebe4ff); color: #5b21b6; }
            QPushButton[role="accent"]:hover { background: #e4dcff; }
            QPushButton[role="danger"] { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #fff6f6, stop:1 #fee7e7); color: #b91c1c; }
            QPushButton[role="danger"]:hover { background: #fee2e2; }
            QPushButton[role="primary"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2c77ff, stop:1 #5b8dff); color: white; font-size: 15px; border: 1px solid rgba(83,133,255,0.9); }
            QPushButton[role="primary"]:hover { background: #2b68de; }
            QPushButton[role="nav"] { text-align: left; padding: 14px 16px; border-radius: 18px; background: rgba(255,255,255,0.76); color: #1d3f97; }
            QPushButton[role="nav"]:hover { background: rgba(231,239,255,0.98); }
            QPushButton[role="nav"][active="true"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #dce9ff, stop:1 #edf4ff); border: 1px solid #a5c0ff; color: #123b93; }
        """)

    def make_button(self, text, primary=False, secondary=False, danger=False, accent=False):
        btn = QPushButton(text)
        if primary:
            btn.setProperty("role", "primary")
        elif secondary:
            btn.setProperty("role", "secondary")
        elif danger:
            btn.setProperty("role", "danger")
        elif accent:
            btn.setProperty("role", "accent")
        else:
            btn.setProperty("role", "default")
        btn.setGraphicsEffect(build_shadow(18, 4, 20))
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        return btn

    def make_nav_button(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setProperty("role", "nav")
        btn.setProperty("active", False)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        return btn

    def make_stat_chip(self, label_text: str, value_text: str):
        frame = QFrame()
        frame.setObjectName("statChip")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        label = QLabel(label_text)
        label.setObjectName("statLabel")
        value = QLabel(value_text)
        value.setObjectName("statValue")
        layout.addWidget(label)
        layout.addWidget(value)
        frame.value_label = value
        return frame

    def set_stat_chip_value(self, chip: QFrame, text: str):
        chip.value_label.setText(text)

    def switch_module(self, index: int):
        self.content_stack.setCurrentIndex(index)
        labels = ["魔术字设置", "伪装 / 还原", "运行日志"]
        for i, btn in enumerate([self.nav_magic, self.nav_action, self.nav_log]):
            active = i == index
            btn.setChecked(active)
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.set_stat_chip_value(self.mode_stat, labels[index])

    def set_progress_state(self, current: int, total: int, title: str, detail: str = ""):
        percent = 0 if total <= 0 else int((current / total) * 100)
        self.progress_bar.setValue(percent)
        self.progress_label.setText(title)
        self.progress_detail.setText(detail or f"{current}/{total}")

    def reset_progress_state(self, title: str = "等待开始任务", detail: str = "尚未执行"):
        self.progress_bar.setValue(0)
        self.progress_label.setText(title)
        self.progress_detail.setText(detail)

    def finish_progress_state(self, title: str, detail: str):
        self.progress_bar.setValue(100)
        self.progress_label.setText(title)
        self.progress_detail.setText(detail)

    def refresh_status_summary(self):
        self.set_stat_chip_value(self.target_stat, str(len(self.target_files)))
        self.set_stat_chip_value(self.mask_stat, str(len(self.mask_library)))

    # =================== 日志 / 刷新 ===================
    def log(self, text: str):
        self.log_edit.append(text)

    def refresh_target_list(self):
        self.target_list.clear()
        for path in self.target_files:
            self.target_list.addItem(QListWidgetItem(path))
        self.target_drop.set_display_text(f"已添加目标文件 {len(self.target_files)} 个\n继续拖拽可追加")
        self.refresh_status_summary()

    def refresh_mask_list(self):
        self.mask_list.clear()
        for path in self.mask_library:
            self.mask_list.addItem(QListWidgetItem(path))
        self.mask_drop.set_display_text(f"已添加面具文件 {len(self.mask_library)} 个\n继续拖拽可追加到文件库")
        self.mask_edit.setText(f"当前共有 {len(self.mask_library)} 个面具文件")
        self.persist_mask_library()
        self.refresh_status_summary()

    def refresh_magic_ui(self):
        magic = get_magic_bytes(self.config)
        self.magic_edit.setText(magic.hex().upper())
        self.magic_info_label.setText(f"当前魔术字：{magic_to_display_text(magic)}")

    def persist_mask_library(self):
        self.config["mask_library"] = self.mask_library[:]
        save_config(self.config)

    def load_mask_library_from_config(self):
        config = load_config()
        library = config.get("mask_library", [])
        valid_files = []
        seen = set()
        for p in library:
            path = Path(p)
            if path.is_file():
                s = str(path.resolve())
                if s not in seen:
                    seen.add(s)
                    valid_files.append(s)
        self.mask_library = valid_files
        self.config = normalize_config({"mask_library": self.mask_library[:], "magic_hex": config.get("magic_hex", DEFAULT_MAGIC.hex())})
        save_config(self.config)
        self.refresh_mask_list()
        self.log(f"已加载面具库，共 {len(self.mask_library)} 个文件")
        self.refresh_magic_ui()

    def parse_magic_input(self, raw_text: str) -> bytes:
        text = (raw_text or "").strip()
        if not text:
            raise DisguiseError("请输入魔术字")

        compact = text.replace(" ", "").replace("\n", "").replace("\t", "")
        if compact.lower().startswith("0x"):
            compact = compact[2:]

        if compact:
            is_hex_like = all(ch in "0123456789abcdefABCDEF" for ch in compact) and len(compact) % 2 == 0
            if is_hex_like:
                data = bytes.fromhex(compact)
                if not (1 <= len(data) <= 32):
                    raise DisguiseError("HEX 格式长度必须在 1 到 32 字节之间")
                return data

        data = text.encode("utf-8")
        if not (1 <= len(data) <= 32):
            raise DisguiseError("文本编码后的长度必须在 1 到 32 字节之间")
        return data

    def apply_magic_from_input(self):
        try:
            magic = self.parse_magic_input(self.magic_edit.text())
            self.config["magic_hex"] = magic.hex()
            save_config(self.config)
            self.refresh_magic_ui()
            self.log(f"已应用新的魔术字：{magic_to_display_text(magic)}")
            QMessageBox.information(self, "提示", "魔术字已保存并生效")
        except Exception as e:
            QMessageBox.warning(self, "警告", f"应用魔术字失败：{e}")

    def generate_random_magic(self):
        try:
            magic = secrets.token_bytes(4)
            self.config["magic_hex"] = magic.hex()
            save_config(self.config)
            self.refresh_magic_ui()
            self.log(f"已随机生成魔术字：{magic_to_display_text(magic)}")
            QMessageBox.information(self, "提示", "已生成新的随机魔术字")
        except Exception as e:
            QMessageBox.warning(self, "警告", f"随机生成失败：{e}")

    def reset_magic(self):
        self.config["magic_hex"] = DEFAULT_MAGIC.hex()
        save_config(self.config)
        self.refresh_magic_ui()
        self.log(f"已恢复默认魔术字：{magic_to_display_text(DEFAULT_MAGIC)}")
        QMessageBox.information(self, "提示", "默认魔术字已恢复")

    def add_target_paths(self, paths):
        files = collect_files_from_paths(paths)
        added = 0
        existing = set(self.target_files)
        for f in files:
            if f not in existing:
                self.target_files.append(f)
                existing.add(f)
                added += 1
        self.refresh_target_list()
        self.log(f"已添加 {added} 个目标文件，当前共 {len(self.target_files)} 个")

    def replace_target_file(self, old_path: str, new_path: str):
        try:
            idx = self.target_files.index(old_path)
            self.target_files[idx] = str(Path(new_path).resolve())
        except ValueError:
            pass
        self.refresh_target_list()

    def clear_target_files(self):
        self.target_files.clear()
        self.refresh_target_list()
        self.reset_progress_state()
        self.log("已清空目标文件列表")

    def remove_selected_targets(self):
        selected_items = self.target_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要移除的目标文件")
            return
        selected_paths = {item.text() for item in selected_items}
        self.target_files = [p for p in self.target_files if p not in selected_paths]
        self.refresh_target_list()
        self.log(f"已移除 {len(selected_paths)} 个目标文件")

    def select_target_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择目标文件")
        if paths:
            self.add_target_paths(paths)

    def select_target_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if folder:
            self.add_target_paths([folder])

    def get_common_target_parent_dir(self) -> Path:
        if not self.target_files:
            raise DisguiseError("当前没有可用于输出的目标文件")
        resolved_files = []
        for p in self.target_files:
            path = Path(p).resolve()
            if path.is_file():
                resolved_files.append(path)
        if not resolved_files:
            raise DisguiseError("目标列表中没有有效文件")
        parent_dirs = [str(p.parent) for p in resolved_files]
        try:
            common_dir = Path(os.path.commonpath(parent_dirs))
        except ValueError:
            raise DisguiseError("这些文件不在同一可计算公共父目录的路径结构中")
        if not common_dir.exists() or not common_dir.is_dir():
            raise DisguiseError("计算得到的公共目录无效")
        return common_dir

    def add_mask_paths(self, paths):
        files = collect_files_from_paths(paths)
        added = 0
        existing = set(self.mask_library)
        for f in files:
            if f not in existing:
                self.mask_library.append(f)
                existing.add(f)
                added += 1
        self.refresh_mask_list()
        self.log(f"已添加 {added} 个面具文件，当前共 {len(self.mask_library)} 个")

    def remove_selected_masks(self):
        selected_items = self.mask_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要移除的面具文件")
            return
        selected_paths = {item.text() for item in selected_items}
        self.mask_library = [p for p in self.mask_library if p not in selected_paths]
        self.refresh_mask_list()
        self.log(f"已移除 {len(selected_paths)} 个面具文件")

    def clear_mask_library(self):
        reply = QMessageBox.question(self, "确认清空", "确定要清空整个面具文件库吗？此操作不会删除磁盘上的原文件。", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.mask_library.clear()
        self.refresh_mask_list()
        self.log("已清空面具文件库")

    def select_mask_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择面具文件")
        if paths:
            self.add_mask_paths(paths)

    def select_mask_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择面具目录")
        if folder:
            self.add_mask_paths([folder])

    def get_random_mask_file(self) -> str:
        valid_masks = []
        for p in self.mask_library:
            path = Path(p)
            if path.is_file():
                valid_masks.append(str(path.resolve()))
        self.mask_library = valid_masks
        self.refresh_mask_list()
        if not self.mask_library:
            raise DisguiseError("面具文件库为空，无法随机选择面具文件")
        return random.choice(self.mask_library)

    def detect_status(self):
        if not self.target_files:
            QMessageBox.warning(self, "警告", "请先添加需要处理的目标文件")
            return
        self.switch_module(1)
        magic = get_magic_bytes(self.config)
        disguised_count = 0
        original_count = 0
        failed = []
        total = len(self.target_files)
        self.set_progress_state(0, total, "正在检测文件状态...", f"0/{total}")
        self.log(f"开始检测文件状态，当前魔术字：{magic_to_display_text(magic)}")
        for index, path in enumerate(self.target_files, start=1):
            try:
                if is_disguised_file(path, magic):
                    disguised_count += 1
                    self.log(f"[伪装态] {path}")
                else:
                    original_count += 1
                    self.log(f"[原始态] {path}")
            except Exception as e:
                failed.append(f"{path} -> {e}")
            self.set_progress_state(index, total, "正在检测文件状态...", f"{index}/{total}")
            QApplication.processEvents()
        self.finish_progress_state("检测完成", f"原始文件 {original_count} 个，伪装文件 {disguised_count} 个，失败 {len(failed)} 个")
        msg = f"检测完成\n原始文件 {original_count} 个\n伪装文件 {disguised_count} 个"
        if failed:
            msg += f"\n失败 {len(failed)} 个"
        QMessageBox.information(self, "检测结果", msg)
        if failed:
            self.log("以下文件检测失败：")
            for line in failed:
                self.log(line)

    def handle_toggle(self):
        if not self.target_files:
            QMessageBox.warning(self, "警告", "请先添加需要处理的目标文件")
            return
        self.switch_module(1)
        magic = get_magic_bytes(self.config)
        need_mask = False
        for path in self.target_files:
            try:
                if not is_disguised_file(path, magic):
                    need_mask = True
                    break
            except Exception:
                pass
        if need_mask and not self.mask_library:
            QMessageBox.warning(self, "警告", "存在需要伪装的文件，但当前面具文件库为空")
            return

        reserved_outputs = {str(Path(p).resolve()) for p in self.target_files if Path(p).exists()}
        self.log(f"开始执行自动切换操作，当前魔术字：{magic_to_display_text(magic)}")
        self.log("已启用同名前缀保护：伪装时若输出文件名冲突，会自动追加 _disguised_N；恢复时优先还原原始文件名")
        success = 0
        failed = []
        total = len(self.target_files)
        self.set_progress_state(0, total, "正在批量处理文件...", f"0/{total}")
        for index, old_path in enumerate(self.target_files[:], start=1):
            try:
                old_resolved = str(Path(old_path).resolve())
                reserved_outputs.discard(old_resolved)

                if is_disguised_file(old_path, magic):
                    self.log(f"检测到伪装态，准备还原：{old_path}")
                    new_path = reveal_file(old_path, magic, reserved_outputs)
                    self.log(f"还原完成：{new_path}")
                    self.replace_target_file(old_path, new_path)
                else:
                    mask_file = self.get_random_mask_file()
                    self.log(f"检测到原始态，准备伪装：{old_path}")
                    self.log(f"本次使用面具文件：{mask_file}")
                    new_path = disguise_file(old_path, mask_file, magic, reserved_outputs)
                    self.log(f"伪装完成：{new_path}")
                    self.replace_target_file(old_path, new_path)

                reserved_outputs.add(str(Path(new_path).resolve()))
                success += 1
            except Exception as e:
                reserved_outputs.add(str(Path(old_path).resolve()))
                failed.append(f"{old_path} -> {e}")
                self.log(f"处理失败：{old_path} -> {e}")
            self.set_progress_state(index, total, "正在批量处理文件...", f"已处理 {index}/{total}")
            QApplication.processEvents()
        self.finish_progress_state("批处理完成", f"成功 {success} 个，失败 {len(failed)} 个")
        QMessageBox.information(self, "提示", f"处理已结束\n成功 {success} 个\n失败 {len(failed)} 个")
        if failed:
            self.log("以下文件处理失败：")
            for line in failed:
                self.log(line)

    def handle_generate_restore_exe(self):
        try:
            output_dir = self.get_common_target_parent_dir()
            self.log(f"准备生成恢复 EXE，输出目录：{output_dir}")
            self.set_progress_state(0, 1, "正在生成恢复 EXE...", str(output_dir))
            self.create_folder_restore_exe(output_dir)
            self.finish_progress_state("恢复 EXE 已生成", str(output_dir))
        except Exception as e:
            self.log(f"生成 EXE 失败: {e}")
            self.reset_progress_state("生成恢复 EXE 失败", str(e))
            QMessageBox.critical(self, "错误", f"生成 EXE 失败: {e}")

    def create_folder_restore_exe(self, output_dir: Path):
        current_magic = get_magic_bytes(self.config)
        script_name = "restore_all_disguised.py"
        exe_name = "restore_all_disguised.exe"

        temp_script_dir = get_app_dir()
        py_script_path = temp_script_dir / script_name

        script_content = f'''import sys
import os
import struct
from pathlib import Path

MAGIC = bytes.fromhex("{current_magic.hex()}")


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_disguised_file(file_path: Path) -> bool:
    if not file_path.is_file():
        return False
    try:
        if file_path.stat().st_size < (1 + 4 + len(MAGIC)):
            return False
        with open(file_path, "rb") as f:
            f.seek(-len(MAGIC), os.SEEK_END)
            return f.read(len(MAGIC)) == MAGIC
    except Exception:
        return False


def build_non_conflicting_path(target_path: Path, tag: str, reserved_paths=None) -> Path:
    target_path = Path(target_path)
    reserved = set()
    for p in (reserved_paths or []):
        try:
            reserved.add(str(Path(p).resolve()))
        except Exception:
            pass

    resolved_target = str(target_path.resolve())
    if resolved_target not in reserved and not target_path.exists():
        return target_path

    stem = target_path.stem
    suffix = target_path.suffix
    index = 1
    while True:
        candidate = target_path.with_name(f"{{stem}}_{{tag}}_{{index}}{{suffix}}")
        resolved_candidate = str(candidate.resolve())
        if resolved_candidate not in reserved and not candidate.exists():
            return candidate
        index += 1


def parse_disguised_metadata(file_obj, file_size: int):
    file_obj.seek(-len(MAGIC), os.SEEK_END)
    if file_obj.read(len(MAGIC)) != MAGIC:
        raise Exception("文件尾标记无效")

    try:
        if file_size >= len(MAGIC) + 8 + 4 + 1:
            file_obj.seek(-(len(MAGIC) + 8), os.SEEK_END)
            original_size = struct.unpack("<Q", file_obj.read(8))[0]

            file_obj.seek(-(len(MAGIC) + 8 + 4), os.SEEK_END)
            head_len = struct.unpack("<I", file_obj.read(4))[0]

            file_obj.seek(-(len(MAGIC) + 8 + 4 + 1), os.SEEK_END)
            name_len = struct.unpack("B", file_obj.read(1))[0]

            name_pos = file_size - len(MAGIC) - 8 - 4 - 1 - name_len
            head_pos = name_pos - head_len
            if 0 <= name_pos <= file_size and 0 <= head_pos <= file_size:
                file_obj.seek(name_pos)
                raw_name = file_obj.read(name_len)
                decoded = raw_name.decode("utf-8")
                candidate = Path(decoded).name
                if candidate and candidate == decoded and decoded not in (".", ".."):
                    return {{
                        "head_len": head_len,
                        "head_pos": head_pos,
                        "original_name": candidate,
                        "original_size": original_size,
                    }}
    except Exception:
        pass

    file_obj.seek(-(len(MAGIC) + 4), os.SEEK_END)
    head_len = struct.unpack("<I", file_obj.read(4))[0]

    file_obj.seek(-(len(MAGIC) + 4 + 1), os.SEEK_END)
    name_len = struct.unpack("B", file_obj.read(1))[0]

    if name_len > file_size:
        raise Exception("文件结构异常：名称长度非法")

    name_pos = file_size - len(MAGIC) - 4 - 1 - name_len
    if name_pos < 0:
        raise Exception("文件结构异常：name_pos 非法")

    head_pos = name_pos - head_len
    if head_pos < 0:
        raise Exception("文件结构异常：head_pos 非法")

    file_obj.seek(name_pos)
    raw_name = file_obj.read(name_len)
    if len(raw_name) != name_len:
        raise Exception("文件结构异常：名称长度不足")

    try:
        decoded = raw_name.decode("utf-8")
        candidate = Path(decoded).name
        if candidate and candidate == decoded and decoded not in (".", ".."):
            original_name = candidate
        else:
            raise ValueError("不是完整文件名")
    except Exception:
        original_suffix = raw_name.decode("utf-8")
        original_name = Path(file_obj.name).stem + original_suffix

    return {{
        "head_len": head_len,
        "head_pos": head_pos,
        "original_name": original_name,
        "original_size": head_pos,
    }}


def reveal_file(file_path: Path, reserved_output_paths=None) -> Path:
    with open(file_path, "r+b") as f:
        file_size = file_path.stat().st_size
        meta = parse_disguised_metadata(f, file_size)

        f.seek(meta["head_pos"])
        original_head_reversed = f.read(meta["head_len"])
        if len(original_head_reversed) != meta["head_len"]:
            raise Exception("文件结构异常：原始头长度不足")

        original_head = original_head_reversed[::-1]

        f.seek(0)
        f.write(original_head)
        f.truncate(meta["original_size"])

    desired_path = file_path.parent / meta["original_name"]
    restored_path = desired_path
    if str(desired_path.resolve()) in {{str(Path(p).resolve()) for p in (reserved_output_paths or [])}}:
        restored_path = build_non_conflicting_path(desired_path, "restored", reserved_output_paths)

    file_path.replace(restored_path)
    return restored_path


def main():
    base_dir = get_base_dir()
    print(f"递归扫描目录: {{base_dir}}")
    print(f"当前魔术字 HEX: {{MAGIC.hex().upper()}}")
    print("-" * 60)

    restored = 0
    failed = 0
    reserved_outputs = {{str(p.resolve()) for p in base_dir.rglob("*") if p.is_file()}}

    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue

        lower_name = path.name.lower()
        if lower_name in {{"restore_all_disguised.exe", "restore_all_disguised.py"}}:
            continue

        try:
            path_resolved = str(path.resolve())
            reserved_outputs.discard(path_resolved)
            if is_disguised_file(path):
                new_path = reveal_file(path, reserved_outputs)
                reserved_outputs.add(str(new_path.resolve()))
                restored += 1
                print(f"[已恢复] {{path}} -> {{new_path}}")
        except Exception as e:
            failed += 1
            print(f"[失败] {{path}} -> {{e}}")

    print("-" * 60)
    print(f"完成：恢复 {{restored}} 个，失败 {{failed}} 个")
    input("按回车退出...")


if __name__ == "__main__":
    main()
''' 

        try:
            with open(py_script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            self.log(f"生成临时恢复脚本: {py_script_path}")
            self.log(f"当前恢复脚本绑定魔术字：{magic_to_display_text(current_magic)}")
            self.log(f"最终 EXE 输出目录：{output_dir}")

            exe_path = create_restore_exe(str(py_script_path), output_dir)
            self.log(f"生成批量恢复 exe: {exe_path}")

            QMessageBox.information(
                self,
                "生成成功",
                f"批量恢复 EXE 已生成：\n{exe_path}\n\n"
                f"当前绑定魔术字：{current_magic.hex().upper()}\n"
                f"输出目录：{output_dir}\n"
                f"规则：目标文件共同最近父目录。"
            )
        finally:
            try:
                if py_script_path.exists():
                    py_script_path.unlink()
                    self.log(f"已删除临时恢复脚本: {py_script_path}")
            except Exception as e:
                self.log(f"删除临时恢复脚本失败: {e}")


# =================== 运行 ===================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())