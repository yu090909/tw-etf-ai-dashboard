import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# ==========================================
# 1. 頁面基本配置
# ==========================================
st.set_page_config(
    page_title="銘傳金融科技盃 - 7大精選台股 ETF AI 交易儀表板",
    page_icon="📈",
    layout="wide",
)

st.title("🏆 銘傳金融科技盃 - 7 大精選 ETF 每日 Rebalancing 決策系統")
st.caption(
    "精選 7 檔核心 ETF (0050 / 0052 / 00881 / 00981A / 00713 / 00919 / 00679B)"
    " | 融合籌碼面 + 技術面多因子分析"
)
st.markdown("---")

# ==========================================
# 2. 側邊欄：風控與籌碼指標設定
# ==========================================
st.sidebar.header("⚙️ 1. 比賽進度與持股風控")
build_phase = st.sidebar.selectbox(
    "選擇目前比賽建倉階段",
    [
        "第 1 階段：開局試探 (持股上限 30%)",
        "第 2 階段：波段建倉 (持股上限 60%)",
        "第 3 階段：完全佈局 (最高持股 80%，保留 20% 防禦現金)",
    ],
)

phase_max_exposure = {
    "第 1 階段：開局試探 (持股上限 30%)": 0.30,
    "第 2 階段：波段建倉 (持股上限 60%)": 0.60,
    "第 3 階段：完全佈局 (最高持股 80%，保留 20% 防禦現金)": 0.80,
}[build_phase]

st.sidebar.header("⚙️ 2. 今日台股在地數據")
taiex_close = st.sidebar.number_input(
    "加權指數收盤價", value=47800.0, step=50.0
)
taiex_ma20 = st.sidebar.number_input(
    "加權指數月線 (MA20)", value=46450.0, step=50.0
)

foreign_futures_oi = st.sidebar.slider(
    "外資期貨淨多空單 (口)", -100000, 100000, -75568, step=1000
)
pc_ratio = st.sidebar.slider("選擇權 Put/Call Ratio (%)", 50, 150, 87, step=1)
discount_rate = st.sidebar.slider(
    "目標 ETF 折溢價率 (%)", -2.0, 2.0, -0.5, step=0.1
)

# ==========================================
# 3. 主頁面：輸入帳戶當前實際庫存
# ==========================================
st.markdown("### 💼 請輸入目前團隊「實際帳戶庫存」")
st.caption("填入今日帳戶內的現金餘額與各檔 ETF 當前市值 (未持有填 0)。")

r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
with r1_col1:
  cur_cash = st.number_input("現金餘額 (元)", value=9528731, step=100000)
with r1_col2:
  cur_0050 = st.number_input("0050 (台灣50) 市值", value=0, step=50000)
with r1_col3:
  cur_0052 = st.number_input(
      "0052 (富邦科技) 市值", value=322750, step=50000
  )
with r1_col4:
  cur_00881 = st.number_input("00881 (國泰5G+) 市值", value=0, step=50000)

r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
with r2_col1:
  cur_00981a = st.number_input(
      "00981A (主動統一) 市值", value=147850, step=50000
  )
with r2_col2:
  cur_00713 = st.number_input("00713 (高息低波) 市值", value=0, step=50000)
with r2_col3:
  cur_00919 = st.number_input("00919 (精選高息) 市值", value=0, step=50000)
with r2_col4:
  cur_00679b = st.number_input(
      "00679B (美債20年) 市值", value=0, step=50000
  )

nav = (
    cur_cash
    + cur_0050
    + cur_0052
    + cur_00881
    + cur_00981a
    + cur_00713
    + cur_00919
    + cur_00679b
)
st.info(f"💰 **目前總資產淨值 (NAV)**：NT$ {nav:,.0f} 元")
st.markdown("---")

# ==========================================
# 4. 多因子打分模型 (配分重新權重，總分 100 分)
# ==========================================
# 1. 大盤 MA20 技術面 (40分)
taiex_score = 40 if taiex_close > taiex_ma20 else 10

# 2. 外資期貨籌碼面 (30分)
futures_score = (
    30
    if foreign_futures_oi > 10000
    else (0 if foreign_futures_oi < -10000 else 15)
)

# 3. 選擇權 Put/Call Ratio (30分)
option_score = 30 if pc_ratio >= 110 else (5 if pc_ratio <= 85 else 15)

total_score = taiex_score + futures_score + option_score

if total_score >= 70:
  status = "【強勢多頭】全面偏多攻擊"
  status_color = "red"
  base_weights = {
      "0050": 0.20,
      "0052": 0.20,
      "00881": 0.15,
      "00981A": 0.15,
      "00713": 0.10,
      "00919": 0.00,
      "00679B": 0.00,
  }
elif total_score <= 40:
  status = "【空頭防禦】減碼保住勝果"
  status_color = "green"
  base_weights = {
      "0050": 0.05,
      "0052": 0.00,
      "00881": 0.00,
      "00981A": 0.00,
      "00713": 0.20,
      "00919": 0.10,
      "00679B": 0.15,
  }
