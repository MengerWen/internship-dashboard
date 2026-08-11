# Research Desk Visual Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将已批准的 B「研究编辑台」视觉方向完整落地到量化实习成果看板，同时保持现有功能与内容管线不变。

**Architecture:** 继续使用现有纯 HTML、CSS 与原生 JavaScript 架构。通过重构设计令牌和三个样式入口建立浅色出版物系统；仅在成果页脚本中增加由现有 manifest 数据生成的近期简报栏，不修改 Markdown 数据格式、路由协议或构建产物结构。

**Tech Stack:** HTML5、CSS Grid/Flexbox、原生 JavaScript、Python 静态构建、Playwright 浏览器验收。

---

### Task 1: 固化方向批准与基线

**Files:**
- Create: `direction-approved.md`
- Reference: `design-demos/direction-b-research-desk.html`
- Reference: `design-demos/screenshots/direction-b-research-desk.png`

**Steps:**
1. 记录三版原型和截图路径。
2. 原样记录用户选择「实施方案B，对当前项目进行修改」。
3. 确认实现前 gate 文件存在。

**Verification:** `Test-Path direction-approved.md` 返回 `True`。

### Task 2: 重构顶栏与全局设计系统

**Files:**
- Modify: `site/index.html`
- Modify: `site/css/tokens.css`
- Modify: `site/css/base.css`

**Steps:**
1. 将单层暗色顶栏改为刊头与主导航两层结构，保留所有既有 id。
2. 将颜色、边线、阴影、圆角和字体令牌改为暖纸色、深墨色、珊瑚红、青绿的编辑系统。
3. 重写 Markdown、按钮、搜索对话框、表格、代码、引用和提示块样式。
4. 更新 CSS 缓存版本为 `20260811`。

**Verification:** 页面初始化后 `#site-title`、两个主路由 tab 和搜索按钮均存在；桌面和手机无横向溢出。

### Task 3: 落地正式成果编辑台

**Files:**
- Modify: `site/js/showcase.js`
- Modify: `site/css/showcase.css`

**Steps:**
1. 保留阶段 stepper 和滚动吸附逻辑。
2. 为每个阶段增加由 `manifest.daily` 真实数据生成的近期简报栏。
3. 将阶段标题、正文与简报排成多栏出版物布局。
4. 为窄屏降级成顶部横向阶段条与单栏正文。

**Verification:** 点击阶段与上下箭头仍能更新 hash；简报点击进入对应日报；键盘翻页逻辑保持可用。

### Task 4: 统一日报、展示和内容增强样式

**Files:**
- Modify: `site/css/daily.css`
- Modify: `site/js/content-enhance.js`

**Steps:**
1. 将日报元信息、目录、正文和时间轴改成档案阅读器布局。
2. 保留文档/展示切换、全屏、下载、目录折叠和时间轴跳转。
3. 将动态注入的表格、Mermaid 和折叠控件颜色改为设计令牌，移除暗色硬编码。
4. 保持展示 iframe 内容隔离，不向定制展示版强制注入主站风格。

**Verification:** 日报文档与展示模式均可打开；目录折叠、下载链接和全屏按钮状态正常。

### Task 5: 测试、构建与视觉验收

**Files:**
- Generate: `dist/`
- Generate: `design-demos/screenshots/implemented-*.png`

**Steps:**
1. Run: `python -m pytest`
   - Expected: 全部测试通过。
2. Run: `python build.py`
   - Expected: 构建完成，无异常退出。
3. 用 Playwright 在 1440×900、900×900、390×844 检查成果页和日报页。
4. 测试成果阶段切换、日报路由、文档/展示切换、搜索对话框和控制台错误。
5. 肉眼检查最终截图；发现错位先修复再交付。

**Verification:** 无 `pageerror`；无横向溢出；关键交互全部通过；最终截图与 B 方向的出版物语法一致。
