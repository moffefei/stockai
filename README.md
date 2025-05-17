# stockai
## 项目简介
stockai 是一个基于 Flask 和 akshare 的中国A股股票数据看板应用。该项目可用于查询A股股票的实时行情、历史K线（日K）数据，并提供可视化展示。适合股票数据学习、展示和简单分析。

## 功能特性
- 支持按股票代码（如 600519）或名称（如 贵州茅台）检索A股股票。
- 实时获取所选股票最新价格、涨跌幅、成交量、开盘价、最高/最低价等信息。
- 展示所选股票的日K线图，支持近三年的历史数据。
- 前端使用 ECharts 图表库进行可视化，界面美观简洁。
- 提供手动刷新实时数据按钮。
### 技术栈
- Python 3
- Flask
- akshare
- pandas
- ECharts（前端）
### 安装与运行
- 克隆本仓库：

```bash
git clone https://github.com/moffefei/stockai.git
cd stockai
```

- 安装依赖：
```bash
pip install flask akshare pandas
```
- 启动服务：

```bash
python stock_dashboard.py
```
在浏览器中访问：http://127.0.0.1:5001
### 使用说明
- 在输入框输入6位A股股票代码或公司名称，点击“检索”。
- 页面将显示该股票的基本信息、实时行情和日K线图。
- 可点击“手动刷新”按钮获取最新实时数据。
### 主要文件说明
stock_dashboard.py：主程序文件，包含Flask服务、API接口和前端页面模板。
README.md：项目说明文档。
依赖说明
Flask：Web服务框架
akshare：财经数据接口
pandas：数据处理
ECharts：前端可视化（通过CDN引入）
注意事项
需要科学上网以保证 akshare 能够顺利获取数据。
akshare 可能会因数据源变动导致部分接口不可用，遇到问题请及时更新 akshare。
### 许可证
- MIT License
