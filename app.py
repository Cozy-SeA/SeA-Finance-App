import pandas as pd
import streamlit as st
import re
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from fpdf import FPDF
import base64

st.set_page_config(page_title="세아 가계 분석기", layout="wide")
st.title("토스 내역 자동 분류 & 공제 분석기")

total_income = st.number_input("세아의 총급여 입력 (연간)", min_value=1000000, value=42000000, step=1000000)
income_25 = total_income * 0.25
income_03 = total_income * 0.03

st.markdown(f"**카드/현금 공제 기준 (25%)**: {income_25:,.0f}원")
st.markdown(f"**의료비 공제 기준 (3%)**: {income_03:,.0f}원")

uploaded_file = st.file_uploader("토스 내역 CSV 업로드", type=["csv"])

def classify_category(merchant):
    keyword_map = {
        '병원': ['병원', '의원', '한의원', '치과'],
        '약국': ['약국', '약국입금'],
        '식비': ['편의점', 'CU', 'GS25', '이마트24', '배달', '맥도날드', '버거킹', '카페'],
        '교통': ['KTX', '버스', '지하철', '택시', '코레일'],
        '문화': ['영화', 'CGV', '롯데시네마', '예매', '전시', '서점'],
        '쇼핑': ['쿠팡', '마켓컬리', '무신사', 'G마켓', '위메프', '11번가'],
        '기타': []
    }
    for category, keywords in keyword_map.items():
        for keyword in keywords:
            if re.search(keyword, merchant):
                return category
    return '기타'

def tag_deduction(row):
    if row['분류'] in ['식비', '병원', '약국', '문화'] and row['결제수단'] in ['체크카드', '현금']:
        return 'O'
    else:
        return 'X'

def generate_pdf(card_cash, med, card_limit, med_limit):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="세아 재무 분석 리포트", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"카드/현금 공제 누적: {card_cash:,.0f}원 / 한도 {card_limit:,.0f}원", ln=True)
    pdf.cell(200, 10, txt=f"의료비 공제 누적: {med:,.0f}원 / 기준 {med_limit:,.0f}원", ln=True)
    if card_cash >= card_limit * 0.95:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(200, 10, txt=f"※ 공제 전환 시점 도달", ln=True)
    pdf.output("report.pdf")
    with open("report.pdf", "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    return base64_pdf

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    if '사용처' not in df.columns or '결제수단' not in df.columns or '금액' not in df.columns or '날짜' not in df.columns:
        st.error("[날짜, 사용처, 결제수단, 금액] 컬럼이 있어야 합니다. 토스 내보낸 원본 CSV를 사용해주세요.")
    else:
        df['날짜'] = pd.to_datetime(df['날짜'])
        df['월'] = df['날짜'].dt.to_period("M")
        df['분류'] = df['사용처'].apply(classify_category)
        df['공제 가능 여부'] = df.apply(tag_deduction, axis=1)

        total_card_cash = df[df['공제 가능 여부'] == 'O']['금액'].sum()
        total_medical = df[(df['분류'].isin(['병원', '약국'])) & (df['공제 가능 여부'] == 'O')]['금액'].sum()

        st.success("자동 분류 및 공제 태깅 완료!")

        st.subheader("[공제 분석 요약]")
        st.markdown(f"- 카드/현금 공제 누적: **{total_card_cash:,.0f}원** → {total_card_cash - income_25:,.0f}원 공제 대상")
        st.markdown(f"- 의료비 공제 누적: **{total_medical:,.0f}원** → {max(total_medical - income_03, 0):,.0f}원 공제 대상")

        if st.button("리포트 PDF 다운로드"):
            base64_pdf = generate_pdf(total_card_cash, total_medical, income_25, income_03)
            href = f'<a href="data:application/octet-stream;base64,{base64_pdf}" download="세아_재무_리포트.pdf">PDF 다운로드</a>'
            st.markdown(href, unsafe_allow_html=True)

        st.subheader("[이달의 소비 리포트 시각화]")
        top_categories = df.groupby('분류')['금액'].sum().sort_values(ascending=False).head(7)
        fig, ax = plt.subplots()
        sns.barplot(x=top_categories.index, y=top_categories.values, ax=ax)
        ax.set_ylabel("지출 금액")
        ax.set_xlabel("지출 분류")
        ax.set_title("이번 달 주요 지출 항목")
        st.pyplot(fig)
