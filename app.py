import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="ばねレート簡易判定ツール", layout="wide")

# =========================
# ヘッダ（復元）
# =========================
st.title("ばねレート簡易判定ツール")
st.caption("YouTube『チャンネルこぼれ小話 タミケンバーン』連動ツール")
st.caption("※本ツールは診断ではなく、ばねの性格を概算数値で把握するためのものです")

st.markdown(
    "▶ 使用方法解説動画（YouTube）  \n"
    "https://www.youtube.com/"
)

# =========================
# スプリング名（スクショ用）
# =========================
spring_name = st.text_input("スプリング名（車種・年式・固有名詞など自由入力）")

st.divider()

# =========================
# 単位
# =========================
unit = st.radio("表示単位", ["N/mm", "kgf/mm"], horizontal=True)

# =========================
# 入力エリア
# =========================
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("基本寸法")
    d = st.number_input("線径 d [mm]", min_value=0.0, value=3.8, step=0.1)
    Do = st.number_input("外径 Do [mm]", min_value=0.0, value=25.4, step=0.1)
    L_free = st.number_input("自由長 L_free [mm]", min_value=0.0, value=370.0, step=0.1)

with col2:
    st.subheader("巻数")
    N_dense = st.number_input("密巻き数", min_value=0.0, value=35.0, step=0.1)
    N_coarse = st.number_input("荒巻き数", min_value=0.0, value=22.0, step=0.1)
    P = st.number_input("プリロード [mm]", min_value=0.0, value=0.0, step=0.1)

with col3:
    st.subheader("構造補足")
    L_dense_free = st.number_input("密巻自由長 [mm]", min_value=0.0, value=205.0, step=0.1)
    seat_dense = st.number_input("座巻厚（密巻側）[mm]", min_value=0.0, value=1.3, step=0.1)
    seat_coarse = st.number_input("座巻厚（荒巻側）[mm]", min_value=0.0, value=1.3, step=0.1)

# =========================
# 計算
# =========================
if st.button("計算開始"):

    G = 78500
    Dm = Do - d

    if Dm <= 0 or d <= 0:
        st.error("寸法入力が不正です。")
        st.stop()

    # 固体長
    L_solid_dense = d * N_dense + seat_dense
    L_solid_total = d * (N_dense + N_coarse) + seat_dense + seat_coarse
    S_max = max(0, L_free - L_solid_total)

    # シングル判定
    is_single = (N_dense == 0) or (N_coarse == 0)

    if is_single:
        N_effective = N_dense if N_coarse == 0 else N_coarse
        if N_effective == 0:
            st.error("有効巻数が0です。")
            st.stop()

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

    # =========================
    # 線間距離（座巻反映）
    # =========================
    gap_dense = None
    gap_coarse = None

    if N_dense > 0:
        effective_dense_length = max(0, L_dense_free - seat_dense)
        pitch_dense = effective_dense_length / N_dense
        gap_dense = pitch_dense - d

    if N_coarse > 0:
        effective_coarse_length = max(0, (L_free - L_dense_free) - seat_coarse)
        pitch_coarse = effective_coarse_length / N_coarse
        gap_coarse = pitch_coarse - d

    # =========================
    # 結果表示
    # =========================
    st.divider()
    st.header("計算結果")

    if spring_name:
        st.subheader(f"【{spring_name}】")

    r1, r2, r3 = st.columns(3)

    with r1:
        st.metric("初期レート", f"{k_initial:.2f} {unit}")
        st.metric("後半レート", f"{k_late:.2f} {unit}")

    with r2:
        st.metric("変化ポイント（密巻接触完了）", f"{S_change:.1f} mm")
        st.metric("最大可能ストローク（線間密着）", f"{S_max:.1f} mm")

    with r3:
        if gap_dense is not None:
            st.metric("密巻線間距離", f"{gap_dense:.2f} mm")
        if gap_coarse is not None:
            st.metric("荒巻線間距離", f"{gap_coarse:.2f} mm")

    st.caption("※線間距離が大きいほど比較的に復元スピードは高い傾向があります")

    # =========================
    # グラフ
    # =========================
    st.divider()
    st.subheader("ばね荷重特性")

    fig = go.Figure()

    if is_single:
        x = np.linspace(0, S_max, 300)
        y = k_initial * x
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines',
                                 name="レート",
                                 line=dict(color="blue")))
    else:
        x1 = np.linspace(0, S_change, 200)
        y1 = k_initial * x1
        fig.add_trace(go.Scatter(x=x1, y=y1, mode='lines',
                                 name="初期レート",
                                 line=dict(color="blue")))

        x2 = np.linspace(S_change, S_max, 200)
        y2 = (k_initial * S_change + k_late * (x2 - S_change))
        fig.add_trace(go.Scatter(x=x2, y=y2, mode='lines',
                                 name="後半レート",
                                 line=dict(color="orange")))

        fig.add_vline(x=S_change,
                      line_dash="dash",
                      line_color="red",
                      annotation_text="密巻接触完了")

    fig.add_vline(x=S_max,
                  line_dash="dash",
                  line_color="black",
                  annotation_text="線間密着")

    fig.update_layout(
        xaxis_title="ストローク (mm)",
        yaxis_title=f"荷重 ({unit})",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================
# 締め（復元）
# =========================
st.divider()
st.subheader("次のシミュレーター")

col_a, col_b = st.columns(2)

with col_a:
    st.button("▶ ばねカットシミュレーター（準備中）")

with col_b:
    st.button("▶ エアばね・油面調整シミュレーター（準備中）")
