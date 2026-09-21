import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import yfinance as yf

# 頁面配置
st.set_page_config(
    page_title="銘傳金融科技盃 - 台股 ETF AI 量化觀測儀表板",
    page_icon="📈",
    layout="wide",
)

st.title("🏆 銘傳金融科技盃 - 台股 ETF AI 資金配置儀表板")
st.caption(
    "起始資金：NT$ 10,000,000 | 專為 6 個月實戰競賽打造的多因子動態模型"
)
st.markdown("---")

# 側邊欄：台股指標控制面板
st.sidebar.header("⚙️ 今日台股在地數據輸入")

taiex_close = st.sidebar.number_input(
    "加權指數收盤價", value=22500, step=50
)
taiex_ma20 = st.sidebar.number_input(
    "加權指數月線 (MA20)", value=22100, step=50
)
foreign_futures_oi = st.sidebar.slider(
    "外資期貨淨多空單 (口)", -30000, 30000, -5000, step=1000
)
pc_ratio = st.sidebar.slider("選擇權 Put/Call Ratio (%)", 50, 150, 105, step=1)
discount_rate = st.sidebar.slider(
    "目標 ETF 折溢價率 (%)", -2.0, 2.0, 0.2, step=0.1
)

# AI 模型計算邏輯
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

# 分數判定與策略
if total_score >= 75:
    status = "【強勢多頭】全面偏多攻擊"
    status_color = "red"
    tech_w, div_w, cash_w = 0.65, 0.25, 0.10
elif total_score <= 40:
    status = "【空頭防禦】縮減持股保住勝果"
    status_color = "green"
    tech_w, div_w, cash_w = 0.15, 0.45, 0.40
else:
    status = "【震盪整理】區間操作，高股息避險"
    status_color = "orange"
    tech_w, div_w, cash_w = 0.35, 0.45, 0.20

capital = 10000000
allocation_data = {
    "資產類別": [
        "科技攻擊型 (0050/00881)",
        "高股息防禦型 (0056/00713/00878)",
        "避險型 (00679B/現金)",
    ],
    "配置金額 (NT$)": [
        capital * tech_w,
        capital * div_w,
        capital * cash_w,
    ],
    "配置比例 (%)": [tech_w * 100, div_w * 100, cash_w * 100],
}
df_alloc = pd.DataFrame(allocation_data)

# 主要儀表板區域
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("台股 AI 綜合分數", f"{total_score} / 100")
with col2:
    st.subheader(f":{status_color}[{status}]")
with col3:
    if discount_rate > 0.8:
        st.error(f"⚠️ 警示：溢價過高 ({discount_rate}%)，暫緩追高！")
    elif discount_rate < -0.5:
        st.success(f"💡 訊號：折價 ({discount_rate}%)，出現抄底空間！")
    else:
        st.info("ℹ️ 折溢價處於正常合理區間")

st.markdown("### 📊 1,000 萬資金最佳配置比例")

col_chart, col_table = st.columns([1, 1])

with col_chart:
    fig = px.pie(
        df_alloc,
        values="配置金額 (NT$)",
        names="資產類別",
        title="AI 資產配置圓餅圖",
        hole=0.4,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown("#### 具體下單金額建議")
    st.dataframe(
        df_alloc.style.format(
            {"配置金額 (NT$)": "NT$ {:,.0f}", "配置比例 (%)": "{:.0f}%"}
        ),
        use_container_width=True,
    )

st.markdown("---")
st.markdown("### 📈 參賽標的近一個月即時行情監測")


@st.cache_data(ttl=3600)
def load_etf_data():
    tickers = ["0050.TW", "0056.TW", "00878.TW", "00881.TW", "00713.TW"]
    df = yf.download(tickers, period="1mo")["Close"]
    return df


try:
    etf_prices = load_etf_data()
    st.line_chart(etf_prices)
except Exception as e:
    st.warning("即時行情抓取中或市場已收盤。")
