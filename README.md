# RedNote Toolkit

一个使用 Python 和 Playwright 实现的、用于自动化发布小红书笔记的工具。

## 核心功能

- **自动登录与会话保持**: 首次运行通过扫描二维码登录，后续可自动保持登录状态，无需重复扫码。
- **内容发布自动化**: 支持自动化发布包含标题、正文、图片以及话题的完整笔记。
- **健壮的交互逻辑**: 采用先进的定位器策略和等待机制，确保在复杂的页面结构下也能稳定运行。
- **模块化设计**: 将浏览器管理、内容填充、文件上传和发布流程解耦，易于维护和扩展。

## 环境准备

在开始之前，请确保您的电脑上已经安装了以下软件：

- [Python 3.8+](https://www.python.org/downloads/)
- [pip](https://pip.pypa.io/en/stable/installation/) (通常随 Python 一起安装)

## 安装步骤

1.  **克隆项目**
    ```bash
    git clone <your-repository-url>
    cd rednote-toolkit
    ```

2.  **安装依赖**
    项目所需的 Python 包已在 `requirements.txt` 中列出。运行以下命令进行安装：
    ```bash
    pip install -r requirements.txt
    ```

3.  **安装 Playwright 浏览器**
    Playwright 需要下载相���的浏览器核心才能工作。运行以下命令会自动安装：
    ```bash
    playwright install
    ```

## 使用方法

1.  **配置笔记内容**
    打开 `main.py` 文件，根据您的需求修改 `RedNote` 对象中的内容：
    ```python
    note = RedNote(
        title="这里是你的笔记标题",
        content="这里是你的正文内容...",
        # 重要：请确保图片路径是正确的，建议使用绝对路径
        images=["/path/to/your/image.jpeg"], 
        topics=["你的话题1", "你的话题2"]
    )
    ```

2.  **运行脚本**
    在项目根目录下，执行以下命令：
    ```bash
    python main.py
    ```

3.  **首次登录**
    - 脚本首次运行时，会自动打开一个浏览器窗口并导航到小红书的登录页面。
    - 请使用手机上的小红书 App **扫描屏幕上显示的二维码**以完成登录。
    - 登录成功后，脚本会自动保存您的会话信息到 `storage_state.json` 文件中。在后续运行中，脚本将自动加载此文件，跳过登录步骤。

## 项目结构

```
.
├── main.py                 # 项目主入口
├── requirements.txt        # Python 依赖列表
├── storage_state.json      # (自动生成) 存储登录会话
├── rednote/
│   ├── browser.py          # 浏览器管理 (启动, 关闭, 登录逻辑)
│   ├── client.py           # 封装所有操作的主客户端
│   ├── filler.py           # 内容填充器 (标题, 正文, 话题)
│   ├── models.py           # 数据模型 (RedNote, RedPublishResult)
│   ├── publisher.py        # 发布流程管理器
│   └── uploader.py         # 文件上传器
└── README.md               # 项目说明文档
```
