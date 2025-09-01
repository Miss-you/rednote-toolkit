# RedNote Toolkit - Claude 维护指南

## 项目概述

RedNote Toolkit 是一个基于 Python 和 Playwright 的小红书自动化发布工具，用于自动化发布包含文字、图片和话题的笔记内容。

## 技术栈

- **核心语言**: Python 3.8+
- **Web自动化**: Playwright
- **异步编程**: asyncio
- **数据模型**: dataclasses

## 项目架构

```
rednote-toolkit/
├── main.py                 # 主入口文件，演示如何使用客户端
├── requirements.txt        # 依赖管理（目前只有playwright）
├── storage_state.json      # 浏览器会话状态（自动生成）
├── rednote/               # 核心模块
│   ├── __init__.py        # 包初始化
│   ├── models.py          # 数据模型：RedNote, RedPublishResult
│   ├── browser.py         # 浏览器管理器：启动、登录、关闭
│   ├── client.py          # 主客户端：统一接口，整合所有功能
│   ├── uploader.py        # 文件上传器：处理图片/视频上传
│   ├── filler.py          # 内容填充器：标题、正文、话题填充
│   └── publisher.py       # 发布管理器：控制发布流程
└── CLAUDE.md              # 本文件
```

## 核心组件说明

### 1. RedNoteClient (`client.py`)
- **职责**: 主要的客户端接口，整合所有功能
- **关键方法**:
  - `publish_note(note, auto_publish=True)`: 发布笔记
  - 支持自动和手动发布模式

### 2. BrowserManager (`browser.py`)
- **职责**: 浏览器生命周期管理
- **功能**: 启动浏览器、处理登录、保存会话状态

### 3. Publisher (`publisher.py`)
- **职责**: 发布流程控制
- **功能**: 协调上传、填充、发布各个步骤

### 4. ContentFiller (`filler.py`)
- **职责**: 页面内容填充
- **功能**: 填充标题、正文、话题标签
- **注意**: 这是最容易因小红书界面更新而失效的模块

### 5. FileUploader (`uploader.py`)
- **职责**: 媒体文件上传
- **功能**: 处理图片和视频文件的上传

### 6. 数据模型 (`models.py`)
- `RedNote`: 笔记数据结构
- `RedPublishResult`: 发布结果数据结构

## 常见维护任务

### 1. 界面适配更新
**问题**: 小红书web版界面更新导致元素定位失败
**解决**: 主要更新 `filler.py` 中的CSS选择器和XPath

**关键定位器需要关注**:
- 发布按钮定位器
- 内容编辑区定位器  
- 话题输入框定位器
- 图片上传区定位器

### 2. 登录流程变更
**问题**: 登录页面或流程发生变化
**解决**: 更新 `browser.py` 中的登录相关逻辑

### 3. 上传功能失效
**问题**: 文件上传接口或流程变更
**解决**: 检查并更新 `uploader.py` 的上传逻辑

## 调试指南

### 1. 启用调试模式
在浏览器启动时添加 `headless=False` 可以看到浏览器操作过程：
```python
# 在 browser.py 中修改
browser = await self.playwright.chromium.launch(headless=False)
```

### 2. 添加等待和截图
```python
# 添加到关键步骤
await page.wait_for_timeout(2000)  # 等待2秒
await page.screenshot(path="debug.png")  # 截图调试
```

### 3. 常见错误排查
- **登录失败**: 检查 `storage_state.json` 是否存在且有效
- **元素定位失败**: 检查页面是否加载完成，定位器是否正确
- **上传失败**: 检查文件路径是否正确，文件是否存在

## 测试指南

### 基础测试流程
1. 删除 `storage_state.json` 测试首次登录
2. 准备测试图片文件
3. 运行 `python main.py` 进行端到端测试
4. 检查发布结果

### 测试环境准备
```bash
# 安装依赖
pip install -r requirements.txt
playwright install

# 准备测试文件
# 确保 main.py 中的图片路径指向真实存在的图片文件
```

## 版本更新维护

### 更新 CHANGELOG.md
- 记录界面适配更新
- 记录功能增强
- 记录bug修复

### 代码质量
- 保持模块间的低耦合
- 遵循现有的异步编程模式
- 保持错误处理的一致性

## 常用命令

```bash
# 运行主程序
python main.py

# 安装浏览器
playwright install

# 清除会话（重新登录）
rm storage_state.json
```

## 故障排除检查清单

- [ ] 检查依赖是否完整安装
- [ ] 检查 Playwright 浏览器是否正确安装
- [ ] 检查网络连接
- [ ] 检查小红书网站是否可正常访问
- [ ] 检查图片文件路径是否正确
- [ ] 检查会话文件是否损坏
- [ ] 检查页面元素定位器是否需要更新

## 注意事项

1. **频率控制**: 避免过于频繁的自动发布，可能触发反爬机制
2. **内容合规**: 确保发布内容符合小红书社区规范
3. **版本兼容**: 定期检查小红书web版更新，及时适配
4. **数据安全**: 妥善保管 `storage_state.json` 文件，包含登录凭证