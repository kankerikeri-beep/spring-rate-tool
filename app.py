import streamlit as st
import numpy as np
import plotly.graph_objects as go
import streamlit.components.v1 as components

# --- 1. ページ設定（※絶対に一番最初に書く） ---
st.set_page_config(page_title="ばねレート簡易判定ツール v2.5", layout="wide")

# --- 2. Google Analytics 設定 ---
ga_code = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-N6J2MEPVXL"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-N6J2MEPVXL');
</script>
"""
components.html(ga_code, height=0)

# --- 3. タイトルと説明 ---
st.title("ばねレート簡易判定ツール")
st.caption("YouTubeチャンネル『こぼれ小話 タミケンバーン』連動ツール")
st.caption("※本ツールは診断ではなく、ばねの性格を概算数値で把握するためのものです")

st.markdown("▶ 使用方法解説動画（こぼれ小話タミケンバーンYouTubeチャンネル） \nhttps://youtu.be/rES0bE0S45Y")
st.divider()

# --- 4. 入力セクション ---
spring_name = st.text_input("スプリング名（スクショ用）", "グロム/JC92")

unit = st.radio("表示単位", ["kgf/mm", "N/mm"], horizontal=True)
load_unit = "kgf" if unit == "kgf/mm" else "N"

col_in1, col_in2 = st.columns(2)

with col_in1:
    st.header("① 基本寸法")
    d = st.number_input("線径 d [mm]", 0.0, value=3.8, step=0.1)
    Do = st.number_input("外径 Do [mm]", 0.0, value=25.3, step=0.1)

with col_in2:
    st.header("② 有効巻き数")
    N_dense = st.number_input("密巻 有効巻き数", 0.0, value=35.0, step=0.1)
    N_coarse = st.number_input("荒巻 有効巻き数", 0.0, value=21.5, step=0.1)

st.header("③ 構造補足")
col_in3, col_in4 = st.columns(2)
with col_in3:
    L_free = st.number_input("自由長 L_free [mm]", 0.0, value=365.0, step=0.1)
    L_dense_free = st.number_input("密巻自由長（座巻含む実測）[mm]", 0.0, value=204.0, step=0.1)
    seat_dense = st.number_input("座巻厚（密巻側）[mm]", 0.0, value=3.5, step=0.1)

with col_in4:
    seat_coarse = st.number_input("座巻厚（荒巻側）[mm]", 0.0, value=3.0, step=0.1)
    P = st.number_input("プリロード [mm]", 0.0, value=27.0, step=1.0)
    S_susp = st.number_input("サスペンション最大ストローク量 [mm]", 0.0, value=97.0, step=1.0)

# --- 5. 物理計算セクション ---
G_val = 78500
Dm = Do - d

k_dense = (G_val * d**4) / (8 * Dm**3 * N_dense) if N_dense > 0 else 1e10
k_coarse = (G_val * d**4) / (8 * Dm**3 * N_coarse) if N_coarse > 0 else 1e10

k_initial = 1 / ((1 / k_dense) + (1 / k_coarse))
k_late = k_coarse

L_solid_dense = (N_dense * d) + seat_dense
max_delta_dense = max(0.0, L_dense_free - L_solid_dense)
total_delta_at_change = max_delta_dense + (k_dense * max_delta_dense) / k_coarse
S_change = max(0.0, total_delta_at_change - P)
F_change_n = k_initial * total_delta_at_change

L_solid_total = (N_dense + N_coarse) * d + seat_dense + seat_coarse
S_max_total = max(0.0, L_free - L_solid_total)
S_max_stroke = max(0.0, S_max_total - P)

gap_dense = ((L_dense_free - seat_dense) / N_dense) - d if N_dense > 0 else 0
gap_coarse = (((L_free - L_dense_free) - seat_coarse) / N_coarse) - d if N_coarse > 0 else 0

def calc_load_n(x):
    x_total = P + x
    if (N_dense == 0 or N_coarse == 0) or x_total <= total_delta_at_change:
        return k_initial * x_total
    return F_change_n + k_late * (x_total - total_delta_at_change)

def to_disp(val_n, is_rate=False):
    if unit == "kgf/mm":
        return val_n / 9.80665
    return val_n

# --- 6. 算出結果 ---
st.divider()
st.header("④ 算出結果")

col_res1, col_res2 = st.columns(2)

with col_res1:
    st.metric(f"初期レート ({unit})", f"{to_disp(k_initial, True):.3f}")
    st.metric("変化ポイント位置 (mm)", f"{S_change:.1f}")

with col_res2:
    st.metric(f"後半レート ({unit})", f"{to_disp(k_late, True):.3f}")
    st.metric(f"変化ポイント荷重 ({load_unit})", f"{to_disp(F_change_n):.1f}")

F_susp_disp = to_disp(calc_load_n(min(S_susp, S_max_stroke)))
st.metric(f"最大ストローク荷重 ({load_unit})", f"{F_susp_disp:.1f}")
st.metric("線間密着限界 (mm)", f"{S_max_stroke:.1f}")

col_gap1, col_gap2 = st.columns(2)
with col_gap1:
    st.metric("密巻部 線間隙間 (mm)", f"{max(0.0, gap_dense):.2f}")
with col_gap2:
    st.metric("荒巻部 線間隙間 (mm)", f"{max(0.0, gap_coarse):.2f}")

# --- 7. グラフ描画 ---
st.write("---")
x_plot = np.linspace(0, S_max_stroke, 400)
y_vals = np.array([to_disp(calc_load_n(v)) for v in x_plot])

fig = go.Figure()
mask = x_plot <= S_change
x1, y1 = x_plot[mask], y_vals[mask]
x2, y2 = x_plot[~mask], y_vals[~mask]

if len(x1) > 0:
    fig.add_trace(go.Scatter(x=x1, y=y1, name="初期レート区間", line=dict(color='blue', width=5)))
if len(x2) > 0:
    if len(x1) > 0:
        x2 = np.insert(x2, 0, x1[-1])
        y2 = np.insert(y2, 0, y1[-1])
    fig.add_trace(go.Scatter(x=x2, y=y2, name="後半レート区間", line=dict(color='orange', width=5)))

fig.add_vline(x=S_change, line_dash="dash", line_color="red")
fig.add_vline(x=S_susp, line_dash="dash", line_color="purple")
fig.add_vline(x=S_max_stroke, line_dash="dash", line_color="black")

fig.add_annotation(
    x=S_change, y=to_disp(F_change_n),
    text=f"変化点 {S_change:.1f}mm\n{to_disp(F_change_n):.1f}{load_unit}",
    showarrow=True, arrowhead=2
)
fig.add_annotation(
    x=S_susp, y=F_susp_disp,
    text=f"最大ストローク {S_susp:.1f}mm\n{F_susp_disp:.1f}{load_unit}",
    showarrow=True, arrowhead=2, ay=-40
)

fig.update_layout(template="simple_white", xaxis_title="ストローク量 (mm)", yaxis_title=f"荷重 ({load_unit})", height=600)
st.plotly_chart(fig, use_container_width=True, key="rate_tool_chart_v25")

# --- 8. 予告セクション ---
st.divider()
st.subheader("関連ツール・予告")
col_next1, col_next2 = st.columns(2)
with col_next1:
    st.button("▶ リアサスリンクシミュレーター（準備中）", key="btn_rear_sim")
with col_next2:
    st.button("▶ フロントフォークエアバネシミュレーター（更新中）", key="btn_fork_sim_pre")
