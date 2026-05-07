import os
import sys
import json
import random
import struct
import subprocess
import shutil
import secrets
from pathlib import Path

DEFAULT_MAGIC = b"DGSK"
# 全局新版配置文件
CONFIG_FILE_NAME = "apluse_config.json"
# 兼容旧版的配置文件名
OLD_CONFIG_FILE_NAME = "mask_config.json"
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB 分块大小

class DisguiseError(Exception):
    pass

# =================== 核心新增：双路径策略管理器 ===================
class PathManager:
    @staticmethod
    def get_persist_dir() -> Path:
        """
        获取持久化目录（永久保存数据用）。
        打包后：返回 .exe 文件所在的外部物理目录。
        未打包：返回当前 .py 脚本所在的目录。
        """
        if getattr(sys, "frozen", False) or "__compiled__" in globals():
            return Path(sys.argv[0]).resolve().parent
        return Path(__file__).resolve().parent

    @staticmethod
    def get_resource_dir() -> Path:
        """
        获取只读资源目录（读取图标、UI等静态文件用）。
        兼容 PyInstaller 和 Nuitka 两种打包方式。
        """
        # PyInstaller 解压目录
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        # Nuitka 编译后，资源文件与 .exe 同目录
        if "__compiled__" in globals():
            return Path(sys.argv[0]).resolve().parent
        return Path(__file__).resolve().parent


# =================== 基础工具函数 ===================
def get_config_path() -> Path:
    # 强制将配置文件写在 .exe 同级目录下，实现持久化
    return PathManager.get_persist_dir() / CONFIG_FILE_NAME

def normalize_config(data) -> dict:
    if not isinstance(data, dict): data = {}
    mask_library = data.get("mask_library", [])
    if not isinstance(mask_library, list): mask_library = []
    
    magic_hex = data.get("magic_hex", DEFAULT_MAGIC.hex())
    if not isinstance(magic_hex, str): magic_hex = DEFAULT_MAGIC.hex()
    try:
        magic_bytes = bytes.fromhex(magic_hex)
        if not (1 <= len(magic_bytes) <= 32): magic_hex = DEFAULT_MAGIC.hex()
    except Exception:
        magic_hex = DEFAULT_MAGIC.hex()
        
    theme_index = data.get("theme_index", 0)
    if not isinstance(theme_index, int) or not (0 <= theme_index <= 6):
        theme_index = 0
        
    return {
        "mask_library": mask_library, 
        "magic_hex": magic_hex, 
        "theme_index": theme_index
    }

