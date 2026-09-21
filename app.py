import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import yfinance as yf

# ==========================================
# 1. 頁面基本配置
# ==========================================
st.set_page_config(
    page_title="銘傳金融科技盃 - 台股 ETF AI 每日交易決策儀表板",
    page_icon="📈",
    layout="wide",
)

st.title("🏆 銘傳金融科技盃 - 台股 ETF AI 每日買賣決策儀表板")
st.caption("支援當日庫存再平衡 (Rebalancing) | 自動產出買進/賣出/續抱指令")
st.markdown("---")

# ==========================================
# 2. 側邊欄：市場數據與競賽階段設定
# ==========================================
st.sidebar.header("⚙️ 1. 比賽階段與風控設定")
build_phase = st.sidebar.selectbox(
    "選擇目前比賽建倉階段",
    [
        "第 1 階段：試探開局 (持股上限 30%)",
        "第 2 階段：波段建倉 (持股上限 60%)",
        "第 3 階段：完全佈局 (最高持股 80%，保留 20% 防禦現金)",
    ],
)

phase_max_exposure = {
    "第 1 階段：試探開局 (持股上限 30%)": 0.30,
    "第 2 階段：波段建倉 (持股上限 60%)": 0.60,
    "第 3 階段：完全佈局 (最高持股 80%，保留 20% 防禦現金)": 0.80,
}[build_phase]

st.sidebar.header("⚙️ 2. 今日台股在地數據")
taiex_close = st.sidebar.number_input("加權指數收盤價", value=22500, step=50)
taiex_ma20 = st.sidebar.number_input("加權指數月線 (MA20)", value=22100, step=50)
foreign_futures_oi = st.sidebar.slider("外資期貨淨多空單 (口)", -30000, 30000, -5000, step=1000)
pc_ratio = st.sidebar.slider("選擇權 Put/Call Ratio (%)", 50, 150, 105, step=1)
discount_rate = st.sidebar.slider("目標 ETF 折溢價率 (%)", -2.0, 2.0, 0.2, step=0.1)

# ==========================================
# 3. 主頁面：輸入「目前實際庫存與現金」
# ==========================================
st.markdown("### 💼 請輸入目前團隊「實際帳戶庫存」")
st.caption("請填入目前手上的現金餘額與各檔 ETF 的當前市值，AI 將自動比對差異計算今日下單量。")

col_cash, col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(6)
with col_cash:
    cur_cash = st.number_input("當前現金餘額 (元)", value=10000000, step=100000)
with col_h1:
    cur_0050 = st.number_input("0050 現有市值", value=0, step=50000)
with col_h2:
    cur_00881 = st.number_input("00881 現有市值", value=0, step=50000)
with col_h3:
    cur_0056 = st.number_input("0056 現有市值", value=0, step=50000)
with col_h4:
    cur_00713 = st.number_input("00713 現有市值", value=0, step=50000)
with col_h5:
    cur_00679b = st.number_input("00679B 現有市值", value=0, step=50000)

# 計算總資產淨值 (NAV)
total_portfolio_value = cur_cash + cur_0050 + cur_00881 + cur_0056 + cur_00713 + cur_00679b

st.info(f"💰 **目前總資產淨值 (NAV)**：NT$ {total_portfolio_value:,.0f} 元")
st.markdown("---")

# ==========================================
# 4. AI 多因子綜合打分邏輯
# ==========================================
taiex_score = 40 if taiex_close > taiex_ma20 else 10

if foreign_futures_oi > 10000:
    futures_score = 30
elif foreign_futures_oi < -10000:
    futures_score = 0
else:
    futures_score = 15

if pc_ratio >= 110:
    option_score = 30
elif pc_ratio <= 85:
    option_score = 5
else:
    option_score = 18

total_score = taiex_score + futures_score + option_score

# 定義多空決策與細分 ETF 權重 (拆解至具體單一 ETF)
if total_score >= 75:
    status = "【強勢多頭】動態加碼攻擊"
    status_color = "red"
    # 科技 50% (0050:30%, 00881:20%), 高股息 30% (0056:15%, 00713:15%), 債券/現金 20%
    target_weights = {"0050": 0.30, "00881": 0.20, "0056": 0.15, "00713": 0.15, "00679B": 0.00}
