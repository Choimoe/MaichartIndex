# 解析器 (Parser)

`simai_search.parser.SimaiParser` 是负责解析 Simai 格式（`maidata.txt`）的核心组件。

## 主要功能

### 1. 解析 Metadata (`parse_maidata`)

读取整个文件内容，提取元数据和谱面内容。

|提取字段|对应标签|说明|
|:---|:---|:---|
|元数据|`&title`|歌曲标题|
|元数据|`&artist`|艺术家|
|元数据|`&genre`|歌曲分类|
|谱面内容|`&inote_1` ~ `&inote_6`|各难度谱面文本|

### 2. 节奏提取 (`parse_chart_to_rhythm`)

这是搜索功能的核心。它将 Simai 谱面转换为标准化的时间事件序列。

#### 处理逻辑

*   **BPM**: 忽略 BPM 变化（因为节奏搜索通常基于相对网格，而非绝对秒数）。
*   **分辨率**: 处理 `{4}`, `{8}` 等分辨率标记，计算每个逗号（`,`）代表的时长。
*   **音符**: 识别所有类型的音符（Tap, Hold, Slide, Touch, Break）。
    *   **标准化**: 不区分音符类型，只记录“此处有音符”。
    *   **多押**: 同一时间点（`/` 分隔）的多个音符被合并为一个时间点事件。
*   **输出**: 返回一个 `List[Dict]`，包含：
    *   `time`: 节拍位置 (Float)
    *   `bpm`: 当前 BPM (Float)
    *   `is_star`: 是否为星星/Slide头 (Bool)

#### 示例

输入：

```
(150){4}1,2/3,{8}1,1*,
```

解析过程（简化）：

1.  BPM=150。分辨率=4。
2.  `1`: time=0.0, bpm=150, is_star=False。
3.  `2/3`: time=1.0, bpm=150, is_star=False。
4.  分辨率=8。
5.  `1`: time=2.0, bpm=150, is_star=False。
6.  `1*`: time=2.5, bpm=150, is_star=True (假设 * 为修饰符)。

结果为包含上述信息的列表。
