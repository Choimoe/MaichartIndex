# 从代码构建 (Build from Source)

如果您希望参与开发，或者在非 Windows 平台上运行，可以选择从源代码运行 MaichartIndex。

## 1. 环境准备

*   **Python**: 需要 Python 3.10 或更高版本。
*   **Git**:用于克隆代码仓库。

## 2. 获取代码

由于本项目包含子模块（Submodule）用于存储谱面数据，克隆时请务必包含子模块：

```powershell
git clone --recursive https://github.com/Choimoe/MaichartIndex.git
cd MaichartIndex
```

如果已经克隆但未下载子模块，请运行：
```powershell
git submodule update --init --recursive
```

安装依赖：
```powershell
pip install fastapi uvicorn
```

## 3. 构建索引数据库

在运行搜索之前，必须先解析原始数据文件并生成 SQLite 数据库文件 (`maichart.db`)。

```powershell
python main.py build
```
此过程可能需要几分钟，完成后会在根目录生成 `maichart.db`。

## 4. 运行工具

### 启动 Web 界面
```powershell
python main.py serve
```
访问 `http://localhost:8000`。

### 命令行搜索
```powershell
python main.py search "{8}1,1,1,"
```
