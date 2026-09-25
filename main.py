import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# 定义股票代码和板块
stocks = {
    "Materials": ["XOM", "BHP", "RIO", "TSM", "WMT"],
    "Energy": ["BP", "SLB", "COX", "TSM", "XOM"],
    "Technology": ["AAPL", "GOOGL", "AMZN", "MSFT", "NVDA"]
}

# 1. 宏观政策解读
def macro_policy_analysis():
    print("=" * 50)
    print("【宏观政策解读】")
    print("当前市场环境稳定，暂无重大宏观政策影响。")
    print("=" * 50 + "\n")

# 2. 获取并分析单只股票（包含中观和微观逻辑，以及复合策略）
def analyze_stock(symbol, sector):
    try:
        # 使用 yf.Ticker 获取基本面数据
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 安全获取基本面数据（如果不存在则返回 NaN，避免报错）
        eps = info.get('trailingEps', np.nan)             # 每股收益 (EPS)
        pe_ratio = info.get('trailingPE', np.nan)         # 市盈率 (P/E)
        peg_ratio = info.get('pegRatio', np.nan)          # PEG比率
        roe = info.get('returnOnEquity', np.nan)          # 净资产收益率 (ROE)
        revenue = info.get('totalRevenue', np.nan)        # 总营收
        gross_profit = info.get('grossProfits', np.nan)   # 毛利润
        
        # 如果核心数据缺失，跳过分析
        if pd.isna(pe_ratio) or pd.isna(roe) or pd.isna(revenue) or pd.isna(gross_profit):
            print(f"⚠️ {symbol} ({sector}): 核心财务数据缺失，跳过分析。")
            return

        # 计算毛利率
        gross_margin = gross_profit / revenue if revenue != 0 else np.nan
        
        # 计算风险比率 (P/E / PEG)
        risk_ratio = np.nan
        if not pd.isna(peg_ratio) and peg_ratio > 0:
            risk_ratio = pe_ratio / peg_ratio
            
        # ==========================================
        # 💡 复合策略逻辑：ROE > 15% 且 P/E < 20 且 毛利率 > 30%
        # ==========================================
        # 条件1：ROE > 15% (盈利能力)
        condition1 = not pd.isna(roe) and roe > 0.15
        
        # 条件2：P/E < 20 (估值水平)
        condition2 = not pd.isna(pe_ratio) and pe_ratio < 20
        
        # 条件3：毛利率 > 30% (产品竞争力/护城河)
        condition3 = not pd.isna(gross_margin) and gross_margin > 0.30
        
        # 综合判断并生成建议
        if condition1 and condition2 and condition3:
            recommendation = "🟢 买入 (符合所有条件)"
        else:
            recommendation = "🔴 不买入"
            # 打印未满足的条件，方便复盘
            reasons = []
            if not condition1: reasons.append(f"ROE({roe*100:.1f}%) < 15%")
            if not condition2: reasons.append(f"P/E({pe_ratio:.1f}) > 20")
            if not condition3: reasons.append(f"毛利率({gross_margin*100:.1f}%) < 30%")
            recommendation += f" (未达标: {', '.join(reasons)})"
        
        # 打印最终分析结果
        print(f"📈 股票: {symbol} | 板块: {sector}")
        print(f"   - EPS(每股收益): {eps}")
        print(f"   - P/E(市盈率): {pe_ratio:.2f}")
        print(f"   - PEG(市盈率相对盈利增长比率): {peg_ratio if not pd.isna(peg_ratio) else 'N/A'}")
        print(f"   - ROE(净资产收益率): {roe * 100:.2f}%")
        print(f"   - 毛利率: {gross_margin * 100:.2f}%")
        print(f"   - 风险比率 (P/E / PEG): {risk_ratio:.2f}" if not pd.isna(risk_ratio) else "   - 风险比率: N/A")
        print(f"   💡 建议: {recommendation}")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ 处理 {symbol} 时出错，原因: {e}\n")

# 3. 主函数
def main():
    macro_policy_analysis()
    
    print("开始获取并分析股票数据（请确保网络代理已开启）...\n")
    
    # 遍历所有板块和股票
    for sector, symbols in stocks.items():
        print(f"\n【正在分析板块: {sector}】")
        for symbol in symbols:
            analyze_stock(symbol, sector)

if __name__ == "__main__":
    main()