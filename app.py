import streamlit as st
import numpy as np
import plotly.graph_objects as go

# =========================================================
# HEADER（凍結）
# =========================================================
st.set_page_config(page_title="ばねレート簡易判定ツール", layout="wide")

st.title("ばねレート簡易判定ツール")
st.caption("YouTubeチャンネル『こぼれ小話 タミケンバーン』連動ツール")
st.caption("※本ツールは診断ではなく、ばねの性格を概算数値で把握するためのものです")

st.markdown("▶ 使用方法解説動画（YouTube）  \nhttps://www.youtube.com/")
st.divider()

unit = st.radio("表示単位", ["N/mm", "kgf/mm"], horizontal=True)

# =========================================================
# INPUT（凍結）
# =========================================================
st.header("① 基本寸法")
d = st.number_input("線径 d [mm]", 0.0, value=3.8, step=0.1)
Do = st.number_input("外径 Do [mm]", 0.0, value=25.3, step=0.1)
L_free = st.number_input("自由長 L_free [mm]", 0.0, value=365.0, step=0.1)

st.header("② 巻数")
N_dense = st.number_input("密巻き数", 0.0, value=35.0, step=0.1)
N_coarse = st.number_input("荒巻き数", 0.0, value=21.5, step=0.1)
P = st.number_input("プリロード [mm]", 0.0, value=0.0, step=0.1)

st.header("③ 構造補足")
L_dense_free = st.number_input("密巻自由長 [mm]", 0.0, value=204.0, step=0.1)
seat_dense = st.number_input("座巻厚（密巻側）[mm]", 0.0, value=3.5, step=0.1)
seat_coarse = st.number_input("座巻厚（荒巻側）[mm]", 0.0, value=3.0, step=0.1)
S_susp = st.number_input("サスペンション最大ストローク量 [mm]", 0.0, value=97.0, step=0.1)

if st.button("計算開始"):

    # =========================================================
    # PHYSICS（凍結）
    # =========================================================
    G = 78500
    Dm = Do - d

    L_solid_dense = d * N_dense + seat_dense
    L_solid_total = d * (N_dense + N_coarse) + seat_dense + seat_coarse
    S_max = max(0, L_free - L_solid_total)

    is_single = (N_dense == 0) or (N_coarse == 0)

    if is_single:
        N_effective = N_dense if N_coarse == 0 else N_coarse
        k_initial = (G * d**4) / (8 * Dm**3 * N_effective)
        k_late = k_initial
        S_change = 0
    else:
        k_dense = (G * d**4) / (8 * Dm**3 * N_dense)
        k_coarse = (G * d**4) / (8 * Dm**3 * N_coarse)
        k_initial = 1 / ((1 / k_dense) + (1 / k_coarse))
        k_late = k_coarse
        S_change = max(0, L_dense_free - L_solid_dense - P)

    if unit == "kgf/mm":
        k_initial /= 9.80665
        k_late /= 9.80665

    def calc_load(x):
        x_real = P + x
        if is_single:
            return k_initial * x_real
        if x <= S_change:
            return k_initial * x_real
        return (k_initial * (P + S_change)) + k_late * (x - S_change)

    F_change = calc_load(S_change)
    F_susp = calc_load(min(S_susp, S_max))

    # 線間距離
    gap_dense = ((L_dense_free - seat_dense) / N_dense - d) if N_dense > 0 else None
    gap_coarse = (((L_free - L_dense_free) - seat_coarse) / N_coarse - d) if N_coarse > 0 else None

    # =========================================================
    # RESULT（凍結）
    # =========================================================
    st.divider()
    st.header("④ 測定結果")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("初期レート", f"{k_initial:.2f} {unit}")
        st.metric("変化ポイント位置", f"{S_change:.1f} mm")
        st.metric("フルストローク量", f"{S_susp:.1f} mm")
        if gap_dense is not None:
            st.metric("密巻線間距離", f"{gap_dense:.2f} mm")

    with col2:
        st.metric("後半レート", f"{k_late:.2f} {unit}")
        st.metric("変化ポイント荷重", f"{F_change:.1f} {unit}")
        st.metric("フルストローク時の荷重", f"{F_susp:.1f} {unit}")
        if gap_coarse is not None:
            st.metric("荒巻線間距離", f"{gap_coarse:.2f} mm")

    st.metric("線間密着位置", f"{S_max:.1f} mm")

    # =========================================================
    # GRAPH（凍結構造）
    # =========================================================
    x = np.linspace(0, S_max, 400)
    fig = go.Figure()

    if not is_single:
        x1 = x[x <= S_change]
        x2 = x[x >= S_change]

        fig.add_trace(go.Scatter(
            x=x1,
            y=[calc_load(v) for v in x1],
            mode='lines',
            line=dict(color='blue'),
            name=f'初期 {k_initial:.2f}'
        ))

        fig.add_trace(go.Scatter(
            x=x2,
            y=[calc_load(v) for v in x2],
            mode='lines',
            line=dict(color='orange'),
            name=f'後半 {k_late:.2f}'
        ))

    else:
        fig.add_trace(go.Scatter(
            x=x,
            y=[calc_load(v) for v in x],
            mode='lines',
            line=dict(color='blue'),
            name=f'レート {k_initial:.2f}'
        ))

    fig.add_vline(x=S_change, line_color="red", line_dash="dash")
    fig.add_vline(x=S_susp, line_color="purple", line_dash="dash")
    fig.add_vline(x=S_max, line_color="black", line_dash="dash")

    fig.add_annotation(
        x=S_change,
        y=F_change,
        text=f"変化点<br>{S_change:.1f} mm<br>{F_change:.1f} {unit}",
        showarrow=True,
        font=dict(size=15)
    )

    fig.add_annotation(
        x=S_susp,
        y=F_susp,
        text=f"フルストローク<br>{S_susp:.1f} mm<br>{F_susp:.1f} {unit}",
        showarrow=True,
        font=dict(size=15)
    )

    fig.update_layout(
        template="simple_white",
        xaxis_title="ストローク (mm)",
        yaxis_title=f"荷重 ({unit})",
        font=dict(size=15)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption("青：初期 / オレンジ：後半 / 赤：変化点 / 紫：フルストローク / 黒：線間密着")

# =========================================================
# FOOTER（凍結）
# =========================================================
st.divider()
st.subheader("次のシミュレーター")

col_a, col_b = st.columns(2)
with col_a:
    st.button("▶ ばねカットシミュレーター（準備中）")
with col_b:
    st.button("▶ エアばね・油面調整シミュレーター（準備中）")
