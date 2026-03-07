import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="ばねレート簡易判定ツール", layout="wide")

st.title("ばねレート簡易判定ツール")
st.caption("YouTubeチャンネル『こぼれ小話 タミケンバーン』連動ツール")
st.caption("※本ツールは診断ではなく、ばねの性格を概算数値で把握するためのものです")

st.markdown("▶ 使用方法解説動画（YouTube）  \nhttps://www.youtube.com/")
st.divider()

# プリセット変更：スプリング名
spring_name = st.text_input("スプリング名（スクショ用）","グロム/JC92")

unit = st.radio("表示単位",["N/mm","kgf/mm"],horizontal=True)
load_unit = "N" if unit=="N/mm" else "kgf"

st.header("① 基本寸法")

d = st.number_input("線径 d [mm]",0.0,value=3.8,step=0.1)
Do = st.number_input("外径 Do [mm]",0.0,value=25.3,step=0.1)
L_free = st.number_input("自由長 L_free [mm]",0.0,value=365.0,step=0.1)

st.header("② 有効巻き数")

N_dense = st.number_input("密巻 有効巻き数",0.0,value=35.0,step=0.1)
N_coarse = st.number_input("荒巻 有効巻き数",0.0,value=21.5,step=0.1)

# プリセット変更：プリロード
P = st.number_input("プリロード [mm]",0.0,value=27.0,step=0.1)

st.header("③ 構造補足")

L_dense_free = st.number_input(
"密巻自由長（座巻含む実測）[mm]",
0.0,
value=204.0,
step=0.1
)

seat_dense = st.number_input(
"座巻厚（密巻側）[mm]",
0.0,
value=3.5,
step=0.1
)

seat_coarse = st.number_input(
"座巻厚（荒巻側）[mm]",
0.0,
value=3.0,
step=0.1
)

S_susp = st.number_input(
"サスペンション最大ストローク量 [mm]",
0.0,
value=97.0,
step=0.1
)

# --- 物理計算セクション ---
G = 78500
Dm = Do - d

# 単体レートの算出
k_dense = (G * d**4) / (8 * Dm**3 * N_dense) if N_dense > 0 else 1e10
k_coarse = (G * d**4) / (8 * Dm**3 * N_coarse) if N_coarse > 0 else 1e10

# 合成レート（初期レート）
k_initial = 1 / ((1 / k_dense) + (1 / k_coarse))
k_late = k_coarse

# 密巻きの物理的限界（隙間量）
L_solid_dense = (N_dense * d) + seat_dense
max_delta_dense = max(0.0, L_dense_free - L_solid_dense)

# 変化点の物理的算出（変位分配ロジック）
# 密巻きが最大まで縮む荷重 F = k_dense * max_delta_dense
# その時の全体のストローク S = max_delta_dense + (F / k_coarse)
total_delta_at_change = max_delta_dense + (k_dense * max_delta_dense) / k_coarse

# プリロード込のUI数値
S_change = max(0.0, total_delta_at_change - P)
F_change = k_initial * total_delta_at_change

# 全体の線間密着位置（サスペンション基準）
L_solid_total = (N_dense + N_coarse) * d + seat_dense + seat_coarse
S_max_total = max(0.0, L_free - L_solid_total)
S_max_stroke = max(0.0, S_max_total - P)

# --- 表示用計算 ---
is_single = (N_dense == 0) or (N_coarse == 0)

def calc_load(x):
    x_total = P + x  # 自由長からの総圧縮量
    if is_single or x_total <= total_delta_at_change:
        return k_initial * x_total
    else:
        # 変化点荷重 + (変化点以降の追加ストローク * 荒巻き単体レート)
        return F_change + k_late * (x_total - total_delta_at_change)

# 単位表示変換
k_initial_disp = k_initial / 9.80665 if unit == "kgf/mm" else k_initial
k_late_disp = k_late / 9.80665 if unit == "kgf/mm" else k_late
F_change_disp = F_change / 9.80665 if unit == "kgf/mm" else F_change

F_susp = calc_load(min(S_susp, S_max_stroke))
F_susp_disp = F_susp / 9.80665 if unit == "kgf/mm" else F_susp

gap_dense = ((L_dense_free - seat_dense) / N_dense) - d if N_dense > 0 else 0
gap_coarse = (((L_free - L_dense_free) - seat_coarse) / N_coarse) - d if N_coarse > 0 else 0

# --- UI出力 ---
st.divider()
st.header("④ 測定結果")

col1, col2 = st.columns(2)

with col1:
    st.metric("初期レート", f"{k_initial_disp:.2f} {unit}")
    st.metric("変化ポイント位置", f"{S_change:.1f} mm")
    st.metric("フルストローク量", f"{S_susp:.1f} mm")
    st.metric("密巻線間距離", f"{max(0.0, gap_dense):.2f} mm")

with col2:
    st.metric("後半レート", f"{k_late_disp:.2f} {unit}")
    st.metric("変化ポイント荷重", f"{F_change_disp:.1f} {load_unit}")
    st.metric("フルストローク時の荷重", f"{F_susp_disp:.1f} {load_unit}")
    st.metric("荒巻線間距離", f"{max(0.0, gap_coarse):.2f} mm")

st.metric("線間密着位置", f"{S_max_stroke:.1f} mm")

# --- グラフ描画 ---
x_plot = np.linspace(0, S_max_stroke, 400)
y_vals = np.array([calc_load(v) for v in x_plot])
if unit == "kgf/mm":
    y_vals = y_vals / 9.80665

fig = go.Figure()

mask = x_plot <= S_change
x1, y1 = x_plot[mask], y_vals[mask]
x2, y2 = x_plot[~mask], y_vals[~mask]

if len(x1) > 0:
    fig.add_trace(go.Scatter(x=x1, y=y1, mode='lines', name="初期レート", line=dict(color='blue', width=5)))

if len(x2) > 0:
    if len(x1) > 0:
        x2 = np.concatenate([[x1[-1]], x2])
        y2 = np.concatenate([[y1[-1]], y2])
    fig.add_trace(go.Scatter(x=x2, y=y2, mode='lines', name="後半レート", line=dict(color='orange', width=5)))

fig.add_vline(x=S_change, line_color="red", line_dash="dash")
fig.add_vline(x=S_susp, line_color="purple", line_dash="dash")
fig.add_vline(x=S_max_stroke, line_color="black", line_dash="dash")

# アノテーション
fig.add_annotation(
    x=S_change, y=F_change_disp,
    text=f"変化点 {S_change:.1f}mm\n{F_change_disp:.1f}{load_unit}",
    showarrow=True, arrowhead=2
)

fig.add_annotation(
    x=S_susp, y=F_susp_disp,
    text=f"フルストローク {S_susp:.1f}mm\n{F_susp_disp:.1f}{load_unit}",
    showarrow=True, arrowhead=2, ay=-40
)

fig.update_layout(template="simple_white", xaxis_title="ストローク (mm)", yaxis_title=f"荷重 ({load_unit})")

st.plotly_chart(fig, use_container_width=True)
st.caption("青：初期 / オレンジ：後半 / 赤：変化点 / 紫：フルストローク / 黒：線間密着")

# --- 予告セクション (エラー修正済み) ---
st.write("---")
st.subheader("次のシミュレーター（予告）")
ca, cb = st.columns(2)
with ca: st.button("▶ リアサスリンクシミュレーター（準備中）", key="f_link")
with cb: st.button("▶ エアバネ・油面調整シミュレーター（準備中）", key="f_air")
