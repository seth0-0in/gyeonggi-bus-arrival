# 🚌 경기도 버스 도착 정보 조회 서비스

FastAPI와 Streamlit, 공공데이터포털 OpenAPI를 활용하여 경기도 버스 도착 정보를 실시간으로 조회하고 SQLite에 저장하는 서비스입니다.

## 🛠 기술 스택
- Backend: FastAPI, Python, SQLite
- Frontend: Streamlit
- Data: 공공데이터포털 OpenAPI (경기도_버스도착정보 조회, 경기도_버스정류소 조회, 경기도_버스노선 조회)

## 🚀 실행 방법
1. 패키지 설치: `pip install -r requirements.txt`
2. 환경변수 설정: 루트 디렉토리에 `.env` 파일을 만들고 `GYEONGGI_API_KEY=본인키` 입력
3. 백엔드 실행: `uvicorn main:app --reload`
4. 프론트엔드 실행: `streamlit run app.py`
