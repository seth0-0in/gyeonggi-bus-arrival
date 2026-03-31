import os
import sqlite3
import requests
import urllib.parse
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

API_KEY = os.environ.get("GYEONGGI_API_KEY")
DB_NAME = "bus_arrival.db"

STATION_API_URL = "https://apis.data.go.kr/6410000/busstationservice/v2/getBusStationListv2"
ARRIVAL_API_URL = "https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalListv2"
ROUTE_API_URL = "https://apis.data.go.kr/6410000/busrouteservice/v2/getBusRouteInfoItemv2"

name_cache = {}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bus_arrival (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT,
            route_id TEXT,
            predict_time1 INTEGER,
            location_no1 INTEGER,
            plate_no1 TEXT,
            query_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_route_name(route_id: str):
    if route_id in name_cache:
        return name_cache[route_id]
    
    url = f"{ROUTE_API_URL}?serviceKey={API_KEY}&routeId={route_id}&format=json"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            route_name = data.get("response", {}).get("msgBody", {}).get("busRouteInfoItem", {}).get("routeName")
            if route_name:
                name_cache[route_id] = f"{route_name}번"
                return f"{route_name}번"
    except Exception:
        pass
    return route_id 

def fetch_station_id_by_name(station_name: str):
    encoded_name = urllib.parse.quote(station_name)
    url = f"{STATION_API_URL}?serviceKey={API_KEY}&keyword={encoded_name}&format=json"
    
    print(f"\n--- [🔍 API 요청] 정류소명 검색: {station_name} ---")
    response = requests.get(url)
    
    if response.status_code != 200: 
        print(f"❌ [에러] 공공데이터포털 응답 거부 (상태코드: {response.status_code})")
        print(f"👉 이유: '경기도 버스정류소 조회' API 활용신청이 안 되어 있을 확률 99.9%!")
        return None
        
    try:
        data = response.json()
        station_list = data.get("response", {}).get("msgBody", {}).get("busStationList", [])
        if not station_list: 
            print("❌ [결과 없음] 해당 이름을 가진 정류소가 없습니다.")
            return None
            
        if isinstance(station_list, dict): 
            station_list = [station_list]
        
        s_id = str(station_list[0].get("stationId"))
        s_name = str(station_list[0].get("stationName"))
        name_cache[s_id] = s_name
        
        print(f"✅ [성공] '{s_name}'의 고유 ID는 '{s_id}' 입니다!")
        return s_id
    except Exception as e:
        print(f"❌ [데이터 파싱 에러]: {e}")
        return None

def fetch_bus_arrival_from_api(station_id: str):
    url = f"{ARRIVAL_API_URL}?serviceKey={API_KEY}&stationId={station_id}&format=json"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="OpenAPI 호출에 실패했습니다.")
        
    try:
        data = response.json()
        arrival_list = data.get("response", {}).get("msgBody", {}).get("busArrivalList", [])
        if not arrival_list: 
            return []
            
        if isinstance(arrival_list, dict): 
            arrival_list = [arrival_list]

        arrivals = []
        for item in arrival_list:
            arrival = {
                "station_id": str(station_id),
                "route_id": str(item.get("routeId", "")),
                "predict_time1": int(item.get("predictTime1", 0) or 0),
                "location_no1": int(item.get("locationNo1", 0) or 0),
                "plate_no1": str(item.get("plateNo1", ""))
            }
            arrivals.append(arrival)
        return arrivals
    except Exception as e:
        raise HTTPException(status_code=500, detail="데이터를 읽는 중 오류가 발생했습니다.")

def save_arrivals_to_db(arrivals: list):
    if not arrivals: return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for arr in arrivals:
        cursor.execute('''
            INSERT INTO bus_arrival (station_id, route_id, predict_time1, location_no1, plate_no1)
            VALUES (?, ?, ?, ?, ?)
        ''', (arr["station_id"], arr["route_id"], arr["predict_time1"], arr["location_no1"], arr["plate_no1"]))
    conn.commit()
    conn.close()

def get_arrivals_from_db(station_id: str, search_name: str = None):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT station_id, route_id, predict_time1, location_no1, plate_no1, query_time 
        FROM bus_arrival 
        WHERE station_id = ? 
        ORDER BY id DESC 
        LIMIT 20
    ''', (station_id,))
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        row_dict = dict(row)
        display_station = search_name if search_name else name_cache.get(station_id, station_id)
        row_dict["station_id"] = display_station
        row_dict["route_id"] = get_route_name(row_dict["route_id"])
        result.append(row_dict)
        
    return result

init_db()

@app.get("/api/arrival/id/{station_id}")
def get_arrival_by_id(station_id: str):
    try:
        arrivals = fetch_bus_arrival_from_api(station_id)
        if not arrivals: raise HTTPException(status_code=404, detail="도착 예정인 버스가 없습니다.")
        save_arrivals_to_db(arrivals)
        db_data = get_arrivals_from_db(station_id)
        return {"status": "success", "data": db_data}
    except HTTPException as he: raise he
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/arrival/name/{station_name}")
def get_arrival_by_name(station_name: str):
    try:
        station_id = fetch_station_id_by_name(station_name)
        if not station_id: raise HTTPException(status_code=404, detail="해당 이름의 정류소를 찾을 수 없습니다.")
        arrivals = fetch_bus_arrival_from_api(station_id)
        if arrivals: save_arrivals_to_db(arrivals)
        db_data = get_arrivals_from_db(station_id, search_name=station_name)
        return {"status": "success", "data": db_data}
    except HTTPException as he: raise he
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))