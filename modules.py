import re
import numpy as np
import pandas as pd
from datetime import datetime
import streamlit as st
# from typing import List, Tuple  # (파이썬 3.8/3.9 호환용 필요 시 주석 해제)

this_year = datetime.today().year
current_month = datetime.today().month

# ---------------------------------------------
# 공통 유틸 (사이드바/인덱스)
# ---------------------------------------------
def date_update_callback():
    st.session_state.year = st.session_state.year_selector
    st.session_state.month = st.session_state.month_selector

def create_sidebar():
    with st.sidebar:
        st.title("날짜 선택")
        if 'year' not in st.session_state:
            st.session_state.year = this_year
        if 'month' not in st.session_state:
            st.session_state.month = current_month

        st.selectbox(
            '년(Year)', range(2020, 2031),
            key='year_selector',
            index=st.session_state.year - 2020,
            on_change=date_update_callback
        )
        st.selectbox(
            '월(Month)', range(1, 13),
            key='month_selector',
            index=st.session_state.month - 1,
            on_change=date_update_callback
        )
        st.info(f"선택된 날짜: {st.session_state.year}년 {st.session_state.month}월")

def get_month_index(year, month):
    """
    year, month 기준으로 '최근 12개월'의 말일 인덱스를 안전하게 생성.
    12월 → 'YYYY-13' 문제 방지.
    """
    end = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)
    date_index = pd.date_range(end=end, periods=12, freq='M')
    return [f"{d.year % 100}년 {d.month}월" for d in date_index]

def get_year_mean_index(year):
    end_date = f"{year}-11"
    date_index = pd.date_range(end=end_date, periods=5, freq='Y')
    return [f"{date.year % 100}년 월평균" for date in date_index]

def get_year_end_index(year):
    end_date = f"{year}-11"
    date_index = pd.date_range(end=end_date, periods=5, freq='Y')
    return [f"{date.year % 100}년말" for date in date_index]

import re
import pandas as pd

def create_df(year, month, data, mean="True", prev_year=2, prev_month=4):
    # 1) 컬럼 인덱스 생성 ----------------------------------------------------
    months = get_month_index(year, month)  # 예: ['24년 11월', '24년 12월', '25년 1월', ...]
    years  = get_year_mean_index(year) if mean == "True" else get_year_end_index(year)
    columns = years[-prev_year:] + months[-prev_month:]

    # 2) 행 인덱스(구분1, 구분2 등) 생성 ------------------------------------
    categories = [col for col in data.columns if '구분' in col][-2:]
    index = data[categories].drop_duplicates()
    indexes = pd.MultiIndex.from_frame(index, names=['', ''])

    df = pd.DataFrame(0, index=indexes, columns=columns)
    n = len(df.index)   # df 행 개수

    # 3) 각 컬럼별로 data에서 값 채우기 -------------------------------------
    for col in df.columns:
        col_label = str(col)   # 혹시 숫자/튜플이어도 문자열로 처리

        # ---- 3-1. 컬럼에서 연도/월 정보 추출 --------------------------------
        col_year = None
        col_month = None
        is_mean_col = ('월평균' in col_label)
        is_yearend_col = ('년말' in col_label)

        # 컬럼 문자열에서 숫자만 뽑기 (예: "'24년말" -> ['24'], "2025년 1월" -> ['2025','1'])
        nums = re.findall(r'\d+', col_label)

        if is_mean_col or is_yearend_col:
            # 'xx년 월평균' 또는 'xx년말' 형식으로 가정
            if nums:
                yy = int(nums[0])
                if yy < 100:   # '24' -> 2024 식으로 처리
                    yy += 2000
                col_year = yy
            else:
                col_year = year  # 혹시 숫자가 없으면 선택연도 fallback

            col_month = 12 if is_yearend_col else None  # 연말만 12월 고정

        else:
            # 일반 월 컬럼 (예: '1월', '25년 1월', '2025-01' 등 숫자를 포함한다고 가정)
            if len(nums) == 0:
                # 숫자가 하나도 없으면 그냥 선택연도에, 월은 지정 불가 → values 없음 처리
                col_year = year
                col_month = None
            elif len(nums) == 1:
                # 숫자가 1개면 "월"이라고 보고, 연도는 선택연도 사용
                col_year = year
                col_month = int(nums[0])
            else:
                # 숫자가 2개 이상이면 앞쪽은 연도, 마지막은 월로 간주
                yy = int(nums[0])
                if yy < 100:
                    yy += 2000
                col_year = yy
                col_month = int(nums[-1])

        # ---- 3-2. data에서 해당 연도/월의 '실적' 값 가져오기 -------------------
        if is_mean_col:
            # 월평균 컬럼: data['월']에 '월평균' 이라고 저장되어 있다고 가정
            mask = (data['연도'] == col_year) & (data['월'] == '월평균')
            values = data.loc[mask, '실적'].values

        elif is_yearend_col:

            mask = (data['연도'] == col_year) & (data['월'] == '12월')
            values = data.loc[mask, '실적'].values

        else:
            # 일반 월 컬럼
            if col_month is None:
                values = []
            else:
                # data['월']이 "1월", "2월" 처럼 문자열이라고 가정
                month_label = f"{col_month}월"
                mask = (data['연도'] == col_year) & (data['월'] == month_label)
                # 만약 data['월']이 숫자(1,2,3...)라면 위 대신:
                # mask = (data['연도'] == col_year) & (data['월'] == col_month)
                values = data.loc[mask, '실적'].values

        # ---- 3-3. df 행 개수(n)에 맞게 안전하게 대입 ---------------------------
        if len(values) == 0:
            # 데이터가 하나도 없으면 전체를 0으로 (기본값 그대로)
            df.loc[:, col] = 0

        elif len(values) == 1:
            # 값이 하나면 모든 행에 동일 값을 브로드캐스트
            df.loc[:, col] = values[0]

        elif len(values) == n:
            # df 행 수와 딱 맞으면 그대로 넣기
            df.loc[:, col] = values

        else:
            # 길이가 애매하게 다르다면(2개, 5개 등): 잘라서/0으로 채워서 맞추기
            padded = list(values)[:n]
            if len(padded) < n:
                padded += [0] * (n - len(padded))
            df.loc[:, col] = padded

    return df

# --- 공통: 컬럼 세트 생성 유틸 ---
def _build_defect_cols(year:int, month:int) -> list[str]:
    prev = f"{str(year-1)[-2:]}년 월평균"
    target = f"{str(year)[-2:]}년 목표"
    months = [f"{m}월" for m in range(1, month+1)]
    return [prev, target] + months + ["합계", "월평균"]


# ---------------------------------------------
# 매출 집계표
# ---------------------------------------------
def create_report_form(year):
    outside_index = ['CHQ', 'CD', 'STS', 'BTB', 'PB', '기타', '합계']
    inside_index = ['금액', '중량']
    hier_index = pd.MultiIndex.from_product([outside_index, inside_index])
    hier_column = pd.MultiIndex.from_tuples([
        (' ', f"'{str(year)[-2:]}년 계획"), (' ', '전월'),
        ('당월', '계획'), ('당월', '실적'), ('당월', '계획대비'), ('당월', '전월대비'),
        ('당월누적', '계획'), ('당월누적', '실적'), ('당월누적', '계획대비')
    ])
    df = pd.DataFrame(0, index=hier_index, columns=hier_column)
    df = df.drop(index=[('기타', '중량')])
    return df

def update_report_form(year, month):
    df = create_report_form(year)
    file_name = st.secrets["sheets"]["f_30"]
    agg = pd.read_csv(file_name, thousands=',')
    agg.loc[agg['구분2'] == '금액', '실적'] /= 1_000_000
    agg.loc[agg['구분2'] == '중량', '실적'] /= 1_000
    agg['실적'] = round(agg['실적']).astype(float)

    end_date = f"{year}-{month}"
    date_index = pd.date_range(end=end_date, periods=6, freq='M')
    year_month_index = [f"{d.year} {d.month}" for d in date_index]

    # ✅ df에서 마지막 2줄(합계) 빼고, 나머지 index를 그대로 기준으로 사용
    target_index = df.index[:-2]

    def _fill_col(col_idx, temp):
        """groupby 결과를 df.index에 맞춰 reindex + fillna(0) 해서 넣는 헬퍼"""
        grouped = temp.groupby(['구분1', '구분2'])['실적'].sum()
        aligned = grouped.reindex(target_index).fillna(0)
        df.iloc[:-2, col_idx] = aligned.to_numpy()

    # ① 연간 계획
    temp = agg[(agg['연도'] == year) & (agg['구분3'] == '계획')]
    _fill_col(0, temp)

    # ② 최근월 실적 (year_month_index[-1])
    last_year, last_month = map(int, year_month_index[-1].split(" "))
    temp = agg[
        (agg['연도'] == last_year) &
        (agg['월'] == last_month) &
        (agg['구분3'] == '실적')
    ]
    _fill_col(1, temp)

    # ③ 당월 계획
    temp = agg[
        (agg['연도'] == year) &
        (agg['월'] == month) &
        (agg['구분3'] == '계획')
    ]
    _fill_col(2, temp)

    # ④ 당월 실적
    temp = agg[
        (agg['연도'] == year) &
        (agg['월'] == month) &
        (agg['구분3'] == '실적')
    ]
    _fill_col(3, temp)

    # ⑤ 누계 계획
    temp = agg[
        (agg['연도'] == year) &
        (agg['월'] <= month) &
        (agg['구분3'] == '계획')
    ]
    _fill_col(6, temp)

    # ⑥ 누계 실적
    temp = agg[
        (agg['연도'] == year) &
        (agg['월'] <= month) &
        (agg['구분3'] == '실적')
    ]
    _fill_col(7, temp)

    # ---- 여기부터는 원래 코드 로직 그대로 ----
    df.iloc[-2, :] = df.iloc[[0, 2, 4, 6, 8, 10]].sum()
    df.iloc[-1, :] = df.iloc[[1, 3, 5, 7, 9]].sum()

    row_1 = df.iloc[[0, 2, 4, 6, 8, 11]]
    row_2 = df.iloc[[1, 3, 5, 7, 9, 12]]
    new_df = round(((row_1.reset_index(drop=True) / row_2.reset_index(drop=True)) * 1000), 0)
    new_df.index = pd.MultiIndex.from_tuples(
        [('CHQ', '단가'), ('CD', '단가'), ('STS', '단가'),
         ('BTB', '단가'), ('PB', '단가'), ('합계', '단가')]
    )
    df = pd.concat([df, new_df])

    level1_order = ['CHQ', 'CD', 'STS', 'BTB', 'PB', '기타', '합계']
    level2_order = ['금액', '단가', '중량']
    df.index = pd.MultiIndex.from_arrays([
        pd.Categorical(df.index.get_level_values(0), categories=level1_order, ordered=True),
        pd.Categorical(df.index.get_level_values(1), categories=level2_order, ordered=True)
    ])
    df = df.sort_index()

    df.iloc[:, 4] = round(((df.iloc[:, 3] / df.iloc[:, 2]) - 1) * 100, 1)
    df.iloc[:, 4] = df.iloc[:, 4].apply(lambda x: f"{x}%")
    df.iloc[:, 5] = round(((df.iloc[:, 3] / df.iloc[:, 1]) - 1) * 100, 1)
    df.iloc[:, 5] = df.iloc[:, 5].apply(lambda x: f"{x}%")
    df.iloc[:, 8] = round(((df.iloc[:, 7] / df.iloc[:, 6]) - 1) * 100, 1)
    df.iloc[:, 8] = df.iloc[:, 8].apply(lambda x: f"{x}%")

    return df.fillna(0)


# ---------------------------------------------
# 등급별 판매구성
# ---------------------------------------------
def update_item_form(df):
    df.loc[('정상입고품', ''), :] = df.iloc[0, :] + df.iloc[1, :]
    df.loc[('정상입고품', '구성비'), :] = round(
        (df.loc[('정상입고품', '산업재 혹은 중국재'), :] / df.loc[('정상입고품', ''), :]) * 100, 1
    )
    df.loc[('합계', ''), :] = df.iloc[[0, 1, 2]].sum()
    df.loc[('B급', '구성비'), :] = round(
        (df.loc[('B급', ''), :] / df.loc[('합계', ''), :]) * 100, 1
    )

    df = df.rename(index={'정상입고품': '정품', '산업재 혹은 중국재': '산업/중국재'})
    sort_order = [
        ('정품', '정상'), ('정품', '산업/중국재'), ('정품', '구성비'), ('정품', ''),
        ('B급', ''), ('B급', '구성비'), ('합계', '')
    ]
    df = df.reindex(sort_order)

    df.loc[:, ('전월대비')] = df.iloc[:, 5] - df.iloc[:, 4]
    df.loc[:, ('%')] = (df.iloc[:, 6] / df.iloc[:, 4]) * 100
    df.loc[:, ('%')] = round(df.loc[:, ('%')].astype(float), 1).apply(lambda x: f"{x}%")
    df.loc[('정품', '구성비'), ('전월대비')] = round(df.loc[('정품', '구성비'), ('전월대비')], 2)
    df.loc[('B급', '구성비'), ('전월대비')] = round(df.loc[('B급', '구성비'), ('전월대비')], 2)
    df.loc[('정품', '구성비'), df.columns[:-1]] = df.loc[('정품', '구성비'), df.columns[:-1]].apply(lambda x: f"{x}%")
    df.loc[('B급', '구성비'), df.columns[:-1]] = df.loc[('B급', '구성비'), df.columns[:-1]].apply(lambda x: f"{x}%")
    df.loc[('정품', '구성비'), '%'] = ' '
    df.loc[('B급', '구성비'), '%'] = ' '
    df.index.names = [None, None]
    return df

# ---------------------------------------------
# PSI
# ---------------------------------------------
def create_psi_form(year, month):
    end = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(1)
    date_index = pd.date_range(end=end, periods=12, freq='M')
    index = [f"{d.year % 100}.{d.month}" for d in date_index]
    columns = ['원재료 입고①', '매출②', '총재고③', '출고율(②/①)', '재고율(③/②)']
    return pd.DataFrame(0, index=index, columns=columns)

import pandas as pd

def update_psi_form(year, month, data: pd.DataFrame):
    # 템플릿/형식은 기존 함수 그대로 사용
    df = create_psi_form(year, month)

    # ---- data 전처리: 연도/월 숫자로 통일 ----
    data = data.copy()
    data["연도"] = pd.to_numeric(data["연도"], errors="coerce")

    # '1월', '01월' 같은 형식 → '1', '01' → int
    data["월"] = (
        data["월"]
        .astype(str)
        .str.replace("월", "", regex=False)
    )
    data["월"] = pd.to_numeric(data["월"], errors="coerce")

    for idx in df.index:
        # index 형식이 '25.01' 또는 '25.1' 같은 걸로 가정
        part_y, part_m = idx.split(".")
        yy = 2000 + int(part_y)   # '25' -> 2025
        mm = int(part_m)          # '01' or '1' -> 1

        # 해당 연월 데이터 가져오기
        vals = data[(data["연도"] == yy) & (data["월"] == mm)]["실적"].tolist()

        # 기대하는 구조가 [매출, 출하, 재고]라면 최소 3개를 확보
        # 데이터 없으면 전부 0으로 채움
        if len(vals) == 0:
            a, b, c = 0, 0, 0
        else:
            # 부족한 값은 0으로 패딩
            while len(vals) < 3:
                vals.append(0)
            a, b, c = vals[0], vals[1], vals[2]

        # ship = 출하 / 매출
        ship = "0%" if a == 0 else f"{round((b / a) * 100, 1)}%"

        # invt = 재고 / 출하
        if b == 0:
            invt = "-"   # 출하가 0이면 재고 비율 의미 없음
        else:
            invt = f"{round((c / b) * 100, 1)}%"

        # df에 값 채우기
        df.loc[idx] = [a, b, c, ship, invt]

    return df


import pandas as pd

def update_psi_2_form(year, month, data: pd.DataFrame):
    df = create_psi_form(year, month)

    # ---- data 전처리: 연도/월 숫자로 통일 ----
    data = data.copy()
    data["연도"] = pd.to_numeric(data["연도"], errors="coerce")

    # '1월', '01월' 등 → '1', '01' → int
    data["월"] = (
        data["월"]
        .astype(str)
        .str.replace("월", "", regex=False)
    )
    data["월"] = pd.to_numeric(data["월"], errors="coerce")

    for idx in df.index:
        # index 형식이 '25.01' 또는 '25.1' 같은 걸로 가정
        part_y, part_m = idx.split(".")
        yy = 2000 + int(part_y)   # '25' -> 2025
        mm = int(part_m)          # '01' or '1' -> 1

        # 해당 연월 데이터 가져오기
        vals = data[(data["연도"] == yy) & (data["월"] == mm)]["실적"].tolist()

        # 기대하는 구조: [매출, 출하, 재고] 라고 가정하고 최소 3개 확보
        if len(vals) == 0:
            a, b, c = 0, 0, 0
        else:
            while len(vals) < 3:
                vals.append(0)
            a, b, c = vals[0], vals[1], vals[2]

        # ship = 출하 / 매출
        ship = "0%" if a == 0 else f"{round((b / a) * 100, 1)}%"

        # invt = 재고 / 출하
        if b == 0:
            invt = "-"   # 출하가 0이면 재고비율 의미 없으니 '-'
        else:
            invt = f"{round((c / b) * 100, 1)}%"

        # df에 값 채우기
        df.loc[idx] = [a, b, c, ship, invt]

    return df


# ---------------------------------------------
# 재고자산 회전율
# ---------------------------------------------
def create_turnover_form(year, month):
    index_tuples = [
        ('', '상품'), ('', '제품'), ('', '(중량)'),
        (' ', '재공품'), (' ', '(중량)'),
        ('  ', '원재료'), ('  ', '(중량)'),
        ('   ', '부재료'), ('   ', '미착재료'),
        ('재고자산계', ' '), ('(중량 계)', ' ')
    ]
    hier_index = pd.MultiIndex.from_tuples(index_tuples)

    months = get_month_index(year, month)
    y3 = "20" + months[-3].split(" ")[0]; m3 = months[-3].split(" ")[1]
    y2 = "20" + months[-2].split(" ")[0]; m2 = months[-2].split(" ")[1]
    y1 = "20" + months[-1].split(" ")[0]; m1 = months[-1].split(" ")[1]

    columns = pd.MultiIndex.from_tuples([
        (' ', f'{str(year - 2)[2:]}년말'),
        (' ', f'{str(year - 1)[2:]}년말'),
        (y3 , m3), (y2 , m2), (y1 , m1),
        ('전월대비', '증감'), ('전월대비', '증감률')
    ])
    return pd.DataFrame(0, index=hier_index, columns=columns)

def update_turnover_form(year, month):
    file_name = st.secrets['sheets']['f_50']
    turnover = pd.read_csv(file_name, thousands=',')
    turnover['실적'] = round(turnover['실적']).astype(float)
    df = create_turnover_form(year, month)

    for i in df.columns[:-2]:
        if '년말' in i[1]:
            yy = int('20' + i[1][:2])
            mm = 12
            temp = turnover[(turnover['연도'] == yy) & (turnover['월'] == mm)]
            vals = temp['실적'].values
            if len(vals) == 0:
                # 해당 연도/12월 데이터 없으면 그냥 0 유지
                continue
            df.iloc[:-2, df.columns.get_loc(i)] = vals
        else:
            yy = int(i[0].replace("년", ""))   # 예: '2026' → 2026
            mm = int(i[1].replace("월", ""))   # 예: '1월'  → 1
            temp = turnover[(turnover['연도'] == yy) & (turnover['월'] == mm)]
            vals = temp['실적'].values
            if len(vals) == 0:
                # 2026년처럼 아직 안 들어온 월이면 0 유지
                continue
            df.iloc[:-2, df.columns.get_loc(i)] = vals

    # 단위 변환 및 합계 계산 로직은 그대로
    for r in [1, 3, 5, 7, 8]:
        df.iloc[r, :] = round(df.iloc[r, :] / 1_000_000, 0)
        df.iloc[9, :] = df.iloc[9, :] + df.iloc[r, :]
    for r in [2, 4, 6]:
        df.iloc[r, :] = round(df.iloc[r, :] / 1_000, 0)
        df.iloc[10, :] = df.iloc[10, :] + df.iloc[r, :]

    df.loc[:, ('전월대비', '증감')] = (df.iloc[:, -3] - df.iloc[:, -4]).values
    df[('전월대비', '증감률')] = round((df.iloc[:, -2] / df.iloc[:, -4]) * 100, 1)
    df = df.fillna(0)
    df.iloc[:, -1] = df.iloc[:, -1].astype(object).apply(lambda x: f"{x}%")
    return df


# ---------------------------------------------
# 별첨 실적요약
# ---------------------------------------------
def create_performance_form(year, month):
    index = ['매출액', '판매량', '영업이익', '경상이익']
    months = get_month_index(year, month)
    return pd.DataFrame(index=index, columns=months[-5:])

def update_performance_form(year, month):
    all_dfs = {}
    file_name = st.secrets['sheets']['f_89']
    data = pd.read_csv(file_name)

    data['실적'] = data['실적'].str.replace(r'\(', '-', regex=True).str.replace(r'\)', '', regex=True)
    data['실적'] = data['실적'].str.replace(",", "").astype(int)
    data.loc[data['구분2'] != '판매량', '실적'] /= 1_000_000
    data.loc[data['구분2'] == '판매량', '실적'] /= 1_000

    for category in data['구분1'].unique():
        df = create_performance_form(year, month)

        for col in df.columns:
            yy = int("20" + col.split(" ")[0].replace("년", ""))
            mm = int(col.split(" ")[1].replace("월", ""))

            temp = data[
                (data['연도'] == yy) &
                (data['월'] == mm) &
                (data['구분1'] == category)
            ]

            if temp.empty:
                df.loc[:, col] = 0
            else:
                df.loc[:, col] = round(temp['실적'], 0).astype(int).to_list()

        # 영업이익률 계산
        sales = df.loc['매출액', :].replace(0, np.nan)  
        df.loc['영업이익률', :] = (df.loc['영업이익', :] / sales) * 100
        df.loc['영업이익률', :] = (
            df.loc['영업이익률', :]
            .astype(float)
            .round(1)
            .astype(str)
            + "%"
        )

        all_dfs[category] = df

    return all_dfs



def update_monthly_claim_form():
    file_name = st.secrets['sheets']['f_47']
    claim = pd.read_csv(file_name, thousands=',')

    # 단위 변환 (원 → 백만원 등)
    claim['실적'] = claim['실적'] / 1_000_000

    # 연도 숫자형
    claim['연도'] = pd.to_numeric(claim['연도'], errors='coerce')

    # 구분2 x 연도 피벗 (평균)
    pivot = (
        claim
        .groupby(['구분2', '연도'])['실적']
        .mean()
        .unstack('연도')            # index: 구분2, columns: 연도 (예: 2023, 2024, ...)
        .fillna(0)                 # 데이터 없는 연도/구분2는 0
    )

    return pivot



# =========================================================
# 생산: 전체 생산실적 (정렬 포함)
# =========================================================
def sort_board_like_item(df: pd.DataFrame) -> pd.DataFrame:
    """
    '등급별 판매현황'처럼 명확한 표시 순서를 강제.
    (그룹행과 공장행을 원하는 순서로 보여주기)
    """
    order = [
        ("", "포항"),
        ("", "충주"),
        ("CHQ", ""),
        ("", "포항"),
        ("", "충주2"),
        ("CD", ""),
        ("", "포항"),
        ("", "충주2"),
        ("STS", ""),
        ("BTB", ""),
        ("PB", ""),
        ("합계", ""),
        ("포항", ""),
        ("충주", ""),
        ("충주2", ""),
    ]
    names = list(df.index.names)
    target_idx = pd.MultiIndex.from_tuples(order, names=names)
    return df.reindex(target_idx)

def create_board_summary_table(year: int,
                               month: int,
                               data: pd.DataFrame,
                               base_year: int | None = None,
                               prev_year_for_avg: int | None = None) -> pd.DataFrame:
    if base_year is None:
        base_year = year
    if prev_year_for_avg is None:
        prev_year_for_avg = year - 1

    df = data.copy()

    # --- 기본 전처리 ---
    for c in ['구분1', '구분2', '구분3']:
        if c not in df.columns:
            df[c] = ''
        df[c] = df[c].fillna('').astype(str)

    # 실적 (톤 그대로)
    df['실적'] = pd.to_numeric(df.get('실적', 0), errors='coerce').fillna(0.0)

    # 연/월 캐스팅
    y_raw = df.get('연도', np.nan).astype(str).str.extract(r'(\d{4}|\d{2})')[0]
    def _to_year_int(v):
        if pd.isna(v): return np.nan
        s = str(v);   return 2000 + int(s) if len(s) == 2 else int(s)
    df['연도'] = y_raw.apply(_to_year_int)

    m_raw = (df.get('월', '')
               .astype(str).str.replace('월', '', regex=False)
               .str.replace('.', '', regex=False).str.strip())
    df['월'] = pd.to_numeric(m_raw, errors='coerce')

    df = df[df['연도'].between(1990, 2100) & df['월'].between(1, 12)]
    df['연도'] = df['연도'].astype(int)
    df['월'] = df['월'].astype(int)

    # 라벨 정규화
    def clean_text(s: str) -> str:
        s = str(s).replace('\xa0', ' ')
        s = re.sub(r'\s+', ' ', s).strip()
        return s
    df['구분1'] = df['구분1'].map(clean_text)
    df['구분2'] = df['구분2'].map(clean_text)

    def norm_group(x: str) -> str:
        s = x.lower()
        if 'chq' in s: return 'CHQ'
        if re.search(r'(^|\s)cd(\s|$)', s): return 'CD'
        if 'sts' in s: return 'STS'
        if 'btb' in s: return 'BTB'
        if re.search(r'(^|\s)pb(\s|$)', s): return 'PB'
        return x.strip().upper()

    def norm_plant(x: str) -> str:
        s = x.replace(' ', '').replace('공장', '')
        s = re.sub(r'[\(\[\{].*?[\)\]\}]', '', s).strip()
        if '포항' in s: return '포항'
        if ('충주' in s) and ('2' in s): return '충주2'
        if '충주2' in s: return '충주2'
        if '충주' in s: return '충주'
        return x.strip()

    df['G1'] = df['구분1'].map(norm_group)
    df['G2'] = df['구분2'].map(norm_plant)

    # 집계 dict (실적 우선, 없으면 전체 폴백)
    df_perf = df[df['구분3'].str.strip() == '실적']
    perf_detail = df_perf.groupby(['G1', 'G2', '연도', '월'])['실적'].sum().to_dict()
    perf_group  = df_perf.groupby(['G1', '연도', '월'])['실적'].sum().to_dict()
    perf_total  = df_perf.groupby(['연도', '월'])['실적'].sum().to_dict()
    perf_plant  = df_perf.groupby(['G2', '연도', '월'])['실적'].sum().to_dict()

    all_detail = df.groupby(['G1', 'G2', '연도', '월'])['실적'].sum().to_dict()
    all_group  = df.groupby(['G1', '연도', '월'])['실적'].sum().to_dict()
    all_total  = df.groupby(['연도', '월'])['실적'].sum().to_dict()
    all_plant  = df.groupby(['G2', '연도', '월'])['실적'].sum().to_dict()

    def _get_with_fallback(key, d_perf, d_all):
        return float(d_perf[key]) if key in d_perf else float(d_all.get(key, 0.0))

    def val(g, p, yy, mm):           return _get_with_fallback((g, p, yy, mm), perf_detail, all_detail)
    def group_val(g, yy, mm):        return _get_with_fallback((g, yy, mm),    perf_group,  all_group)
    def grand_val(yy, mm):           return _get_with_fallback((yy, mm),       perf_total,  all_total)
    def plant_total_val(p, yy, mm):  return _get_with_fallback((p, yy, mm),    perf_plant,  all_plant)

    def months_for_avg(yy: int):
        upper = month if (yy == base_year and base_year == year) else 12
        return range(1, upper + 1)

    def year_avg(row_key: tuple, yy: int):
        key_g, key_p, kind = row_key
        vals = []
        for mm in months_for_avg(yy):
            if kind == 'plant':         vals.append(val(key_g, key_p, yy, mm))
            elif kind == 'group':       vals.append(group_val(key_g, yy, mm))
            elif kind == 'grand':       vals.append(grand_val(yy, mm))
            elif kind == 'plant_total': vals.append(plant_total_val(key_g, yy, mm))
        arr = np.array(vals, dtype=float)
        return float(arr.mean()) if arr.size else 0.0

    group_order = ["CHQ", "CD", "STS", "BTB", "PB"]
    plants_map  = {"CHQ": ["포항", "충주"], "CD": ["포항", "충주2"], "STS": ["포항", "충주2"], "BTB": [], "PB": []}

    rows = []
    for g in group_order:
        for p in plants_map[g]:
            rows.append(("", p))
        rows.append((g, ""))
    rows += [("합계", ""), ("포항", ""), ("충주", ""), ("충주2", "")]
    index = pd.MultiIndex.from_tuples(rows, names=["구분", ""])

    cols = [f"'{str(prev_year_for_avg)[-2:]}년 월평균",
            f"'{str(base_year)[-2:]}년 월평균"] + \
           [f"'{str(base_year)[-2:]}.{m}" for m in range(1, int(month) + 1)] + \
           ["전월대비", "%"]
    out = pd.DataFrame(0.0, index=index, columns=cols)

    prev_y, prev_m = (year, month - 1) if month > 1 else (year - 1, 12)

    r = 0
    for g in group_order:
        for p in plants_map[g]:
            out.iloc[r, out.columns.get_loc(f"'{str(prev_year_for_avg)[-2:]}년 월평균")] = year_avg((g, p, "plant"), prev_year_for_avg)
            out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}년 월평균")]        = year_avg((g, p, "plant"), base_year)
            for mth in range(1, int(month) + 1):
                out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}.{mth}")] = val(g, p, base_year, mth)
            curr, prev = val(g, p, year, month), val(g, p, prev_y, prev_m)
            diff = curr - prev
            out.iloc[r, out.columns.get_loc("전월대비")] = diff
            out.iloc[r, out.columns.get_loc("%")] = (diff / prev * 100.0) if prev != 0 else 0.0
            r += 1

        out.iloc[r, out.columns.get_loc(f"'{str(prev_year_for_avg)[-2:]}년 월평균")] = year_avg((g, "", "group"), prev_year_for_avg)
        out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}년 월평균")]        = year_avg((g, "", "group"), base_year)
        for mth in range(1, int(month) + 1):
            out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}.{mth}")] = group_val(g, base_year, mth)
        curr, prev = group_val(g, year, month), group_val(g, prev_y, prev_m)
        diff = curr - prev
        out.iloc[r, out.columns.get_loc("전월대비")] = diff
        out.iloc[r, out.columns.get_loc("%")] = (diff / prev * 100.0) if prev != 0 else 0.0
        r += 1

    out.iloc[r, out.columns.get_loc(f"'{str(prev_year_for_avg)[-2:]}년 월평균")] = year_avg(("합계", "", "grand"), prev_year_for_avg)
    out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}년 월평균")]        = year_avg(("합계", "", "grand"), base_year)
    for mth in range(1, int(month) + 1):
        out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}.{mth}")] = grand_val(base_year, mth)
    curr, prev = grand_val(year, month), grand_val(prev_y, prev_m)
    diff = curr - prev
    out.iloc[r, out.columns.get_loc("전월대비")] = diff
    out.iloc[r, out.columns.get_loc("%")] = (diff / prev * 100.0) if prev != 0 else 0.0
    r += 1

    for plant_total in ["포항", "충주", "충주2"]:
        out.iloc[r, out.columns.get_loc(f"'{str(prev_year_for_avg)[-2:]}년 월평균")] = year_avg((plant_total, "", "plant_total"), prev_year_for_avg)
        out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}년 월평균")]        = year_avg((plant_total, "", "plant_total"), base_year)
        for mth in range(1, int(month) + 1):
            out.iloc[r, out.columns.get_loc(f"'{str(base_year)[-2:]}.{mth}")] = plant_total_val(plant_total, base_year, mth)
        curr, prev = plant_total_val(plant_total, year, month), plant_total_val(plant_total, prev_y, prev_m)
        diff = curr - prev
        out.iloc[r, out.columns.get_loc("전월대비")] = diff
        out.iloc[r, out.columns.get_loc("%")] = (diff / prev * 100.0) if prev != 0 else 0.0
        r += 1

    # 숫자형 정리
    num_cols = [c for c in out.columns if c != "%"]
    out[num_cols] = out[num_cols].round(0).astype(int)
    out["%"] = out["%"].astype(float)

    # === 표시 순서 강제 ===
    out = sort_board_like_item(out)

    return out

# =========================
# 부적합(포항) 요약 테이블
# =========================

# --- 공통: 순서 강제 유틸 ---
def order_like(df: pd.DataFrame, order: list[tuple]) -> pd.DataFrame:
    """
    df.index가 MultiIndex일 때, order에 적힌 튜플 순서대로 정렬.
    order에 없는 나머지 행은 기존 순서를 유지한 채 뒤에 붙인다.
    """
    if not isinstance(df.index, pd.MultiIndex):
        return df
    cur = list(df.index)
    seen = set()
    head = [t for t in order if t in cur and not (t in seen or seen.add(t))]
    tail = [t for t in cur if t not in set(head)]
    return df.reindex(head + tail)

# # 반올림
# return out.round(0)


def _build_defect_cols1(year: int, month: int) -> list[str]:
    prev   = f"{str(year-1)[-2:]}년 월평균"
    target = f"{str(year)[-2:]}년 목표"
    # ← 월에 '월' 글자 안 붙임
    months = [f"'{str(year)[-2:]}.{m}" for m in range(1, month+1)]
    return [prev, target] + months + ["합계", "월평균"]


def create_defect_summary_pohang(
    year: int,
    month: int,
    data: pd.DataFrame,
    months_window: tuple | None = None,
    plant_name: str = "포항"
) -> pd.DataFrame:
    """
    멀티인덱스(상/중/구분) 구조, 컬럼은 항상:
    [전년 월평균, 당년 목표, 1~선택월, 합계, 월평균]
    """
    df = data.copy()

    # ---------- Type Conversion/Normalization ----------
    for c in ['연도', '월', '실적']:
        df[c] = pd.to_numeric(df.get(c), errors='coerce')
    for c in ['구분1', '구분2', '구분3', '구분4']:
        if c not in df.columns:
            df[c] = ''
        df[c] = df[c].fillna('').astype(str)

    # Filter for the target plant only
    df = df[df['구분1'].str.contains(plant_name)]
    prev_year = year - 1
    if months_window is None:
        months_window = tuple(range(1, month + 1))
    mlist = list(months_window)

    # ---------- Safe Sum/Mean Functions ----------
    safe_sum = lambda s: float(np.nansum(s)) if len(s) else 0.0
    safe_mean = lambda s: float(np.nanmean(s)) if len(s) else 0.0

    # ---------- Aggregation Helper ----------
    def pick(g2=None, g3=None, yy=None, mm=None, only_target=False):
        q = df
        if only_target:
            q = q[q['구분4'] == '목표']
        if g2 is not None:
            q = q[q['구분2'] == g2]
        if g3 is not None:
            q = q[q['구분3'] == g3]
        if yy is not None:
            q = q[q['연도'] == yy]
        if mm is not None:
            q = q[q['월'] == mm]
        return safe_sum(q['실적'])

    # ---------- Define Index/Columns (Internal level names are unique) ----------
    rows = [
        ('', '', '공정성'), ('', '', '소재성'), ('', 'CHQ', ''),
        ('', ' ', '공정성'), ('', ' ', '소재성'), ('', 'CD', ''),
        ('', '공정성', ''), ('', '소재성', ''), ('포항', '', ''),
    ]
    index = pd.MultiIndex.from_tuples(rows, names=['상', '중', '구분'])

    cols = _build_defect_cols1(year, month)
    prev_col, goal_col = cols[0], cols[1]
    month_cols = cols[2:-2]     

    col_prev_avg = cols[0]
    col_target = cols[1]

    out = pd.DataFrame(0.0, index=index, columns=cols)

    # ---------- ① Previous Year Monthly Average ----------
    # CHQ
    chq_prev_ps = [pick(g2='CHQ', g3='공정성', yy=prev_year, mm=m) for m in range(1, 13)]
    chq_prev_ms = [pick(g2='CHQ', g3='소재성', yy=prev_year, mm=m) for m in range(1, 13)]
    out.loc[('', '', '공정성'), col_prev_avg] = safe_mean(chq_prev_ps)
    out.loc[('', '', '소재성'), col_prev_avg] = safe_mean(chq_prev_ms)
    out.loc[('', 'CHQ', ''), col_prev_avg] = safe_mean([a + b for a, b in zip(chq_prev_ps, chq_prev_ms)])

    # CD (Mid-level ' ' block)
    cd_prev_ps = [pick(g2='CD', g3='공정성', yy=prev_year, mm=m) for m in range(1, 13)]
    cd_prev_ms = [pick(g2='CD', g3='소재성', yy=prev_year, mm=m) for m in range(1, 13)]
    out.loc[('', ' ', '공정성'), col_prev_avg] = safe_mean(cd_prev_ps)
    out.loc[('', ' ', '소재성'), col_prev_avg] = safe_mean(cd_prev_ms)
    out.loc[('', 'CD', ''), col_prev_avg] = safe_mean([a + b for a, b in zip(cd_prev_ps, cd_prev_ms)])

    # Total/Pohang
    ps_all_prev = [pick(g3='공정성', yy=prev_year, mm=m) for m in range(1, 13)]
    ms_all_prev = [pick(g3='소재성', yy=prev_year, mm=m) for m in range(1, 13)]
    out.loc[('', '공정성', ''), col_prev_avg] = safe_mean(ps_all_prev)
    out.loc[('', '소재성', ''), col_prev_avg] = safe_mean(ms_all_prev)
    out.loc[('포항', '', ''), col_prev_avg] = safe_mean([ps_all_prev[i] + ms_all_prev[i] for i in range(12)])

    # ---------- ② Current Year Target (0 if not available) ----------
    out.loc[:, col_target] = 0.0

    # ---------- ③ Selected Months/Sum/Monthly Average ----------
    # CHQ
    chq_ps = [pick(g2='CHQ', g3='공정성', yy=year, mm=m) for m in mlist]
    chq_ms = [pick(g2='CHQ', g3='소재성', yy=year, mm=m) for m in mlist]
    out.loc[('', '', '공정성'), month_cols] = chq_ps
    out.loc[('', '', '소재성'), month_cols] = chq_ms
    out.loc[('', '', '공정성'), ['합계', '월평균']] = [safe_sum(chq_ps), safe_mean(chq_ps)]
    out.loc[('', '', '소재성'), ['합계', '월평균']] = [safe_sum(chq_ms), safe_mean(chq_ms)]
    out.loc[('', 'CHQ', ''), month_cols] = [chq_ps[i] + chq_ms[i] for i in range(len(mlist))]
    out.loc[('', 'CHQ', ''), ['합계', '월평균']] = [
        safe_sum(out.loc[('', 'CHQ', ''), month_cols]),
        safe_mean(out.loc[('', 'CHQ', ''), month_cols]),
    ]

    # CD
    cd_ps = [pick(g2='CD', g3='공정성', yy=year, mm=m) for m in mlist]
    cd_ms = [pick(g2='CD', g3='소재성', yy=year, mm=m) for m in mlist]
    out.loc[('', ' ', '공정성'), month_cols] = cd_ps
    out.loc[('', ' ', '소재성'), month_cols] = cd_ms
    out.loc[('', ' ', '공정성'), ['합계', '월평균']] = [safe_sum(cd_ps), safe_mean(cd_ps)]
    out.loc[('', ' ', '소재성'), ['합계', '월평균']] = [safe_sum(cd_ms), safe_mean(cd_ms)]
    out.loc[('', 'CD', ''), month_cols] = [cd_ps[i] + cd_ms[i] for i in range(len(mlist))]
    out.loc[('', 'CD', ''), ['합계', '월평균']] = [
        safe_sum(out.loc[('', 'CD', ''), month_cols]),
        safe_mean(out.loc[('', 'CD', ''), month_cols]),
    ]

    # Total Process/Material + Pohang Grand Total
    ps_all = [pick(g3='공정성', yy=year, mm=m) for m in mlist]
    ms_all = [pick(g3='소재성', yy=year, mm=m) for m in mlist]
    out.loc[('', '공정성', ''), month_cols] = ps_all
    out.loc[('', '소재성', ''), month_cols] = ms_all
    out.loc[('', '공정성', ''), ['합계', '월평균']] = [safe_sum(ps_all), safe_mean(ps_all)]
    out.loc[('', '소재성', ''), ['합계', '월평균']] = [safe_sum(ms_all), safe_mean(ms_all)]
    total = [ps_all[i] + ms_all[i] for i in range(len(mlist))]
    out.loc[('포항', '', ''), month_cols] = total
    out.loc[('포항', '', ''), ['합계', '월평균']] = [safe_sum(total), safe_mean(total)]

    # Ensure no missing columns/correct order
    out = out.reindex(columns=cols, fill_value=0).round(0)

    return out

# =========================
# 부적합(충주) 요약 테이블
# =========================

def create_defect_summary_chungju(
        year:int,
        month:int,
        data:pd.DataFrame,
        months_window:tuple,
        plant1_name:str="충주",      # 충주1공장
        plant2_name:str="충주2"      # 충주2공장 (CD만)
    ) -> pd.DataFrame:

        df = data.copy()

        # 숫자/문자 정리
        for c in ['연도','월','실적']:
            df[c] = pd.to_numeric(df.get(c), errors='coerce')
        for c in ['구분1','구분2','구분3','구분4']:
            if c not in df.columns: df[c] = ''
            df[c] = df[c].fillna('').astype(str)

        prev_year = year - 1
        mlist = list(months_window)

        # 안전 합/평균
        safe_sum  = lambda s: float(np.nansum(s))  if len(s) else 0.0
        safe_mean = lambda s: float(np.nanmean(s)) if len(s) else 0.0

        # 필터/집계
        def pick(plant=None, g2=None, cause=None, yy=None, mm=None, only_target=False):
            q = df.copy()
            if plant is not None:
                q = q[q['구분1'].str.contains(plant)]
            if only_target:
                q = q[q['구분4'] == '목표']
            if g2 is not None:
                q = q[q['구분2'] == g2]
            if cause is not None:
                q = q[q['구분3'] == cause]
            if yy is not None:
                q = q[q['연도'] == yy]
            if mm is not None:
                q = q[q['월'] == mm]
            return safe_sum(q['실적'])

        # ── 인덱스(9행) ──
        rows = [
            ('',   '',  '공정성'),
            ('',   '',  '소재성'),
            ('',  '충주1공장(CHQ)', ''),
            ('',   '',  '공정성'),
            ('',   '',  '소재성'),
            ('',   '충주2공장',      ''),
            ('','공정성',  ''),
            ('','소재성',  ''),
            ('충주','',    ''),
        ]
        index = pd.MultiIndex.from_tuples(rows, names=['상','중','하'])

        month_cols = [f"'{str(year)[-2:]}.{m}" for m in mlist]

        col_prev_avg = f"{str(prev_year)[-2:]}년 월평균"
        col_target   = f"{str(year)[-2:]}년 목표"
        cols         = [col_prev_avg, col_target] + month_cols + ['합계','월평균']

        out = pd.DataFrame(0.0, index=index, columns=cols)

        # ---------- 전년 월평균 ----------
        # 충주1 CHQ (0,1,2)
        cj1_prev_ps = [pick(plant=plant1_name, g2='CHQ', cause='공정성', yy=prev_year, mm=m) for m in range(1,13)]
        cj1_prev_ms = [pick(plant=plant1_name, g2='CHQ', cause='소재성', yy=prev_year, mm=m) for m in range(1,13)]
        out.iloc[0, out.columns.get_loc(col_prev_avg)] = safe_mean(cj1_prev_ps)
        out.iloc[1, out.columns.get_loc(col_prev_avg)] = safe_mean(cj1_prev_ms)
        out.iloc[2, out.columns.get_loc(col_prev_avg)] = safe_mean([a+b for a,b in zip(cj1_prev_ps, cj1_prev_ms)])

        # 충주2 CD (3,4,5)
        cj2_prev_ps_cd = [pick(plant=plant2_name, g2='마봉강', cause='공정성', yy=prev_year, mm=m) for m in range(1,13)]
        cj2_prev_ms_cd = [pick(plant=plant2_name, g2='마봉강', cause='소재성', yy=prev_year, mm=m) for m in range(1,13)]
        out.iloc[3, out.columns.get_loc(col_prev_avg)] = safe_mean(cj2_prev_ps_cd)
        out.iloc[4, out.columns.get_loc(col_prev_avg)] = safe_mean(cj2_prev_ms_cd)
        out.iloc[5, out.columns.get_loc(col_prev_avg)] = safe_mean([a+b for a,b in zip(cj2_prev_ps_cd, cj2_prev_ms_cd)])

        # 전체 공정성/소재성/충주 총계 (6~8)
        chungju_mask = df['구분1'].str.contains(plant1_name) | df['구분1'].str.contains(plant2_name)
        def pick_chungju_total(yy, mm):
            q = df[(df['연도']==yy)&(df['월']==mm)&chungju_mask]
            return safe_sum(q['실적'])

        all_prev_ps = [pick(plant=None, g2=None, cause='공정성', yy=prev_year, mm=m) for m in range(1,13)]
        all_prev_ms = [pick(plant=None, g2=None, cause='소재성', yy=prev_year, mm=m) for m in range(1,13)]
        chungju_prev = [pick_chungju_total(prev_year, m) for m in range(1,13)]

        out.iloc[6, out.columns.get_loc(col_prev_avg)] = safe_mean(all_prev_ps)
        out.iloc[7, out.columns.get_loc(col_prev_avg)] = safe_mean(all_prev_ms)
        out.iloc[8, out.columns.get_loc(col_prev_avg)] = safe_mean(chungju_prev)

        # ---------- 목표(없으면 0) ----------
        out.loc[:, col_target] = 0.0

        # ---------- 당해 선택월 ----------
        # 충주1 CHQ (0~2)
        cj1_ps = [pick(plant=plant1_name, g2='CHQ', cause='공정성', yy=year, mm=m) for m in mlist]
        cj1_ms = [pick(plant=plant1_name, g2='CHQ', cause='소재성', yy=year, mm=m) for m in mlist]
        out.iloc[0, out.columns.get_indexer(month_cols)] = cj1_ps
        out.iloc[1, out.columns.get_indexer(month_cols)] = cj1_ms
        out.iloc[2, out.columns.get_indexer(month_cols)] = [cj1_ps[i]+cj1_ms[i] for i in range(len(mlist))]
        out.iloc[0, out.columns.get_indexer(['합계','월평균'])] = [safe_sum(cj1_ps), safe_mean(cj1_ps)]
        out.iloc[1, out.columns.get_indexer(['합계','월평균'])] = [safe_sum(cj1_ms), safe_mean(cj1_ms)]
        out.iloc[2, out.columns.get_indexer(['합계','월평균'])] = [
            safe_sum(out.iloc[2, out.columns.get_indexer(month_cols)]),
            safe_mean(out.iloc[2, out.columns.get_indexer(month_cols)]),
        ]

        # 충주2 CD (3~5)
        cj2_ps_cd = [pick(plant=plant2_name, g2='마봉강', cause='공정성', yy=year, mm=m) for m in mlist]
        cj2_ms_cd = [pick(plant=plant2_name, g2='마봉강', cause='소재성', yy=year, mm=m) for m in mlist]
        out.iloc[3, out.columns.get_indexer(month_cols)] = cj2_ps_cd
        out.iloc[4, out.columns.get_indexer(month_cols)] = cj2_ms_cd
        out.iloc[5, out.columns.get_indexer(month_cols)] = [cj2_ps_cd[i]+cj2_ms_cd[i] for i in range(len(mlist))]
        out.iloc[3, out.columns.get_indexer(['합계','월평균'])] = [safe_sum(cj2_ps_cd), safe_mean(cj2_ps_cd)]
        out.iloc[4, out.columns.get_indexer(['합계','월평균'])] = [safe_sum(cj2_ms_cd), safe_mean(cj2_ms_cd)]
        out.iloc[5, out.columns.get_indexer(['합계','월평균'])] = [
            safe_sum(out.iloc[5, out.columns.get_indexer(month_cols)]),
            safe_mean(out.iloc[5, out.columns.get_indexer(month_cols)]),
        ]

        # 전체 공정성/소재성/충주 총계 (6~8)
        ps_all = [pick(plant=None, g2=None, cause='공정성', yy=year, mm=m) for m in mlist]
        ms_all = [pick(plant=None, g2=None, cause='소재성', yy=year, mm=m) for m in mlist]
        chungju_total = [pick_chungju_total(year, m) for m in mlist]

        out.iloc[6, out.columns.get_indexer(month_cols)] = ps_all
        out.iloc[7, out.columns.get_indexer(month_cols)] = ms_all
        out.iloc[8, out.columns.get_indexer(month_cols)] = chungju_total

        for ridx in [6, 7, 8]:
            vals = out.iloc[ridx, out.columns.get_indexer(month_cols)].to_list()
            out.iloc[ridx, out.columns.get_indexer(['합계','월평균'])] = [safe_sum(vals), safe_mean(vals)]

        return out.round(0)


    # ---------------------------------------------
    # 표시 포맷(렌더용)
    # ---------------------------------------------
def format_total_production_table_for_display(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        def fmt_int(x):
            try: return f"{int(x):,}"
            except Exception: return x

        def fmt_diff(x):
            try:
                xi = int(round(float(x)))
                return f"({abs(xi):,})" if xi < 0 else f"{xi:,}"
            except Exception:
                return x

        def fmt_pct(x):
            try: return f"{float(x):.1f}%"
            except Exception: return x

        for c in df.columns:
            if c == "전월대비": df[c] = df[c].apply(fmt_diff)
            elif c == "%":     df[c] = df[c].apply(fmt_pct)
            else:              df[c] = df[c].apply(fmt_int)

        return df.reset_index()


####### 비용분석


########################
##사용량 원단위 추이 포항##
########################

import pandas as pd
import numpy as np

def create_material_usage_table_pohang(
    year: int,
    month: int,                 # 기준 연/월 (this_year, current_month)
    data: pd.DataFrame,
    window: int = 12,           # 몇 개월을 볼지(기본 12개월)
    plant_name: str = "포항",
    item_order: list[str] | None = None,
    round_digits: int = 6,
) -> pd.DataFrame:
    """
    [롱포맷 전용 롤링 12개월 테이블]
    - 필요한 컬럼: 구분3(공장), 구분1(항목), 월, 실적  (+ 선택: 연도)
    - 기준 연/월(year, month)을 포함하여 과거 window-1개월까지의 데이터 사용
      (예: year=2025, month=8, window=12 → 2024-09 ~ 2025-08)
    - 연도 컬럼이 있으면 연/월 기준으로 12개월 롤링, 없으면 같은 연도 내에서만 처리
    - **선택연월 기준 window개월에 데이터가 하나도 없으면**
      → item_order 기준 행 + 12개월 열 구조는 그대로, 값은 전부 '-' 로 채움
    """
    required = ["구분3", "구분1", "월", "실적"]
    df = data.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing} (필요: {required})")

    # item_order 기본값
    if item_order is None:
        item_order = ["열처리用LNG(㎥)", "질소(㎥)", "염산(kg)", "수소(㎥)", "산세용LNG(㎥)", "피막보급제(kg)"]

    # 1) 공장 필터
    q = df[df["구분3"].astype(str).str.contains(plant_name, na=False)].copy()

    # 2) 숫자화
    q["월"] = pd.to_numeric(q["월"], errors="coerce")
    q["실적"] = pd.to_numeric(q["실적"], errors="coerce")

    # 전체 기간에 데이터가 없을 때를 구분하기 위한 플래그
    no_data_all = False

    # ==============================
    # A. 연도 컬럼이 있는 경우: 연/월 기준 '진짜' 12개월 롤링
    # ==============================
    if "연도" in q.columns:
        q["연도"] = pd.to_numeric(q["연도"], errors="coerce")

        # 유효한 연/월만 사용
        q = q[q["연도"].notna() & q["월"].notna()].copy()

        # 연월 키(0-based): year*12 + (month-1)
        q["ym_key"] = (q["연도"].astype(int) * 12) + (q["월"].astype(int) - 1)

        end_key = int(year) * 12 + (int(month) - 1)
        start_key = end_key - (window - 1)

        # 범위 필터
        q = q[(q["ym_key"] >= start_key) & (q["ym_key"] <= end_key)].copy()

        full_keys = list(range(start_key, end_key + 1))

        if q.empty:
            # ★ 12개월 전체에 데이터가 1건도 없는 경우 → '-' 템플릿
            no_data_all = True

            col_labels = []
            for k in full_keys:
                y_ = k // 12
                m_ = (k % 12) + 1
                yy = str(int(y_))[-2:]
                col_labels.append(f"{yy}.{m_:02d}")

            piv = pd.DataFrame('-', index=item_order, columns=col_labels)
        else:
            # 피벗: 컬럼 = ym_key
            piv = q.pivot_table(index="구분1", columns="ym_key", values="실적", aggfunc="sum")

            # 전체 12개월 키 생성 (데이터 없으면 NaN 컬럼으로 채움)
            for k in full_keys:
                if k not in piv.columns:
                    piv[k] = np.nan
            piv = piv[full_keys]

            # 컬럼 라벨을 "YY.MM" 형식으로 변환 (예: 2024-09 → "24.09")
            new_cols = []
            for k in full_keys:
                y_ = k // 12
                m_ = (k % 12) + 1
                yy = str(int(y_))[-2:]
                new_cols.append(f"{yy}.{m_:02d}")
            piv.columns = new_cols

    # ==============================
    # B. 연도 컬럼이 없는 경우: 같은 연도 내에서만 롤링 (fallback)
    # ==============================
    else:
        # 유효한 월만
        q = q[q["월"].notna()].copy()

        # month 기준 window개월 전 ~ month까지 (1~12 범위 안에서만)
        start_month = max(1, int(month) - (window - 1))
        end_month = int(month)
        months_range = list(range(start_month, end_month + 1))

        q = q[q["월"].isin(months_range)].copy()

        if q.empty:
            # ★ 12개월 전체에 데이터가 1건도 없는 경우 → '-' 템플릿
            no_data_all = True
            col_labels = [f"{m}월" for m in months_range]
            piv = pd.DataFrame('-', index=item_order, columns=col_labels)
        else:
            piv = q.pivot_table(index="구분1", columns="월", values="실적", aggfunc="sum")

            # 누락 월 NaN 추가 + 정렬
            for m in months_range:
                if m not in piv.columns:
                    piv[m] = np.nan
            piv = piv[months_range]

            # "n월" 라벨 사용
            piv.columns = [f"{m}월" for m in months_range]

    # ==============================
    # C. 행 순서 정리 + 반올림
    # ==============================
    if no_data_all:
        # 전체 구간 무데이터 → 이미 piv가 item_order × 12개월, 값은 '-'
        # 그래도 혹시 모를 순서 정리를 한 번 더
        order = [r for r in item_order if r in piv.index]
        if order:
            piv = piv.loc[order]
        out = piv  # 문자열 그대로 반환 (반올림/숫자 변환 X)
    else:
        # 데이터가 있는 경우: 숫자형 변환 + 반올림
        order = [r for r in item_order if r in piv.index]
        if order:
            piv = piv.loc[order]

        out = piv.apply(pd.to_numeric, errors="coerce").astype(float).round(round_digits)

    out.index.name = plant_name
    return out




########################
##사용량 원단위 추이 충주1##
########################

import pandas as pd
import numpy as np

def create_material_usage_table_chungju1(
    year: int,
    month: int,                 # 기준 연/월 (this_year, current_month)
    data: pd.DataFrame,
    window: int = 12,           # 최근 몇 개월을 볼지(기본 12개월)
    plant_name: str = "충주",
    item_order: list[str] | None = None,
    round_digits: int = 6,
) -> pd.DataFrame:
    """
    [롱포맷 전용 롤링 12개월 테이블 - 충주1]
    - 기준 연/월(year, month)을 포함하여 과거 window-1개월까지의 데이터 사용
      (예: year=2025, month=8, window=12 → 2024-09 ~ 2025-08)
    - 필요한 컬럼: 구분3(공장), 구분1(항목), 월, 실적  (+ 선택: 연도)
    - 기간 안에 데이터가 없어도 그 달은 컬럼으로 생성
    - 선택 연월 기준 window개월 전체에 데이터가 1건도 없으면
      → item_order 행 + 12개월 열 구조 유지, 값은 전부 '-'로 채움
    """

    required = ["구분3", "구분1", "월", "실적"]
    df = data.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing} (필요: {required})")

    # item_order 기본값
    if item_order is None:
        item_order = ["열처리用LNG(㎥)", "질소(㎥)", "염산(kg)", "수소(㎥)", "산세용LNG(㎥)", "피막보급제(kg)"]

    # 1) 공장 필터
    q = df[df["구분3"].astype(str).str.contains(plant_name, na=False)].copy()

    # 2) 숫자화
    q["월"] = pd.to_numeric(q["월"], errors="coerce")
    q["실적"] = pd.to_numeric(q["실적"], errors="coerce")

    no_data_all = False  # 12개월 전체 무데이터 여부 플래그

    # ==============================
    # A. 연도 컬럼이 있는 경우: 연/월 기준 '진짜' 롤링 12개월
    # ==============================
    if "연도" in q.columns:
        q["연도"] = pd.to_numeric(q["연도"], errors="coerce")
        q = q[q["연도"].notna() & q["월"].notna()].copy()

        # 연월 키(0-based): year*12 + (month-1)
        q["ym_key"] = (q["연도"].astype(int) * 12) + (q["월"].astype(int) - 1)

        end_key = int(year) * 12 + (int(month) - 1)
        start_key = end_key - (window - 1)

        # 12개월 구간 전체 키
        full_keys = list(range(start_key, end_key + 1))

        # 구간 내 데이터만 필터
        q = q[(q["ym_key"] >= start_key) & (q["ym_key"] <= end_key)].copy()

        if q.empty:
            # ★ 12개월 전체에 데이터 1건도 없으면 '-' 템플릿
            no_data_all = True
            labels = []
            for k in full_keys:
                y = k // 12
                m = (k % 12) + 1
                yy = str(int(y))[-2:]
                labels.append(f"{yy}.{m:02d}")
            piv = pd.DataFrame('-', index=item_order, columns=labels)
        else:
            # 피벗: 컬럼 = ym_key
            piv = q.pivot_table(index="구분1", columns="ym_key", values="실적", aggfunc="sum")

            # 데이터 없는 달도 컬럼 생성(NaN)
            for k in full_keys:
                if k not in piv.columns:
                    piv[k] = np.nan
            piv = piv[full_keys]

            # 컬럼 라벨을 "YY.MM" 형식으로 변환
            labels = []
            for k in full_keys:
                y = k // 12
                m = (k % 12) + 1
                yy = str(int(y))[-2:]
                labels.append(f"{yy}.{m:02d}")
            piv.columns = labels

    # ==============================
    # B. 연도 컬럼이 없는 경우: 같은 연도 내에서만 롤링 (fallback)
    # ==============================
    else:
        q = q[q["월"].notna()].copy()
        q["월"] = q["월"].astype(int)

        end_m = int(month)
        start_m = max(1, end_m - (window - 1))
        months_range = list(range(start_m, end_m + 1))

        q = q[q["월"].isin(months_range)].copy()

        if q.empty:
            # ★ 12개월 전체에 데이터 1건도 없으면 '-' 템플릿
            no_data_all = True
            labels = [f"{m}월" for m in months_range]
            piv = pd.DataFrame('-', index=item_order, columns=labels)
        else:
            piv = q.pivot_table(index="구분1", columns="월", values="실적", aggfunc="sum")

            # 누락 월 NaN 추가 + 순서 정렬
            for m in months_range:
                if m not in piv.columns:
                    piv[m] = np.nan
            piv = piv[months_range]

            piv.columns = [f"{m}월" for m in months_range]

    # ==============================
    # C. 행 순서 정리 + 반올림
    # ==============================
    if no_data_all:
        # 이미 item_order × window개월, 값은 '-' 인 상태
        order = [r for r in item_order if r in piv.index]
        if order:
            piv = piv.loc[order]
        out = piv  # 문자열 그대로 반환
    else:
        # 데이터가 있는 경우: 숫자형 변환 + 반올림
        order = [r for r in item_order if r in piv.index]
        if order:
            piv = piv.loc[order]

        out = piv.apply(pd.to_numeric, errors="coerce").astype(float).round(round_digits)

    out.index.name = plant_name
    return out


########################
##사용량 원단위 추이 충주2##
########################

import pandas as pd
import numpy as np

def create_material_usage_table_chungju2(
    year: int,
    month: int,                 # 기준 연/월 (this_year, current_month)
    data: pd.DataFrame,
    window: int = 12,           # 최근 몇 개월을 볼지(기본 12개월)
    plant_name: str = "충주2",
    item_order: list[str] | None = None,
    round_digits: int = 6,
) -> pd.DataFrame:
    """
    [롱포맷 전용 롤링 12개월 테이블 - 충주2]
    - 기준 연/월(year, month)을 포함하여 과거 window-1개월까지의 데이터 사용
      (예: year=2025, month=8, window=12 → 2024-09 ~ 2025-08)
    - 필요한 컬럼: 구분3(공장), 구분1(항목), 월, 실적  (+ 선택: 연도)
    - 기간 안에 데이터가 없어도 그 달은 컬럼으로 생성
    - 선택 연월 기준 window개월 전체에 데이터가 1건도 없으면
      → item_order 행 + window개월 열 구조 유지, 값은 전부 '-' 로 채움
    """

    required = ["구분3", "구분1", "월", "실적"]
    df = data.copy()
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing} (필요: {required})")

    # item_order 기본값
    if item_order is None:
        item_order = ["CD用SHOTBALL(kg)", "CD/BTB 방청유(Drum)"]

    # 1) 공장 필터
    q = df[df["구분3"].astype(str).str.contains(plant_name, na=False)].copy()

    # 2) 숫자화
    q["월"] = pd.to_numeric(q["월"], errors="coerce")
    q["실적"] = pd.to_numeric(q["실적"], errors="coerce")

    no_data_all = False  # 12개월 전체 무데이터 여부

    # ==============================
    # A. 연도 컬럼이 있는 경우: 연/월 기준 롤링 window개월
    # ==============================
    if "연도" in q.columns:
        q["연도"] = pd.to_numeric(q["연도"], errors="coerce")
        q = q[q["연도"].notna() & q["월"].notna()].copy()

        # 연월 키(0-based): year*12 + (month-1)
        q["ym_key"] = (q["연도"].astype(int) * 12) + (q["월"].astype(int) - 1)

        end_key = int(year) * 12 + (int(month) - 1)
        start_key = end_key - (window - 1)

        # window개월 구간 전체 키
        full_keys = list(range(start_key, end_key + 1))

        # 컬럼 라벨 "YY.MM" 미리 생성
        labels = []
        for k in full_keys:
            y = k // 12
            m = (k % 12) + 1
            yy = str(int(y))[-2:]
            labels.append(f"{yy}.{m:02d}")

        # 구간 내 데이터만 필터
        q = q[(q["ym_key"] >= start_key) & (q["ym_key"] <= end_key)].copy()

        if q.empty:
            # ★ 전체 기간 무데이터 → '-' 템플릿
            no_data_all = True
            piv = pd.DataFrame('-', index=item_order, columns=labels)
        else:
            # 피벗: 컬럼 = ym_key
            piv = q.pivot_table(index="구분1", columns="ym_key", values="실적", aggfunc="sum")

            # 데이터 없는 달도 컬럼 생성(NaN)
            for k in full_keys:
                if k not in piv.columns:
                    piv[k] = np.nan
            piv = piv[full_keys]

            # "YY.MM" 라벨 적용
            piv.columns = labels

    # ==============================
    # B. 연도 컬럼이 없는 경우: 같은 연도 내에서만 롤링 (fallback)
    # ==============================
    else:
        q = q[q["월"].notna()].copy()
        q["월"] = q["월"].astype(int)

        end_m = int(month)
        start_m = max(1, end_m - (window - 1))
        months_range = list(range(start_m, end_m + 1))

        labels = [f"{m}월" for m in months_range]

        q = q[q["월"].isin(months_range)].copy()

        if q.empty:
            # ★ 전체 기간 무데이터 → '-' 템플릿
            no_data_all = True
            piv = pd.DataFrame('-', index=item_order, columns=labels)
        else:
            piv = q.pivot_table(index="구분1", columns="월", values="실적", aggfunc="sum")

            # 누락 월 NaN 추가 + 순서 정렬
            for m in months_range:
                if m not in piv.columns:
                    piv[m] = np.nan
            piv = piv[months_range]

            piv.columns = labels

    # ==============================
    # C. 행 순서 정리 + 반올림
    # ==============================
    if no_data_all:
        # 이미 item_order × window개월, 값은 '-' 인 상태
        order = [r for r in item_order if r in piv.index]
        if order:
            piv = piv.loc[order]
        out = piv  # 문자열 그대로 반환
    else:
        # 데이터가 있는 경우: 숫자형 변환 + 반올림
        order = [r for r in item_order if r in piv.index]
        if order:
            piv = piv.loc[order]

        out = piv.apply(pd.to_numeric, errors="coerce").astype(float).round(round_digits)

    out.index.name = plant_name
    return out





#####단가추이#####

from typing import Optional, List

def _to_month_any(s) -> float:
    """문자/숫자에서 월(1~12) 추출: '2월','2025-02','02',' 5 ' 등 허용."""
    if pd.isna(s): return np.nan
    ss = str(s).strip()
    m = re.search(r"(\d{1,2})(?!.*\d)", ss) or re.search(r"(\d{1,2})", ss)
    if not m: return np.nan
    v = int(m.group(1))
    return float(v) if 1 <= v <= 12 else np.nan



def create_material_usage_table_unit_price(
    year: int,
    month: int,
    data: pd.DataFrame,
    window: int = 12,                    # ✅ 기준월 포함 최근 12개월
    plant_name: Optional[str] = "",
    item_order: Optional[List[str]] = None,
    round_digits: int = 6,
) -> pd.DataFrame:
    """
    [롱포맷 전용 / 롤링 12개월 버전]

    - 필수 컬럼: 구분3(공장), 구분1(항목), 월, 실적  (+선택: 연도)
    - 기준 연/월(year, month)을 포함하여 과거 window-1개월까지의 데이터 사용
      (예: year=2025, month=8, window=12 → 2024-09 ~ 2025-08)
    - '연도' 컬럼이 있으면 연/월 단위로 12개월 롤링 (연도跨 가능, 컬럼 라벨: 'YY.MM')
    - '연도' 컬럼이 없으면 같은 연도 안에서만 롤링 (컬럼 라벨: 'n월')
    - 대상 항목(item_order)만 행으로 사용 (없으면 기본 6개)
    - 기간 안에 데이터가 없어도 그 달은 컬럼으로 생성(NaN 유지)
    """

    # 기본 대상 항목 6개
    if item_order is None:
        item_order = [
            "LNG(천㎥, 전년동기)",
            "난방등유(L)",
            "LNG(천㎥)",
            "수소(천㎥)",
            "질소(천㎥)",
            "전력(천kwh)",
        ]

    # 원본 정리
    df = data.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # 필수 컬럼 체크
    required = ["구분1", "월", "실적"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}")

    q = df.copy()

    # 공장 필터 (원하면 plant_name=None로 스킵 가능)
    if plant_name is not None and "구분3" in q.columns:
        mask = q["구분3"].astype(str).str.contains(plant_name, na=False)
        q = q[mask] if mask.any() else q

    # 연도 필터(있을 때만; 비면 해제)
    if "연도" in q.columns:
        yr = pd.to_numeric(q["연도"], errors="coerce")
        q_year = q[yr == year]
        if len(q_year) > 0:
            q = q_year

    # 월/값 숫자화
    q["월"] = q["월"].apply(_to_month_any)
    q["실적"] = pd.to_numeric(q["실적"], errors="coerce")

    # 대상 항목만 남기기
    q = q[q["구분1"].isin(item_order)]

    # 유효 월만
    q = q[(q["월"] >= 1) & (q["월"] <= 12)]
    if q.empty:
        raise ValueError("유효한 월 데이터가 없습니다.")

    # ==============================
    # A. '연도'가 있는 경우: 연/월 기준 롤링 window개월 (연도跨 가능)
    # ==============================
    if "연도" in q.columns:
        q["연도"] = pd.to_numeric(q["연도"], errors="coerce")
        q = q[q["연도"].notna() & q["월"].notna()].copy()

        # 연월 key (0-based month)
        q["ym_key"] = (q["연도"].astype(int) * 12) + (q["월"].astype(int) - 1)

        end_key = int(year) * 12 + (int(month) - 1)
        start_key = end_key - (window - 1)

        # 12개월 전체 key
        full_keys = list(range(start_key, end_key + 1))

        # 구간 필터
        q = q[(q["ym_key"] >= start_key) & (q["ym_key"] <= end_key)].copy()

        # 피벗: index=항목, columns=ym_key
        piv = q.pivot_table(index="구분1", columns="ym_key", values="실적", aggfunc="sum")

        # 없는 달도 NaN 컬럼으로 생성 + 순서 보장
        for k in full_keys:
            if k not in piv.columns:
                piv[k] = np.nan
        piv = piv[full_keys]

        # 컬럼 라벨을 "YY.MM" 로 변환
        labels = []
        for k in full_keys:
            y = k // 12
            m = (k % 12) + 1
            yy = str(int(y))[-2:]   # 연도 뒤 2자리
            labels.append(f"{yy}.{m:02d}")
        piv.columns = labels

    # ==============================
    # B. '연도'가 없는 경우: 같은 연도 내에서만 롤링 window개월
    # ==============================
    else:
        q = q[q["월"].notna()].copy()
        q["월"] = q["월"].astype(int)

        end_m = int(month)
        start_m = max(1, end_m - (window - 1))
        months_range = list(range(start_m, end_m + 1))

        q = q[q["월"].isin(months_range)].copy()

        piv = q.pivot_table(index="구분1", columns="월", values="실적", aggfunc="sum")

        # 없는 월도 NaN 컬럼으로 생성 + 순서 보장
        for m in months_range:
            if m not in piv.columns:
                piv[m] = np.nan
        piv = piv[months_range]

        piv.columns = [f"{m}월" for m in months_range]

    # ==============================
    # C. 행 순서 고정 + 반올림
    # ==============================
    piv = piv.reindex(item_order)  # 지정된 6개 순서대로, 없으면 NaN 행

    out = piv.apply(pd.to_numeric, errors="coerce").astype(float).round(round_digits)
    out.index.name = plant_name if plant_name is not None else ""
    return out




_NUM_PAT = re.compile(r"^\s*\((.*)\)\s*$")
def _to_number_robust(x)->float:
    if pd.isna(x): return 0.0
    s = str(x).replace("\u2212","-").replace(",","").strip()
    m = _NUM_PAT.match(s)
    if m: s = "-" + m.group(1).strip()
    try: return float(s)
    except: return 0.0

def load_nonop_cost_csv(source: str) -> pd.DataFrame:
    df = pd.read_csv(source, dtype=str)
    for c in ["구분1","구분2","구분3","구분4"]:
        if c in df.columns:
            #
            # 올바른 코드
            df[c] = (
                df[c]
                .astype(str)
                .fillna("")                 # 결측을 빈 문자열로
                .str.replace("\u00A0", " ", regex=False)  # 비정상 공백(NBSP) 제거(있을 때만)
                .str.strip()                # 앞뒤 공백 제거  ← 여기!
            )

    if "연도" in df: df["연도"] = pd.to_numeric(df["연도"].str.extract(r"(\d+)", expand=False), errors="coerce").fillna(0).astype(int)
    if "월"  in df: df["월"]  = pd.to_numeric(df["월"].str.extract(r"(\d+)",  expand=False), errors="coerce").fillna(0).astype(int)
    df["실적"] = df.get("실적", 0).apply(_to_number_robust)
    key = [c for c in ["구분1","구분2","구분3","구분4","연도","월"] if c in df.columns]
    return df.groupby(key, as_index=False, dropna=False)["실적"].sum()



##### 비용분석 영업외 비용 내역 #####


def create_nonop_cost_3month_by_g2_g4(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:


    # ── 1. 기준 연월 및 전월/전전월 계산 (연도 포함) ──
    y0 = int(year)
    m0 = int(month)

    def shift_month(y: int, m: int, delta: int):
        total = y * 12 + (m - 1) + delta
        yy = total // 12
        mm = total % 12 + 1
        return yy, mm

    y1, m1 = shift_month(y0, m0, -1)  # 전월
    y2, m2 = shift_month(y0, m0, -2)  # 전전월

    key0 = y0 * 100 + m0
    key1 = y1 * 100 + m1
    key2 = y2 * 100 + m2
    keys = [key2, key1, key0]

    # ── 2. 선택연월 기준 3개월 데이터 필터 ──
    ym_key = data["연도"].astype(int) * 100 + data["월"].astype(int)
    df_y = data[ym_key.isin(keys)].copy()
    df_y["연월키"] = df_y["연도"].astype(int) * 100 + df_y["월"].astype(int)

    # ── 3. 피벗: (구분2, 구분4) 기준, 연월키를 컬럼으로 ──
    piv = (
        df_y.pivot_table(
            index=["구분2", "구분4"],
            columns="연월키",
            values="실적",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reindex(columns=keys, fill_value=0.0)
        .reset_index()
    )

    # ── 4. 표시용 컬럼명 생성 (연도까지 반영) ──
    def _lbl(yy: int, mm: int) -> str:
        return f"'{str(yy)[-2:]}.{mm}월 실적"

    c_m2 = _lbl(y2, m2)   # 전전월
    c_m1 = _lbl(y1, m1)   # 전월
    c_m  = _lbl(y0, m0)   # 당월

    for k, col in zip(keys, [c_m2, c_m1, c_m]):
        piv[col] = piv[k].astype(float)

    piv["증감"] = piv[c_m] - piv[c_m1]
    piv = piv.drop(columns=keys)

    # ── 5. 섹션별(구분2) 노출 순서 ──
    order_fin = [  # 금융비용
        "이자비용",
        "외환차손",
        "외화환산손실",
        "파생상품평가손실",
        "파생상품거래손실",
        "매도가능증권손상차손",
        "리스부채이자비용",
        "기타금융부채평가손실",
    ]
    order_etc = [  # 기타비용
        "기부금",
        "유형자산처분손실",
        "무형자산처분손실",
        "무형자산손상차손",
        "지급수수료(영업외)",   # ↓ 이 아래에 child 2개
        "고철매각작업비",       # child
        "기타",                # child (= 잡손실 − 고철매각작업비)
        "잡손실",
        "공동지배기업투자처분손실",
        "종속기업주식손상차손",
        "기타비용",
    ]

    rows = []

    def add_row(sec, acct, v2, v1, v, diff, row_type):
        rows.append({
            "구분": sec,
            "계정": acct,
            c_m2: float(v2),
            c_m1: float(v1),
            c_m:  float(v),
            "증감": float(diff),
            "_row_type": row_type,
        })

    # ── 섹션 처리 함수 ──
    def build_section(sec_name: str, grp_df: pd.DataFrame, order_list: list[str]):
        recs = {r["구분4"]: r for r in grp_df.to_dict(orient="records")}
        start_idx = len(rows)

        for acct in order_list:
            if acct == "지급수수료(영업외)":
                # 부모
                parent = recs.get("지급수수료(영업외)")
                if parent is not None:
                    add_row("", "지급수수료(영업외)",
                            parent[c_m2], parent[c_m1], parent[c_m], parent["증감"], "parent")

                # child: 고철
                steel = recs.get("고철매각작업비")
                # child 계산용: 잡손실
                jab   = recs.get("잡손실")

                if steel is not None:
                    add_row("", "고철매각작업비",
                            steel[c_m2], steel[c_m1], steel[c_m], steel["증감"], "child")

                # 기타 = 잡손실 − 고철
                v_j2 = float(jab[c_m2]) if jab is not None else 0.0
                v_j1 = float(jab[c_m1]) if jab is not None else 0.0
                v_j  = float(jab[c_m])  if jab is not None else 0.0
                d_j  = float(jab["증감"]) if jab is not None else 0.0

                v_s2 = float(steel[c_m2]) if steel is not None else 0.0
                v_s1 = float(steel[c_m1]) if steel is not None else 0.0
                v_s  = float(steel[c_m])  if steel is not None else 0.0
                d_s  = float(steel["증감"]) if steel is not None else 0.0

                add_row("", "기타",
                        v_j2 - v_s2, v_j1 - v_s1, v_j - v_s, d_j - d_s, "child")

                continue

            if acct in ("고철매각작업비", "기타"):
                # 위에서 child로 처리
                continue

            rec = recs.get(acct)
            if rec is not None:
                add_row("", acct, rec[c_m2], rec[c_m1], rec[c_m], rec["증감"], "item")

        # ── 섹션 합계 ──
        sec_block = rows[start_idx:]
        if sec_block:
            sec_df = pd.DataFrame(sec_block)

            # 기타비용은 잡손실 값 합계에 X
            if sec_name == "기타비용":
                sec_df_for_total = sec_df[sec_df["계정"] != "잡손실"]
            else:
                sec_df_for_total = sec_df

            s = sec_df_for_total[[c_m2, c_m1, c_m, "증감"]].sum(numeric_only=True)

            add_row(sec_name, "", s[c_m2], s[c_m1], s[c_m], s["증감"], "section_total")

    # 섹션 순서
    preferred = ["기타비용", "금융비용"]
    others = [s for s in piv["구분2"].dropna().unique().tolist() if s not in preferred]
    sec_order = preferred + others

    for sec in sec_order:
        grp = piv[piv["구분2"] == sec]
        if grp.empty:
            continue

        if sec == "기타비용":
            build_section("기타비용", grp, order_etc)
        elif sec == "금융비용":
            build_section("금융비용", grp, order_fin)
        else:
            build_section(str(sec), grp, sorted(grp["구분4"].unique().tolist()))

    out = pd.DataFrame(rows)

    # ---- 1) 3개월 구간에 데이터가 전혀 없을 때: 템플릿 구조 ----
    if out.empty or "_row_type" not in out.columns:
        rows = []

        def add_zero_row(sec, acct, row_type):
            rows.append({
                "구분": sec if row_type in ("section_total", "grand_total") else "",
                "계정": acct,
                c_m2: "",
                c_m1: "",
                c_m:  "",
                "증감": "",
                "_row_type": row_type,
            })

        for acct in order_etc:
            if acct == "지급수수료(영업외)":
                add_zero_row("", acct, "parent")
            elif acct in ("고철매각작업비", "기타"):
                add_zero_row("", acct, "child")
            else:
                add_zero_row("", acct, "item")
        add_zero_row("기타비용", "", "section_total")

        for acct in order_fin:
            add_zero_row("", acct, "item")
        add_zero_row("금융비용", "", "section_total")

        add_zero_row("계", "", "grand_total")

        out = pd.DataFrame(rows)
        return out[["구분", "계정", c_m2, c_m1, c_m, "증감", "_row_type"]]

    # ---- 2) 데이터가 있는 경우: 섹션 합계 → 전체 계 계산 ----
    sec_totals = out[out["_row_type"] == "section_total"]
    if sec_totals.empty:
        grand_vals = {c_m2: 0.0, c_m1: 0.0, c_m: 0.0, "증감": 0.0}
    else:
        s = sec_totals[[c_m2, c_m1, c_m, "증감"]].sum(numeric_only=True)
        grand_vals = {
            c_m2: float(s.get(c_m2, 0.0)),
            c_m1: float(s.get(c_m1, 0.0)),
            c_m:  float(s.get(c_m, 0.0)),
            "증감": float(s.get("증감", 0.0)),
        }

    rows.append({
        "구분": "계",
        "계정": "",
        c_m2: grand_vals[c_m2],
        c_m1: grand_vals[c_m1],
        c_m:  grand_vals[c_m],
        "증감": grand_vals["증감"],
        "_row_type": "grand_total",
    })

    out = pd.DataFrame(rows)
    return out[["구분", "계정", c_m2, c_m1, c_m, "증감", "_row_type"]]










##### 실적 분석 #####


# ================= 공통 유틸 =================

def _coerce_number_series(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.replace(',', '', regex=False)
         .replace({'': None, 'nan': None})
         .astype(float)
    )

def _normalize_company_name(x: str) -> str:
    # 타이/태국 → '태국' 으로 통일
    if x in ['타이', '태국']:
        return '태국'
    return x

def _clean_profit_connected_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    # 표준화
    df['연도'] = df['연도'].astype(int)
    df['월']   = df['월'].astype(int)
    df['구분2'] = df['구분2'].astype(str).map(_normalize_company_name)
    df['구분3'] = df['구분3'].astype(str)
    df['구분4'] = df['구분4'].astype(str)
    df['실적']  = _coerce_number_series(df['실적'])

    # 스케일링
    money_metrics = ['매출액', '영업이익', '순금융비용', '경상이익']
    qty_metrics   = ['판매량']
    df.loc[df['구분3'].isin(money_metrics), '실적'] /= 1_000_000
    df.loc[df['구분3'].isin(qty_metrics),   '실적'] /= 1_000

    # 열 정리
    drop_cols = [c for c in df.columns if c.startswith('Unnamed')]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors='ignore')
    return df

def _sum_at(df: pd.DataFrame, y: int, m: int, kind: str) -> pd.Series:
    """특정 연-월, 계획/실적(kind) 합계: (회사, 지표)로 그룹."""
    return (
        df[(df['연도'] == y) & (df['월'] == m) & (df['구분4'] == kind)]
        .groupby(['구분2', '구분3'])['실적'].sum()
    )

def _pp(val):
    """증감 숫자를 괄호 표기로(음수만 괄호)."""
    if pd.isna(val):
        return ""
    try:
        v = float(val)
    except Exception:
        return val
    s = f"{abs(int(round(v))):,}"
    return f"({s})" if v < 0 else s

def _fmt_int(val):
    try:
        return f"{int(round(float(val))):,}"
    except Exception:
        return val

def _fmt_pct1(val):
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return ""
    try:
        # 소수점 1자리까지, % 기호는 안 붙임
        return f"{float(val):.1f}"
    except Exception:
        return val


def _shift_year_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """
    year, month 기준으로 delta개월 이동한 (year, month)를 반환.
    delta = -1 이면 전월, delta = -2 이면 전전월 등.
    규칙:
      - 전월 = 같은 해 (month-1)
      - 1월의 전월 = 이전 해 12월
    """
    base = year * 12 + (month - 1) + delta
    new_year = base // 12
    new_month = base % 12 + 1
    return new_year, new_month


#


# ================= 손익 연결 요약표 (전전월/전월/당월 + 회사별) =================

def create_connected_profit(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
       
    df = _clean_profit_connected_df(data)

    # 화면에 보여줄 회사 컬럼 순서
    companies_order = ['본사', '중국', '남통', '천진', '태국']
    metrics_order   = ['매출액', '판매량', '영업이익', '%(영업)', '순금융비용', '경상이익', '%(경상)']

    # 전전월/전월/당월 연월 계산 (year, month는 당월로 그대로 사용)
    yy_prev,  mm_prev  = _shift_year_month(year, month, -1)  # 전월
    yy_prev2, mm_prev2 = _shift_year_month(year, month, -2)  # 전전월

    # 집계 시리즈(회사, 지표)
    s_prev2 = _sum_at(df, yy_prev2, mm_prev2, '실적')
    s_prev  = _sum_at(df, yy_prev,  mm_prev,  '실적')
    s_plan  = _sum_at(df, year, month, '계획')   # 당월 계획
    s_curr  = _sum_at(df, year, month, '실적')   # 당월 실적

    # 합계(지표 기준)
    def total_by_metric(s: pd.Series) -> pd.Series:
        return s.groupby('구분3').sum()

    tot_prev2 = total_by_metric(s_prev2)
    tot_prev  = total_by_metric(s_prev)
    tot_plan  = total_by_metric(s_plan)
    tot_curr  = total_by_metric(s_curr)

    # ─ 회사별 당월 실적 피벗(열=회사, 행=지표) ─
    base_companies = ['본사', '남통', '천진', '태국']  # 원 데이터 기준

    company_curr = (
        s_curr.reset_index()
             .pivot_table(index='구분3', columns='구분2', values='실적', aggfunc='sum')
             .reindex(columns=base_companies)
             .fillna(0.0)
    )

    # 중국 = 남통 + 천진
    company_curr['중국'] = company_curr['남통'] + company_curr['천진']

    # 최종 컬럼 순서
    company_curr = company_curr[companies_order]

    # ─ 퍼센트(합계, 회사별) 계산 ─
    def safe_ratio(n, d):
        return None if (d is None or d == 0 or pd.isna(d)) else n / d * 100

    # 전체 합계 기준 마진
    op_margin_prev2 = safe_ratio(tot_prev2.get('영업이익', 0), tot_prev2.get('매출액', 0))
    op_margin_prev  = safe_ratio(tot_prev.get('영업이익', 0),  tot_prev.get('매출액', 0))
    op_margin_plan  = safe_ratio(tot_plan.get('영업이익', 0),  tot_plan.get('매출액', 0))
    op_margin_curr  = safe_ratio(tot_curr.get('영업이익', 0),  tot_curr.get('매출액', 0))

    or_margin_prev2 = safe_ratio(tot_prev2.get('경상이익', 0), tot_prev2.get('매출액', 0))
    or_margin_prev  = safe_ratio(tot_prev.get('경상이익', 0),  tot_prev.get('매출액', 0))
    or_margin_plan  = safe_ratio(tot_plan.get('경상이익', 0),  tot_plan.get('매출액', 0))
    or_margin_curr  = safe_ratio(tot_curr.get('경상이익', 0),  tot_curr.get('매출액', 0))

    # 회사별 퍼센트(당월)
    def company_margin_row(nm: str):
        num = company_curr.loc[nm] if nm in company_curr.index else pd.Series(0, index=company_curr.columns)
        den = company_curr.loc['매출액'] if '매출액' in company_curr.index else pd.Series(0, index=company_curr.columns)
        out = []
        for c in companies_order:
            v = None if (c not in num or c not in den or den[c] == 0) else num[c] / den[c] * 100
            out.append(v)
        return out

    comp_op_margin = company_margin_row('영업이익')
    comp_or_margin = company_margin_row('경상이익')

    # ─ 표 본체 생성 ─
    cols = ['전전월 실적', '전월 실적', '당월 계획', '당월 실적'] + companies_order + ['전월 실적 대비', '계획 대비']
    out = pd.DataFrame(index=metrics_order, columns=cols, dtype=object)

    # 숫자 행
    for metric in ['매출액', '판매량', '영업이익', '순금융비용', '경상이익']:
        out.at[metric, '전전월 실적'] = _fmt_int(tot_prev2.get(metric, 0))
        out.at[metric, '전월 실적']  = _fmt_int(tot_prev.get(metric, 0))
        out.at[metric, '당월 계획']  = _fmt_int(tot_plan.get(metric, 0))
        out.at[metric, '당월 실적']  = _fmt_int(tot_curr.get(metric, 0))

        for c in companies_order:
            v = company_curr.get(c).get(metric, 0) if metric in company_curr.index else 0
            out.at[metric, c] = _fmt_int(v)

        diff_prev = tot_curr.get(metric, 0) - tot_prev.get(metric, 0)
        diff_plan = tot_curr.get(metric, 0) - tot_plan.get(metric, 0)
        out.at[metric, '전월 실적 대비'] = _pp(diff_prev)
        out.at[metric, '계획 대비']     = _pp(diff_plan)

    #음수 괄호 반영    
    for c in out.columns:
        out[c] = out[c].apply(_pp)
   
    # 퍼센트 행 처리
    out.at['%(영업)', '전전월 실적'] = _fmt_pct1(op_margin_prev2)
    out.at['%(영업)', '전월 실적']  = _fmt_pct1(op_margin_prev)
    out.at['%(영업)', '당월 계획']  = _fmt_pct1(op_margin_plan)
    out.at['%(영업)', '당월 실적']  = _fmt_pct1(op_margin_curr)

    out.at['%(경상)', '전전월 실적'] = _fmt_pct1(or_margin_prev2)
    out.at['%(경상)', '전월 실적']  = _fmt_pct1(or_margin_prev)
    out.at['%(경상)', '당월 계획']  = _fmt_pct1(or_margin_plan)
    out.at['%(경상)', '당월 실적']  = _fmt_pct1(or_margin_curr)

    # 회사별 퍼센트(당월)
    for i, c in enumerate(companies_order):
        out.at['%(영업)', c] = _fmt_pct1(comp_op_margin[i])
        out.at['%(경상)', c] = _fmt_pct1(comp_or_margin[i])

    # 퍼센트 증감(포인트)
    def pp_delta(a, b):
        if a is None or b is None:
            return ""
        try:
            return _pp(a - b)
        except Exception:
            return ""

    out.at['%(영업)', '전월 실적 대비'] = pp_delta(op_margin_curr, op_margin_prev)
    out.at['%(영업)', '계획 대비']     = pp_delta(op_margin_curr, op_margin_plan)
    out.at['%(경상)', '전월 실적 대비'] = pp_delta(or_margin_curr, or_margin_prev)
    out.at['%(경상)', '계획 대비']     = pp_delta(or_margin_curr, or_margin_plan)

    # 인덱스 재정렬(가독성)
    out.index = metrics_order



    return out





# ====================== 현금흐름표 ======================
import pandas as pd
import numpy as np

def _normalize_company_cf(x: str) -> str:
    x = str(x)
    if x in ("타이", "태국"):
        return "태국"
    return x

def _paren_to_signed(s: pd.Series) -> pd.Series:
    s = s.fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
    neg = s.str.match(r"^\(.*\)$")
    s = s.str.replace(r"[\(\)]", "", regex=True)
    v = pd.to_numeric(s, errors="coerce")
    v[neg] = -v[neg].abs()
    return v.fillna(0.0)

def clean_cashflow_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    # 항목/회사/연월 컬럼 탐색
    item_col = next((c for c in ["구분", "구분3", "항목"] if c in df.columns), None)
    if item_col is None:
        raise ValueError("CSV에 '구분'(또는 '구분3'/'항목') 컬럼이 필요합니다.")
    comp_col = next((c for c in ["구분2", "회사", "법인"] if c in df.columns), None)
    if comp_col is None:
        comp_col = "_회사"
        df[comp_col] = "전체"
    if "연도" not in df.columns or "월" not in df.columns or "실적" not in df.columns:
        raise ValueError("CSV에 '연도','월','실적' 컬럼이 필요합니다.")

    # 문자열 정리(중복 방지용): 좌우공백/연속공백 제거
    df[item_col] = (
        df[item_col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )
    df[comp_col] = (
        df[comp_col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        .map(_normalize_company_cf)
    )

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df["월"],   errors="coerce").astype("Int64")
    df["실적"] = _paren_to_signed(df["실적"])

    drop_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors="ignore")

    return df.rename(columns={item_col: "구분", comp_col: "회사"})

def create_cashflow_by_gubun(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    df = clean_cashflow_df(data)

    companies = ["본사", "남통", "천진", "태국"]

    used_year = year
    used_month = month

    # "전월"용 prev_year/prev_month (메타 정보)
    prev_year = used_year
    prev_month = used_month - 1
    if prev_month == 0:
        prev_year -= 1
        prev_month = 12

    gubun_order = list(dict.fromkeys(df["구분"].astype(str).tolist()))

    # ---------- 집계 함수 ----------
    def total_by_items(y, months):
        q = (df["연도"] == y) & (df["월"].isin(months))
        s = df[q].groupby("구분", sort=False)["실적"].sum()
        if s.index.duplicated().any():
            s = s.groupby(level=0).sum()
        return s

    def company_by_month(y, m):
        q = (df["연도"] == y) & (df["월"] == m)
        pv = (
            df[q]
            .pivot_table(
                index="구분",
                columns="회사",
                values="실적",
                aggfunc="sum",
                fill_value=0.0,
            )
        )
        if pv.index.duplicated().any():
            pv = pv.groupby(level=0).sum()
        return pv.reindex(columns=companies).fillna(0.0)
    # ---------- /집계 함수 ----------

    # ✅ 전년도 누계 (항상 year-1 기준)
    prev_full_year = used_year - 1
    col_prev_year = total_by_items(prev_full_year, range(1, 13))

    # ✅ 전월 누적 (선택연도 기준)
    if used_month > 1:
        col_prev_cum = total_by_items(used_year, range(1, used_month))
    else:
        # 선택연도 1월이면 전월누적 = 전년도 누계
        col_prev_cum = col_prev_year

    # ✅ 당월 / 당월누적 (선택연도 기준)
    col_month = total_by_items(used_year, [used_month])
    col_ytd   = total_by_items(used_year, range(1, used_month + 1))

    by_comp = company_by_month(used_year, used_month)

    all_items = pd.Index(gubun_order, name="구분")

    # ✅ 연도 라벨 동적으로 생성
    prev_year_label = f"'{prev_full_year % 100:02d}"
    used_year_label = f"'{used_year % 100:02d}"

    out = pd.DataFrame(index=all_items, dtype=float)
    out[prev_year_label] = col_prev_year.reindex(all_items).fillna(0.0).values      # 전년도 누계
    out[used_year_label] = col_prev_cum.reindex(all_items).fillna(0.0).values       # 선택연도 전월누계
    out["당월"] = col_month.reindex(all_items).fillna(0.0).values
    out["당월누적"] = col_ytd.reindex(all_items).fillna(0.0).values

    for c in companies:
        out[c] = by_comp.reindex(all_items).get(c, 0.0).fillna(0.0).values

    # 컬럼 순서 정리
    out = out[[prev_year_label, used_year_label, "당월", "본사", "남통", "천진", "태국", "당월누적"]]

    # 메타 정보(전월) 유지
    out.attrs["used_year"] = used_year
    out.attrs["used_month"] = used_month
    out.attrs["prev_year"] = prev_year
    out.attrs["prev_month"] = prev_month

    return out




# ====================== 재무상태표 ======================


import pandas as pd
import numpy as np

def _bs_to_number(x):
    s = str(x).strip()
    if not s:
        return 0.0
    neg = s.startswith('(') and s.endswith(')')
    s = s.replace('(', '').replace(')', '').replace(',', '')
    try:
        v = float(s)
    except Exception:
        return 0.0
    return -abs(v) if neg else v


def _normalize_bs_simple(df_raw: pd.DataFrame) -> pd.DataFrame:

    df = df_raw.copy()

    item_col = next((c for c in ['구분3','구분2','항목','구분'] if c in df.columns), None)
    comp_col = next((c for c in ['회사','법인','구분4'] if c in df.columns), None)

    for need in ['연도','월','실적']:
        if need not in df.columns:
            raise ValueError(f"재무상태표 데이터에 '{need}' 컬럼이 필요합니다.")
    if item_col is None:
        raise ValueError("재무상태표: '구분3/구분2/항목/구분' 중 하나가 필요합니다.")

    df[item_col] = df[item_col].astype(str).str.strip()
    if comp_col is None:
        comp_col = '_회사'
        df[comp_col] = '전체'
    else:
        df[comp_col] = df[comp_col].astype(str).str.strip().replace({'타이':'태국'})

    s = df['실적'].astype(str).str.strip()
    neg = s.str.match(r'^\(.*\)$')
    s = s.str.replace(r'[(),]', '', regex=True)
    v = pd.to_numeric(s, errors='coerce').fillna(0.0)
    v[neg] = -v[neg].abs()
    df['실적'] = v

    df['연도'] = pd.to_numeric(df['연도'], errors='coerce').astype('Int64')
    df['월']   = pd.to_numeric(df['월'],   errors='coerce').astype('Int64')

    drop_cols = [c for c in df.columns if str(c).startswith('Unnamed')]
    if drop_cols: 
        df = df.drop(columns=drop_cols, errors='ignore')

    return df.rename(columns={item_col:'구분3', comp_col:'회사'})


def _closest_month(df: pd.DataFrame, year: int, month: int) -> int | None:
    """
    (다른 곳에서 쓸 수 있으니 남겨 두지만,
    create_bs_by_items 안에서는 '당월/전월' 계산에 더 이상 사용하지 않음)
    """
    avail = sorted(m for m in df.loc[df['연도']==year, '월'].dropna().unique())
    if not avail: 
        return None
    le = [m for m in avail if m <= month]
    return le[-1] if le else avail[-1]


def create_bs_by_items(
    year: int,
    month: int,
    data: pd.DataFrame,
    item_order: list[str],
) -> pd.DataFrame:

    df = _normalize_bs_simple(data)

    # ───────────────
    # ✔ 전월 / 당월 계산
    # ───────────────
    month_pairs = []
    for k in (1, 0):  # 1: 전월, 0: 당월
        y0 = year
        m0 = month - k
        while m0 <= 0:
            y0 -= 1
            m0 += 12
        month_pairs.append((y0, m0))

    (prev_y, prev_m), (used_y, used_m) = month_pairs

    # 전년도 12월(또는 가장 가까운 달)
    last_prev_year_m = _closest_month(df, year - 1, 12)

    # ───────────────
    # ✔ 회사 컬럼 구성
    # ───────────────
    fixed_comp = ['특수강', '남통', '천진', '태국']
    all_comp = sorted(df['구분2'].dropna().unique())
    others = [c for c in all_comp if c not in fixed_comp]
    comp_cols = fixed_comp + others

    # ───────────────
    # ✔ 동적 연도 라벨 생성
    # ───────────────
    prev_year_label = f"'{(year-1) % 100:02d}"               # 예: '25
    prev_month_label = f"'{(prev_y % 100):02d} {prev_m}월"   # 예: '25 12월

    rows: list[dict] = []

    for item in item_order:
        mask_item = df['구분3'] == item

        def _sum_at(y, m):
            if y is None or m is None:
                return 0.0
            sub = df[mask_item & (df['연도'] == y) & (df['월'] == m)]
            return float(sub['실적'].sum())

        def _by_company(y, m):
            result = {c: 0.0 for c in comp_cols}
            if y is None or m is None:
                return result
            sub = df[mask_item & (df['연도'] == y) & (df['월'] == m)]
            s = sub.groupby('구분2')['실적'].sum()
            for c in comp_cols:
                if c in s.index:
                    result[c] = float(s[c])
            return result

        v_prev_year = _sum_at(year - 1, last_prev_year_m)  # 전년도 12월
        v_prev_month = _sum_at(prev_y, prev_m)              # 전월
        v_month = _sum_at(used_y, used_m)                  # 당월
        comp_v = _by_company(used_y, used_m)

        row = {
            prev_year_label: v_prev_year,
            prev_month_label: v_prev_month,
            "당월": v_month,
            **comp_v,
            "전월비 증감": v_month - v_prev_month,
        }
        rows.append(row)

    out = pd.DataFrame(rows, index=pd.Index(item_order, name='구분')).fillna(0.0)

    # 열 순서 재정렬
    out = out[[prev_year_label, prev_month_label, "당월"] + comp_cols + ["전월비 증감"]]

    # 메타 저장
    out.attrs['base_year'] = year
    out.attrs['used_year'] = used_y
    out.attrs['used_month'] = used_m
    out.attrs['prev_year'] = prev_y
    out.attrs['prev_month'] = prev_m

    return out





# ===== 회전일 =====

import pandas as pd
import numpy as np

def _num_paren(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    neg = s.str.match(r'^\(.*\)$')
    s = s.str.replace(r'[(),]', '', regex=True)
    v = pd.to_numeric(s, errors='coerce')
    v[neg] = -v[neg].abs()
    return v


def _normalize_turnover(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    회전일 원천을 표준 스키마로 정리:
      - 항목: '구분' 컬럼로 반환
      - 회사: '회사' 컬럼로 반환
      - 값 : '값'  컬럼로 반환
    회사명이 구분3에 있는 형태(계/특수강/남(통)/천진/태국)도 자동 감지해서
    '회사'로 사용하고, 항목은 구분2(또는 구분/항목)를 사용한다.
    """
    df = df_raw.copy()

    # 값/항목/회사 후보
    val_col = next((c for c in ['회전일','실적','값','value'] if c in df.columns), None)
    if val_col is None:
        raise ValueError("회전일 데이터에 '회전일/실적/값' 컬럼이 필요합니다.")

    # 기본 숫자/연월 정리
    df['연도'] = pd.to_numeric(df['연도'], errors='coerce').astype('Int64')
    df['월']   = pd.to_numeric(df['월'],   errors='coerce').astype('Int64')

    # 괄호 음수 → 음수, 쉼표 제거
    df[val_col] = _num_paren(df[val_col]).astype(float)

    # 후보 열들
    cand_item = ['구분3','구분2','구분','항목']
    cand_comp = ['회사','법인','구분4']

    # 회사/항목 기본 선택
    item_col = next((c for c in cand_item if c in df.columns), None)
    comp_col = next((c for c in cand_comp if c in df.columns), None)

    # --- 회사명이 구분3에 들어있는 케이스 감지 ---
    known_companies = {'계','전체','연결','특수강','본사','남통','남동','천진','태국','타이'}
    def looks_like_company(series) -> bool:
        s = series.astype(str).str.strip()
        nonnull = s[s != ""]
        if len(nonnull) == 0:
            return False
        hit = nonnull.isin(known_companies).mean()
        return hit >= 0.7

    if ('구분3' in df.columns) and (comp_col is None or looks_like_company(df['구분3'])):
        comp_col = '구분3'
        # 항목은 구분2 > 구분 > 항목 순으로
        item_col = next((c for c in ['구분2','구분','항목'] if c in df.columns and c != comp_col), item_col)

    if item_col is None:
        raise ValueError("회전일 데이터에 항목 컬럼(구분3/구분2/구분/항목) 중 하나가 필요합니다.")

    # 문자열 정리 + alias
    df[item_col] = df[item_col].astype(str).str.strip()
    if comp_col is None:
        comp_col = '_회사'
        df[comp_col] = '전체'
    df[comp_col] = (
        df[comp_col].astype(str).str.strip()
          .replace({'타이':'태국', '남동':'남통'})   # alias 통일
    )

    # 쓰지 않는 Unnamed 열 제거
    drop_cols = [c for c in df.columns if str(c).startswith('Unnamed')]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors='ignore')

    return df.rename(columns={item_col: '구분', comp_col: '회사', val_col: '값'})


def create_turnover(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    import numpy as np

    df = _normalize_turnover(data)

    # ───────── 선택월 / 전월 계산 (연도 경계 포함) ─────────
    used_y, used_m = year, month
    if month > 1:
        prev_y, prev_m = year, month - 1
    else:
        prev_y, prev_m = year - 1, 12

    # ───────── 회사 라벨 정규화 ─────────
    def norm_comp(x: str) -> str:
        x = str(x).strip()
        x = {'타이': '태국', '남동': '남통'}.get(x, x)
        if x in ('전체', '연결'):
            return '계'
        return x

    all_raw = df['회사'].dropna().astype(str)
    all_norm = pd.Index(all_raw.map(norm_comp).unique())

    fixed_comp = ['특수강', '남통', '천진', '태국']
    others = [c for c in all_norm if c not in fixed_comp and c not in ('계', '')]
    companies = fixed_comp + others

    # ───────── 항목×월 집계 ─────────
    def row_by_month(item, y, m):
        sub = df[(df['구분'] == item) & (df['연도'] == y) & (df['월'] == m)].copy()
        res = {c: np.nan for c in companies}
        res['계'] = np.nan

        if sub.empty:
            return res

        sub['회사N'] = sub['회사'].map(norm_comp)
        byc = sub.groupby('회사N', dropna=True)['값'].mean()

        for c in companies:
            if c in byc.index:
                res[c] = float(byc[c])

        if '계' in byc.index:
            res['계'] = float(byc['계'])
        else:
            vals = [res[c] for c in companies if pd.notnull(res[c])]
            res['계'] = float(np.mean(vals)) if vals else np.nan

        return res

    items = ['매출채권', '재고자산', '매임채무']

    rows_curr = {it: row_by_month(it, used_y, used_m) for it in items}
    rows_prev = {it: row_by_month(it, prev_y, prev_m) for it in items}

    # ───────── 현금전환주기 ─────────
    def combine_ccc(a, b, c):
        keys = set(a) | set(b) | set(c)
        return {
            k: (a.get(k, 0) or 0) + (b.get(k, 0) or 0) - (c.get(k, 0) or 0)
            for k in keys
        }

    curr_ccc = combine_ccc(rows_curr['매출채권'], rows_curr['재고자산'], rows_curr['매임채무'])
    prev_ccc = combine_ccc(rows_prev['매출채권'], rows_prev['재고자산'], rows_prev['매임채무'])

    # ───────── 출력 DataFrame ─────────
    subcols = list(dict.fromkeys(['계'] + companies))
    cols = pd.MultiIndex.from_product([['당월', '전월비'], subcols])

    index_order = items + ['현금전환주기']
    out = pd.DataFrame(index=index_order, columns=cols, dtype=float)

    def fill_row(it):
        cur, prv = rows_curr[it], rows_prev[it]
        for k in subcols:
            cv, pv = cur.get(k), prv.get(k)
            out.loc[it, ('당월', k)] = cv
            out.loc[it, ('전월비', k)] = (cv - pv) if pd.notnull(cv) and pd.notnull(pv) else np.nan

    for it in items:
        fill_row(it)

    for k in subcols:
        cv, pv = curr_ccc.get(k), prev_ccc.get(k)
        out.loc['현금전환주기', ('당월', k)] = cv
        out.loc['현금전환주기', ('전월비', k)] = (cv - pv) if pd.notnull(cv) and pd.notnull(pv) else np.nan

    out = out.round(1)


    out.attrs['used_year'] = used_y
    out.attrs['used_month'] = used_m
    out.attrs['prev_year'] = prev_y
    out.attrs['prev_month'] = prev_m

    return out



##### ROE #####

# modules.py

import re
import numpy as np
import pandas as pd

# ===== 공통 유틸 =====

ZWS = "\u200b"          
_WS_RE = re.compile(r"\s+", re.UNICODE)

def _clean_str(s):
    """제로폭/비정상 공백 제거 + strip + 내부 공백 1칸화"""
    if pd.isna(s):
        return ""
    t = str(s).replace(ZWS, "")
    t = t.replace("\u00a0", " ")  # NBSP
    t = _WS_RE.sub(" ", t).strip()
    return t

def _norm_kind_label(x):
    """구분3 라벨 통일: 경영계획→계획, sps→SPS 등"""
    t = _clean_str(x).lower()
    if t in ("경영계획","계획","plan"):
        return "계획"
    if t in ("수정계획","replan"):
        return "수정계획"
    if t in ("sps","sps (100점)","sps(100점)"):
        return "SPS"
    if t in ("실적","actual"):
        return "실적"
    return _clean_str(x)  # 기타는 원형 보존

def _norm_scope_label(x):
    """구분4 라벨 통일: 누적/YTD 만 사용"""
    t = _clean_str(x).lower()
    if "누적" in t or "ytd" in t:
        return "누적"
    return _clean_str(x)

def _to_year_col(s: pd.Series) -> pd.Series:
    def _f(x):
        t = _clean_str(x)
        m = re.search(r"\d{2,4}", t)
        if not m:
            return pd.NA
        v = m.group()
        if len(v) == 2:
            v = "20" + v
        try:
            return int(v)
        except:
            return pd.NA
    return s.map(_f).astype("Int64")

def _to_month_col(s: pd.Series) -> pd.Series:
    def _f(x):
        t = _clean_str(x)
        m = re.search(r"\d{1,2}", t)
        return int(m.group()) if m else pd.NA
    return s.map(_f).astype("Int64")

def _to_number(s: pd.Series) -> pd.Series:
    def _f(x):
        if pd.isna(x):
            return np.nan
        t = _clean_str(x).replace(",", "")
        neg = t.startswith("(") and t.endswith(")")
        t = t.strip("()").replace("%","")
        try:
            v = float(t)
            return -abs(v) if neg else v
        except:
            return np.nan
    return s.map(_f)

# ===== ROE 정규화 / 생성 =====

def _normalize_roe_table(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    ROE 원천 데이터 정리:
      - 구분1~4 문자열 클린
      - 연도/월 숫자화
      - 실적: 숫자로 변환하지 않고, 문자열 그대로 클린만
      - ROE_연결 + 누적 데이터만 필터링
    """
    req = ['구분1','구분2','구분3','구분4','연도','월','실적']
    miss = [c for c in req if c not in df_raw.columns]
    if miss:
        raise ValueError(f"ROE 데이터에 필요한 컬럼 누락: {miss}")

    df = df_raw.copy()

    # 문자열 정리
    for c in ['구분1','구분2','구분3','구분4']:
        df[c] = df[c].map(_clean_str)

    # 연도/월 숫자화
    df['연도'] = _to_year_col(df['연도'])
    df['월']   = _to_month_col(df['월'])

    # 실적: 숫자로 변환하지 않고, 문자열만 정리
    df['실적'] = df['실적'].map(_clean_str)

    # 대상: 구분1에 'ROE' 포함(연결), 구분4=누적만
    df = df[df['구분1'].str.contains("ROE", na=False)]
    df['구분3'] = df['구분3'].map(_norm_kind_label)
    df['구분4'] = df['구분4'].map(_norm_scope_label)
    df = df[df['구분4'].eq("누적")]

    return df

def create_roe_table(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    """
    ROE 표 생성.
    - 실적은 문자열로 그대로 사용 (계산 X)
    - (metric, kind, 연도, 월) 조합당 한 행이라 가정하고 첫 값만 사용
    """
    df = _normalize_roe_table(data)

    # 당해 가용월 중 선택월 보정
    avail = sorted(df.loc[df['연도'].eq(year),'월'].dropna().unique())
    used_m = int(month)
    if avail and used_m not in avail:
        le = [m for m in avail if m <= used_m]
        used_m = int(le[-1] if le else avail[-1])

    prev_year, prev_month = year-1, 12

    # 문자열 버전 pick: 조건에 맞는 행 중 가장 늦은 월의 '실적' 문자열 반환
    def pick(metric: str, kind: str, y: int, m: int | None):
        sub = df[
            (df['구분2'].eq(metric)) &
            (df['구분3'].eq(kind)) &
            (df['연도'].eq(y))
        ]

        if len(sub) == 0:
            return pd.NA

        if m is not None:
            mm = sub['월'].dropna().astype(int)
            if len(mm) == 0:
                return pd.NA
            if m in mm.values:
                sub = sub[sub['월'].eq(m)]
            else:
                le = mm[mm.le(m)]
                if len(le):
                    sub = sub[sub['월'].eq(int(le.max()))]
                else:
                    return pd.NA
        else:
            # 계획류: 그 해 가장 늦은 월
            mm = sub['월'].dropna().astype(int)
            if len(mm) == 0:
                return pd.NA
            sub = sub[sub['월'].eq(int(mm.max()))]

        vals = sub['실적'].dropna().astype(str)
        return vals.iloc[0] if len(vals) else pd.NA

    cols = [
        "'" + str(prev_year)[-2:] + "년",
        f"{used_m}월 누적",
        "경영계획",
        "수정계획",
        "SPS (100점)",
    ]
    # 문자열을 담을 것이므로 dtype=object
    out = pd.DataFrame(index=['ROE*','당기순이익*'], columns=cols, dtype=object)

    # ROE
    out.loc['ROE*', cols[0]] = pick('ROE', '실적',      prev_year, prev_month)
    out.loc['ROE*', cols[1]] = pick('ROE', '실적',      year,      used_m)
    out.loc['ROE*', cols[2]] = pick('ROE', '계획',      year,      None)
    out.loc['ROE*', cols[3]] = pick('ROE', '수정계획',  year,      None)
    out.loc['ROE*', cols[4]] = pick('ROE', 'SPS',       year,      None)

    # 당기순이익
    out.loc['당기순이익*', cols[0]] = pick('당기순이익','실적',      prev_year, prev_month)
    out.loc['당기순이익*', cols[1]] = pick('당기순이익','실적',      year,      used_m)
    out.loc['당기순이익*', cols[2]] = pick('당기순이익','계획',      year,      None)
    out.loc['당기순이익*', cols[3]] = pick('당기순이익','수정계획',  year,      None)
    out.loc['당기순이익*', cols[4]] = pick('당기순이익','SPS',       year,      None)

    out.attrs['used_month'] = used_m
    return out


## 손익 별도
from decimal import Decimal, ROUND_HALF_UP

def _halfup0(x):
    """정수 자리 HALF_UP"""
    try:
        return int(Decimal(str(float(x))).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
    except Exception:
        return None

def _halfup1(x):
    """소수 1자리 HALF_UP"""
    try:
        return float(Decimal(str(float(x))).quantize(Decimal('0.0'), rounding=ROUND_HALF_UP))
    except Exception:
        return None

def _num_coerce_pl(x):
    """숫자 파싱: 괄호=음수, 콤마 제거"""
    s = str(x).strip() if x is not None else ""
    if s == "" or s.lower() == "nan":
        return np.nan
    neg = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace(",", "")
    try:
        v = float(s)
        return -abs(v) if neg else v
    except:
        return np.nan

def _coerce_series_pl(s: pd.Series) -> pd.Series:
    return s.map(_num_coerce_pl)

def _norm_label_pl(s: str) -> str:
    if s is None: return ""
    t = str(s).replace("\u3000"," ").strip()
    return t.replace("순금융비요","순금융비용")  

def _ratio(n, d):
    """n/d*100 (둘 다 유효할 때만)"""
    try:
        n = float(n); d = float(d)
        if d == 0 or np.isnan(n) or np.isnan(d):
            return None
        return n/d*100
    except Exception:
        return None

def _diff(a, b):
    """a-b (둘 다 유효할 때만)"""
    try:
        if a is None or b is None: return None
        if isinstance(a, float) and np.isnan(a): return None
        if isinstance(b, float) and np.isnan(b): return None
        return float(a) - float(b)
    except Exception:
        return None

def _fmt_int(v):
    """백만원/천톤 등 정수표시(HALF_UP)"""
    r = _halfup0(v)
    return "" if r is None else f"{r:,}"

def _fmt_pp0(v):
    """증감(정수, 음수만 괄호)"""
    r = _halfup0(v)
    if r is None: return ""
    s = f"{abs(r):,}"
    return f"({s})" if r < 0 else s

def _fmt_pct(v):
    """% 값 1자리(HALF_UP) → '3.5' 형태(기호는 UI에서 묶을 수도)"""
    r = _halfup1(v)
    return "" if r is None else f"{r:.1f}"

def _fmt_pp1(v):
    """증감(퍼센트포인트, 1자리, 음수만 괄호)"""
    r = _halfup1(v)
    if r is None: return ""
    s = f"{abs(r):.1f}"
    return f"({s})" if r < 0 else s




def _sum_metric(df: pd.DataFrame, y: int, m: int, tag: str) -> pd.Series:
    sub = df[(df["연도"]==y) & (df["월"]==m) & (df["구분4"]==tag)]
    if sub.empty:
        return pd.Series(dtype=float)
    return sub.groupby("구분3")["실적"].sum()

def _sum_metric_cum(df: pd.DataFrame, y: int, m: int, tag: str) -> pd.Series:
    sub = df[(df["연도"]==y) & (df["월"]<=m) & (df["구분4"]==tag)]
    if sub.empty:
        return pd.Series(dtype=float)
    return sub.groupby("구분3")["실적"].sum()


def create_pl_separate_hq(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    """
    손익(별도) 표 생성 (고정 스케일 방식).
    - 금액 지표(매출액/영업이익/순금융비용/경상이익)는 '원' 기준이라고 가정하고 여기서 /1,000,000 → '백만원'
    - 판매량은 '톤' 그대로
    - 퍼센트는 (이익/매출액)*100
    """


    money_metrics = ["매출액", "영업이익", "순금융비용", "경상이익"]

    # ── 1) 최소 전처리: 라벨 정리/숫자 파싱/본사 필터(스케일링은 하지 않음) ──
    df = data.copy()

    for c in ["구분1","구분2","구분3","구분4"]:
        if c not in df.columns: df[c] = ""
        df[c] = (
            df[c].astype(str)
                 .str.replace("\u3000"," ")
                 .str.strip()
                 .replace({"순금융비용":"순금융비용"})
        )

    # 본사만
    df = df[df["구분2"] == "본사"].copy()

    # 연/월
    df["연도"] = pd.to_numeric(df.get("연도"), errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df.get("월").astype(str).str.extract(r"(\d+)")[0], errors="coerce").astype("Int64")

    # 숫자 파싱(괄호=음수, 콤마 제거) - 스케일 변환은 아직 X
    def _to_num(x):
        s = str(x).strip() if x is not None else ""
        if s == "" or s.lower() == "nan": return np.nan
        neg = s.startswith("(") and s.endswith(")")
        s = s.replace("(","").replace(")","").replace(",","")
        try:
            v = float(s)
            return -abs(v) if neg else v
        except:
            return np.nan

    df["실적"] = df["실적"].map(_to_num)

    # ── 2) 합계 시리즈 만들기(전월/당월/누적), 금액 지표만 /1e6 고정 스케일 ──
    def _sum_metric_fixed(y: int, m: int, tag: str) -> pd.Series:
        sub = df[(df["연도"]==y) & (df["월"]==m) & (df["구분4"]==tag)]
        if sub.empty: return pd.Series(dtype=float)
        s = sub.groupby("구분3")["실적"].sum()
        # 금액 지표만 백만원 스케일
        for k in money_metrics:
            if k in s.index and pd.notnull(s[k]):
                s[k] = float(s[k]) / 1_000_000.0
        return s

    def _sum_metric_cum_fixed(y: int, m: int, tag: str) -> pd.Series:
        sub = df[(df["연도"]==y) & (df["월"]<=m) & (df["구분4"]==tag)]
        if sub.empty: return pd.Series(dtype=float)
        s = sub.groupby("구분3")["실적"].sum()
        for k in money_metrics:
            if k in s.index and pd.notnull(s[k]):
                s[k] = float(s[k]) / 1_000_000.0
        return s

    # 전월 계산
    prev_y, prev_m = (year-1, 12) if month == 1 else (year, month-1)

    s_prev  = _sum_metric_fixed(prev_y, prev_m, "실적")
    s_cplan = _sum_metric_fixed(year,   month,  "계획")
    s_cact  = _sum_metric_fixed(year,   month,  "실적")
    s_yplan = _sum_metric_cum_fixed(year, month, "계획")
    s_yact  = _sum_metric_cum_fixed(year, month, "실적")

    rows = ['매출액','판매량','영업이익','%(영업)','순금융비용','경상이익','%(경상)']
    cols = ['전월','당월 계획','당월 실적','당월 계획대비','당월 전월대비','누적 계획','누적 실적','누적 계획대비']
    out = pd.DataFrame(index=rows, columns=cols, dtype=object)

    def g(sr, k):
        v = sr.get(k, np.nan)
        try: return float(v)
        except: return np.nan

    # ── 3) 금액/수량 행 포맷(정수/증감) ──
    for mkey in ['매출액','판매량','영업이익','순금융비용','경상이익']:
        prev = g(s_prev,  mkey)
        cp   = g(s_cplan, mkey)
        ca   = g(s_cact,  mkey)
        yp   = g(s_yplan, mkey)
        ya   = g(s_yact,  mkey)

        out.at[mkey,'전월']            = _fmt_int(prev)
        out.at[mkey,'당월 계획']        = _fmt_int(cp)
        out.at[mkey,'당월 실적']        = _fmt_int(ca)
        out.at[mkey,'당월 계획대비']     = _fmt_pp0(_diff(ca, cp))
        out.at[mkey,'당월 전월대비']     = _fmt_pp0(_diff(ca, prev))
        out.at[mkey,'누적 계획']         = _fmt_int(yp)
        out.at[mkey,'누적 실적']         = _fmt_int(ya)
        out.at[mkey,'누적 계획대비']      = _fmt_pp0(_diff(ya, yp))

    # ── 4) 퍼센트 행(이익/매출액*100) ──
    def _ratio_safe(n, d):
        try:
            n = float(n); d = float(d)
            if d == 0 or np.isnan(n) or np.isnan(d): return None
            return n/d*100
        except: return None

    op_prev  = _ratio_safe(g(s_prev,'영업이익'),  g(s_prev,'매출액'))
    op_plan  = _ratio_safe(g(s_cplan,'영업이익'), g(s_cplan,'매출액'))
    op_curr  = _ratio_safe(g(s_cact,'영업이익'),  g(s_cact,'매출액'))
    op_yplan = _ratio_safe(g(s_yplan,'영업이익'), g(s_yplan,'매출액'))
    op_yact  = _ratio_safe(g(s_yact,'영업이익'),  g(s_yact,'매출액'))

    or_prev  = _ratio_safe(g(s_prev,'경상이익'),  g(s_prev,'매출액'))
    or_plan  = _ratio_safe(g(s_cplan,'경상이익'), g(s_cplan,'매출액'))
    or_curr  = _ratio_safe(g(s_cact,'경상이익'),  g(s_cact,'매출액'))
    or_yplan = _ratio_safe(g(s_yplan,'경상이익'), g(s_yplan,'매출액'))
    or_yact  = _ratio_safe(g(s_yact,'경상이익'),  g(s_yact,'매출액'))

    # 영업이익률
    out.at['%(영업)','전월']          = _fmt_pct(op_prev)
    out.at['%(영업)','당월 계획']      = _fmt_pct(op_plan)
    out.at['%(영업)','당월 실적']      = _fmt_pct(op_curr)
    out.at['%(영업)','누적 계획']      = _fmt_pct(op_yplan)
    out.at['%(영업)','누적 실적']      = _fmt_pct(op_yact)
    out.at['%(영업)','당월 계획대비']   = _fmt_pp1(_diff(op_curr, op_plan))
    out.at['%(영업)','당월 전월대비']   = _fmt_pp1(_diff(op_curr, op_prev))

    # 경상이익률
    out.at['%(경상)','전월']          = _fmt_pct(or_prev)
    out.at['%(경상)','당월 계획']      = _fmt_pct(or_plan)
    out.at['%(경상)','당월 실적']      = _fmt_pct(or_curr)
    out.at['%(경상)','누적 계획']      = _fmt_pct(or_yplan)
    out.at['%(경상)','누적 실적']      = _fmt_pct(or_yact)
    out.at['%(경상)','당월 계획대비']   = _fmt_pp1(_diff(or_curr, or_plan))
    out.at['%(경상)','당월 전월대비']   = _fmt_pp1(_diff(or_curr, or_prev))

    # 메타
    out.attrs["units"] = {"money": "백만원(고정스케일)", "qty": "톤", "rate": "%"}
    out.attrs["used_month"] = int(month)
    out.attrs["prev_month"] = int(prev_m)
    return out


##### 실적요약 품목손익(별도) #####

def create_item_pl_table_simple(
    year: int,
    month: int,
    data: pd.DataFrame,
    main_items: list[str] = ("CHQ", "CD", "STS", "BTB", "PB"),
) -> pd.DataFrame:
    import numpy as np
    import pandas as pd

    # 1) 원본 데이터 복사 & 기본 전처리
    df = data.copy()

    for c in ["구분1", "구분2", "구분3", "구분4"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = (
            df[c]
            .astype(str)
            .str.replace("\u3000", " ")
            .str.strip()
        )

    # 연/월 숫자화
    df["연도"] = pd.to_numeric(df.get("연도"), errors="coerce").astype("Int64")
    df["월"] = pd.to_numeric(
        df.get("월").astype(str).str.extract(r"(\d+)")[0],
        errors="coerce"
    ).astype("Int64")

    # 숫자 파싱(괄호=음수, 콤마 제거)
    def _to_num(x):
        s = str(x).strip() if x is not None else ""
        if s == "" or s.lower() == "nan":
            return np.nan
        neg = s.startswith("(") and s.endswith(")")
        s = s.replace("(", "").replace(")", "").replace(",", "")
        try:
            v = float(s)
            return -abs(v) if neg else v
        except:
            return np.nan

    if "실적" in df.columns:
        df["실적"] = df["실적"].map(_to_num)

    # 2) **선택 연/월 + 본사 + 실적** 데이터만 필터
    sub = df[
        (df["연도"] == int(year))
        & (df["월"] == int(month))
        & (df["구분2"] == "본사")
        & (df["구분4"] == "실적")  # 실적만 사용
    ].copy()

    cols = ["합계", *list(main_items), "상품 등"]
    rows = ["매출액", "판매량", "영업이익", "%(영업)", "경상이익", "%(경상)"]
    out = pd.DataFrame(index=rows, columns=cols, dtype=float)

    # 선택월 데이터가 없으면 빈 표 반환
    if sub.empty:
        return out

    # 3) 선택월 데이터만으로 품목/지표별 합계
    #   - 구분1: 품목(CHQ, CD...)
    #   - 구분3: 지표(매출액, 판매량, 영업이익, 경상이익)
    gi = sub.groupby(["구분1", "구분3"])["실적"].sum()

    metrics_n = ["매출액", "판매량", "영업이익", "경상이익"]

    for m in metrics_n:
        # 전체 합계
        if m in gi.index.get_level_values(1):
            tot = gi.xs(m, level="구분3", drop_level=False).sum()
        else:
            tot = 0.0
        out.loc[m, "합계"] = float(tot)

        # 주요 품목별
        s_main = 0.0
        for it in main_items:
            v = gi.get((it, m), np.nan)
            try:
                v = float(v)
            except:
                v = np.nan
            out.loc[m, it] = v
            if pd.notnull(v):
                s_main += v

        # 나머지(상품 등)
        out.loc[m, "상품 등"] = float(tot) - float(s_main)

    # 4) 선택월 기준 영업이익률 / 경상이익률 계산
    den = out.loc["매출액"].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out.loc["%(영업)"] = np.where(
            (den != 0) & np.isfinite(den) & np.isfinite(out.loc["영업이익"]),
            (out.loc["영업이익"] / den) * 100.0,
            np.nan,
        )
        out.loc["%(경상)"] = np.where(
            (den != 0) & np.isfinite(den) & np.isfinite(out.loc["경상이익"]),
            (out.loc["경상이익"] / den) * 100.0,
            np.nan,
        )

    return out



#품목손익 별도
import pandas as pd
import numpy as np
import re

def _parse_number(x) -> float:
    """천단위 콤마/괄호(음수)/공백을 안전하게 숫자로 변환."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s == "":
        return np.nan
    # (12,345) → -12345
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        # '1 234' 같은 경우 한 번 더 정리
        s = re.sub(r"\s+", "", s)
        try:
            return float(s)
        except Exception:
            return np.nan

def create_item_pl_from_flat(
    data: pd.DataFrame,
    year: int,
    month: int,
    main_items: tuple[str, ...] = ("CHQ","CD","STS","BTB","PB"),
    filter_tag: str = "품목손익"
) -> pd.DataFrame:
    """
    주어진 납작한 테이블(구분1~4, 연도, 월, 실적)을 품목손익 표로 변환.
    반환값: 숫자 DataFrame (포맷팅은 페이지에서)
    index: ['매출액','판매량','영업이익','%(영업)','경상이익','%(경상)']
    columns: ['합계', *main_items, '상품 등']
    """
    df = data.copy()

    # 문자열/숫자 정리
    for c in ["구분1","구분2","구분3","구분4"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].astype(str).str.strip()

    # 연/월 숫자화
    df["연도"] = pd.to_numeric(df.get("연도"), errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df.get("월"), errors="coerce").astype("Int64")

    # 실적 숫자화(콤마/괄호 대응)
    df["실적"] = df["실적"].apply(_parse_number)

    # 본사 + 해당 연월 + 품목손익 자료만
    mask = (
        df["구분2"].eq("본사") &
        df["연도"].eq(int(year)) &
        df["월"].eq(int(month)) &
        df["구분1"].str.contains(filter_tag)
    )
    sub = df.loc[mask, ["구분3","구분4","실적"]].copy()

    if sub.empty:
        cols = ["합계", *list(main_items), "상품 등"]
        rows = ["매출액","판매량","영업이익","%(영업)","경상이익","%(경상)"]
        return pd.DataFrame(index=rows, columns=cols, dtype=float)

    # 피벗: 행=지표(구분3), 열=품목/합계(구분4)
    pvt = sub.pivot_table(index="구분3", columns="구분4", values="실적", aggfunc="sum")

    # 출력 틀
    cols = ["합계", *list(main_items), "상품 등"]
    rows = ["매출액","판매량","영업이익","%(영업)","경상이익","%(경상)"]
    out  = pd.DataFrame(index=rows, columns=cols, dtype=float)

    # 숫자 지표 채우기
    money_metrics = ["매출액", "영업이익", "경상이익"]  # ← 백만원으로 변환할 지표

    for m in ["매출액","판매량","영업이익","경상이익"]:
        # 합계
        tot = pvt.get("합계", pd.Series(dtype=float)).get(m, np.nan)
        if pd.notnull(tot) and m in money_metrics:
            tot = float(tot) / 1_000_000.0
        out.at[m, "합계"] = float(tot) if pd.notnull(tot) else np.nan

        s_main = 0.0
        for it in main_items:
            v = pvt.get(it, pd.Series(dtype=float)).get(m, np.nan)
            if pd.notnull(v) and m in money_metrics:
                v = float(v) / 1_000_000.0
            else:
                v = float(v) if pd.notnull(v) else np.nan
            out.at[m, it] = v
            if pd.notnull(v):
                s_main += v

        # 상품 등 = 합계 − 지정 품목 합
        out.at[m, "상품 등"] = (out.at[m, "합계"] - s_main) if pd.notnull(out.at[m, "합계"]) else np.nan

        if m == "판매량":
            out.at[m, "상품 등"] = ""


    # 퍼센트 계산(매출액 분모)
    den = out.loc["매출액", cols].astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        op = out.loc["영업이익", cols].astype(float)
        rp = out.loc["경상이익", cols].astype(float)
        out.loc["%(영업)", cols] = np.where((den!=0)&np.isfinite(den)&np.isfinite(op), (op/den)*100.0, np.nan)
        out.loc["%(경상)", cols] = np.where((den!=0)&np.isfinite(den)&np.isfinite(rp), (rp/den)*100.0, np.nan)
    
    out.at["%(영업)", "상품 등"] = ""
    out.at["%(경상)", "상품 등"] = ""

    return out





## 수정원가기준 손익 (별도)


def _parse_number(x):
    if pd.isna(x): return np.nan
    s = str(x).strip()
    if not s: return np.nan
    neg = s.startswith("(") and s.endswith(")")
    if neg: s = s[1:-1]
    s = s.replace(",", "").replace("%","")
    try:
        v = float(s)
        return -v if neg else v
    except:
        try:
            v = float(re.sub(r"\s+","",s))
            return -v if neg else v
        except:
            return np.nan

def create_item_change_cost_from_flat(
    data: pd.DataFrame,
    year: int,
    month: int,
    col_order=("계","CHQ","CD","STS","BTB","PB","내수","수출"),
):

    # ---- 정리 ----
    df = data.copy()
    for c in ["구분1","구분2","구분3","구분4"]:
        if c not in df.columns: df[c] = ""
        df[c] = df[c].astype(str).str.replace("\n"," ").str.strip()

    df["연도"] = pd.to_numeric(df.get("연도"), errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df.get("월").astype(str).str.extract(r"(\d+)")[0],
                               errors="coerce").astype("Int64")
    if "실적" in df.columns:
        df["실적"] = df["실적"].apply(_parse_number)

    # 연월만 필터 (이 파일은 이미 ‘수정원가기준 별도’만 들어 있음)
    sub = df[(df["연도"].eq(int(year))) & (df["월"].eq(int(month)))].copy()

    # 피벗: index=지표(구분2), columns=구분3(계/CHQ/…)
    if sub.empty:
        present_cols = [c for c in col_order]  # 비어 있어도 프레임 반환
        rows = ["매출액","판매량","X등급 및 재고평가","영업이익","%(영업)","한계이익","%(한계)"]
        return pd.DataFrame(index=rows, columns=present_cols, dtype=object).fillna("")

    pvt = sub.pivot_table(index="구분2", columns="구분3", values="실적", aggfunc="last")
    pvt.index = [s.replace("  "," ").strip() for s in pvt.index]  # 라벨 정리

    # 실제 존재하는 열만 사용 (데이터에 없으면 자동 제외)
    present_cols = [c for c in col_order if c in pvt.columns]
    rows = ["매출액","판매량","X등급 및 재고평가","영업이익","%(영업)","한계이익","%(한계)"]
    out = pd.DataFrame(index=rows, columns=present_cols, dtype=float)

    def gv(metric, col):
        try: return pvt.loc[metric, col]
        except KeyError: return np.nan

    # 1) 기본 지표 채우기
    for r in ["매출액","판매량","영업이익","X등급 및 재고평가"]:
        for c in present_cols:
            out.at[r, c] = gv(r, c)

    # 2) 파생: 한계이익
    for c in present_cols:
        e = out.at["영업이익", c]
        x = out.at["X등급 및 재고평가", c]
        out.at["한계이익", c] = (0 if pd.isna(e) else float(e)) + (0 if pd.isna(x) else float(x))
        if pd.isna(e) and pd.isna(x):
            out.at["한계이익", c] = np.nan

    # 3) 퍼센트 계산 (파일의 % 행은 사용하지 않고 직접 산출)
    for pct_name, num_name in [("%(영업)","영업이익"),("%(한계)","한계이익")]:
        den = out.loc["매출액", present_cols].astype(float)
        num = out.loc[num_name, present_cols].astype(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            out.loc[pct_name, present_cols] = np.where(
                (den!=0)&np.isfinite(den)&np.isfinite(num), (num/den)*100.0, np.nan
            )

    # 4) NaN → 공란
    out = out.astype("object")
    out.iloc[:, :] = out.where(pd.notnull(out), "")

    return out

##### 원재료 입고-기초 단가 차이 #####



def create_9(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"] = pd.to_numeric(df["월"], errors="coerce")
    df["실적"] = pd.to_numeric(df["실적"].astype(str).str.replace(",", ""), errors="coerce")

    target_name = "원재료 입고-기초 단가 차이"
    df = df[(df["구분1"] == target_name) & (df["연도"] == year) & (df["월"] == month)].copy()

    pvt = (
        df.pivot_table(
            index="구분2",      # 메이커
            columns="구분3",    # 중량/금액/단가
            values="실적",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename(columns={"구분2": "메이커"})
    )

    for col in ["중량", "금액", "단가"]:
        if col not in pvt.columns:
            pvt[col] = 0

    pvt = pvt[["메이커", "중량", "금액", "단가"]]

    # 행 순서 고정
    maker_order = [
        "포스코",
        "JFE STEEL(S)",
        "세아창원특수강",
        "현대제철",
        "세아베스틸",
        "합계",
    ]

    # 데이터 없더라도 행 유지
    pvt2 = pvt.set_index("메이커").reindex(maker_order)

    # 숫자 NaN → 0
    for c in ["중량", "금액", "단가"]:
        pvt2[c] = pd.to_numeric(pvt2[c], errors="coerce").fillna(0)

    return pvt2.reset_index()

##### 원재료 입고-기초 단가 차이 거래처 기준 #####

def create_10(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"] = pd.to_numeric(df["월"], errors="coerce")
    df["실적"] = pd.to_numeric(df["실적"].astype(str).str.replace(",", ""), errors="coerce")

    target_name = "원재료 입고 단가차이_거래처 기준"
    df = df[(df["구분1"] == target_name) & (df["연도"] == year) & (df["월"] == month)].copy()

    pvt = (
        df.pivot_table(
            index="구분2",      # 메이커
            columns="구분3",    # 금액/단가
            values="실적",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename(columns={"구분2": "메이커"})
    )

    for col in ["금액", "단가"]:
        if col not in pvt.columns:
            pvt[col] = 0

    pvt = pvt[["메이커", "금액", "단가"]]

    # 행 순서 고정
    maker_order = [
        "포스코_일반",
        "포스코_산업",
        "JFE STEEL(S)",
        "세아창원특수강",
        "현대제철",
        "세아베스틸",
        "합계",
    ]

    # 데이터 없더라도 행 유지
    pvt2 = pvt.set_index("메이커").reindex(maker_order)

    # 숫자 NaN → 0
    for c in ["금액", "단가"]:
        pvt2[c] = pd.to_numeric(pvt2[c], errors="coerce").fillna(0)

    return pvt2.reset_index()



## 제품수불표

# === 제품수불표: 연산 전용 ===


def _pf_to_num(s: pd.Series) -> pd.Series:
    s = s.fillna("").astype(str)
    s = s.str.replace(",", "", regex=False).str.replace(r"\s+", "", regex=True)
    v = pd.to_numeric(s, errors="coerce")
    return v.fillna(0.0)

def _clean_product_flow(df_raw: pd.DataFrame) -> pd.DataFrame:
    need = {"구분1","구분2","구분3","연도","월","실적"}
    miss = need - set(df_raw.columns)
    if miss:
        raise ValueError(f"[제품수불표] 필수 컬럼 누락: {miss}")
    df = df_raw.copy()

    # 텍스트 정규화
    for c in ["구분1","구분2","구분3","구분4"]:
        if c not in df.columns: df[c] = ""
        df[c] = (df[c].astype(str)
                     .str.replace("\xa0", " ")
                     .str.replace(r"\s+", " ", regex=True)
                     .str.strip())

    # 숫자화
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df["월"],   errors="coerce").astype("Int64")
    df["실적"] = _pf_to_num(df["실적"])

    # 제품수불표만
    df = df[df["구분1"] == "제품수불표"].copy()
    # 동일(구분2,구분3)이 여러 줄이면 ‘마지막 값’ 사용하도록 순서 기억
    df["__ord__"] = range(len(df))
    return df

def create_product_flow_base(year: int,
                             month: int,
                             data: pd.DataFrame,
                             amount_div: float = 1_000_000) -> pd.DataFrame:
    """
    원천 데이터에서 해당 연·월의 값을 뽑아 1행짜리 '연산 결과 테이블'을 돌려준다.
    - 반환 컬럼(숫자만, 포맷/헤더 없음):
      ['입고-기초_단가','입고-기초_금액','매출원가-기초_단가','매출원가-기초_금액']
    - 금액은 amount_div로 나눠 단위를 맞춘다(기본: 원→백만원).
    """
    df = _clean_product_flow(data)

    sel = df[(df["연도"] == year) & (df["월"] == month)].copy()
    # 마지막 값 우선
    sel = sel.sort_values("__ord__").drop_duplicates(["구분2","구분3"], keep="last")

    # 피벗(없으면 0.0)
    pv = sel.pivot_table(index="구분2", columns="구분3", values="실적", aggfunc="last")
    get = lambda g2, g3: float(pv.get(g3, pd.Series()).get(g2, 0.0))

    in_unit     = get("입고-기초", "단가")
    in_amount   = get("입고-기초", "금액") / amount_div
    cogs_unit   = get("매출원가-기초", "단가")
    cogs_amount = get("매출원가-기초", "금액") / amount_div

    base = pd.DataFrame([{
        "입고-기초_단가": in_unit,
        "입고-기초_금액": in_amount,
        "매출원가-기초_단가": cogs_unit,
        "매출원가-기초_금액": cogs_amount,
    }])
    # 나중에 화면에서 쓸 메타 정보도 같이 보관(옵션)
    base.attrs["unit_label"] = "백만원" if amount_div == 1_000_000 else ""
    base.attrs["year"] = year
    base.attrs["month"] = month
    return base


## 현금흐름표 별도


def _to_num_cf(s: pd.Series) -> pd.Series:
    s = s.fillna("").astype(str).str.replace(",", "", regex=False).str.strip()
    v = pd.to_numeric(s, errors="coerce")
    return v.fillna(0.0)

def _clean_cf_separate(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    need = {"구분1","구분2","연도","월","실적"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"필수 컬럼 누락: {miss}")
    for c in ["구분1","구분2","구분3","구분4"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df["월"],   errors="coerce").astype("Int64")
    df["실적"] = _to_num_cf(df["실적"])
    # 별도만 사용
    df = df[df["구분1"] == "현금흐름표_별도"].copy()
    # 원본 등장 순서 보존용
    df["__ord__"] = range(len(df))
    return df

def create_cashflow_separate_by_order(year: int, month: int, data: pd.DataFrame, item_order: list[str]) -> pd.DataFrame:
    """
    - 행: item_order 순서를 그대로 사용 (중복 라벨 허용; 예: '기타' 2번)
    - 열: (year-2)년, (year-1)년, 전월누적, 당월누적, (year)년누적
    - 선택월에 (item_order에 해당하는) 데이터가 없으면: 표 계산을 하지 않고 NaN으로만 채운 표를 반환
    """
    import numpy as np
    import pandas as pd

    df = _clean_cf_separate(data)

    # item_order에서 같은 라벨(예: '기타')의 n번째 등장 번호 지정
    name_counts = {}
    order_with_n = []
    for name in item_order:
        name_counts[name] = name_counts.get(name, 0) + 1
        order_with_n.append((name, name_counts[name]))  # ('기타', 1), ('기타', 2) ...

    # 인덱스는 원래 라벨 그대로
    index_labels = [nm for (nm, _) in order_with_n]

    # 열 라벨
    col_prev2_label   = f"{str(year-2)[-2:]}년"
    col_prev1_label   = f"{str(year-1)[-2:]}년"
    col_currsum_label = f"{str(year)[-2:]}년누적"

    # ── 핵심: "선택월 + item_order에 해당하는 데이터" 존재 여부 체크 ──
    sel_month = df[
        (df["연도"] == year)
        & (df["월"] == month)
        & (df["구분2"].isin(item_order))
    ]

    # 선택월에 item_order 대상 데이터가 하나도 없으면 NaN 테이블 반환
    if sel_month.empty:
        out = pd.DataFrame(
            {
                col_prev2_label:   [np.nan] * len(index_labels),
                col_prev1_label:   [np.nan] * len(index_labels),
                "전월누적":         [np.nan] * len(index_labels),
                "당월누적":         [np.nan] * len(index_labels),
                col_currsum_label: [np.nan] * len(index_labels),
            },
            index=pd.Index(index_labels, name="구분"),
            dtype=float,
        )
        out.attrs["used_month"] = None
        out.attrs["prev_month"] = None
        return out

    # 선택월에 데이터가 있는 경우에만 연산 진행
    used_month = int(month)

    # (핵심) 라벨의 n번째 등장만 골라 합산
    def _sum_item_nth(name: str, nth: int, years, months):
        sub = df[(df["연도"].isin(years)) & (df["월"].isin(months))]
        total = 0.0
        # (연,월)별로, 해당 라벨의 nth 등장 행만 집계
        for (_, _), g in sub.groupby(["연도", "월"], sort=False):
            g = g[g["구분2"] == name].sort_values("__ord__", kind="stable")
            if len(g) >= nth:
                total += float(g.iloc[nth - 1]["실적"])
        return total

    def _block(years, months):
        return [_sum_item_nth(nm, nth, years, months) for (nm, nth) in order_with_n]

    col_prev2 = _block([year-2], range(1, 13))
    col_prev1 = _block([year-1], range(1, 13))

    prev_months = range(1, used_month) if used_month > 1 else []
    col_prev   = _block([year], prev_months) if prev_months else [0.0] * len(order_with_n)
    col_ytd    = _block([year], range(1, used_month + 1))

    out = pd.DataFrame(
        {
            col_prev2_label:   col_prev2,
            col_prev1_label:   col_prev1,
            "전월누적":         col_prev,
            "당월누적":         col_ytd,
            col_currsum_label: col_ytd,
        },
        index=pd.Index(index_labels, name="구분"),
        dtype=float
    )

    out.attrs["used_month"] = used_month
    out.attrs["prev_month"] = (used_month - 1) if used_month > 1 else 1
    return out







#####재무상태표 별도

def _bs_to_number(x):
    s = str(x).strip()
    if not s:
        return 0.0
    neg = s.startswith('(') and s.endswith(')')
    s = s.replace('(', '').replace(')', '').replace(',', '')
    try:
        v = float(s)
    except Exception:
        return 0.0
    return -abs(v) if neg else v


def _normalize_bs_simple(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    # 항목 / 회사 컬럼 찾기
    item_col = next((c for c in ['구분3','구분2','항목','구분'] if c in df.columns), None)
    comp_col = next((c for c in ['회사','법인','구분4'] if c in df.columns), None)

    for need in ['연도','월','실적']:
        if need not in df.columns:
            raise ValueError(f"재무상태표 데이터에 '{need}' 컬럼이 필요합니다.")
    if item_col is None:
        raise ValueError("재무상태표: '구분3/구분2/항목/구분' 중 하나가 필요합니다.")

    df[item_col] = df[item_col].astype(str).str.strip()

    if comp_col is None:
        comp_col = '_회사'
        df[comp_col] = '전체'
    else:
        df[comp_col] = (
            df[comp_col]
            .astype(str)
            .str.strip()
            .replace({'타이':'태국'})
        )

    # 숫자 파싱 (괄호=음수, 콤마 제거)
    s = df['실적'].astype(str).str.strip()
    neg = s.str.match(r'^\(.*\)$')
    s = s.str.replace(r'[(),]', '', regex=True)
    v = pd.to_numeric(s, errors='coerce').fillna(0.0)
    v[neg] = -v[neg].abs()
    df['실적'] = v

    df['연도'] = pd.to_numeric(df['연도'], errors='coerce').astype('Int64')
    df['월']   = pd.to_numeric(df['월'],   errors='coerce').astype('Int64')

    drop_cols = [c for c in df.columns if str(c).startswith('Unnamed')]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors='ignore')

    return df.rename(columns={item_col:'구분3', comp_col:'회사'})


def create_bs_from_teuksugang(
    year: int,
    month: int,
    data: pd.DataFrame,
    item_order: list[str],
) -> pd.DataFrame:

    # 1) 원본에서 '구분2'로 선필터 (특수강만 사용)
    if '구분2' not in data.columns:
        raise ValueError("'구분2' 컬럼이 없습니다. 원본 스키마를 확인하세요.")

    df_src = data.copy()
    df_src['구분2'] = df_src['구분2'].astype(str).str.strip()
    df_src = df_src[df_src['구분2'] == '특수강'].copy()

    if df_src.empty:
        raise ValueError("원본 '구분2'에서 '특수강' 데이터를 찾지 못했습니다.")

    # 2) 정규화
    df = _normalize_bs_simple(df_src)  # '구분3','연도','월','실적','회사' 등

    req_y = int(year)
    req_m = int(month)

    # 선택월/전월 (연도 경계 포함)
    used_y = req_y
    used_m = req_m

    if used_m > 1:
        prev_y = used_y
        prev_m = used_m - 1
    else:
        prev_y = used_y - 1
        prev_m = 12

    # 연도 포맷(두 자리)
    yy_prev = f"{(used_y - 1) % 100:02d}"   # 전년도
    yy_curr = f"{used_y % 100:02d}"         # 선택연도

    # 이 재무상태표가 "월별 잔액" 형태로 저장돼 있다고 가정
    sel_curr = df[(df['연도'] == used_y) & (df['월'] == used_m)]

    index_labels = pd.Index(item_order, name='구분')

    # 3) 선택월에 데이터가 전혀 없으면: 폴백 없이 "빈 표" 생성
    if sel_curr.empty:
        # 내부 컬럼명(계산용)
        col_yend = f"'{yy_prev}년말"          # 전년도 12월
        col_prev = f"'{yy_curr}년 선택전 월"  # 선택 전월
        col_curr = f"'{yy_curr}년 선택월"     # 선택월

        out = pd.DataFrame(
            {
                col_yend: [0.0] * len(index_labels),
                col_prev: [0.0] * len(index_labels),
                col_curr: [0.0] * len(index_labels),
                "전월대비": [0.0] * len(index_labels),
            },
            index=index_labels,
            dtype=float,
        )

        out = out.rename(columns={
            col_yend: f"'{yy_prev}년말",   # 예: '24년말
            col_prev: f"'{yy_curr}",      # 예: '25
            col_curr: "당월",
            "전월대비": "전월비 증감",
        })
        out = out[[f"'{yy_prev}년말", f"'{yy_curr}", "당월", "전월비 증감"]]

        # 메타 정보
        out.attrs['base_year']  = used_y
        out.attrs['used_year']  = used_y
        out.attrs['used_month'] = used_m
        out.attrs['prev_year']  = prev_y
        out.attrs['prev_month'] = prev_m
        return out

    # 4) 선택월에 데이터가 있는 경우: 정상 계산
    # 합계 헬퍼
    def _sum_item(item: str, y: int | None, m: int | None) -> float:
        if y is None or m is None:
            return 0.0
        mask = (
            (df['구분3'].astype(str).str.strip() == item)
            & (df['연도'] == y)
            & (df['월'] == m)
        )
        return float(df.loc[mask, '실적'].sum())

    # 5) 컬럼 라벨(내부)
    col_yend = f"'{yy_prev}년말"
    col_prev = f"'{yy_curr}년 선택전 월"
    col_curr = f"'{yy_curr}년 선택월"

    # 6) 행 구성 (item_order 그대로)
    rows = []
    for item in item_order:
        v_yend = _sum_item(item, used_y - 1, 12)  # 전년도 12월
        v_prev = _sum_item(item, prev_y, prev_m)  # 선택전 월
        v_curr = _sum_item(item, used_y, used_m)  # 선택월
        rows.append({
            col_yend:   v_yend,
            col_prev:   v_prev,
            col_curr:   v_curr,
            "전월대비": v_curr - v_prev,
        })

    out = pd.DataFrame(rows, index=index_labels).fillna(0.0)

    # 7) 뷰 호환용 컬럼명
    out = out.rename(columns={
        col_yend: f"'{yy_prev}년말",  # 전년도 12월 (예: '24년말)
        col_prev: f"'{yy_curr}",     # 전월 컬럼 (예: '25)
        col_curr: "당월",            # 선택월
        "전월대비": "전월비 증감",
    })

    out = out[[f"'{yy_prev}년말", f"'{yy_curr}", "당월", "전월비 증감"]]

    # 8) 메타 정보 (뷰 헤더에서 사용)
    out.attrs['base_year']  = used_y
    out.attrs['used_year']  = used_y
    out.attrs['used_month'] = used_m
    out.attrs['prev_year']  = prev_y
    out.attrs['prev_month'] = prev_m

    return out




###회전일 (별도)

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────
# 공통 유틸: 괄호음수 + 쉼표 제거
# ─────────────────────────────────────────────────────────────
def _num_paren(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    neg = s.str.match(r'^\(.*\)$')
    s = s.str.replace(r'[(),]', '', regex=True)
    v = pd.to_numeric(s, errors='coerce')
    v[neg] = -v[neg].abs()
    return v


# ─────────────────────────────────────────────────────────────
# 원천 정규화 (표준 스키마: 구분 / 회사 / 값 / 연도 / 월)
# ─────────────────────────────────────────────────────────────
def _normalize_turnover_v2(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    회전일 원천을 표준 스키마로 정리:
      - 항목: '구분'
      - 회사: '회사'
      - 값  : '값'
    회사명이 구분3(계/특수강/남통/천진/태국 등)에 들어있는 경우도 자동 감지.
    """
    df = df_raw.copy()

    # 값/항목/회사 후보
    val_col = next((c for c in ['회전일','실적','값','value'] if c in df.columns), None)
    if val_col is None:
        raise ValueError("회전일 데이터에 '회전일/실적/값' 컬럼이 필요합니다.")

    # 기본 숫자/연월 정리
    df['연도'] = pd.to_numeric(df['연도'], errors='coerce').astype('Int64')
    df['월']   = pd.to_numeric(df['월'],   errors='coerce').astype('Int64')

    # 괄호 음수 → 음수, 쉼표 제거
    df[val_col] = _num_paren(df[val_col]).astype(float)

    # 후보 열들
    cand_item = ['구분3','구분2','구분','항목']
    cand_comp = ['회사','법인','구분4']

    # 회사/항목 기본 선택
    item_col = next((c for c in cand_item if c in df.columns), None)
    comp_col = next((c for c in cand_comp if c in df.columns), None)

    # 회사명이 구분3에 들어있는 케이스 감지
    known_companies = {'계','전체','연결','특수강','본사','남통','남동','천진','태국','타이'}
    def looks_like_company(series) -> bool:
        s = series.astype(str).str.strip()
        nonnull = s[s != ""]
        if len(nonnull) == 0: 
            return False
        hit = nonnull.isin(known_companies).mean()
        return hit >= 0.7

    if ('구분3' in df.columns) and (comp_col is None or looks_like_company(df['구분3'])):
        comp_col = '구분3'
        # 항목은 구분2 > 구분 > 항목 순으로
        item_col = next((c for c in ['구분2','구분','항목'] if c in df.columns and c != comp_col), item_col)

    if item_col is None:
        raise ValueError("회전일 데이터에 항목 컬럼(구분3/구분2/구분/항목) 중 하나가 필요합니다.")

    # 문자열 정리 + alias
    df[item_col] = df[item_col].astype(str).str.strip()
    if comp_col is None:
        comp_col = '_회사'
        df[comp_col] = '전체'
    df[comp_col] = (
        df[comp_col].astype(str).str.strip()
          .replace({'타이':'태국', '남동':'남통'})   # alias 통일
    )

    # 쓰지 않는 Unnamed 열 제거
    drop_cols = [c for c in df.columns if str(c).startswith('Unnamed')]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors='ignore')

    return df.rename(columns={item_col: '구분', comp_col: '회사', val_col: '값'})




def create_turnover_special_steel(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    """
    행: 매출채권 / 재고자산 / 매임채무 / 현금전환주기
    열: '{YY}년말' / '{YY}.{prev_m} 월' / '{YY}.{m} 월' / '전월대비'

    - 구분3 == '특수강' 행만 사용
    - 선택월(year, month)에 특수강 데이터가 없으면:
        → 폴백 없이, 표 구조는 유지하되 값은 전부 NaN (포맷 단계에서 ""로 표시)
    - 선택월에 데이터가 있으면:
        → 전년도 12월(없으면 선택연도 1월), 선택전월(month-1 또는 전년도 12월), 선택월 기준으로 값 계산
    """
    req_y = int(year)
    req_m = int(month)

    # 1) 원천 정규화
    df_norm = _normalize_turnover_v2(data)

    # alias 통일 함수
    def norm_comp(x: str) -> str:
        x = str(x).strip()
        x = {'타이': '태국', '남동': '남통'}.get(x, x)
        if x in ('전체', '연결'):
            return '계'
        return x

    # 2) 특수강 필터
    if '구분3' in data.columns:
        g3norm = (data['구분3'].astype(str).str.strip()
                               .replace({'타이':'태국', '남동':'남통'}))
        mask = g3norm.eq('특수강')
        df = df_norm.loc[mask].copy()
    else:
        df = df_norm.loc[df_norm['회사'].map(norm_comp).eq('특수강')].copy()

    # 인덱스 (항목)
    items = ['매출채권', '재고자산', '매임채무']
    idx = ['매출채권', '재고자산', '매임채무', '현금전환주기']

    # 3) 선택월에 특수강 데이터 존재 여부 체크
    sel_curr = df[(df['연도'] == req_y) & (df['월'] == req_m)]

    # 4) 전월/전년도 말 라벨은 선택월과 무관하게 항상 동일 규칙으로 생성
    prev_year = req_y - 1
    yend_label_year = prev_year        # '25년말' 같은 라벨용 연도
    yend_data_year  = prev_year        # 기본은 전년도 연말(=12월)을 바라봄

    if req_m > 1:
        prev_y = req_y
        prev_m = req_m - 1
    else:
        prev_y = req_y - 1
        prev_m = 12

    col_yend = f"'{str(yend_label_year)[-2:]}년말"
    col_prev = f"'{str(prev_y)[-2:]}.{prev_m} 월"
    col_curr = f"'{str(req_y)[-2:]}.{req_m} 월"

    # 5) 선택월에 데이터가 전혀 없으면: 폴백 없이 "모두 NaN" 표 생성
    if sel_curr.empty:
        out = pd.DataFrame(
            np.nan,
            index=pd.Index(idx, name=None),
            columns=[col_yend, col_prev, col_curr, '전월대비'],
            dtype=float,
        )

        out.attrs.update({
            'company': '특수강',
            'used_month': req_m,
            'prev_month': prev_m,
            'year_end_label_year': yend_label_year,
            # 여기서는 실제 계산 안 하니까 "이론상" 전년도 12월로만 기록
            'year_end_data': (yend_data_year, 12),
        })
        return out

    # 6) (여기서부터는 선택월에 데이터가 있을 때만) 정상 계산

    # ★ 전년도 12월이 있으면 그걸 연말로 사용
    #    없으면 선택연도 1월 데이터를 연말로 폴백
    mask_prev_dec = (df['연도'] == prev_year) & (df['월'] == 12)
    if df.loc[mask_prev_dec].empty:
        # 전년도 12월 데이터가 없을 때만 → 선택연도 1월 사용
        yend_data_year = req_y
        yend_m = 1
    else:
        # 전년도 12월 있음 → 그대로 사용
        yend_data_year = prev_year
        yend_m = 12

    # 단일 월·항목 값 추출 (중복행은 회사별 평균, 없으면 NaN)
    def val_of(item: str, y: int, m: int) -> float:
        sub = df[(df['구분'] == item) & (df['연도'] == y) & (df['월'] == m)].copy()
        if sub.empty:
            return np.nan
        sub['회사N'] = sub['회사'].map(norm_comp)
        byc = sub.groupby('회사N', dropna=True)['값'].mean()
        if '특수강' in byc.index:
            return float(byc['특수강'])
        return np.nan

    yend = {it: val_of(it, yend_data_year, yend_m) for it in items}
    prev = {it: val_of(it, prev_y,           prev_m) for it in items}
    curr = {it: val_of(it, req_y,            req_m)  for it in items}

    # 현금전환주기 = 매출채권 + 재고자산 - 매임채무
    def ccc(dic):
        vals = [dic.get('매출채권', np.nan),
                dic.get('재고자산', np.nan),
                dic.get('매임채무', np.nan)]
        # 셋 다 NaN이면 NaN 그대로 반환 → 빈칸
        if all(pd.isna(v) for v in vals):
            return np.nan
        # 일부만 있으면 없는 것만 0으로 보고 계산
        a = 0 if pd.isna(vals[0]) else vals[0]
        b = 0 if pd.isna(vals[1]) else vals[1]
        c = 0 if pd.isna(vals[2]) else vals[2]
        return a + b - c

    yend_ccc = ccc(yend)
    prev_ccc = ccc(prev)
    curr_ccc = ccc(curr)

    # 7) 표 구성 (어디에서도 fillna(0) 안 씀!)
    out = pd.DataFrame(
        index=pd.Index(idx, name=None),
        columns=[col_yend, col_prev, col_curr, '전월대비'],
        dtype=float
    )

    for it in items:
        out.loc[it, col_yend] = yend[it]
        out.loc[it, col_prev] = prev[it]
        out.loc[it, col_curr] = curr[it]
        out.loc[it, '전월대비'] = (
            curr[it] - prev[it] if pd.notnull(curr[it]) and pd.notnull(prev[it]) else np.nan
        )

    out.loc['현금전환주기', col_yend] = yend_ccc
    out.loc['현금전환주기', col_prev] = prev_ccc
    out.loc['현금전환주기', col_curr] = curr_ccc
    out.loc['현금전환주기', '전월대비'] = (
        curr_ccc - prev_ccc if pd.notnull(curr_ccc) and pd.notnull(prev_ccc) else np.nan
    )

    out.attrs.update({
        'company': '특수강',
        'used_month': req_m,
        'prev_month': prev_m,
        'year_end_label_year': yend_label_year,
        'year_end_data': (yend_data_year, yend_m),
    })
    return out





##### 수익성 #####


import numpy as np
import pandas as pd

def create_profitability_special_steel(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    """
    - 대상: 본사(구분3 == '본사' 또는 회사 라벨상 '본사')
    - 항목: ROA, ROE
    - 열:
        '{YY}년말'       : 전년도 말 (라벨은 year-1, 데이터는 전년도 12월. 12월이 없으면 선택연도 1월로 폴백)
        '{YY}.{prev} 월' : 선택월의 직전월 (1월이면 전년도 12월)
        '{YY}.{m} 월'    : 선택월
        '전월대비'       : 선택월 - 전월

    ⚠︎ 선택한 (year, month)에 해당 항목(ROA/ROE) 데이터가 하나도 없으면:
       → 어떤 폴백도 하지 않고, 표 구조는 유지하되 값은 모두 NaN.
    """
    req_y = int(year)
    req_m = int(month)

    # 0) 원본 복사 및 기본 컬럼 정리
    df_norm = data.copy()

    if "구분" not in df_norm.columns and "구분2" in df_norm.columns:
        df_norm["구분"] = df_norm["구분2"]
    if "회사" not in df_norm.columns and "구분3" in df_norm.columns:
        df_norm["회사"] = df_norm["구분3"]
    if "값" not in df_norm.columns and "실적" in df_norm.columns:
        df_norm["값"] = (
            df_norm["실적"].astype(str).str.strip().str.replace("%", "", regex=False)
        )

    for c in ["연도", "월"]:
        if c in df_norm.columns:
            df_norm[c] = pd.to_numeric(df_norm[c], errors="coerce").astype("Int64")
    if "값" in df_norm.columns:
        df_norm["값"] = pd.to_numeric(df_norm["값"], errors="coerce")
    for c in ["구분", "회사", "구분3"]:
        if c in df_norm.columns:
            df_norm[c] = df_norm[c].astype(str).str.strip()

    # alias 통일
    def norm_comp(x: str) -> str:
        x = str(x).strip()
        x = {"타이": "태국", "남동": "남통"}.get(x, x)
        if x in ("전체", "연결"):
            return "계"
        return x

    # 1) 본사 필터 (구분3 기준이 우선, 없으면 회사 기준)
    if "구분3" in df_norm.columns:
        g3norm = df_norm["구분3"].astype(str).str.strip().replace({"타이": "태국", "남동": "남통"})
        df = df_norm.loc[g3norm.eq("본사")].copy()
    else:
        df = df_norm.loc[df_norm["회사"].map(norm_comp).eq("본사")].copy()

    items = ["ROA", "ROE"]

    # 2) 선택월에 본사 ROA/ROE 데이터 존재 여부 체크
    sel_curr = df[
        (df["연도"] == req_y)
        & (df["월"] == req_m)
        & (df["구분"].isin(items))
    ]

    # 3) 전월 (단순 계산: month-1, 1월이면 전년도 12월)
    if req_m > 1:
        prev_y = req_y
        prev_m = req_m - 1
    else:
        prev_y = req_y - 1
        prev_m = 12

    # 4) '전년도 말' 라벨/참조 정보
    prev_year = req_y - 1
    yend_label_year = prev_year     # 라벨용: '24년말 등
    yend_data_year = prev_year      # 기본은 전년도 연말(=12월)을 바라봄

    # 5) 컬럼 라벨 (선택월 데이터 유무와 상관없이 동일 규칙)
    col_yend = f"'{str(yend_label_year)[-2:]}년말"          # 예: '24년말
    col_prev = f"'{str(prev_y)[-2:]}.{int(prev_m)} 월"
    col_curr = f"'{str(req_y)[-2:]}.{int(req_m)} 월"

    # 6) 선택월에 데이터가 전혀 없으면: 폴백 없이 "빈 표" (모두 NaN)
    if sel_curr.empty:
        out = pd.DataFrame(
            np.nan,
            index=pd.Index(items, name=None),
            columns=[col_yend, col_prev, col_curr, "전월대비"],
            dtype=float,
        )

        out.attrs.update({
            "company": "본사",
            "used_month": req_m,
            "prev_month": prev_m,
            "year_end_label_year": yend_label_year,
            # 논리상 전년도 12월을 연말로 간주 (실제값은 NaN)
            "year_end_data": (yend_data_year, 12),
        })
        return out

    # 7) (여기부터는 선택월에 데이터가 있을 때만) 정상 계산
    # 전년도 12월이 있으면 그걸 연말로 사용, 없으면 선택연도 1월 사용
    mask_prev_dec = (df["연도"] == prev_year) & (df["월"] == 12)
    if df.loc[mask_prev_dec].empty:
        # 전년도 12월 데이터가 없을 때만 → 선택연도 1월로 폴백
        yend_data_year = req_y
        yend_m = 1
    else:
        # 전년도 12월 있음 → 그대로 사용
        yend_data_year = prev_year
        yend_m = 12

    # 값 조회 (본사 행 중복 시 평균)
    def val_of(item: str, y: int, m: int) -> float:
        sub = df[(df["구분"] == item) & (df["연도"] == y) & (df["월"] == m)].copy()
        if sub.empty:
            return np.nan
        if "회사" in sub.columns:
            sub["회사N"] = sub["회사"].map(norm_comp)
        elif "구분3" in sub.columns:
            sub["회사N"] = sub["구분3"].map(norm_comp)
        else:
            sub["회사N"] = "본사"
        byc = sub.groupby("회사N", dropna=True)["값"].mean()
        return float(byc["본사"]) if "본사" in byc.index else np.nan

    yend = {it: val_of(it, yend_data_year, int(yend_m)) for it in items}
    prev = {it: val_of(it, prev_y,           int(prev_m)) for it in items}
    curr = {it: val_of(it, req_y,            int(req_m))  for it in items}

    out = pd.DataFrame(
        index=pd.Index(items, name=None),
        columns=[col_yend, col_prev, col_curr, "전월대비"],
        dtype=float
    )

    for it in items:
        out.loc[it, col_yend] = yend[it]
        out.loc[it, col_prev] = prev[it]
        out.loc[it, col_curr] = curr[it]
        out.loc[it, "전월대비"] = (
            curr[it] - prev[it] if pd.notnull(curr[it]) and pd.notnull(prev[it]) else np.nan
        )

    # 메타
    out.attrs.update({
        "company": "본사",
        "used_month": req_m,
        "prev_month": prev_m,
        "year_end_label_year": yend_label_year,
        "year_end_data": (yend_data_year, int(yend_m)),
    })
    return out




#####판매계획 및 실적



__all__ = ["create_sales_plan_vs_actual"]

# ---- 단위 스케일 정의 (원천 기준 가정)
AMOUNT_SCALE = 1 / 100   
UNIT_SCALE   = 1000      

def _to_number(x):
    s = str(x).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return np.nan
    s = s.replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        try:
            return -float(s.strip("()"))
        except:
            pass
    try:
        return float(s)
    except:
        return np.nan

def _trunc(v):
    """소수 버림(끊기). NaN은 그대로."""
    if pd.isna(v):
        return np.nan
    return float(np.trunc(v))

def create_sales_plan_vs_actual(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    """
    연간사업계획 > 1) 판매계획 및 실적 (연산 모듈)
    - 출력 단위: 판매량=톤(정수), 단가=천개(정수), 매출액=억원(정수)
    """
    df = data.copy()

    # 0) 문자열 정리/숫자화
    for c in ["구분1", "구분2", "구분3", "구분4"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].astype(str).str.replace("\u00A0", "", regex=False).str.strip()

    df["연도"] = pd.to_numeric(df.get("연도"), errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df.get("월"),   errors="coerce").astype("Int64")
    df["실적"] = df["실적"].apply(_to_number)

    # 1) 키/조건
    y = int(year)
    m = int(month)
    key = ["구분2", "구분3", "구분4"]

    # 2) 합계 시리즈(원천 단위: 판매량=톤, 매출액=백만원)
    def sum_year(flag: str):
        q = (df["연도"] == y) & (df["구분4"] == flag)
        return df[q].groupby(key)["실적"].sum()

    def sum_cum(flag: str):
        q = (df["연도"] == y) & (df["월"].between(1, m)) & (df["구분4"] == flag)
        return df[q].groupby(key)["실적"].sum()

    y_plan_raw = sum_year("계획")
    p_plan_raw = sum_cum("계획")
    a_act_raw  = sum_cum("실적")

    # 3) 원천→요청 단위 변환 + 끊기(버림)
    def qty(series, team, flag):     # 톤 (정수)
        v = series.get((team, "판매량", flag), 0.0)
        v = 0.0 if pd.isna(v) else float(v)
        return _trunc(v)

    def amt(series, team, flag):     # 억원 (정수)
        v = series.get((team, "매출액", flag), 0.0)
        v = 0.0 if pd.isna(v) else float(v)
        return _trunc(v * AMOUNT_SCALE)

    def unit(series, team, flag):    # 천개 (정수)
        q = series.get((team, "판매량", flag), 0.0)
        a = series.get((team, "매출액", flag), 0.0)
        q = 0.0 if pd.isna(q) else float(q)
        a = 0.0 if pd.isna(a) else float(a)
        if q == 0:
            return np.nan
        return _trunc((a / q) * UNIT_SCALE)

    # 4) 원천 팀 목록
    teams_raw = [
        "선재영업팀", "봉강영업팀", "부산영업소", "대구영업소", "글로벌영업팀",
        "AT_국내", "AT_기차배건",
        "남통", "천진", "태국",
    ]

    # 5) 개별 팀(원천) 행 생성 — 모두 '끊기' 반영
    def build_row(team: str) -> dict:
        y_qty = qty(y_plan_raw, team, "계획")
        y_amt = amt(y_plan_raw, team, "계획")
        y_uni = unit(y_plan_raw, team, "계획")

        p_qty = qty(p_plan_raw, team, "계획")
        p_amt = amt(p_plan_raw, team, "계획")
        p_uni = unit(p_plan_raw, team, "계획")

        a_qty = qty(a_act_raw,  team, "실적")
        a_amt = amt(a_act_raw,  team, "실적")
        a_uni = unit(a_act_raw, team, "실적")

        d_qty = _trunc(a_qty - p_qty) if (not pd.isna(a_qty) and not pd.isna(p_qty)) else np.nan
        d_amt = _trunc(a_amt - p_amt) if (not pd.isna(a_amt) and not pd.isna(p_amt)) else np.nan
        d_uni = _trunc(a_uni - p_uni) if (not pd.isna(a_uni) and not pd.isna(p_uni)) else np.nan

        ach_qty = (a_qty / p_qty * 100) if (p_qty not in (0, None, np.nan) and not pd.isna(p_qty)) else np.nan
        ach_amt = (a_amt / p_amt * 100) if (p_amt not in (0, None, np.nan) and not pd.isna(p_amt)) else np.nan

        return {
            ("사업 계획(연간)", "판매량"): y_qty,
            ("사업 계획(연간)", "단가"):  y_uni,
            ("사업 계획(연간)", "매출액"): y_amt,

            ("사업 계획(누적)", "판매량"): p_qty,
            ("사업 계획(누적)", "단가"):  p_uni,
            ("사업 계획(누적)", "매출액"): p_amt,

            ("실적(누적)", "판매량"):     a_qty,
            ("실적(누적)", "단가"):      a_uni,
            ("실적(누적)", "매출액"):     a_amt,

            ("실적-계획", "판매량"):      d_qty,
            ("실적-계획", "단가"):       d_uni,
            ("실적-계획", "매출액"):      d_amt,

            ("달성률(%)", "판매량"):      ach_qty,
            ("달성률(%)", "매출액"):      ach_amt,
        }

    cols = pd.MultiIndex.from_tuples(list(build_row(teams_raw[0]).keys()))
    out  = pd.DataFrame(index=teams_raw, columns=cols, dtype=float)
    for t in teams_raw:
        out.loc[t] = pd.Series(build_row(t))

    # 6) 합계(집계) — 끊긴 값으로 합산, 단가 재계산도 끊기
    def sum_rows(row_names, label):
        names = [r for r in row_names if r in out.index]
        if not names:
            return
        sub = out.loc[names]

        y_qty = _trunc(sub[("사업 계획(연간)", "판매량")].sum())
        y_amt = _trunc(sub[("사업 계획(연간)", "매출액")].sum())
        p_qty = _trunc(sub[("사업 계획(누적)", "판매량")].sum())
        p_amt = _trunc(sub[("사업 계획(누적)", "매출액")].sum())
        a_qty = _trunc(sub[("실적(누적)",     "판매량")].sum())
        a_amt = _trunc(sub[("실적(누적)",     "매출액")].sum())

        def _safe_unit(a, q):
            if q in (0, None) or pd.isna(q):
                return np.nan
            # a는 "억원" 단위, 단가는 (백만원/톤)*1000:
            return _trunc((a / q) * (UNIT_SCALE / AMOUNT_SCALE))  # = 100,000 * (a/q)

        row = {}
        row[("사업 계획(연간)", "판매량")] = y_qty
        row[("사업 계획(연간)", "단가")]  = _safe_unit(y_amt, y_qty)
        row[("사업 계획(연간)", "매출액")] = y_amt

        row[("사업 계획(누적)", "판매량")] = p_qty
        row[("사업 계획(누적)", "단가")]  = _safe_unit(p_amt, p_qty)
        row[("사업 계획(누적)", "매출액")] = p_amt

        row[("실적(누적)", "판매량")]     = a_qty
        row[("실적(누적)", "단가")]      = _safe_unit(a_amt, a_qty)
        row[("실적(누적)", "매출액")]     = a_amt

        row[("실적-계획", "판매량")]      = _trunc(a_qty - p_qty)
        uni_act = _safe_unit(a_amt, a_qty)
        uni_pln = _safe_unit(p_amt, p_qty)
        row[("실적-계획", "단가")]       = _trunc(uni_act - uni_pln) if (not pd.isna(uni_act) and not pd.isna(uni_pln)) else np.nan
        row[("실적-계획", "매출액")]      = _trunc(a_amt - p_amt)

        row[("달성률(%)", "판매량")]      = (a_qty / p_qty * 100) if (p_qty not in (0, None, np.nan) and not pd.isna(p_qty)) else np.nan
        row[("달성률(%)", "매출액")]      = (a_amt / p_amt * 100) if (p_amt not in (0, None, np.nan) and not pd.isna(p_amt)) else np.nan

        out.loc[label] = pd.Series(row)

    # 7) 묶음/집계행 (요청 규칙 반영)
    naesoo    = ["선재영업팀", "봉강영업팀", "부산영업소", "대구영업소"]
    soochul   = ["글로벌영업팀"]              # 수출=글로벌영업팀
    hq_total  = naesoo + soochul             # 국내(선재) = 내수 + 수출
    at_dom    = ["AT_국내"]                  # 국내(AT) = AT_국내 (❗기차배건 제외)
    at_train  = ["AT_기차배건"]             # 기차배건(별도)
    china     = ["남통", "천진"]             # 포스세아 원천
    thailand  = ["태국"]

    # 원천 묶음
    sum_rows(naesoo,                       "내수")
    sum_rows(soochul,                      "수출    글로벌영업팀")
    sum_rows(hq_total,                     "국내(선재)")
    sum_rows(at_dom,                       "국내(AT)")
    sum_rows(at_train,                     "기차배건")
    sum_rows(china,                        "포스세아")
    sum_rows(["포스세아", "기차배건"],      "중국 계")     # 중국 계 = 포스세아 + 기차배건
    # 판매량은 포스세아 값 그대로 사용
    if ("중국 계" in out.index) and ("포스세아" in out.index):
        for g in ["사업 계획(연간)", "사업 계획(누적)", "실적(누적)", "실적-계획"]:
            out.loc["중국 계", (g, "판매량")] = out.loc["포스세아", (g, "판매량")]

        # 판매량 달성률도 포스세아 기준으로 동일하게
        out.loc["중국 계", ("달성률(%)", "판매량")] = out.loc["포스세아", ("달성률(%)", "판매량")]


    sum_rows(thailand,                     "태국 계")

    # 국내 계 = 국내(선재) + 국내(AT)  (판매량/매출액만 사용)
    sum_rows(["국내(선재)", "국내(AT)"],   "국내 계")

    # 국내 계 판매량은 국내(선재) 값 
    if ("국내 계" in out.index) and ("국내(선재)" in out.index):
        for g in ["사업 계획(연간)", "사업 계획(누적)", "실적(누적)", "실적-계획"]:
            out.loc["국내 계", (g, "판매량")] = out.loc["국내(선재)", (g, "판매량")]

        # 판매량을 바꿨으니, 판매량 기준으로 달성률(판매량)도 국내(선재)와 동일하게 맞춤
        out.loc["국내 계", ("달성률(%)", "판매량")] = out.loc["국내(선재)", ("달성률(%)", "판매량")]


    # AT계 = 국내(AT) + 기차배건
    sum_rows(["국내(AT)", "기차배건"],     "AT 계")

    # total = 매출액만: 국내 계 + 중국 계 + 태국 계
    sum_rows(["국내 계", "중국 계", "태국 계"], "total")
    
    # 선재 계 = 국내(선재) + 중국 계 + 태국 계  (AT 제외)
    sum_rows(["국내(선재)", "중국 계", "태국 계"], "선재 계")


    

    # 8) 열 비우기/제한 (요청사항)
    # 국내 계: 판매량/매출액만 표시 (단가/달성률/차이의 단가는 NaN)
    if "국내 계" in out.index:
        for g in ["사업 계획(연간)", "사업 계획(누적)", "실적(누적)", "실적-계획"]:
            out.loc["국내 계", (g, "단가")] = np.nan
        out.loc["국내 계", ("달성률(%)", "판매량")] = out.loc["국내 계", ("달성률(%)", "판매량")]
        out.loc["국내 계", ("달성률(%)", "매출액")] = out.loc["국내 계", ("달성률(%)", "매출액")]

    # total: 매출액만 표시 (그 외 전부 NaN)
    if "total" in out.index:
        for g in ["사업 계획(연간)", "사업 계획(누적)", "실적(누적)", "실적-계획"]:
            out.loc["total", (g, "판매량")] = np.nan
            out.loc["total", (g, "단가")]   = np.nan
        out.loc["total", ("달성률(%)", "판매량")] = np.nan
        # 달성률(매출액)은 유지할지 여부 정책에 따라 결정; 일단 유지
        # 필요시 아래 줄로 비울 수 있음:
        # out.loc["total", ("달성률(%)", "매출액")] = np.nan

    # 선재 계: 생성만 하고 전부 빈칸
    # blank_label = "선재 계"
    # out.loc[blank_label] = np.nan

    # 9) 표시 순서
    order = [
        "선재영업팀","봉강영업팀","부산영업소","대구영업소",
        "내수","수출    글로벌영업팀","국내(선재)","국내(AT)","국내 계",
        "남통","천진","포스세아",
        "기차배건","중국 계",
        "태국 계",
        "total",
        "선재 계",
        "AT 계",
    ]
    # (집계 다 끝난 뒤)
    out = out.loc[[r for r in order if r in out.index]]


    out.attrs.update({"used_month": m})
    return out



##### 손익 분석 #####

# =========================
# 공통 유틸
# =========================
def _num(x):
    """'12,345' '(1,234)' '10.5%' 등 안전 숫자 변환."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.replace(",", "").replace("%", "")
    try:
        v = float(re.sub(r"\s+", "", s))
        return -v if neg else v
    except Exception:
        return np.nan

def _tf(v) -> float:
    """to-float: Series/DataFrame/ndarray/리스트라도 단일 float로 강제 변환."""
    if isinstance(v, pd.DataFrame):
        v = v.values.ravel()
    if isinstance(v, (pd.Series, np.ndarray, list, tuple)):
        if len(v) == 0:
            return np.nan
        try:
            return float(np.asarray(v).ravel()[0])
        except Exception:
            return np.nan
    try:
        return float(v)
    except Exception:
        return np.nan

def _scale_for_display(idx_tuple, v):
    """표시 반올림: %는 1자리, 나머지 0자리."""
    if pd.isna(v):
        return np.nan
    sec, item = idx_tuple if isinstance(idx_tuple, tuple) else ("", "")
    return np.round(v, 1) if str(item).endswith("(%)") else np.round(v, 0)

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    컬럼 정리 + 라벨 표준화:
      - 구분3: 실적/계획
      - 구분4: 당월/누적 (누계/당월누계/공백 등 흡수)
    """
    df = df.copy()
    # 누락 컬럼 보강
    for c in ["구분1", "구분2", "구분3", "구분4", "연도", "월", "실적"]:
        if c not in df.columns:
            df[c] = ""

    for c in ["구분1","구분2","구분3","구분4"]:
        df[c] = (df[c].astype(str)
                   .str.replace("\xa0", " ")
                   .str.replace(r"\s+", " ", regex=True)
                   .str.strip())

    # 라벨 표준화
    map_g3 = {"실":"실적","실적":"실적","actual":"실적","Actual":"실적",
              "계":"계획","계획":"계획","plan":"계획","Plan":"계획"}
    # 계획의 구분4 공백 → 당월로 간주(실무 데이터 흔함)
    map_g4 = {"당월":"당월","월":"당월","당월실적":"당월","": "당월",
              "누적":"누적","누계":"누적","당월누계":"누적","당월누적":"누적"}
    df["구분3"] = df["구분3"].map(lambda x: map_g3.get(x, x))
    df["구분4"] = df["구분4"].map(lambda x: map_g4.get(x, x))

    # 숫자형
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")
    df["월"]   = pd.to_numeric(df["월"],   errors="coerce").astype("Int64")
    df["실적"] = df["실적"].apply(_num)

    # 최신값 우선
    df["__o__"] = range(len(df))
    df = (df.sort_values("__o__")
            .drop_duplicates(["연도","월","구분2","구분3","구분4"], keep="last")
            .drop(columns="__o__"))
    return df

def normalize_row_order(row_order_spec):

    norm = []
    header_rows = set()
    cur_group = None

    for g, i in row_order_spec:
        if g != "":
            cur_group = g
        g = cur_group
        norm.append((g, i))
        if i == "":
            header_rows.add((g, i))
    return norm, header_rows

def create_profit_month_block_table(year: int, month: int, df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    선택 year/month 기준 손익요약 블록(단일 '구분' 컬럼 버전) 생성.
    반환 컬럼: ['구분', '’{year-2}년', '’{year-1}년', '{pm}월', '{m}월①', '전월대비',
              '{pm}월계획', '{m}월계획(②)', '계획대비(①-②)', '당월누적']
    """
    df = _clean(df_raw)

    # ─ 피벗 준비 ─
    pv    = df.pivot_table(index=["연도","월","구분3","구분4","구분2"], values="실적", aggfunc="sum")
    pv_m  = df.pivot_table(index=["연도","월","구분3","구분2"],      values="실적", aggfunc="sum")

    df_plan     = df[df["구분3"] == "계획"].copy()
    pv_plan_dom = df_plan[df_plan["구분4"] == "당월"].pivot_table(index=["연도","월","구분2"], values="실적", aggfunc="sum")
    pv_plan_cum = df_plan[df_plan["구분4"] == "누적"].pivot_table(index=["연도","월","구분2"], values="실적", aggfunc="sum")

    # ─ 기준 월/전월/전년 ─
    if month == 1:
        prev_year, pm = year - 1, 12
    else:
        prev_year, pm = year, month - 1
    m, y_1, y_2 = month, year - 1, year - 2

    # ─ 값 헬퍼(항상 스칼라 반환) ─
    def _get(yy, mm, item, g3, g4):
        try:
            v = pv.loc[(yy, mm, g3, g4, item)]
            return _tf(v)
        except KeyError:
            return np.nan

    def get_acc_or_sum(yy, mm, item):
        # (실적, 누적) 우선, 없으면 1~mm (실적, 당월) 합으로 대체
        try:
            v = pv.loc[(yy, mm, "실적", "누적", item)]
            return _tf(v)
        except KeyError:
            pass
        try:
            s = pv_m.loc[(yy, slice(1, mm), "실적", item)]
            return _tf(getattr(s, "sum", lambda: s)())
        except KeyError:
            return np.nan

    def get_plan_month(yy, mm, item):
        # 1) (계획, 당월)
        if (yy, mm, item) in pv_plan_dom.index:
            return _tf(pv_plan_dom.loc[(yy, mm, item)])
        # 2) (계획, 누적) 차분 → 당월계획
        cur = _tf(pv_plan_cum.loc[(yy, mm, item)]) if (yy, mm, item) in pv_plan_cum.index else np.nan
        if not pd.isna(cur):
            if mm == 1:
                prev = _tf(pv_plan_cum.loc[(yy-1, 12, item)]) if (yy-1, 12, item) in pv_plan_cum.index else 0.0
            else:
                prev = _tf(pv_plan_cum.loc[(yy, mm-1, item)]) if (yy, mm-1, item) in pv_plan_cum.index else 0.0
            return cur - prev
        return np.nan
    
    # --- 유틸: 특정 라벨 행을 다른 라벨 행 '바로 위'에 복제 삽입 ---
    def _dup_row_before(df: pd.DataFrame, src_label: str, before_label: str, new_label: str | None = None) -> pd.DataFrame:
        if "구분" not in df.columns:
            return df
        src_rows = df[df["구분"] == src_label]
        if src_rows.empty:
            return df  # 복제 원본이 없으면 그대로 반환
        before_idx = df.index[df["구분"] == before_label]
        if len(before_idx) == 0:
            return df  # 기준 행이 없으면 그대로 반환

        insert_pos = int(before_idx.min())    # 첫 번째 등장 위치 기준
        dup = src_rows.copy(deep=True)
        if new_label is not None:
            dup.loc[:, "구분"] = new_label

        upper = df.iloc[:insert_pos]
        lower = df.iloc[insert_pos:]
        return pd.concat([upper, dup, lower], ignore_index=True)


    # ─ 한 줄 ‘구분’ 순서(중복 없게 구성) ─
    order = [
        "매출액", "제품등", "부산물",
        "판매량",
        "매출원가", "제품원가", "C조건 선임", "클레임", "재고평가분", "단가소급 등",
        "매출이익", "매출이익(%)",
        "판관비", "인건비", "관리비", "판매비",
        "영업이익", "영업이익(%)",
        "내수운반", "수출개별",
        "내수", "수출",
    ]

    # ─ 열 라벨(동적) ─
    col_23     = f"'{str(y_2)[-2:]}년"
    col_24     = f"'{str(y_1)[-2:]}년"
    col_pm     = f"{pm}월"
    col_m      = f"{m}월(①)"
    col_pm_pln = f"{pm}월계획"
    col_m_pln  = f"{m}월계획(②)"
    cols_num   = [col_23, col_24, col_pm, col_m, "전월대비", col_pm_pln, col_m_pln, "계획대비(①-②)", "당월누적"]

    # ─ 빈 틀(DataFrame) : '구분'을 컬럼으로 둠(인덱스는 RangeIndex) ─
    out = pd.DataFrame({"구분": order})
    for c in cols_num:
        out[c] = np.nan

    # ─ 값 주입: '구분' 라벨→실제 아이템 이름을 그대로 사용 ─
    #   * 매출액/매출원가/판관비/매출이익/영업이익 : 총계 행 보정 로직 적용
    data_items = set(order)  # 원 데이터의 구분2 라벨과 동일하다고 가정

    # 1) 일반 항목(퍼센트/총계 제외)
    for lbl in order:
        if lbl.endswith("(%)"):   # 퍼센트는 뒤에서 계산
            continue
        if lbl in ["매출액", "매출원가", "판관비", "매출이익", "영업이익"]:
            continue  # 총계/계산 항목은 아래에서 일괄 계산

        # 실적/계획/누적
        out.loc[out["구분"] == lbl, col_23]     = _tf(get_acc_or_sum(y_2, 12, lbl))
        out.loc[out["구분"] == lbl, col_24]     = _tf(get_acc_or_sum(y_1, 12, lbl))
        out.loc[out["구분"] == lbl, col_pm]     = _tf(_get(prev_year, pm, lbl, "실적", "당월"))
        out.loc[out["구분"] == lbl, col_m]      = _tf(_get(year,      m,  lbl, "실적", "당월"))
        out.loc[out["구분"] == lbl, col_pm_pln] = _tf(get_plan_month(prev_year, pm, lbl))
        out.loc[out["구분"] == lbl, col_m_pln]  = _tf(get_plan_month(year,      m,  lbl))
        out.loc[out["구분"] == lbl, "당월누적"] = _tf(get_acc_or_sum(year, m, lbl))

    # 2) 총계/계산 항목
    def _sales_total(col):
        # 매출액 총계가 있으면 사용
        v = _tf(_get(year, m, "매출액", "실적", "당월"))  # 당월만 체크해 총계 존재 여부 판단 용
        has_sales_item = ("매출액" in data_items) and not pd.isna(v)
        if has_sales_item:
            # 각 열별로 직접 조회
            a = {
                col_23:     _tf(get_acc_or_sum(y_2, 12, "매출액")),
                col_24:     _tf(get_acc_or_sum(y_1, 12, "매출액")),
                col_pm:     _tf(_get(prev_year, pm, "매출액", "실적", "당월")),
                col_m:      _tf(_get(year,      m,  "매출액", "실적", "당월")),
                col_pm_pln: _tf(get_plan_month(prev_year, pm, "매출액")),
                col_m_pln:  _tf(get_plan_month(year,      m,  "매출액")),
                "당월누적":  _tf(get_acc_or_sum(year, m, "매출액")),
            }
            return a
        else:
            # 제품등 + 부산물로 총계 생성
            def v_part(col, item):
                if item not in data_items: return np.nan
                if   col == col_23:     return _tf(get_acc_or_sum(y_2, 12, item))
                elif col == col_24:     return _tf(get_acc_or_sum(y_1, 12, item))
                elif col == col_pm:     return _tf(_get(prev_year, pm, item, "실적", "당월"))
                elif col == col_m:      return _tf(_get(year,      m,  item, "실적", "당월"))
                elif col == col_pm_pln: return _tf(get_plan_month(prev_year, pm, item))
                elif col == col_m_pln:  return _tf(get_plan_month(year,      m,  item))
                elif col == "당월누적":  return _tf(get_acc_or_sum(year, m, item))
                else: return np.nan

            summ = {}
            for c in [col_23, col_24, col_pm, col_m, col_pm_pln, col_m_pln, "당월누적"]:
                a = v_part(c, "제품등")
                b = v_part(c, "부산물")
                a = 0.0 if pd.isna(a) else a
                b = 0.0 if pd.isna(b) else b
                summ[c] = a + b
            return summ

    def _cogs_total(col):
        # 매출원가 총계가 있으면 사용, 없으면 구성항목 합
        parts = ["매출원가","제품원가","C조건 선임","클레임","재고평가분","단가소급 등"]
        def get(item, colname):
            if item not in parts: return np.nan
            if   colname == col_23:     return _tf(get_acc_or_sum(y_2, 12, item))
            elif colname == col_24:     return _tf(get_acc_or_sum(y_1, 12, item))
            elif colname == col_pm:     return _tf(_get(prev_year, pm, item, "실적", "당월"))
            elif colname == col_m:      return _tf(_get(year,      m,  item, "실적", "당월"))
            elif colname == col_pm_pln: return _tf(get_plan_month(prev_year, pm, item))
            elif colname == col_m_pln:  return _tf(get_plan_month(year,      m,  item))
            elif colname == "당월누적":  return _tf(get_acc_or_sum(year, m, item))
            else: return np.nan

        totals = {}
        for c in [col_23, col_24, col_pm, col_m, col_pm_pln, col_m_pln, "당월누적"]:
            # 우선 매출원가 단일 항목이 있으면 우선
            v_direct = get("매출원가", c)
            if not pd.isna(v_direct):
                totals[c] = v_direct
            else:
                s = 0.0; any_found = False
                for p in ["제품원가","C조건 선임","클레임","재고평가분","단가소급 등"]:
                    v = get(p, c)
                    if not pd.isna(v):
                        s += v; any_found = True
                totals[c] = s if any_found else np.nan
        return totals

    def _sganda_total(col):
        # 판관비 총계가 있으면 사용, 없으면 인건비+관리비+판매비
        def get(item, colname):
            if   colname == col_23:     return _tf(get_acc_or_sum(y_2, 12, item))
            elif colname == col_24:     return _tf(get_acc_or_sum(y_1, 12, item))
            elif colname == col_pm:     return _tf(_get(prev_year, pm, item, "실적", "당월"))
            elif colname == col_m:      return _tf(_get(year,      m,  item, "실적", "당월"))
            elif colname == col_pm_pln: return _tf(get_plan_month(prev_year, pm, item))
            elif colname == col_m_pln:  return _tf(get_plan_month(year,      m,  item))
            elif colname == "당월누적":  return _tf(get_acc_or_sum(year, m, item))
            else: return np.nan

        totals = {}
        for c in [col_23, col_24, col_pm, col_m, col_pm_pln, col_m_pln, "당월누적"]:
            v_direct = get("판관비", c)
            if not pd.isna(v_direct):
                totals[c] = v_direct
            else:
                s = 0.0; any_found = False
                for p in ["인건비","관리비","판매비"]:
                    v = get(p, c)
                    if not pd.isna(v):
                        s += v; any_found = True
                totals[c] = s if any_found else np.nan
        return totals

    # 매출액·매출원가·판관비 총계 채우기
    sales_tot = _sales_total(col_m)  # 존재 확인용 호출만 했던 부분과 무관, 아래서 다시 채움
    sales_dict = _sales_total  # 함수 핸들 보관(열별 호출)
    cogs_dict  = _cogs_total
    sga_dict   = _sganda_total

    # 각 총계에 대해 열별 값 채우기
    for lbl, calc in [("매출액", sales_dict), ("매출원가", cogs_dict), ("판관비", sga_dict)]:
        if lbl in out["구분"].values:
            row_mask = out["구분"] == lbl
            d = calc(None)  # 내부에서 열별로 계산
            for c in [col_23, col_24, col_pm, col_m, col_pm_pln, col_m_pln, "당월누적"]:
                out.loc[row_mask, c] = _tf(d[c])

    # 매출이익 = 매출액 - 매출원가
    if "매출이익" in out["구분"].values:
        rm = out["구분"] == "매출이익"
        for c in [col_23, col_24, col_pm, col_m, "당월누적"]:
            s = _tf(out.loc[out["구분"] == "매출액", c])
            g = _tf(out.loc[out["구분"] == "매출원가", c])
            out.loc[rm, c] = np.nan if pd.isna(s) or pd.isna(g) else (s - g)

    # 영업이익 = 매출이익 - 판관비
    if "영업이익" in out["구분"].values:
        ro = out["구분"] == "영업이익"
        for c in [col_23, col_24, col_pm, col_m, "당월누적"]:
            gp = _tf(out.loc[out["구분"] == "매출이익", c])
            sg = _tf(out.loc[out["구분"] == "판관비",  c])
            out.loc[ro, c] = np.nan if pd.isna(gp) or pd.isna(sg) else (gp - sg)

    # 파생 열
    out["전월대비"]       = out[col_m].astype(float) - out[col_pm].astype(float)
    out["계획대비(①-②)"] = out[col_m].astype(float) - out[col_m_pln].astype(float)

    # 퍼센트 계산
    def _pct(num, den):
        num, den = _tf(num), _tf(den)
        if pd.isna(num) or pd.isna(den) or den == 0:
            return np.nan
        return (num/den)*100.0

    if "매출이익(%)" in out["구분"].values:
        r = out["구분"] == "매출이익(%)"
        for c in cols_num:
            if c == "전월대비" or c == "계획대비(①-②)": 
                continue
            den = _tf(out.loc[out["구분"] == "매출액", c])
            num = _tf(out.loc[out["구분"] == "매출이익", c])
            out.loc[r, c] = _pct(num, den)

    if "영업이익(%)" in out["구분"].values:
        r = out["구분"] == "영업이익(%)"
        for c in cols_num:
            if c == "전월대비" or c == "계획대비(①-②)":
                continue
            den = _tf(out.loc[out["구분"] == "매출액", c])
            num = _tf(out.loc[out["구분"] == "영업이익", c])
            out.loc[r, c] = _pct(num, den)

    # 매출이익(계획) = 매출액(계획) - 매출원가(계획)
    if "매출이익" in out["구분"].values:
        gi_mask = out["구분"] == "매출이익"
        for plan_col in [col_pm_pln, col_m_pln]:
            s = _tf(out.loc[out["구분"] == "매출액",  plan_col])
            g = _tf(out.loc[out["구분"] == "매출원가", plan_col])
            out.loc[gi_mask, plan_col] = np.nan if pd.isna(s) or pd.isna(g) else (s - g)

    # 영업이익(계획) = 매출이익(계획) - 판관비(계획)
    if "영업이익" in out["구분"].values:
        op_mask = out["구분"] == "영업이익"
        for plan_col in [col_pm_pln, col_m_pln]:
            gi = _tf(out.loc[out["구분"] == "매출이익", plan_col])
            sg = _tf(out.loc[out["구분"] == "판관비",  plan_col])
            out.loc[op_mask, plan_col] = np.nan if pd.isna(gi) or pd.isna(sg) else (gi - sg)
    # ─────────────────────────────────
    # 퍼센트 계산: (이익 / 매출액) * 100
    # ─────────────────────────────────
    # 필요한 퍼센트 행이 없으면 추가
    for r in ["매출이익(%)", "영업이익(%)"]:
        if r not in out["구분"].values:
            out.loc[len(out)] = [r] + [np.nan] * (out.shape[1]-1)  # '구분' + 수치열
            # 위 한 줄로 추가하면 '구분' 컬럼이 첫 컬럼이라고 가정합니다.

    def _pct(num, den):
        num, den = _tf(num), _tf(den)
        if pd.isna(num) or pd.isna(den) or den == 0:
            return np.nan
        return (num / den) * 100.0

    # 퍼센트를 계산해 줄 대상 열(차이열은 퍼센트 계산 대상에서 제외)
    pct_cols = [col_23, col_24, col_pm, col_m, col_pm_pln, col_m_pln, "당월누적"]

    # 매출액/매출이익/영업이익 행 마스크
    row_sales = out["구분"] == "매출액"
    row_gp    = out["구분"] == "매출이익"
    row_op    = out["구분"] == "영업이익"
    row_gp_pct = out["구분"] == "매출이익(%)"
    row_op_pct = out["구분"] == "영업이익(%)"

    # 각 열별로 퍼센트 계산
    for c in pct_cols:
        den = _tf(out.loc[row_sales, c])  # 매출액
        # 매출이익(%)
        num = _tf(out.loc[row_gp, c])
        out.loc[row_gp_pct, c] = _pct(num, den)
        # 영업이익(%)
        num = _tf(out.loc[row_op, c])
        out.loc[row_op_pct, c] = _pct(num, den)






    # 표시 반올림(금액/수량 0자리, % 1자리)
    num_cols = [col_23, col_24, col_pm, col_m, "전월대비", col_pm_pln, col_m_pln, "계획대비(①-②)", "당월누적"]
    is_pct_row = out["구분"].astype(str).str.endswith("(%)")
    # 숫자화
    out[num_cols] = out[num_cols].applymap(lambda v: _tf(v))
    # 반올림
    out.loc[~is_pct_row, num_cols] = out.loc[~is_pct_row, num_cols].round(0)
    out.loc[ is_pct_row, num_cols] = out.loc[ is_pct_row, num_cols].round(1)
    
    # ── 표시 반올림 완료 후, 복제 삽입 ──
    out = _dup_row_before(out, src_label="판매비",  before_label="내수운반")  
    out = _dup_row_before(out, src_label="판매량", before_label="내수")      

    return out


##### 수출 환율 차이 #####
# modules.py
import pandas as pd
from typing import Tuple


def _to_num(series: pd.Series) -> pd.Series:
    """'3,977,969원' 같은 문자열을 숫자로 변환."""
    s = series.astype(str)
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(r"[^\d\.\-]", "", regex=True)  # 숫자/소수점/마이너스만 남기기
    s = s.str.strip()
    return pd.to_numeric(s, errors="coerce")


# modules.py
import pandas as pd
import numpy as np

def fx_export_table(df_long: pd.DataFrame, year: int, month: int):
    """
    df_long : [구분1,구분2,구분3,구분4,연도,월,실적]
    """

    # ── 0. 기본 전처리 : 문자열 → 숫자 ─────────────────
    df = df_long.copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"]   = pd.to_numeric(df["월"], errors="coerce")

    df["실적"] = (
        df["실적"].astype(str)
        .str.replace(",", "", regex=False)
    )
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce")

    # ── 1. 기준월 / 전월 ──────────────────────────────
    curr_y, curr_m = year, month
    prev_y, prev_m = (year, month - 1) if month > 1 else (year - 1, 12)

    prev_lab = f"{prev_m}월"
    curr_lab = f"{curr_m}월"

    df_curr = df[(df["연도"] == curr_y) & (df["월"] == curr_m)].copy()
    df_prev = df[(df["연도"] == prev_y) & (df["월"] == prev_m)].copy()

    # ── 2. 월별 피벗 ──────────────────────────────────
    def make_month_pivot(df_m):
        if df_m.empty:
            base = (pd.DataFrame(columns=["구분1","중량","외화공급가액","원화공급가액"])
                    .set_index("구분1"))
        else:
            tmp = (
                df_m.groupby(["구분1", "구분2"], as_index=False)["실적"]
                    .sum()
            )
            base = tmp.pivot(index="구분1", columns="구분2", values="실적")

        for c in ["중량", "외화공급가액", "원화공급가액"]:
            if c not in base.columns:
                base[c] = np.nan

        for c in base.columns:
            base[c] = pd.to_numeric(base[c], errors="coerce")

        fx = base["외화공급가액"].replace(0, np.nan)
        base["환율"] = base["원화공급가액"] / fx

        return base[["중량", "외화공급가액", "환율", "원화공급가액"]]

    prev_p = make_month_pivot(df_prev)
    curr_p = make_month_pivot(df_curr)

    prev_p = prev_p.add_prefix(f"{prev_lab}_")
    curr_p = curr_p.add_prefix(f"{curr_lab}_")

    body = prev_p.join(curr_p, how="outer")

    # ── 3. 통화 순서 고정 (USD, JPY, CNY) ─────────────
    order_ccy = ["USD", "JPY", "CNY"]
    body = body.reindex(order_ccy)      # 없으면 NaN 행이 생김

    body.index.name = "구분1"
    body = body.reset_index().rename(columns={"구분1": "구분"})

    # ── 4. 차이단가 & 영향금액 ────────────────────────
    prev_fx_col  = f"{prev_lab}_환율"
    curr_fx_col  = f"{curr_lab}_환율"
    curr_amt_col = f"{curr_lab}_외화공급가액"

    body["차이단가"] = body[curr_fx_col] - body[prev_fx_col]
    body["영향금액"] = body[curr_amt_col] * body["차이단가"]

    # ── 5. 총계 행 계산 (중량 / 원화공급가액 / 영향금액만) ─
    sum_cols = []
    for pref in (prev_lab, curr_lab):
        for item in ("중량", "원화공급가액"):
            col = f"{pref}_{item}"
            if col in body.columns:
                sum_cols.append(col)
    if "영향금액" in body.columns:
        sum_cols.append("영향금액")

    total_row = {c: np.nan for c in body.columns}
    total_row["구분"] = "총계"

    for col in sum_cols:
        total_row[col] = body.loc[body["구분"].isin(order_ccy), col].sum(min_count=1)

    body = pd.concat([body, pd.DataFrame([total_row])], ignore_index=True)

    # ── 6. USD 기준 요약 ──────────────────────────────
    usd_row = body[body["구분"] == "USD"]

    if usd_row.empty:
        usd_delta  = 0.0
        usd_effect = 0.0
    else:
        usd_delta  = float(usd_row[curr_fx_col].iloc[0] - usd_row[prev_fx_col].iloc[0])
        usd_effect = float(usd_row["영향금액"].iloc[0])

    return body, prev_lab, curr_lab, usd_delta, usd_effect














##### 포스코 對 JFE 입고가격 #####

from typing import Sequence, Tuple, List

KIND_ORDER = ["탄소강", "합금강", ""]
PARTY_ORDER = ["포스코", "JFE", "차이", "포스코 할인단가(원)", "환율"]

_dyn_col_pat = re.compile(r"^(?P<m>\d{1,2})월\((?P<y>\d{4})\)$")

def _month_shift(y: int, m: int, delta: int) -> Tuple[int, int]:
    t = y * 12 + (m - 1) + delta
    ny = t // 12
    nm = t % 12 + 1
    return int(ny), int(nm)

def _parse_kind_party_item(s: str) -> Tuple[str, str, str]:
    """
    구분2를 (kind, party, item)으로 분해
      - '탄소강_포스코_SWRCH45FS' -> ('탄소강','포스코','SWRCH45FS')
      - '탄소강_포스코_변동폭(천원/톤)' -> ('탄소강','포스코','변동폭(천원/톤)')
      - '탄소강_SWRCH45K-M' -> ('탄소강','JFE','SWRCH45K-M')
      - '탄소강_(USD)' -> ('탄소강','JFE','(USD)')
      - '탄소강_변동폭(USD/톤)' -> ('탄소강','JFE','변동폭(USD/톤)')
      - '포스코 할인단가(원)' -> ('','포스코 할인단가(원)','')
      - '환율' -> ('','환율','')
      - '차이' -> kind는 이후 ffill로 보강, party='차이', item=''
    """
    if not isinstance(s, str):
        return "", "", ""
    s = s.strip()
    if s in ("포스코 할인단가(원)", "환율"):
        return "", s, ""
    if s == "차이":
        return np.nan, "차이", ""  # kind는 나중에 (연/월 그룹 내) ffill

    # '탄소강_...' / '합금강_...'
    parts = s.split("_")
    if len(parts) == 1:
        return "", s, ""
    kind = parts[0]
    rest = parts[1:]

    # 포스코 패턴
    if rest and rest[0] == "포스코":
        party = "포스코"
        item = "_".join(rest[1:]) if len(rest) > 1 else ""
        return kind, party, item

    # 그 외는 JFE로 분류
    party = "JFE"
    item = "_".join(rest)
    return kind, party, item

def _sort_index(idx: pd.MultiIndex) -> List[Tuple[str,str,str]]:
    def key_fn(t):
        k, p, i = t
        k_rank = KIND_ORDER.index(k) if k in KIND_ORDER else len(KIND_ORDER)
        p_rank = PARTY_ORDER.index(p) if p in PARTY_ORDER else len(PARTY_ORDER)
        # 아이템은 그대로(사전식)
        return (k_rank, p_rank, i)
    return sorted([tuple(x) for x in idx], key=key_fn)

def build_posco_jfe_price_wide(
    df: pd.DataFrame,
    sel_y: int,
    sel_m: int,
    group_name: str = "포스코 對 JFE 입고가격",
    monthly_years: Sequence[int] | None = None,   # ← 기본값을 None으로 바꿈
):
    """
    반환:
      wide_df, col_order, hdr1_labels, hdr2_labels
    - wide_df: index = (kind, party, item) / values = 표시용 문자열(실적 원문)
    - 연도별 12월 = 'YYYY년 월평균', 동적 3칸 = 전전월/전월/선택월 'M월(YYYY)'
    """

    # 선택연도 기준 자동계산
    if monthly_years is None:
        monthly_years = [sel_y - 4, sel_y - 3, sel_y - 2, sel_y - 1]

    d = df.copy()
    d = d[d["구분1"] == group_name].copy()

    # 타입 정리
    d["연도"] = pd.to_numeric(d["연도"], errors="coerce")
    d["월"]   = pd.to_numeric(d["월"],   errors="coerce")

    # (kind, party, item) 파싱
    kp = d["구분2"].astype(str).apply(_parse_kind_party_item)
    d["kind"]  = kp.apply(lambda x: x[0])
    d["party"] = kp.apply(lambda x: x[1])
    d["item"]  = kp.apply(lambda x: x[2])

    # '차이'의 kind 보강
    d = d.sort_values(["연도", "월", "구분3"]).copy()
    def _ffill_kind(group: pd.DataFrame) -> pd.DataFrame:
        cur = None
        kinds = []
        for _, r in group.iterrows():
            k = r["kind"]
            if isinstance(k, str) and k != "":
                cur = k
            if pd.isna(k):  # 차이 라인에서만 NaN으로 들어옴
                kinds.append(cur if cur is not None else "")
            else:
                kinds.append(k)
        group["kind"] = kinds
        return group

    d = d.groupby(["연도","월"], as_index=False, group_keys=False).apply(_ffill_kind)

    frames = []
    col_order = []
    hdr1_labels = []
    hdr2_labels = []

    # 1) 연도별 월평균(12월) 열
    d_base = d[d["구분3"] == "월평균"]
    for y in monthly_years:
        dd = d_base[(d_base["연도"] == y) & (d_base["월"] == 12)]
        col_name = f"{y}년 월평균"

        if dd.empty:
            col_order.append(col_name)
            hdr1_labels.append(f"{y}년")
            hdr2_labels.append("월평균")
            continue

        p = dd.pivot_table(index=["kind","party","item"], values="실적", aggfunc="first")
        p = p.rename(columns={"실적": col_name})
        frames.append(p)
        col_order.append(col_name)
        hdr1_labels.append(f"{y}년")
        hdr2_labels.append("월평균")

    # 2) 전전월/전월/선택월
    prev2_y, prev2_m = _month_shift(sel_y, sel_m, -2)
    prev_y,  prev_m  = _month_shift(sel_y, sel_m, -1)
    dyn = [
        (prev2_y, prev2_m, f"{prev2_m}월({prev2_y})", f"{prev2_m}월"),
        (prev_y,  prev_m,  f"{prev_m}월({prev_y})",  f"{prev_m}월"),
        (sel_y,   sel_m,   f"{sel_m}월({sel_y})",    f"{sel_m}월"),
    ]
    for y, m, col, sublab in dyn:
        dd = d[(d["연도"] == y) & (d["월"] == m)]
        if dd.empty:
            col_order.append(col)
            hdr1_labels.append(f"{sel_y}년")  # hdr1은 선택연도 기준 라벨 유지
            hdr2_labels.append(sublab)
            continue

        p  = dd.pivot_table(index=["kind","party","item"],
                            values="실적", aggfunc="first").rename(columns={"실적": col})
        frames.append(p)
        col_order.append(col)
        hdr1_labels.append(f"{sel_y}년")
        hdr2_labels.append(sublab)

    # 3) 병합
    wide = None
    for f in frames:
        wide = f if wide is None else wide.join(f, how="outer")

    # 4) '포스코 할인단가(원)'  항상 첫행
    top_row = ("", "포스코 할인단가(원)", "")

    if wide is None or wide.empty:
        wide = pd.DataFrame(
            index=pd.MultiIndex.from_tuples([top_row], names=["kind","party","item"])
        )
    else:
        if top_row not in wide.index:
            wide.loc[top_row, :] = np.nan

    ordered_rest = [idx for idx in _sort_index(wide.index) if idx != top_row]
    wide = wide.reindex([top_row] + ordered_rest)

    # 5) 컬럼 보장 + 순서 고정 )
    for c in col_order:
        if c not in wide.columns:
            wide[c] = np.nan
    wide = wide[col_order]

    # 6) kind/party 표시 정리
    #   - kind: (탄소강, 합금강) 블록마다 첫 행만 표시
    #   - party: 각 kind 블록 안에서 party별 첫 행만 표시
    idx_df = wide.index.to_frame(index=False)   # 컬럼: kind, party, item

    # 6-1) party: (kind, party) 조합별 첫 행만 표시
    for k in ["탄소강", "합금강"]:
        mask_kind = idx_df["kind"] == k
        parties = idx_df.loc[mask_kind, "party"].unique()
        for p in parties:
            mask = mask_kind & (idx_df["party"] == p)
            idxs = idx_df.index[mask].tolist()
            if len(idxs) > 1:
                # 같은 kind, 같은 party 안에서 첫 행만 party 표시, 나머진 공백
                idx_df.loc[idxs[1:], "party"] = ""

    # 6-2) kind: kind 블록 안에서 첫 행만 표시
    for k in ["탄소강", "합금강"]:
        mask_kind = idx_df["kind"] == k
        idxs = idx_df.index[mask_kind].tolist()
        if len(idxs) > 1:
            idx_df.loc[idxs[1:], "kind"] = ""

    wide.index = pd.MultiIndex.from_frame(idx_df)

    return wide, col_order, hdr1_labels, hdr2_labels







##### 포스코 JFE 단가 #####
def is_percent(x):
    return isinstance(x, str) and x.strip().endswith("%")

def to_number(x):
    if isinstance(x, (int, float)): 
        return float(x)
    s = str(x).replace(",", "").strip()
    if s.endswith("%"):
        s = s[:-1]
    try:
        return float(s)
    except:
        return np.nan

def split_kind_party(v):
    if not isinstance(v, str): 
        return "", ""
    p = v.split("_", 1)
    return (p[0], p[1]) if len(p) == 2 else (v, "")

def _is_percent(x):
    return isinstance(x, str) and x.strip().endswith("%")

def _to_number(x):
    if isinstance(x, (int, float)): return float(x)
    s = str(x).replace(",", "").strip()
    if s.endswith("%"): s = s[:-1]
    try: return float(s)
    except: return np.nan

def _split_kind_party(v):
    if not isinstance(v, str): return "", ""
    p = v.split("_", 1)
    return (p[0], p[1]) if len(p) == 2 else (v, "")


##### 손익분석 포스코/JFE 투입비중 #####


def _is_percent(x):
    return isinstance(x, str) and x.strip().endswith("%")

def _to_number(x):
    if isinstance(x, (int, float)): return float(x)
    s = str(x).replace(",", "").strip()
    if s.endswith("%"): s = s[:-1]
    try: return float(s)
    except: return np.nan

def _split_kind_party(v):
    if not isinstance(v, str): return "", ""
    p = v.split("_", 1)
    return (p[0], p[1]) if len(p) == 2 else (v, "")

def _metric_row(sub: str, is_pct: bool):
    if sub in ("포스코", "JFE"): return "비중" if is_pct else "중량"
    if sub == "평균단가": return "평균단가"
    return "값"

def _month_shift(year: int, month: int, delta: int) -> tuple[int, int]:
    """
    year, month에서 delta개월(음수 가능) 만큼 이동한 (연도, 월)을 반환.
    예: (2025, 1, -2) -> (2024, 11)
    """
    # year-month 를 '전체 개월 수'로 바꾸기 (0 기반 월로 변환)
    total = year * 12 + (month - 1) + delta
    new_year = total // 12
    new_month = total % 12 + 1
    return new_year, new_month





def build_posco_jfe_wide(
    df: pd.DataFrame,
    sel_y: int,
    sel_m: int,
    monthly_years: Sequence[int] | None = None,   # ← 기본값을 None으로 변경
):
    """
    반환:
      wide_df, col_order, hdr1_labels, hdr2_labels
      - hdr1_labels:
          · 과거 연도 월평균: 각 연도별 'YYYY년'
          · 동적 3칸(전전월/전월/선택월): 해당 월의 실제 연도 'YYYY년'
      - hdr2_labels:
          · 과거 연도 월평균: '월평균'
          · 동적 3칸: [전전월, 전월, 선택월] 형태의 'M월'

    monthly_years:
      - None 인 경우: sel_y 기준으로 [sel_y-3, sel_y-2, sel_y-1] 사용
      - 직접 리스트/튜플로 넣으면 그 연도들 사용
    """
    

    if monthly_years is None:
        monthly_years = [sel_y - 3, sel_y - 2, sel_y - 1]

    d = df.copy()
    d = d[d["구분1"] == "포스코/JFE 투입비중"].copy()
    d["연도"] = pd.to_numeric(d["연도"], errors="coerce")
    d["월"]   = pd.to_numeric(d["월"],   errors="coerce")

    d["is_pct"] = d["실적"].apply(_is_percent)
    d["val"]    = d["실적"].apply(_to_number)

    ks = d["구분2"].astype(str).map(_split_kind_party)
    d["kind"] = ks.apply(lambda x: x[0] if isinstance(x, tuple) and len(x)==2 else "")
    d["sub"]  = ks.apply(lambda x: x[1] if isinstance(x, tuple) and len(x)==2 else "")

    single = ~d["kind"].isin(["탄소강", "합금강"])
    d.loc[single, "kind"] = ""
    d.loc[single, "sub"]  = d.loc[single, "구분2"]

    d["metric"] = [_metric_row(sub, is_pct) for sub, is_pct in zip(d["sub"], d["is_pct"])]

    frames = []
    col_order = []
    hdr1_labels = []
    hdr2_labels = []
    

    # 1) 과거 연도들: 12월 = 월평균 (구분3='월평균'만)
    d_base = d[d["구분3"] == "월평균"]
    for y in monthly_years:
        dd = d_base[(d_base["연도"] == y) & (d_base["월"] == 12)]
        col = f"{y}년 월평균"

        # dd가 비어도 col_order/hdr 라벨은 일단 확보
        if dd.empty:
            col_order.append(col)
            hdr1_labels.append(f"{y}년")
            hdr2_labels.append("월평균")
            continue

        p = dd.pivot_table(index=["kind","sub","metric"], values="val", aggfunc="first") \
             .rename(columns={"val": col})
        frames.append(p)
        col_order.append(col)
        hdr1_labels.append(f"{y}년")
        hdr2_labels.append("월평균")

    # 2) 전전월/전월/선택월 (구분3 필터 없음)
    prev2_y, prev2_m = _month_shift(sel_y, sel_m, -2)
    prev_y,  prev_m  = _month_shift(sel_y, sel_m, -1)

    dyn = [
        (prev2_y, prev2_m, f"{prev2_m}월({prev2_y})", f"{prev2_m}월"),
        (prev_y,  prev_m,  f"{prev_m}월({prev_y})",  f"{prev_m}월"),
        (sel_y,   sel_m,   f"{sel_m}월({sel_y})",    f"{sel_m}월"),
    ]
    for y, m, col, sublab in dyn:
        dd = d[(d["연도"] == y) & (d["월"] == m)]

        if dd.empty:
            # 데이터 없을 때도 컬럼/헤더는 채워둔다
            col_order.append(col)
            hdr1_labels.append(f"{y}년")     # ← 해당 월의 실제 연도
            hdr2_labels.append(sublab)       # ← 'M월'
            continue

        p  = dd.pivot_table(index=["kind","sub","metric"], values="val", aggfunc="first") \
               .rename(columns={"val": col})
        frames.append(p)
        col_order.append(col)
        hdr1_labels.append(f"{y}년")         # ← 기존 sel_y 대신 실제 연도 사용
        hdr2_labels.append(sublab)

    # 3) 병합
    wide = None
    for f in frames:
        wide = f if wide is None else wide.join(f, how="outer")

    # --- 공통: 숫자 변환 함수 ---
    def _safe(x):
        try:
            return float(x)
        except:
            return np.nan

    # --- (추가) 탄소강/합금강 포스코·JFE 비중 계산 ---
    #   각 kind별로:
    #     포스코 비중 = 포스코 중량 / (포스코+JFE 중량) * 100
    #     JFE 비중   = JFE 중량   / (포스코+JFE 중량) * 100
    if wide is not None and not wide.empty:
        for kind in ["탄소강", "합금강"]:
            idx_pos_w = (kind, "포스코", "중량")
            idx_jfe_w = (kind, "JFE",   "중량")
            idx_pos_s = (kind, "포스코", "비중")
            idx_jfe_s = (kind, "JFE",   "비중")

            # 비중 행이 없으면 생성
            for idx in [idx_pos_s, idx_jfe_s]:
                if idx not in wide.index:
                    wide.loc[idx, :] = np.nan

            for col in wide.columns:
                pos_w = _safe(wide.loc[idx_pos_w, col]) if idx_pos_w in wide.index else np.nan
                jfe_w = _safe(wide.loc[idx_jfe_w, col]) if idx_jfe_w in wide.index else np.nan
                denom = pos_w + jfe_w

                if denom and not np.isnan(denom) and denom != 0:
                    pos_share = pos_w / denom * 100.0
                    jfe_share = jfe_w / denom * 100.0
                else:
                    pos_share = np.nan
                    jfe_share = np.nan

                # ✅ 항상 계산값으로 덮어쓰기 (지금은 0%라서 아예 다시 계산해주기 위함)
                wide.loc[idx_pos_s, col] = pos_share
                wide.loc[idx_jfe_s, col] = jfe_share

    # --- JFE 사용비중 자동 계산 (탄소강+합금강 전체 기준) ---
    # 현재 wide는 여러 metric이 섞여 있으므로, '중량' 행만 집계해서 비중 계산
    idxs_jfe = [(k, "JFE",   "중량") for k in ["탄소강", "합금강"]]
    idxs_pos = [(k, "포스코", "중량") for k in ["탄소강", "합금강"]]

    jfe_share_col = {}
    for col in (wide.columns if wide is not None else []):
        jfe_w = sum(_safe(wide.loc[idx, col]) for idx in idxs_jfe if idx in wide.index)
        pos_w = sum(_safe(wide.loc[idx, col]) for idx in idxs_pos if idx in wide.index)
        denom = jfe_w + pos_w
        jfe_share_col[col] = (jfe_w / denom * 100.0) if (denom and not np.isnan(denom) and denom != 0) else np.nan

    # 결과를 행 ("", "JFE 사용비중", "비중") 에 반영 (없으면 생성, 있으면 NaN만 채움)
    jfe_row = ("", "JFE 사용비중", "비중")
    if wide is None or wide.empty:
        wide = pd.DataFrame(index=pd.Index([jfe_row]))
    if jfe_row not in wide.index:
        wide.loc[jfe_row, :] = np.nan

    for col, val in jfe_share_col.items():
        if pd.isna(wide.at[jfe_row, col]):
            wide.at[jfe_row, col] = val


    # 4) 보기 좋은 행 순서
    desired = []
    for kind in ["탄소강", "합금강"]:
        for sub in ["포스코", "JFE"]:
            for metric in ["중량", "비중"]:
                desired.append((kind, sub, metric))
        desired.append((kind, "평균단가", "평균단가"))
    desired += [
        ("", "JFE 사용비중", "비중"),
        ("", "전월(전년)대비 손익영향 금액", "값"),
    ]

    if wide is None or wide.empty:
        wide = pd.DataFrame(
            index=pd.MultiIndex.from_tuples(desired, names=["kind","sub","metric"])
        )
    else:
        wide = wide.reindex([idx for idx in desired if idx in wide.index])

    # 5) 컬럼 보장 + 순서 고정
    for c in col_order:
        if c not in wide.columns:
            wide[c] = np.nan
    wide = wide[col_order]

    # 6) kind / sub 표시 정리
    #   - kind: (탄소강, 합금강) 블록마다 첫 행만 표시
    #   - sub : 각 kind 블록 안에서 (포스코, JFE)별 첫 행만 표시
    idx_df = wide.index.to_frame(index=False)  # 컬럼: kind, sub, metric

    # 6-1) sub 정리: (kind, sub) 조합별로 첫 행만 sub 표시
    for k in ["탄소강", "합금강"]:
        mask_kind = idx_df["kind"] == k
        if not mask_kind.any():
            continue
        # 이 kind에서 등장하는 sub 목록
        for s in ["포스코", "JFE"]:
            mask = mask_kind & (idx_df["sub"] == s)
            idxs = idx_df.index[mask].tolist()
            if len(idxs) > 1:
                # 같은 kind, 같은 sub 안에서 첫 행만 sub 유지, 나머지는 공백
                idx_df.loc[idxs[1:], "sub"] = ""

    # 6-2) kind 정리: kind 블록 안에서 첫 행만 kind 표시
    for k in ["탄소강", "합금강"]:
        mask_kind = idx_df["kind"] == k
        idxs = idx_df.index[mask_kind].tolist()
        if len(idxs) > 1:
            idx_df.loc[idxs[1:], "kind"] = ""

    # 수정된 인덱스를 다시 MultiIndex로 적용
    wide.index = pd.MultiIndex.from_frame(idx_df)

    return wide, col_order, hdr1_labels, hdr2_labels





# ===== 공통 유틸 =====
def _to_num(x):
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return np.nan

def _month_shift(y: int, m: int, delta: int):
    t = y * 12 + (m - 1) + delta
    ny = t // 12
    nm = t % 12 + 1
    return int(ny), int(nm)

def _safe_series(obj, index):
    if obj is None:
        return pd.Series(index=index, dtype=float)
    if isinstance(obj, pd.Series):
        return obj.reindex(index).astype(float)
    return pd.Series(index=index, dtype=float)

def _share(series: pd.Series) -> pd.Series:
    if not isinstance(series, pd.Series) or series.empty:
        return pd.Series(index=series.index if isinstance(series, pd.Series) else [], dtype=float)
    tot = float(series.sum(skipna=True))
    if not np.isfinite(tot) or tot == 0:
        return pd.Series(index=series.index, dtype=float)
    return series / tot * 100.0

def _thousand_out(x: float) -> float:
    if not np.isfinite(x):
        return np.nan
    # 백의자리 반올림 후 1000으로 스케일다운
    return round(float(x), -3) / 1000

def _milions_out(x: float) -> float:
    if not np.isfinite(x):
        return np.nan
    # 백의자리 반올림 후 1000으로 스케일다운
    return round(float(x), -5) / 1000000


# ===== 메인 =====
def build_maker_receipt_wide(
    df_raw: pd.DataFrame,
    sel_y: int,
    sel_m: int,
    base_year: int | None = None,  # 기본은 sel_y-1
    base_avg_mode: str = "mean",   # "mean" 또는 "december"
):
    # ========= 공통 도우미 =========
    def _safe_series(s, idx):
        """None이면 빈 시리즈, 있으면 idx로 reindex"""
        if s is None:
            return pd.Series(index=idx, dtype=float)
        return pd.to_numeric(pd.Series(s), errors="coerce").reindex(idx)

    def _price(amount_s: pd.Series, weight_s: pd.Series) -> pd.Series:
        """(금액/중량)*1000; 중량<=0 또는 NaN은 NaN"""
        w = pd.to_numeric(weight_s, errors="coerce")
        a = pd.to_numeric(amount_s, errors="coerce")
        w = w.where(w > 0)  # 0 -> NaN
        return (a / w) * 1000.0

    # ========= 데이터 준비 =========
    d = df_raw.copy()
    d = d[d["구분1"] == "메이커별 입고추이"].copy()
    d["연도"] = pd.to_numeric(d["연도"], errors="coerce")
    d["월"]  = pd.to_numeric(d["월"],  errors="coerce")
    d["실적"] = pd.to_numeric(d["실적"].apply(_to_num), errors="coerce")

    fixed_order = ["포스코", "JFE", "세아창원특수강", "현대제철", "세아베스틸"]
    makers_all  = list(d["구분2"].dropna().unique())
    tail        = sorted([m for m in makers_all if m not in fixed_order])
    makers      = fixed_order + tail

    # 피벗
    w = d[d["구분3"] == "중량"].pivot_table(index="구분2", columns=["연도","월"], values="실적", aggfunc="sum")
    a = d[d["구분3"] == "금액"].pivot_table(index="구분2", columns=["연도","월"], values="실적", aggfunc="sum")

    if base_year is None:
        base_year = sel_y - 1

    # 기준년 월평균(또는 12월)
    if base_avg_mode == "december":
        base_weight = _safe_series(w.get((base_year, 12)), makers)
        base_amount = _safe_series(a.get((base_year, 12)), makers)
    else:
        if not w.empty:
            mask_by = (w.columns.get_level_values(0) == base_year)
            base_weight = (w.loc[:, mask_by].mean(axis=1, skipna=True) if mask_by.any()
                           else pd.Series(index=makers, dtype=float))
        else:
            base_weight = pd.Series(index=makers, dtype=float)
        if not a.empty:
            mask_ay = (a.columns.get_level_values(0) == base_year)
            base_amount = (a.loc[:, mask_ay].mean(axis=1, skipna=True) if mask_ay.any()
                           else pd.Series(index=makers, dtype=float))
        else:
            base_amount = pd.Series(index=makers, dtype=float)

    base_weight = base_weight.reindex(makers)
    base_amount = base_amount.reindex(makers)
    base_share  = _share(base_weight)

    # 선택연도 YTD 월평균(1~sel_m)
    if not w.empty:
        sel_mask = (w.columns.get_level_values(0) == sel_y) & (w.columns.get_level_values(1) <= sel_m)
        sel_weight = (w.loc[:, sel_mask].mean(axis=1, skipna=True) if sel_mask.any()
                      else pd.Series(index=makers, dtype=float))
    else:
        sel_mask = None
        sel_weight = pd.Series(index=makers, dtype=float)
    sel_weight = sel_weight.reindex(makers)
    sel_share  = _share(sel_weight)

    if not a.empty and sel_mask is not None and sel_mask.any():
        sel_amount = a.loc[:, sel_mask].mean(axis=1, skipna=True).reindex(makers)
    else:
        sel_amount = pd.Series(index=makers, dtype=float)

    # ===== 단가 계산(금액/중량*1000) =====
    base_price = _price(base_amount, base_weight)  # 기준년도 월평균 단가
    sel_price  = _price(sel_amount,  sel_weight)   # 선택년도 YTD 월평균 단가

    def price_series(y, m):
        aw = _safe_series(a.get((y, m)), makers)
        ww = _safe_series(w.get((y, m)), makers)
        return _price(aw, ww)  # 월 단가

    # 전월/전전월/전전전월
    prev_y,  prev_m  = _month_shift(sel_y, sel_m, -1)
    prev2_y, prev2_m = _month_shift(sel_y, sel_m, -2)
    prev3_y, prev3_m = _month_shift(sel_y, sel_m, -3)

    prev_w  = _safe_series(w.get((prev_y,  prev_m)),  makers)
    prev2_w = _safe_series(w.get((prev2_y, prev2_m)), makers)
    prev_s  = _share(prev_w)
    prev2_s = _share(prev2_w)

    p_prev2 = price_series(prev2_y, prev2_m)
    p_prev  = price_series(prev_y,  prev_m)
    p_prev3 = price_series(prev3_y, prev3_m)

    diff_prev2 = p_prev2 - p_prev3  # 전전월 - 전전전월
    diff_prev  = p_prev  - p_prev2  # 전월 - 전전월

    # ===== 컬럼 정의 =====
    col_defs = [
        (f"'{str(base_year)[-2:]}년", "월평균"),
        (f"'{str(base_year)[-2:]}년", "매입비중"),
        (f"{prev2_y}.{prev2_m}월", "중량"),
        (f"{prev2_y}.{prev2_m}월", "매입비중"),
        (f"{prev_y}.{prev_m}월", "중량"),
        (f"{prev_y}.{prev_m}월", "매입비중"),
        (f"'{str(sel_y)[-2:]}년", "월평균"),
        (f"'{str(sel_y)[-2:]}년", "매입비중"),
    ]
    cols_mi = pd.MultiIndex.from_tuples(col_defs, names=["상단","하단"])

    # ===== 표 조립 (총계 제거) =====
    data = {}
    for mk in makers:
        # 중량
        data[(mk, "중량")] = [
            base_weight.get(mk, np.nan), base_share.get(mk, np.nan),
            prev2_w.get(mk, np.nan),     prev2_s.get(mk, np.nan),
            prev_w.get(mk, np.nan),      prev_s.get(mk, np.nan),
            sel_weight.get(mk, np.nan),  sel_share.get(mk, np.nan),
        ]
        # 단가 (월평균/월 자리에 값, 비중 자리는 NaN)
        data[(mk, "단가")] = [
            base_price.get(mk, np.nan),  np.nan,
            p_prev2.get(mk, np.nan),     np.nan,
            p_prev.get(mk, np.nan),      np.nan,
            sel_price.get(mk, np.nan),   np.nan,
        ]
        # 증감 (단가 차)
        r = [np.nan] * len(col_defs)
        r[2] = diff_prev2.get(mk, np.nan)  # 전전월 증감
        r[4] = diff_prev.get(mk, np.nan)   # 전월 증감
        data[(mk, "증감")] = r

    wide = pd.DataFrame.from_dict(data, orient="index")
    wide = wide.reindex(columns=range(len(col_defs)))
    wide.columns = cols_mi

    ordered_index = []
    for mk in makers:
        ordered_index.extend([(mk,"중량"), (mk,"단가"), (mk,"증감")])
    wide = wide.reindex(pd.MultiIndex.from_tuples(ordered_index, names=["구분","항목"]))

    # 혹시 남은 ±inf 제거
    wide = wide.replace([np.inf, -np.inf], np.nan)

    return wide, cols_mi



##### 제조 가공비 #####

from typing import Tuple, Dict, Optional


# ===================== 유틸 =====================
def month_shift(y: int, m: int, delta: int) -> Tuple[int, int]:
    t = y * 12 + (m - 1) + delta
    return t // 12, t % 12 + 1

def _num(s):
    if isinstance(s, pd.Series):
        s = s.astype(str).str.replace(",", "", regex=False).str.strip()
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(str(s).replace(",", "").strip(), errors="coerce")

def _pick_col(cols, candidates):

    for c in candidates:
        if c in cols:
            return c
    low = {c.lower(): c for c in cols}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]

    for pat in candidates:
        rx = re.compile(pat, flags=re.I)
        for c in cols:
            if rx.search(str(c)):
                return c
    return None



def _to_wide(df_src: pd.DataFrame) -> pd.DataFrame:

    cols = list(df_src.columns)
    c_y  = _pick_col(cols, ["연도", "년도", "year"])
    c_m  = _pick_col(cols, ["월", "month"])
    c_it = _pick_col(cols, ["구분1", "항목", "대분류"])
    c_site = _pick_col(cols, ["구분3", "사업장", "공장", "Site"])
    c_val  = _pick_col(cols, ["실적", "금액", "비용", "원가", "Amount", "AMT"])

    if not all([c_y, c_m, c_it, c_site, c_val]):
        raise ValueError("필수 컬럼(연도,월,구분1,구분3,실적)을 찾을 수 없습니다.")

    df = df_src.copy()
    df[c_y]   = _num(df[c_y])
    df[c_m]   = _num(df[c_m])
    df[c_val] = _num(df[c_val]).fillna(0)

    def _site_norm(s: str) -> str:
        s = str(s).strip()
        if "포항" in s :
            return "포항"
        if "충주2" in s :
            return "충주2"
        if "충주" in s:
            return "충주"
        return "기타"

    df["__site__"] = df[c_site].map(_site_norm)
    df = df[df["__site__"].isin(["포항", "충주", "충주2"])]

    pv = (
        df.groupby([c_y, c_m, c_it, "__site__"])[c_val].sum().reset_index()
          .pivot(index=[c_y, c_m, c_it], columns="__site__", values=c_val)
          .reset_index()
    )
    for c in ["포항", "충주", "충주2"]:
        if c not in pv.columns:
            pv[c] = 0.0

    pv.rename(columns={c_y: "연도", c_m: "월", c_it: "항목"}, inplace=True)
    pv["계"] = pv[["포항", "충주", "충주2"]].sum(axis=1)
    return pv[["연도", "월", "항목", "포항", "충주", "충주2", "계"]]


# 구분 고정
_ORDER = [
    "부재료비",
    "급료와임금",
    "상여금",
    "잡급",
    "퇴직급여충당금",
    "제조노무비",
    "전력비",
    "수도료",
    "감가상각비",
    "수선비",
    "소모품비",
    "복리후생비",
    "지급임차료",
    "지급수수료",
    "외주용역비",
    "외주가공비",
    "기타",
    "제조경비",
    "총합",
    "원재투입중량",
    "투입중량 원단위(천원)",
]

_LABOR = ["급료와임금", "상여금", "잡급", "퇴직급여충당금"]
_OH    = ["전력비","수도료","감가상각비","수선비","소모품비","복리후생비",
          "지급임차료","지급수수료","외주용역비","외주가공비","기타"]

def _month_list(df_wide: pd.DataFrame, y: int, m: int) -> pd.DataFrame:
    """특정 연월의 요구 """
    d = df_wide[(df_wide["연도"] == y) & (df_wide["월"] == m)].copy()

    # 기본 항목 합산
    base = d.groupby("항목")[["포항","충주","충주2","계"]].sum()

    # 파생 항목 계산
    def _row_sum(names):
        if not names: 
            return pd.Series([0,0,0,0], index=["포항","충주","충주2","계"])
        sub = base.reindex(names).fillna(0)
        return sub.sum()

    # 제조노무비, 제조경비, 총합
    labor = _row_sum(_LABOR)
    oh    = _row_sum(_OH)
    # 부재료비가 없을 수도 있으므로 보정
    material = base.reindex(["부재료비"]).fillna(0).sum()
    total = labor.add(oh, fill_value=0).add(material, fill_value=0)

    # 원재투입중량 (항목명 그대로 존재)
    weight = d[d["항목"]=="원재투입중량"][["포항","충주","충주2","계"]].sum()
    if weight.empty:
        weight = pd.Series([np.nan]*4, index=["포항","충주","충주2","계"])

    # 원단위(천원) = 총합(백만원) * 1000 / 원재투입중량
    unit = total * 1000.0 / weight.replace({0: np.nan})

    # 순서대로 테이블 만들기
    rows = {}
    for name in _ORDER:
        if name == "제조노무비":
            rows[name] = labor
        elif name == "제조경비":
            rows[name] = oh
        elif name == "총합":
            rows[name] = total
        elif name == "원재투입중량":
            rows[name] = weight
        elif name == "투입중량 원단위(천원)":
            rows[name] = unit
        else:
            rows[name] = base.reindex([name]).fillna(0).sum()

    snap = pd.DataFrame(rows).T[["포항","충주","충주2","계"]]
    snap.index.name = "구분"
    return snap


# ===================== 최종 표 =====================
def _make_table(prev_snap: pd.DataFrame, curr_snap: pd.DataFrame) -> pd.DataFrame:
    idx = prev_snap.index.union(curr_snap.index)
    prev = prev_snap.reindex(idx).fillna(0.0)
    curr = curr_snap.reindex(idx).fillna(0.0)
    diff = curr - prev

    prev.columns = pd.MultiIndex.from_product([["전월"], prev.columns])
    curr.columns = pd.MultiIndex.from_product([["당월"], curr.columns])
    diff.columns = pd.MultiIndex.from_product([["전월대비"], diff.columns])

    out = pd.concat([prev, curr, diff], axis=1).reset_index()
    # 명시적으로 by 지정 → sort_values 에러 방지
    order_map = {name: i for i, name in enumerate(_ORDER)}
    out["__ord__"] = out["구분"].map(order_map).fillna(9999)
    out = out.sort_values(by="__ord__").drop(columns="__ord__").reset_index(drop=True)
    return out


def build_mfg_cost_table(df_src: pd.DataFrame, sel_y: int, sel_m: int):

    wide = _to_wide(df_src)

    prev_y, prev_m = month_shift(sel_y, sel_m, -1)
    prev_snap = _month_list(wide, prev_y, prev_m)
    curr_snap = _month_list(wide, sel_y, sel_m)

    disp = _make_table(prev_snap, curr_snap)
    meta = dict(prev_y=prev_y, prev_m=prev_m, sel_y=sel_y, sel_m=sel_m)
    return disp, meta



##### 판매비와 인건비 #####

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional

# ===================== 유틸 =====================

import re

def _norm_txt(s: str) -> str:
    return re.sub(r"\s+", "", str(s)).lower()

# 판매량 별칭들: 필요 시 여기에 더 추가 가능
_SALES_ALIASES = [
   "판매량(제품)"
]

def _find_sales_key(index_like) -> Optional[str]:
    """
    Series.index 또는 DataFrame 컬럼명 리스트에서 '판매량' 의미의 키를 찾아 반환.
    없으면 None.
    """
    idx = [str(x) for x in index_like]
    # 1) 미리 정의한 별칭 우선
    lowmap = { _norm_txt(x): x for x in idx }
    for alias in _SALES_ALIASES:
        if _norm_txt(alias) in lowmap:
            return lowmap[_norm_txt(alias)]
    # 2) fallback: '판매량' 포함 텍스트 탐색
    for x in idx:
        if "판매량" in _norm_txt(x):
            return x
    return None

def month_shift(y: int, m: int, delta: int) -> Tuple[int, int]:
    t = y * 12 + (m - 1) + delta
    return t // 12, t % 12 + 1

def _num(s):
    if isinstance(s, pd.Series):
        s = s.astype(str).str.replace(",", "", regex=False).str.strip()
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(str(s).replace(",", "").strip(), errors="coerce")

def _pick_col(cols, candidates):
    # 완전일치 → 소문자일치 → 부분일치
    for c in candidates:
        if c in cols:
            return c
    low = {c.lower(): c for c in cols}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]
    import re
    for pat in candidates:
        rx = re.compile(pat, flags=re.I)
        for c in cols:
            if rx.search(str(c)):
                return c
    return None


# =========================================================
# =============== 1) 제조 가공비(롱→와이드) ===============
# =========================================================
def _to_wide(df_src: pd.DataFrame) -> pd.DataFrame:
    """
    f_26 예시 스키마(롱):
      - 구분1(항목), 구분3(사업장: 포항/충주/충주2), 연도, 월, 실적
    를 (연도,월,항목,포항,충주,충주2,계) 와이드로 변환
    """
    cols = list(df_src.columns)
    c_y  = _pick_col(cols, ["연도"])
    c_m  = _pick_col(cols, ["월"])
    c_it = _pick_col(cols, ["구분1"])
    c_site = _pick_col(cols, ["구분3"])
    c_val  = _pick_col(cols, ["실적"])

    if not all([c_y, c_m, c_it, c_site, c_val]):
        raise ValueError("필수 컬럼(연도,월,구분1,구분3,실적)을 찾을 수 없습니다.")

    df = df_src.copy()
    df[c_y]   = _num(df[c_y])
    df[c_m]   = _num(df[c_m])
    df[c_val] = _num(df[c_val]).fillna(0)

    def _site_norm(s: str) -> str:
        s = str(s).strip()
        if "포항" in s :
            return "포항"
        if "충주2" in s :
            return "충주2"
        if "충주" in s:
            return "충주"
        return "기타"

    df["__site__"] = df[c_site].map(_site_norm)
    df = df[df["__site__"].isin(["포항", "충주", "충주2"])]

    pv = (
        df.groupby([c_y, c_m, c_it, "__site__"])[c_val].sum().reset_index()
          .pivot(index=[c_y, c_m, c_it], columns="__site__", values=c_val)
          .reset_index()
    )
    for c in ["포항", "충주", "충주2"]:
        if c not in pv.columns:
            pv[c] = 0.0

    pv.rename(columns={c_y: "연도", c_m: "월", c_it: "항목"}, inplace=True)
    pv["계"] = pv[["포항", "충주", "충주2"]].sum(axis=1)
    return pv[["연도", "월", "항목", "포항", "충주", "충주2", "계"]]


#구분 고정
_ORDER = [
    "부재료비",
    "급료와임금",
    "상여금",
    "잡급",
    "퇴직급여충당금",
    "제조노무비",
    "전력비",
    "수도료",
    "감가상각비",
    "수선비",
    "소모품비",
    "복리후생비",
    "지급임차료",
    "지급수수료",
    "외주용역비",
    "외주가공비",
    "기타",
    "제조경비",
    "총합",
    "원재투입중량",
    "투입중량 원단위(천원)",
]
_LABOR = ["급료와임금", "상여금", "잡급", "퇴직급여충당금"]
_OH    = ["전력비","수도료","감가상각비","수선비","소모품비","복리후생비",
          "지급임차료","지급수수료","외주용역비","외주가공비","기타"]

def _month_list(df_wide: pd.DataFrame, y: int, m: int) -> pd.DataFrame:
    """특정 연월의 요구 행 순서 생성"""
    d = df_wide[(df_wide["연도"] == y) & (df_wide["월"] == m)].copy()

    # 기본 항목 합산
    base = d.groupby("항목")[["포항","충주","충주2","계"]].sum()

    # 파생 항목 계산
    def _row_sum(names):
        if not names:
            return pd.Series([0,0,0,0], index=["포항","충주","충주2","계"])
        sub = base.reindex(names).fillna(0)
        return sub.sum()

    labor = _row_sum(_LABOR)
    oh    = _row_sum(_OH)
    material = base.reindex(["부재료비"]).fillna(0).sum()
    total = labor.add(oh, fill_value=0).add(material, fill_value=0)

    # 원재투입중량
    weight = d[d["항목"]=="원재투입중량"][["포항","충주","충주2","계"]].sum()
    if weight.empty:
        weight = pd.Series([np.nan]*4, index=["포항","충주","충주2","계"])

    # 원단위(천원)
    unit = total * 1000.0 / weight.replace({0: np.nan})

    # 순서대로 테이블
    rows = {}
    for name in _ORDER:
        if name == "제조노무비":
            rows[name] = labor
        elif name == "제조경비":
            rows[name] = oh
        elif name == "총합":
            rows[name] = total
        elif name == "원재투입중량":
            rows[name] = weight
        elif name == "투입중량 원단위(천원)":
            rows[name] = unit
        else:
            rows[name] = base.reindex([name]).fillna(0).sum()

    snap = pd.DataFrame(rows).T[["포항","충주","충주2","계"]]
    snap.index.name = "구분"
    return snap

def _make_table(prev_snap: pd.DataFrame, curr_snap: pd.DataFrame) -> pd.DataFrame:
    idx = prev_snap.index.union(curr_snap.index)
    prev = prev_snap.reindex(idx).fillna(0.0)
    curr = curr_snap.reindex(idx).fillna(0.0)
    diff = curr - prev

    prev.columns = pd.MultiIndex.from_product([["전월"], prev.columns])
    curr.columns = pd.MultiIndex.from_product([["당월"], curr.columns])
    diff.columns = pd.MultiIndex.from_product([["전월대비"], diff.columns])

    out = pd.concat([prev, curr, diff], axis=1).reset_index()
    order_map = {name: i for i, name in enumerate(_ORDER)}
    out["__ord__"] = out["구분"].map(order_map).fillna(9999)
    out = out.sort_values(by="__ord__").drop(columns="__ord__").reset_index(drop=True)
    return out

def build_mfg_cost_table(df_src: pd.DataFrame, sel_y: int, sel_m: int):
    wide = _to_wide(df_src)
    prev_y, prev_m = month_shift(sel_y, sel_m, -1)
    prev_snap = _month_list(wide, prev_y, prev_m)
    curr_snap = _month_list(wide, sel_y, sel_m)
    disp = _make_table(prev_snap, curr_snap)
    meta = dict(prev_y=prev_y, prev_m=prev_m, sel_y=sel_y, sel_m=sel_m)
    return disp, meta



# 행 순서
_SGNA_ORDER = [
    # 인건비
    "급료와임금","상여금","퇴직급여충당금","인건비",
    # 관리비
    "복리후생비","지급임차료","사용권자산 감가상각비","접대비","세금과공과",
    "대손상각비","지급수수료","A/S비","경상연구비","기타","관리비",
    # 판매비
    "판관-운반비","판관-수출개별비","판매비",
    # 합계/원단위
    "합계","판매량","인건비 및 관리비 원단위","운반비 원단위",
]

_SGNA_LABOR = ["급료와임금","상여금","퇴직급여충당금"]
_SGNA_ADMIN = ["복리후생비","지급임차료","사용권자산 감가상각비","접대비",
               "세금과공과","대손상각비","지급수수료","A/S비","경상연구비","기타"]
_SGNA_SELL  = ["판관-운반비","판관-수출개별비"]

def _to_wide_sgna(df_src: pd.DataFrame) -> pd.DataFrame:
    """숫자 월만 집계(월평균 행 제외) → 최근 3개월/전월대비 계산용"""
    cols = list(df_src.columns)
    c_y   = _pick_col(cols, ["연도","년도","year"])
    c_m   = _pick_col(cols, ["월","month"])
    c_it  = _pick_col(cols, ["항목","구분1","대분류","계정과목"])
    c_val = _pick_col(cols, ["실적","금액","비용","원가","Amount","AMT"])
    if not all([c_y, c_m, c_it, c_val]):
        raise ValueError("필수 컬럼(연도, 월, 항목, 실적)을 찾을 수 없습니다.")

    df = df_src.copy()
    df["__월_raw__"] = df[c_m].astype(str).str.strip()
    df[c_y]   = _num(df[c_y])
    df[c_m]   = _num(df[c_m])
    df[c_val] = _num(df[c_val]).fillna(0)

    df = df[df[c_m].notna()]  # 숫자월만
    g = df.groupby([c_y, c_m, c_it])[c_val].sum().reset_index()
    g.rename(columns={c_y:"연도", c_m:"월", c_it:"항목", c_val:"계"}, inplace=True)
    return g[["연도","월","항목","계"]]

def _extract_explicit_avg(df_src: pd.DataFrame) -> pd.DataFrame:
    """월 컬럼에 '평균'이 포함된 행만 모아 연도·항목별 합계(=월평균 값)를 만든다."""
    cols = list(df_src.columns)
    c_y   = _pick_col(cols, ["연도"])
    c_m   = _pick_col(cols, ["월"])
    c_it  = _pick_col(cols, ["구분1"])
    c_val = _pick_col(cols, ["실적"])
    if not all([c_y, c_m, c_it, c_val]):
        raise ValueError("필수 컬럼(연도, 월, 항목, 실적)을 찾을 수 없습니다.")

    df = df_src.copy()
    df["__월_raw__"] = df[c_m].astype(str).str.strip()
    df[c_y]   = _num(df[c_y])
    df[c_val] = _num(df[c_val]).fillna(0)

    avg_rows = df[df["__월_raw__"].str.contains("평균", na=False)]
    if avg_rows.empty:
        return pd.DataFrame(columns=["연도","항목","계"])

    g = avg_rows.groupby([c_y, c_it])[c_val].sum().reset_index()
    g.rename(columns={c_y:"연도", c_it:"항목", c_val:"계"}, inplace=True)
    return g[["연도","항목","계"]]

def _sgna_from_base_series(base: pd.Series, sales_qty_override: Optional[float]=None) -> pd.Series:
    def _sum(keys): return float(base.reindex(keys).fillna(0).sum())

    labor = _sum(_SGNA_LABOR)
    admin = _sum(_SGNA_ADMIN)
    sell  = _sum(_SGNA_SELL)

    # 판매량: alias 인식
    sales_key = _find_sales_key(base.index)
    sales_from_base = float(base.get(sales_key, 0.0)) if sales_key else 0.0


    if sales_qty_override is not None and not pd.isna(sales_qty_override) and sales_qty_override != 0:
        sales_qty = float(sales_qty_override)
    else:
        sales_qty = sales_from_base

    total = labor + admin + sell
    unit_la = ((labor + admin) / sales_qty * 1000.0) if sales_qty else float("nan")
    unit_f  = (sell / sales_qty * 1000.0) if sales_qty else float("nan")

    out = {}
    # 원본 항목 값은 그대로
    for k in set(_SGNA_LABOR + _SGNA_ADMIN + _SGNA_SELL):
        out[k] = float(base.get(k, 0.0))
    # 표준 라벨로 매핑해서 '판매량' 행 채우기
    out["판매량"] = sales_from_base

    # 파생
    out["인건비"] = labor
    out["관리비"] = admin
    out["판매비"] = sell
    out["합계"]   = total
    out["인건비 및 관리비 원단위"] = unit_la
    out["운반비 원단위"]         = unit_f
    return pd.Series(out).reindex(_SGNA_ORDER)


def _sgna_list(df_wide: pd.DataFrame, y: int, m: int) -> pd.Series:
    """숫자월 데이터로 특정 연월 순서 (행=_SGNA_ORDER)"""
    d = df_wide[(df_wide["연도"]==y) & (df_wide["월"]==m)]
    base = d.groupby("항목")["계"].sum()
    return _sgna_from_base_series(base)

import numpy as np
import pandas as pd

def build_sgna_table(df_src: pd.DataFrame, sel_y: int, sel_m: int):


    # 1) 숫자월 데이터(최근 3개월/전월대비)
    wide = _to_wide_sgna(df_src)

    # 2) 월평균(명시행) 추출
    avg_explicit = _extract_explicit_avg(df_src)  # (연도, 항목, 계)

    # ★ 월평균 연도는 무조건 "전전연도, 전연도"
    avg_years = [sel_y - 2, sel_y - 1]

    # 실제로 월평균 행이 존재하는 연도 집합
    if not avg_explicit.empty:
        years_have_avg = set(
            avg_explicit["연도"]
            .dropna()
            .astype(int)
            .tolist()
        )
    else:
        years_have_avg = set()

    # 3) 최근 3개월 + 전월대비
    m2_y, m2_m = month_shift(sel_y, sel_m, -2)
    m1_y, m1_m = month_shift(sel_y, sel_m, -1)
    s_m2 = _sgna_list(wide, m2_y, m2_m)
    s_m1 = _sgna_list(wide, m1_y, m1_m)
    s_m0 = _sgna_list(wide, sel_y, sel_m)
    diff = s_m0 - s_m1

    # 4) 본문 데이터(월/전월대비부터 넣고, 월평균은 앞에 삽입)
    data = {
        "구분": _SGNA_ORDER,
        f"{m2_m}월": s_m2.values,
        f"{m1_m}월": s_m1.values,
        f"{sel_m}월": s_m0.values,
        "전월대비": diff.values,
    }

    # 5) 연도별 '월평균' 
    for y in reversed(avg_years):
        if y in years_have_avg:
            # ----- 실제 월평균 데이터 있는 연도 -----
            base = (
                avg_explicit[avg_explicit["연도"] == y]
                .set_index("항목")["계"]
                .astype(float)
            )

            # ---- 판매량 월평균 확보 (alias 인식) ----
            sales_key = _find_sales_key(base.index)
            sales_avg = base.get(sales_key, np.nan) if sales_key else np.nan

            if pd.isna(sales_avg) or sales_avg == 0:
                # 월=월평균에 판매량이 없으면, 숫자월 데이터에서 같은 연도의 판매량 평균 구함
                wide_y = wide[wide["연도"] == int(y)]
                # alias 인식: 해당 연도에서 '판매량*' 항목만 필터
                sales_rows = wide_y[wide_y["항목"].apply(lambda s: _find_sales_key([s]) is not None)]
                if not sales_rows.empty:
                    sales_avg = sales_rows.groupby("월")["계"].sum().mean()
                else:
                    sales_avg = np.nan

            s_avg = _sgna_from_base_series(base, sales_qty_override=sales_avg)
            col_values = s_avg.values

        else:
            col_values = np.full(len(_SGNA_ORDER), np.nan)

        # 앞쪽으로 prepend
        data = {f"'{int(y)}년 월평균": col_values, **data}

    disp = pd.DataFrame(data)

    # 숫자형 보정
    numeric_cols = [c for c in disp.columns if c != "구분"]
    for c in numeric_cols:
        disp[c] = pd.to_numeric(disp[c], errors="coerce")


    return disp, dict(avg_years=avg_years, months=[m2_m, m1_m, sel_m])





##### 성과급 및 격려금 #####



def _num(s):
    if isinstance(s, pd.Series):
        s = s.astype(str).str.replace(",", "", regex=False).str.strip()
        return pd.to_numeric(s, errors="coerce")
    return pd.to_numeric(str(s).replace(",", "").strip(), errors="coerce")

# ========== 성과급 및 격려금 (구분1~4 전용) ==========
_BONUS_ORDER = ["제조", "판관", "임원", "직원", "총"]

def _b_group_norm(s: str) -> str:
    s = str(s).strip()
    if "제조" in s: return "제조"
    if "임원" in s: return "임원"
    if "직원" in s: return "직원"
    return s

def _to_long_bonus_28(df_src: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    need = ["구분1","구분2","구분3","구분4","연도","월","실적"]
    for c in need:
        if c not in df_src.columns:
            raise ValueError(f"필수 컬럼 누락: {c}")

    df = df_src.copy()

    # 이 테이블만 필터(혹시 다른 항목 섞여있을 대비)
    df = df[df["구분1"].astype(str).str.contains("성과급", na=False)]

    # 숫자화
    df["연도"] = _num(df["연도"])
    df["월"]   = _num(df["월"])    # 100%|연간/월은 NaN이어도 무방
    df["실적"] = _num(df["실적"]).fillna(0.0)

    # 부문 정규화
    df["부문"] = df["구분2"].map(_b_group_norm)

    # --- 당월(월별) 계획/실적 ---
    mon = df[df["구분4"]=="당월"].copy()
    plan = (mon[mon["구분3"]=="계획"]
            .groupby(["연도","월","부문"])["실적"].sum().rename("계획"))
    act  = (mon[mon["구분3"]=="실적"]
            .groupby(["연도","월","부문"])["실적"].sum().rename("실적"))
    mon_tbl = pd.concat([plan, act], axis=1).fillna(0.0).reset_index()

    # --- 100% 금액(연간/월) ---
    cent = df[df["구분3"]=="100%"].copy()
    cent_ann = (cent[cent["구분4"]=="연간"]
                .groupby(["연도","부문"])["실적"].sum().rename("연간")).reset_index()
    cent_mon = (cent[cent["구분4"]=="월"]
                .groupby(["연도","부문"])["실적"].sum().rename("월")).reset_index()

    return mon_tbl, cent_ann, cent_mon


def build_bonus_table_28(df_src: pd.DataFrame, sel_y: int, sel_m: int):
    mon_tbl, cent_ann, cent_mon = _to_long_bonus_28(df_src)

    # ── 당월 ──
    mon_y = mon_tbl[(mon_tbl["연도"]==sel_y) & (mon_tbl["월"]==sel_m)]
    if mon_y.empty:
        mon_df = pd.DataFrame(index=["제조","임원","직원"], columns=["계획","실적"]).fillna(0.0)
    else:
        mon_df = (mon_y.groupby("부문")[["계획","실적"]].sum()).reindex(["제조","임원","직원"]).fillna(0.0)
    mon_df.loc["판관", ["계획","실적"]] = mon_df.reindex(["임원","직원"]).sum()
    mon_df.loc["총",    ["계획","실적"]] = mon_df.reindex(["제조","판관"]).sum()
    mon_df["차이"] = mon_df["실적"] - mon_df["계획"]

    # ── 누적(1~sel_m) ──
    ytd = mon_tbl[(mon_tbl["연도"]==sel_y) & (mon_tbl["월"].between(1, sel_m, inclusive="both"))]
    if ytd.empty:
        ytd_df = pd.DataFrame(index=["제조","임원","직원"], columns=["계획","실적"]).fillna(0.0)
    else:
        ytd_df = (ytd.groupby("부문")[["계획","실적"]].sum()).reindex(["제조","임원","직원"]).fillna(0.0)
    ytd_df.loc["판관", ["계획","실적"]] = ytd_df.reindex(["임원","직원"]).sum()
    ytd_df.loc["총",    ["계획","실적"]] = ytd_df.reindex(["제조","판관"]).sum()
    ytd_df["차이"] = ytd_df["실적"] - ytd_df["계획"]

    # ── 100% 금액(원본 그대로) ──
    ann = cent_ann[cent_ann["연도"]==sel_y].set_index("부문")["연간"] if not cent_ann.empty else pd.Series(dtype=float)
    mon100 = cent_mon[cent_mon["연도"]==sel_y].set_index("부문")["월"] if not cent_mon.empty else pd.Series(dtype=float)

    # 보강 및 파생(판관/총)
    def _fill_100(s: pd.Series) -> pd.Series:
        s = s.reindex(["제조","판관","임원","직원","총"]).fillna(0.0)
        if s.get("판관", 0)==0:
            s.loc["판관"] = s.reindex(["임원","직원"]).sum()
        if s.get("총", 0)==0:
            s.loc["총"] = s.reindex(["제조","판관"]).sum()
        return s

    ann   = _fill_100(ann)
    mon100= _fill_100(mon100)

    # ── 출력 DF ──
    order = ["제조","판관","임원","직원","총"]
    out = pd.DataFrame({"구분": order})

    for k in ["계획","실적","차이"]:
        out[f"당월|{k}"] = out["구분"].map(mon_df[k].to_dict()).fillna(0.0)

    ytd_lbl = f"{sel_m}월 누적"
    for k in ["계획","실적","차이"]:
        out[f"{ytd_lbl}|{k}"] = out["구분"].map(ytd_df[k].to_dict()).fillna(0.0)

    out["100% 금액|연간"] = out["구분"].map(ann.to_dict()).fillna(0.0)
    out["100% 금액|월"]   = out["구분"].map(mon100.to_dict()).fillna(0.0)

    # 숫자형 보정(구분 제외)
    for c in [c for c in out.columns if c != "구분"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    return out, dict(ytd_lbl=ytd_lbl)


##### 통상임금 #####

def _month_to_quarter(m: int) -> str:
    if 1 <= m <= 3:
        return "1분기"
    elif 4 <= m <= 6:
        return "2분기"
    elif 7 <= m <= 9:
        return "3분기"
    else:
        return "4분기"


def build_wage_table_29(df_src: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    f_29(통상임금) 원본 df → 분기/연간 집계.
    컬럼: [구분, 항목, 1분기, 2분기, 3분기, 4분기, 연간]
    """

    df = df_src.copy()

    df = df[(df["구분1"] == "통상임금") &
            (df["연도"].astype(int) == int(year))]

    if df.empty:
        return pd.DataFrame(
            columns=["구분", "항목", "1분기", "2분기", "3분기", "4분기", "연간"]
        )

    df["월"] = df["월"].astype(int)
    df["실적"] = (
        df["실적"].astype(str)
        .str.replace(",", "", regex=False)
        .replace("", "0")
        .astype(float)
    )

    df["분기"] = df["월"].map(_month_to_quarter)

    def make_block(df_block: pd.DataFrame, label: str) -> pd.DataFrame:
        g = df_block.groupby(["구분2", "분기"], as_index=False)["실적"].sum()

        piv = (
            g.pivot_table(index="구분2", columns="분기", values="실적", aggfunc="sum")
            .fillna(0.0)
        )

        # 4개 분기 다 만들어두기
        for q in ["1분기", "2분기", "3분기", "4분기"]:
            if q not in piv.columns:
                piv[q] = 0.0

        piv = piv[["1분기", "2분기", "3분기", "4분기"]]

        piv["연간"] = piv.sum(axis=1)

        row_order = [
            "1. 급여소급분_소급분",
            "1. 급여소급분_증가분",
            "2.연월차",
            "3.퇴직급여",
        ]
        ordered = [r for r in row_order if r in piv.index]
        others = [r for r in piv.index if r not in ordered]
        piv = piv.loc[ordered + others]

        total_row = piv.sum(axis=0).to_frame().T
        total_row.index = ["총계"]
        piv = pd.concat([piv, total_row])

        piv.insert(0, "항목", piv.index)
        piv.insert(0, "구분", label)

        return piv.reset_index(drop=True)

    df_seon = df[df["구분3"] == "선재"]
    df_at = df[df["구분3"] == "AT"]

    block_total = make_block(df, "총계")
    block_seon = make_block(df_seon, "선재") if not df_seon.empty else pd.DataFrame()
    block_at = make_block(df_at, "AT") if not df_at.empty else pd.DataFrame()

    disp_raw = pd.concat([block_total, block_seon, block_at], ignore_index=True)

    return disp_raw



##### 인원현황 #####


def build_table_60(df_src: pd.DataFrame, year: int, month: int):


    df = df_src.copy()

    # 숫자형 변환
    df["연도"] = df["연도"].astype(int)
    df["월"] = df["월"].astype(int)
    df["실적"] = (
        df["실적"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace("", "0")
        .astype(float)
    )

    prev_year = year - 1
    m = month
    m1 = month - 1
    m2 = month - 2

    # ---------- 집계용 헬퍼 ----------
    def avg_for_year(sub: pd.DataFrame, y: int, upto: int | None = None) -> float:
        s = sub[(sub["연도"] == y) & (sub["구분4"] == "실적")]
        if upto is not None:
            s = s[s["월"] <= upto]
        if s.empty:
            return 0.0
        bym = s.groupby("월")["실적"].sum()
        return float(bym.mean())

    def val_for(sub: pd.DataFrame, y: int, mo: int, kind: str) -> float:
        if mo < 1:
            return 0.0
        s = sub[(sub["연도"] == y) & (sub["월"] == mo) & (sub["구분4"] == kind)]
        if s.empty:
            return 0.0
        return float(s["실적"].sum())

    def compute_for(sub: pd.DataFrame) -> dict:
        prev_avg = avg_for_year(sub, prev_year)
        plan = val_for(sub, year, m, "계획")
        act2 = val_for(sub, year, m2, "실적")
        act1 = val_for(sub, year, m1, "실적")
        act = val_for(sub, year, m, "실적")
        this_avg = avg_for_year(sub, year, upto=m)
        mom = act - act1
        plan_diff = act - plan
        return {
            "prev_avg": prev_avg,
            "plan_m": plan,
            "act_m2": act2,
            "act_m1": act1,
            "act_m": act,
            "this_avg": this_avg,
            "mom_diff": mom,
            "plan_diff": plan_diff,
        }

    # ---------- 행 만들기 ----------
    rows: list[dict] = []

    def add_row(label1: str, label2: str, sub: pd.DataFrame):
        metrics = compute_for(sub)
        row = {"구분1": label1, "구분2": label2}
        row.update(metrics)
        rows.append(row)

    plants = ["서울", "포항", "충주", "충주2", "원주"]

    for plant in plants:
        plant_df = df[df["구분1"] == plant]

        if plant_df.empty:
            add_row(plant, "", plant_df)
            continue

        if plant == "서울":
            # 서울: 사무직만
            sub = plant_df[
                (plant_df["구분2"] == "자사")
                & (plant_df["구분3"] == "사무기술직")
            ]
            if sub.empty:
                sub = plant_df
            add_row("서울", "사무직", sub)
        else:
            # 포항/충주/충주2/원주
            off = plant_df[
                (plant_df["구분2"] == "자사")
                & (plant_df["구분3"] == "사무기술직")
            ]
            func = plant_df[
                (plant_df["구분2"] == "자사")
                & (plant_df["구분3"] == "기능직")
            ]
            own = plant_df[plant_df["구분2"] == "자사"]
            out = plant_df[plant_df["구분2"] == "외주"]

            add_row(plant, "사무직", off)
            add_row(plant, "기능직", func)
            add_row(plant, "자사", own)
            add_row(plant, "외주", out)
            add_row(plant, "합계", plant_df)

    # 자사계
    own_all = df[df["구분2"] == "자사"]
    off_all = own_all[own_all["구분3"] == "사무기술직"]
    func_all = own_all[own_all["구분3"] == "기능직"]

    add_row("자사계", "사무직", off_all)
    add_row("자사계", "기능직", func_all)
    add_row("자사계", "합계", own_all)

    # 외주계
    out_all = df[df["구분2"] == "외주"]
    add_row("외주계", "합계", out_all)

    # 전체
    add_row("전체", "합계", df)

    disp = pd.DataFrame(rows)

    col_order = [
        "구분1",
        "구분2",
        "prev_avg",
        "plan_m",
        "act_m2",
        "act_m1",
        "act_m",
        "this_avg",
        "mom_diff",
        "plan_diff",
    ]
    disp = disp[col_order]

    #구분1 중복제거
    disp["구분1"] = disp["구분1"].mask(disp["구분1"].duplicated(keep="last"), "")


    meta = {
        "prev_year": prev_year,
        "this_year": year,
        "m2": m2,
        "m1": m1,
        "m": m,
        "cols": col_order,
        "hdr1": [
            "구분",
            "",
            f"'{str(prev_year)[-2:]}년 연평균",
            f"{year}년 계획",
            f"{year}년 실적",
            f"{year}년 실적",
            f"{year}년 실적",
            f"'{str(year)[-2:]}년 연평균",
            "전월대비",
            "계획대비",
        ],
        "hdr2": [
            "",
            "",
            "",                               # prev_avg
            f"{m}월",                         # plan_m
            f"{m2}월" if m2 >= 1 else "",
            f"{m1}월" if m1 >= 1 else "",
            f"{m}월",
            "",                               # this_avg
            "",                               # mom_diff
            "",                               # plan_diff
        ],
    }

    return disp, meta


##### 해외법인실적 등급별 판매현황 #####

def build_grade_sales_table_68(df_src: pd.DataFrame, year: int, month: int):
    df = df_src.copy()

    # 숫자 처리
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"] = pd.to_numeric(df["월"], errors="coerce")
    df["실적"] = df["실적"].astype(str).str.replace(",", "", regex=False)
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce").fillna(0)

    # 실제 존재하는 구분1 리스트 (원본 순서 유지)
    base_plants = list(df["구분1"].unique())

    # 구분1 순서에 '중국' 끼워넣기: '태국' 바로 앞
    if "태국" in base_plants:
        idx = base_plants.index("태국")
        plants_for_loop = base_plants[:idx] + ["중국"] + base_plants[idx:]
    else:
        plants_for_loop = base_plants + ["중국"]

    # 구분2 기본 순서
    ORDER = ["POSCO", "천진向", "남통向", "세아특수강", "로컬", "기타"]

    rows = []

    # 기준연도 직전 3개 연도 (연간 누계용)
    prev_years = [year - 3, year - 2, year - 1]
    prev_year_labels = [f"{str(y)[-2:]}년" for y in prev_years]

    # ============================
    # 최근 3개월 (전전월, 전월, 선택월) - 연도 경계 처리
    # 예: year=2026, month=2 → (2025,12), (2026,1), (2026,2)
    # ============================
    month_pairs: list[tuple[int, int]] = []
    for k in (2, 1, 0):  # 전전월, 전월, 선택월
        y = year
        m = month - k
        while m <= 0:
            y -= 1
            m += 12
        month_pairs.append((y, m))

    # 컬럼명: "yy년m월" (예: '25년12월, '26년1월, '26년2월)
    month_labels = [f"{str(y)[-2:]}년{m}월" for (y, m) in month_pairs]

    # 전월비(톤) / 전월비(%) 컬럼 이름 (선택연도 기준 라벨은 기존 로직 그대로 유지)
    yy = str(year)[-2:]  # '2025' -> '25'
    diff_col = f"{yy}년전월비"
    diff_pct_col = f"{yy}년전월비%"

    # 전월/당월 (연,월) 쌍: month_pairs[1]=전월, month_pairs[2]=선택월
    (prev_y, prev_m), (cur_y, cur_m) = month_pairs[1], month_pairs[2]

    # 공장별 생성-> 중국 = 남통+천진
    for plant in plants_for_loop:

        # plant별로 사용할 pdf 결정
        if plant == "중국":
            # 남통 + 천진 합산
            pdf = df[df["구분1"].isin(["남통", "천진"])].copy()
            if pdf.empty:
                continue  # 남통/천진 없으면 중국 블록 생략
        else:
            pdf = df[df["구분1"] == plant].copy()

        if pdf.empty:
            continue

        # 연/월별 개별 등급 값
        def val(y, m, name):
            sub = pdf[pdf["연도"] == y]
            if m:  # 월별 → 누계 제외
                sub = sub[(sub["월"] == m) & (sub["구분3"] != "누계")]
            else:  # 연간(누계)
                sub = sub[sub["구분3"] == "누계"]

            if sub.empty:
                return 0
            return sub[sub["구분2"] == name]["실적"].sum()

        # 항목 순서 (해당 pdf에 실제로 있는 구분2만)
        cats = [c for c in ORDER if c in pdf["구분2"].unique()]

        # 합계(분모용) : 해당 공장 전체(모든 구분2) 합계
        def total_all(y, m):
            sub = pdf[pdf["연도"] == y]
            if m:
                sub = sub[(sub["월"] == m) & (sub["구분3"] != "누계")]
            else:
                sub = sub[sub["구분3"] == "누계"]
            if sub.empty:
                return 0
            return sub["실적"].sum()

        # 정품: B급 제외 전체
        def good(y, m):
            total = 0
            for cat in cats:
                if cat != "B급":
                    total += val(y, m, cat)
            return total

        # (1) POSCO % : 정품 중 POSCO 비율
        def posco_pct(y, m):
            g = good(y, m)
            p = val(y, m, "POSCO")
            return (p / g * 100) if g else 0

        # (2) B급 비율 : B급 / 합계 * 100  → 기존 '% ' 행의 정의
        def b_rate(y, m):
            b = val(y, m, "B급") if "B급" in pdf["구분2"].unique() else 0
            t = total_all(y, m)
            return (b / t * 100) if t else 0

        # --------------------------
        # (1) 하위 항목 (POSCO, 로컬 등)
        # --------------------------
        for cat in cats:
            row = {
                "구분1": plant,
                "구분2": cat,
            }

            # 직전 3개 연도(연간, 누계)
            for y, lab in zip(prev_years, prev_year_labels):
                row[lab] = val(y, None, cat)

            # 최근 3개월 (연도 포함)
            for (y_m, m_m), lab in zip(month_pairs, month_labels):
                row[lab] = val(y_m, m_m, cat)

            # 전월비 (톤 + %): (cur_y,cur_m) vs (prev_y,prev_m)
            cur_val = val(cur_y, cur_m, cat)
            prev_val = val(prev_y, prev_m, cat)
            diff = cur_val - prev_val
            row[diff_col] = diff
            row[diff_pct_col] = (diff / prev_val * 100) if prev_val != 0 else 0

            rows.append(row)

        # --------------------------
        # (1-1) POSCO % 행 (로컬과 정품 사이)
        # --------------------------
        row = {
            "구분1": plant,
            "구분2": "POSCO %",
        }

        # 직전 3개 연도 (연간 기준 POSCO/정품)
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = posco_pct(y, None)

        # 최근 3개월
        for (y_m, m_m), lab in zip(month_pairs, month_labels):
            row[lab] = posco_pct(y_m, m_m)

        # 전월비 (현재 POSCO% vs 전월 POSCO%)
        cur_posco = posco_pct(cur_y, cur_m)
        prev_posco = posco_pct(prev_y, prev_m)
        diff = cur_posco - prev_posco
        row[diff_col] = diff
        row[diff_pct_col] = (diff / prev_posco * 100) if prev_posco != 0 else 0

        rows.append(row)

        # --------------------------
        # (2) 정품 / B급 / % (B급/합계) 행
        # --------------------------
        for label in ["정품", "B급", "%"]:

            def get_value(y, m):
                if label == "정품":
                    return good(y, m)
                elif label == "B급":
                    return val(y, m, "B급")
                else:  # '%' 행: B급 / 합계
                    return b_rate(y, m)

            row = {
                "구분1": plant,
                "구분2": label,
            }

            # 직전 3개 연도
            for y, lab in zip(prev_years, prev_year_labels):
                row[lab] = get_value(y, None)

            # 최근 3개월
            for (y_m, m_m), lab in zip(month_pairs, month_labels):
                row[lab] = get_value(y_m, m_m)

            # 전월비 (톤 + % 또는 비율의 전월비)
            cur_val = get_value(cur_y, cur_m)
            prev_val = get_value(prev_y, prev_m)
            diff = cur_val - prev_val
            row[diff_col] = diff
            row[diff_pct_col] = (diff / prev_val * 100) if prev_val != 0 else 0

            rows.append(row)

        # --------------------------
        # (3) 공장 합계 행
        # --------------------------
        row = {
            "구분1": plant,
            "구분2": "",
        }

        # 직전 3개 연도 합계 (누계 기준)
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = pdf[
                (pdf["연도"] == y) & (pdf["구분3"] == "누계")
            ]["실적"].sum()

        # 최근 3개월 합계 (월별)
        for (y_m, m_m), lab in zip(month_pairs, month_labels):
            row[lab] = pdf[
                (pdf["연도"] == y_m)
                & (pdf["월"] == m_m)
                & (pdf["구분3"] != "누계")
            ]["실적"].sum()

        # 전월비 합계 (톤 + %)
        cur_sum = pdf[
            (pdf["연도"] == cur_y)
            & (pdf["월"] == cur_m)
            & (pdf["구분3"] != "누계")
        ]["실적"].sum()
        prev_sum = pdf[
            (pdf["연도"] == prev_y)
            & (pdf["월"] == prev_m)
            & (pdf["구분3"] != "누계")
        ]["실적"].sum()

        diff = cur_sum - prev_sum
        row[diff_col] = diff
        row[diff_pct_col] = (diff / prev_sum * 100) if prev_sum != 0 else 0

        rows.append(row)

    disp = pd.DataFrame(rows)

    for plant in disp["구분1"].unique():
        mask = disp["구분1"] == plant
        idxs = disp.index[mask]
        # 마지막행 을 제외하고 나머지 공장명 삭제
        if len(idxs) > 1:
            disp.loc[idxs[:-1], "구분1"] = ""

    return disp



##### 해외법인실적 CHQ 열처리 제품 판매현황 #####


def build_chq_f69(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    
    df = df_src[df_src["구분1"] == "CHQ 열처리 제품 판매현황"].copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"]   = pd.to_numeric(df["월"],   errors="coerce")

    df["실적"] = df["실적"].astype(str).str.replace(",", "", regex=False)
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce").fillna(0)

    # 공장(남통, 천진, 태국 등)은 구분2 기준
    base_plants = list(df["구분2"].dropna().unique())

    plants_for_loop: list[str] = []

    for p in ["남통", "천진"]:
        if p in base_plants:
            plants_for_loop.append(p)

    # 남통/천진 중 하나라도 있으면 중국 블록 추가
    if any(p in base_plants for p in ["남통", "천진"]):
        plants_for_loop.append("중국")

    if "태국" in base_plants:
        plants_for_loop.append("태국")

    rows = []


    # 직전 3개 연도: year-3, year-2, year-1
    prev_years = [year - 3, year - 2, year - 1]

    # 헤더용 라벨
    prev_year_labels = []
    for y in prev_years:
        if y == year - 1:
            prev_year_labels.append(f"'{str(y)[-2:]}년 누계")
        else:
            prev_year_labels.append(f"'{str(y)[-2:]}년")

    # 최근 3개월 / 연도 넘어감 정리

    month_pairs: list[tuple[int, int]] = []
    for k in (2, 1, 0):  # 전전월, 전월, 선택월
        y0 = year
        m0 = month - k
        while m0 <= 0:
            y0 -= 1
            m0 += 12
        month_pairs.append((y0, m0))

    # 월 컬럼 라벨: "yy년m월" (예: '25년12월, '26년1월, '26년2월)
    month_labels = [f"{str(y0)[-2:]}년{m0}월" for (y0, m0) in month_pairs]

    # (3) 전월 / 당월 (연,월) 쌍
    (prev_y, prev_m), (cur_y, cur_m) = month_pairs[1], month_pairs[2]

    # (4) 전월비(톤) / 전월비(%) 컬럼 이름 (라벨은 기준연도 기준 유지)
    yy = str(year)[-2:]
    diff_col     = f"{yy}년전월비"
    diff_pct_col = f"{yy}년전월비%"

    # ======================
    # 4. 공장(구분1)별 블록 생성
    # ======================
    for plant in plants_for_loop:

        # 4-1) 현재 plant에 해당하는 데이터 선택
        if plant == "중국":
            # 중국 = 남통 + 천진
            pdf = df[df["구분2"].isin(["남통", "천진"])].copy()
        else:
            pdf = df[df["구분2"] == plant].copy()

        if pdf.empty:
            continue

        # --------------------------
        # 4-2) 값 꺼내는 함수들
        # --------------------------
        # kind : "비열처리" / "열처리"
        def val(y, m, kind):
            sub = pdf[pdf["연도"] == y]
            if m is None:  # 연간(누계) → 월이 NaN 또는 결측
                sub = sub[sub["월"].isna()]
            else:          # 월별
                sub = sub[sub["월"] == m]

            sub = sub[sub["구분3"] == kind]
            return sub["실적"].sum()

        # 합계 = 비열처리 + 열처리
        def sum_bt(y, m):
            return val(y, m, "비열처리") + val(y, m, "열처리")

        # 열처리 비율(%) = 열처리 / (비열처리+열처리) * 100
        def heat_ratio(y, m):
            heat = val(y, m, "열처리")
            non  = val(y, m, "비열처리")
            tot  = heat + non
            return (heat / tot * 100) if tot else 0

        # ===========================
        # 4-3) 비열처리 / 열처리 행
        # ===========================
        for kind in ["비열처리", "열처리"]:
            row = {
                "구분1": plant,
                "구분2": kind,
            }

            # 직전 3개 연도 (연간 누계)
            for y, lab in zip(prev_years, prev_year_labels):
                row[lab] = val(y, None, kind)

            # 최근 3개월 (연도 포함 월별)
            for (y_m, m_m), lab in zip(month_pairs, month_labels):
                row[lab] = val(y_m, m_m, kind)

            # 전월비 (톤 + %): (cur_y,cur_m) vs (prev_y,prev_m)
            cur_val  = val(cur_y, cur_m, kind)
            prev_val = val(prev_y, prev_m, kind)
            diff = cur_val - prev_val
            row[diff_col]     = diff
            row[diff_pct_col] = (diff / prev_val * 100) if prev_val != 0 else 0

            rows.append(row)

        # ===========================
        # 4-4) % 행 (열처리 비율)
        # ===========================
        row = {
            "구분1": plant,
            "구분2": "%",  # 열처리 비율
        }

        # 연간(누계) 기준 열처리 비율
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = heat_ratio(y, None)

        # 최근 3개월 열처리 비율
        for (y_m, m_m), lab in zip(month_pairs, month_labels):
            row[lab] = heat_ratio(y_m, m_m)

        # 전월비 (비율의 변화량, pp 기준)
        cur_ratio  = heat_ratio(cur_y, cur_m)
        prev_ratio = heat_ratio(prev_y, prev_m)
        diff = cur_ratio - prev_ratio          # pp(퍼센트포인트)
        row[diff_col]     = diff
        row[diff_pct_col] = (diff / prev_ratio * 100) if prev_ratio != 0 else 0

        rows.append(row)

        # ===========================
        # 4-5) 합계 행 (비열처리+열처리)
        # ===========================
        row = {
            "구분1": plant,
            "구분2": "",
        }

        # 직전 3개 연도 (누계) → 비열처리+열처리
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = sum_bt(y, None)

        # 최근 3개월 (월별) → 비열처리+열처리
        for (y_m, m_m), lab in zip(month_pairs, month_labels):
            row[lab] = sum_bt(y_m, m_m)

        # 전월비 (톤 + %)
        cur_sum  = sum_bt(cur_y, cur_m)
        prev_sum = sum_bt(prev_y, prev_m)
        diff = cur_sum - prev_sum
        row[diff_col]     = diff
        row[diff_pct_col] = (diff / prev_sum * 100) if prev_sum != 0 else 0

        rows.append(row)

    disp = pd.DataFrame(rows)

    for plant in disp["구분1"].unique():
        mask = disp["구분1"] == plant
        idxs = disp.index[mask]
        # 마지막행 을 제외하고 나머지 공장명 삭제
        if len(idxs) > 1:
            disp.loc[idxs[:-1], "구분1"] = ""

    return disp





##### 해외법인실적 비가공품 판매현황 #####

def build_f70(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    # 0) 비가공품 판매현황만 사용 (공백/오타 대비)
    df = df_src.copy()
    df["구분1"] = df["구분1"].astype(str).str.strip()
    df = df[df["구분1"].str.contains("비가공품 판매현황", na=False)].copy()

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"]   = pd.to_numeric(df["월"],   errors="coerce")

    df["실적"] = df["실적"].astype(str).str.replace(",", "", regex=False)
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce").fillna(0)

    # 구분2/구분3 공백 제거
    df["구분2"] = df["구분2"].astype(str).str.strip()
    df["구분3"] = df["구분3"].astype(str).str.strip()

    # 공장(남통, 천진, 태국 등)은 구분2 기준
    base_plants = list(df["구분2"].dropna().unique())

    plants_for_loop: list[str] = []

    for p in ["남통", "천진"]:
        if p in base_plants:
            plants_for_loop.append(p)

    # 남통/천진 중 하나라도 있으면 중국 블록 추가
    if any(p in base_plants for p in ["남통", "천진"]):
        plants_for_loop.append("중국")

    if "태국" in base_plants:
        plants_for_loop.append("태국")

    rows: list[dict] = []

    # ======================
    # 3. 기준 연/월 정보
    # ======================
    # 직전 3개 연도
    prev_years = [year - 3, year - 2, year - 1]

    # 헤더용 라벨
    prev_year_labels = []
    for y in prev_years:
        if y == year - 1:
            prev_year_labels.append(f"'{str(y)[-2:]}년 누계")
        else:
            prev_year_labels.append(f"'{str(y)[-2:]}년")

    # 최근 3개월 
    month_pairs: list[tuple[int, int]] = []
    for k in (2, 1, 0):  # 전전월, 전월, 선택월
        y0 = year
        m0 = month - k
        while m0 <= 0:
            y0 -= 1
            m0 += 12
        month_pairs.append((y0, m0))

    # 월 컬럼 라벨: "yy년m월" (예: '25년12월, '26년1월, '26년2월)
    month_labels = [f"{str(y0)[-2:]}년{m0}월" for (y0, m0) in month_pairs]

    # (3) 전월 / 당월 (연,월) 쌍
    (prev_y, prev_m), (cur_y, cur_m) = month_pairs[1], month_pairs[2]

    # (4) 전월비(톤) / 전월비(%) 컬럼 이름 (라벨은 기준연도 기준 유지)
    yy = str(year)[-2:]  # 2025 -> "25"
    diff_col     = f"{yy}년전월비"
    diff_pct_col = f"{yy}년전월비%"

    # ======================
    # 4. 공장(구분1)별 블록 생성
    # ======================
    for plant in plants_for_loop:

        # 4-1) 현재 plant에 해당하는 데이터 선택
        if plant == "중국":
            pdf = df[df["구분2"].isin(["남통", "천진"])].copy()
        else:
            pdf = df[df["구분2"] == plant].copy()

        if pdf.empty:
            continue

        # --------------------------
        # 4-2) 값 꺼내는 함수들
        # --------------------------
        def val(y, m, kind: str):
            """kind: '가공', '비가공', '연강' 등"""
            sub = pdf[pdf["연도"] == y]

            if m is None:  # 연간(누계) → 월이 NaN 또는 결측
                sub = sub[sub["월"].isna()]
            else:          # 월별
                sub = sub[sub["월"] == m]

            # kind 정확히 일치
            sub = sub[sub["구분3"] == kind]
            return sub["실적"].sum()

        # 합계 = 가공 + 비가공
        def sum_bt(y, m):
            return val(y, m, "가공") + val(y, m, "비가공")

        # 가공 비율(%) = (여기서는 기존 코드 유지: 비가공 / (가공+비가공) * 100)
        def proc_ratio(y, m):
            proc = val(y, m, "비가공")
            raw  = val(y, m, "가공")
            tot  = proc + raw
            return (proc / tot * 100) if tot else 0

        # 연강: 구분3에 '연강'이 포함된 모든 것 합산 (공백/붙임말 대응)
        def val_yeon(y, m):
            sub = pdf[pdf["연도"] == y]
            if m is None:
                sub = sub[sub["월"].isna()]
            else:
                sub = sub[sub["월"] == m]

            # '연강'이 포함된 구분3
            yeon = sub[sub["구분3"].str.contains("연강", na=False)]
            return yeon["실적"].sum()

        # 태국에 연강이 실제로 있는지 미리 체크
        has_yeon = (plant == "태국") and any(
            pdf["구분3"].str.contains("연강", na=False)
        )

        # ===========================
        # 4-3) 가공 / 비가공 행
        # ===========================
        for kind in ["가공", "비가공"]:
            row: dict = {
                "구분1": plant,
                "구분2": kind,
            }

            # 직전 3개 연도 (연간 누계)
            for y, lab in zip(prev_years, prev_year_labels):
                row[lab] = val(y, None, kind)

            # 최근 3개월 (연도 포함 월별)
            for (y_m, m_m), lab in zip(month_pairs, month_labels):
                row[lab] = val(y_m, m_m, kind)

            # 전월비 (톤 + %): (cur_y,cur_m) vs (prev_y,prev_m)
            cur_val  = val(cur_y, cur_m, kind)
            prev_val = val(prev_y, prev_m, kind)
            diff = cur_val - prev_val
            row[diff_col]     = diff
            row[diff_pct_col] = (diff / prev_val * 100) if prev_val != 0 else 0

            rows.append(row)

        # ===========================
        # 4-4) % 행 (가공 비율)
        # ===========================
        row = {
            "구분1": plant,
            "구분2": "%",   # 비율 행
        }

        # 직전 3개 연도 (누계 기준 비율)
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = proc_ratio(y, None)

        # 최근 3개월 비율
        for (y_m, m_m), lab in zip(month_pairs, month_labels):
            row[lab] = proc_ratio(y_m, m_m)

        # 전월비 (비율 변화, pp + %)
        cur_ratio  = proc_ratio(cur_y, cur_m)
        prev_ratio = proc_ratio(prev_y, prev_m)
        diff = cur_ratio - prev_ratio
        row[diff_col]     = diff
        row[diff_pct_col] = (diff / prev_ratio * 100) if prev_ratio != 0 else 0

        rows.append(row)

        # ===========================
        # 4-4-1) 연강 행 (태국만)
        # ===========================
        if has_yeon:
            row = {
                "구분1": plant,
                "구분2": "연강",
            }

            # 직전 3개 연도 (누계)
            for y, lab in zip(prev_years, prev_year_labels):
                row[lab] = val_yeon(y, None)

            # 최근 3개월
            for (y_m, m_m), lab in zip(month_pairs, month_labels):
                row[lab] = val_yeon(y_m, m_m)

            # 전월비
            cur_val  = val_yeon(cur_y, cur_m)
            prev_val = val_yeon(prev_y, prev_m)
            diff = cur_val - prev_val
            row[diff_col]     = diff
            row[diff_pct_col] = (diff / prev_val * 100) if prev_val != 0 else 0

            rows.append(row)

        # ===========================
        # 4-5) 합계 행 (가공+비가공)
        # ===========================
        row = {
            "구분1": plant,
            "구분2": "",
        }

        # 직전 3개 연도 (누계)
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = sum_bt(y, None)

        # 최근 3개월 (월별)
        for (y_m, m_m), lab in zip(month_pairs, month_labels):
            row[lab] = sum_bt(y_m, m_m)

        # 전월비 (톤 + %)
        cur_sum  = sum_bt(cur_y, cur_m)
        prev_sum = sum_bt(prev_y, prev_m)
        diff = cur_sum - prev_sum
        row[diff_col]     = diff
        row[diff_pct_col] = (diff / prev_sum * 100) if prev_sum != 0 else 0

        rows.append(row)

    disp = pd.DataFrame(rows)

    for plant in disp["구분1"].unique():
        mask = disp["구분1"] == plant
        idxs = disp.index[mask]
        # 마지막행 을 제외하고 나머지 공장명 삭제
        if len(idxs) > 1:
            disp.loc[idxs[:-1], "구분1"] = ""

    return disp



##### 해외법인실적 제품/임가공 판매현황 #####

def build_f71(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:

    

    df = df_src[df_src["구분1"] == "제품/임가공 판매현황"].copy()

    # ======================
    # 1. 기본 전처리
    # ======================
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"]   = pd.to_numeric(df["월"],   errors="coerce")

    df["실적"] = df["실적"].astype(str).str.replace(",", "", regex=False)
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce").fillna(0)

    # 공장(남통, 천진, 태국 등)은 구분2 기준
    base_plants = list(df["구분2"].dropna().unique())

    # ======================
    # 2. 구분1(공장) 순서 구성
    #    남통, 천진, 중국(=남통+천진), 태국
    # ======================
    plants_for_loop: list[str] = []

    for p in ["남통", "천진"]:
        if p in base_plants:
            plants_for_loop.append(p)

    # 남통/천진 중 하나라도 있으면 중국 블록 추가
    if any(p in base_plants for p in ["남통", "천진"]):
        plants_for_loop.append("중국")

    if "태국" in base_plants:
        plants_for_loop.append("태국")

    rows = []

    # ======================
    # 3. 기준 연/월 정보
    # ======================
    # 직전 3개 연도: year-3, year-2, year-1
    prev_years = [year - 3, year - 2, year - 1]

    # 헤더용 라벨: 예) '22년, '23년, '24년 누계
    prev_year_labels = []
    for y in prev_years:
        if y == year - 1:
            prev_year_labels.append(f"'{str(y)[-2:]}년 누계")
        else:
            prev_year_labels.append(f"'{str(y)[-2:]}년")

    # 기준연도 최근 3개월 (선택월 포함, 1월/2월 처리)
    yy = str(year)[-2:]  # 2025 -> "25"
    months = [m for m in [month - 2, month - 1, month] if m >= 1]
    month_labels = [f"{yy}년{m}월" for m in months]

    # 전월비(톤) / 전월비(%) 컬럼 이름
    diff_col     = f"{yy}년전월비"
    diff_pct_col = f"{yy}년전월비%"

    # ======================
    # 4. 공장(구분1)별 블록 생성
    # ======================
    for plant in plants_for_loop:

        # 4-1) 현재 plant에 해당하는 데이터 선택
        if plant == "중국":
            # 중국 = 남통 + 천진
            pdf = df[df["구분2"].isin(["남통", "천진"])].copy()
        else:
            pdf = df[df["구분2"] == plant].copy()

        if pdf.empty:
            continue

        # --------------------------
        # 4-2) 값 꺼내는 함수들
        # --------------------------
        # kind : "비열처리" / "열처리"
        def val(y, m, kind):
            sub = pdf[pdf["연도"] == y]
            if m is None:  # 연간(누계) → 월이 NaN 또는 결측
                sub = sub[sub["월"].isna()]
            else:          # 월별
                sub = sub[sub["월"] == m]

            sub = sub[sub["구분3"] == kind]
            return sub["실적"].sum()

        # 합계 = 비열처리 + 열처리
        def sum_bt(y, m):
            return val(y, m, "제품") + val(y, m, "임가공")

        # 열처리 비율(%) = 열처리 / (비열처리+열처리) * 100
        def heat_ratio(y, m):
            heat = val(y, m, "임가공")
            non  = val(y, m, "제품")
            tot  = heat + non
            return (heat / tot * 100) if tot else 0

        # ===========================
        # 4-3) 비열처리 / 열처리 행
        # ===========================
        for kind in ["제품", "임가공"]:
            row = {
                "구분1": plant,
                "구분2": kind,
            }

            # 직전 3개 연도 (연간 누계)
            for y, lab in zip(prev_years, prev_year_labels):
                row[lab] = val(y, None, kind)

            # 기준연도 최근 3개월 (월별)
            for m_, lab in zip(months, month_labels):
                row[lab] = val(year, m_, kind)

            # 전월비 (톤 + %)
            if month >= 2 and (month - 1) in months:
                cur  = val(year, month, kind)
                prev = val(year, month - 1, kind)
                diff = cur - prev
                row[diff_col]     = diff
                row[diff_pct_col] = (diff / prev * 100) if prev != 0 else 0
            else:
                row[diff_col]     = 0
                row[diff_pct_col] = 0

            rows.append(row)

        # ===========================
        # 4-4) % 행 (열처리 비율)
        # ===========================
        row = {
            "구분1": plant,
            "구분2": "%",
        }

        # 연간(누계) 기준 열처리 비율
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = heat_ratio(y, None)

        # 월별 열처리 비율
        for m_, lab in zip(months, month_labels):
            row[lab] = heat_ratio(year, m_)

        # 전월비 (비율의 변화량)
        if month >= 2 and (month - 1) in months:
            cur  = heat_ratio(year, month)
            prev = heat_ratio(year, month - 1)
            diff = cur - prev              # pp(퍼센트포인트) 관점
            row[diff_col]     = diff
            row[diff_pct_col] = (diff / prev * 100) if prev != 0 else 0
        else:
            row[diff_col]     = 0
            row[diff_pct_col] = 0

        rows.append(row)

        # ===========================
        # 4-5) 합계 행 (비열처리+열처리)
        # ===========================
        row = {
            "구분1": plant,
            "구분2": "",
        }

        # 직전 3개 연도 (누계) → 비열처리+열처리
        for y, lab in zip(prev_years, prev_year_labels):
            row[lab] = sum_bt(y, None)

        # 기준연도 최근 3개월 (월별) → 비열처리+열처리
        for m_, lab in zip(months, month_labels):
            row[lab] = sum_bt(year, m_)

        # 전월비 (톤 + %)
        if month >= 2 and (month - 1) in months:
            cur_sum  = sum_bt(year, month)
            prev_sum = sum_bt(year, month - 1)
            diff = cur_sum - prev_sum
            row[diff_col]     = diff
            row[diff_pct_col] = (diff / prev_sum * 100) if prev_sum != 0 else 0
        else:
            row[diff_col]     = 0
            row[diff_pct_col] = 0

        rows.append(row)

    disp = pd.DataFrame(rows)

    for plant in disp["구분1"].unique():
        mask = disp["구분1"] == plant
        idxs = disp.index[mask]
        # 마지막행 을 제외하고 나머지 공장명 삭제
        if len(idxs) > 1:
            disp.loc[idxs[:-1], "구분1"] = ""

    return disp


##### 해외법인실적 재무상태표 #####

def create_bs_from_company(
    year: int,
    month: int,
    data: pd.DataFrame,
    item_order: list[str],
    company_name: str,
) -> pd.DataFrame:


    # 1) 기본 컬럼 체크
    required_cols = ['구분1', '구분2']
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"'{col}' 컬럼이 없습니다. 원본 스키마를 확인하세요.")

    # 2) 회사 필터링
    df_src = data.copy()
    df_src['구분1'] = df_src['구분1'].astype(str).str.strip()
    df_src = df_src[df_src['구분1'] == str(company_name).strip()].copy()




    #    - 연산용 항목 컬럼: 구분2 → 구분3
    #    - 회사 컬럼: 구분1 → 회사
    df_src['구분3'] = df_src['구분2']
    df_src['회사']   = df_src['구분1']


    df = _normalize_bs_simple(df_src)

    req_y = int(year)
    req_m = int(month)

    # 연도 포맷(두 자리)
    yy_m3  = f"{(req_y - 3) % 100:02d}"   
    yy_m2  = f"{(req_y - 2) % 100:02d}"   
    yy_m1  = f"{(req_y - 1) % 100:02d}"   
    yy_curr = f"{req_y % 100:02d}"        

    # 선택월 / 전월 계산
    used_m = req_m
    if used_m > 1:
        prev_y = req_y
        prev_m = used_m - 1
    else:
        prev_y = req_y - 1
        prev_m = 12

    # 4) 항목별 합계 헬퍼 (구분3 == item)
    def _sum_item(item: str, y: int | None, m: int | None) -> float:
        if y is None or m is None:
            return 0.0
        mask = (
            (df['구분3'].astype(str).str.strip() == item)
            & (df['연도'] == y)
            & (df['월'] == m)
        )
        return float(df.loc[mask, '실적'].sum())

    # 5) 행 인덱스 (item_order 그대로)
    index_labels = pd.Index(item_order, name='구분')

    # 6) 내부 컬럼 라벨 (계산용)
    col_yend_m3 = f"'{yy_m3}년말"    # 선택 전전전년 말
    col_yend_m2 = f"'{yy_m2}년말"    # 선택 전전년 말
    col_yend_m1 = f"'{yy_m1}년말"    # 전년말
    col_prev    = f"'{yy_curr} 전월" # 선택연도 전월
    col_curr    = f"'{yy_curr} 선택월"  # 선택연도 선택월

    # 7) 행 구성
    rows = []
    for item in item_order:
        v_m3 = _sum_item(item, req_y - 3, 12)   # 선택연도 -3년 12월
        v_m2 = _sum_item(item, req_y - 2, 12)   # 선택연도 -2년 12월
        v_m1 = _sum_item(item, req_y - 1, 12)   # 전년 12월
        v_prev = _sum_item(item, prev_y, prev_m)  # 전월
        v_curr = _sum_item(item, req_y, used_m)   # 선택월

        rows.append({
            col_yend_m3: v_m3,
            col_yend_m2: v_m2,
            col_yend_m1: v_m1,
            col_prev:    v_prev,
            col_curr:    v_curr,
            "전월비":      v_curr - v_prev,
        })

    out = pd.DataFrame(rows, index=index_labels).fillna(0.0)

    # 선택  연월 기준
    out = out.rename(columns={
        col_yend_m3: f"'{yy_m3}년말",   # 선택 전전전년 말
        col_yend_m2: f"'{yy_m2}년말",   # 선택 전전년 말
        col_yend_m1: f"'{yy_m1}년말",   # 전년말
        col_prev:    f"'{yy_curr} 전월", # 선택연도 전월
        col_curr:    "당월",             # 선택연도 선택월
        "전월비":      "전월비",
    })

    # 원하는 순서로 재정렬
    out = out[
        [
            f"'{yy_m3}년말",
            f"'{yy_m2}년말",
            f"'{yy_m1}년말",
            f"'{yy_curr} 전월",
            "당월",
            "전월비",
        ]
    ]

    # 9) 메타 정보
    out.attrs['used_month'] = used_m
    out.attrs['prev_month'] = prev_m
    out.attrs['prev_year']  = prev_y
    out.attrs['company']    = company_name
    out.attrs['base_year']  = req_y

    return out





##### 해외법인실적 손익요약 ######



def create_abroad_profit_month_block_table(df_raw: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    df = df_raw.copy()

    # ===== 공통 전처리 =====
    df["실적"] = (
        df["실적"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["값"] = pd.to_numeric(df["실적"], errors="coerce")
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce").astype("Int64")

    def _parse_month(m):
        """
        '월' 컬럼 파싱:
        - '3월누적' -> (3, True)
        - '3월'     -> (3, False)
        - '3'       -> (3, False)
        - nan / 'nan' / 빈값 / 이상한 값 -> (np.nan, False)
        """
        # 1) NaN 자체인 경우
        if pd.isna(m):
            return np.nan, False

        s = str(m).strip()

        # 2) 'nan', 'NaN', 빈 문자열 처리
        if s == "" or s.lower() == "nan":
            return np.nan, False

        # 3) "월누적" 포함 케이스
        if "월누적" in s:
            num_part = s.replace("월누적", "")
            num_part = re.sub(r"[^0-9]", "", num_part)  # 혹시 공백/기타 문자 섞여 있으면 숫자만 추출
            if num_part == "":
                return np.nan, True
            try:
                return int(num_part), True
            except ValueError:
                return np.nan, True

        # 4) 일반 "월" 표기 (예: '11월', ' 11 월 ')
        if "월" in s:
            num_part = s.replace("월", "")
            num_part = re.sub(r"[^0-9]", "", num_part)
            if num_part == "":
                return np.nan, False
            try:
                return int(num_part), False
            except ValueError:
                return np.nan, False

        # 5) 그냥 숫자라고 가정 ('11' 같은 케이스)
        num_part = re.sub(r"[^0-9]", "", s)
        if num_part == "":
            return np.nan, False
        try:
            return int(num_part), False
        except ValueError:
            return np.nan, False


    tmp = df["월"].apply(_parse_month)
    df["월_num"] = tmp.apply(lambda x: x[0])
    df["is_acc"] = tmp.apply(lambda x: x[1])

    df = df[df["연도"] == year]

    prev_month = month - 1 if month > 1 else 12
    idx_cols = ["구분1", "구분2"]
    yy = str(int(year))[-2:]

    # 최종 지표 컬럼 이름(먼저 만들어두고 템플릿에도 같이 사용)
    metric_cols = [
        f"{prev_month}월실적",
        f"{month}월계획",
        f"{month}월실적",
        f"{month}월계획비",
        f"{month}월전월비",
        f"'{yy}년누적계획",
        f"'{yy}년누적실적",
        f"'{yy}년누적계획비",
    ]


    def _build_empty_table():
        # 판매량: 고정 순서
        sales_qty_order = ["남통", "천진", "중국", "태국", "(제품)", "(연강)"]
        # 나머지 대분류 기본 순서
        other_order = ["남통", "천진", "중국", "태국"]

        sections = ["매출액", "판매량", "영업이익", "영업이익률(%)"]
        rows = []
        for sec in sections:
            if sec == "판매량":
                order = sales_qty_order
            else:
                order = other_order
            for g in order:
                row = {"대분류": sec, "구분": g}
                row.update({c: 0 for c in metric_cols})
                rows.append(row)
        return pd.DataFrame(rows, columns=["대분류", "구분"] + metric_cols)

    # ===== 1) 전월/당월/누적 집계 =====
    prev = df[
        (df["월_num"] == prev_month) &
        (~df["is_acc"]) &
        (df["구분3"] == "실적")
    ]
    s_prev = (
        prev.groupby(idx_cols)["값"]
        .sum()
        .rename(f"{prev_month}월실적")
    )

    curr = df[(df["월_num"] == month) & (~df["is_acc"])]

    curr_plan = (
        curr[curr["구분3"] == "계획"]
        .groupby(idx_cols)["값"]
        .sum()
        .rename(f"{month}월계획")
    )
    curr_act = (
        curr[curr["구분3"] == "실적"]
        .groupby(idx_cols)["값"]
        .sum()
        .rename(f"{month}월실적")
    )

    acc = df[(df["월_num"] == month) & (df["is_acc"])]

    acc_plan = (
        acc[acc["구분3"] == "계획"]
        .groupby(idx_cols)["값"]
        .sum()
        .rename(f"'{yy}년누적계획")
    )
    acc_act = (
        acc[acc["구분3"] == "실적"]
        .groupby(idx_cols)["값"]
        .sum()
        .rename(f"'{yy}년누적실적")
    )

    base = pd.concat(
        [s_prev, curr_plan, curr_act, acc_plan, acc_act],
        axis=1
    ).reset_index()


    if base.empty:
        return _build_empty_table()

    # 부족한 컬럼 0으로 채우기
    for c in [f"{prev_month}월실적",
              f"{month}월계획",
              f"{month}월실적",
              f"'{yy}년누적계획",
              f"'{yy}년누적실적"]:
        if c not in base.columns:
            base[c] = 0
    base[[f"{prev_month}월실적",
          f"{month}월계획",
          f"{month}월실적",
          f"'{yy}년누적계획",
          f"'{yy}년누적실적"]] = base[
        [f"{prev_month}월실적",
         f"{month}월계획",
         f"{month}월실적",
         f"'{yy}년누적계획",
         f"'{yy}년누적실적"]
    ].fillna(0)

    # 차이 컬럼
    base[f"{month}월계획비"] = base[f"{month}월실적"] - base[f"{month}월계획"]
    base[f"{month}월전월비"] = base[f"{month}월실적"] - base[f"{prev_month}월실적"]
    base[f"'{yy}년누적계획비"] = (
        base[f"'{yy}년누적실적"] - base[f"'{yy}년누적계획"]
    )

    base = base.rename(columns={"구분1": "대분류", "구분2": "구분"})
    base = base[["대분류", "구분"] + metric_cols]

    # ===== 2) 중국 집계행 추가 =====
    china_src = base[
        base["구분"].isin(["남통", "천진"]) &
        base["대분류"].isin(["매출액", "판매량", "영업이익"])
    ]
    if not china_src.empty:
        china_agg = (
            china_src
            .groupby("대분류")[metric_cols]
            .sum()
            .reset_index()
        )
        china_agg["구분"] = "중국"
        china_agg = china_agg[["대분류", "구분"] + metric_cols]
        base = pd.concat([base, china_agg], ignore_index=True)

    # ===== 3) 영업이익률(%) 추가 =====
    sales = base[base["대분류"] == "매출액"].set_index("구분")[metric_cols]
    op    = base[base["대분류"] == "영업이익"].set_index("구분")[metric_cols]

    common_idx = sales.index.intersection(op.index)
    if len(common_idx) > 0:
        ratio = op.loc[common_idx, metric_cols].div(
            sales.loc[common_idx, metric_cols]
        ) * 100
        ratio = ratio.reset_index()
        ratio.insert(0, "대분류", "영업이익률(%)")
        ratio = ratio[["대분류", "구분"] + metric_cols]
        base = pd.concat([base, ratio], ignore_index=True)

    # ===== 4) 대분류/구분 정렬 + 판매량 고정 순서 =====
    sections = ["매출액", "판매량", "영업이익", "영업이익률(%)"]
    result_parts = []

    sales_qty_order = ["남통", "천진", "중국", "태국", "(제품)", "(연강)"]
    default_order = ["남통", "천진","중국", "태국"]

    for sec in sections:
        part = base[base["대분류"] == sec].copy()
        if part.empty:

            if sec == "판매량":
                tpl = pd.DataFrame({
                    "대분류": ["판매량"] * len(sales_qty_order),
                    "구분": sales_qty_order
                })
                for c in metric_cols:
                    tpl[c] = 0
                result_parts.append(tpl)
            continue

        if sec == "판매량":
            tpl = pd.DataFrame({
                "대분류": ["판매량"] * len(sales_qty_order),
                "구분": sales_qty_order
            })
            part = tpl.merge(part, on=["대분류", "구분"], how="left")
            for c in metric_cols:
                part[c] = part[c].fillna(0)
            part["구분"] = pd.Categorical(part["구분"], sales_qty_order, ordered=True)
            part = part.sort_values("구분")
        else:
            order = default_order
            exist = [g for g in order if g in part["구분"].unique()]
            others = sorted([g for g in part["구분"].unique() if g not in exist])
            cat = exist + others
            part["구분"] = pd.Categorical(part["구분"], cat, ordered=True)
            part = part.sort_values("구분")

        result_parts.append(part)

    if not result_parts:

        return _build_empty_table()

    final = pd.concat(result_parts, ignore_index=True)
    final = final[["대분류", "구분"] + metric_cols]

    return final


##### 해외법인실적 재고자산 현황 #####
from typing import List


def create_inv_table_from_company(
    year: int,
    month: int,
    data: pd.DataFrame,
    company_name: str,
) -> pd.DataFrame:


    # 0) 기본 컬럼 체크
    required_cols = ['구분1', '구분2', '구분3', '연도', '월', '실적']
    for c in required_cols:
        if c not in data.columns:
            raise ValueError(f"'{c}' 컬럼이 없습니다. 원본 스키마를 확인하세요.")

    # 1) 회사 기준 필터링
    df_src = data.copy()
    df_src['구분1'] = df_src['구분1'].astype(str).str.strip()
    df_src = df_src[df_src['구분1'] == str(company_name).strip()].copy()
    if df_src.empty:
        raise ValueError(f"회사 '{company_name}' 데이터가 없습니다.")

    # 2) 타입 정리: 연도/월/실적 숫자화
    df_src['연도'] = (
        df_src['연도']
        .astype(str)
        .str.replace(' ', '', regex=False)
        .astype(int)
    )
    df_src['월'] = (
        df_src['월']
        .astype(str)
        .str.replace(' ', '', regex=False)
        .astype(int)
    )

    df_src['실적'] = (
        df_src['실적']
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.replace(' ', '', regex=False)
    )
    df_src.loc[df_src['실적'] == '', '실적'] = '0'
    df_src['실적'] = df_src['실적'].astype(float)

    req_y = int(year)
    req_m = int(month)

    # 3) 연말 4개 연도: 선택연도-4 ~ 선택연도-1
    year_list: List[int] = [req_y - 4, req_y - 3, req_y - 2, req_y - 1]
    year_cols: List[str] = [
        f"'{str(y % 100).zfill(2)}년말" for y in year_list
    ]

    # 4) 최근 3개월 (연도 넘어가는 경우도 포함)
    #    예: (2026, 1) → (2025,11), (2025,12), (2026,1)
    month_pairs: List[tuple[int, int]] = []
    for k in (2, 1, 0):  # 전전월, 전월, 당월
        y = req_y
        m = req_m - k
        while m <= 0:
            y -= 1
            m += 12
        month_pairs.append((y, m))

    month_years = [y for (y, m) in month_pairs]
    month_list = [m for (y, m) in month_pairs]  # [전전월, 전월, 당월]
    month_cols: List[str] = [f"{m}월" for m in month_list]

    # 5) 합계 헬퍼
    def _sum(row2: str, row3: str, y: int, m: int) -> float:
        mask = (
            (df_src['구분2'].astype(str).str.strip() == row2)
            & (df_src['구분3'].astype(str).str.strip() == row3)
            & (df_src['연도'] == y)
            & (df_src['월'] == m)
        )
        return float(df_src.loc[mask, '실적'].sum())

    rows: list[dict] = []

    categories = ['원재료', '재공', '제품']
    sub_items = ['POSCO', 'LOCAL', '기타']

    # 6) 세부 행 + 소계 행 작성
    for cat in categories:
        # 세부 항목 (POSCO/LOCAL/기타)
        for sub in sub_items:
            row = {'구분2': cat, '구분3': sub}

            # 연말 4개 (12월)
            for y, col in zip(year_list, year_cols):
                row[col] = _sum(cat, sub, y, 12)

            # 최근 3개월 (연도 포함)
            for (y_m, m_m), col in zip(month_pairs, month_cols):
                row[col] = _sum(cat, sub, y_m, m_m)

            prev_val = row[month_cols[1]]  # 전월
            curr_val = row[month_cols[2]]  # 당월
            diff = curr_val - prev_val

            row['증량'] = diff
            row['증감률'] = (diff / prev_val * 100.0) if prev_val != 0 else None

            rows.append(row)

        # 소계 행
        sub_df = pd.DataFrame(
            [r for r in rows if r['구분2'] == cat and r['구분3'] in sub_items]
        )
        total_row = {'구분2': cat, '구분3': '소계'}

        # 연말/월 합계
        for col in year_cols + month_cols:
            total_row[col] = float(sub_df[col].sum())

        # 증량/증감률 (합계 기준)
        prev_total = total_row[month_cols[1]]
        curr_total = total_row[month_cols[2]]
        diff_total = curr_total - prev_total

        total_row['증량'] = diff_total
        total_row['증감률'] = (diff_total / prev_total * 100.0) if prev_total != 0 else None

        rows.append(total_row)

    # 7) DataFrame 변환 후 총재고 행 추가

    res = pd.DataFrame(rows)

    # 총재고 = 카테고리 소계 합
    subset = res[res['구분3'] == '소계']
    total_row = {'구분2': '총재고', '구분3': ''}

    for col in year_cols + month_cols:
        total_row[col] = float(subset[col].sum())

    prev_total = total_row[month_cols[1]]
    curr_total = total_row[month_cols[2]]
    diff_total = curr_total - prev_total

    total_row['증량'] = diff_total
    total_row['증감률'] = (diff_total / prev_total * 100.0) if prev_total != 0 else None

    res = pd.concat([res, pd.DataFrame([total_row])], ignore_index=True)

    # 구분2는 블록마다 1번만 출력되도록 

    res = res.reset_index(drop=True)

    for cat in ['원재료', '재공', '제품', '총재고']:
        mask = res['구분2'] == cat
        idxs = res.index[mask].tolist()
        if len(idxs) > 1:
            res.loc[idxs[:-1], '구분2'] = ""   # 첫 행만 남기고 나머지 비움

    # 8) 열 순서 및 인덱스 정리
    res = res[['구분2', '구분3'] + year_cols + month_cols + ['증량', '증감률']]
    res = res.set_index(['구분2', '구분3'])

    # 9) 메타 정보 설정
    res.attrs['company'] = company_name
    res.attrs['base_year'] = req_y

    res.attrs['used_year'] = month_years[2]
    res.attrs['used_month'] = month_list[2]

    res.attrs['prev_year'] = month_years[1]
    res.attrs['prev_month'] = month_list[1]

    res.attrs['prev2_year'] = month_years[0]
    res.attrs['prev2_month'] = month_list[0]

    return res




##### 해외법인실적 부적합 및 장기재고 현황 #####

def create_defect_longinv_table_from_company(
    year: int,
    month: int,
    data: pd.DataFrame,
    company_name: str,
) -> pd.DataFrame:


    required_cols = ['구분1', '구분2', '구분3', '구분4', '연도', '월', '실적']


    # 1) 회사 기준 필터링
    df_src = data.copy()
    df_src['구분1'] = df_src['구분1'].astype(str).str.strip()
    df_src = df_src[df_src['구분1'] == str(company_name).strip()].copy()


    # 2) 타입 정리
    df_src['연도'] = df_src['연도'].astype(str).str.strip().astype(int)
    df_src['월'] = df_src['월'].astype(str).str.strip().astype(int)
    df_src['실적'] = (
        df_src['실적']
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.strip()
    )
    df_src.loc[df_src['실적'] == '', '실적'] = '0'
    df_src['실적'] = df_src['실적'].astype(float)

    req_y = int(year)
    req_m = int(month)

    # 3) 연말 4개 연도 (12월 실적)
    year_list: List[int] = [req_y - 4, req_y - 3, req_y - 2, req_y - 1]
    year_cols: List[str] = [f"'{y % 100:02d}년말" for y in year_list]

    # 4) 최근 3개월 (전전월, 전월, 선택월)
    month_pairs: List[tuple[int, int]] = []
    for k in (2, 1, 0):  # 전전월, 전월, 당월(선택월)
        y = req_y
        m = req_m - k
        while m <= 0:
            y -= 1
            m += 12
        month_pairs.append((y, m))

    month_years = [y for (y, m) in month_pairs]
    prev2_y, prev_y, used_y = month_years
    prev2_m, prev_m, used_m = [m for (y, m) in month_pairs]

    col_prev2 = f"{prev2_m}월"
    col_prev = f"{prev_m}월"
    col_gen = "발생"
    col_used = "소진"
    col_end = "기말"
    col_rate = "증감률"

    # 5) 조회 헬퍼
    def _sum(row2: str, row3: str, y: int, m: int, kind: str | None) -> float:
        mask = (
            (df_src['구분2'].astype(str).str.strip() == row2)
            & (df_src['구분3'].astype(str).str.strip() == row3)
            & (df_src['연도'] == y)
            & (df_src['월'] == m)
        )
        if kind is not None:
            mask &= df_src['구분4'].astype(str).str.strip().eq(kind)
        return float(df_src.loc[mask, '실적'].sum())

    rows: list[dict] = []

    defect_cats = ['재공', 'B급', 'C급', 'D급', 'D2급', 'X급']
    long_cats = ['원재료', '재공', '제품']

    # 6) 기본 행 생성 함수 (부적합/장기 공통)
    def _build_base_row(inv_type: str, cat: str) -> dict:
        row: dict = {'구분2': inv_type, '구분3': cat}

        # 연말 4개 (12월 실적)
        for y, col in zip(year_list, year_cols):
            row[col] = _sum(inv_type, cat, y, 12, '실적')

        # 전전월, 전월 (실적 = 기말로 사용)
        (y2, m2), (y1, m1), (yu, mu) = month_pairs
        row[col_prev2] = _sum(inv_type, cat, y2, m2, '실적')
        row[col_prev] = _sum(inv_type, cat, y1, m1, '실적')

        # 선택월 : 발생/소진
        gen = _sum(inv_type, cat, yu, mu, '발생')
        used = _sum(inv_type, cat, yu, mu, '소진')
        row[col_gen] = gen
        row[col_used] = used

        prev_val = row[col_prev]
        end_val = prev_val + gen - used
        row[col_end] = end_val
        row[col_rate] = (end_val / prev_val - 1) * 100.0 if prev_val != 0 else None

        return row

    # 7) 부적합재고 세부행
    defect_rows = [_build_base_row('부적합재고', c) for c in defect_cats]
    rows.extend(defect_rows)

    # 8) 부적합재고 - 제품 = B급+C급+D급+D2급+X급
    prod_row: dict = {'구분2': '부적합재고', '구분3': '제품'}
    sum_targets = ['B급', 'C급', 'D급', 'D2급', 'X급']

    for col in year_cols + [col_prev2, col_prev, col_gen, col_used, col_end]:
        prod_row[col] = float(
            sum(r[col] for r in defect_rows if r['구분3'] in sum_targets)
        )

    prev_val = prod_row[col_prev]
    end_val = prod_row[col_end]
    prod_row[col_rate] = (end_val / prev_val - 1) * 100.0 if prev_val != 0 else None
    rows.append(prod_row)

    # 9) 부적합재고 소계 = 재공+B급+C급+D급+D2급+X급
    defect_total: dict = {'구분2': '부적합재고', '구분3': '부적합재고 소계'}

    for col in year_cols + [col_prev2, col_prev, col_gen, col_used, col_end]:
        defect_total[col] = float(sum(r[col] for r in defect_rows))

    prev_val = defect_total[col_prev]
    end_val = defect_total[col_end]
    defect_total[col_rate] = (
        (end_val / prev_val - 1) * 100.0 if prev_val != 0 else None
    )
    rows.append(defect_total)

    # 10) 장기재고 기본행
    long_rows = [_build_base_row('장기재고', c) for c in long_cats]
    rows.extend(long_rows)

    # 11) 장기재고 소계 = 원재료+재공+제품
    long_total: dict = {'구분2': '장기재고', '구분3': '장기재고 소계'}

    for col in year_cols + [col_prev2, col_prev, col_gen, col_used, col_end]:
        long_total[col] = float(sum(r[col] for r in long_rows))

    prev_val = long_total[col_prev]
    end_val = long_total[col_end]
    long_total[col_rate] = (
        (end_val / prev_val - 1) * 100.0 if prev_val != 0 else None
    )
    rows.append(long_total)

    # 12) DataFrame 변환 + 정렬
        # 12) DataFrame 변환 + 정렬
    res = pd.DataFrame(rows)

    # 구분 순서 강제
    desired_order = [
        ('부적합재고', '재공'),
        ('부적합재고', 'B급'),
        ('부적합재고', 'C급'),
        ('부적합재고', 'D급'),
        ('부적합재고', 'D2급'),
        ('부적합재고', 'X급'),
        ('부적합재고', '제품'),
        ('부적합재고', '부적합재고 소계'),
        ('장기재고', '원재료'),
        ('장기재고', '재공'),
        ('장기재고', '제품'),
        ('장기재고', '장기재고 소계'),
    ]
    res['__order__'] = res.apply(
        lambda r: desired_order.index((r['구분2'], r['구분3'])),
        axis=1,
    )
    res = res.sort_values('__order__').drop(columns='__order__')

    # 최종 컬럼 순서
    col_order = (
        ['구분2', '구분3']
        + year_cols
        + [col_prev2, col_prev, col_gen, col_used, col_end, col_rate]
    )
    res = res[col_order]

    # 구분2는 블록마다 한 번만 표시
    res = res.set_index(['구분2', '구분3'])


    idx_df = res.index.to_frame(index=False)   # 컬럼: 구분2, 구분3

    for cat in ['부적합재고', '장기재고']:
        mask = idx_df['구분2'] == cat
        idxs = idx_df.index[mask].tolist()
        if len(idxs) > 1:
            idx_df.loc[idxs[:-1], '구분2'] = ""   # 마지막 행만

    # 3) 수정된 인덱스로 다시 MultiIndex 구성
    res.index = pd.MultiIndex.from_frame(idx_df)

    # 13) 메타 정보
    res.attrs['company'] = company_name
    res.attrs['base_year'] = req_y

    res.attrs['used_year'] = used_y
    res.attrs['used_month'] = used_m

    res.attrs['prev_year'] = prev_y
    res.attrs['prev_month'] = prev_m

    res.attrs['prev2_year'] = prev2_y
    res.attrs['prev2_month'] = prev2_m

    return res




##### 해외법인실적 연령별 재고현황 #####




def create_age_table_from_company(
    year: int,
    month: int,
    data: pd.DataFrame,
    company_name: str,
) -> pd.DataFrame:




    # 1) 회사 필터
    df_src = data.copy()
    df_src['구분1'] = df_src['구분1'].astype(str).str.strip()
    df_src = df_src[df_src['구분1'] == str(company_name).strip()].copy()
    if df_src.empty:
        raise ValueError(f"회사 '{company_name}' 데이터가 없습니다.")

    # 2) 타입 정리
    df_src['연도'] = df_src['연도'].astype(str).str.replace(' ', '', regex=False).astype(int)
    df_src['월'] = df_src['월'].astype(str).str.replace(' ', '', regex=False).astype(int)

    df_src['실적'] = (
        df_src['실적']
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.replace(' ', '', regex=False)
    )
    df_src.loc[df_src['실적'] == '', '실적'] = '0'
    df_src['실적'] = df_src['실적'].astype(float)

    req_y = int(year)
    req_m = int(month)

    # 3) 연말 4개 연도
    year_list: List[int] = [req_y - 4, req_y - 3, req_y - 2, req_y - 1]
    year_cols: List[str] = [f"'{y % 100:02d}년말" for y in year_list]

    # 4) 최근 3개월 (전전월, 전월, 선택월)
    month_pairs: List[tuple[int, int]] = []
    for k in (2, 1, 0):  # 전전월, 전월, 선택월
        y = req_y
        m = req_m - k
        while m <= 0:
            y -= 1
            m += 12
        month_pairs.append((y, m))

    month_years = [y for (y, m) in month_pairs]
    month_list = [m for (y, m) in month_pairs]
    prev2_y, prev_y, used_y = month_years
    prev2_m, prev_m, used_m = month_list

    col_prev2 = f"{prev2_m}월"
    col_prev = f"{prev_m}월"
    col_used = f"{used_m}월"
    col_money = "금액"
    col_rate = "증감률"

    # 5) 합계 헬퍼
    def _sum_qty(
        material: str,
        bucket: str,
        y: int,
        m: int,
        unit: str,  # '중량' or '금액'
    ) -> float:
        mask = (
            (df_src['구분2'].astype(str).str.strip() == material)
            & (df_src['구분3'].astype(str).str.strip() == bucket)
            & (df_src['구분4'].astype(str).str.strip() == unit)
            & (df_src['연도'] == y)
            & (df_src['월'] == m)
        )
        return float(df_src.loc[mask, '실적'].sum())

    materials = ['원재료', '재공', '제품']
    buckets = ['3개월 이하', '3개월 초과', '6개월 초과', '1년 초과']

    rows: list[dict] = []
    base_rows: list[dict] = []

    # 6) 원재료/재공/제품 × 월령 기본 행
    for mat in materials:
        for bucket in buckets:
            row: dict = {'구분2': mat, '구분3': bucket}

            # 연말 4개 (중량)
            for y, col in zip(year_list, year_cols):
                row[col] = _sum_qty(mat, bucket, y, 12, '중량')

            # 전전월 / 전월 / 선택월 (중량)
            (y2, m2), (y1, m1), (yu, mu) = month_pairs
            row[col_prev2] = _sum_qty(mat, bucket, y2, m2, '중량')
            row[col_prev]  = _sum_qty(mat, bucket, y1, m1, '중량')
            row[col_used]  = _sum_qty(mat, bucket, yu, mu, '중량')

            # 선택월 금액
            row[col_money] = _sum_qty(mat, bucket, yu, mu, '금액')

            prev_val = row[col_prev]
            used_val = row[col_used]
            row[col_rate] = (used_val / prev_val - 1) * 100.0 if prev_val != 0 else None

            base_rows.append(row)
            rows.append(row)

        # 7) 각 소재 소계 행 (구분3='소계')
        mat_rows = [r for r in base_rows if r['구분2'] == mat]
        total_row: dict = {'구분2': mat, '구분3': '소계'}
        numeric_cols = year_cols + [col_prev2, col_prev, col_used, col_money]

        for col in numeric_cols:
            total_row[col] = float(sum(r[col] for r in mat_rows))

        prev_val = total_row[col_prev]
        used_val = total_row[col_used]
        total_row[col_rate] = (used_val / prev_val - 1) * 100.0 if prev_val != 0 else None

        rows.append(total_row)

    # 8) 전체 6개월 이하 / 6개월 초과 / 합계 (구분2='합계')
    numeric_cols = year_cols + [col_prev2, col_prev, col_used, col_money]

    def _total_row(bucket_label: str, target_buckets: list[str]) -> dict:
        t: dict = {'구분2': '합계', '구분3': bucket_label}
        targets = [
            r for r in base_rows
            if r['구분3'] in target_buckets
        ]
        for col in numeric_cols:
            t[col] = float(sum(r[col] for r in targets))
        prev_val = t[col_prev]
        used_val = t[col_used]
        t[col_rate] = (used_val / prev_val - 1) * 100.0 if prev_val != 0 else None
        return t

    row_6less = _total_row('6개월 이하', ['3개월 이하', '3개월 초과'])
    row_6over = _total_row('6개월 초과', ['6개월 초과', '1년 초과'])
    row_total = _total_row('합계', ['3개월 이하', '3개월 초과', '6개월 초과', '1년 초과'])

    rows.extend([row_6less, row_6over, row_total])

    # 9) DataFrame 변환 + 행 순서 고정
    res = pd.DataFrame(rows)

    order_spec = [
        ('원재료', '3개월 이하'),
        ('원재료', '3개월 초과'),
        ('원재료', '6개월 초과'),
        ('원재료', '1년 초과'),
        ('원재료', '소계'),
        ('재공',   '3개월 이하'),
        ('재공',   '3개월 초과'),
        ('재공',   '6개월 초과'),
        ('재공',   '1년 초과'),
        ('재공',   '소계'),
        ('제품',   '3개월 이하'),
        ('제품',   '3개월 초과'),
        ('제품',   '6개월 초과'),
        ('제품',   '1년 초과'),
        ('제품',   '소계'),
        ('합계',   '6개월 이하'),
        ('합계',   '6개월 초과'),
        ('합계',   '합계'),
    ]
    order_map = {key: i for i, key in enumerate(order_spec)}
    res['__order__'] = res.apply(
        lambda r: order_map.get((r['구분2'], r['구분3']), 999),
        axis=1,
    )
    res = res.sort_values('__order__').drop(columns='__order__')

    col_order = ['구분2', '구분3'] + year_cols + [col_prev2, col_prev, col_used, col_money, col_rate]
    res = res[col_order].set_index(['구분2', '구분3'])

    # ── 여기부터 추가: 구분2는 블록마다 첫 행에만 표시 ──
    idx_df = res.index.to_frame(index=False)   # 컬럼: 구분2, 구분3

    # 원재료 / 재공 / 제품 / 합계 별로 첫 행을 제외하고 구분2를 공백 처리
    for cat in ['원재료', '재공', '제품', '합계']:
        mask = idx_df['구분2'] == cat
        idxs = idx_df.index[mask].tolist()
        if len(idxs) > 1:
            idx_df.loc[idxs[:-1], '구분2'] = ""   # 첫 행만 값 유지, 나머지는 공백

    # 수정된 인덱스로 다시 MultiIndex 구성
    res.index = pd.MultiIndex.from_frame(idx_df)
    # ── 여기까지 추가 ──

    # 10) 메타 정보
    res.attrs['company'] = company_name
    res.attrs['base_year'] = req_y

    res.attrs['used_year'] = used_y
    res.attrs['used_month'] = used_m

    res.attrs['prev_year'] = prev_y
    res.attrs['prev_month'] = prev_m

    res.attrs['prev2_year'] = prev2_y
    res.attrs['prev2_month'] = prev2_m

    return res





def create_ar_status_table_from_company(
    year: int,
    month: int,
    data: pd.DataFrame,
    company_name: str,
) -> pd.DataFrame:
    """
    매출채권 현황 표 생성.

    데이터 스키마
    ------------
    data 컬럼:
        ['구분1','구분2','구분3','구분4','연도','월','실적'] 가정
        - 구분1 : 회사명
        - 구분2 : 매출액(세금포함), 정상채권, 3개월 이하, 3개월 초과,
                  6개월 초과, 회수불능, 매출채권기일, 정상채권기일
        - 구분3, 구분4 는 사용 안 함 (비어 있어도 됨)

    열 구조
    -------
    'YY년말' 4개 : (year-4) ~ (year-1)년 12월 (연말)
    전월         : 기준월의 전월
    기준월       : year, month

    행 구조 (구분 순서 고정)
    ------------------------
    매출액(세금포함)
    정상채권
    3개월 이하
    3개월 초과
    6개월 초과
    회수불능
    기준초과채권          = 3개월 이하 + 3개월 초과 + 6개월 초과 + 회수불능
    매출채권 계           = 정상채권 + 기준초과채권
    초과채권 비율(%)      = 기준초과채권 / 매출채권 계 * 100
    초과채권 이자손실     = 기준초과채권 * 0.05 / 12
    매출채권기일
    정상채권기일
    차이                 = 매출채권기일 - 정상채권기일

    attrs
    -----
    res.attrs['company']      = company_name
    res.attrs['base_year']    = year
    res.attrs['used_year']    = 기준월 연도
    res.attrs['used_month']   = 기준월 월
    res.attrs['prev_year']    = 전월 연도
    res.attrs['prev_month']   = 전월 월
    res.attrs['prev2_year']   = None (미사용, 일관성 위해 생략)
    res.attrs['prev2_month']  = None
    """

    # 0) 기본 컬럼 체크
    required_cols = ['구분1', '구분2', '연도', '월', '실적']
    for c in required_cols:
        if c not in data.columns:
            raise ValueError(f"'{c}' 컬럼이 없습니다. 원본 스키마를 확인하세요.")

    # 1) 회사 기준 필터링
    df_src = data.copy()
    df_src['구분1'] = df_src['구분1'].astype(str).str.strip()
    df_src = df_src[df_src['구분1'] == str(company_name).strip()].copy()
    if df_src.empty:
        raise ValueError(f"회사 '{company_name}' 데이터가 없습니다.")

    # 2) 타입 정리
    df_src['연도'] = (
        df_src['연도']
        .astype(str)
        .str.replace(' ', '', regex=False)
        .astype(int)
    )
    df_src['월'] = (
        df_src['월']
        .astype(str)
        .str.replace(' ', '', regex=False)
        .astype(int)
    )

    df_src['실적'] = (
        df_src['실적']
        .astype(str)
        .str.replace(',', '', regex=False)
        .str.replace(' ', '', regex=False)
    )
    df_src.loc[df_src['실적'] == '', '실적'] = '0'
    df_src['실적'] = df_src['실적'].astype(float)

    req_y = int(year)
    req_m = int(month)

    # 3) 연말 4개 연도 (12월을 연말로 사용)
    year_list: List[int] = [req_y - 4, req_y - 3, req_y - 2, req_y - 1]
    year_cols: List[str] = [
        f"'{str(y % 100).zfill(2)}년말" for y in year_list
    ]

    # 4) 전월 / 기준월
    month_pairs: List[tuple[int, int]] = []
    for k in (1, 0):  # 전월, 기준월
        y = req_y
        m = req_m - k
        while m <= 0:
            y -= 1
            m += 12
        month_pairs.append((y, m))

    (prev_y, prev_m), (used_y, used_m) = month_pairs
    col_prev = f"{prev_m}월"
    col_used = f"{used_m}월"

    # 5) 합계 헬퍼
    def _sum(kind: str, y: int, m: int) -> float:
        mask = (
            (df_src['구분2'].astype(str).str.strip() == kind)
            & (df_src['연도'] == y)
            & (df_src['월'] == m)
        )
        return float(df_src.loc[mask, '실적'].sum())

    base_cats = [
        '매출액(세금포함)',
        '정상채권',
        '3개월 이하',
        '3개월 초과',
        '6개월 초과',
        '회수불능',
        '매출채권기일',
        '정상채권기일',
    ]

    rows: list[dict] = []
    base_rows: dict[str, dict] = {}

    # 6) 기본 행 작성
    for cat in base_cats:
        row: dict = {'구분': cat}

        # 연말 4개 (12월)
        for y, col in zip(year_list, year_cols):
            row[col] = _sum(cat, y, 12)

        # 전월 / 기준월
        row[col_prev] = _sum(cat, prev_y, prev_m)
        row[col_used] = _sum(cat, used_y, used_m)

        rows.append(row)
        base_rows[cat] = row

    period_cols = year_cols + [col_prev, col_used]

    # 7) 기준초과채권 = 3개월 이하 + 3개월 초과 + 6개월 초과 + 회수불능
    crit_name = '기준초과채권'
    crit_row: dict = {'구분': crit_name}
    crit_sources = ['3개월 이하', '3개월 초과', '6개월 초과', '회수불능']

    for col in period_cols:
        crit_row[col] = float(sum(base_rows[s][col] for s in crit_sources))

    rows.append(crit_row)

    # 8) 매출채권 계 = 정상채권 + 기준초과채권
    total_name = '매출채권 계'
    total_row: dict = {'구분': total_name}
    for col in period_cols:
        total_row[col] = float(base_rows['정상채권'][col] + crit_row[col])

    rows.append(total_row)

    # 9) 초과채권 비율(%) = 기준초과채권 / 매출채권 계 * 100
    ratio_name = '초과채권 비율(%)'
    ratio_row: dict = {'구분': ratio_name}
    for col in period_cols:
        denom = total_row[col]
        ratio_row[col] = (crit_row[col] / denom * 100.0) if denom != 0 else None

    rows.append(ratio_row)

    # 10) 초과채권 이자손실 = 기준초과채권 * 0.05 / 12
    loss_name = '초과채권 이자손실'
    loss_row: dict = {'구분': loss_name}
    for col in period_cols:
        loss_row[col] = crit_row[col] * 0.05 / 12.0

    rows.append(loss_row)

    # 11) 차이 = 매출채권기일 - 정상채권기일
    diff_name = '차이'
    diff_row: dict = {'구분': diff_name}
    for col in period_cols:
        diff_row[col] = base_rows['매출채권기일'][col] - base_rows['정상채권기일'][col]

    # 매출채권기일 / 정상채권기일 행은 이미 base_rows에 들어가 있으므로
    rows.append(diff_row)

    # 12) DataFrame 변환 및 행 순서 정리
    res = pd.DataFrame(rows)

    ordered = [
        '매출액(세금포함)',
        '정상채권',
        '3개월 이하',
        '3개월 초과',
        '6개월 초과',
        '회수불능',
        '기준초과채권',
        '매출채권 계',
        '초과채권 비율(%)',
        '초과채권 이자손실',
        '매출채권기일',
        '정상채권기일',
        '차이',
    ]
    res['__order__'] = res['구분'].map({n: i for i, n in enumerate(ordered)})
    res = res.sort_values('__order__').drop(columns='__order__')

    col_order = ['구분'] + year_cols + [col_prev, col_used]
    res = res[col_order].set_index('구분')

    # 13) 메타 정보 설정
    res.attrs['company'] = company_name
    res.attrs['base_year'] = req_y

    res.attrs['used_year'] = used_y
    res.attrs['used_month'] = used_m

    res.attrs['prev_year'] = prev_y
    res.attrs['prev_month'] = prev_m

    # 전전월은 사용하지 않지만 attr 형식 맞추려면 None 등으로 둘 수 있음
    res.attrs['prev2_year'] = None
    res.attrs['prev2_month'] = None

    return res


##### 해외법인실적 인원현황표 #####

def create_87(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:
    """
    인원현황표 생성
    - 구분1 : 인원현황
    - 구분2 : 남통 / 천진 / 중국(남통+천진) / 태국
    - 구분3 : 사무직 / 기능직 / 외주기능직
    - 자사 = 사무직 + 기능직
    - 합계 = 사무직 + 기능직 + 외주기능직
    - 컬럼 : '21년말 ~ '24년말, (전월), (당월), 전월비, %
    """

    df = data.copy()

    # 숫자형 정리
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"] = pd.to_numeric(df["월"], errors="coerce")
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce").fillna(0)

    # 인원현황만 사용
    df = df[df["구분1"] == "인원현황"].copy()
    if df.empty:
        return pd.DataFrame()

    # --------------------------------------------------
    # 1) 공장 순서 고정 (남통 → 천진 → 중국 → 태국)
    #    - 중국은 남통+천진 합산용 가상 공장
    # --------------------------------------------------
    actual_plants = set(df["구분2"].unique())
    PLANT_ORDER = ["남통", "천진", "중국", "태국"]

    plants_for_loop: list[str] = []
    for plant in PLANT_ORDER:
        if plant == "중국":
            # 남통 또는 천진이 실제로 있을 때만 중국 블록 생성
            if {"남통", "천진"} & actual_plants:
                plants_for_loop.append("중국")
        else:
            if plant in actual_plants:
                plants_for_loop.append(plant)

    # --------------------------------------------------
    # 2) 행(직종) 순서 고정
    #    사무직 → 기능직 → 자사 → 외주기능직 → 합계
    # --------------------------------------------------
    ROW_ORDER = ["사무직", "기능직", "자사", "외주기능직", "합계"]

    # 전년 연말 4개
    prev_years = [year - 4, year - 3, year - 2, year - 1]
    year_labels = [f"'{str(y)[-2:]}년말" for y in prev_years]

    # 전월 / 당월
    prev_y, prev_m = year, month - 1
    if prev_m <= 0:
        prev_y -= 1
        prev_m += 12

    prev_label = f"{prev_m}월"
    cur_label = f"{month}월"
    diff_col = "전월비"
    pct_col = "%"

    rows = []

    # --------------------------------------------------
    # 3) 공장별 루프
    # --------------------------------------------------
    for plant in plants_for_loop:
        # 중국이면 남통+천진 합산한 pdf 사용
        if plant == "중국":
            pdf = df[df["구분2"].isin(["남통", "천진"])].copy()
            if pdf.empty:
                continue
        else:
            pdf = df[df["구분2"] == plant].copy()
            if pdf.empty:
                continue

        # 값 계산 함수
        def get_value(y: int, m: int | None, label: str) -> float:
            """
            y년 m월 값 (m=None이면 해당 연도의 마지막 월 사용)
            label: 사무직 / 기능직 / 외주기능직 / 자사 / 합계
            """
            sub = pdf[pdf["연도"] == y]
            if sub.empty:
                return 0

            if m is None:
                last_m = sub["월"].max()
                sub = sub[sub["월"] == last_m]
            else:
                sub = sub[sub["월"] == m]

            if sub.empty:
                return 0

            if label in ["사무직", "기능직", "외주기능직"]:
                return sub[sub["구분3"] == label]["실적"].sum()
            elif label == "자사":
                # 사무직 + 기능직
                return sub[sub["구분3"].isin(["사무직", "기능직"])]["실적"].sum()
            elif label == "합계":
                # 전체 합계
                return sub["실적"].sum()
            else:
                return 0

        # --------------------------------------------------
        # 4) 행 생성: ROW_ORDER 순서대로 한 번에 생성
        #    (사무직 / 기능직 / 자사 / 외주기능직 / 합계)
        # --------------------------------------------------
        for label in ROW_ORDER:
            row = {"구분1": plant, "구분2": label}

            # 4개 연말
            for y, lab in zip(prev_years, year_labels):
                row[lab] = get_value(y, None, label)

            # 전월 / 당월
            row[prev_label] = get_value(prev_y, prev_m, label)
            row[cur_label] = get_value(year, month, label)

            prev_val = row[prev_label]
            cur_val = row[cur_label]
            diff = cur_val - prev_val
            row[diff_col] = diff
            row[pct_col] = (diff / prev_val * 100) if prev_val != 0 else 0

            rows.append(row)

    disp = pd.DataFrame(rows)

    # 컬럼 순서 정리
    cols = ["구분1", "구분2"] + year_labels + [prev_label, cur_label, diff_col, pct_col]
    disp = disp[cols]


    for plant in disp["구분1"].unique():
        mask = disp["구분1"] == plant
        idxs = disp.index[mask]
        # 마지막행 을 제외하고 나머지 공장명 삭제
        if len(idxs) > 1:
            disp.loc[idxs[:-1], "구분1"] = ""

    return disp




def create_89(year: int, month: int, data: pd.DataFrame) -> pd.DataFrame:


    df = data.copy()

    # 숫자 정리
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"] = pd.to_numeric(df["월"], errors="coerce")
    df["실적"] = (
        df["실적"]
        .astype(str)
        .str.replace(",", "", regex=False)
    )
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce").fillna(0)

    # 해당 구분1만 사용
    df = df[df["구분1"] == "인당월평균생산량"].copy()
    if df.empty:
        return pd.DataFrame()

    # 공장 순서 (예시: 남통 → 천진 → 태국)
    PLANT_ORDER = ["남통", "천진", "태국"]
    actual_plants = set(df["구분2"].unique())
    plants_for_loop = [p for p in PLANT_ORDER if p in actual_plants]

    # 과거 4개년 월평균 컬럼
    prev_years = [year - 4, year - 3, year - 2, year - 1]
    year_avg_cols = [f"'{str(y)[-2:]}년 월평균" for y in prev_years]

    # 전월 계산
    prev_y, prev_m = year, month - 1
    if prev_m <= 0:
        prev_y -= 1
        prev_m += 12

    prev_col = f"{prev_m}월"
    cur_col = f"{month}월"
    cur_avg_col = f"'{str(year)[-2:]}년 월평균"

    rows: list[dict] = []

    for plant in plants_for_loop:
        pdf = df[df["구분2"] == plant].copy()
        if pdf.empty:
            continue

        # 기본값 가져오기
        def get_base(metric: str, y: int, mode: str, m: int | None = None) -> float:
            """
            metric: '생산량' / '직접인원'
            mode  : 'avg' (월평균) / 'actual' (실적)
            m     : 월 (실적용 / 특정 월평균용)
            """
            sub = pdf[pdf["연도"] == y]
            if sub.empty:
                return 0

            if mode == "avg":
                sub = sub[sub["구분4"] == "월평균"]
                if m is not None:
                    sub_m = sub[sub["월"] == m]
                    if not sub_m.empty:
                        sub = sub_m
            else:  # 'actual'
                if m is None:
                    return 0
                sub = sub[(sub["구분4"] == "실적") & (sub["월"] == m)]

            if sub.empty:
                return 0

            sub = sub[sub["구분3"] == metric]
            if sub.empty:
                return 0
            return sub["실적"].sum()

        # 공장별 3행: 생산량 / 직접인원 / (인당)
        for row_type in ["생산량", "직접인원", "(인당)"]:
            row: dict = {"구분1": plant, "구분2": row_type}

            # ① 과거 4개년 월평균
            for y, col in zip(prev_years, year_avg_cols):
                if row_type == "(인당)":
                    prod = get_base("생산량", y, "avg")
                    ppl = get_base("직접인원", y, "avg")
                    row[col] = prod / ppl if ppl else 0
                else:
                    row[col] = get_base(row_type, y, "avg")

            # ② 전월 실적
            if row_type == "(인당)":
                prod = get_base("생산량", prev_y, "actual", prev_m)
                ppl = get_base("직접인원", prev_y, "actual", prev_m)
                row[prev_col] = prod / ppl if ppl else 0
            else:
                row[prev_col] = get_base(row_type, prev_y, "actual", prev_m)

            # ③ 당월 실적
            if row_type == "(인당)":
                prod = get_base("생산량", year, "actual", month)
                ppl = get_base("직접인원", year, "actual", month)
                row[cur_col] = prod / ppl if ppl else 0
            else:
                row[cur_col] = get_base(row_type, year, "actual", month)

            # ④ 선택연도 월평균 (해당 month 기준)
            if row_type == "(인당)":
                prod = get_base("생산량", year, "avg", month)
                ppl = get_base("직접인원", year, "avg", month)
                row[cur_avg_col] = prod / ppl if ppl else 0
            else:
                row[cur_avg_col] = get_base(row_type, year, "avg", month)

            rows.append(row)

    disp = pd.DataFrame(rows)

    # 컬럼 순서 정리
    cols = ["구분1", "구분2"] + year_avg_cols + [prev_col, cur_col, cur_avg_col]
    disp = disp[cols]

    for plant in disp["구분1"].unique():
        mask = disp["구분1"] == plant
        idxs = disp.index[mask]
        # 마지막행 을 제외하고 나머지 공장명 삭제
        if len(idxs) > 1:
            disp.loc[idxs[:-1], "구분1"] = ""

    return disp




def _to_number(s):
    if pd.isna(s):
        return 0.0
    s = str(s).strip()
    if s == "":
        return 0.0
    s = s.replace(",", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except Exception:
        return 0.0


# modules.py

import pandas as pd
import numpy as np


def _f95_period_layout(month: int):
    """
    선택 월 기준 컬럼(기간) 정의
    반환형: [(라벨, [포함월 리스트]), ...]
    """
    if month < 1 or month > 12:
        raise ValueError("month must be 1~12")

    periods = []

    # 1~6월 구간 : 1월 2월 3월 1분기 4월 5월 6월 2분기 (선택월까지만)
    if month <= 6:
        # 1,2,3월
        for m in range(1, min(month, 3) + 1):
            periods.append((f"{m}월", [m]))
        periods.append(("1분기", [m for m in range(1, min(month, 3) + 1)]))
            
        # 1분기
        if month >= 3:
            periods.append(("1분기", [1, 2, 3]))
        # 4,5,6월
        if month > 3:
            for m in range(4, min(month, 6) + 1):
                periods.append((f"{m}월", [m]))
            periods.append(("2분기", [m for m in range(4, min(month, 6) + 1)]))
        # 2분기
        if month >= 6:
            periods.append(("2분기", [4, 5, 6]))

    # 7월 이후 : 1분기 2분기 7월 8월 9월 3분기 10월 11월 12월 4분기 (선택월까지만)
    else:
        periods.append(("1분기", [1, 2, 3]))
        periods.append(("2분기", [4, 5, 6]))

        q3_months = [7, 8, 9]
        for m in q3_months:
            if m <= month:
                periods.append((f"{m}월", [m]))
        # 3분기(선택월까지 합)
        periods.append(("3분기", [m for m in q3_months if m <= month]))

        if month >= 10:
            q4_months = [10, 11, 12]
            for m in q4_months:
                if m <= month:
                    periods.append((f"{m}월", [m]))
            periods.append(("4분기", [m for m in q4_months if m <= month]))

    # 누계 (1월~선택월)
    periods.append(("누계", list(range(1, month + 1))))

    return periods


def build_f95(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """
    손익계산서_수정정상원가 데이터를 이미지 표 형식으로 변환.

    - [단위: 백만원, 톤]
      · 금액 계열 : 원 단위 -> 백만원(1,000,000)으로 나눔
      · 수량      : 그대로 (톤)
      · DM%, (이익율) : 기존 실적값의 평균 사용 (원하면 이후 계산식으로 교체)
    """

    df = df_src.copy()

    # ===== 1) 숫자 컬럼 정리 (★★ 중요: 콤마 제거) =====
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df["월"] = pd.to_numeric(df["월"], errors="coerce")

    # 실적에 포함된 콤마/공백 제거 후 숫자 변환
    df["실적"] = (
        df["실적"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["실적"] = pd.to_numeric(df["실적"], errors="coerce").fillna(0)

    # 없는 컬럼 대비
    if "구분3" not in df.columns:
        df["구분3"] = ""
    if "구분4" not in df.columns:
        df["구분4"] = ""

    df["구분3"] = df["구분3"].fillna("")
    df["구분4"] = df["구분4"].fillna("")

    # 대상 연도 + 손익계산서_수정정상원가
    df = df[(df["연도"] == year) & (df["구분1"] == "손익계산서_수정정상원가")]

    periods = _f95_period_layout(month)

    # ===== 2) 행 순서 정의 =====
    row_specs = [
        {"type": "money", "g2": "매출액"},
        {"type": "money", "g2": "제품 매출"},
        {"type": "qty",   "g2": "수량"},
        {"type": "money", "g2": "부산물 매출"},

        {"type": "money", "g2": "변동비"},
        {"type": "money", "g2": "재료비"},
        {"type": "pct",   "g2": "DM%"},

        {"type": "money", "g2": "가공비", "g3": "부재료비"},
        {"type": "money", "g2": "가공비", "g3": "외주용역비"},
        {"type": "money", "g2": "가공비", "g3": "수선비"},
        {"type": "money", "g2": "가공비", "g3": "기타"},

        {"type": "money", "g2": "운반비", "g3": "C조건 선임"},
        {"type": "money", "g2": "운반비", "g3": "수출개별비"},
        {"type": "money", "g2": "운반비", "g3": "국내 운반비"},

        {"type": "money", "g2": "한계이익"},
        {"type": "pct",   "g2": "(이익율)"},

        {"type": "money", "g2": "고정비"},
        {"type": "money", "g2": "가공비", "g3": "감가상각비"},
        {"type": "money", "g2": "가공비", "g3": "제조노무비"},
        {"type": "money", "g2": "가공비", "g3": "기타"},
        {"type": "money", "g2": "판관비", "g3": "기타"},
        {"type": "money", "g2": "재고자산평가, X등급 매출 등"},

        {"type": "money", "g2": "영업이익"},
        {"type": "pct",   "g2": "(이익율)"},

        {"type": "money", "g2": "기타수익"},
        {"type": "money", "g2": "기타비용"},
        {"type": "money", "g2": "금융수익"},
        {"type": "money", "g2": "금융비용"},

        {"type": "money", "g2": "경상이익"},
        {"type": "pct",   "g2": "(이익율)"},


        {"type": "money", "g2": "경상이익_재경마감"},
        {"type": "pct",   "g2": "(이익율)"},
    ]

    rows = []

    # ===== 3) 기간별 합계/평균 계산 =====
    for spec in row_specs:
        if spec["type"] == "blank":
            row = {"구분2": "", "구분3": ""}
            for label, _ in periods:
                row[label] = ""
            rows.append(row)
            continue

        g2 = spec.get("g2")
        g3 = spec.get("g3", "")
        rtype = spec["type"]

        row = {"구분2": g2, "구분3": g3}

        sub = df[(df["구분2"] == g2) & (df["구분3"] == g3)]

        for label, m_list in periods:
            if sub.empty:
                row[label] = ""
                continue

            mask = sub["월"].isin(m_list)
            if not mask.any():
                row[label] = ""
                continue

            vals = sub.loc[mask, "실적"]

            if rtype == "money":
                raw = vals.sum()
                val = raw / 1_000_000.0     # 백만원
            elif rtype == "qty":
                raw = vals.sum()
                val = raw / 1_000.0
            elif rtype == "pct":
                val = vals.mean()           # 단순 평균
            else:
                val = ""

            row[label] = val

        rows.append(row)

    result = pd.DataFrame(rows)
    result["구분3"] = result["구분3"].fillna("")

    # -----------------------------
    # 1) 가짜열(구분1) 생성
    # -----------------------------
    major_accounts = [
        "매출액",
        "변동비",
        "한계이익",
        "고정비",
        "재고자산평가, X등급 매출 등",
        "영업이익",
        "경상이익",
        "경상이익_재경마감",
    ]

    # 제일 왼쪽에 '구분1' 삽입
    result.insert(0, "구분1", "")

    # major_accounts 에 해당하는 항목을 구분1으로 올리고 구분2 비우기
    mask_major = result["구분2"].isin(major_accounts)
    result.loc[mask_major, "구분1"] = result.loc[mask_major, "구분2"]
    result.loc[mask_major, "구분2"] = ""

    #구분2 중복 제거
    prev_key = (None, None)

    for i in result.index:
        g1 = result.at[i, "구분1"]
        g2 = result.at[i, "구분2"]

        key = (g1, g2)

        if key == prev_key and g2 != "":
            result.at[i, "구분2"] = ""   # 중복된 가공비/운반비 제거
        else:
            prev_key = key

    # -----------------------------
    # 3) DM% / (이익율) 은 구분3 로 이동
    #    - 재료비 아래 DM%
    #    - 한계이익 / 영업이익 / 경상이익 / 경상이익_재경마감 아래 (이익율)
    # -----------------------------
    mask_move_to_g3 = result["구분2"].isin(["DM%", "(이익율)"])
    result.loc[mask_move_to_g3, "구분3"] = result.loc[mask_move_to_g3, "구분2"]
    result.loc[mask_move_to_g3, "구분2"] = ""

    return result






def build_f96(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:


    df = df_src.copy()

    # 숫자/연월 전처리
    df["실적"] = df["실적"].apply(_to_number)
    df["연도"] = df["연도"].astype(int)
    df["월"]   = df["월"].astype(int)

    # 선택연월 "당월"만 사용
    mask = (df["연도"] == int(year)) & (df["월"] == int(month))
    df = df.loc[mask].copy()

    products = ["CHQ", "CD", "STS", "BTB", "PB"]
    df = df[df["구분1"].isin(products)]

    # (구분2=내수/수출, 구분3=업종, 구분1=제품, 구분4=지표) 집계
    tmp = (
        df.pivot_table(
            index=["구분2", "구분3", "구분1"],
            columns="구분4",
            values="실적",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    for col in ["매출중량", "매출금액", "영업이익"]:
        if col not in tmp.columns:
            tmp[col] = 0.0

    tmp["판매중량"]     = tmp["매출중량"]
    tmp["판매금액"]     = tmp["매출금액"]
    tmp["영업이익금액"] = tmp["영업이익"]
    metrics_cols = ["판매중량", "판매금액", "영업이익금액"]

    # 한 섹션(내수 전체, 내수-자동차 등)을 한 행으로 만드는 함수
    def make_row(sub: pd.DataFrame, label1: str, label2: str) -> dict:
        row = {"구분1": label1, "구분2": label2}
        prod_sums = {}

        for p in products:
            d = sub[sub["구분1"] == p]
            if not d.empty:
                vals = d[metrics_cols].sum()
            else:
                vals = pd.Series([0.0, 0.0, 0.0], index=metrics_cols)

            qty = vals["판매중량"]
            amt = vals["판매금액"]
            op  = vals["영업이익금액"]

            # ── 제품별 지표 ──
            row[f"{p}_판매중량"] = qty
            row[f"{p}_판매금액"] = amt
            row[f"{p}_영업이익"] = op

            row[f"{p}_단가"] = op / qty if qty != 0 else 0.0        # 영업이익 단가
            row[f"{p}_%"]   = (op / amt * 100.0) if amt != 0 else 0.0

            prod_sums[p] = (qty, amt, op)

        # ── 총계(제품 합산 후 재계산) ──
        total_qty = sum(q for q, _, _ in prod_sums.values())
        total_amt = sum(a for _, a, _ in prod_sums.values())
        total_op  = sum(o for _, _, o in prod_sums.values())

        row["총계_판매중량"] = total_qty
        row["총계_판매금액"] = total_amt
        row["총계_영업이익"] = total_op
        row["총계_단가"] = total_op / total_qty if total_qty != 0 else 0.0
        row["총계_%"]   = (total_op / total_amt * 100.0) if total_amt != 0 else 0.0

        return row

    # 행 구성 – 내수/수출/총계 + 업종별
    industry_order = ["자동차", "산업기계", "건설", "전자", "기타", "조선", "항공"]
    rows = []

    # 내수, 수출 섹션
    for ch in ["내수", "수출"]:
        base_ch = tmp[tmp["구분2"] == ch]
        rows.append(make_row(base_ch, ch, ""))  # 채널 합계 (구분1 = 내수/수출)
        for ind in industry_order:
            sub = base_ch[base_ch["구분3"] == ind]
            rows.append(make_row(sub, "", ind))

    # 내수+수출 총계 섹션 (섹션 맨 위의 총계)
    total_row = make_row(tmp, "총계", "")
    rows.append(total_row)  # 여기서는 구분1 = '총계' 그대로 사용

    for ind in industry_order:
        sub = tmp[tmp["구분3"] == ind]
        rows.append(make_row(sub, "", ind))

    # 총계 행 추가
    last_row = total_row.copy()
    last_row["구분1"] = ""   
    last_row["구분2"] = ""  
    rows.append(last_row)

    df_out = pd.DataFrame(rows)


    # ── 컬럼 순서: 총계 → CHQ → CD → STS → BTB → PB ──
    cols = ["구분1", "구분2"]

    def block(prod):
        return [
            f"{prod}_판매중량",
            f"{prod}_단가",

            f"{prod}_영업이익",
            f"{prod}_%",
        ]

    cols += block("총계")
    for p in products:
        cols += block(p)

    cols = [c for c in cols if c in df_out.columns]
    df_out = df_out[cols]

    # ── 단위 해결 ──
    # 1) 중량, 판매금액
    def _round_for_display_1k(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1000.0, 0))

    # 2) 영업이익 금액
    def _round_for_display_1m(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1000000.0, 0))

    # 중량 / 판매금액 컬럼들 (기존 방식: /1000)
    weight_and_sales_cols = [
        c for c in df_out.columns
        if ("판매중량" in c) or ("판매금액" in c)
    ]

    # 영업이익 '금액' 컬럼들 (%, 비율은 제외)
    op_profit_amount_cols = [
        c for c in df_out.columns
        if ("영업이익금액" in c )or( "영업이익"  in c)
    ]

    for c in weight_and_sales_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1k)

    for c in op_profit_amount_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1m)

    return df_out

def build_f97(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    df = df_src.copy()

    # 숫자/연월 전처리
    df["실적"] = df["실적"].apply(_to_number)
    df["연도"] = df["연도"].astype(int)
    df["월"]   = df["월"].astype(int)

    # 선택연월 "당월"만 사용
    mask = (df["연도"] == int(year)) & (df["월"] == int(month))
    df = df.loc[mask].copy()

    products = ["CHQ", "CD", "STS", "BTB", "PB"]
    df = df[df["구분1"].isin(products)]

    # (구분2=내수/수출, 구분3=유통/실수요, 구분1=제품, 구분4=지표) 집계
    tmp = (
        df.pivot_table(
            index=["구분2", "구분3", "구분1"],
            columns="구분4",
            values="실적",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    for col in ["매출중량", "매출금액", "영업이익"]:
        if col not in tmp.columns:
            tmp[col] = 0.0

    tmp["판매중량"]     = tmp["매출중량"]
    tmp["판매금액"]     = tmp["매출금액"]
    tmp["영업이익금액"] = tmp["영업이익"]
    metrics_cols = ["판매중량", "판매금액", "영업이익금액"]

    # 한 섹션(내수 전체, 내수-유통 등)을 한 행으로 만드는 함수
    def make_row(sub: pd.DataFrame, label1: str, label2: str, ch_tag: str) -> dict:
        row = {"구분1": label1, "구분2": label2, "채널": ch_tag}
        prod_sums = {}

        for p in products:
            d = sub[sub["구분1"] == p]
            if not d.empty:
                vals = d[metrics_cols].sum()
            else:
                vals = pd.Series([0.0, 0.0, 0.0], index=metrics_cols)

            qty = vals["판매중량"]
            amt = vals["판매금액"]
            op  = vals["영업이익금액"]

            # ── 제품별 지표 ──
            row[f"{p}_판매중량"] = qty
            row[f"{p}_판매금액"] = amt
            row[f"{p}_영업이익"] = op

            row[f"{p}_단가"] = op / qty if qty != 0 else 0.0        # 영업이익 단가
            row[f"{p}_%"]   = (op / amt * 100.0) if amt != 0 else 0.0

            prod_sums[p] = (qty, amt, op)

        # ── 총계(제품 합산 후 재계산) ──
        total_qty = sum(q for q, _, _ in prod_sums.values())
        total_amt = sum(a for _, a, _ in prod_sums.values())
        total_op  = sum(o for _, _, o in prod_sums.values())

        row["총계_판매중량"] = total_qty
        row["총계_판매금액"] = total_amt
        row["총계_영업이익"] = total_op
        row["총계_단가"]     = total_op / total_qty if total_qty != 0 else 0.0
        row["총계_%"]       = (total_op / total_amt * 100.0) if total_amt != 0 else 0.0

        return row

    # 행 구성 – 내수/수출/총계 + 유통/실수요
    industry_order = ["유통", "실수요"]
    rows = []

    # 내수, 수출 섹션
    for ch in ["내수", "수출"]:
        base_ch = tmp[tmp["구분2"] == ch]

        # 채널 합계
        rows.append(make_row(base_ch, ch, "", ch))

        # 유통 / 실수요
        for ind in industry_order:
            sub = base_ch[base_ch["구분3"] == ind]
            rows.append(make_row(sub, "", ind, ch))

    # 내수+수출 총계 섹션
    total_row = make_row(tmp, "총계", "", "총계")
    rows.append(total_row)

    for ind in industry_order:
        sub = tmp[tmp["구분3"] == ind]
        rows.append(make_row(sub, "", ind, "총계"))

    # 총계 행 추가 (구분은 공백)
    last_row = total_row.copy()
    last_row["구분1"] = ""
    last_row["구분2"] = ""
    rows.append(last_row)

    df_out = pd.DataFrame(rows)


        # ── 비중 계산 ──
    # 비중 = (유통/실수요 행의 총계_판매중량) / (해당 채널 합계 행의 총계_판매중량) * 100
    df_out["비중"] = ""   # 컬럼 이름을 그냥 "비중"으로

    for ch in ["내수", "수출", "총계"]:
        mask_ch = df_out["채널"] == ch
        if not mask_ch.any():
            continue

        # 해당 채널의 "합계 행" (구분1=채널명)
        total_qty_series = df_out.loc[
            mask_ch & (df_out["구분1"] == ch),
            "총계_판매중량"
        ]
        if total_qty_series.empty:
            continue

        denom = total_qty_series.iloc[0]
        if denom == 0:
            continue

        # 유통 / 실수요 행만 비중 계산
        numer_mask = mask_ch & df_out["구분2"].isin(["유통", "실수요"])
        df_out.loc[numer_mask, "비중"] = (
            df_out.loc[numer_mask, "총계_판매중량"] / denom * 100.0
        )


        # ── 컬럼 순서: 구분1, 구분2, 비중 → 총계 → CHQ → ... ──
    cols = ["구분1", "구분2", "비중"]

    def block(prod):
        return [
            f"{prod}_판매중량",
            f"{prod}_단가",
            f"{prod}_영업이익",
            f"{prod}_%",
        ]

    cols += block("총계")
    for p in products:
        cols += block(p)

    cols = [c for c in cols if c in df_out.columns]
    df_out = df_out[cols]


    # ── 단위 해결 ──
    def _round_for_display_1k(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1000.0, 0))

    def _round_for_display_1m(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1_000_000.0, 0))

    # 중량 / 판매금액
    weight_and_sales_cols = [
        c for c in df_out.columns
        if ("판매중량" in c) or ("판매금액" in c)
    ]

    # 영업이익 '금액'
    op_profit_amount_cols = [
        c for c in df_out.columns
        if ("영업이익" in c and "%" not in c)
    ]

    for c in weight_and_sales_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1k)

    for c in op_profit_amount_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1m)

    return df_out


def build_f98(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    df = df_src.copy()

    # 숫자/연월 전처리
    df["실적"] = df["실적"].apply(_to_number)
    df["연도"] = df["연도"].astype(int)
    df["월"]   = df["월"].astype(int)

    # 선택연월 "당월"만 사용
    mask = (df["연도"] == int(year)) & (df["월"] == int(month))
    df = df.loc[mask].copy()

    products = ["CHQ", "CD", "STS", "BTB", "PB"]
    df = df[df["구분1"].isin(products)]

    # (구분2=내수/수출, 구분3=유통/실수요, 구분1=제품, 구분4=지표) 집계
    tmp = (
        df.pivot_table(
            index=["구분2", "구분3", "구분1"],
            columns="구분4",
            values="실적",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    for col in ["매출중량", "매출금액", "영업이익"]:
        if col not in tmp.columns:
            tmp[col] = 0.0

    tmp["판매중량"]     = tmp["매출중량"]
    tmp["판매금액"]     = tmp["매출금액"]
    tmp["영업이익금액"] = tmp["영업이익"]
    metrics_cols = ["판매중량", "판매금액", "영업이익금액"]

    # 한 섹션(내수 전체, 내수-유통 등)을 한 행으로 만드는 함수
    def make_row(sub: pd.DataFrame, label1: str, label2: str, ch_tag: str) -> dict:
        row = {"구분1": label1, "구분2": label2, "채널": ch_tag}
        prod_sums = {}

        for p in products:
            d = sub[sub["구분1"] == p]
            if not d.empty:
                vals = d[metrics_cols].sum()
            else:
                vals = pd.Series([0.0, 0.0, 0.0], index=metrics_cols)

            qty = vals["판매중량"]
            amt = vals["판매금액"]
            op  = vals["영업이익금액"]

            # ── 제품별 지표 ──
            row[f"{p}_판매중량"] = qty
            row[f"{p}_판매금액"] = amt
            row[f"{p}_영업이익"] = op

            row[f"{p}_단가"] = op / qty if qty != 0 else 0.0        # 영업이익 단가
            row[f"{p}_%"]   = (op / amt * 100.0) if amt != 0 else 0.0

            prod_sums[p] = (qty, amt, op)

        # ── 총계(제품 합산 후 재계산) ──
        total_qty = sum(q for q, _, _ in prod_sums.values())
        total_amt = sum(a for _, a, _ in prod_sums.values())
        total_op  = sum(o for _, _, o in prod_sums.values())

        row["총계_판매중량"] = total_qty
        row["총계_판매금액"] = total_amt
        row["총계_영업이익"] = total_op
        row["총계_단가"]     = total_op / total_qty if total_qty != 0 else 0.0
        row["총계_%"]       = (total_op / total_amt * 100.0) if total_amt != 0 else 0.0

        return row

    # ── 채널별 industry order 정의 ──
    industry_order_domestic = [
        "포스코",
        "JFE STEEL(S)",
        "세아창원특수강",
        "현대제철",
        "세아베스틸",
        "사강",
        "진양특수강(주)",
        "용강제철",
        "JFE STEEL",
        "삼원강재",
        "중천강철",
        "DAIDO",
        "SAARSTAHL",
        "청도강철",
    ]

    industry_order_export = [
        "포스코",
        "JFE STEEL(S)",
        "세아베스틸",
        "세아창원특수강",
        "진양특수강(주)",
        "WALSIN",
    ]

    industry_order_total = [
        "포스코",
        "JFE STEEL(S)",
        "세아창원특수강",
        "현대제철",
        "세아베스틸",
        "사강",
        "진양특수강(주)",
        "용강제철",
        "JFE STEEL",
        "삼원강재",
        "중천강철",
        "DAIDO",
        "SAARSTAHL",
        "청도강철",
        "WALSIN",
    ]

    rows = []

    # ── 내수, 수출 섹션 ──
    for ch in ["내수", "수출"]:
        base_ch = tmp[tmp["구분2"] == ch]

        # 채널 합계
        rows.append(make_row(base_ch, ch, "", ch))

        # 산업체(구분3)별
        if ch == "내수":
            curr_order = industry_order_domestic
        else:  # "수출"
            curr_order = industry_order_export

        for ind in curr_order:
            sub = base_ch[base_ch["구분3"] == ind]
            rows.append(make_row(sub, "", ind, ch))

    # ── 내수+수출 총계 섹션 ──
    total_row = make_row(tmp, "총계", "", "총계")
    rows.append(total_row)

    for ind in industry_order_total:
        sub = tmp[tmp["구분3"] == ind]
        rows.append(make_row(sub, "", ind, "총계"))

    # 마지막 총계 행 추가 (구분은 공백)
    last_row = total_row.copy()
    last_row["구분1"] = ""
    last_row["구분2"] = ""
    rows.append(last_row)

    df_out = pd.DataFrame(rows)

    # ── 비중 계산 ──
    # 비중 = (산업체 행의 총계_판매중량) / (해당 채널 합계 행의 총계_판매중량) * 100
    df_out["비중"] = ""   # 컬럼 이름을 그냥 "비중"으로

    for ch in ["내수", "수출", "총계"]:
        mask_ch = df_out["채널"] == ch
        if not mask_ch.any():
            continue

        # 해당 채널의 "합계 행" (구분1=채널명 또는 "총계")
        total_qty_series = df_out.loc[
            mask_ch & (df_out["구분1"] == ch),
            "총계_판매중량"
        ]
        if total_qty_series.empty:
            continue

        denom = total_qty_series.iloc[0]
        if denom == 0:
            continue

        # 채널별 industry 리스트 선택
        if ch == "내수":
            targets = industry_order_domestic
        elif ch == "수출":
            targets = industry_order_export
        else:  # "총계"
            targets = industry_order_total

        numer_mask = mask_ch & df_out["구분2"].isin(targets)
        df_out.loc[numer_mask, "비중"] = (
            df_out.loc[numer_mask, "총계_판매중량"] / denom * 100.0
        )

    # ── 컬럼 순서: 구분1, 구분2, 비중 → 총계 → CHQ → ... ──
    cols = ["구분1", "구분2", "비중"]

    def block(prod):
        return [
            f"{prod}_판매중량",
            f"{prod}_단가",
            f"{prod}_영업이익",
            f"{prod}_%",
        ]

    cols += block("총계")
    for p in products:
        cols += block(p)

    cols = [c for c in cols if c in df_out.columns]
    df_out = df_out[cols]

    # ── 단위 해결 ──
    def _round_for_display_1k(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1000.0, 0))

    def _round_for_display_1m(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1_000_000.0, 0))

    # 중량 / 판매금액
    weight_and_sales_cols = [
        c for c in df_out.columns
        if ("판매중량" in c) or ("판매금액" in c)
    ]

    # 영업이익 '금액'
    op_profit_amount_cols = [
        c for c in df_out.columns
        if ("영업이익" in c and "%" not in c)
    ]

    for c in weight_and_sales_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1k)

    for c in op_profit_amount_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1m)

    return df_out



def build_f99(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:

    df = df_src.copy()

    # 숫자/연월 전처리
    df["실적"] = df["실적"].apply(_to_number)
    df["연도"] = df["연도"].astype(int)
    df["월"]   = df["월"].astype(int)

    # 선택 연월 필터
    mask = (df["연도"] == int(year)) & (df["월"] == int(month))
    df = df.loc[mask].copy()

    # 제품 목록(표에 나올 순서)
    products = ["선재영업팀", "봉강영업팀", "부산영업소", "대구영업소", "글로벌영업팀"]
    df = df[df["구분1"].isin(products)]

   
    tmp = (
        df.pivot_table(
            index=["구분2", "구분1"],
            columns="분류",
            values="실적",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    
    for col in ["매출중량", "매출금액", "영업이익"]:
        if col not in tmp.columns:
            tmp[col] = 0.0

    # 통일된 컬럼명
    tmp["판매중량"]     = tmp["매출중량"]
    tmp["판매금액"]     = tmp["매출금액"]
    tmp["영업이익금액"] = tmp["영업이익"]
    metrics_cols = ["판매중량", "판매금액", "영업이익금액"]

    
    def make_row(sub: pd.DataFrame, industry_label: str) -> dict:
        # 출력용: 구분1에 '포스코', 'JFE STEEL(S)' 등 표시
        row = {"구분1": industry_label}
        prod_sums = {}

        for p in products:
            d = sub[sub["구분1"] == p]
            if not d.empty:
                vals = d[metrics_cols].sum()
            else:
                vals = pd.Series([0.0, 0.0, 0.0], index=metrics_cols)

            qty = vals["판매중량"]
            amt = vals["판매금액"]
            op  = vals["영업이익금액"]

            # 제품별 지표
            row[f"{p}_판매중량"] = qty
            row[f"{p}_판매금액"] = amt
            row[f"{p}_영업이익"] = op
            row[f"{p}_단가"]      = op / qty if qty != 0 else 0.0
            row[f"{p}_%"]        = (op / amt * 100.0) if amt != 0 else 0.0

            prod_sums[p] = (qty, amt, op)

        # 총계(제품 합산)
        total_qty = sum(q for q, _, _ in prod_sums.values())
        total_amt = sum(a for _, a, _ in prod_sums.values())
        total_op  = sum(o for _, _, o in prod_sums.values())

        row["총계_판매중량"] = total_qty
        row["총계_판매금액"] = total_amt
        row["총계_영업이익"] = total_op
        row["총계_단가"]     = total_op / total_qty if total_qty != 0 else 0.0
        row["총계_%"]       = (total_op / total_amt * 100.0) if total_amt != 0 else 0.0

        return row

    industry_order = [
        "포스코",
        "JFE STEEL(S)",
        "세아창원특수강",
        "현대제철",
        "세아베스틸",
        "기타",
    ]

    rows = []
    for ind in industry_order:
        sub = tmp[tmp["구분2"] == ind]
        # if sub.empty:
        #     continue
        rows.append(make_row(sub, ind))

    # 전체 합계 행
    total_row = make_row(tmp, "")
    rows.append(total_row)

    df_out = pd.DataFrame(rows)


    df_out["비중"] = 0.0


    #전체 총계
    total_qty_series = df_out.loc[df_out["구분1"] == "", "총계_판매중량"] 
    if not total_qty_series.empty:
        denom = total_qty_series.iloc[0]
        if denom != 0:
            mask_industry = df_out["구분1"] != ""
            df_out.loc[mask_industry, "비중"] = (
                df_out.loc[mask_industry, "총계_판매중량"] / denom * 100.0
            )


    df_out.loc[df_out["구분1"] == "", "비중"] = ""

    # ── 컬럼 순서 정리: 구분1, 비중 → 총계 → 제품별 ──
    cols = ["구분1", "비중"]

    def block(prod):
        return [
            f"{prod}_판매중량",
            f"{prod}_단가",
            f"{prod}_영업이익",
            f"{prod}_%",
        ]

    cols += block("총계")
    for p in products:
        cols += block(p)

    cols = [c for c in cols if c in df_out.columns]
    df_out = df_out[cols]

    # ── 단위(표시용 스케일링 및 반올림) ──
    def _round_for_display_1k(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1000.0, 0))

    def _round_for_display_1m(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1_000_000.0, 0))

    # 중량 / 판매금액
    weight_and_sales_cols = [
        c for c in df_out.columns
        if ("판매중량" in c) or ("판매금액" in c)
    ]

    # 영업이익 금액
    op_profit_amount_cols = [
        c for c in df_out.columns
        if ("영업이익" in c and "%" not in c)
    ]

    for c in weight_and_sales_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1k)

    for c in op_profit_amount_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1m)

    # 비중은 소수 첫째 자리까지(원하면 조정 가능)
    if df_out["비중"].dtype != object:
        df_out["비중"] = df_out["비중"].round(1)

    return df_out





def build_f100(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    df = df_src.copy()

    # 숫자/연월 전처리
    df["실적"] = df["실적"].apply(_to_number)
    df["연도"] = df["연도"].astype(int)
    df["월"]   = df["월"].astype(int)

    # 선택연월 "당월"만 사용
    mask = (df["연도"] == int(year)) & (df["월"] == int(month))
    df = df.loc[mask].copy()

    products = ["선재영업팀","봉강영업팀","부산영업소","대구영업소","글로벌영업팀"]
    df = df[df["구분1"].isin(products)]

    tmp = (
        df.pivot_table(
            index=["구분2", "구분3", "구분1"],
            columns="구분4",
            values="실적",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    for col in ["매출중량", "매출금액", "영업이익"]:
        if col not in tmp.columns:
            tmp[col] = 0.0

    tmp["판매중량"]     = tmp["매출중량"]
    tmp["판매금액"]     = tmp["매출금액"]
    tmp["영업이익금액"] = tmp["영업이익"]
    metrics_cols = ["판매중량", "판매금액", "영업이익금액"]

    # 한 섹션(내수 전체, 내수-유통 등)을 한 행으로 만드는 함수
    def make_row(sub: pd.DataFrame, label1: str, label2: str, ch_tag: str) -> dict:
        row = {"구분1": label1, "구분2": label2, "채널": ch_tag}
        prod_sums = {}

        for p in products:
            d = sub[sub["구분1"] == p]
            if not d.empty:
                vals = d[metrics_cols].sum()
            else:
                vals = pd.Series([0.0, 0.0, 0.0], index=metrics_cols)

            qty = vals["판매중량"]
            amt = vals["판매금액"]
            op  = vals["영업이익금액"]

            # ── 제품별 지표 ──
            row[f"{p}_판매중량"] = qty
            row[f"{p}_판매금액"] = amt
            row[f"{p}_영업이익"] = op

            row[f"{p}_단가"] = op / qty if qty != 0 else 0.0        # 영업이익 단가
            row[f"{p}_%"]   = (op / amt * 100.0) if amt != 0 else 0.0

            prod_sums[p] = (qty, amt, op)

        # ── 총계(제품 합산 후 재계산) ──
        total_qty = sum(q for q, _, _ in prod_sums.values())
        total_amt = sum(a for _, a, _ in prod_sums.values())
        total_op  = sum(o for _, _, o in prod_sums.values())

        row["총계_판매중량"] = total_qty
        row["총계_판매금액"] = total_amt
        row["총계_영업이익"] = total_op
        row["총계_단가"]     = total_op / total_qty if total_qty != 0 else 0.0
        row["총계_%"]       = (total_op / total_amt * 100.0) if total_amt != 0 else 0.0

        return row

    industry_order = ["포스코",
        "JFE STEEL(S)",
        "세아창원특수강",
        "현대제철",
        "세아베스틸",
        "기타"
        ]
    rows = []

    # 내수, 수출 섹션
    for ch in ["포항공장", "충주공장","충주2공장"]:
        base_ch = tmp[tmp["구분2"] == ch]

        # 채널 합계
        rows.append(make_row(base_ch, ch, "", ch))

        # 유통 / 실수요
        for ind in industry_order:
            sub = base_ch[base_ch["구분3"] == ind]
            rows.append(make_row(sub, "", ind, ch))

    # 내수+수출 총계 섹션
    total_row = make_row(tmp, "총합계", "", "총합계")
    rows.append(total_row)

    # for ind in industry_order:
    #     sub = tmp[tmp["구분3"] == ind]
    #     rows.append(make_row(sub, "", ind, "총계"))

    # # 총계 행 추가 (구분은 공백)
    # last_row = total_row.copy()
    # last_row["구분1"] = ""
    # last_row["구분2"] = ""
    # rows.append(last_row)

    df_out = pd.DataFrame(rows)


    # ── 비중 계산 ──
    # 비중 = (유통/실수요 행의 총계_판매중량) / (해당 채널 합계 행의 총계_판매중량) * 100
    df_out["비중"] = ""   # 컬럼 이름을 그냥 "비중"으로

    for ch in ["포항공장", "충주공장", "충주2공장"]:
        mask_ch = df_out["채널"] == ch
        if not mask_ch.any():
            continue

        # 해당 채널의 "합계 행" (구분1=채널명)
        total_qty_series = df_out.loc[
            mask_ch & (df_out["구분1"] == ch),
            "총계_판매중량"
        ]
        if total_qty_series.empty:
            continue

        denom = total_qty_series.iloc[0]
        if denom == 0:
            continue

        # 유통 / 실수요 행만 비중 계산
        numer_mask = mask_ch & df_out["구분2"].isin(["포스코",
            "JFE STEEL(S)",
            "세아창원특수강",
            "현대제철",
            "세아베스틸",
            "기타"])
        df_out.loc[numer_mask, "비중"] = (
            df_out.loc[numer_mask, "총계_판매중량"] / denom * 100.0
        )


        # ── 컬럼 순서: 구분1, 구분2, 비중 → 총계 → CHQ → ... ──
    cols = ["구분1", "구분2", "비중"]

    def block(prod):
        return [
            f"{prod}_판매중량",
            f"{prod}_단가",
            f"{prod}_영업이익",
            f"{prod}_%",
        ]

    cols += block("총계")
    for p in products:
        cols += block(p)

    cols = [c for c in cols if c in df_out.columns]
    df_out = df_out[cols]


    # ── 단위 해결 ──
    def _round_for_display_1k(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1000.0, 0))

    def _round_for_display_1m(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1_000_000.0, 0))

    # 중량 / 판매금액
    weight_and_sales_cols = [
        c for c in df_out.columns
        if ("판매중량" in c) or ("판매금액" in c)
    ]

    # 영업이익 '금액'
    op_profit_amount_cols = [
        c for c in df_out.columns
        if ("영업이익" in c and "%" not in c)
    ]

    for c in weight_and_sales_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1k)

    for c in op_profit_amount_cols:
        df_out[c] = df_out[c].apply(_round_for_display_1m)

    return df_out



import pandas as pd

def build_f101(df_src: pd.DataFrame, year: int, month: int) -> pd.DataFrame:

    df = df_src.copy()



    df["실적"] = df["실적"].apply(_to_number)
    df["연도"] = df["연도"].astype(int)
    df["월"]   = df["월"].astype(int)



    # long → wide 피벗
    pivot = (
        df.pivot_table(
            index=["연도", "월", "구분1", "구분2"],
            columns="구분3",
            values="실적",
            aggfunc="sum",
            fill_value=0.0,
        )
        .reset_index()
    )

    for col in ["매출중량", "매출금액", "영업이익", "인원"]:
        if col not in pivot.columns:
            pivot[col] = 0.0


    #누적
    mask_ytd = (pivot["연도"] == year) & (pivot["월"] <= month)
    sub_ytd = pivot.loc[mask_ytd].copy()

    # YTD 기간에 포함된 서로 다른 월 개수 (데이터 있는 월 기준)
    n_months_ytd = (
        sub_ytd[["연도", "월"]]
        .drop_duplicates()["월"]
        .nunique()
    )

    # 연도 넘어갈때 문제 해결
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    mask_prev = (pivot["연도"] == prev_year) & (pivot["월"] == prev_month)
    sub_prev = pivot.loc[mask_prev].copy()

    # 당월
    mask_cur = (pivot["연도"] == year) & (pivot["월"] == month)
    sub_cur = pivot.loc[mask_cur].copy()
    


    def prepare_period(
        sub: pd.DataFrame,
        avg_monthly: bool = False,
        n_months: int | None = None,
    ):
        if sub.empty:
            return (
                pd.DataFrame(columns=["구분1", "구분2", "매출중량", "매출금액", "영업이익"]),
                {}
            )

        sales_df = (
            sub.groupby(["구분1", "구분2"], as_index=False)
               .agg(
                   매출중량=("매출중량", "sum"),
                   매출금액=("매출금액", "sum"),
                   영업이익=("영업이익", "sum"),
               )
        )

        # YTD 등: 월평균으로 변환 (합계 / 월수)
        if avg_monthly:
            if n_months is None or n_months <= 0:
                n_months = (
                    sub[["연도", "월"]]
                    .drop_duplicates()["월"]
                    .nunique()
                )
            if n_months > 0:
                for col in ["매출중량", "매출금액", "영업이익"]:
                    if col in sales_df.columns:
                        sales_df[col] = sales_df[col] / n_months

        # 인원: 정상 데이터 기준, 기간 평균
        staff_map = (
            sub[(sub["구분1"] == "정상") & (sub["인원"] > 0)]
            .groupby("구분2")["인원"]
            .mean()
            .to_dict()
        )
        return sales_df, staff_map

    # YTD는 월평균으로 계산
    sales_ytd,  staff_ytd  = prepare_period(sub_ytd, avg_monthly=True, n_months=n_months_ytd)
    # 전월/당월은 "그 달 한 달" 실적
    sales_prev, staff_prev = prepare_period(sub_prev)
    sales_cur,  staff_cur  = prepare_period(sub_cur)

    # ──────────────────────────────────
    # 4. 섹션/팀/기간별 지표 계산
    # ──────────────────────────────────
    def _metrics_for_period(
    sales_df: pd.DataFrame,
    staff_map: dict,
    section: str,      # 정상 / 매입매출 / 중계 / 총계 / 종합계
    team: str | None,  # None 이면 합계행
) -> dict:

        #중계 총계 통일
        if section == "중계":
            section = "총계"

        if sales_df.empty:
            qty = amt = op = 0.0
        else:
            if section in ("정상", "매입매출"):
                cond = (sales_df["구분1"] == section)
                if team is not None:
                    cond &= (sales_df["구분2"] == team)
                d = sales_df.loc[cond]

            elif section in ("총계", "종합계"):
                # 정상 + 매입매출 전체 합산
                if team is not None:
                    d = sales_df[sales_df["구분2"] == team]
                else:
                    d = sales_df

            else:
                raise ValueError(f"unknown section: {section}")

            qty = d["매출중량"].sum()
            amt = d["매출금액"].sum()
            op  = d["영업이익"].sum()

        # 인원: 항상 정상 기준 staff_map 사용
        if team is None:
            staff = sum(staff_map.values()) if staff_map else 0.0
        else:
            staff = staff_map.get(team, 0.0)

        unit_price     = amt / qty if qty != 0 else 0.0
        op_margin      = (op / amt * 100.0) if amt != 0 else 0.0
        percap_qty     = qty / staff if staff != 0 else 0.0
        percap_profit  = op  / staff if staff != 0 else 0.0

        return {
            "판매중량":       qty,
            "판매단가":       unit_price,
            "영업이익":       op,
            "영업이익율":     op_margin,
            "인원":          staff,
            "인당중량":       percap_qty,
            "인당영업이익":   percap_profit,
        }


    def make_row(section: str, team: str | None, label1: str, label2: str) -> dict:
        row = {"구분1": label1, "구분2": label2}

        for prefix, s_df, s_staff in [
            ("누적_", sales_ytd,  staff_ytd),
            ("전월_", sales_prev, staff_prev),
            ("당월_", sales_cur,  staff_cur),
        ]:
            m = _metrics_for_period(s_df, s_staff, section, team)
            for k, v in m.items():
                row[f"{prefix}{k}"] = v

        return row


    teams = ["선재영업팀", "봉강영업팀", "부산영업소", "대구영업소", "글로벌영업팀"]
    rows: list[dict] = []

    # 정상
    rows.append(make_row("정상", None, "정상", ""))
    for t in teams:
        rows.append(make_row("정상", t, "", t))

    # 매입매출
    rows.append(make_row("매입매출", None, "매입매출", ""))
    for t in teams:
        rows.append(make_row("매입매출", t, "", t))

    # 총계
    rows.append(make_row("중계", None, "총계", ""))
    for t in teams:
        rows.append(make_row("총계", t, "", t))

    # 총합계
    rows.append(make_row("총계", None, "총합계", ""))

    df_out = pd.DataFrame(rows)

    metrics_order = [
        "판매중량", "판매단가", "영업이익", "영업이익율",
        "인원", "인당중량", "인당영업이익",
    ]

    cols_order = ["구분1", "구분2"] + [
        f"{p}{m}"
        for p in ["누적_", "전월_", "당월_"]
        for m in metrics_order
    ]
    cols_order = [c for c in cols_order if c in df_out.columns]
    df_out = df_out[cols_order]


    def _round_1k(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1000.0, 0))

    def _round_1m(x):
        try:
            v = float(x)
        except (TypeError, ValueError):
            return x
        return int(round(v / 1_000_000.0, 0))

    weight_cols = [c for c in df_out.columns if ("판매중량" in c) or ("인당중량" in c)]
    profit_cols = [c for c in df_out.columns if ("영업이익" in c and "율" not in c)]
    staff_cols  = [c for c in df_out.columns if c.endswith("인원")]
    rate_cols   = [c for c in df_out.columns if c.endswith("영업이익율")]
    price_cols  = [c for c in df_out.columns if c.endswith("판매단가")]

    for c in weight_cols:
        df_out[c] = df_out[c].apply(_round_1k)

    for c in profit_cols:
        df_out[c] = df_out[c].apply(_round_1m)

    for c in staff_cols:
        df_out[c] = df_out[c].round(0).astype(int, errors="ignore")

    for c in rate_cols:
        df_out[c] = df_out[c].round(1)

    for c in price_cols:
        df_out[c] = df_out[c].round(0).astype(int, errors="ignore")

    return df_out
