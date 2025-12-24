import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# 1. 페이지 설정 및 한글 폰트 CSS 적용
st.set_page_config(page_title="🌱 극지식물 최적 EC 농도 연구", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@100;400;700&display=swap');
html, body, [class*="css"], .stMarkdown {
    font-family: 'Noto Sans KR', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# Plotly 한글 폰트 설정 (시스템 폰트 우선 순위)
FONT_SETTING = dict(family="Noto Sans KR, Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# 2. 데이터 로딩 함수 (NFC/NFD 호환 및 캐싱)
@st.cache_data
def load_data():
    data_path = Path("data")
    if not data_path.exists():
        st.error("❌ 'data' 폴더를 찾을 수 없습니다.")
        return None, None

    # 학교 정보 및 EC 매핑
    school_info = {
        "송도고": {"ec_target": 1.0, "color": "#AB63FA"},
        "하늘고": {"ec_target": 2.0, "color": "#00CC96"},
        "아라고": {"ec_target": 4.0, "color": "#FFA15A"},
        "동산고": {"ec_target": 8.0, "color": "#EF553B"}
    }

    env_data = {}
    growth_data = {}

    # 폴더 내 모든 파일 탐색 (NFC/NFD 대응)
    for file in data_path.iterdir():
        # 파일명을 NFC로 정규화하여 비교
        norm_name = unicodedata.normalize('NFC', file.name)
        
        # 1. 환경 데이터 (CSV)
        if norm_name.endswith('.csv'):
            for school in school_info.keys():
                if school in norm_name:
                    df = pd.read_csv(file)
                    df['time'] = pd.to_datetime(df['time'])
                    env_data[school] = df

        # 2. 생육 데이터 (XLSX)
        elif norm_name.endswith('.xlsx'):
            xls = pd.ExcelFile(file)
            for sheet_name in xls.sheet_names:
                norm_sheet = unicodedata.normalize('NFC', sheet_name)
                for school in school_info.keys():
                    if school in norm_sheet:
                        growth_data[school] = pd.read_excel(file, sheet_name=sheet_name)
    
    return env_data, growth_data, school_info

# 데이터 로드 실행
with st.spinner('데이터를 불러오는 중입니다...'):
    env_dict, growth_dict, info_dict = load_data()

if not env_dict or not growth_dict:
    st.error("데이터 파일이 부족하거나 파일명이 올바르지 않습니다. (NFC/NFD 체크 필요)")
    st.stop()

# --- 사이드바 ---
st.sidebar.header("🔍 필터 설정")
school_list = ["전체"] + list(info_dict.keys())
selected_school = st.sidebar.selectbox("학교 선택", school_list)

# 데이터 가공 (전체 또는 개별 학교)
if selected_school == "전체":
    display_env = pd.concat([df.assign(school=s) for s, df in env_dict.items()])
    display_growth = pd.concat([df.assign(school=s) for s, df in growth_dict.items()])
else:
    display_env = env_dict[selected_school].assign(school=selected_school)
    display_growth = growth_dict[selected_school].assign(school=selected_school)

# --- 메인 대시보드 ---
st.title("🌱 극지식물 최적 EC 농도 연구 대시보드")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# --- Tab 1: 실험 개요 ---
with tab1:
    st.subheader("연구 배경 및 목적")
    st.info("본 연구는 극지 식물의 생장 효율을 극대화하기 위한 최적의 전기전도도(EC) 농도를 분석합니다. "
            "4개 고등학교의 서로 다른 EC 조건에서 재배된 데이터를 비교 분석합니다.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 개체수", f"{len(display_growth)} 개")
    with col2:
        st.metric("평균 온도", f"{display_env['temperature'].mean():.1f} °C")
    with col3:
        st.metric("평균 습도", f"{display_env['humidity'].mean():.1f} %")
    with col4:
        st.metric("최적 EC (도출)", "2.0 (하늘고)")

    st.markdown("### 학교별 EC 설정 조건")
    summary_data = []
    for s, info in info_dict.items():
        summary_data.append({
            "학교명": s,
            "EC 목표": info['ec_target'],
            "개체수": len(growth_dict[s]),
            "색상": info['color']
        })
    st.table(pd.DataFrame(summary_data))

# --- Tab 2: 환경 데이터 ---
with tab2:
    st.subheader("학교별 환경 지표 비교")
    
    # 2x2 서브플롯 생성
    fig_env = make_subplots(rows=2, cols=2, 
                            subplot_titles=("평균 온도 (°C)", "평균 습도 (%)", "평균 pH", "목표 EC vs 실측 EC"))

    schools = list(info_dict.keys())
    avg_temp = [env_dict[s]['temperature'].mean() for s in schools]
    avg_hum = [env_dict[s]['humidity'].mean() for s in schools]
    avg_ph = [env_dict[s]['ph'].mean() for s in schools]
    target_ec = [info_dict[s]['ec_target'] for s in schools]
    actual_ec = [env_dict[s]['ec'].mean() for s in schools]

    fig_env.add_trace(go.Bar(x=schools, y=avg_temp, marker_color='orange', name="온도"), row=1, col=1)
    fig_env.add_trace(go.Bar(x=schools, y=avg_hum, marker_color='blue', name="습도"), row=1, col=2)
    fig_env.add_trace(go.Bar(x=schools, y=avg_ph, marker_color='green', name="pH"), row=2, col=1)
    
    fig_env.add_trace(go.Bar(x=schools, y=target_ec, name="목표 EC", marker_color='lightgrey'), row=2, col=2)
    fig_env.add_trace(go.Bar(x=schools, y=actual_ec, name="실측 EC", marker_color='darkblue'), row=2, col=2)

    fig_env.update_layout(height=700, font=FONT_SETTING, showlegend=False)
    st.plotly_chart(fig_env, use_container_width=True)

    if selected_school != "전체":
        st.subheader(f"📈 {selected_school} 시계열 변화")
        fig_line = make_subplots(specs=[[{"secondary_y": True}]])
        df_sel = env_dict[selected_school]
        
        fig_line.add_trace(go.Scatter(x=df_sel['time'], y=df_sel['temperature'], name="온도(°C)"), secondary_y=False)
        fig_line.add_trace(go.Scatter(x=df_sel['time'], y=df_sel['humidity'], name="습도(%)"), secondary_y=True)
        
        # EC 변화 및 목표선
        fig_ec = px.line(df_sel, x='time', y='ec', title=f"{selected_school} EC 변화")
        fig_ec.add_hline(y=info_dict[selected_school]['ec_target'], line_dash="dash", line_color="red", annotation_text="목표 EC")
        
        st.plotly_chart(fig_line, use_container_width=True)
        st.plotly_chart(fig_ec, use_container_width=True)

    with st.expander("📥 환경 데이터 원본 및 다운로드"):
        st.dataframe(display_env)
        csv = display_env.to_csv(index=False).encode('utf-8-sig')
        st.download_button("CSV 다운로드", csv, "env_data.csv", "text/csv")

# --- Tab 3: 생육 결과 ---
with tab3:
    # 핵심 결과 요약
    avg_weights = {s: df['생중량(g)'].mean() for s, df in growth_dict.items()}
    best_school = max(avg_weights, key=avg_weights.get)
    
    st.success(f"🥇 **분석 결과:** 최적 생육 EC는 **{info_dict[best_school]['ec_target']}** (학교: {best_school})이며, "
               f"평균 생중량은 **{avg_weights[best_school]:.2f}g**으로 가장 높게 나타났습니다.")

    # 2x2 생육 지표 비교
    fig_growth = make_subplots(rows=2, cols=2, 
                               subplot_titles=("평균 생중량(g) ⭐", "평균 잎 수(장)", "평균 지상부 길이(mm)", "실험 개체수"))

    names = list(info_dict.keys())
    weights = [growth_dict[s]['생중량(g)'].mean() for s in names]
    leaves = [growth_dict[s]['잎 수(장)'].mean() for s in names]
    heights = [growth_dict[s]['지상부 길이(mm)'].mean() for s in names]
    counts = [len(growth_dict[s]) for s in names]

    colors = [info_dict[s]['color'] for s in names]

    fig_growth.add_trace(go.Bar(x=names, y=weights, marker_color=colors), row=1, col=1)
    fig_growth.add_trace(go.Bar(x=names, y=leaves, marker_color=colors), row=1, col=2)
    fig_growth.add_trace(go.Bar(x=names, y=heights, marker_color=colors), row=2, col=1)
    fig_growth.add_trace(go.Bar(x=names, y=counts, marker_color='grey'), row=2, col=2)

    fig_growth.update_layout(height=800, font=FONT_SETTING, showlegend=False)
    st.plotly_chart(fig_growth, use_container_width=True)

    # 분포 및 상관관계
    col_left, col_right = st.columns(2)
    with col_left:
        fig_box = px.box(display_growth, x="school", y="생중량(g)", color="school", 
                         title="학교별 생중량 분포", color_discrete_map={s: info_dict[s]['color'] for s in info_dict})
        st.plotly_chart(fig_box, use_container_width=True)
    
    with col_right:
        fig_scatter = px.scatter(display_growth, x="지상부 길이(mm)", y="생중량(g)", color="school",
                                 title="지상부 길이와 생중량의 상관관계")
        st.plotly_chart(fig_scatter, use_container_width=True)

    with st.expander("📥 생육 데이터 원본 및 XLSX 다운로드"):
        st.dataframe(display_growth)
        
        # XLSX 다운로드 구현 (BytesIO 사용)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            display_growth.to_excel(writer, index=False, sheet_name='Sheet1')
        
        st.download_button(
            label="XLSX 다운로드",
            data=buffer.getvalue(),
            file_name="growth_data_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


