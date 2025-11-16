/**
 * Estate-Hub Frontend JavaScript
 * 서버리스 API를 호출하고 결과를 표시합니다.
 */

// API 엔드포인트 설정
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:3000'  // 로컬 개발
    : '';  // Vercel 배포 (same origin)

// DOM 요소
const form = document.getElementById('searchForm');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const resultCount = document.getElementById('resultCount');
const resultList = document.getElementById('resultList');

/**
 * 폼 제출 이벤트 핸들러
 */
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // 로딩 표시
    loading.classList.add('show');
    results.classList.remove('show');

    // 폼 데이터 수집
    const formData = new FormData(form);
    const params = new URLSearchParams();

    for (const [key, value] of formData.entries()) {
        if (value) {
            params.append(key, value);
        }
    }

    try {
        // API 호출
        const response = await fetch(`${API_BASE_URL}/api/search?${params}`);
        const data = await response.json();

        // 로딩 숨김
        loading.classList.remove('show');

        if (data.success) {
            // 결과 표시
            displayResults(data);
        } else {
            // 에러 표시
            showError(data.error || '검색에 실패했습니다.');
        }
    } catch (error) {
        loading.classList.remove('show');
        showError(`오류가 발생했습니다: ${error.message}`);
        console.error('Error:', error);
    }
});

/**
 * 검색 결과 표시
 */
function displayResults(data) {
    resultCount.textContent = `${data.company_location} 기준 ${data.total_count}개 매물 발견`;

    if (data.total_count === 0) {
        resultList.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #666;">
                <p style="font-size: 18px; margin-bottom: 10px;">😔 조건에 맞는 오피스텔이 없습니다.</p>
                <p>조건을 변경해보세요.</p>
            </div>
        `;
    } else {
        resultList.innerHTML = data.results.map(officetel => createOfficetelCard(officetel, data.company_location)).join('');
    }

    results.classList.add('show');
}

/**
 * 오피스텔 카드 HTML 생성
 */
function createOfficetelCard(officetel, companyLocation) {
    return `
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

            ${officetel.commute ? createCommuteSection(officetel.commute, companyLocation) : ''}
        </div>
    `;
}

/**
 * 출퇴근 정보 섹션 HTML 생성
 */
function createCommuteSection(commute, companyLocation) {
    return `
        <div class="commute-section">
            <div class="commute-header">🚇 출퇴근 경로 (${companyLocation})</div>
            <div class="commute-time">⏱️ 총 ${commute.duration_minutes}분 소요</div>
            <div class="commute-meta">
                <strong>${commute.route_summary}</strong> |
                환승 ${commute.transfers}회 |
                요금 ${commute.fare.toLocaleString()}원
            </div>
            <ul class="route-steps">
                ${commute.detailed_steps.map(step => `<li>${step}</li>`).join('')}
            </ul>
        </div>
    `;
}

/**
 * 에러 메시지 표시
 */
function showError(message) {
    resultList.innerHTML = `
        <div style="text-align: center; padding: 40px; color: #e74c3c;">
            <p style="font-size: 18px; margin-bottom: 10px;">❌ ${message}</p>
        </div>
    `;
    resultCount.textContent = '검색 실패';
    results.classList.add('show');
}

/**
 * 페이지 로드 시 초기화
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('Estate-Hub initialized');
    console.log('API Base URL:', API_BASE_URL);
});