def load_config() -> dict:
    new_config_path = get_config_path()
    old_config_path = PathManager.get_persist_dir() / OLD_CONFIG_FILE_NAME

    # 1. 优先尝试加载新版配置文件
    if new_config_path.exists():
        try:
            with open(new_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return normalize_config(data)
        except Exception:
            return normalize_config({})
            
    # 2. 🟢【兼容升级逻辑】：如果新版不存在，且存在旧版配置 (mask_config.json)
    if old_config_path.exists():
        try:
            with open(old_config_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                
            # 将旧数据标准化（自动补全主题等新字段）
            migrated_data = normalize_config(old_data)
            
            # 立即将数据写入新版配置文件，完成无缝迁移
            with open(new_config_path, "w", encoding="utf-8") as f:
                json.dump(migrated_data, f, ensure_ascii=False, indent=2)
                
            # 将旧文件重命名为备份文件，防止后续重复读取产生干扰
            try:
                old_config_path.rename(old_config_path.with_name(f"{OLD_CONFIG_FILE_NAME}.bak"))
            except Exception:
                pass # 若重命名由于权限问题失败，也不影响主流程
                
            return migrated_data
        except Exception:
            pass

    # 3. 全新安装，返回默认配置
    return normalize_config({})

def save_config(config: dict):
    config = normalize_config(config)
    with open(get_config_path(), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def format_file_size(size_bytes: int) -> str:
    """将字节大小格式化为人类可读的字符串。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def magic_to_display_text(magic: bytes) -> str:
    try: ascii_part = magic.decode("utf-8")
    except Exception: ascii_part = "<非UTF-8字节序列>"
    return f"HEX={magic.hex().upper()} | BYTES={magic!r} | TEXT={ascii_part}"

def build_non_conflicting_path(target_path: Path, tag: str, reserved_paths=None) -> Path:
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

def collect_files_from_paths(paths):
    results, seen = [], set()
    for p in paths:
        path = Path(p)
        if not path.exists(): continue
        if path.is_file():
            s = str(path.resolve())
            if s not in seen:
                seen.add(s), results.append(s)
        elif path.is_dir():
            for sub in path.rglob("*"):
                if sub.is_file():
                    s = str(sub.resolve())
                    if s not in seen:
                        seen.add(s), results.append(s)
    return results

# =================== 反侦察: 字节异或加密 ===================
def xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key: return data
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

# =================== 文件操作核心 ===================
def parse_disguised_metadata(file_obj, file_size: int, magic: bytes):
    file_obj.seek(-len(magic), os.SEEK_END)
    if file_obj.read(len(magic)) != magic:
        raise DisguiseError("文件尾标记无效")

    try:
        if file_size >= len(magic) + 13:
            file_obj.seek(-(len(magic) + 13), os.SEEK_END)
            encrypted_meta = file_obj.read(13)
            dec_meta = xor_bytes(encrypted_meta, magic)
            
            name_len = dec_meta[0]
            head_len = struct.unpack("<I", dec_meta[1:5])[0]
            original_size = struct.unpack("<Q", dec_meta[5:13])[0]
            
            name_pos = file_size - len(magic) - 13 - name_len
            head_pos = name_pos - head_len
            
            if 0 <= name_pos <= file_size and 0 <= head_pos <= file_size:
                file_obj.seek(name_pos)
                raw_name = file_obj.read(name_len)
                try:
                    decoded_xor = xor_bytes(raw_name, magic).decode("utf-8")
                    if decoded_xor and decoded_xor == Path(decoded_xor).name and decoded_xor not in (".", ".."):
                        return {"format": "v4", "head_len": head_len, "name_len": name_len,
                                "name_pos": name_pos, "head_pos": head_pos,
                                "original_name": decoded_xor, "original_size": original_size}
                except Exception: pass
    except Exception: pass

    try:
        if file_size >= len(magic) + 13:
            file_obj.seek(-(len(magic) + 8), os.SEEK_END)
            original_size = struct.unpack("<Q", file_obj.read(8))[0]
            file_obj.seek(-(len(magic) + 12), os.SEEK_END)
            head_len = struct.unpack("<I", file_obj.read(4))[0]
            file_obj.seek(-(len(magic) + 13), os.SEEK_END)
            name_len = struct.unpack("B", file_obj.read(1))[0]

            name_pos = file_size - len(magic) - 13 - name_len
            head_pos = name_pos - head_len
            if 0 <= name_pos <= file_size and 0 <= head_pos <= file_size:
                file_obj.seek(name_pos)
                raw_name = file_obj.read(name_len)
                
                candidate = None
                try:
                    decoded_xor = xor_bytes(raw_name, magic).decode("utf-8")
                    if decoded_xor and decoded_xor == Path(decoded_xor).name and decoded_xor not in (".", ".."):
                        candidate = decoded_xor
                except Exception: pass

                if not candidate:
                    try:
                        decoded_plain = raw_name.decode("utf-8")
                        if decoded_plain and decoded_plain == Path(decoded_plain).name and decoded_plain not in (".", ".."):
                            candidate = decoded_plain
                    except Exception: pass

                if candidate:
                    return {"format": "v2_v3", "head_len": head_len, "name_len": name_len,
                            "name_pos": name_pos, "head_pos": head_pos,
                            "original_name": candidate, "original_size": original_size}
    except Exception: pass

    try:
        file_obj.seek(-(len(magic) + 4), os.SEEK_END)
        head_len = struct.unpack("<I", file_obj.read(4))[0]
        file_obj.seek(-(len(magic) + 5), os.SEEK_END)
        name_len = struct.unpack("B", file_obj.read(1))[0]
        if name_len > file_size: raise DisguiseError("名称长度非法")
        name_pos = file_size - len(magic) - 5 - name_len
        if name_pos < 0: raise DisguiseError("name_pos 非法")
        head_pos = name_pos - head_len
        if head_pos < 0: raise DisguiseError("head_pos 非法")
        file_obj.seek(name_pos)
        raw_name = file_obj.read(name_len)
        if len(raw_name) != name_len: raise DisguiseError("名称长度不足")
        # 一次性读取完毕，后续不再 seek/read，避免文件指针问题
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
                raise DisguiseError(f"无法解析后缀：{e}")
            original_name = Path(file_obj.name).stem + original_suffix

        return {"format": "v1", "head_len": head_len, "name_len": name_len,
                "name_pos": name_pos, "head_pos": head_pos, "original_name": original_name,
                "original_size": head_pos}
    except Exception as e:
        raise DisguiseError("解析失败：文件已被损坏、被平台二次压缩，或当前使用的魔术字错误！")

def is_disguised_file(file_path: str, magic: bytes) -> bool:
    path = Path(file_path)
    if not path.is_file(): return False
    try:
        if path.stat().st_size < (1 + 4 + len(magic)): return False
        with open(path, "rb") as f:
            f.seek(-len(magic), os.SEEK_END)
            return f.read(len(magic)) == magic
    except Exception: return False

def disguise_file(file_path: str, mask_path: str, magic: bytes, reserved_output_paths=None) -> str:
    file_path, mask_path = Path(file_path), Path(mask_path)
    if not file_path.is_file(): raise FileNotFoundError(f"目标不存在: {file_path}")
    if is_disguised_file(str(file_path), magic): raise DisguiseError("已经是伪装态")

    mask_size = mask_path.stat().st_size
    if mask_size == 0: raise DisguiseError("面具文件为空")

    original_file_name_bytes = file_path.name.encode("utf-8")
    if len(original_file_name_bytes) > 255: raise DisguiseError("文件名过长")
    
    obfuscated_name_bytes = xor_bytes(original_file_name_bytes, magic)
    original_size = file_path.stat().st_size
    actual_head_len = min(mask_size, original_size)
    safe_append_offset = max(original_size, mask_size)

    try:
        f = open(file_path, "r+b")
    except PermissionError:
        raise DisguiseError(f"无法打开文件（可能被占用）: {file_path}\n请关闭可能正在使用该文件的程序后重试。")

    with f:
        f.seek(safe_append_offset)
        f.truncate(safe_append_offset)

        bytes_left = actual_head_len
        while bytes_left > 0:
            read_size = min(CHUNK_SIZE, bytes_left)
            offset = bytes_left - read_size
            f.seek(offset)
            chunk = f.read(read_size)
            write_offset = safe_append_offset + (actual_head_len - bytes_left)
            f.seek(write_offset)
            f.write(chunk[::-1])
            bytes_left -= read_size

        f.seek(0)
        with open(mask_path, "rb") as mf:
            while True:
                chunk = mf.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)

        meta_struct = struct.pack("B", len(obfuscated_name_bytes)) + \
                      struct.pack("<I", actual_head_len) + \
                      struct.pack("<Q", original_size)
        encrypted_meta_struct = xor_bytes(meta_struct, magic)

        f.seek(0, os.SEEK_END)
        f.write(obfuscated_name_bytes)
        f.write(encrypted_meta_struct)
        f.write(magic)

    desired_path = file_path.with_suffix(mask_path.suffix)
    disguised_path = build_non_conflicting_path(desired_path, "disguised", reserved_output_paths)
    try:
        shutil.move(str(file_path), str(disguised_path))
    except PermissionError:
        raise DisguiseError(f"文件被占用或无权限移动: {file_path}\n请关闭可能正在使用该文件的程序后重试。")
    return str(disguised_path)

def reveal_file(file_path: str, magic: bytes, reserved_output_paths=None) -> str:
    file_path = Path(file_path)
    if not is_disguised_file(str(file_path), magic): raise DisguiseError("非当前魔术字对应伪装文件")

    try:
        f = open(file_path, "r+b")
    except PermissionError:
        raise DisguiseError(f"无法打开文件（可能被占用）: {file_path}\n请关闭可能正在使用该文件的程序后重试。")

    with f:
        meta = parse_disguised_metadata(f, file_path.stat().st_size, magic)
        bytes_left = meta["head_len"]
        read_offset = meta["head_pos"]
        while bytes_left > 0:
            read_size = min(CHUNK_SIZE, bytes_left)
            f.seek(read_offset)
            chunk = f.read(read_size)
            write_offset = bytes_left - read_size
            f.seek(write_offset)
            f.write(chunk[::-1])
            read_offset += read_size
            bytes_left -= read_size
        f.truncate(meta["original_size"])

    desired_path = file_path.parent / meta["original_name"]
    restored_path = desired_path
    if str(desired_path.resolve()) in {str(Path(p).resolve()) for p in (reserved_output_paths or [])}:
        restored_path = build_non_conflicting_path(desired_path, "restored", reserved_output_paths)
    try:
        shutil.move(str(file_path), str(restored_path))
    except PermissionError:
        raise DisguiseError(f"文件被占用或无权限移动: {file_path}\n请关闭可能正在使用该文件的程序后重试。")
    return str(restored_path)


# =================== 恢复脚本模板 ===================
# 解析逻辑与 parse_disguised_metadata 保持一致，避免维护两份代码。

_RESTORE_SCRIPT_TEMPLATE = '''import sys
import os
import struct
from pathlib import Path

MAGIC = bytes.fromhex("__MAGIC_HEX__")
CHUNK_SIZE = 4 * 1024 * 1024
SELF_NAMES = {__SELF_NAMES_SET__}


def xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key:
        return data
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        return Path(sys.argv[0]).resolve().parent
    return Path(__file__).resolve().parent


def is_disguised_file(p: Path) -> bool:
    try:
        if p.stat().st_size < (1 + 4 + len(MAGIC)):
            return False
        with open(p, "rb") as f:
            f.seek(-len(MAGIC), os.SEEK_END)
            return f.read(len(MAGIC)) == MAGIC
    except Exception:
        return False


def _try_parse_name(raw_bytes, magic):
    """尝试从原始字节中解析文件名，优先 XOR 解密，回退明文。"""
    try:
        decoded = xor_bytes(raw_bytes, magic).decode("utf-8")
        if decoded and decoded == Path(decoded).name and decoded not in (".", ".."):
            return decoded
    except Exception:
        pass
    try:
        decoded = raw_bytes.decode("utf-8")
        if decoded and decoded == Path(decoded).name and decoded not in (".", ".."):
            return decoded
    except Exception:
        pass
    return None


def parse_metadata(f, sz):
    f.seek(-len(MAGIC), os.SEEK_END)
    if f.read(len(MAGIC)) != MAGIC:
        raise Exception("标记无效")

    # v4: 加密元数据  name_len(1B XOR) + head_len(4B XOR) + original_size(8B XOR) + magic
    try:
        if sz >= len(MAGIC) + 13:
            f.seek(-(len(MAGIC) + 13), os.SEEK_END)
            dec_meta = xor_bytes(f.read(13), MAGIC)
            nlen = dec_meta[0]
            hlen = struct.unpack("<I", dec_meta[1:5])[0]
            osize = struct.unpack("<Q", dec_meta[5:13])[0]
            npos = sz - len(MAGIC) - 13 - nlen
            hpos = npos - hlen
            if 0 <= npos <= sz and 0 <= hpos <= sz:
                f.seek(npos)
                raw = f.read(nlen)
                name = _try_parse_name(raw, MAGIC)
                if name:
                    return {"hlen": hlen, "hpos": hpos, "name": name, "osize": osize}
    except Exception:
        pass

    # v2/v3: 明文元数据  name_len(1B) + head_len(4B) + original_size(8B) + magic
    try:
        if sz >= len(MAGIC) + 13:
            f.seek(-(len(MAGIC) + 8), os.SEEK_END)
            osize = struct.unpack("<Q", f.read(8))[0]
            f.seek(-(len(MAGIC) + 12), os.SEEK_END)
            hlen = struct.unpack("<I", f.read(4))[0]
            f.seek(-(len(MAGIC) + 13), os.SEEK_END)
            nlen = struct.unpack("B", f.read(1))[0]
            npos = sz - len(MAGIC) - 13 - nlen
            hpos = npos - hlen
            if 0 <= npos <= sz and 0 <= hpos <= sz:
                f.seek(npos)
                raw_name = f.read(nlen)
                name = _try_parse_name(raw_name, MAGIC)
                if name:
                    return {"hlen": hlen, "hpos": hpos, "name": name, "osize": osize}
    except Exception:
        pass

    # v1:  name_len(1B) + head_len(4B) + magic  (无 original_size)
    f.seek(-(len(MAGIC) + 4), os.SEEK_END)
    hlen = struct.unpack("<I", f.read(4))[0]
    f.seek(-(len(MAGIC) + 5), os.SEEK_END)
    nlen = struct.unpack("B", f.read(1))[0]
    if nlen > sz:
        raise Exception("名称长度非法")
    npos = sz - len(MAGIC) - 5 - nlen
    if npos < 0:
        raise Exception("name_pos 非法")
    hpos = npos - hlen
    if hpos < 0:
        raise Exception("head_pos 非法")
    f.seek(npos)
    raw_name = f.read(nlen)
    if len(raw_name) != nlen:
        raise Exception("名称长度不足")
    # 一次性读取完毕，后续不再 seek/read，避免文件指针问题
    name = _try_parse_name(raw_name, MAGIC)
    if not name:
        # 回退：当作后缀拼接
        try:
            suffix = raw_name.decode("utf-8")
        except Exception as e:
            raise Exception(f"无法解析后缀: {e}")
        name = Path(fp_name).stem + suffix
    return {"hlen": hlen, "hpos": hpos, "name": name, "osize": hpos}


def reveal_file(fp: Path, reserved):
    global fp_name
    fp_name = fp.name
    with open(fp, "r+b") as f:
        meta = parse_metadata(f, fp.stat().st_size)
        bytes_left, read_offset = meta["hlen"], meta["hpos"]
        while bytes_left > 0:
            read_size = min(CHUNK_SIZE, bytes_left)
            f.seek(read_offset)
            chunk = f.read(read_size)
            write_offset = bytes_left - read_size
            f.seek(write_offset)
            f.write(chunk[::-1])
            read_offset += read_size
            bytes_left -= read_size
        f.truncate(meta["osize"])

    dp = fp.parent / meta["name"]
    rest = dp
    if str(dp.resolve()) in reserved:
        idx = 1
        while True:
            c = dp.with_name(f"{dp.stem}_restored_{idx}{dp.suffix}")
            if str(c.resolve()) not in reserved and not c.exists():
                rest = c
                break
            idx += 1
    fp.replace(rest)
    return rest


fp_name = ""


def main():
    global fp_name
    bd = get_base_dir()
    print(f"扫描: {bd}\\n魔术字: {MAGIC.hex()}\\n" + "-" * 40)
    res, fail = 0, 0
    reserved = {str(p.resolve()) for p in bd.rglob("*") if p.is_file()}
    for p in bd.rglob("*"):
        if p.is_file() and p.name.lower() not in SELF_NAMES:
            try:
                reserved.discard(str(p.resolve()))
                if is_disguised_file(p):
                    fp_name = p.name
                    np = reveal_file(p, reserved)
                    reserved.add(str(np.resolve()))
                    res += 1
                    print(f"[恢复] {p.name} -> {np.name}")
            except Exception as e:
                fail += 1
                print(f"[失败] {p.name} -> {e}")
    print(f"\\n完成: 成功 {res}, 失败 {fail}")
    input("按回车退出...")


if __name__ == "__main__":
    main()
'''


def _build_restore_script(magic_hex: str, script_filename: str) -> str:
    """根据模板生成恢复脚本源码。"""
    self_names = f'"{script_filename}", "{script_filename.replace(".py", ".exe")}"'
    return (
        _RESTORE_SCRIPT_TEMPLATE
        .replace("__MAGIC_HEX__", magic_hex)
        .replace("__SELF_NAMES_SET__", self_names)
    )


def _build_android_project(magic_hex: str, project_dir: Path, script_name: str):
    """将 Android 项目模板写入指定目录。"""
    from android_templates import (
        GRADLE_SETTINGS, PROJECT_BUILD_GRADLE, APP_BUILD_GRADLE, GRADLE_PROPERTIES,
        GRADLE_WRAPPER_PROPERTIES,
        ANDROID_MANIFEST, ACTIVITY_MAIN_XML, STRINGS_XML, COLORS_XML, STYLES_XML,
        RESTORE_ENGINE_JAVA, MAIN_ACTIVITY_JAVA,
    )

    pkg = "com.apluse.restore"
    app_name = "APLUSE 3.4"
    self_names_set = f'"{script_name}", "{script_name.replace(".py", ".exe")}"'

    def apply(text):
        return (text
                .replace("__MAGIC_HEX__", magic_hex)
                .replace("__APP_NAME__", app_name)
                .replace("__PACKAGE_NAME__", pkg)
                .replace("__SELF_NAMES_SET__", self_names_set))

    pkg_dir = project_dir / "app" / "src" / "main" / "java" / "com" / "apluse" / "restore"
    res_dir = project_dir / "app" / "src" / "main" / "res"
    layout_dir = res_dir / "layout"
    values_dir = res_dir / "values"
    wrapper_dir = project_dir / "gradle" / "wrapper"

    for d in [pkg_dir, layout_dir, values_dir, wrapper_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Gradle 文件
    (project_dir / "settings.gradle").write_text(apply(GRADLE_SETTINGS), encoding="utf-8")
    (project_dir / "build.gradle").write_text(apply(PROJECT_BUILD_GRADLE), encoding="utf-8")
    (project_dir / "gradle.properties").write_text(apply(GRADLE_PROPERTIES), encoding="utf-8")
    (project_dir / "app" / "build.gradle").write_text(apply(APP_BUILD_GRADLE), encoding="utf-8")
    (wrapper_dir / "gradle-wrapper.properties").write_text(apply(GRADLE_WRAPPER_PROPERTIES), encoding="utf-8")

    # AndroidManifest
    manifest_dir = project_dir / "app" / "src" / "main"
    (manifest_dir / "AndroidManifest.xml").write_text(apply(ANDROID_MANIFEST), encoding="utf-8")

    # 资源文件
    (layout_dir / "activity_main.xml").write_text(apply(ACTIVITY_MAIN_XML), encoding="utf-8")
    (values_dir / "strings.xml").write_text(apply(STRINGS_XML), encoding="utf-8")
    (values_dir / "colors.xml").write_text(apply(COLORS_XML), encoding="utf-8")
    (values_dir / "styles.xml").write_text(apply(STYLES_XML), encoding="utf-8")

    # Java 源码
    (pkg_dir / "RestoreEngine.java").write_text(apply(RESTORE_ENGINE_JAVA), encoding="utf-8")
    (pkg_dir / "MainActivity.java").write_text(apply(MAIN_ACTIVITY_JAVA), encoding="utf-8")


def _convert_icon_for_android(project_dir: Path, log_cb):
    """将 icon.ico 转换为 Android mipmap PNG 图标。"""
    icon_path = PathManager.get_resource_dir() / "icon.ico"
    if not icon_path.exists():
        log_cb("icon.ico 不存在，跳过图标设置")
        return

    # Android 图标尺寸: mdpi=48, hdpi=72, xhdpi=96, xxhdpi=144, xxxhdpi=192
    sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    res_dir = project_dir / "app" / "src" / "main" / "res"

    try:
        from PIL import Image
        img = Image.open(str(icon_path))
        for folder, size in sizes.items():
            out_dir = res_dir / folder
            out_dir.mkdir(parents=True, exist_ok=True)
            resized = img.resize((size, size), Image.LANCZOS)
            resized.save(str(out_dir / "ic_launcher.png"), "PNG")
        log_cb("已将 icon.ico 转换为 Android 图标")
    except ImportError:
        log_cb("未安装 Pillow，跳过图标转换（pip install Pillow 可启用）")
    except Exception as e:
        log_cb(f"图标转换失败: {e}")


# =================== 引擎状态类 ===================
class DisguiseEngine:
    def __init__(self):
        self.config = load_config()
        self.target_files = []
        self.mask_library = []
        self._load_mask_library_from_config()

    def _load_mask_library_from_config(self):
        library = self.config.get("mask_library", [])
        old_library = self.mask_library[:] if self.mask_library else []
        self.mask_library = [s for s in (str(Path(p).resolve()) for p in library) if Path(s).is_file()]
        # 只在面具库实际发生变化时才写磁盘（如启动时有文件被移除）
        if self.mask_library != old_library:
            self.save_config()

    def save_config(self):
        self.config["mask_library"] = self.mask_library[:]
        save_config(self.config)

    def get_magic_bytes(self) -> bytes:
        try:
            magic = bytes.fromhex(self.config.get("magic_hex", DEFAULT_MAGIC.hex()))
            return magic if (1 <= len(magic) <= 32) else DEFAULT_MAGIC
        except Exception: return DEFAULT_MAGIC

    def parse_and_set_magic(self, raw_text: str) -> bytes:
        text = (raw_text or "").strip()
        if not text: raise DisguiseError("请输入魔术字")
        compact = text.replace(" ", "").replace("\n", "").replace("\t", "")
        if compact.lower().startswith("0x"): compact = compact[2:]

        if compact and all(ch in "0123456789abcdefABCDEF" for ch in compact) and len(compact) % 2 == 0:
            data = bytes.fromhex(compact)
        else:
            data = text.encode("utf-8")

        if not (1 <= len(data) <= 32): raise DisguiseError("长度必须在 1 到 32 字节之间")
        self.config["magic_hex"] = data.hex()
        self.save_config()
        return data

    def generate_random_magic(self) -> bytes:
        magic = secrets.token_bytes(4)
        self.config["magic_hex"] = magic.hex()
        self.save_config()
        return magic

    def reset_magic(self) -> bytes:
        self.config["magic_hex"] = DEFAULT_MAGIC.hex()
        self.save_config()
        return DEFAULT_MAGIC

    def get_common_target_parent_dir(self) -> Path:
        if not self.target_files: raise DisguiseError("没有目标文件")
        resolved = [Path(p).resolve() for p in self.target_files if Path(p).is_file()]
        if not resolved: raise DisguiseError("目标列表中没有有效文件")
        try: common_dir = Path(os.path.commonpath([str(p.parent) for p in resolved]))
        except ValueError: raise DisguiseError("不在可计算公共目录的结构中")
        if not common_dir.exists() or not common_dir.is_dir(): raise DisguiseError("目录无效")
        return common_dir

    def get_random_mask_file(self) -> str:
        # 过滤无效文件，但不立即写磁盘（批量操作时由调用方统一保存）
        original_len = len(self.mask_library)
        self.mask_library = [p for p in self.mask_library if Path(p).is_file()]
        if len(self.mask_library) != original_len:
            self.save_config()
        if not self.mask_library:
            raise DisguiseError("面具库为空")
        return random.choice(self.mask_library)

    def detect_status(self, progress_cb, log_cb, process_events_cb=None):
        magic = self.get_magic_bytes()
        disguised_count, original_count, failed = 0, 0, []
        total = len(self.target_files)

        log_cb(f"开始检测，魔术字：{magic_to_display_text(magic)}")
        progress_cb(0, total, "正在检测文件状态...", f"0/{total}")

        for index, path in enumerate(self.target_files, start=1):
            try:
                if is_disguised_file(path, magic):
                    disguised_count += 1
                    log_cb(f"[伪装态] {path}")
                else:
                    original_count += 1
                    log_cb(f"[原始态] {path}")
            except Exception as e: failed.append(f"{path} -> {e}")
            progress_cb(index, total, "正在检测...", f"{index}/{total}")
            if process_events_cb:
                process_events_cb()

        return original_count, disguised_count, failed

    def handle_toggle(self, progress_cb, log_cb, process_events_cb=None):
        magic = self.get_magic_bytes()
        need_mask = any(not is_disguised_file(p, magic) for p in self.target_files)
        if need_mask and not self.mask_library:
            raise DisguiseError("存在需伪装文件，但面具库为空")

        reserved_outputs = {str(Path(p).resolve()) for p in self.target_files if Path(p).exists()}
        success, failed = 0, []
        total = len(self.target_files)

        log_cb(f"执行自动切换，魔术字：{magic_to_display_text(magic)}")
        progress_cb(0, total, "正在批处理...", f"0/{total}")

        for index, old_path in enumerate(self.target_files[:], start=1):
            try:
                reserved_outputs.discard(str(Path(old_path).resolve()))
                if is_disguised_file(old_path, magic):
                    log_cb(f"准备还原：{old_path}")
                    new_path = reveal_file(old_path, magic, reserved_outputs)
                    log_cb(f"还原完成：{new_path}")
                else:
                    mask_file = self.get_random_mask_file()
                    log_cb(f"准备伪装(使用 {mask_file})：{old_path}")
                    new_path = disguise_file(old_path, mask_file, magic, reserved_outputs)
                    log_cb(f"伪装完成：{new_path}")

                self.target_files[index-1] = str(Path(new_path).resolve())
                reserved_outputs.add(self.target_files[index-1])
                success += 1
            except Exception as e:
                reserved_outputs.add(str(Path(old_path).resolve()))
                failed.append(f"{old_path} -> {e}")
                log_cb(f"失败：{old_path} -> {e}")

            progress_cb(index, total, "正在批处理...", f"已处理 {index}/{total}")
            if process_events_cb:
                process_events_cb()

        return success, failed

    def _get_real_python(self) -> str:
        if getattr(sys, "frozen", False) or "__compiled__" in globals():
            if shutil.which("python"): return "python"
            if shutil.which("py"): return "py"
            raise DisguiseError("未检测到系统 Python 环境，打包环境不可执行子打包功能。")
        return sys.executable

    def _ensure_pyinstaller(self, log_cb, process_events_cb, python_exe: str):
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

        try:
            res = subprocess.run(
                [python_exe, "-m", "PyInstaller", "--version"], 
                capture_output=True, text=True, stdin=subprocess.DEVNULL, **kwargs
            )
            if res.returncode == 0: return
        except Exception: pass

        log_cb("⚠️ 未检测到 PyInstaller 模块。正在自动安装，请稍候...")
        if process_events_cb: process_events_cb()
        
        try:
            process = subprocess.Popen(
                [python_exe, "-m", "pip", "install", "--user", "pyinstaller", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, stdin=subprocess.DEVNULL, **kwargs
            )
            for line in process.stdout:
                line = line.strip()
                if line: log_cb(f"[pip] {line}")
                if process_events_cb: process_events_cb()
            
            process.wait()
            if process.returncode != 0:
                raise DisguiseError(f"安装 PyInstaller 失败，返回码: {process.returncode}")
            
            log_cb("✅ PyInstaller 自动安装成功！")
        except Exception as e:
            raise DisguiseError(f"启动安装进程失败: {e}")

    def generate_restore_exe(self, output_dir: Path, log_cb, process_events_cb=None):
        python_exe = self._get_real_python()
        self._ensure_pyinstaller(log_cb, process_events_cb, python_exe)

        magic = self.get_magic_bytes()
        magic_tag = magic.hex()
        script_name = f"{magic_tag}_restore.py"
        py_script_path = PathManager.get_persist_dir() / script_name

        script_content = _build_restore_script(magic_tag, script_name)
        try:
            with open(py_script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            output_dir.mkdir(parents=True, exist_ok=True)
            build_dir = output_dir / "build_pyinstaller_restore"
            spec_dir = output_dir / "spec_pyinstaller_restore"
            restore_name = f"{magic_tag}_restore"
            exe_name = restore_name + ".exe"
            dist_path = output_dir / exe_name

            # 查找图标文件
            icon_path = PathManager.get_resource_dir() / "icon.ico"

            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

            cmd = [
                python_exe, "-m", "PyInstaller", "--onefile",
                "--name", restore_name,
                "--exclude-module", "PyQt5",
                "--exclude-module", "PyQt6",
                "--exclude-module", "PySide2",
                "--exclude-module", "PySide6",
                "--exclude-module", "tkinter",
                "--exclude-module", "numpy",
                "--exclude-module", "pandas",
                "--exclude-module", "matplotlib",
                "--exclude-module", "scipy",
                "--exclude-module", "PIL",
                "--exclude-module", "requests",
                "--distpath", str(output_dir),
                "--workpath", str(build_dir),
                "--specpath", str(spec_dir),
            ]
            if icon_path.exists():
                cmd.extend(["--icon", str(icon_path)])
            cmd.append(str(py_script_path))

            log_cb(f"🚀 正在调用 PyInstaller 进行极限瘦身打包，请耐心等待...")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                **kwargs
            )
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    log_cb(f"[PyInstaller] {line}")
                if process_events_cb:
                    process_events_cb()
            
            process.wait()
            
            if process.returncode != 0:
                raise DisguiseError(f"打包过程失败，返回码: {process.returncode}")

            shutil.rmtree(build_dir, ignore_errors=True)
            shutil.rmtree(spec_dir, ignore_errors=True)
            shutil.rmtree(py_script_path.parent / "__pycache__", ignore_errors=True)
            if (spec_dir / f"{py_script_path.stem}.spec").exists():
                (spec_dir / f"{py_script_path.stem}.spec").unlink()
            
            return dist_path
        finally:
            if py_script_path.exists(): py_script_path.unlink()

    def generate_restore_apk(self, output_dir: Path, log_cb, process_events_cb=None):
        magic = self.get_magic_bytes()
        magic_tag = magic.hex()
        script_name = f"apluse_restore_{magic_tag}.py"

        project_dir = output_dir / "apluse_restore_android"
        log_cb("正在生成 Android 项目...")

        _build_android_project(magic_tag, project_dir, script_name)
        log_cb("项目源码已生成")

        # 尝试将 icon.ico 转换为 Android PNG 图标
        _convert_icon_for_android(project_dir, log_cb)

        # 尝试使用 Gradle 编译
        gradle_cmd = shutil.which("gradle") or shutil.which("gradlew")
        apk_path = project_dir / "app" / "build" / "outputs" / "apk" / "release" / "app-release-unsigned.apk"

        if gradle_cmd:
            log_cb(f"检测到 Gradle: {gradle_cmd}，正在编译...")
            try:
                kwargs = {}
                if sys.platform == "win32":
                    kwargs["creationflags"] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

                process = subprocess.Popen(
                    [gradle_cmd, "assembleRelease", "--no-daemon", "--quiet"],
                    cwd=str(project_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    **kwargs,
                )
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        log_cb(f"[Gradle] {line}")
                    if process_events_cb:
                        process_events_cb()

                process.wait()
                if process.returncode == 0 and apk_path.exists():
                    final_apk = output_dir / "apluse_restore.apk"
                    shutil.copy2(str(apk_path), str(final_apk))
                    shutil.rmtree(str(project_dir), ignore_errors=True)
                    log_cb(f"编译成功: {final_apk.name}")
                    return final_apk
                else:
                    log_cb("Gradle 编译失败，请使用 Android Studio 打开项目手动编译")
            except Exception as e:
                log_cb(f"Gradle 执行异常: {e}")
        else:
            log_cb("未检测到 Gradle，请用 Android Studio 打开项目目录进行编译")
            log_cb(f"项目路径: {project_dir}")

        # 无法自动编译时，返回项目目录路径
        log_cb(f"Android 项目已就绪，请在 Android Studio 中打开: {project_dir}")
        return project_dir