elif total_score <= 40:
    status = "【空頭防禦】減碼保住獲利"
    status_color = "green"
    # 科技 10% (0050:10%), 高股息 30% (0056:15%, 00713:15%), 債券 10%, 現金 50%
    target_weights = {"0050": 0.10, "00881": 0.00, "0056": 0.15, "00713": 0.15, "00679B": 0.10}
else:
    status = "【震盪整理】區間操作避險"
    status_color = "orange"
    # 科技 30% (0050:20%, 00881:10%), 高股息 40% (0056:20%, 00713:20%), 現金 30%
    target_weights = {"0050": 0.20, "00881": 0.10, "0056": 0.20, "00713": 0.20, "00679B": 0.00}

# 套用建倉階段上限風控
sum_stock_w = sum(target_weights.values())
if sum_stock_w > phase_max_exposure:
    scale = phase_max_exposure / sum_stock_w
    target_weights = {k: v * scale for k, v in target_weights.items()}

# ==========================================
# 5. 計算當日再平衡與買賣指令 (Rebalancing Engine)
# ==========================================
etf_tickers = {
    "0050": "0050.TW",
    "00881": "00881.TW",
    "0056": "0056.TW",
    "00713": "00713.TW",
    "00679B": "00679B.TWO"
}

# 抓取最新單價（用來估算買賣張數）
@st.cache_data(ttl=60)
def get_latest_prices():
    prices = {}
    for code, ticker in etf_tickers.items():
        try:
            df = yf.download(ticker, period="2d")["Close"]
            prices[code] = float(df.iloc[-1])
        except:
            prices[code] = 100.0  # 抓取失敗時預設備用價格
    return prices

latest_prices = get_latest_prices()

current_holdings = {
    "0050": cur_0050,
    "00881": cur_00881,
    "0056": cur_0056,
    "00713": cur_00713,
    "00679B": cur_00679b
}

trade_suggestions = []
rebalance_threshold = 30000  # 風控：調倉門檻 3 萬元，低於 3 萬元不動作以節省交易成本

for code in target_weights.keys():
    target_amt = total_portfolio_value * target_weights[code]
    cur_amt = current_holdings[code]
    delta = target_amt - cur_amt
    price = latest_prices.get(code, 100.0)
    
    # 判斷買賣動作
    if delta > rebalance_threshold:
        action = "🟢 加碼買進"
        trade_amt = delta
        shares = int(trade_amt / (price * 1000))  # 計算張數 (1張 = 1000股)
    elif delta < -rebalance_threshold:
        action = "🔴 減碼獲利/停損"
        trade_amt = abs(delta)
        shares = int(trade_amt / (price * 1000))
    else:
        action = "⚪ 續抱觀望"
        trade_amt = 0
        shares = 0
        
    trade_suggestions.append({
        "標的代號": code,
        "最新參考單價": f"NT$ {price:.2f}",
        "目前庫存金額": cur_amt,
        "AI 當日目標金額": target_amt,
        "當日交易建議": action,
        "建議調整金額": trade_amt,
        "預估交易張數": f"{shares} 張" if shares > 0 else "-"
    })

df_trade = pd.DataFrame(trade_suggestions)

# ==========================================
# 6. 視覺化呈現與當日指令輸出
# ==========================================
st.markdown("### 🎯 今日 AI 具體交易指令 (Rebalancing Signal)")

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric("台股 AI 綜合分數", f"{total_score} / 100")
with col_m2:
    st.subheader(f":{status_color}[{status}]")
with col_m3:
    if discount_rate > 0.8:
        st.error(f"⚠️ 風控警示：折溢價過高 ({discount_rate}%)，暫緩追高買進！")
    elif discount_rate < -0.5:
        st.success(f"💡 套利訊號：折價 ({discount_rate}%)，出現抄底買點！")
    else:
        st.info("ℹ️ 折溢價處於正常安全區間")

# 顯示當日買賣建議表格
st.dataframe(
    df_trade.style.format({
        "目前庫存金額": "NT$ {:,.0f}",
        "AI 當日目標金額": "NT$ {:,.0f}",
        "建議調整金額": "NT$ {:,.0f}"
    }),
    use_container_width=True
)

st.caption("💡 **風控門檻提示**：若調整金額低於 NT$ 30,000 元，系統會自動認定為「續抱觀望」，避免頻繁小額交易產生過多摩擦成本。")
