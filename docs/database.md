# 数据库 (Database)

`simai_search.db.SimaiDB` 封装了 SQLite 操作，负责数据的存储和检索。

## Schema 设计

### Songs 表

存储歌曲级别的元数据。

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INTEGER PRIMARY KEY | 自增主键 |
| `title` | TEXT | 标题 |
| `artist` | TEXT | 艺术家 |
| `genre` | TEXT | 分类 |
| `path` | TEXT | 原始文件路径 (用于去重) |

### Charts 表

存储具体的谱面数据。

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INTEGER PRIMARY KEY | 自增主键 |
| `song_id` | INTEGER | 外键关联 Songs |
| `difficulty` | INTEGER | 难度 ID (1=Easy, ..., 6=ReMaster) |
| `level` | TEXT | 等级字符串 (如 "13+") |
| `designer` | TEXT | 谱师 |
| `raw_content` | TEXT | 原始 Simai 文本 (用于展示) |
| `note_data` | TEXT (JSON) | 节奏事件列表 (用于搜索) |

## 筛选接口 (`get_charts`)

支持多维度筛选：

| 参数名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `level_min` | `float` | 最低等级。通过 `CAST(level AS REAL)` 比较。 |
| `level_max` | `float` | 最高等级。 |
| `difficulties` | `List[int]` | 难度 ID 列表。 |
| `designer` | `str` | 谱师名称 (SQL `LIKE` 模糊匹配)。 |
