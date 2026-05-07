package com.apluse.restore;

import java.io.*;
import java.util.*;

/**
 * 核心恢复引擎 — 与 Python 版 core.py 的 parse_disguised_metadata 逻辑完全一致。
 * 支持 v4(加密)、v2/v3(明文+size)、v1(仅后缀) 三种元数据格式。
 */
public class RestoreEngine {

    private static final int CHUNK_SIZE = 4 * 1024 * 1024;
    private final byte[] magic;
    private final Set<String> selfNames;

    public RestoreEngine(byte[] magic, Set<String> selfNames) {
        this.magic = magic;
        this.selfNames = selfNames;
    }

    // ===== 字节工具 =====

    public static byte[] xorBytes(byte[] data, byte[] key) {
        if (key.length == 0) return data;
        byte[] result = new byte[data.length];
        for (int i = 0; i < data.length; i++) {
            result[i] = (byte) (data[i] ^ key[i % key.length]);
        }
        return result;
    }

    public static byte[] hexToBytes(String hex) {
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                    + Character.digit(hex.charAt(i + 1), 16));
        }
        return data;
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b & 0xff));
        }
        return sb.toString();
    }

    // ===== 文件检测 =====

    public boolean isDisguisedFile(File file) {
        try {
            if (!file.isFile()) return false;
            long size = file.length();
            if (size < 1 + 4 + magic.length) return false;
            try (RandomAccessFile raf = new RandomAccessFile(file, "r")) {
                raf.seek(size - magic.length);
                byte[] tail = new byte[magic.length];
                raf.readFully(tail);
                return Arrays.equals(tail, magic);
            }
        } catch (Exception e) {
            return false;
        }
    }

    // ===== 文件名解析 =====

    private String tryParseName(byte[] raw, byte[] key) {
        // 尝试 XOR 解密
        try {
            byte[] dec = xorBytes(raw, key);
            String s = new String(dec, "UTF-8");
            if (isValidFileName(s)) return s;
        } catch (Exception ignored) {}
        // 尝试明文
        try {
            String s = new String(raw, "UTF-8");
            if (isValidFileName(s)) return s;
        } catch (Exception ignored) {}
        return null;
    }

    private boolean isValidFileName(String s) {
        if (s == null || s.isEmpty()) return false;
        if (s.equals(".") || s.equals("..")) return false;
        // 检查是否为纯文件名（不含路径分隔符）
        return !s.contains("/") && !s.contains("\\") && s.equals(new File(s).getName());
    }

    // ===== 元数据解析 =====

    public static class Metadata {
        public final int headLen;
        public final long headPos;
        public final String name;
        public final long originalSize;

        public Metadata(int headLen, long headPos, String name, long originalSize) {
            this.headLen = headLen;
            this.headPos = headPos;
            this.name = name;
            this.originalSize = originalSize;
        }
    }

    public Metadata parseMetadata(RandomAccessFile f, long sz) throws Exception {
        // 验证尾部魔术字
        f.seek(sz - magic.length);
        byte[] tail = new byte[magic.length];
        f.readFully(tail);
        if (!Arrays.equals(tail, magic)) {
            throw new Exception("标记无效");
        }

        // v4: 加密元数据  name_len(1B XOR) + head_len(4B XOR) + original_size(8B XOR) + magic
        try {
            if (sz >= magic.length + 13) {
                f.seek(sz - magic.length - 13);
                byte[] encMeta = new byte[13];
                f.readFully(encMeta);
                byte[] decMeta = xorBytes(encMeta, magic);
                int nlen = decMeta[0] & 0xff;
                int hlen = (decMeta[1] & 0xff) | ((decMeta[2] & 0xff) << 8)
                        | ((decMeta[3] & 0xff) << 16) | ((decMeta[4] & 0xff) << 24);
                long osize = (decMeta[5] & 0xffL) | ((decMeta[6] & 0xffL) << 8)
                        | ((decMeta[7] & 0xffL) << 16) | ((decMeta[8] & 0xffL) << 24)
                        | ((decMeta[9] & 0xffL) << 32) | ((decMeta[10] & 0xffL) << 40)
                        | ((decMeta[11] & 0xffL) << 48) | ((decMeta[12] & 0xffL) << 56);
                long npos = sz - magic.length - 13 - nlen;
                long hpos = npos - hlen;
                if (npos >= 0 && npos <= sz && hpos >= 0 && hpos <= sz) {
                    f.seek(npos);
                    byte[] raw = new byte[nlen];
                    f.readFully(raw);
                    String name = tryParseName(raw, magic);
                    if (name != null) return new Metadata(hlen, hpos, name, osize);
                }
            }
        } catch (Exception ignored) {}

        // v2/v3: 明文元数据  name_len(1B) + head_len(4B) + original_size(8B) + magic
        try {
            if (sz >= magic.length + 13) {
                f.seek(sz - magic.length - 8);
                byte[] buf8 = new byte[8];
                f.readFully(buf8);
                long osize = (buf8[0] & 0xffL) | ((buf8[1] & 0xffL) << 8)
                        | ((buf8[2] & 0xffL) << 16) | ((buf8[3] & 0xffL) << 24)
                        | ((buf8[4] & 0xffL) << 32) | ((buf8[5] & 0xffL) << 40)
                        | ((buf8[6] & 0xffL) << 48) | ((buf8[7] & 0xffL) << 56);

                f.seek(sz - magic.length - 12);
                byte[] buf4 = new byte[4];
                f.readFully(buf4);
                int hlen = (buf4[0] & 0xff) | ((buf4[1] & 0xff) << 8)
                        | ((buf4[2] & 0xff) << 16) | ((buf4[3] & 0xff) << 24);

                f.seek(sz - magic.length - 13);
                int nlen = f.readByte() & 0xff;

                long npos = sz - magic.length - 13 - nlen;
                long hpos = npos - hlen;
                if (npos >= 0 && npos <= sz && hpos >= 0 && hpos <= sz) {
                    f.seek(npos);
                    byte[] rawName = new byte[nlen];
                    f.readFully(rawName);
                    String name = tryParseName(rawName, magic);
                    if (name != null) return new Metadata(hlen, hpos, name, osize);
                }
            }
        } catch (Exception ignored) {}

        // v1: name_len(1B) + head_len(4B) + magic (无 original_size)
        {
            f.seek(sz - magic.length - 4);
            byte[] buf4 = new byte[4];
            f.readFully(buf4);
            int hlen = (buf4[0] & 0xff) | ((buf4[1] & 0xff) << 8)
                    | ((buf4[2] & 0xff) << 16) | ((buf4[3] & 0xff) << 24);

            f.seek(sz - magic.length - 5);
            int nlen = f.readByte() & 0xff;
            if (nlen > sz) throw new Exception("名称长度非法");

            long npos = sz - magic.length - 5 - nlen;
            if (npos < 0) throw new Exception("name_pos 非法");
            long hpos = npos - hlen;
            if (hpos < 0) throw new Exception("head_pos 非法");

            f.seek(npos);
            byte[] rawName = new byte[nlen];
            f.readFully(rawName);

            String name = tryParseName(rawName, magic);
            if (name == null) {
                // 回退：当作后缀拼接
                String suffix = new String(rawName, "UTF-8");
                String baseName = file.getName();
                int dotIdx = baseName.lastIndexOf('.');
                name = (dotIdx > 0 ? baseName.substring(0, dotIdx) : baseName) + suffix;
            }
            return new Metadata(hlen, hpos, name, hpos);
        }
    }

    // ===== 恢复文件 =====

    private File file; // 当前处理的文件，供 parseMetadata v1 回退使用

    public File revealFile(File fp, Set<String> reserved) throws Exception {
        this.file = fp;
        Metadata meta;
        try (RandomAccessFile raf = new RandomAccessFile(fp, "rw")) {
            meta = parseMetadata(raf, fp.length());
            long bytesLeft = meta.headLen;
            long readOffset = meta.headPos;
            byte[] chunk;

            while (bytesLeft > 0) {
                int readSize = (int) Math.min(CHUNK_SIZE, bytesLeft);
                raf.seek(readOffset);
                chunk = new byte[readSize];
                raf.readFully(chunk);
                // 反转
                for (int i = 0; i < readSize / 2; i++) {
                    byte tmp = chunk[i];
                    chunk[i] = chunk[readSize - 1 - i];
                    chunk[readSize - 1 - i] = tmp;
                }
                raf.seek(bytesLeft - readSize);
                raf.write(chunk);
                readOffset += readSize;
                bytesLeft -= readSize;
            }
            raf.setLength(meta.originalSize);
        }

        // 重命名
        File dest = new File(fp.getParent(), meta.name);
        if (reserved.contains(dest.getCanonicalPath())) {
            int idx = 1;
            String stem = meta.name;
            String ext = "";
            int dotIdx = meta.name.lastIndexOf('.');
            if (dotIdx > 0) {
                stem = meta.name.substring(0, dotIdx);
                ext = meta.name.substring(dotIdx);
            }
            while (true) {
                File candidate = new File(fp.getParent(), stem + "_restored_" + idx + ext);
                if (!reserved.contains(candidate.getCanonicalPath()) && !candidate.exists()) {
                    dest = candidate;
                    break;
                }
                idx++;
            }
        }
        if (!fp.renameTo(dest)) {
            throw new Exception("重命名失败: " + fp.getName() + " -> " + dest.getName());
        }
        return dest;
    }

    // ===== 扫描目录 =====

    public interface ScanCallback {
        void onFileFound(File file, boolean disguised);
    }

    public List<File> scanDirectory(File dir, ScanCallback cb) {
        List<File> disguised = new ArrayList<>();
        scanRecursive(dir, disguised, cb);
        return disguised;
    }

    private void scanRecursive(File dir, List<File> result, ScanCallback cb) {
        File[] files = dir.listFiles();
        if (files == null) return;
        for (File f : files) {
            if (f.isDirectory()) {
                scanRecursive(f, result, cb);
            } else if (f.isFile() && !selfNames.contains(f.getName().toLowerCase())) {
                boolean disguised = isDisguisedFile(f);
                if (cb != null) cb.onFileFound(f, disguised);
                if (disguised) result.add(f);
            }
        }
    }
}
