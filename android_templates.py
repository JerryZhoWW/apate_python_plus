"""
APLUSE ENGINE - Android 恢复工具模板
包含生成 Android 项目所需的全部模板常量。
占位符: __MAGIC_HEX__, __APP_NAME__, __PACKAGE_NAME__, __SELF_NAMES_SET__
"""

# =================== Gradle 配置 ===================

GRADLE_SETTINGS = """\
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "__APP_NAME__"
include ':app'
"""

PROJECT_BUILD_GRADLE = """\
plugins {
    id 'com.android.application' version '8.2.0' apply false
}
"""

APP_BUILD_GRADLE = """\
plugins {
    id 'com.android.application'
}

android {
    namespace '__PACKAGE_NAME__'
    compileSdk 34

    defaultConfig {
        applicationId "__PACKAGE_NAME__"
        minSdk 21
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
        }
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }
}
"""

GRADLE_PROPERTIES = """\
android.useAndroidX=true
org.gradle.jvmargs=-Xmx2048m
"""

GRADLE_WRAPPER_PROPERTIES = """\
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://mirrors.cloud.tencent.com/gradle/gradle-8.5-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""

# =================== AndroidManifest ===================

ANDROID_MANIFEST = """\
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" />

    <application
        android:label="__APP_NAME__"
        android:icon="@mipmap/ic_launcher"
        android:requestLegacyExternalStorage="true"
        android:theme="@style/AppTheme">

        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

    </application>
</manifest>
"""

# =================== 资源文件 ===================

ACTIVITY_MAIN_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="24dp"
    android:background="#121217">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="__APP_NAME__"
        android:textSize="22sp"
        android:textColor="#F4F4F5"
        android:textStyle="bold"
        android:layout_marginBottom="8dp" />

    <TextView
        android:id="@+id/tvMagic"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="魔术字: --"
        android:textColor="#A1A1AA"
        android:textSize="13sp"
        android:layout_marginBottom="8dp" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginBottom="16dp">

        <EditText
            android:id="@+id/etMagic"
            android:layout_width="0dp"
            android:layout_height="44dp"
            android:layout_weight="1"
            android:hint="输入 HEX 或文本魔术字"
            android:textColor="#F4F4F5"
            android:textColorHint="#52525B"
            android:background="#27272A"
            android:paddingStart="12dp"
            android:paddingEnd="12dp"
            android:textSize="14sp"
            android:fontFamily="monospace"
            android:singleLine="true"
            android:inputType="text" />

        <Button
            android:id="@+id/btnApplyMagic"
            android:layout_width="wrap_content"
            android:layout_height="44dp"
            android:text="应用"
            android:textSize="13sp"
            android:layout_marginStart="8dp" />

        <Button
            android:id="@+id/btnResetMagic"
            android:layout_width="wrap_content"
            android:layout_height="44dp"
            android:text="默认"
            android:textSize="13sp"
            android:layout_marginStart="4dp" />
    </LinearLayout>

    <Button
        android:id="@+id/btnSelectFolder"
        android:layout_width="match_parent"
        android:layout_height="52dp"
        android:text="选择文件夹"
        android:textSize="15sp"
        android:layout_marginBottom="12dp" />

    <Button
        android:id="@+id/btnScan"
        android:layout_width="match_parent"
        android:layout_height="52dp"
        android:text="扫描伪装文件"
        android:textSize="15sp"
        android:enabled="false"
        android:layout_marginBottom="12dp" />

    <Button
        android:id="@+id/btnRestore"
        android:layout_width="match_parent"
        android:layout_height="56dp"
        android:text="一键恢复全部"
        android:textSize="16sp"
        android:textStyle="bold"
        android:enabled="false"
        android:layout_marginBottom="20dp" />

    <TextView
        android:id="@+id/tvStatus"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="请选择包含伪装文件的文件夹"
        android:textColor="#A1A1AA"
        android:textSize="13sp"
        android:layout_marginBottom="12dp" />

    <ProgressBar
        android:id="@+id/progressBar"
        style="?android:attr/progressBarStyleHorizontal"
        android:layout_width="match_parent"
        android:layout_height="8dp"
        android:max="100"
        android:visibility="gone"
        android:layout_marginBottom="16dp" />

    <ScrollView
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:background="#000000"
        android:padding="12dp">

        <TextView
            android:id="@+id/tvLog"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:textColor="#10B981"
            android:fontFamily="monospace"
            android:textSize="12sp"
            android:text="> 等待操作...\n" />
    </ScrollView>

</LinearLayout>
"""

