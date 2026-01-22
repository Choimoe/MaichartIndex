# MaichartIndex

MaichartIndex 是一个用于解析、索引和检索 Simai 格式谱面的工具集。它旨在帮助谱面创作者和玩家通过节奏型（Rhythm Pattern）快速查找相似的谱面段落，支持模糊匹配。

## 功能特性

*   **高效解析**: 内置 `SimaiParser`，能够处理 `maidata.txt` 格式，提取歌曲元数据及谱面详情。
*   **节奏标准化**: 将复杂的 Simai 语法（BPM 变化、多押、各类音符）转换为标准化的时间轴事件，专注于“节奏”而非具体的键位。
*   **模糊检索**: 可以在数据库中搜索特定的节奏型（如 `{16}1,1,1,1,1,`），支持通过时间容差进行模糊匹配。
*   **多维筛选**: 支持按难度等级（Level）、难度类型（Difficulty）、谱师（Designer）过滤搜索结果。
*   **SQL存储**: 使用 SQLite 存储索引数据，轻量且易于迁移。

具体内容可以参考 [项目文档](https://choimoe.github.io/MaichartIndex/)。

## 快速开始 (使用 Release 版本)

推荐普通用户直接下载编译好的可执行文件，无需安装 Python 环境。

### 1. 下载
前往 [Releases 页面](https://github.com/Choimoe/MaichartIndex/releases) 下载最新版本的附件：
*   **MaichartIndex-Tools-vX.X.zip** (包含 `maichart-webui.exe` 和 `maichart-cli.exe`)
*   **MaichartIndex-Database-vX.X.zip** (包含 `maichart.db`)

### 2. 安装
1.  解压 `MaichartIndex-Tools` 压缩包到任意文件夹。
2.  解压 `MaichartIndex-Database` 中的 `maichart.db` 文件，将其放到工具所在的**同一级目录**。

### 3. 运行 Web 界面
双击运行 `maichart-webui.exe`。
程序启动后（控制台显示 "Uvicorn running..."），打开浏览器访问 `http://localhost:8000` 即可使用。

### 4. 运行命令行工具
在文件夹中打开终端（PowerShell 或 CMD），运行：
```powershell
.\maichart-cli.exe search "{8}1,1,1,"
```

---

## 开发者与高阶使用

如果您希望从源代码构建，或在 Linux/macOS 环境下运行，请参阅文档中的 [从代码构建](https://choimoe.github.io/MaichartIndex/build/) 章节。
