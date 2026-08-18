# Markdown 编辑器 · 单 exe 封装

把 `index.html`（含 `vendor/`）打包成一个独立 `MarkdownEditor.exe`，双击即用，方便分发。

## 原理
- 启动器 `app.py` 在本地 `127.0.0.1` 随机端口起一个静态 HTTP 服务，托管 `index.html` 与 `vendor/`。
- 用系统 WebView 窗口（pywebview / Edge WebView2）打开该地址，形成"原生窗口"体验。
- 目标机没有 pywebview 时自动回退到默认浏览器打开（同样可用）。
- 用 PyInstaller 把 `app.py` + 资源打成一个 `--onefile` exe；运行时资源自动释放到临时目录。

## 依赖（打包机需要）
- Python 3.10+
- `pip install pyinstaller pywebview`
- 目标用户机：Win10/11 自带 Edge WebView2 运行时（无需额外安装）。

## 打包
在 `packager/` 目录下执行：
```
python build.py
```
产物：`packager/dist/MarkdownEditor.exe`（单文件）。

## 分发
直接把 `MarkdownEditor.exe` 发给别人即可。对方双击运行，无需安装 Python、无需 `vendor/` 文件夹。

## 说明
- 首次运行若被 Windows Defender 拦截，点"仍要运行"即可（PyInstaller 打包的程序偶尔触发误报）。
- 编辑器所有数据仍保存在浏览器/WebView 的 localStorage（按用户配置隔离），换机器不携带文档，需要时请用"保存 .md"或"导出 HTML"备份。
