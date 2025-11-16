"""
Estate-Hub 출퇴근 기반 오피스텔 추천 프로토타입

최소 기능:
- 하드코딩된 오피스텔 데이터
- 회사 위치 기반 검색 (간단한 필터링)
- 간단한 Web UI
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# FastAPI 앱 생성
app = FastAPI(
    title="Estate-Hub Commute Agent",
    description="출퇴근 기반 오피스텔 추천 프로토타입",
    version="0.1.0"
)

# CORS 설정 (프론트엔드에서 API 호출 가능하게)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 데이터 모델
# =============================================================================

class CommuteRoute(BaseModel):
    """출퇴근 경로 정보"""
    duration_minutes: int
    transfers: int
    fare: int
    route_summary: str
    detailed_steps: List[str]

class Officetel(BaseModel):
    """오피스텔 정보"""
    id: str
    name: str
    address: str
    station: str  # 가장 가까운 역
    walking_to_station: int  # 역까지 도보 시간 (분)
    deposit: int  # 보증금 (만원)
    monthly_rent: int  # 월세 (만원)
    room_type: str  # 원룸, 투룸 등
    area_pyeong: float  # 면적 (평)
    build_year: int  # 건축년도
    commute: Optional[CommuteRoute] = None  # 출퇴근 정보

class SearchRequest(BaseModel):
    """검색 요청"""
    company_location: str
    max_commute_minutes: Optional[int] = 30
    max_transfers: Optional[int] = 1
    budget_deposit_max: Optional[int] = None
    budget_monthly_max: Optional[int] = None
    room_type: Optional[str] = None

class SearchResponse(BaseModel):
    """검색 응답"""
    success: bool
    company_location: str
    total_count: int
    results: List[Officetel]

# =============================================================================
# 하드코딩된 데이터 (실제 DB 대신)
# =============================================================================

# 회사 위치 → 근처 역 매핑 (간단화)
COMPANY_TO_STATIONS = {
    "강남역": ["강남역"],
    "판교": ["판교역", "정자역"],
    "정자역": ["정자역"],
    "삼성역": ["삼성역"],
    "선릉역": ["선릉역"],
}

# 하드코딩된 오피스텔 데이터
MOCK_OFFICETEL_DATA = [
    # 강남역 근처
    Officetel(
        id="oft-001",
        name="선릉역 센트럴오피스텔",
        address="서울시 강남구 선릉로 123",
        station="선릉역",
        walking_to_station=3,
        deposit=1000,
        monthly_rent=55,
        room_type="원룸",
        area_pyeong=6.5,
        build_year=2020
    ),
    Officetel(
        id="oft-002",
        name="삼성역 래미안오피스텔",
        address="서울시 강남구 테헤란로 456",
        station="삼성역",
        walking_to_station=5,
        deposit=1500,
        monthly_rent=70,
        room_type="원룸",
        area_pyeong=8.0,
        build_year=2019
    ),
    Officetel(
        id="oft-003",
        name="역삼역 아크로오피스텔",
        address="서울시 강남구 역삼동 789",
        station="역삼역",
        walking_to_station=2,
        deposit=1200,
        monthly_rent=60,
        room_type="원룸",
        area_pyeong=7.0,
        build_year=2021
    ),

    # 판교/정자역 근처
    Officetel(
        id="oft-004",
        name="정자역 푸르지오오피스텔",
        address="경기도 성남시 분당구 정자동 101",
        station="정자역",
        walking_to_station=4,
        deposit=800,
        monthly_rent=45,
        room_type="원룸",
        area_pyeong=6.0,
        build_year=2018
    ),
    Officetel(
        id="oft-005",
        name="미금역 현대오피스텔",
        address="경기도 성남시 분당구 미금동 202",
        station="미금역",
        walking_to_station=5,
        deposit=700,
        monthly_rent=40,
        room_type="원룸",
        area_pyeong=5.5,
        build_year=2017
    ),

    # 가성비 옵션
    Officetel(
        id="oft-006",
        name="수서역 SK허브오피스텔",
        address="서울시 강남구 수서동 303",
        station="수서역",
        walking_to_station=7,
        deposit=900,
        monthly_rent=50,
        room_type="투룸",
        area_pyeong=10.0,
        build_year=2022
    ),
    Officetel(
        id="oft-007",
        name="강남구청역 힐스테이트오피스텔",
        address="서울시 강남구 논현동 404",
        station="강남구청역",
        walking_to_station=3,
        deposit=1100,
        monthly_rent=58,
        room_type="원룸",
        area_pyeong=7.5,
        build_year=2020
    ),
    Officetel(
        id="oft-008",
        name="선정릉역 자이오피스텔",
        address="서울시 강남구 대치동 505",
        station="선정릉역",
        walking_to_station=6,
        deposit=950,
        monthly_rent=52,
        room_type="원룸",
        area_pyeong=6.8,
        build_year=2019
    ),
]

# 역 간 경로 정보 (하드코딩)
MOCK_ROUTES = {
    # 강남역 기준
    ("선릉역", "강남역"): CommuteRoute(
        duration_minutes=7,
        transfers=0,
        fare=1400,
        route_summary="2호선 직통",
        detailed_steps=["도보 3분 (오피스텔 → 선릉역)", "2호선 1정거장 (2분)", "도보 2분 (강남역 → 회사)"]
    ),
    ("삼성역", "강남역"): CommuteRoute(
        duration_minutes=5,
        transfers=0,
        fare=1400,
        route_summary="2호선 직통",
        detailed_steps=["도보 5분 (오피스텔 → 삼성역)", "2호선 1정거장 (2분)", "도보 2분 (강남역 → 회사)"]
    ),
    ("역삼역", "강남역"): CommuteRoute(
        duration_minutes=8,
        transfers=0,
        fare=1400,
        route_summary="2호선 직통",
        detailed_steps=["도보 2분 (오피스텔 → 역삼역)", "2호선 2정거장 (4분)", "도보 2분 (강남역 → 회사)"]
    ),
    ("수서역", "강남역"): CommuteRoute(
        duration_minutes=25,
        transfers=1,
        fare=1550,
        route_summary="3호선 → 2호선",
        detailed_steps=["도보 7분 (오피스텔 → 수서역)", "3호선 (수서 → 교대, 12분)", "환승 3분", "2호선 (교대 → 강남, 3분)"]
    ),
    ("강남구청역", "강남역"): CommuteRoute(
        duration_minutes=12,
        transfers=1,
        fare=1550,
        route_summary="분당선 → 신분당선",
        detailed_steps=["도보 3분 (오피스텔 → 강남구청역)", "분당선 (강남구청 → 선릉, 5분)", "환승 2분", "신분당선 (선릉 → 강남, 2분)"]
    ),
    ("선정릉역", "강남역"): CommuteRoute(
        duration_minutes=20,
        transfers=1,
        fare=1550,
        route_summary="분당선 → 2호선",
        detailed_steps=["도보 6분 (오피스텔 → 선정릉역)", "분당선 (선정릉 → 선릉, 8분)", "환승 3분", "2호선 (선릉 → 강남, 3분)"]
    ),

    # 정자역 기준
    ("미금역", "정자역"): CommuteRoute(
        duration_minutes=8,
        transfers=0,
        fare=1400,
        route_summary="신분당선 직통",
        detailed_steps=["도보 5분 (오피스텔 → 미금역)", "신분당선 2정거장 (3분)"]
    ),
    ("정자역", "정자역"): CommuteRoute(
        duration_minutes=4,
        transfers=0,
        fare=0,
        route_summary="도보",
        detailed_steps=["도보 4분 (오피스텔 → 회사)"]
    ),
}

# =============================================================================
# API 엔드포인트
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지 - 간단한 UI"""
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Estate-Hub 출퇴근 오피스텔 찾기</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 40px;
            }
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            .search-card {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                font-weight: 600;
                margin-bottom: 8px;
                color: #333;
            }
            .form-group input, .form-group select {
                width: 100%;
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            .form-group input:focus, .form-group select:focus {
                outline: none;
                border-color: #667eea;
            }
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
            .btn-search {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .btn-search:hover {
                transform: translateY(-2px);
            }
            .btn-search:active {
                transform: translateY(0);
            }
            .results {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                display: none;
            }
            .results.show {
                display: block;
            }
            .result-header {
                margin-bottom: 30px;
            }
            .result-header h2 {
                color: #333;
                margin-bottom: 10px;
            }
            .result-header .count {
                color: #667eea;
                font-weight: 600;
            }
            .officetel-card {
                border: 2px solid #f0f0f0;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 20px;
                transition: all 0.3s;
            }
            .officetel-card:hover {
                border-color: #667eea;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
            }
            .officetel-header {
                display: flex;
                justify-content: space-between;
                align-items: start;
                margin-bottom: 16px;
            }
            .officetel-name {
                font-size: 1.3rem;
                font-weight: 600;
                color: #333;
            }
            .officetel-price {
                font-size: 1.2rem;
                color: #667eea;
                font-weight: 600;
            }
            .officetel-info {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 12px;
                margin-bottom: 16px;
            }
            .info-item {
                display: flex;
                align-items: center;
                color: #666;
            }
            .info-item .icon {
                margin-right: 8px;
            }
            .commute-section {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 16px;
                margin-top: 16px;
            }
            .commute-header {
                font-weight: 600;
                color: #333;
                margin-bottom: 12px;
            }
            .commute-time {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: 600;
                margin-bottom: 12px;
            }
            .route-steps {
                list-style: none;
                padding-left: 0;
            }
            .route-steps li {
                padding: 6px 0;
                color: #555;
                display: flex;
                align-items: center;
            }
            .route-steps li:before {
                content: "→";
                margin-right: 8px;
                color: #667eea;
                font-weight: bold;
            }
            .loading {
                text-align: center;
                padding: 40px;
                display: none;
            }
            .loading.show {
                display: block;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏢 Estate-Hub</h1>
                <p>출퇴근 시간 기반 오피스텔 찾기</p>
            </div>

            <div class="search-card">
                <form id="searchForm">
                    <div class="form-group">
                        <label for="company">🏢 회사 위치</label>
                        <select id="company" name="company_location" required>
                            <option value="">선택하세요</option>
                            <option value="강남역">강남역</option>
                            <option value="판교">판교</option>
                            <option value="정자역">정자역</option>
                            <option value="삼성역">삼성역</option>
                            <option value="선릉역">선릉역</option>
                        </select>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="commute_time">⏱️ 최대 출퇴근 시간 (분)</label>
                            <input type="number" id="commute_time" name="max_commute_minutes" value="30" min="10" max="120">
                        </div>
                        <div class="form-group">
                            <label for="room_type">🏠 방 타입</label>
                            <select id="room_type" name="room_type">
                                <option value="">전체</option>
                                <option value="원룸">원룸</option>
                                <option value="투룸">투룸</option>
                            </select>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="deposit">💰 최대 보증금 (만원)</label>
                            <input type="number" id="deposit" name="budget_deposit_max" placeholder="예: 1000">
                        </div>
                        <div class="form-group">
                            <label for="monthly">💸 최대 월세 (만원)</label>
                            <input type="number" id="monthly" name="budget_monthly_max" placeholder="예: 60">
                        </div>
                    </div>

                    <button type="submit" class="btn-search">🔍 오피스텔 찾기</button>
                </form>
            </div>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>검색 중...</p>
            </div>

            <div class="results" id="results">
                <div class="result-header">
                    <h2>검색 결과</h2>
                    <p class="count" id="resultCount"></p>
                </div>
                <div id="resultList"></div>
            </div>
        </div>

        <script>
            const form = document.getElementById('searchForm');
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const resultCount = document.getElementById('resultCount');
            const resultList = document.getElementById('resultList');

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                // 로딩 표시
                loading.classList.add('show');
                results.classList.remove('show');

                // 폼 데이터 수집
                const formData = new FormData(form);
                const params = new URLSearchParams();

                for (const [key, value] of formData.entries()) {
                    if (value) params.append(key, value);
                }

                try {
                    // API 호출
                    const response = await fetch(`/api/search?${params}`);
                    const data = await response.json();

                    // 로딩 숨김
                    loading.classList.remove('show');

                    if (data.success) {
                        // 결과 표시
                        displayResults(data);
                    } else {
                        alert('검색 실패: ' + data.error);
                    }
                } catch (error) {
                    loading.classList.remove('show');
                    alert('오류가 발생했습니다: ' + error.message);
                }
            });

            function displayResults(data) {
                resultCount.textContent = `${data.company_location} 기준 ${data.total_count}개 매물 발견`;

                if (data.total_count === 0) {
                    resultList.innerHTML = '<p>조건에 맞는 오피스텔이 없습니다. 조건을 변경해보세요.</p>';
                } else {
                    resultList.innerHTML = data.results.map(officetel => `
                        <div class="officetel-card">
                            <div class="officetel-header">
                                <div class="officetel-name">${officetel.name}</div>
                                <div class="officetel-price">보증금 ${officetel.deposit}만원 / 월세 ${officetel.monthly_rent}만원</div>
                            </div>

                            <div class="officetel-info">
                                <div class="info-item">
                                    <span class="icon">📍</span>
                                    ${officetel.address}
                                </div>
                                <div class="info-item">
                                    <span class="icon">🏠</span>
                                    ${officetel.room_type} ${officetel.area_pyeong}평
                                </div>
                                <div class="info-item">
                                    <span class="icon">🏗️</span>
                                    ${officetel.build_year}년 건축
                                </div>
                                <div class="info-item">
                                    <span class="icon">🚇</span>
                                    ${officetel.station} 도보 ${officetel.walking_to_station}분
                                </div>
                            </div>

                            ${officetel.commute ? `
                                <div class="commute-section">
                                    <div class="commute-header">🚇 출퇴근 경로 (${data.company_location})</div>
                                    <div class="commute-time">⏱️ 총 ${officetel.commute.duration_minutes}분 소요</div>
                                    <div style="margin-bottom: 8px;">
                                        <strong>${officetel.commute.route_summary}</strong> |
                                        환승 ${officetel.commute.transfers}회 |
                                        요금 ${officetel.commute.fare.toLocaleString()}원
                                    </div>
                                    <ul class="route-steps">
                                        ${officetel.commute.detailed_steps.map(step => `<li>${step}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                    `).join('');
                }

                results.classList.add('show');
            }
        </script>
    </body>
    </html>
    """

@app.get("/api/search", response_model=SearchResponse)
async def search_officetel(
    company_location: str,
    max_commute_minutes: int = 30,
    max_transfers: int = 1,
    budget_deposit_max: Optional[int] = None,
    budget_monthly_max: Optional[int] = None,
    room_type: Optional[str] = None
):
    """
    오피스텔 검색 API

    현재는 하드코딩된 데이터로 간단한 필터링만 수행
    """

    # 1. 회사 위치 유효성 검사
    if company_location not in COMPANY_TO_STATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"'{company_location}'는 지원하지 않는 위치입니다. 지원 위치: {list(COMPANY_TO_STATIONS.keys())}"
        )

    # 2. 회사 근처 역 목록
    company_stations = COMPANY_TO_STATIONS[company_location]

    # 3. 오피스텔 필터링 및 경로 정보 추가
    results = []

    for officetel in MOCK_OFFICETEL_DATA:
        # 가격 필터
        if budget_deposit_max and officetel.deposit > budget_deposit_max:
            continue
        if budget_monthly_max and officetel.monthly_rent > budget_monthly_max:
            continue

        # 방 타입 필터
        if room_type and officetel.room_type != room_type:
            continue

        # 경로 찾기
        route_found = False
        for company_station in company_stations:
            route_key = (officetel.station, company_station)

            if route_key in MOCK_ROUTES:
                route = MOCK_ROUTES[route_key]

                # 시간 필터
                if route.duration_minutes <= max_commute_minutes and route.transfers <= max_transfers:
                    # 경로 정보 추가
                    officetel_with_route = officetel.model_copy()
                    officetel_with_route.commute = route
                    results.append(officetel_with_route)
                    route_found = True
                    break

    # 4. 출퇴근 시간 순으로 정렬
    results.sort(key=lambda x: x.commute.duration_minutes if x.commute else 999)

    return SearchResponse(
        success=True,
        company_location=company_location,
        total_count=len(results),
        results=results
    )

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "version": "0.1.0"}

# =============================================================================
# 메인 실행
# =============================================================================

if __name__ == "__main__":
    print("""
    🏢 Estate-Hub 출퇴근 오피스텔 추천 프로토타입 시작!

    📍 접속 주소:
       - 웹 UI: http://localhost:8000
       - API 문서: http://localhost:8000/docs

    🔍 테스트 예시:
       http://localhost:8000/api/search?company_location=강남역&max_commute_minutes=30

    ⏹️  종료: Ctrl+C
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
