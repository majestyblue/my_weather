import os
import math
import json
from datetime import datetime, timedelta
import xmltodict
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my_korea_weather")

API_KEY = os.environ.get('KOREA_WEATHER_API_KEY')
URL = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'

def get_datetime():
    current_date = datetime.now().date().strftime("%Y%m%d")
    current_time = datetime.now()
    if current_time.minute < 40: # API 제공 시간에 맞춰 40분으로 조정
        current_time = current_time - timedelta(hours=1)
    current_time = current_time.strftime("%H%M")
    return current_date, current_time

def convert_to_grid(lat, lon):
    RE = 6371.00877; GRID = 5.0; SLAT1 = 30.0; SLAT2 = 60.0
    OLON = 126.0; OLAT = 38.0; XO = 43; YO = 136
    DEGRAD = math.pi / 180.0
    slat1 = SLAT1 * DEGRAD; slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD; olat = OLAT * DEGRAD
    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = RE / GRID * sf / (ro ** sn)
    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = RE / GRID * sf / (ra ** sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi: theta -= 2 * math.pi
    if theta < -math.pi: theta += 2 * math.pi
    theta *= sn
    x = ra * math.sin(theta) + XO
    y = ro - ra * math.cos(theta) + YO
    return {'x': int(x + 0.5), 'y': int(y + 0.5)}

# --- 개선 사항 2: nx, ny를 직접 인자로 받도록 변경 ---
async def st_forecast(api_key, url, nx, ny):
    """
    지정된 격자 좌표(nx, ny)의 초단기 실황을 비동기 방식으로 요청하고
    응답을 딕셔너리로 반환합니다.
    """
    date, time = get_datetime()
    parameters = {
        'serviceKey': api_key,
        'numOfRows': 30,
        'pageNo': 1,
        'dataType': 'XML',
        'base_date': date,
        'base_time': time,
        'nx': nx,
        'ny': ny
    }

    # httpx의 비동기 클라이언트를 사용합니다.
    async with httpx.AsyncClient() as client:
        try:
            # client.get은 await 키워드가 필요한 코루틴(coroutine)입니다.
            response = await client.get(url, params=parameters, timeout=10)
            
            # 응답 상태 코드가 200(OK)이 아닐 경우 예외를 발생시킵니다.
            response.raise_for_status()
            
            # xmltodict는 동기 함수이므로 await 없이 그대로 사용합니다.
            return xmltodict.parse(response.text)
        
        except httpx.HTTPStatusError as e:
            # HTTP 상태 코드 오류 (4xx, 5xx 등)
            return {"error": f"API 서버 오류: 상태 코드 {e.response.status_code}"}
        except httpx.RequestError as e:
            # 네트워크 연결 오류, 타임아웃 등
            return {"error": f"API 요청 실패: {e}"}


def describe_wind_components(uuu: float, vvv: float) -> dict:
    if uuu > 0: uuu_description = f"동풍 {uuu}m/s"
    elif uuu < 0: uuu_description = f"서풍 {abs(uuu)}m/s"
    else: uuu_description = "없음"
    if vvv > 0: vvv_description = f"북풍 {vvv}m/s"
    elif vvv < 0: vvv_description = f"남풍 {abs(vvv)}m/s"
    else: vvv_description = "없음"
    return {"동서성분": uuu_description, "남북성분": vvv_description}

def format_rainfall(rn1_value: float) -> str:
    if rn1_value < 0.1: return "강수없음"
    elif rn1_value < 1.0: return "1mm 미만"
    elif rn1_value < 30.0: return f"{rn1_value}mm"
    elif rn1_value < 50.0: return "30.0~50.0mm"
    return "50.0mm 이상"

def format_wind_direction(degree: float) -> str:
    directions = ["북", "북북동", "북동", "동북동", "동", "동남동", "남동", "남남동",
                  "남", "남남서", "남서", "서남서", "서", "서북서", "북서", "북북서", "북"]
    index = int((degree + 11.25) / 22.5) % 16 # 360도(0도) 처리를 위해 나머지 연산 추가
    return directions[index]

def format_wind_speed(wsd_value: float) -> str:
    if wsd_value < 4: description = "바람이 약하게 느껴집니다."
    elif wsd_value < 9: description = "나뭇잎이 흔들리는 정도의 바람입니다."
    elif wsd_value < 14: description = "나무가지가 흔들리는 정도의 강한 바람입니다."
    else: description = "나무 전체가 흔들릴 정도의 매우 강한 바람입니다."
    return f"{wsd_value}m/s, {description}"

def parse_ultra_short_term_weather(api_response: dict) -> dict:
    # --- 개선 사항 4: 가독성을 위한 category_map 키 이름 변경 ---
    category_map = {'T1H': '기온(℃)', 'RN1': '1시간 강수량', 'UUU': '동서바람성분(m/s)',
                    'VVV': '남북바람성분(m/s)', 'REH': '습도(%)', 'PTY': '강수형태',
                    'VEC': '풍향', 'WSD': '풍속'}
    pty_map = {'0': '없음', '1': '비', '2': '비/눈', '3': '눈', '5': '빗방울', '6': '빗방울/눈날림', '7': '눈날림'}

    if "error" in api_response: return api_response
    try:
        items = api_response['response']['body']['items']['item']
    except (KeyError, TypeError):
        return {"error": "API 응답 데이터 형식이 올바르지 않습니다."}

    weather_data = {'발표일자': items[0]['baseDate'], '발표시각': items[0]['baseTime']}
    
    for item in items:
        category, value = item['category'], item['obsrValue']
        if category not in category_map: continue
        
        key_name = category_map[category]
        try:
            if category == 'RN1': weather_data[key_name] = format_rainfall(float(value))
            elif category == 'PTY' and value in pty_map: weather_data[key_name] = pty_map[value]
            elif category == 'WSD': weather_data[key_name] = format_wind_speed(float(value))
            elif category == 'VEC': weather_data[key_name] = format_wind_direction(float(value))
            else: weather_data[key_name] = float(value)
        except (ValueError, TypeError):
            weather_data[key_name] = value

    if '동서바람성분(m/s)' in weather_data and '남북바람성분(m/s)' in weather_data:
        uuu = weather_data.pop('동서바람성분(m/s)')
        vvv = weather_data.pop('남북바람성분(m/s)')
        weather_data.update(describe_wind_components(uuu, vvv))
    
    return weather_data


@mcp.tool()
async def get_current_weather(lat: float, lon: float) -> str:
    """지정된 위도와 경도를 기반으로 현재 날씨 정보를 조회하여 정리된 문자열로 반환합니다."""
    if not API_KEY or API_KEY == '<your_api_key>':
        return "오류: 서버에 API 키가 설정되지 않았습니다. 관리자에게 문의하세요."

    grid = convert_to_grid(lat, lon)
    nx, ny = grid['x'], grid['y']
    
    my_response = await st_forecast(API_KEY, URL, nx, ny) # 'await' 추가!
    parsed_weather = parse_ultra_short_term_weather(my_response)

    if 'error' in parsed_weather:
        return f"날씨 정보를 가져오는 데 실패했습니다: {parsed_weather['error']}"
    
    date_str = parsed_weather.get('발표일자', '00000000')
    time_str = parsed_weather.get('발표시각', '0000')
    
    result = f"""# 현재 날씨 정보 (위도: {lat}, 경도: {lon})
- 기준 시각: {date_str[:4]}년 {date_str[4:6]}월 {date_str[6:]}일 {time_str[:2]}시 {time_str[2:]}분
- 격자 좌표: X={nx}, Y={ny}

## 기상 상태
- 기온: {parsed_weather.get('기온(℃)', 'N/A')}℃
- 습도: {parsed_weather.get('습도(%)', 'N/A')}%
- 강수 형태: {parsed_weather.get('강수형태', 'N/A')}
- 1시간 강수량: {parsed_weather.get('1시간 강수량', 'N/A')}

## 바람 정보
- 풍향: {parsed_weather.get('풍향', 'N/A')}
- 풍속: {parsed_weather.get('풍속', 'N/A')}
- 동서성분: {parsed_weather.get('동서성분', 'N/A')}
- 남북성분: {parsed_weather.get('남북성분', 'N/A')}
"""
    return result

if __name__ == "__main__":
    print("MCP 날씨 정보 서버 시작... (종료하려면 Ctrl+C)")
    print("테스트 메시지를 JSON-RPC 형식으로 입력하세요.")
    mcp.run(transport='stdio')