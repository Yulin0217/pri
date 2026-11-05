# SmarPod SDK 安装说明与迁移指南

> 整理日期：2026-11-05　　来源电脑：本机（用户 renji）

## 1. 本机安装情况

本机 **没有** 通过 SmarAct 官方安装程序安装 SDK（"程序和功能"中无 SmarAct 条目，也没有相关环境变量），
而是采用 **手动拷贝 DLL + pip 安装 Python 包** 的方式，装在 conda 环境 `robot` 中。

| 组成 | 位置 | 说明 |
|---|---|---|
| Python 接口 `smaract.smarpod` 1.9.0 | `C:\Users\renji\anaconda3\envs\robot\Lib\site-packages\smaract\` | 由本地 zip 用 pip 安装（原路径 `Desktop\pCLE_robot_integration\SDK\...`，已不存在） |
| 安装包备份 | `C:\Users\renji\Desktop\pri\SDK\Python\packages\smaract.smarpod-1.9.0.zip` | 仅 9 KB，只含 Python 封装，**不含 DLL** |
| 底层 DLL（64 位） | `C:\Users\renji\anaconda3\envs\robot\Library\bin\` | 见下表 |
| FTDI USB 驱动 | `C:\Windows\System32\ftd2xx.dll`（2.12.36）+ ftdibus / ftdiport 驱动 | USB 连接控制器所需 |
| Python | 3.7.16（64 位），依赖 `cffi` | |
| VC++ 运行库 | MSVCP140 / VCRUNTIME140 / VCRUNTIME140_1 | Visual C++ 2015-2022 x64 |

### 必需的 DLL（均在 `envs\robot\Library\bin\`）

| 文件 | 版本 | 依赖 |
|---|---|---|
| `SmarPod.dll` | 1.9.7 | MCSControl.dll |
| `MCSControl.dll` | 3.0.33 | SmarActCTL.dll, SmarActIO.dll |
| `SmarActCTL.dll` | 1.3.19 | SmarActIO.dll |
| `SmarActIO.dll` | 2.3.3 | ftd2xx.dll, FTChipID.dll |
| `FTChipID.dll` | — | FTDI 辅助库 |

调用链：`Python (smaract.smarpod) → SmarPod.dll → MCSControl.dll → SmarActCTL.dll / SmarActIO.dll → ftd2xx.dll (FTDI 驱动)`

Python 包通过 `ffi.dlopen("SmarPod.dll")` 按文件名加载 DLL，因此 DLL 只要位于搜索路径（PATH 或当前目录）即可。
conda 环境的 `Library\bin` 会自动加入 PATH，所以放在那里能正常工作。

## 2. 迁移到其他电脑

可以迁移。步骤如下：

1. **安装 VC++ 运行库**：Microsoft Visual C++ 2015-2022 Redistributable (x64)。
2. **安装 FTDI D2XX 驱动**：从 https://ftdichip.com 下载，或插上控制器后让 Windows 自动安装。（若仅用网口连接控制器可跳过。）
3. **创建 Python 环境**（必须是 64 位 Python）：
   ```
   conda create -n robot python=3.7
   conda activate robot
   pip install cffi
   pip install smaract.smarpod-1.9.0.zip
   ```
4. **拷贝 5 个 DLL**：`SmarPod.dll`、`MCSControl.dll`、`SmarActCTL.dll`、`SmarActIO.dll`、`FTChipID.dll`
   → 新环境的 `<anaconda>\envs\robot\Library\bin\`（或脚本所在目录 / 任意 PATH 目录）。
5. **验证**：
   ```python
   import smaract.smarpod as sp
   print(sp.GetDLLVersion())
   print(sp.FindSystems())   # 连接控制器后应能列出设备
   ```

> 也可以整体复制 `envs\robot` 文件夹，但 conda 环境含有硬编码路径，仅在新电脑用户名 / 路径完全一致时较稳妥，不推荐。

## 3. 注意事项

- **备份**：桌面上的 zip 不含 DLL，目前 DLL 只存在于 conda 环境中。建议把上述 5 个 DLL 与 zip 放在同一个 SDK 文件夹中备份。
- **授权**：包的许可证为 "SmarAct EULA"，实验室内部同一设备使用一般没问题，对外分发前请查看条款。
- **版本**：pip 缓存中还有 `smaract.smarpod-1.9.18` 的 wheel，说明曾安装过更新版本。最稳妥的方式是向 SmarAct 索取官方 SDK 安装包（MCS / SmarPod SDK）在新电脑上正式安装。
- **位数一致**：DLL 为 x64，Python 必须是 64 位，否则加载失败。
