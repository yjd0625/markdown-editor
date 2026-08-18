#!/usr/bin/env python3
# Markdown 编辑器 —— 单 exe 启动器
# 作用：把 index.html + vendor/ 通过本地 HTTP 服务起来，
#       优先用系统 WebView（pywebview / Edge WebView2）打开成原生窗口；
#       若目标机没装 WebView2 Runtime，则自动回退用默认浏览器打开（同样可用，绝不空白屏）。
import os
import sys
import base64
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


def resolve_base():
    """找到 index.html 与 vendor/ 所在目录。
    打包后资源在 sys._MEIPASS；开发时在本脚本的上级目录。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and os.path.exists(os.path.join(meipass, "index.html")):
        return meipass
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.dirname(here)  # packager/ -> 项目根
    if os.path.exists(os.path.join(candidate, "index.html")):
        return candidate
    return here


BASE = resolve_base()


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def log_message(self, *args, **kwargs):  # 静默访问日志
        pass


httpd = None


def start_server():
    global httpd
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return port


def shutdown():
    if httpd:
        try:
            httpd.shutdown()
        except Exception:
            pass


def has_webview2_runtime():
    r"""检测目标机是否安装了 Microsoft WebView2 Runtime。
    没装时我们不创建原生窗口，直接回退浏览器，避免空白屏。
    注意：WebView2 在不同安装方式下注册位置不同，需要多键兜底——
    例如本机常注册在 HKLM/HKCU 的 SOFTWARE\Microsoft\EdgeWebView，
    而独立安装包可能在 SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{GUID}。"""
    try:
        import winreg
    except Exception:
        return False
    key_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeWebView"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeWebView"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\EdgeWebView"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A08C11}"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeWebView\WebView2Runtime"),
    ]
    for root, k in key_paths:
        try:
            h = winreg.OpenKey(root, k)
            winreg.CloseKey(h)
            return True
        except OSError:
            pass
    # 文件系统兜底：运行时核心目录存在即认为可用
    for p in (
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\EdgeWebView\Application"),
        r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application",
    ):
        if os.path.isdir(p):
            return True
    return False


def maybe_use_bundled_runtime():
    """若把固定版 WebView2 运行时目录（webview2_runtime/）打进 exe，
    通过环境变量指给 pywebview，实现真正的零依赖原生窗口。当前无此目录时为 no-op。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        for cand in ("webview2_runtime", "WebView2Runtime"):
            p = os.path.join(meipass, cand)
            if os.path.isdir(p):
                os.environ["WEBVIEW2_BROWSER_EXECUTABLE_FOLDER"] = p
                return True
    return False


def open_in_browser(port):
    """回退方案：用默认浏览器打开编辑器，并弹一个 Windows 消息框保持进程、
    点『确定』即退出（ctypes 无需额外依赖，--windowed 也能用，不再卡死）。"""
    url = "http://127.0.0.1:%d/index.html" % port
    webbrowser.open(url)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "已在你的默认浏览器中打开 Markdown 编辑器。\n点击「确定」即可退出程序。\n\n"
            "（安装 Microsoft WebView2 Runtime 可获得独立原生窗口体验）",
            "Markdown 编辑器",
            0,  # MB_OK
        )
    except Exception:
        try:
            input("已在浏览器打开。按 Enter 退出…")
        except EOFError:
            import time
            while True:
                time.sleep(3600)
    finally:
        shutdown()


import webview  # 模块级导入：保证 Bridge 的各个方法内能直接引用 webview.*
              # （此前只在 _win() 内局部 import，导致 open_file/save_file/save_file_as
              #  在方法作用域里找不到 webview 名称，打包后报 NameError）

