# 使用指南 (CLI)

项目提供了 `main.py` 作为命令行入口。

## 构建索引 (Build)

扫描 `data/` 目录并重建数据库。建议在添加新谱面后运行。

```powershell
python main.py build
```

## 搜索 (Search)

### 基本用法

```powershell
python main.py search "QUERY_STRING" [FILTERS]
```

### 参数说明

| 参数 | 必选 | 类型 | 说明 | 示例 |
| :--- | :--- | :--- | :--- | :--- |
| `query` | 是 | `str` | Simai 格式的节奏串。 | `{16}1,1,1,1,` |
| `--diff` | 否 | `List[str]` | 难度名，支持多个。 | `--diff Master ReMaster` |
| `--level-min` | 否 | `float` | 最低等级。 | `--level-min 13.0` |
| `--level-max` | 否 | `float` | 最高等级。 | `--level-max 14.5` |
| `--designer` | 否 | `str` | 谱师名称 (模糊匹配)。 | `--designer "DX"` |
| `--bpm-min` | 否 | `float` | 匹配段落的最低 BPM。 | `--bpm-min 180` |
| `--bpm-max` | 否 | `float` | 匹配段落的最高 BPM。 | `--bpm-max 200` |

### 完整示例

查找 BPM 在 190~200 之间，且包含星星头（Slide）的 16 分音符段落：

```powershell
python main.py search "{8}1*,1,1," --bpm-min 190 --bpm-max 200
```
