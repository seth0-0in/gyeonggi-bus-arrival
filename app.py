import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://localhost:8000/api/arrival"

def fetch_data(search_type, keyword):
    if search_type == "정류소 ID":
        url = f"{API_BASE_URL}/id/{keyword}"
    else:
        url = f"{API_BASE_URL}/name/{keyword}"
        
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            error_msg = response.json().get("detail", "데이터를 불러오는 중 오류가 발생했습니다.")
            st.error(error_msg)
            return None
    except requests.exceptions.RequestException:
        st.error("백엔드 서버(FastAPI)와 연결할 수 없습니다. 서버 실행 여부를 확인해주세요.")
        return None

def main():
    st.title("🚌 경기도 버스 도착 정보 조회")
    st.write("공공데이터포털 OpenAPI를 활용한 버스 도착 정보 시스템입니다.")

    search_type = st.radio("검색 기준을 선택하세요", ("정류소명", "정류소 ID"))
    keyword = st.text_input(f"{search_type}을(를) 입력하세요:")

    if st.button("조회하기"):
        if not keyword.strip():
            st.warning("검색어를 입력해주세요.")
            return

        with st.spinner("데이터를 가져오는 중입니다..."):
            raw_data = fetch_data(search_type, keyword)

        if raw_data:
            df = pd.DataFrame(raw_data)
            
            df.rename(columns={
                "station_id": "정류소 ID",
                "route_id": "노선 ID",
                "predict_time1": "도착예정(분)",
                "location_no1": "남은 정류장(개)",
                "plate_no1": "차량번호",
                "query_time": "조회시간"
            }, inplace=True)

            st.success(f"총 {len(df)}건의 버스 도착 정보를 찾았습니다.")

            sort_col = st.selectbox("정렬 기준", ["도착예정(분)", "남은 정류장(개)"])
            df = df.sort_values(by=sort_col)

            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 CSV 다운로드",
                data=csv,
                file_name=f"bus_arrival_{keyword}.csv",
                mime="text/csv",
            )

if __name__ == "__main__":
    main()