class Bridge:
    """暴露给前端(JS)的原生文件读写桥接。
    用系统文件对话框 + Python 直接写盘，使 exe 内的『打开/保存/另存为』是真正的桌面行为，
    不依赖浏览器的 File System Access API（file:// / WebView2 下可能不可用）。"""
    # 注意：pywebview 要求 file_types 是「字符串」元组，格式 '描述 (*.ext;*.ext)'，
    # 不是 (描述, 模式) 的二元组——后者会在 window.create_file_dialog 内部的
    # parse_file_type() 里触发 re.search(tuple)，报
    # "expected string or bytes-like object, got 'tuple'"。
    FILE_TYPES = ("Markdown 文件 (*.md;*.markdown;*.txt)", "所有文件 (*.*)")

    def _win(self):
        return webview.windows[0]

    @staticmethod
    def _dialog_path(res):
        """pywebview 6.x 的 create_file_dialog 一律返回「选中文件元组」（即便单选/SAVE 也是
        1 元组），取消时返回 None。这里统一归一化成单条字符串路径，避免把 tuple 直接喂给
        open() 触发 'expected str, bytes or os.PathLike object, not tuple'。"""
        if not res:
            return None
        if isinstance(res, (list, tuple)):
            return res[0] if res else None
        return res

    def open_file(self):
        try:
            res = self._win().create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=self.FILE_TYPES)
        except Exception as e:
            return {"error": str(e)}
        path = self._dialog_path(res)
        if not path:
            return None
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return {"error": str(e)}
        return {"path": path, "name": os.path.basename(path), "content": content}

    def save_file(self, path, content):
        if not path:
            try:
                res = self._win().create_file_dialog(webview.SAVE_DIALOG, file_types=self.FILE_TYPES, save_filename="未命名.md")
            except Exception as e:
                return {"error": str(e)}
            path = self._dialog_path(res)
            if not path:
                return None
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        except Exception as e:
            return {"error": str(e)}
        return {"path": path, "name": os.path.basename(path)}

    def save_file_as(self, content, suggested):
        try:
            res = self._win().create_file_dialog(webview.SAVE_DIALOG, file_types=self.FILE_TYPES, save_filename=suggested or "未命名.md")
        except Exception as e:
            return {"error": str(e)}
        path = self._dialog_path(res)
        if not path:
            return None
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        except Exception as e:
            return {"error": str(e)}
        return {"path": path, "name": os.path.basename(path)}

    _IMG_MIME = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
        ".svg": "image/svg+xml",
    }

    @staticmethod
    def _safe_join(base_dir, rel_path):
        """把相对路径合成绝对路径并校验仍在 base_dir 之内（防目录穿越）。"""
        abs_path = os.path.normpath(os.path.join(base_dir, rel_path))
        base_abs = os.path.normpath(base_dir)
        if abs_path != base_abs and not abs_path.startswith(base_abs + os.sep):
            return None
        return abs_path

    def save_image(self, dir_path, rel_path, b64):
        """方案 B（侧车文件）：把图片(base64)写入 .md 同目录的 rel_path（如 images/foo.png）。
        仅允许写在 dir_path 之内，防目录穿越。返回 {'ok': True, 'path': abs} 或 {'error': ...}。"""
        try:
            if not dir_path or not os.path.isdir(dir_path):
                return {"error": "文档目录不存在"}
            abs_path = self._safe_join(dir_path, rel_path)
            if not abs_path:
                return {"error": "非法路径（超出文档目录）"}
            parent = os.path.dirname(abs_path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            with open(abs_path, "wb") as f:
                f.write(base64.b64decode(b64))
            return {"ok": True, "path": abs_path}
        except Exception as e:
            return {"error": str(e)}

    def read_image(self, base_dir, rel_path):
        """预览用：读取 .md 同目录内的相对图片，返回 data URL（仅供预览，不改写 .md 源码）。
        仅允许读取 base_dir 之内，防目录穿越。返回 {'ok': True, 'data': 'data:...'} 或 {'error': ...}。"""
        try:
            if not base_dir or not os.path.isdir(base_dir):
                return {"error": "文档目录不存在"}
            abs_path = self._safe_join(base_dir, rel_path)
            if not abs_path or not os.path.isfile(abs_path):
                return {"error": "文件不存在"}
            ext = os.path.splitext(abs_path)[1].lower()
            mime = self._IMG_MIME.get(ext, "application/octet-stream")
            with open(abs_path, "rb") as f:
                data = f.read()
            return {"ok": True, "data": "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))}
        except Exception as e:
            return {"error": str(e)}


def main():
    port = start_server()
    if has_webview2_runtime() or maybe_use_bundled_runtime():
        try:
            import webview  # 原生窗口（Edge WebView2）
            webview.create_window(
                "Markdown 编辑器",
                "http://127.0.0.1:%d/index.html" % port,
                width=1200,
                height=800,
                min_size=(820, 600),
                js_api=Bridge(),
            )
            webview.start()
            shutdown()
            return
        except Exception as e:
            sys.stderr.write("WebView 启动失败，回退到默认浏览器：%s\n" % e)
            # 落到浏览器回退（不再残留空白原生窗口）
    open_in_browser(port)


if __name__ == "__main__":
    main()
