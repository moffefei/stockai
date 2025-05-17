from flask import Flask, render_template_string, request, jsonify
import akshare as ak
import pandas as pd
import json
from datetime import datetime

app = Flask(__name__)

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>股票数据看板 (A股)</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.3.2/dist/echarts.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 1000px; margin: auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #333; text-align: center; }
        .section { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9;}
        input[type="text"] { padding: 10px; margin-right: 10px; border: 1px solid #ccc; border-radius: 4px; width: calc(100% - 120px); box-sizing: border-box; }
        button { padding: 10px 15px; background-color: #5cb85c; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #4cae4c; }
        #stockInfo, .realtime-info p { margin: 5px 0; }
        #klineChart { width: 100%; height: 450px; margin-top:15px;}
        .error { color: red; font-weight: bold; margin-top: 5px; }
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 10px; }
        .info-item { background-color: #e9ecef; padding: 10px; border-radius: 4px; }
        .info-item strong { display: block; margin-bottom: 5px; color: #495057; }
        .refresh-button-container { text-align: right; margin-top: 10px; } /* 新增样式 */
    </style>
</head>
<body>
    <div class="container">
        <h1>股票数据看板 (中国A股)</h1>

        <div class="section">
            <h2>股票检索</h2>
            <input type="text" id="stockQuery" placeholder="输入6位股票代码 (例如: 600519) 或 名称 (例如: 贵州茅台)">
            <button onclick="searchStock()">检索</button>
            <div id="searchError" class="error"></div>
            <div id="stockInfo" class="info-grid" style="margin-top:15px;"></div>
        </div>

        <div class="section realtime-info">
            <h2>实时数据: <span id="currentStockNameDisplay">--</span> (<span id="currentStockCodeDisplay">--</span>)</h2>
            <div id="realtimeError" class="error"></div>
            <div class="info-grid">
                <div class="info-item"><strong>价格:</strong> <span id="stockPrice">--</span></div>
                <div class="info-item"><strong>涨跌额:</strong> <span id="stockChangeAmount">--</span></div>
                <div class="info-item"><strong>涨跌幅:</strong> <span id="stockChangePercent">--</span>%</div>
                <div class="info-item"><strong>成交量 (手):</strong> <span id="stockVolume">--</span></div>
                <div class="info-item"><strong>成交额 (元):</strong> <span id="stockTurnover">--</span></div>
                <div class="info-item"><strong>今开:</strong> <span id="stockOpen">--</span></div>
                <div class="info-item"><strong>昨收:</strong> <span id="stockPrevClose">--</span></div>
                <div class="info-item"><strong>最高:</strong> <span id="stockHigh">--</span></div>
                <div class="info-item"><strong>最低:</strong> <span id="stockLow">--</span></div>
            </div>
            <!-- 手动刷新按钮 -->
            <div class="refresh-button-container">
                 <button onclick="manualRefreshData()" id="manualRefreshBtn" style="background-color: #007bff;">手动刷新</button>
            </div>
            <p style="text-align:right; font-size:0.9em; color:#666;">最后更新: <span id="lastUpdated">--</span></p>
        </div>

        <div class="section">
            <h2>日K线图</h2>
            <div id="klineError" class="error"></div>
            <div id="klineChartContainer" style="width: 100%; height: 450px;">
                 <div id="klineChart" style="width: 100%; height: 100%;"></div>
            </div>
        </div>
    </div>

    <script>
        let currentStockCode = null;
        // let realtimeIntervalId = null; // 移除定时器ID变量
        let klineChartInstance = null;

        function displayError(elementId, message) {
            const el = document.getElementById(elementId);
            if (el) el.innerText = message;
        }
        function clearError(elementId) {
            const el = document.getElementById(elementId);
            if (el) el.innerText = "";
        }
        
        function initKlineChart() {
            const chartDom = document.getElementById('klineChart');
            if (!chartDom) {
                console.error("KLine chart DOM element not found!");
                return;
            }
            klineChartInstance = echarts.init(chartDom);
            klineChartInstance.setOption({
                title: { text: '请先检索股票以加载K线数据', left: 'center', top: 'center', textStyle: {color: '#888'} },
                xAxis: {show:false}, yAxis: {show:false}
            });
        }


        async function searchStock() {
            clearError('searchError');
            clearError('realtimeError');
            clearError('klineError');
            const query = document.getElementById('stockQuery').value.trim();
            if (!query) {
                displayError('searchError', '请输入股票代码或名称。');
                return;
            }

            document.getElementById('stockInfo').innerHTML = '正在检索...';
            document.getElementById('currentStockNameDisplay').innerText = '--';
            document.getElementById('currentStockCodeDisplay').innerText = '--';
            ['stockPrice', 'stockChangeAmount', 'stockChangePercent', 'stockVolume', 'stockTurnover', 'stockOpen', 'stockPrevClose', 'stockHigh', 'stockLow', 'lastUpdated'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerText = '--';
            });
            if(klineChartInstance) klineChartInstance.clear();
            document.getElementById('manualRefreshBtn').disabled = true; // 禁用刷新按钮直到搜索完成


            try {
                const response = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
                if (!response.ok) {
                    const errData = await response.json().catch(() => ({error: "检索失败，请检查输入或稍后再试。"}));
                    throw new Error(errData.error || `服务器错误: ${response.status}`);
                }
                const data = await response.json();

                if (data.error) {
                    displayError('searchError', data.error);
                    document.getElementById('stockInfo').innerHTML = '';
                    return;
                }
                
                currentStockCode = data.code;
                document.getElementById('stockInfo').innerHTML = `
                    <div class="info-item"><strong>代码:</strong> ${data.code}</div>
                    <div class="info-item"><strong>名称:</strong> ${data.name}</div>
                `;
                document.getElementById('currentStockNameDisplay').innerText = data.name;
                document.getElementById('currentStockCodeDisplay').innerText = data.code;

                fetchRealtimeData(currentStockCode); // 首次加载实时数据
                fetchAndDrawKLine(currentStockCode);
                document.getElementById('manualRefreshBtn').disabled = false; // 启用刷新按钮

                // 移除自动刷新逻辑:
                // if (realtimeIntervalId) {
                //     clearInterval(realtimeIntervalId);
                // }
                // realtimeIntervalId = setInterval(() => fetchRealtimeData(currentStockCode), 10000); 

            } catch (error) {
                console.error('Search error:', error);
                displayError('searchError', '检索失败: ' + error.message);
                document.getElementById('stockInfo').innerHTML = '';
                document.getElementById('manualRefreshBtn').disabled = true; // 搜索失败也禁用
            }
        }

        async function fetchRealtimeData(stockCode) {
            if (!stockCode) {
                // displayError('realtimeError', '请先检索股票。'); // 如果按钮被正确禁用，这里可以不提示
                return;
            }
            clearError('realtimeError');
            const refreshBtn = document.getElementById('manualRefreshBtn');
            refreshBtn.disabled = true; // 刷新时禁用按钮
            refreshBtn.innerText = '刷新中...';

            try {
                const response = await fetch(`/api/realtime?code=${stockCode}`);
                 if (!response.ok) {
                    const errData = await response.json().catch(() => ({error: "获取实时数据失败。"}));
                    throw new Error(errData.error || `服务器错误: ${response.status}`);
                }
                const data = await response.json();

                if (data.error) {
                    displayError('realtimeError', data.error);
                    return;
                }
                
                const fields = {
                    'stockPrice': data.price,
                    'stockChangeAmount': data.change_amount,
                    'stockChangePercent': data.change_percent,
                    'stockVolume': data.volume !== null ? (data.volume / 100).toLocaleString() : '--', 
                    'stockTurnover': data.turnover !== null ? (data.turnover / 10000).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' 万' : '--', 
                    'stockOpen': data.open,
                    'stockPrevClose': data.prev_close,
                    'stockHigh': data.high,
                    'stockLow': data.low
                };

                for (const id in fields) {
                    const el = document.getElementById(id);
                    if (el) el.innerText = fields[id] !== null && fields[id] !== undefined ? fields[id] : '--';
                }
                const luEl = document.getElementById('lastUpdated');
                if (luEl) luEl.innerText = new Date().toLocaleTimeString();

            } catch (error) {
                console.error('Realtime data error:', error);
                displayError('realtimeError', '获取实时数据失败: ' + error.message);
            } finally {
                refreshBtn.disabled = false; // 无论成功失败都恢复按钮
                refreshBtn.innerText = '手动刷新';
            }
        }

        // 新增手动刷新函数
        function manualRefreshData() {
            if (currentStockCode) {
                fetchRealtimeData(currentStockCode);
            } else {
                displayError('realtimeError', '请先检索一只股票。');
            }
        }

        async function fetchAndDrawKLine(stockCode) {
            if (!stockCode || !klineChartInstance) return;
            clearError('klineError');
            klineChartInstance.showLoading();
            try {
                const response = await fetch(`/api/history?code=${stockCode}`);
                if (!response.ok) {
                    const errData = await response.json().catch(() => ({error: "获取历史数据失败。"}));
                    throw new Error(errData.error || `服务器错误: ${response.status}`);
                }
                const data = await response.json();

                if (data.error) {
                    displayError('klineError', data.error);
                    klineChartInstance.hideLoading();
                    return;
                }
                
                const dates = data.map(item => item.date);
                const klineData = data.map(item => [item.open, item.close, item.low, item.high]);
                const volumes = data.map((item, idx) => [idx, item.volume, item.open > item.close ? -1 : 1]);


                const option = {
                    tooltip: {
                        trigger: 'axis',
                        axisPointer: { type: 'cross' }
                    },
                    legend: { data: ['日K', '成交量'] },
                    grid: [
                        { left: '10%', right: '8%', height: '50%' },
                        { left: '10%', right: '8%', top: '65%', height: '16%' }
                    ],
                    xAxis: [
                        { type: 'category', data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false }, min: 'dataMin', max: 'dataMax' },
                        { type: 'category', gridIndex: 1, data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, min: 'dataMin', max: 'dataMax' }
                    ],
                    yAxis: [
                        { scale: true, splitArea: { show: true }, axisLabel: { formatter: function (value) { return value.toFixed(2); } } },
                        { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
                    ],
                    dataZoom: [
                        { type: 'inside', xAxisIndex: [0, 1], start: 70, end: 100 },
                        { show: true, xAxisIndex: [0, 1], type: 'slider', top: '85%', start: 70, end: 100 }
                    ],
                    series: [
                        {
                            name: '日K',
                            type: 'candlestick',
                            data: klineData,
                            itemStyle: {
                                color: '#FD1050', // 阳线 red
                                color0: '#0CF49B', // 阴线 green
                                borderColor: '#FD1050',
                                borderColor0: '#0CF49B'
                            }
                        },
                        {
                            name: '成交量',
                            type: 'bar',
                            xAxisIndex: 1,
                            yAxisIndex: 1,
                            data: volumes.map(item => ({
                                value: item[1],
                                itemStyle: {
                                    color: item[2] === 1 ? '#FD1050' : '#0CF49B' // 阳红柱，阴绿柱
                                }
                            }))
                        }
                    ]
                };
                klineChartInstance.hideLoading();
                klineChartInstance.setOption(option);
            } catch (error) {
                console.error('K-line data error:', error);
                displayError('klineError', '获取K线数据失败: ' + error.message);
                if (klineChartInstance) klineChartInstance.hideLoading();
            }
        }
        
        window.onload = () => {
            initKlineChart();
            document.getElementById('manualRefreshBtn').disabled = true; // 初始禁用刷新按钮
        }
    </script>
</body>
</html>
"""

stock_list_df = None

def get_stock_list_cached():
    global stock_list_df
    if stock_list_df is None or stock_list_df.empty: # Check if empty too
        try:
            print("Fetching A-share list from akshare (stock_zh_a_spot_em)...")
            # Fetch all A-share stock codes and names from Eastmoney real-time data
            # This df contains code, name, and other real-time fields
            temp_df = ak.stock_zh_a_spot_em()
            if temp_df is not None and not temp_df.empty:
                stock_list_df = temp_df[['代码', '名称']].copy() # Keep only relevant columns
                print(f"Successfully fetched {len(stock_list_df)} A-share stock entries.")
            else:
                print("Failed to fetch stock list or list is empty, will try generic search.")
                stock_list_df = pd.DataFrame(columns=['代码', '名称']) # Ensure it's a DataFrame
        except Exception as e:
            print(f"Error fetching stock list with stock_zh_a_spot_em: {e}. Falling back to empty list.")
            stock_list_df = pd.DataFrame(columns=['代码', '名称']) # Ensure it's a DataFrame on error
    return stock_list_df


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/search', methods=['GET'])
def search_stock_api():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "查询不能为空"}), 400

    all_a_shares = get_stock_list_cached()
    
    matched_stock = None

    # Try to match by code first (6 digits) from cached list
    if query.isdigit() and len(query) == 6:
        if not all_a_shares.empty:
            stock_data = all_a_shares[all_a_shares['代码'] == query]
            if not stock_data.empty:
                matched_stock = {"code": stock_data.iloc[0]['代码'], "name": stock_data.iloc[0]['名称']}
        
    # If not matched by code from cache, or query is not a code, try to match by name from cache
    if not matched_stock and not query.isdigit(): 
        if not all_a_shares.empty:
            exact_name_match = all_a_shares[all_a_shares['名称'].str.lower() == query.lower()]
            if not exact_name_match.empty:
                 matched_stock = {"code": exact_name_match.iloc[0]['代码'], "name": exact_name_match.iloc[0]['名称']}
            else:
                partial_name_match = all_a_shares[all_a_shares['名称'].str.contains(query, case=False, na=False)]
                if not partial_name_match.empty:
                    matched_stock = {"code": partial_name_match.iloc[0]['代码'], "name": partial_name_match.iloc[0]['名称']}

    # If still not matched, try fallback search using ak.stock_fuzzy_search
    if not matched_stock:
        try:
            print(f"'{query}' not in cached A-share list or cache is empty, trying ak.stock_fuzzy_search...")
            # 使用 ak.stock_fuzzy_search 作为备用方案
            search_results_df = ak.stock_fuzzy_search(keyword=query)
            if not search_results_df.empty:
                potential_matches = pd.DataFrame()
                # 筛选 A 股市场 (通常类型包含 A股/股票，市场包含 SH/SZ/BJ)
                # '市场' 列可能的值: SH (沪市), SZ (深市), BJ (北交所)
                # '类型' 列可能的值: 例如 'A股', '股票', '深A', '沪A'
                
                # 优先处理代码完全匹配的情况
                if query.isdigit() and len(query) == 6:
                    potential_matches = search_results_df[
                        (search_results_df['代码'] == query) &
                        (
                            search_results_df['类型'].astype(str).str.contains('A股|股票', case=False, na=False) |
                            search_results_df['市场'].astype(str).str.contains('SH|SZ|BJ', case=False, na=False)
                        )
                    ]

                # 如果代码不完全匹配，或者查询本身不是代码，则进行更广泛的名称和类型匹配
                if potential_matches.empty:
                    potential_matches = search_results_df[
                        (
                            search_results_df['类型'].astype(str).str.contains('A股|股票', case=False, na=False) |
                            search_results_df['市场'].astype(str).str.contains('SH|SZ|BJ', case=False, na=False)
                        ) & 
                        ( # 确保至少有一个条件满足：代码匹配或名称包含查询（如果查询不是纯数字）
                           (search_results_df['代码'] == query) | 
                           ((not query.isdigit()) & search_results_df['名称'].astype(str).str.contains(query, case=False, na=False))
                        )
                    ]
                
                if not potential_matches.empty:
                    # 如果查询是名称，优先精确名称匹配
                    temp_matched_stock = None
                    if not query.isdigit():
                        exact_name_df = potential_matches[potential_matches['名称'].astype(str).str.lower() == query.lower()]
                        if not exact_name_df.empty:
                            temp_matched_stock = {"code": exact_name_df.iloc[0]['代码'], "name": exact_name_df.iloc[0]['名称']}
                    
                    if not temp_matched_stock: # 如果没有精确名称匹配或查询是代码，取第一个结果
                         temp_matched_stock = {"code": potential_matches.iloc[0]['代码'], "name": potential_matches.iloc[0]['名称']}

                    # 验证找到的股票代码是否是合法的6位数字A股代码
                    if isinstance(temp_matched_stock['code'], str) and len(temp_matched_stock['code']) == 6 and temp_matched_stock['code'].isdigit():
                        matched_stock = temp_matched_stock
                    else:
                        print(f"Fuzzy search found a non-standard code: {temp_matched_stock['code']}")


        except Exception as e:
            print(f"ak.stock_fuzzy_search error for query '{query}': {e}")
            # 此处不直接返回错误，允许后续的错误处理

    if matched_stock:
         return jsonify(matched_stock)
    else:
        return jsonify({"error": f"未能找到与 '{query}' 匹配的A股股票。请确保输入正确的6位A股代码或中文名称，或稍后再试。"}), 404


@app.route('/api/realtime', methods=['GET'])
def realtime_stock_data():
    stock_code = request.args.get('code', '').strip()
    if not stock_code or not (stock_code.isdigit() and len(stock_code) == 6) :
        return jsonify({"error": "无效的股票代码格式"}), 400

    try:
        stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em() #东财实时行情
        stock_data = stock_zh_a_spot_em_df[stock_zh_a_spot_em_df['代码'] == stock_code]

        if stock_data.empty:
            # Fallback if not in EM list for some reason (e.g. new stock, suspension)
            # Try a more direct real-time quote if available, e.g. stock_individual_info_em
            # For simplicity, we'll stick to stock_zh_a_spot_em for now.
            return jsonify({"error": "未找到该股票的实时数据 (可能已退市或代码错误)"}), 404

        data = stock_data.iloc[0]
        # Helper to convert to float or None
        def to_float_or_none(val):
            try: return float(val) if pd.notna(val) else None
            except ValueError: return None
        # Helper to convert to int or None
        def to_int_or_none(val):
            try: return int(val) if pd.notna(val) else None
            except ValueError: return None

        return jsonify({
            "code": data['代码'],
            "name": data['名称'],
            "price": to_float_or_none(data['最新价']),
            "change_amount": to_float_or_none(data['涨跌额']),
            "change_percent": to_float_or_none(data['涨跌幅']),
            "volume": to_int_or_none(data['成交量']), # 单位：股
            "turnover": to_float_or_none(data['成交额']), # 单位：元
            "open": to_float_or_none(data['今开']),
            "high": to_float_or_none(data['最高']),
            "low": to_float_or_none(data['最低']),
            "prev_close": to_float_or_none(data['昨收']),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error fetching realtime data for {stock_code}: {e}")
        return jsonify({"error": f"获取实时数据失败: {str(e)}"}), 500

@app.route('/api/history', methods=['GET'])
def history_stock_data():
    stock_code = request.args.get('code', '').strip()
    if not stock_code or not (stock_code.isdigit() and len(stock_code) == 6):
        return jsonify({"error": "无效的股票代码格式"}), 400

    try:
        # Fetch daily K-line data, qfq = 前复权
        # Fetch data for the last 3 years for a reasonable chart size
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - pd.Timedelta(days=3*365)).strftime('%Y%m%d')
        
        stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq") 
        
        if stock_hist_df.empty:
            return jsonify({"error": "未找到该股票的历史数据"}), 404
        
        # Helper to convert to float or None
        def to_float_or_none(val):
            try: return float(val) if pd.notna(val) else None
            except ValueError: return None
        # Helper to convert to int or None
        def to_int_or_none(val):
            try: return int(val) if pd.notna(val) else None
            except ValueError: return None

        history_data = []
        for index, row in stock_hist_df.iterrows():
            history_data.append({
                "date": row['日期'], 
                "open": to_float_or_none(row['开盘']),
                "close": to_float_or_none(row['收盘']),
                "low": to_float_or_none(row['最低']),
                "high": to_float_or_none(row['最高']),
                "volume": to_int_or_none(row['成交量']), 
            })
        return jsonify(history_data)
    except Exception as e:
        print(f"Error fetching historical data for {stock_code}: {e}")
        return jsonify({"error": f"获取历史数据失败: {str(e)}"}), 500

if __name__ == '__main__':
    # Pre-fetch stock list on startup to make name search faster
    # This might take a few seconds on first run
    get_stock_list_cached() 
    print(f"股票数据看板已启动。请在浏览器中打开 http://127.0.0.1:5001")
    app.run(debug=False, host='0.0.0.0', port=5001)