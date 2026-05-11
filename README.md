# Before Initialization

1. Find the USB locator by `smarpod.FindSystems()`.
2. Define the right model code. For example, model code is 10001. You need to configure controller by `smarpod.ConfigureController(10001, locator)`.
3. Initialization by `smarpod.Open(10001, locator)`.

## `demo.py`（螺旋 mosaic + 仅发图）

`demo.py` 在 XY 平面上按与 `client.py` mosaic 模式相同的螺旋公式扫描（`i * cos(iπ)` / `i * sin(iπ)`，缩放 `1e-4`），逐点移动 SmarPod、截屏采图，并把图像按与 `client.py` 相同的协议发给 server（`pickle` 载荷 + 4 字节大端长度前缀；图像为 JPEG，`signal` 置 `1`）。

**重要：** server 返回的数据包会被读取（避免阻塞 socket），但**不会用于更新机器人位姿或视觉伺服**；运动完全由本地螺旋轨迹决定。

### 运行前

- 在 `demo.py` 顶部设置 `HOST`、`PORT` 与 AGX/server 一致。
- 使用本机已配置的 Python 环境（例如 `pCLE_diffusion` conda 环境），并确保已安装 `opencv-python`、`numpy`、`mss` 及 SmarPod Python API。

### 运行

```bash
python demo.py
```

### 输出

运行会在当前目录生成 `mosaic_demo_<时间戳>/images/`，保存每步的大图与小图（`img_*.png`、`frame_*.png`）。
