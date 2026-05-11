# 📈 Wyckoff Point & Figure Chart

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Mac%20%7C%20Linux-lightgrey.svg)

一个基于**威科夫方法**(Wyckoff Method)开发的**点数图**(Point & Figure Chart)分析工具，帮助投资者识别市场趋势和交易机会。

</div>

## ✨ 特性

| 功能 | 描述 |
|------|------|
| 📊 **专业图表** | 绘制标准的P&F图表，支持X/O列显示 |
| ⚙️ **参数灵活** | 自定义Box Size和Reversal参数 |
| 📁 **多格式支持** | 支持CSV和Parquet数据导入 |
| 🖱️ **交互操作** | 支持缩放、平移、框选等交互 |
| 📈 **趋势分析** | 识别上涨/下跌趋势，辅助交易决策 |

## 🖥️ 界面预览

```
┌─────────────────────────────────────────────────────────┐
│  Wyckoff Point & Figure Chart v0.2                      │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  控制面板     │           P&F 图表区域                   │
│              │                                          │
│  • 数据导入   │     X   X   X                          │
│  • 参数配置   │     X   X   X   O                      │
│  • 计算绘制   │     X   X   O   O   O                  │
│              │           O   O   O                      │
│              │                                          │
└──────────────┴──────────────────────────────────────────┘
```

## 🛠️ 技术栈

- **PyQt5** - 跨平台GUI框架
- **pyqtgraph** - 高性能图表库
- **pandas** - 数据处理与分析
- **numpy** - 数值计算

## 📦 安装

### 1. 克隆项目

```bash
git clone https://github.com/zhulimeng-ai/wyckoof-pf.git
cd wyckoof-pf
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行程序

```bash
python main.py
```

## 📖 使用指南

### 步骤 1: 导入数据
点击「导入CSV/Parquet」按钮，选择包含价格数据的文件。

### 步骤 2: 选择数据列
从下拉菜单中选择要分析的数值列（如Close收盘价）。

### 步骤 3: 设置参数
- **Box Size**: 箱子大小（固定值或百分比）
- **Reversal**: 反转所需格子数（通常为3格）

### 步骤 4: 查看图表
点击「计算并绘制」，查看P&F图表分析结果。

## 📊 数据格式要求

| 列名 | 类型 | 说明 |
|------|------|------|
| 日期列 | Datetime | 日期时间（Date/Timestamp/Datetime） |
| 数值列 | Number | 价格数据（Close/Price/High/Low） |

支持的格式：
- **CSV** - 通用数据交换格式
- **Parquet** - 高效列式存储格式

## 🧮 P&F核心概念

```
📦 Box (箱子): 价格变动的最小单位

🔄 Reversal (反转): 
   - 当价格向相反方向变动达到一定格子数时
   - 产生新的列（从X转O，或从O转X）
   - 通常设置为3格

📈 X列: 表示上涨趋势
📉 O列: 表示下跌趋势
```

## 📁 项目结构

```
wyckoof-pf/
├── main.py                 # 程序入口
├── src/
│   ├── pf_engine.py       # P&F核心算法
│   └── ui/
│       ├── main_window.py  # 主窗口
│       └── pf_chart.py    # 图表组件
├── resmcom/               # 数据预处理脚本
├── data/                  # 数据目录
└── requirements.txt       # 依赖列表
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 了解详情。

---

<div align="center">

⭐ 如果这个项目对你有帮助，欢迎Star支持！

</div>
