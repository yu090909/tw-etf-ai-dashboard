import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
import yfinance as yf

# ==========================================
# 1. 頁面基本配置
# ==========================================
st.set_page_config(
    page_title="銘傳金融科技盃 - 台股 ETF AI 量化觀測儀表板",
    page_icon="📈",
    layout="wide",
)

st.title("🏆 銘傳金融科技盃 - 台股 ETF AI 資金配置儀表板")
st.caption(
    "起始資金：NT$ 10,000,000 | 具備「分批建倉」與「動態現金避險」的 6 個月競賽模型"
)
st.markdown("---")

# ==========================================
# 2. 側邊欄：控制面板與半年度風控設定
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

# 風控對應持股上限
phase_max_exposure = {
    "第 1 階段：試探開局 (持股上限 30%)": 0.30,
    "第 2 階段：波段建倉 (持股上限 60%)": 0.60,
    "第 3 階段：完全佈局 (最高持股 80%，保留 20% 防禦現金)": 0.80,
}[build_phase]

st.sidebar.header("⚙️ 2. 今日台股在地數據")
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

# ==========================================
# 3. AI 多因子綜合打分邏輯
# ==========================================
# 技術面分數 (0 - 40)
taiex_score = 40 if taiex_close > taiex_ma20 else 10

# 期貨籌碼分數 (0 - 30)
if foreign_futures_oi > 10000:
    futures_score = 30
elif foreign_futures_oi < -10000:
    futures_score = 0
else:
    futures_score = 15

# 選擇權情緒分數 (0 - 30)
if pc_ratio >= 110:
    option_score = 30
elif pc_ratio <= 85:
    option_score = 5
else:
    option_score = 18

total_score = taiex_score + futures_score + option_score

# ==========================================
# 4. 風控與資金動態調配算牌器
# ==========================================
if total_score >= 75:
    status = "【強勢多頭】偏多操作 (動態加碼)"
    status_color = "red"
    target_tech_ratio = 0.50
    target_div_ratio = 0.30
elif total_score <= 40:
    status = "【空頭防禦】縮減風險部位 (提高現金)"
    status_color = "green"
    target_tech_ratio = 0.10
    target_div_ratio = 0.30
else:
    status = "【震盪整理】區間操作 (高股息避險)"
    status_color = "orange"
    target_tech_ratio = 0.30
    target_div_ratio = 0.40

# 強制風控限制：持股不得超過當前階段上限
raw_stock_ratio = target_tech_ratio + target_div_ratio
actual_stock_ratio = min(raw_stock_ratio, phase_max_exposure)

# 依比例重新等比分配
scale_factor = (
    actual_stock_ratio / raw_stock_ratio if raw_stock_ratio > 0 else 0
)
tech_w = target_tech_ratio * scale_factor
div_w = target_div_ratio * scale_factor
cash_w = 1.0 - tech_w - div_w  # 剩餘資金全部強制作為防禦現金池

capital = 10000000
allocation_data = {
    "資產類別": [
        "科技/大盤攻擊型 (0050/00881)",
        "高股息/低波防禦型 (0056/00713/00878)",
        "防禦現金池 / 債券 (00679B)",
    ],
    "建議金額 (NT$)": [
        capital * tech_w,
        capital * div_w,
        capital * cash_w,
    ],
    "配置比例 (%)": [tech_w * 100, div_w * 100, cash_w * 100],
}
df_alloc = pd.DataFrame(allocation_data)

# ==========================================
# 5. 儀表板主要視覺化呈現
# ==========================================
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("台股 AI 綜合多空分數", f"{total_score} / 100")
with col2:
    st.subheader(f":{status_color}[{status}]")
    st.caption(
        f"風控限制：目前階段最高持股上限為 {phase_max_exposure*100:.0f}%"
    )
with col3:
    if discount_rate > 0.8:
        st.error(f"⚠️ 風控警示：溢價過高 ({discount_rate}%)，暫緩追高！")
    elif discount_rate < -0.5:
        st.success(
            f"💡 套利訊號：出現折價 ({discount_rate}%)，具備錯殺抄底空間！"
        )
    else:
        st.info("ℹ️ 折溢價處於合理安全區間")

st.markdown("### 📊 1,000 萬資金動態配置建議")

col_chart, col_table = st.columns([1, 1])

with col_chart:
    fig = px.pie(
        df_alloc,
        values="建議金額 (NT$)",
        names="資產類別",
        title="AI 風控資金配置圖",
        hole=0.4,
        color_discrete_sequence=["#FF4B4B", "#00C04D", "#1C83E1"],
    )
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown("#### 具體下單金額與權重")
    st.dataframe(
        df_alloc.style.format(
            {"建議金額 (NT$)": "NT$ {:,.0f}", "配置比例 (%)": "{:.1f}%"}
        ),
        use_container_width=True,
    )
    st.caption(
        "💡 單一標的風控提醒：建議任意單一 ETF 持股金額請勿超過總資金 35%（即 NT$"
        " 3,500,000）。"
    )

st.markdown("---")
st.markdown("### 📈 競賽核心標的行情監測 (60秒刷新)")


@st.cache_data(ttl=60)
def load_etf_data():
    tickers = ["0050.TW", "0056.TW", "00878.TW", "00881.TW", "00713.TW"]
    df = yf.download(tickers, period="1mo")["Close"]
    return df


try:
    etf_prices = load_etf_data()
    st.line_chart(etf_prices)
except Exception as e:
    st.warning("即時行情抓取中，若非開盤時間將顯示最後收盤歷史行情。")