STRINGS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">__APP_NAME__</string>
</resources>
"""

COLORS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="purple_500">#FF6200EE</color>
    <color name="purple_700">#FF3700B3</color>
    <color name="teal_200">#FF03DAC5</color>
    <color name="teal_700">#FF018786</color>
    <color name="black">#FF000000</color>
    <color name="white">#FFFFFFFF</color>
</resources>
"""

STYLES_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="android:Theme.Material.Light.DarkActionBar">
        <item name="android:colorPrimary">#2563EB</item>
        <item name="android:colorPrimaryDark">#1D4ED8</item>
        <item name="android:colorAccent">#6D28D9</item>
    </style>
</resources>
"""

# =================== Java 源码 ===================

RESTORE_ENGINE_JAVA = r"""package __PACKAGE_NAME__;

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
"""

MAIN_ACTIVITY_JAVA = r"""package __PACKAGE_NAME__;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.*;
import android.provider.DocumentsContract;
import android.view.View;
import android.widget.*;
import java.io.File;
import java.util.*;

public class MainActivity extends Activity {

    private static final int REQUEST_PERMISSION = 100;
    private static final int REQUEST_FOLDER = 200;

    private static final String DEFAULT_MAGIC_HEX = "__MAGIC_HEX__";

    private Button btnSelectFolder, btnScan, btnRestore, btnApplyMagic, btnResetMagic;
    private TextView tvMagic, tvStatus, tvLog;
    private EditText etMagic;
    private ProgressBar progressBar;

    private RestoreEngine engine;
    private Set<String> selfNames;
    private byte[] currentMagic;
    private File selectedDir;
    private List<File> disguisedFiles = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvMagic = findViewById(R.id.tvMagic);
        tvStatus = findViewById(R.id.tvStatus);
        tvLog = findViewById(R.id.tvLog);
        etMagic = findViewById(R.id.etMagic);
        btnSelectFolder = findViewById(R.id.btnSelectFolder);
        btnScan = findViewById(R.id.btnScan);
        btnRestore = findViewById(R.id.btnRestore);
        btnApplyMagic = findViewById(R.id.btnApplyMagic);
        btnResetMagic = findViewById(R.id.btnResetMagic);
        progressBar = findViewById(R.id.progressBar);

        selfNames = new HashSet<>(Arrays.asList(__SELF_NAMES_SET__));

        // 初始化引擎（默认魔术字）
        initEngine(DEFAULT_MAGIC_HEX);

