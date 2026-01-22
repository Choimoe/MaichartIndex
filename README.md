# MaichartIndex

MaichartIndex 是一个用于解析、索引和检索 Simai 格式谱面的工具集。它旨在帮助谱面创作者和玩家通过节奏型（Rhythm Pattern）快速查找相似的谱面段落，支持模糊匹配。

## 功能特性

*   **高效解析**: 内置 `SimaiParser`，能够处理 `maidata.txt` 格式，提取歌曲元数据及谱面详情。
*   **节奏标准化**: 将复杂的 Simai 语法（BPM 变化、多押、各类音符）转换为标准化的时间轴事件，专注于“节奏”而非具体的键位。
*   **模糊检索**: 可以在数据库中搜索特定的节奏型（如 `{16}1,1,1,1,1,`），支持通过时间容差进行模糊匹配。
*   **多维筛选**: 支持按难度等级（Level）、难度类型（Difficulty）、谱师（Designer）过滤搜索结果。
*   **SQL存储**: 使用 SQLite 存储索引数据，轻量且易于迁移。

## 快速开始

### 1. 安装
确保 Python 3.10+ 环境。

### 2. 构建索引
将你的 Simai 格式数据（`maidata.txt` 文件）放在 `data/Maichart-Converts` 目录下（或修改源码中的路径），然后运行：
```powershell
python main.py build
```

### 3. 搜索谱面
搜索一个 16 分音符的五连打节奏，筛选 Master 难度且等级大于 13.0 的谱面：
```powershell
python main.py search "{16}1,1,1,1,1,,1,1,1,,1,1,1," --diff Master --level-min 13.0
```

## 文档及模块
详细文档请参考 [Wiki/Docs](https://choimoe.github.io/MaichartIndex/) (构建后生成)。

*   **解析器 (Parser)**: 处理文本解析与节奏提取。
*   **数据库 (Database)**: 负责数据持久化与筛选查询。
*   **搜索核心 (Search)**: 实现模糊匹配算法。
