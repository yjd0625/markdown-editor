#!/usr/bin/env python3
# 用 PyInstaller 把 app.py 打包成单文件 exe（MarkdownEditor.exe）
# 资源（index.html + vendor/）会一起打进 exe，运行时自动释放到临时目录并本地托管。
import os
import PyInstaller.__main__  # type: ignore

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app.py")
HTML = os.path.join(HERE, "..", "index.html")
VENDOR = os.path.join(HERE, "..", "vendor")

PyInstaller.__main__.run([
    APP,
    "--onefile",
    "--windowed",
    "--name", "MarkdownEditor",
    # 注： deliberately 不加 --clean。本机 Python 的 sitecustomize 垫片把所有 os.remove 强制走回收站，
    # 而回收站不可用会抛 OSError 中断打包；去掉 --clean 可避免构建末尾的清理 os.remove。
    # 若需彻底清理，请手动删除 packager/build 与 dist 旧 exe 后再构建。
    "--add-data", os.path.join(HTML) + os.pathsep + ".",
    "--add-data", os.path.join(VENDOR) + os.pathsep + "vendor",
    # 必须把 webview 的全部子模块（尤其 webview.platforms.edgechromium）打进去，
    # 否则运行时动态 import 会失败、原生窗口起不来，被回退逻辑变成"开浏览器"。
    # 注意：千万不要用 --exclude-module webview.platforms.*，那会把整个
    # webview.platforms 包（连同 edgechromium）一起剔掉。
    "--hidden-import", "webview",
    "--hidden-import", "webview.platforms.edgechromium",
    "--collect-submodules", "webview",
    # 浏览器回退改用 ctypes 消息框，不再需要 tkinter（tkinter 是顶层模块，不受上面影响）
    "--exclude-module", "tkinter",
    "--noconfirm",
])
