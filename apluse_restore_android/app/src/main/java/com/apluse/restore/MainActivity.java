package com.apluse.restore;

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

    private static final String DEFAULT_MAGIC_HEX = "4a903513";

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

        selfNames = new HashSet<>(Arrays.asList("apluse_restore_4a903513.py", "apluse_restore_4a903513.exe"));

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
