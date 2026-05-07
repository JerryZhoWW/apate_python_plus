import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui import MainWindow

# 引入核心中新定义的全局路径管理器
from core import PathManager

# =================== 核心机制 2：程序基础自校验 ===================
def self_check():
    """
    基础的程序自检与环境校验。
    防止程序被逆向人员使用调试器（如 PySnooper, PDB 等）动态调试分析。
    """
    if sys.gettrace() is not None:
        ctypes.windll.user32.MessageBoxW(0, "安全自检未通过：检测到非法调试环境！\n程序即将退出。", "安全拦截", 0x10)
        sys.exit(1)

# =================== 主程序入口 ===================
if __name__ == "__main__":
    # 1. 启动前先执行自检
    self_check()
    
    # 2. 初始化应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 3. 设置全局应用图标 (包括窗口左上角和 Windows 任务栏)
    # 【修改】：使用 PathManager.get_resource_dir() 精准寻找 Nuitka/PyInstaller 的资源解压目录
    icon_path = os.path.join(PathManager.get_resource_dir(), 'icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    # 4. 加载并显示主窗口
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())