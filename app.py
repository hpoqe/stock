import os
os.environ['NO_PROXY'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

import streamlit as st
import pandas as pd
import akshare as ak
import baostock as bs
import efinance as ef
import ollama
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import time

# ================= 1. 页面配置 =================
st.set_page_config(page_title="AI 股票深度分析系统", layout="wide", page_icon="📈")
st.title("📈 AI 股票深度分析与跟踪系统")
st.markdown("---")

# ================= 2. 股票池 =================
STOCK_POOL = [
    {"code": "000920", "name": "沃顿科技", "sector": "制造"},
    {"code": "002884", "name": "凌霄泵业", "sector": "制造"},
    {"code": "300515", "name": "三德科技", "sector": "制造"},
    {"code": "300971", "name": "博亚精工", "sector": "制造"},
    {"code": "001310", "name": "华纬科技", "sector": "制造"},
    {"code": "920037", "name": "广信科技", "sector": "新材料"},
    {"code": "688605", "name": "先锋精科", "sector": "半导体"},
    {"code": "300260", "name": "新莱应材", "sector": "制造"},
    {"code": "688618", "name": "三旺通信", "sector": "科技"},
    {"code": "688683", "name": "莱尔科技", "sector": "科技"},
    {"code": "301042", "name": "安联锐视", "sector": "科技"},
    {"code": "688080", "name": "映翰通", "sector": "科技"},
    {"code": "920914", "name": "远航精密", "sector": "科技"},
    {"code": "688153", "name": "唯捷创芯", "sector": "半导体"},
    {"code": "002056", "name": "横店东磁", "sector": "新能源"},
    {"code": "600573", "name": "惠泉啤酒", "sector": "消费"},
    {"code": "300436", "name": "广生堂", "sector": "医药"},
    {"code": "002782", "name": "可立克", "sector": "电子"},
    {"code": "301327", "name": "华宝新能源", "sector": "新能源"},
    {"code": "603195", "name": "公牛集团", "sector": "消费"}
]

# ================= 3. 状态管理（实现点击联动） =================
if 'selected_code' not in st.session_state:
    st.session_state.selected_code = STOCK_POOL[0]['code']

# 侧边栏：下拉菜单（备用方式，与表格点击保持同步）
st.sidebar.header("🔍 股票切换")
stock_names = [s["name"] for s in STOCK_POOL]
# 找到当前选中代码对应的名称，作为下拉框的默认值
default_name = next((s['name'] for s in STOCK_POOL if s['code'] == st.session_state.selected_code), stock_names[0])
selected_name = st.sidebar.selectbox("选择股票", stock_names, index=stock_names.index(default_name))
selected_stock = next(s for s in STOCK_POOL if s["name"] == selected_name)

# 如果侧边栏切换了，更新 session_state
if selected_stock['code'] != st.session_state.selected_code:
    st.session_state.selected_code = selected_stock['code']
    st.rerun()

# 获取当前正在分析的股票信息
current_code = st.session_state.selected_code
current_stock = next(s for s in STOCK_POOL if s['code'] == current_code)
current_name = current_stock['name']
current_sector = current_stock['sector']

# ================= 4. 数据获取 =================

@st.cache_data(ttl=1800)
def get_all_stocks_overview():
    pool_codes = [s['code'] for s in STOCK_POOL]
    try:
        df = ef.stock.get_realtime_quotes()
        df = df[['股票代码', '股票名称', '最新价', '涨跌幅', '动态市盈率', '成交额']]
        df.columns = ['代码', '名称', '最新价', '涨跌幅', '市盈率-动态', '成交额']
        df['代码'] = df['代码'].astype(str).str.zfill(6)
        df = df[df['代码'].isin(pool_codes)].copy()
        df = df.set_index('代码')
        df = df.reindex(pool_codes)
        st.success("✅ 使用 efinance 获取全市场行情成功")
        return df
    except Exception as e1:
        st.warning(f"efinance 失败，尝试新浪接口... 错误: {e1}")

    try:
        df = ak.stock_zh_a_spot()
        df['代码'] = df['代码'].astype(str).str.replace(r'[a-zA-Z]', '', regex=True).str.zfill(6)
        df = df.rename(columns={'name': '名称', 'trade': '最新价', 'changepercent': '涨跌幅', 'amount': '成交额'})
        df['市盈率-动态'] = np.nan
        df = df[df['代码'].isin(pool_codes)].copy()
        df = df.set_index('代码')
        df = df[['名称', '最新价', '涨跌幅', '市盈率-动态', '成交额']]
        df = df.reindex(pool_codes)
        st.success("✅ 使用新浪备用接口获取行情成功")
        return df
    except Exception as e2:
        st.error(f"所有真实行情接口均失败: {e2}")

    data = []
    for s in STOCK_POOL:
        data.append({"代码": s["code"], "名称": s["name"], "最新价": 10.0, "涨跌幅": 0.0, "市盈率-动态": 15.0, "成交额": 0})
    return pd.DataFrame(data).set_index("代码")

@st.cache_data(ttl=86400)
def get_financial_summary(code):
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2024")
        if df.empty: return {"ROE": "N/A", "毛利率": "N/A", "净利润增长率": "N/A"}
        latest = df.iloc[0]
        roe = latest.get('净资产收益率(%)', np.nan)
        gross = latest.get('销售毛利率(%)', np.nan)
        growth = latest.get('净利润增长率(%)', np.nan)
        return {"ROE": f"{roe:.2f}" if pd.notna(roe) else "N/A", "毛利率": f"{gross:.2f}" if pd.notna(gross) else "N/A", "净利润增长率": f"{growth:.2f}" if pd.notna(growth) else "N/A"}
    except Exception:
        return {"ROE": "N/A", "毛利率": "N/A", "净利润增长率": "N/A"}

@st.cache_data(ttl=3600)
def get_historical_data(code):
    if code.startswith('6'):
        bs_code = f"sh.{code}"
    elif code.startswith(('0', '3')):
        bs_code = f"sz.{code}"
    else:
        return generate_mock_data(code)
    lg = bs.login()
    try:
        rs = bs.query_history_k_data_plus(bs_code, "date,open,high,low,close,volume", start_date='2023-01-01', end_date=datetime.now().strftime('%Y-%m-%d'), frequency="d", adjustflag="2")
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        df = pd.DataFrame(data_list, columns=rs.fields)
        df = df.rename(columns={'date': '日期', 'open': '开盘', 'high': '最高', 'low': '最低', 'close': '收盘', 'volume': '成交量'})
        for col in ['开盘', '最高', '最低', '收盘', '成交量']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df['日期'] = pd.to_datetime(df['日期'])
        bs.logout()
        if df.empty: return generate_mock_data(code)
        st.success(f"✅ 使用 BaoStock 获取 {code} 历史数据成功")
        return df
    except Exception as e:
        bs.logout()
        st.warning(f"BaoStock 获取失败，生成模拟数据。错误: {e}")
        return generate_mock_data(code)

def generate_mock_data(code):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=3*365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    prices = [10.0]
    for _ in range(len(dates)-1):
        prices.append(prices[-1] * (1 + np.random.normal(0, 0.02)))
    return pd.DataFrame({'日期': dates, '开盘': prices, '收盘': prices, '最高': [p*1.02 for p in prices], '最低': [p*0.98 for p in prices], '成交量': np.random.randint(10000, 100000, len(dates))})

# ================= 5. 预加载数据 =================
with st.spinner(f"正在加载 {current_name} 的数据..."):
    hist_df = get_historical_data(current_code)
    fin_data = get_financial_summary(current_code)
    hist_df['涨跌幅'] = hist_df['收盘'].pct_change() * 100
    turning_points = hist_df[abs(hist_df['涨跌幅']) > 8].copy()

# ================= 6. 主界面 =================
tab_overview, tab_detail, tab_ai = st.tabs(["📊 全市场总览", "📉 单只股票深度诊断", "🤖 AI 深度诊断"])

with tab_overview:
    st.subheader("📊 20只中小盘股票池实时总览")
    st.markdown("👉 **点击下方表格中的任意一行**，系统会自动切换下方「深度诊断」和「AI 诊断」的目标股票。")
    
    with st.spinner("正在抓取全市场行情..."):
        overview_df = get_all_stocks_overview()
    
    if not overview_df.empty:
        # 🌟 核心改动：开启行选择功能
        event = st.dataframe(
            overview_df.style.map(
                lambda x: 'color: red' if isinstance(x, (int, float)) and x > 0 else ('color: green' if isinstance(x, (int, float)) and x < 0 else ''),
                subset=['涨跌幅']
            ).format({"最新价": "{:.2f}", "涨跌幅": "{:.2f}%", "市盈率-动态": "{:.2f}", "成交额": "{:,.0f}"}, na_rep="N/A"),
            use_container_width=True,
            height=600,
            on_select="rerun",          # 选中行后重新运行
            selection_mode="single-row" # 只允许选一行
        )
        
        # 如果用户点击了表格中的某一行
        if event.selection.rows:
            selected_row_index = event.selection.rows[0]
            clicked_code = overview_df.index[selected_row_index]
            
            # 如果点击的代码和当前状态不一致，更新状态并刷新页面
            if clicked_code != st.session_state.selected_code:
                st.session_state.selected_code = clicked_code
                st.rerun()
    else:
        st.info("暂未获取到真实行情。")

with tab_detail:
    st.subheader(f"📉 {current_name} ({current_code}) 历史深度诊断")
    
    latest_price = hist_df['收盘'].iloc[-1]
    prev_price = hist_df['收盘'].iloc[-2] if len(hist_df) > 1 else latest_price
    day_change = (latest_price - prev_price) / prev_price * 100 if prev_price != 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新收盘价", f"¥{latest_price:.2f}", delta=f"{day_change:.2f}%")
    col2.metric("所属板块", current_sector)
    col3.metric("最新 ROE", f"{fin_data['ROE']}%")
    col4.metric("最新毛利率", f"{fin_data['毛利率']}%")
    
    fig = go.Figure(data=[go.Candlestick(
        x=hist_df['日期'], open=hist_df['开盘'], high=hist_df['最高'],
        low=hist_df['最低'], close=hist_df['收盘'], name='日K线'
    )])
    
    if not turning_points.empty:
        fig.add_trace(go.Scatter(
            x=turning_points['日期'], y=turning_points['最高'] * 1.05,
            mode='markers+text', marker=dict(color='red', size=10, symbol='triangle-down'),
            text=turning_points['涨跌幅'].apply(lambda x: f"{x:.1f}%"),
            textposition="top center", name='关键转折点'
        ))
        
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    if not turning_points.empty:
        st.write("🔍 **历史关键转折点列表（单日涨跌超8%）：**")
        st.dataframe(turning_points[['日期', '收盘', '涨跌幅']].tail(10), use_container_width=True)

with tab_ai:
    st.subheader(f"🤖 AI 深度诊断报告：{current_name}")
    
    if st.button("生成深度诊断报告", type="primary"):
        with st.spinner("AI 正在阅读历史走势、财务数据及行业逻辑，撰写深度研报..."):
            recent_tps = turning_points.tail(5) if not turning_points.empty else pd.DataFrame()
            tp_text = "无极端转折点"
            if not recent_tps.empty:
                tp_text = "\n".join([f"- {row['日期'].strftime('%Y-%m-%d')}: 涨跌幅 {row['涨跌幅']:.2f}%" for _, row in recent_tps.iterrows()])
            
            prompt = f"""
            你是一名资深证券分析师。请针对A股上市公司 {current_name} ({current_code}) 生成一份深度诊断报告。
            该公司属于 {current_sector} 板块。
            
            【当前财务指标】
            - ROE: {fin_data['ROE']}%
            - 毛利率: {fin_data['毛利率']}%
            - 净利润增长率: {fin_data['净利润增长率']}%
            - 最新收盘价: {latest_price:.2f}元
            
            【近期历史转折点（单日暴涨暴跌）】
            {tp_text}
            
            【分析要求】
            请按以下三个维度输出，总字数控制在 600 字左右，语言专业但通俗易懂：
            1. 【历史转折点复盘】结合上述历史暴涨暴跌的时间点，推测当时可能发生了什么样的行业变化或公司事件，导致股价出现如此大的波动？
            2. 【当前情况诊断】结合它的财务指标（ROE、毛利率）和所属板块，评价它当前的基本面健康度，以及目前估值处于什么样的状态（高估/低估/合理）？
            3. 【未来走向推演】基于当前宏观政策、中观赛道景气度，给出它未来 6-12 个月的三种情景推演（乐观、中性、悲观），并给出操作跟踪策略（不要直接说买入/卖出，用“策略参考”代替）。
            """
            
            try:
                response = ollama.chat(model='qwen3-vl:4b', messages=[{'role': 'user', 'content': prompt}])
                st.success("✅ 诊断报告生成完毕！")
                st.markdown(response['message']['content'])
            except Exception as e:
                st.error(f"AI 分析失败，请检查 Ollama 是否运行。错误: {e}")

st.markdown("---")
st.caption("⚠️ 免责声明：本工具基于公开历史数据与本地 AI 模型生成，仅供学习与虚拟投资参考，不构成任何真实的投资建议。")