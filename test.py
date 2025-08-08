from datetime import datetime, timedelta
import requests, xmltodict, json, math

API_KEY = 'DQSVAXjwbENj0h9yi6VcguroQGtT/R397C1GzzL0LuSKAwnSJZG3ziyKOfKJHqVls6zCcvqG/oVNnmmUs68/2A=='
URL = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'

def get_datetime():
    current_date = datetime.now().date().strftime("%Y%m%d")
    current_time = datetime.now()

    if current_time.minute < 10:
        current_time = current_time - timedelta(hours=1)

    current_time = current_time.strftime("%H%S")
    return current_date, current_time

def convert_to_grid(lat, lon):
    """
    위도, 경도를 기상청 격자 x, y 좌표로 변환하는 함수
    (LCC DFS GRID C Program C 소스 기반)

    Args:
        lat (float): 위도
        lon (float): 경도

    Returns:
        dict: x, y 격자 좌표를 담은 딕셔너리 (예: {'x': 60, 'y': 127})
    """
    # LCC DFS GRID C 프로그램에서 사용하는 상수 정의
    RE = 6371.00877  # 지구 반경(km)
    GRID = 5.0      # 격자 간격(km)
    SLAT1 = 30.0    # 표준 위도 1
    SLAT2 = 60.0    # 표준 위도 2
    OLON = 126.0    # 기준점 경도
    OLAT = 38.0     # 기준점 위도
    XO = 43         # 기준점 X좌표 (210/5)
    YO = 136        # 기준점 Y좌표 (675/5)
    
    DEGRAD = math.pi / 180.0
    
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = RE / GRID * sf / (ro ** sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = RE / GRID * sf / (ra ** sn)
    
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2 * math.pi
    if theta < -math.pi:
        theta += 2 * math.pi
    
    theta *= sn
    
    x = ra * math.sin(theta) + XO
    y = ro - ra * math.cos(theta) + YO
    
    nx = int(x + 0.5)
    ny = int(y + 0.5)

    return {'x': nx, 'y': ny}


def st_forecast(api_key, url, lat, lon): # lat, lon 인자 추가
    """
    지정된 위도, 경도의 위치에 대한 초단기 실황을 요청하고 응답을 딕셔너리로 반환합니다.
    """
    date, time = get_datetime()
    
    # 위도, 경도를 격자 좌표로 변환
    grid = convert_to_grid(lat, lon)
    nx = grid['x']
    ny = grid['y']
    
    print(f"조회 위치: 위도={lat}, 경도={lon} -> 격자좌표: nx={nx}, ny={ny}") # 확인용 출력

    parameters = {'serviceKey': api_key,
                  'numOfRows': 30,
                  'pageNo': 1,
                  'dataType': 'XML',
                  'base_date': date,
                  'base_time': time,
                  'nx': nx,
                  'ny': ny}
    
    request = requests.get(url, params=parameters)
    xml_data = request.text
    dict_data = xmltodict.parse(xml_data)

    return dict_data

def describe_wind_components(uuu: float, vvv: float) -> dict:
    """
    동서(UUU), 남북(VVV) 바람 성분 값을 받아 각각을 직관적인 설명으로 변환합니다.

    Args:
        uuu (float): 동서바람성분 값 (m/s). 양수(+)는 동풍, 음수(-)는 서풍.
        vvv (float): 남북바람성분 값 (m/s). 양수(+)는 북풍, 음수(-)는 남풍.

    Returns:
        dict: 각 성분을 설명하는 문자열이 담긴 딕셔너리.
              예: {'동서성분': '서풍 0.9 m/s', '남북성분': '북풍 0.5 m/s'}
    """
    
    # 1. 동서바람성분(UUU) 처리
    if uuu > 0:
        # 양수일 경우 '동풍'으로 표기
        uuu_description = f"동풍 {uuu}"
    elif uuu < 0:
        # 음수일 경우 '서풍'으로 표기하고, 세기는 양수로 표현 (abs 함수 사용)
        uuu_description = f"서풍 {abs(uuu)}"
    else:
        # 0일 경우 바람 성분이 없음을 표기
        uuu_description = "없음"

    # 2. 남북바람성분(VVV) 처리
    if vvv > 0:
        # 양수일 경우 '북풍'으로 표기
        vvv_description = f"북풍 {vvv}"
    elif vvv < 0:
        # 음수일 경우 '남풍'으로 표기하고, 세기는 양수로 표현 (abs 함수 사용)
        vvv_description = f"남풍 {abs(vvv)}"
    else:
        # 0일 경우 바람 성분이 없음을 표기
        vvv_description = "없음"

    # 3. 처리된 두 설명을 딕셔너리 형태로 묶어서 반환
    return {
        "동서바람성분(m/s)": uuu_description,
        "남북바람성분(m/s)": vvv_description
    }

def format_rainfall(rn1_value: float) -> str:
    """
    기상청 API의 강수량(RN1) 숫자 값을 예보 기준에 맞는 문자열로 변환합니다.

    Args:
        rn1_value (float): 1시간 강수량(mm) 값.

    Returns:
        str: 변환된 강수량 정보 문자열.
             예: '강수없음', '1mm 미만', '6.2mm', '30.0~50.0mm', '50.0mm 이상'
    """
    if rn1_value < 0.1:  # 0을 포함한 0.1 미만의 값
        return "강수없음"
    elif rn1_value < 1.0:  # 0.1 이상 1.0 미만
        return "1mm 미만"
    elif rn1_value < 30.0: # 1.0 이상 30.0 미만
        return f"{rn1_value}mm"
    elif rn1_value < 50.0: # 30.0 이상 50.0 미만
        return "30.0~50.0mm"
    elif rn1_value >= 50.0: # 50.0 이상
        return "50.0mm 이상"
    else:
        # 예상치 못한 값이 들어올 경우를 대비
        return "정보 확인 필요"

def format_wind_direction(degree: float) -> str:
    """
    풍향 각도(degree) 값을 16방위 한글 표기로 변환합니다.

    Args:
        degree (float): 풍향 값 (0~360).

    Returns:
        str: 변환된 16방위 한글 문자열 (예: '북북서', '남남동').
    """
    # 16방위를 순서대로 리스트에 저장
    directions = [
        "북", "북북동", "북동", "동북동", "동", "동남동", "남동", "남남동",
        "남", "남남서", "남서", "서남서", "서", "서북서", "북서", "북북서", "북"
    ]

    # 제공된 변환식 적용
    # (degree + 11.25) / 22.5 -> 22.5 * 0.5 = 11.25
    index = int((degree + 11.25) / 22.5)
    
    # 계산된 인덱스에 해당하는 방위 반환
    return directions[index]

def format_wind_speed(wsd_value: float) -> str:
    """
    풍속(WSD) 숫자 값을 기준에 맞는 설명 문자열로 변환합니다.

    Args:
        wsd_value (float): 풍속(m/s) 값.

    Returns:
        str: 변환된 풍속 정보 문자열.
             예: "풍속: 4.5m/s, 나뭇잎이 조금 흔들릴 정도로 바람이 약간 강함."
    """
    if wsd_value < 4:
        description = "감지할 수 없을 정도로 바람이 약함."
    elif wsd_value < 9:
        description = "나뭇잎이 조금 흔들릴 정도로 바람이 약간 강함."
    elif wsd_value < 14:
        description = "나무가지가 가볍게 흔들릴 정도로 바람이 강함."
    else: # 14 이상
        description = "작은 나무 전체가 흔들릴 정도로 바람이 매우 강함."
    
    return f"{wsd_value}m/s, {description}"

def parse_ultra_short_term_weather(api_response: dict) -> dict:
    """
    기상청 초단기 실황조회 API 응답을 파싱하여 사용하기 쉬운 딕셔너리로 변환합니다.

    Args:
        api_response (dict): API로부터 받은 전체 응답 딕셔너리.

    Returns:
        dict: 처리된 날씨 정보와 발표 시각을 담은 딕셔너리.
              예: {'발표일자': '20250805', '발표시각': '2000', '기온(℃)': 26.2, ...}
    """

    # 1. API 코드값 정보를 바탕으로 코드와 한글명, 단위를 매핑하는 딕셔너리를 만듭니다.
    category_map = {
        'T1H': '기온(℃)',
        'RN1': '1시간 강수량(mm)',
        'UUU': '동서바람성분(m/s)',
        'VVV': '남북바람성분(m/s)',
        'REH': '습도(%)',
        'PTY': '강수형태(코드값)',
        'VEC': '풍향(deg)',
        'WSD': '풍속'
    }
    
    # 강수형태(PTY) 코드에 대한 설명 추가
    pty_map = {
        '0': '없음',
        '1': '비',
        '2': '비/눈',
        '3': '눈',
        '5': '빗방울',
        '6': '빗방울/눈날림',
        '7': '눈날림'
    }

    try:
        # 2. API 응답 구조를 따라 실제 데이터가 있는 item 리스트에 접근합니다.
        items = api_response['response']['body']['items']['item']
    except (KeyError, TypeError):
        # 응답 구조가 예상과 다를 경우 오류 메시지를 포함한 결과를 반환합니다.
        return {"error": "올바른 형식의 API 응답이 아닙니다."}

    # 3. 결과를 저장할 새로운 딕셔너리를 생성합니다.
    weather_data = {}

    # 발표일자와 시각은 모든 항목에 동일하게 포함되므로 첫 번째 항목에서 가져와 저장합니다.
    if items:
        weather_data['발표일자'] = items[0]['baseDate']
        weather_data['발표시각'] = items[0]['baseTime']

    # 4. item 리스트를 순회하며 데이터를 추출하고 새로운 딕셔너리에 저장합니다.
    for item in items:
        category = item['category']
        value = item['obsrValue']

        # 매핑 테이블에 있는 카테고리인 경우에만 처리합니다.
        if category in category_map:
            # 카테고리 코드를 한글명으로 변환
            key_name = category_map[category]

            if category == 'RN1':
                try:
                    rn1_float = float(value)
                    # format_rainfall 함수를 호출하여 문자열로 변환
                    weather_data[key_name] = format_rainfall(rn1_float)
                except ValueError:
                    weather_data[key_name] = "강수없음"
            
            # 강수형태(PTY)의 경우, 코드값을 실제 의미로 변환해줍니다.
            elif category == 'PTY' and value in pty_map:
                weather_data[key_name] = pty_map[value]
            
            elif category == 'WSD':
                try:
                    wsd_float = float(value)
                    # format_wind_speed 함수를 호출하여 문자열로 변환
                    weather_data[key_name] = format_wind_speed(wsd_float)
                except ValueError:
                    weather_data[key_name] = "풍속 정보 확인 불가"

            elif category == 'VEC':
                try:
                    # format_wind_direction 함수를 호출하여 한글 방위로 변환
                    weather_data[key_name] = format_wind_direction(float(value))
                except ValueError:
                    weather_data[key_name] = "풍향 정보 확인 불가"

            else:
                try:
                    weather_data[key_name] = float(value)
                except ValueError:
                    weather_data[key_name] = value

    # 파싱된 데이터에서 UUU, VVV 값을 확인하고 변환을 진행합니다.
    if '동서바람성분(m/s)' in weather_data and '남북바람성분(m/s)' in weather_data:
        uuu_val = weather_data['동서바람성분(m/s)']
        vvv_val = weather_data['남북바람성분(m/s)']
        
        # 내부 함수를 호출하여 설명이 포함된 딕셔너리를 받습니다.
        wind_descriptions = describe_wind_components(uuu_val, vvv_val)
        
        # 기존의 숫자 데이터를 제거합니다.
        del weather_data['동서바람성분(m/s)']
        del weather_data['남북바람성분(m/s)']
        
        # 새로 생성된 설명을 추가합니다.
        weather_data.update(wind_descriptions)

    return weather_data


# --- 테스트 ---
# 대전광역시 중구 태평동 위도,경도
latitude = 36.326824624904
longitude = 127.39544700311

my_response = st_forecast(API_KEY, URL, latitude, longitude)
parsed_weather = parse_ultra_short_term_weather(my_response)

print(json.dumps(parsed_weather, indent=4, ensure_ascii=False))