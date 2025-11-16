"""
Vercel Serverless Function - 오피스텔 검색 API

이 함수는 Vercel에서 자동으로 /api/search 엔드포인트로 배포됩니다.
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

# =============================================================================
# 하드코딩된 데이터 (임시)
# =============================================================================

COMPANY_TO_STATIONS = {
    "강남역": ["강남역"],
    "판교": ["판교역", "정자역"],
    "정자역": ["정자역"],
    "삼성역": ["삼성역"],
    "선릉역": ["선릉역"],
}

MOCK_OFFICETEL_DATA = [
    {
        "id": "oft-001",
        "name": "선릉역 센트럴오피스텔",
        "address": "서울시 강남구 선릉로 123",
        "station": "선릉역",
        "walking_to_station": 3,
        "deposit": 1000,
        "monthly_rent": 55,
        "room_type": "원룸",
        "area_pyeong": 6.5,
        "build_year": 2020
    },
    {
        "id": "oft-002",
        "name": "삼성역 래미안오피스텔",
        "address": "서울시 강남구 테헤란로 456",
        "station": "삼성역",
        "walking_to_station": 5,
        "deposit": 1500,
        "monthly_rent": 70,
        "room_type": "원룸",
        "area_pyeong": 8.0,
        "build_year": 2019
    },
    {
        "id": "oft-003",
        "name": "역삼역 아크로오피스텔",
        "address": "서울시 강남구 역삼동 789",
        "station": "역삼역",
        "walking_to_station": 2,
        "deposit": 1200,
        "monthly_rent": 60,
        "room_type": "원룸",
        "area_pyeong": 7.0,
        "build_year": 2021
    },
    {
        "id": "oft-004",
        "name": "정자역 푸르지오오피스텔",
        "address": "경기도 성남시 분당구 정자동 101",
        "station": "정자역",
        "walking_to_station": 4,
        "deposit": 800,
        "monthly_rent": 45,
        "room_type": "원룸",
        "area_pyeong": 6.0,
        "build_year": 2018
    },
    {
        "id": "oft-005",
        "name": "미금역 현대오피스텔",
        "address": "경기도 성남시 분당구 미금동 202",
        "station": "미금역",
        "walking_to_station": 5,
        "deposit": 700,
        "monthly_rent": 40,
        "room_type": "원룸",
        "area_pyeong": 5.5,
        "build_year": 2017
    },
    {
        "id": "oft-006",
        "name": "수서역 SK허브오피스텔",
        "address": "서울시 강남구 수서동 303",
        "station": "수서역",
        "walking_to_station": 7,
        "deposit": 900,
        "monthly_rent": 50,
        "room_type": "투룸",
        "area_pyeong": 10.0,
        "build_year": 2022
    },
    {
        "id": "oft-007",
        "name": "강남구청역 힐스테이트오피스텔",
        "address": "서울시 강남구 논현동 404",
        "station": "강남구청역",
        "walking_to_station": 3,
        "deposit": 1100,
        "monthly_rent": 58,
        "room_type": "원룸",
        "area_pyeong": 7.5,
        "build_year": 2020
    },
    {
        "id": "oft-008",
        "name": "선정릉역 자이오피스텔",
        "address": "서울시 강남구 대치동 505",
        "station": "선정릉역",
        "walking_to_station": 6,
        "deposit": 950,
        "monthly_rent": 52,
        "room_type": "원룸",
        "area_pyeong": 6.8,
        "build_year": 2019
    },
]

MOCK_ROUTES = {
    ("선릉역", "강남역"): {
        "duration_minutes": 7,
        "transfers": 0,
        "fare": 1400,
        "route_summary": "2호선 직통",
        "detailed_steps": ["도보 3분 (오피스텔 → 선릉역)", "2호선 1정거장 (2분)", "도보 2분 (강남역 → 회사)"]
    },
    ("삼성역", "강남역"): {
        "duration_minutes": 5,
        "transfers": 0,
        "fare": 1400,
        "route_summary": "2호선 직통",
        "detailed_steps": ["도보 5분 (오피스텔 → 삼성역)", "2호선 1정거장 (2분)", "도보 2분 (강남역 → 회사)"]
    },
    ("역삼역", "강남역"): {
        "duration_minutes": 8,
        "transfers": 0,
        "fare": 1400,
        "route_summary": "2호선 직통",
        "detailed_steps": ["도보 2분 (오피스텔 → 역삼역)", "2호선 2정거장 (4분)", "도보 2분 (강남역 → 회사)"]
    },
    ("수서역", "강남역"): {
        "duration_minutes": 25,
        "transfers": 1,
        "fare": 1550,
        "route_summary": "3호선 → 2호선",
        "detailed_steps": ["도보 7분 (오피스텔 → 수서역)", "3호선 (수서 → 교대, 12분)", "환승 3분", "2호선 (교대 → 강남, 3분)"]
    },
    ("강남구청역", "강남역"): {
        "duration_minutes": 12,
        "transfers": 1,
        "fare": 1550,
        "route_summary": "분당선 → 신분당선",
        "detailed_steps": ["도보 3분 (오피스텔 → 강남구청역)", "분당선 (강남구청 → 선릉, 5분)", "환승 2분", "신분당선 (선릉 → 강남, 2분)"]
    },
    ("선정릉역", "강남역"): {
        "duration_minutes": 20,
        "transfers": 1,
        "fare": 1550,
        "route_summary": "분당선 → 2호선",
        "detailed_steps": ["도보 6분 (오피스텔 → 선정릉역)", "분당선 (선정릉 → 선릉, 8분)", "환승 3분", "2호선 (선릉 → 강남, 3분)"]
    },
    ("미금역", "정자역"): {
        "duration_minutes": 8,
        "transfers": 0,
        "fare": 1400,
        "route_summary": "신분당선 직통",
        "detailed_steps": ["도보 5분 (오피스텔 → 미금역)", "신분당선 2정거장 (3분)"]
    },
    ("정자역", "정자역"): {
        "duration_minutes": 4,
        "transfers": 0,
        "fare": 0,
        "route_summary": "도보",
        "detailed_steps": ["도보 4분 (오피스텔 → 회사)"]
    },
}

# =============================================================================
# Vercel Handler
# =============================================================================

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET 요청 처리"""

        # URL 파싱
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        # 쿼리 파라미터 추출
        company_location = query_params.get('company_location', [None])[0]
        max_commute_minutes = int(query_params.get('max_commute_minutes', [30])[0])
        max_transfers = int(query_params.get('max_transfers', [1])[0])

        budget_deposit_max = query_params.get('budget_deposit_max', [None])[0]
        if budget_deposit_max:
            budget_deposit_max = int(budget_deposit_max)

        budget_monthly_max = query_params.get('budget_monthly_max', [None])[0]
        if budget_monthly_max:
            budget_monthly_max = int(budget_monthly_max)

        room_type = query_params.get('room_type', [None])[0]

        # 유효성 검사
        if not company_location:
            self.send_error_response(400, "company_location is required")
            return

        if company_location not in COMPANY_TO_STATIONS:
            self.send_error_response(
                400,
                f"'{company_location}' is not supported. Available: {list(COMPANY_TO_STATIONS.keys())}"
            )
            return

        # 검색 실행
        results = self.search_officetel(
            company_location,
            max_commute_minutes,
            max_transfers,
            budget_deposit_max,
            budget_monthly_max,
            room_type
        )

        # 응답 반환
        self.send_json_response(200, {
            "success": True,
            "company_location": company_location,
            "total_count": len(results),
            "results": results
        })

    def search_officetel(self, company_location, max_commute_minutes, max_transfers,
                         budget_deposit_max, budget_monthly_max, room_type):
        """오피스텔 검색 로직"""

        company_stations = COMPANY_TO_STATIONS[company_location]
        results = []

        for officetel in MOCK_OFFICETEL_DATA:
            # 가격 필터
            if budget_deposit_max and officetel["deposit"] > budget_deposit_max:
                continue
            if budget_monthly_max and officetel["monthly_rent"] > budget_monthly_max:
                continue

            # 방 타입 필터
            if room_type and officetel["room_type"] != room_type:
                continue

            # 경로 찾기
            for company_station in company_stations:
                route_key = (officetel["station"], company_station)

                if route_key in MOCK_ROUTES:
                    route = MOCK_ROUTES[route_key]

                    # 시간 필터
                    if route["duration_minutes"] <= max_commute_minutes and route["transfers"] <= max_transfers:
                        result = officetel.copy()
                        result["commute"] = route
                        results.append(result)
                        break

        # 출퇴근 시간 순 정렬
        results.sort(key=lambda x: x["commute"]["duration_minutes"])

        return results

    def send_json_response(self, status_code, data):
        """JSON 응답 전송"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        response = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))

    def send_error_response(self, status_code, message):
        """에러 응답 전송"""
        self.send_json_response(status_code, {
            "success": False,
            "error": message
        })

    def do_OPTIONS(self):
        """CORS preflight 요청 처리"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
