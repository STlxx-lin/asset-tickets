# 工单管理系统打包说明

本文档说明如何将工单管理系统打包为单个可执行文件，支持 Windows 和 macOS 平台。

## 系统要求

- Python 3.8+
- pip 包管理器

## 快速开始

### 自动打包（推荐）

运行自动打包脚本：

```bash
python build_script.py
```

脚本会自动：
1. 安装所需依赖
2. 根据当前平台选择合适的打包配置
3. 生成单个可执行文件

### 手动打包

#### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install pyinstaller
```

#### 2. Windows 平台打包

```bash
python -m PyInstaller 工单管理系统.spec
```

生成文件：`dist/工单管理系统.exe`

#### 3. macOS 平台打包

```bash
python -m PyInstaller 工单管理系统_mac.spec
```

生成文件：`dist/工单管理系统_mac`

## 打包配置文件说明

- `工单管理系统.spec`: Windows 版本配置，生成 .exe 文件
- `工单管理系统_mac.spec`: macOS 版本配置，生成单个可执行文件

## 输出文件

打包完成后，可执行文件将生成在 `dist/` 目录下：

- **Windows**: `工单管理系统.exe` (~45MB)
- **macOS**: `工单管理系统_mac` (~30MB)

## 注意事项

1. **跨平台打包**: 需要在对应的操作系统上进行打包
   - Windows 可执行文件需要在 Windows 系统上打包
   - macOS 可执行文件需要在 macOS 系统上打包

2. **依赖管理**: 确保所有依赖都在 `requirements.txt` 中列出

3. **文件大小**: 单文件打包会包含所有依赖，文件较大但便于分发

4. **权限设置**: macOS 版本可能需要设置执行权限：
   ```bash
   chmod +x dist/工单管理系统_mac
   ```

## 故障排除

### 常见问题

1. **模块缺失错误**: 检查 `requirements.txt` 是否包含所有依赖
2. **打包失败**: 确保 PyInstaller 版本兼容
3. **运行时错误**: 检查路径和资源文件是否正确包含

### 调试模式

如需调试，可以修改 spec 文件中的 `debug=True` 和 `console=True`。

## 更新依赖

当添加新的 Python 包时，记得更新 `requirements.txt`：

```bash
pip freeze > requirements.txt
```

## 技术支持

如遇到打包问题，请检查：
1. Python 版本兼容性
2. 依赖包版本
3. PyInstaller 版本
4. 操作系统兼容性