        btnApplyMagic.setOnClickListener(v -> applyMagicFromInput());
        btnResetMagic.setOnClickListener(v -> {
            etMagic.setText("");
            initEngine(DEFAULT_MAGIC_HEX);
            appendLog("已恢复默认魔术字");
        });
        btnSelectFolder.setOnClickListener(v -> requestPermissions());
        btnScan.setOnClickListener(v -> scanFolder());
        btnRestore.setOnClickListener(v -> restoreAll());
    }

    private void initEngine(String magicHex) {
        try {
            currentMagic = RestoreEngine.hexToBytes(magicHex);
            engine = new RestoreEngine(currentMagic, selfNames);
            tvMagic.setText("魔术字: HEX=" + magicHex.toUpperCase()
                    + "  (" + currentMagic.length + " 字节)");
            etMagic.setText(magicHex.toUpperCase());
        } catch (Exception e) {
            appendLog("[错误] 魔术字格式无效: " + e.getMessage());
        }
    }

    private void applyMagicFromInput() {
        String input = etMagic.getText().toString().trim();
        if (input.isEmpty()) {
            appendLog("[提示] 请输入魔术字");
            return;
        }
        // 尝试当作 HEX 解析
        String hex = input.replaceAll("\\s+", "");
        if (hex.startsWith("0x") || hex.startsWith("0X")) {
            hex = hex.substring(2);
        }
        boolean isHex = hex.length() % 2 == 0
                && hex.matches("[0-9a-fA-F]+");
        if (isHex) {
            initEngine(hex);
            appendLog("已应用 HEX 魔术字: " + hex.toUpperCase());
        } else {
            // 当作 UTF-8 文本
            try {
                byte[] bytes = input.getBytes("UTF-8");
                if (bytes.length < 1 || bytes.length > 32) {
                    appendLog("[错误] 长度必须在 1-32 字节之间");
                    return;
                }
                StringBuilder sb = new StringBuilder();
                for (byte b : bytes) sb.append(String.format("%02x", b & 0xff));
                initEngine(sb.toString());
                appendLog("已应用文本魔术字: " + input);
            } catch (Exception e) {
                appendLog("[错误] 编码失败: " + e.getMessage());
            }
        }
    }

    // ===== 权限 =====

    private void requestPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            // Android 11+: 请求 MANAGE_EXTERNAL_STORAGE
            if (!Environment.isExternalStorageManager()) {
                Intent intent = new Intent(android.provider.Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                intent.setData(Uri.parse("package:" + getPackageName()));
                startActivityForResult(intent, REQUEST_PERMISSION);
            } else {
                pickFolder();
            }
        } else {
            // Android 10 及以下
            if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                        Manifest.permission.READ_EXTERNAL_STORAGE,
                        Manifest.permission.WRITE_EXTERNAL_STORAGE
                }, REQUEST_PERMISSION);
            } else {
                pickFolder();
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_PERMISSION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                pickFolder();
            } else {
                appendLog("[错误] 存储权限被拒绝，无法访问文件");
            }
        }
    }

    // ===== 选择文件夹 =====

    private void pickFolder() {
        // 使用 SAF 选择文件夹（兼容 Android 11+）
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION
                | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try {
            startActivityForResult(intent, REQUEST_FOLDER);
        } catch (Exception e) {
            // SAF 不可用时，使用输入框
            showManualPathInput();
        }
    }

    private void showManualPathInput() {
        EditText input = new EditText(this);
        input.setHint("输入文件夹路径，如 /sdcard/Download");
        input.setText("/sdcard/");
        input.setSingleLine(true);

        new android.app.AlertDialog.Builder(this)
                .setTitle("输入文件夹路径")
                .setView(input)
                .setPositiveButton("确定", (d, w) -> {
                    String path = input.getText().toString().trim();
                    if (!path.isEmpty()) {
                        selectedDir = new File(path);
                        if (selectedDir.isDirectory()) {
                            onFolderSelected(path);
                        } else {
                            appendLog("[错误] 路径不存在或不是文件夹: " + path);
                        }
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_FOLDER && resultCode == RESULT_OK && data != null) {
            Uri treeUri = data.getData();
            if (treeUri != null) {
                // 持久化权限
                getContentResolver().takePersistableUriPermission(treeUri,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                // 将 URI 转换为文件路径
                String path = uriToPath(treeUri);
                if (path != null) {
                    selectedDir = new File(path);
                    onFolderSelected(path);
                } else {
                    // 无法转换时，使用 SAF 直接操作
                    appendLog("[提示] 使用 SAF 模式操作: " + treeUri);
                    selectedDir = new File(Environment.getExternalStorageDirectory(), "Download");
                    onFolderSelected(selectedDir.getAbsolutePath());
                }
            }
        } else if (requestCode == REQUEST_PERMISSION) {
            // 权限回调后继续选择文件夹
            pickFolder();
        }
    }

    private String uriToPath(Uri uri) {
        // 尝试从 tree URI 提取路径
        String docId = DocumentsContract.getTreeDocumentId(uri);
        if (docId != null) {
            // 格式: "primary:Download" -> "/storage/emulated/0/Download"
            String[] split = docId.split(":");
            if (split.length >= 2) {
                if ("primary".equals(split[0])) {
                    return Environment.getExternalStorageDirectory() + "/" + split[1];
                }
                // 外置存储
                return "/storage/" + split[0] + "/" + split[1];
            }
            // 根目录
            if ("primary".equals(docId)) {
                return Environment.getExternalStorageDirectory().getAbsolutePath();
            }
        }
        return null;
    }

    private void onFolderSelected(String path) {
        appendLog("已选择文件夹: " + path);
        tvStatus.setText("文件夹: " + path);
        btnScan.setEnabled(true);
        btnRestore.setEnabled(false);
        disguisedFiles.clear();
    }

    // ===== 扫描 =====

    private void scanFolder() {
        if (selectedDir == null || !selectedDir.isDirectory()) {
            appendLog("[错误] 请先选择有效文件夹");
            return;
        }
        btnScan.setEnabled(false);
        btnRestore.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);
        progressBar.setIndeterminate(true);
        tvStatus.setText("正在扫描...");

        new Thread(() -> {
            disguisedFiles.clear();
            int[] counts = {0, 0}; // [original, disguised]

            List<File> found = engine.scanDirectory(selectedDir, (file, isDisguised) -> {
                counts[isDisguised ? 1 : 0]++;
                if (isDisguised) {
                    appendLog("[伪装态] " + file.getName());
                }
            });

            disguisedFiles.addAll(found);

            runOnUiThread(() -> {
                progressBar.setVisibility(View.GONE);
                btnScan.setEnabled(true);
                btnRestore.setEnabled(!disguisedFiles.isEmpty());
                int total = counts[0] + counts[1];
                tvStatus.setText(String.format("扫描完成: 共 %d 个文件, 伪装态 %d, 原始态 %d",
                        total, counts[1], counts[0]));
                appendLog(String.format("扫描结束: 共 %d 个文件, 伪装态 %d, 原始态 %d",
                        total, counts[1], counts[0]));
            });
        }).start();
    }

    // ===== 恢复 =====

    private void restoreAll() {
        if (disguisedFiles.isEmpty()) {
            appendLog("[提示] 没有需要恢复的文件");
            return;
        }
        btnRestore.setEnabled(false);
        btnScan.setEnabled(false);
        progressBar.setVisibility(View.VISIBLE);
        progressBar.setIndeterminate(false);
        progressBar.setMax(disguisedFiles.size());
        progressBar.setProgress(0);

        new Thread(() -> {
            int success = 0, fail = 0;
            Set<String> reserved = new HashSet<>();
            // 收集目录中所有现有文件
            collectReserved(selectedDir, reserved);

            for (int i = 0; i < disguisedFiles.size(); i++) {
                File f = disguisedFiles.get(i);
                final int progress = i + 1;
                try {
                    reserved.remove(f.getCanonicalPath());
                    File restored = engine.revealFile(f, reserved);
                    reserved.add(restored.getCanonicalPath());
                    success++;
                    appendLog("[恢复] " + f.getName() + " -> " + restored.getName());
                } catch (Exception e) {
                    fail++;
                    appendLog("[失败] " + f.getName() + " -> " + e.getMessage());
                }
                final int s = success, fl = fail;
                runOnUiThread(() -> {
                    progressBar.setProgress(progress);
                    tvStatus.setText(String.format("恢复中: %d/%d  成功:%d 失败:%d",
                            progress, disguisedFiles.size(), s, fl));
                });
            }

            final int fs = success, ff = fail;
            runOnUiThread(() -> {
                progressBar.setVisibility(View.GONE);
                btnScan.setEnabled(true);
                tvStatus.setText(String.format("恢复完成: 成功 %d, 失败 %d", fs, ff));
                appendLog(String.format("\n恢复完成: 成功 %d, 失败 %d", fs, ff));
            });
        }).start();
    }

    private void collectReserved(File dir, Set<String> reserved) {
        File[] files = dir.listFiles();
        if (files == null) return;
        for (File f : files) {
            try {
                reserved.add(f.getCanonicalPath());
                if (f.isDirectory()) collectReserved(f, reserved);
            } catch (Exception ignored) {}
        }
    }

    // ===== 日志 =====

    private void appendLog(String msg) {
        String timestamp = new java.text.SimpleDateFormat("HH:mm:ss", Locale.getDefault())
                .format(new java.util.Date());
        runOnUiThread(() -> {
            tvLog.append("[" + timestamp + "] " + msg + "\n");
        });
    }
}
"""