else:
  status = "【震盪整理】高股息防禦避險"
  status_color = "orange"
  base_weights = {
      "0050": 0.10,
      "0052": 0.10,
      "00881": 0.10,
      "00981A": 0.10,
      "00713": 0.20,
      "00919": 0.10,
      "00679B": 0.00,
  }

# 根據建倉階段進行風控放縮
total_stock_w = sum(base_weights.values())
if total_stock_w > phase_max_exposure:
  scale = phase_max_exposure / total_stock_w
  target_weights = {k: v * scale for k, v in base_weights.items()}
else:
  target_weights = base_weights.copy()

target_weights["現金"] = 1.0 - sum(target_weights.values())

# ==========================================
# 5. 抓取最新股價引擎 (帶防死鎖機制)
# ==========================================
etf_tickers = {
    "0050": "0050.TW",
    "0052": "0052.TW",
    "00881": "00881.TW",
    "00981A": "00981A.TW",
    "00713": "00713.TW",
    "00919": "00919.TW",
    "00679B": "00679B.TWO",
}


@st.cache_data(ttl=300)
def get_latest_prices():
  prices = {
      "0050": 195.0,
      "0052": 64.55,
      "00881": 27.0,
      "00981A": 29.57,
      "00713": 58.0,
      "00919": 24.5,
      "00679B": 30.0,
  }
  try:
    df = yf.download(
        list(etf_tickers.values()), period="5d", progress=False, timeout=2
    )
    df_close = df["Close"] if "Close" in df else df
    df_close = df_close.ffill().bfill()

    for code, ticker in etf_tickers.items():
      if ticker in df_close.columns:
        val = float(df_close[ticker].dropna().iloc[-1])
        if val > 0:
          prices[code] = val
  except Exception:
    pass
  return prices


latest_prices = get_latest_prices()
current_holdings = {
    "0050": cur_0050,
    "0052": cur_0052,
    "00881": cur_00881,
    "00981A": cur_00981a,
    "00713": cur_00713,
    "00919": cur_00919,
    "00679B": cur_00679b,
}

trade_suggestions = []
threshold = 30000  # 調倉門檻 3 萬元

for code, price in latest_prices.items():
  target_amt = nav * target_weights.get(code, 0.0)
  cur_amt = current_holdings.get(code, 0.0)
  delta = target_amt - cur_amt

  if delta > threshold:
    action = "🟢 加碼買進"
    trade_amt = delta
    shares = int(trade_amt / (price * 1000)) if price > 0 else 0
  elif delta < -threshold:
    action = "🔴 減碼賣出"
    trade_amt = abs(delta)
    shares = int(trade_amt / (price * 1000)) if price > 0 else 0
  else:
    action = "⚪ 續抱觀望"
    trade_amt = 0
    shares = 0

  trade_suggestions.append({
      "標的": f"{code}",
      "最新單價": f"NT$ {price:.2f}",
      "目前持股金額": cur_amt,
      "AI 目標金額": target_amt,
      "當日交易指令": action,
      "建議調倉金額": trade_amt,
      "建議下單張數": f"{shares} 張" if shares > 0 else "-",
  })

df_trade = pd.DataFrame(trade_suggestions)

# ==========================================
# 6. 視覺化儀表板呈現
# ==========================================
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
  st.metric("台股 AI 綜合分數", f"{total_score} / 100")
with col_m2:
  st.subheader(f":{status_color}[{status}]")
  st.caption(
      f"風控限制：目前最高總持股上限為 {phase_max_exposure*100:.0f}%"
  )
with col_m3:
  if discount_rate > 0.8:
    st.error(f"⚠️ 警示：溢價高達 {discount_rate}%，暫緩追高進場！")
  elif discount_rate < -0.5:
    st.success(f"💡 訊號：折價 {discount_rate}%，出現錯殺抄底空間！")
  else:
    st.info("ℹ️ 折溢價處於正常合理區間")

st.markdown("---")
st.markdown("### 🎯 今日 7 大精選 ETF 具體買賣下單指令")

col_chart, col_table = st.columns([1, 1.2])

with col_chart:
  df_pie = pd.DataFrame({
      "類別": list(target_weights.keys()),
      "比例": [v * 100 for v in target_weights.values()],
  })
  fig = px.pie(
      df_pie,
      values="比例",
      names="類別",
      title="AI 當日最佳資產權重圖",
      hole=0.4,
      color_discrete_sequence=[
          "#FF4B4B",
          "#FF6B6B",
          "#FF8585",
          "#FFA07A",
          "#00C04D",
          "#20E070",
          "#1C83E1",
          "#CCCCCC",
      ],
  )
  st.plotly_chart(fig, use_container_width=True)

with col_table:
  st.dataframe(
      df_trade.style.format({
          "目前持股金額": "NT$ {:,.0f}",
          "AI 目標金額": "NT$ {:,.0f}",
          "建議調倉金額": "NT$ {:,.0f}",
      }),
      use_container_width=True,
  )
  st.caption(
      "💡 **下單說明**：若調倉金額未滿 NT$ 30,000"
      " 元，系統會自動認定為「續抱觀望」，以節省手續費與證交稅。"
  )
