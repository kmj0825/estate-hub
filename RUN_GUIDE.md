# 🚀 Estate-Hub 서버리스 버전 실행 가이드

## 📁 프로젝트 구조

```
estate-hub/
├── api/                    # Vercel Serverless Functions
│   └── search.py          # 검색 API
├── frontend/               # 정적 프론트엔드 (GitHub Pages용)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── vercel.json            # Vercel 설정
├── package.json           # NPM 스크립트
├── requirements.txt       # Python 의존성
└── main.py               # 로컬 개발용 (선택사항)
```

---

## 🏃 로컬 실행 방법

### Option 1: Vercel CLI 사용 (추천)

```bash
# 1. Vercel CLI 설치
npm install -g vercel

# 2. 프로젝트 디렉토리로 이동
cd estate-hub

# 3. 로컬 개발 서버 실행
vercel dev
```

**접속:** http://localhost:3000

### Option 2: Python HTTP 서버 (간단한 방법)

프론트엔드만 테스트:

```bash
# frontend 폴더에서 실행
cd frontend
python -m http.server 8000
```

**접속:** http://localhost:8000

**주의:** 이 방법은 API가 작동하지 않습니다. 프론트엔드 UI만 확인 가능합니다.

---

## 🌐 Vercel 배포 방법

### 1단계: Vercel 계정 생성

https://vercel.com 에서 GitHub 계정으로 로그인

### 2단계: CLI로 배포

```bash
# 처음 배포
vercel

# 프로덕션 배포
vercel --prod
```

### 3단계: 자동 배포 설정

Vercel 대시보드에서:
1. GitHub 레포지토리 연결
2. 브랜치 자동 배포 설정
3. 푸시할 때마다 자동 배포됨

---

## 📄 GitHub Pages 배포 (프론트엔드만)

### 방법 1: frontend 폴더를 gh-pages 브랜치로

```bash
# frontend 폴더 내용을 gh-pages 브랜치로 복사
git subtree push --prefix frontend origin gh-pages
```

### 방법 2: GitHub Actions

`.github/workflows/deploy.yml` 생성:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./frontend
```

**주의:** GitHub Pages는 정적 파일만 호스팅합니다. API는 Vercel에 배포해야 합니다!

---

## 🔧 환경 변수 설정 (향후)

실제 API 연동 시 필요:

### 로컬 개발

`.env` 파일 생성:

```env
KAKAO_API_KEY=your_kakao_api_key
ODSAY_API_KEY=your_odsay_api_key
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Vercel 배포

Vercel 대시보드 → 프로젝트 → Settings → Environment Variables

---

## 🧪 API 테스트

### 로컬에서 테스트

```bash
# Vercel dev 실행 후
curl "http://localhost:3000/api/search?company_location=강남역&max_commute_minutes=30"
```

### 브라우저에서 테스트

http://localhost:3000/api/search?company_location=강남역&max_commute_minutes=30

---

## 📊 현재 기능

✅ **하드코딩된 데이터**
- 8개 오피스텔 매물
- 강남역, 판교, 정자역 등 5개 지역
- 실제 경로 정보 (지하철 노선, 환승, 요금)

✅ **필터링**
- 출퇴근 시간
- 보증금/월세
- 방 타입
- 환승 횟수

---

## 🚧 다음 단계

### Phase 2: 실제 API 연동
- [ ] 카카오맵 API (주소 → 좌표)
- [ ] ODsay API (경로 계산)
- [ ] Supabase 연동

### Phase 3: 데이터 수집
- [ ] 크롤러 수정 (APT → OFT)
- [ ] GitHub Actions 자동 크롤링
- [ ] 실제 오피스텔 데이터 수집

### Phase 4: AI 통합
- [ ] OpenAI Function Calling
- [ ] 자연어 질의응답
- [ ] 대화형 추천

---

## 🐛 문제 해결

### Vercel dev가 안 될 때

```bash
# Vercel CLI 재설치
npm uninstall -g vercel
npm install -g vercel

# 캐시 삭제
rm -rf .vercel
```

### CORS 에러

- Vercel dev: 자동 처리됨
- 로컬 Python 서버: 프론트엔드와 API를 같은 포트에서 실행

### API 응답 없음

1. `vercel dev` 실행 확인
2. `api/search.py` 파일 존재 확인
3. 브라우저 콘솔에서 에러 확인

---

## 📞 도움말

- Vercel 문서: https://vercel.com/docs
- GitHub Pages: https://pages.github.com
- 이슈 리포팅: GitHub Issues

---

**현재 버전:** 0.1.0 (프로토타입)
**마지막 업데이트:** 2025-11-16
