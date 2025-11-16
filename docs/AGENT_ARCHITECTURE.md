# AI 에이전트 아키텍처 상세 설계

## 📋 목차
1. [에이전트 구현 방식 비교](#1-에이전트-구현-방식-비교)
2. [Option A: LangGraph 기반 에이전트](#2-option-a-langgraph-기반-에이전트)
3. [Option B: OpenAI Function Calling 기반](#3-option-b-openai-function-calling-기반)
4. [의도 분석 시스템](#4-의도-분석-시스템)
5. [툴/함수 상세 설계](#5-툴함수-상세-설계)
6. [상태 관리 전략](#6-상태-관리-전략)
7. [최종 추천 및 구현 가이드](#7-최종-추천-및-구현-가이드)

---

## 1. 에이전트 구현 방식 비교

### 1.1 비교표

| 항목 | **LangGraph** | **OpenAI Function Calling** |
|------|---------------|----------------------------|
| **복잡도** | 높음 (그래프 설계 필요) | 낮음 (함수 정의만) |
| **유연성** | ⭐⭐⭐⭐⭐ (복잡한 워크플로우 가능) | ⭐⭐⭐ (단순 ReAct 패턴) |
| **비용** | 높음 (LLM 호출 많음) | 낮음 (최소한의 호출) |
| **응답 속도** | 느림 (멀티스텝) | 빠름 (1-2회 호출) |
| **상태 관리** | 내장 (StateGraph) | 직접 구현 필요 |
| **디버깅** | 어려움 | 쉬움 |
| **서버리스 적합성** | ⭐⭐ (상태 관리 복잡) | ⭐⭐⭐⭐⭐ |
| **학습 곡선** | 가파름 | 완만함 |

### 1.2 사용 사례별 추천

#### **LangGraph가 적합한 경우**
```
✓ 복잡한 멀티스텝 워크플로우
  예: "회사 찾기 → 역 찾기 → 경로 계산 → 오피스텔 검색 → 가격 분석 → 추천"
✓ 조건부 분기가 많은 경우
  예: "데이터 없으면 대안 제시, 있으면 상세 분석"
✓ 사람의 승인이 필요한 단계가 있는 경우
✓ 복잡한 상태 추적이 필요한 경우
```

#### **OpenAI Function Calling이 적합한 경우**
```
✓ 단순 질의응답 + 함수 호출
  예: "회사 → 오피스텔 추천" (1-2단계)
✓ 서버리스 환경 (Vercel Functions)
✓ 빠른 응답 속도 필요
✓ 비용 최소화
✓ 간단한 프로토타입
```

### 1.3 우리 프로젝트 분석

**현재 요구사항:**
1. 사용자: "강남역 회사 다니는데 30분 안에 출근 가능한 원룸 찾아줘"
2. 시스템: 회사 위치 확인 → 경로 계산 → 오피스텔 검색 → 결과 반환

**복잡도 분석:**
- 단계: 3-4단계 (중간)
- 분기: 적음
- 상태: 대화 컨텍스트만 필요

**결론: OpenAI Function Calling이 더 적합 (단, LangGraph도 함께 설계)**

---

## 2. Option A: LangGraph 기반 에이전트

### 2.1 그래프 구조 설계

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────────┐
                    │  의도 분석 노드  │
                    │ (Intent Parser) │
                    └──────┬──────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
    │  검색 요청   │ │  경로 조회  │ │  일반 질문  │
    │   (Search)  │ │  (Route)   │ │   (QA)     │
    └──────┬──────┘ └─────┬──────┘ └─────┬──────┘
           │               │               │
    ┌──────▼──────────────┐│               │
    │ 회사 위치 확인 노드  ││               │
    │ (Location Finder)   ││               │
    └──────┬──────────────┘│               │
           │                │               │
    ┌──────▼──────────────┐│               │
    │ 경로 계산 노드       ││               │
    │ (Route Calculator)  ││               │
    └──────┬──────────────┘│               │
           │                │               │
    ┌──────▼──────────────┐│               │
    │ 오피스텔 검색 노드   ││               │
    │ (Officetel Search)  ││               │
    └──────┬──────────────┘│               │
           │                │               │
    ┌──────▼──────────────┐│               │
    │ 결과 정리 노드       ││               │
    │ (Result Formatter)  ││               │
    └──────┬──────────────┘│               │
           │                │               │
           └────────────────┴───────────────┘
                           │
                    ┌──────▼──────┐
                    │  응답 생성   │
                    │  (Response)  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │     END     │
                    └─────────────┘
```

### 2.2 상태 스키마 정의

```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """에이전트 상태 정의"""

    # 대화 메시지
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # 의도 분류
    intent: str  # "search_officetel", "get_route", "compare", "general_qa"

    # 사용자 조건
    company_location: str | None  # 회사 위치
    company_coords: tuple[float, float] | None  # 회사 좌표 (lat, lng)
    max_commute_minutes: int | None  # 최대 출퇴근 시간
    max_transfers: int | None  # 최대 환승 횟수
    budget_deposit: int | None  # 보증금
    budget_monthly: int | None  # 월세
    room_type: str | None  # 원룸, 투룸 등

    # 중간 결과
    nearby_stations: list[dict] | None  # 회사 근처 역 목록
    routes_data: list[dict] | None  # 경로 데이터
    officetel_candidates: list[dict] | None  # 후보 오피스텔

    # 최종 결과
    recommendations: list[dict] | None  # 최종 추천

    # 에러 처리
    error: str | None

    # 다음 액션
    next_action: str | None  # "search", "route", "compare", "respond"
```

### 2.3 노드 구현

#### 노드 1: 의도 분석 노드

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

def intent_parser_node(state: AgentState) -> AgentState:
    """
    사용자 메시지를 분석하여 의도를 파악하고 엔티티를 추출합니다.
    """

    # 프롬프트 정의
    intent_prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 부동산 검색 의도를 분석하는 전문가입니다.

사용자 메시지를 분석하여 다음을 JSON 형식으로 추출하세요:

1. intent: 의도 분류
   - search_officetel: 오피스텔 검색 요청
   - get_route: 경로 정보 요청
   - compare: 매물 비교 요청
   - general_qa: 일반 질문

2. entities: 추출된 정보
   - company_location: 회사 위치 (예: "강남역", "판교")
   - max_commute_minutes: 최대 출퇴근 시간 (분)
   - budget_deposit: 보증금 (만원)
   - budget_monthly: 월세 (만원)
   - room_type: 방 타입 ("원룸", "투룸", "쓰리룸")
   - building_age_max: 최대 건물 연식 (년)

예시:
입력: "강남역 다니는데 30분 안에 출근 가능한 원룸 찾아줘. 보증금 1000에 월세 60 정도"
출력: {{
  "intent": "search_officetel",
  "entities": {{
    "company_location": "강남역",
    "max_commute_minutes": 30,
    "budget_deposit": 1000,
    "budget_monthly": 60,
    "room_type": "원룸"
  }}
}}
"""),
        ("human", "{input}")
    ])

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = intent_prompt | llm

    # 마지막 사용자 메시지 가져오기
    user_message = state["messages"][-1].content

    # LLM 호출
    result = chain.invoke({"input": user_message})
    parsed = json.loads(result.content)

    # 상태 업데이트
    return {
        **state,
        "intent": parsed["intent"],
        "company_location": parsed["entities"].get("company_location"),
        "max_commute_minutes": parsed["entities"].get("max_commute_minutes", 30),
        "budget_deposit": parsed["entities"].get("budget_deposit"),
        "budget_monthly": parsed["entities"].get("budget_monthly"),
        "room_type": parsed["entities"].get("room_type"),
    }
```

#### 노드 2: 회사 위치 확인 노드

```python
import httpx

async def location_finder_node(state: AgentState) -> AgentState:
    """
    회사 위치를 좌표로 변환합니다 (카카오맵 API 사용).
    """

    company_location = state["company_location"]

    if not company_location:
        return {**state, "error": "회사 위치 정보가 없습니다."}

    # 카카오맵 주소 검색 API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {KAKAO_API_KEY}"},
            params={"query": company_location}
        )
        data = response.json()

    if not data["documents"]:
        return {**state, "error": f"{company_location}을(를) 찾을 수 없습니다."}

    # 첫 번째 결과 사용
    result = data["documents"][0]
    coords = (float(result["y"]), float(result["x"]))  # (lat, lng)

    return {
        **state,
        "company_coords": coords,
        "error": None
    }
```

#### 노드 3: 경로 계산 노드

```python
async def route_calculator_node(state: AgentState) -> AgentState:
    """
    회사 근처 역들과 각 오피스텔의 가까운 역 간 경로를 계산합니다.
    """

    company_coords = state["company_coords"]
    max_commute_minutes = state["max_commute_minutes"]

    # 1. 회사 근처 지하철역 찾기 (Supabase 쿼리)
    nearby_stations = await get_nearby_stations(
        lat=company_coords[0],
        lng=company_coords[1],
        radius_km=1.0
    )

    # 2. 모든 오피스텔의 가까운 역 목록 가져오기
    all_officetel_stations = await get_all_officetel_stations()

    # 3. 경로 계산 (ODsay API)
    routes_data = []

    for company_station in nearby_stations:
        for officetel_station in all_officetel_stations:
            # ODsay API 호출
            route = await get_route_odsay(
                origin=(officetel_station["lat"], officetel_station["lng"]),
                destination=(company_station["lat"], company_station["lng"])
            )

            if route and route["duration_minutes"] <= max_commute_minutes:
                routes_data.append({
                    "officetel_station_id": officetel_station["id"],
                    "company_station_id": company_station["id"],
                    "duration_minutes": route["duration_minutes"],
                    "transfers": route["transfers"],
                    "fare": route["fare"],
                    "route_summary": route["summary"],
                    "detail": route["detail"]
                })

    return {
        **state,
        "nearby_stations": nearby_stations,
        "routes_data": routes_data
    }
```

#### 노드 4: 오피스텔 검색 노드

```python
async def officetel_search_node(state: AgentState) -> AgentState:
    """
    경로 데이터를 기반으로 조건에 맞는 오피스텔을 검색합니다.
    """

    routes_data = state["routes_data"]
    budget_deposit = state["budget_deposit"]
    budget_monthly = state["budget_monthly"]
    room_type = state["room_type"]

    # 출퇴근 가능한 역 ID 추출
    accessible_station_ids = list(set([r["officetel_station_id"] for r in routes_data]))

    # Supabase 쿼리
    query = supabase.table("officetel_complexes").select("""
        *,
        unit_types (*),
        prices (*)
    """).in_("nearest_station_id", accessible_station_ids)

    # 가격 필터
    if budget_deposit:
        query = query.lte("prices.deposit", budget_deposit)
    if budget_monthly:
        query = query.lte("prices.monthly_rent", budget_monthly)

    # 방 타입 필터
    if room_type:
        query = query.eq("unit_types.room_type", room_type)

    officetel_list = query.execute().data

    # 경로 정보 매핑
    candidates = []
    for officetel in officetel_list:
        # 해당 오피스텔의 경로 찾기
        matching_routes = [
            r for r in routes_data
            if r["officetel_station_id"] == officetel["nearest_station_id"]
        ]

        # 가장 빠른 경로 선택
        if matching_routes:
            best_route = min(matching_routes, key=lambda x: x["duration_minutes"])

            candidates.append({
                **officetel,
                "commute_route": best_route
            })

    # 출퇴근 시간 순으로 정렬
    candidates.sort(key=lambda x: x["commute_route"]["duration_minutes"])

    return {
        **state,
        "officetel_candidates": candidates,
        "recommendations": candidates[:10]  # 상위 10개
    }
```

#### 노드 5: 결과 정리 노드

```python
async def result_formatter_node(state: AgentState) -> AgentState:
    """
    검색 결과를 사용자에게 보여줄 형식으로 정리합니다.
    """

    recommendations = state["recommendations"]

    if not recommendations:
        formatted_message = "죄송합니다. 조건에 맞는 오피스텔을 찾지 못했습니다. 조건을 조정해보시겠어요?"
    else:
        # LLM을 사용해 자연어로 정리
        formatting_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 부동산 전문가입니다.
검색 결과를 사용자 친화적인 형식으로 정리해주세요.

다음을 포함하세요:
1. 찾은 매물 개수
2. 상위 3개 추천 (이름, 가격, 출퇴근 시간, 경로)
3. 지역별 그룹화
4. 간단한 분석 코멘트
"""),
            ("human", "검색 결과:\n{results}")
        ])

        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        chain = formatting_prompt | llm

        formatted = chain.invoke({
            "results": json.dumps(recommendations, ensure_ascii=False, indent=2)
        })

        formatted_message = formatted.content

    # 메시지 추가
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=formatted_message)]
    }
```

### 2.4 그래프 연결 (LangGraph)

```python
from langgraph.graph import StateGraph, END

# 그래프 생성
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("intent_parser", intent_parser_node)
workflow.add_node("location_finder", location_finder_node)
workflow.add_node("route_calculator", route_calculator_node)
workflow.add_node("officetel_search", officetel_search_node)
workflow.add_node("result_formatter", result_formatter_node)

# 엣지 연결 (조건부 라우팅)
def route_after_intent(state: AgentState) -> str:
    """의도에 따라 다음 노드 결정"""
    intent = state["intent"]

    if intent == "search_officetel":
        return "location_finder"
    elif intent == "get_route":
        return "route_calculator"
    elif intent == "general_qa":
        return "result_formatter"  # 바로 응답
    else:
        return "result_formatter"

workflow.set_entry_point("intent_parser")

workflow.add_conditional_edges(
    "intent_parser",
    route_after_intent,
    {
        "location_finder": "location_finder",
        "route_calculator": "route_calculator",
        "result_formatter": "result_formatter"
    }
)

workflow.add_edge("location_finder", "route_calculator")
workflow.add_edge("route_calculator", "officetel_search")
workflow.add_edge("officetel_search", "result_formatter")
workflow.add_edge("result_formatter", END)

# 그래프 컴파일
app = workflow.compile()
```

### 2.5 사용 예시

```python
# 초기 상태
initial_state = {
    "messages": [HumanMessage(content="강남역 다니는데 30분 안에 출근 가능한 원룸 찾아줘. 보증금 1000에 월세 60")],
    "intent": None,
    "company_location": None,
    "company_coords": None,
    "max_commute_minutes": None,
    "budget_deposit": None,
    "budget_monthly": None,
    "room_type": None,
    "nearby_stations": None,
    "routes_data": None,
    "officetel_candidates": None,
    "recommendations": None,
    "error": None,
    "next_action": None
}

# 실행
result = await app.ainvoke(initial_state)

# 최종 응답
print(result["messages"][-1].content)
```

---

## 3. Option B: OpenAI Function Calling 기반

### 3.1 아키텍처

```
사용자 입력
    │
    ▼
┌─────────────────────────────────┐
│  OpenAI API (GPT-4o)            │
│  + Function Calling             │
│                                  │
│  System Prompt:                 │
│  "당신은 부동산 전문가입니다"   │
└──────────┬──────────────────────┘
           │
           ▼
    ┌──────────────┐
    │ 함수 선택    │ (OpenAI가 자동 결정)
    └──────┬───────┘
           │
    ┌──────┴─────────────────────────────┐
    │                                     │
    ▼                                     ▼
search_officetel_by_commute     get_detailed_route
    │                                     │
    ▼                                     ▼
[함수 실행]                          [함수 실행]
    │                                     │
    ▼                                     ▼
결과를 OpenAI에 전달                 결과를 OpenAI에 전달
    │                                     │
    └──────────────┬──────────────────────┘
                   ▼
           ┌───────────────┐
           │  최종 응답 생성│
           └───────────────┘
```

### 3.2 함수 정의

#### 함수 1: search_officetel_by_commute

```python
search_officetel_by_commute_definition = {
    "type": "function",
    "function": {
        "name": "search_officetel_by_commute",
        "description": """
        회사 위치를 기준으로 출퇴근 시간 내에 도달 가능한 오피스텔을 검색합니다.

        이 함수는 다음을 수행합니다:
        1. 회사 위치를 좌표로 변환
        2. 회사 근처 지하철역 찾기
        3. 설정된 시간 내 도달 가능한 모든 역 계산
        4. 해당 역 근처 오피스텔 검색
        5. 가격, 평형 등의 조건 필터링
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "company_location": {
                    "type": "string",
                    "description": "회사 위치. 주소, 역명, 건물명 등 (예: '강남역', '판교 카카오', '서울시 강남구 테헤란로 123')"
                },
                "max_commute_minutes": {
                    "type": "integer",
                    "description": "최대 출퇴근 시간 (분 단위). 기본값 30분",
                    "default": 30
                },
                "max_transfers": {
                    "type": "integer",
                    "description": "최대 환승 횟수. 기본값 1회",
                    "default": 1
                },
                "budget_deposit_max": {
                    "type": "integer",
                    "description": "최대 보증금 (만원 단위)"
                },
                "budget_monthly_max": {
                    "type": "integer",
                    "description": "최대 월세 (만원 단위)"
                },
                "room_type": {
                    "type": "string",
                    "enum": ["원룸", "투룸", "쓰리룸", "오피스텔"],
                    "description": "방 타입"
                },
                "building_age_max": {
                    "type": "integer",
                    "description": "최대 건물 연식 (년). 예: 5년 이내 신축"
                },
                "min_area_pyeong": {
                    "type": "number",
                    "description": "최소 면적 (평)"
                }
            },
            "required": ["company_location"]
        }
    }
}
```

#### 함수 구현

```python
async def search_officetel_by_commute(
    company_location: str,
    max_commute_minutes: int = 30,
    max_transfers: int = 1,
    budget_deposit_max: int | None = None,
    budget_monthly_max: int | None = None,
    room_type: str | None = None,
    building_age_max: int | None = None,
    min_area_pyeong: float | None = None
) -> dict:
    """
    출퇴근 기반 오피스텔 검색 함수 실제 구현
    """

    # 1. 회사 위치 → 좌표 변환
    company_coords = await geocode_location(company_location)
    if not company_coords:
        return {
            "success": False,
            "error": f"'{company_location}'의 좌표를 찾을 수 없습니다."
        }

    # 2. 회사 근처 지하철역 찾기 (반경 1km)
    nearby_stations = await db.get_nearby_stations(
        lat=company_coords["lat"],
        lng=company_coords["lng"],
        radius_km=1.0
    )

    if not nearby_stations:
        return {
            "success": False,
            "error": f"'{company_location}' 근처에 지하철역이 없습니다."
        }

    # 3. 출퇴근 가능한 역 찾기
    accessible_officetel_stations = []

    for company_station in nearby_stations:
        # 모든 지하철역 목록 가져오기
        all_stations = await db.get_all_stations()

        for officetel_station in all_stations:
            # 경로 계산 (ODsay API 또는 캐시)
            route = await calculate_route(
                origin=officetel_station,
                destination=company_station,
                max_time=max_commute_minutes,
                max_transfers=max_transfers
            )

            if route and route["duration_minutes"] <= max_commute_minutes:
                accessible_officetel_stations.append({
                    "station": officetel_station,
                    "route": route
                })

    # 4. 해당 역 근처 오피스텔 검색
    officetel_list = await db.search_officetel(
        station_ids=[s["station"]["id"] for s in accessible_officetel_stations],
        deposit_max=budget_deposit_max,
        monthly_max=budget_monthly_max,
        room_type=room_type,
        building_age_max=building_age_max,
        min_area_pyeong=min_area_pyeong
    )

    # 5. 경로 정보 매핑
    results = []
    for officetel in officetel_list:
        # 해당 오피스텔의 경로 찾기
        matching_route = next(
            (s["route"] for s in accessible_officetel_stations
             if s["station"]["id"] == officetel["nearest_station_id"]),
            None
        )

        if matching_route:
            results.append({
                "id": officetel["id"],
                "name": officetel["name"],
                "address": officetel["address"],
                "deposit": officetel["prices"][0]["deposit"],
                "monthly_rent": officetel["prices"][0]["monthly_rent"],
                "room_type": officetel["unit_types"][0]["room_type"],
                "area_pyeong": officetel["unit_types"][0]["pyeong"],
                "build_year": officetel["build_year"],
                "commute": {
                    "duration_minutes": matching_route["duration_minutes"],
                    "transfers": matching_route["transfers"],
                    "fare": matching_route["fare"],
                    "route_summary": matching_route["summary"],
                    "detailed_steps": matching_route["steps"]
                }
            })

    # 6. 출퇴근 시간 순 정렬
    results.sort(key=lambda x: x["commute"]["duration_minutes"])

    return {
        "success": True,
        "total_count": len(results),
        "company_location": company_location,
        "max_commute_minutes": max_commute_minutes,
        "results": results[:20]  # 상위 20개
    }
```

### 3.3 대화 플로우 구현

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# 함수 매핑
AVAILABLE_FUNCTIONS = {
    "search_officetel_by_commute": search_officetel_by_commute,
    "get_detailed_route": get_detailed_route,
    "compare_officetel_by_commute": compare_officetel_by_commute,
    "get_area_recommendation": get_area_recommendation,
}

async def chat_with_agent(user_message: str, conversation_history: list = None):
    """
    OpenAI Function Calling을 사용한 에이전트 대화
    """

    if conversation_history is None:
        conversation_history = []

    # 시스템 프롬프트
    system_message = {
        "role": "system",
        "content": """당신은 출퇴근 기반 오피스텔 추천 전문가입니다.

역할:
- 사용자의 회사 위치와 조건을 듣고 최적의 오피스텔을 추천
- 출퇴근 시간과 경로를 상세하게 설명
- 가격, 편의성, 생활 편의시설을 종합적으로 고려

응답 스타일:
- 친근하고 전문적인 톤
- 구체적인 숫자와 경로 정보 제공
- 이모지 적절히 사용 (🏢 📍 🚇 💰 등)
- 표나 목록으로 정보 정리

제약사항:
- 데이터에 없는 정보는 추측하지 않음
- 법적 조언이나 투자 권유 금지
"""
    }

    # 대화 기록 구성
    messages = [system_message] + conversation_history + [
        {"role": "user", "content": user_message}
    ]

    # 함수 정의 목록
    tools = [
        search_officetel_by_commute_definition,
        get_detailed_route_definition,
        compare_officetel_definition,
        get_area_recommendation_definition
    ]

    # OpenAI API 호출
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7
    )

    response_message = response.choices[0].message

    # 함수 호출이 있는 경우
    if response_message.tool_calls:
        # 메시지 추가
        messages.append(response_message)

        # 각 함수 호출 처리
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # 함수 실행
            function_to_call = AVAILABLE_FUNCTIONS[function_name]
            function_response = await function_to_call(**function_args)

            # 함수 응답 추가
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_response, ensure_ascii=False)
            })

        # 두 번째 API 호출 (함수 결과 포함)
        second_response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7
        )

        final_message = second_response.choices[0].message.content
    else:
        # 함수 호출 없이 바로 응답
        final_message = response_message.content

    # 대화 기록 업데이트
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": final_message})

    return {
        "response": final_message,
        "conversation_history": conversation_history
    }
```

### 3.4 Vercel Function으로 배포

```python
# api/chat.py (Vercel Serverless Function)

from http.server import BaseHTTPRequestHandler
import json
import asyncio

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        user_message = data.get("message")
        conversation_history = data.get("history", [])

        # 비동기 함수 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            chat_with_agent(user_message, conversation_history)
        )

        # 응답
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())
```

---

## 4. 의도 분석 시스템

### 4.1 의도 분류 체계

```python
class Intent(Enum):
    """사용자 의도 분류"""

    # 검색 관련
    SEARCH_OFFICETEL = "search_officetel"  # 오피스텔 검색
    SEARCH_BY_AREA = "search_by_area"      # 지역별 검색
    SEARCH_BY_PRICE = "search_by_price"    # 가격대별 검색

    # 경로 관련
    GET_ROUTE = "get_route"                # 특정 경로 조회
    COMPARE_ROUTES = "compare_routes"      # 경로 비교

    # 비교 관련
    COMPARE_OFFICETEL = "compare_officetel"  # 매물 비교

    # 정보 조회
    GET_AREA_INFO = "get_area_info"        # 지역 정보
    GET_PRICE_TREND = "get_price_trend"    # 시세 동향

    # 일반 질문
    GENERAL_QA = "general_qa"              # 일반 질의응답

    # 필터 조정
    REFINE_SEARCH = "refine_search"        # 검색 조건 변경
```

### 4.2 Few-Shot 의도 분석

```python
intent_classification_examples = [
    {
        "input": "강남역 다니는데 30분 안에 출근 가능한 원룸 찾아줘",
        "output": {
            "intent": "SEARCH_OFFICETEL",
            "confidence": 0.95,
            "entities": {
                "company_location": "강남역",
                "max_commute_minutes": 30,
                "room_type": "원룸"
            }
        }
    },
    {
        "input": "선릉역 오피스텔에서 판교까지 얼마나 걸려?",
        "output": {
            "intent": "GET_ROUTE",
            "confidence": 0.92,
            "entities": {
                "origin": "선릉역",
                "destination": "판교"
            }
        }
    },
    {
        "input": "강남역 래미안이랑 삼성역 푸르지오 비교해줘",
        "output": {
            "intent": "COMPARE_OFFICETEL",
            "confidence": 0.90,
            "entities": {
                "officetel_names": ["강남역 래미안", "삼성역 푸르지오"]
            }
        }
    },
    {
        "input": "좀 더 저렴한 곳으로 보여줘",
        "output": {
            "intent": "REFINE_SEARCH",
            "confidence": 0.88,
            "entities": {
                "filter_change": "lower_price"
            }
        }
    }
]
```

### 4.3 엔티티 추출 패턴

```python
import re

class EntityExtractor:
    """사용자 입력에서 엔티티 추출"""

    @staticmethod
    def extract_location(text: str) -> str | None:
        """위치 정보 추출"""
        # 역 패턴
        station_pattern = r'([가-힣]+역)'
        match = re.search(station_pattern, text)
        if match:
            return match.group(1)

        # 동 패턴
        dong_pattern = r'([가-힣]+동)'
        match = re.search(dong_pattern, text)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def extract_time(text: str) -> int | None:
        """시간 정보 추출 (분)"""
        # "30분", "1시간", "1시간 30분" 등
        patterns = [
            (r'(\d+)시간\s*(\d+)분', lambda m: int(m.group(1)) * 60 + int(m.group(2))),
            (r'(\d+)시간', lambda m: int(m.group(1)) * 60),
            (r'(\d+)분', lambda m: int(m.group(1)))
        ]

        for pattern, converter in patterns:
            match = re.search(pattern, text)
            if match:
                return converter(match)

        return None

    @staticmethod
    def extract_budget(text: str) -> tuple[int | None, int | None]:
        """예산 정보 추출 (보증금, 월세)"""
        # "보증금 1000에 월세 60", "1000/60" 등
        patterns = [
            r'보증금\s*(\d+).*?월세\s*(\d+)',
            r'(\d+)\s*/\s*(\d+)',
            r'(\d{3,4})\s*(\d{2})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                deposit = int(match.group(1))
                monthly = int(match.group(2))
                return (deposit, monthly)

        return (None, None)

    @staticmethod
    def extract_room_type(text: str) -> str | None:
        """방 타입 추출"""
        room_types = ["원룸", "투룸", "쓰리룸", "오피스텔"]

        for room_type in room_types:
            if room_type in text:
                return room_type

        return None
```

---

## 5. 툴/함수 상세 설계

### 5.1 전체 툴 목록

| 함수명 | 용도 | 입력 | 출력 |
|--------|------|------|------|
| `search_officetel_by_commute` | 출퇴근 기반 검색 | 회사 위치, 시간, 예산 | 오피스텔 목록 |
| `get_detailed_route` | 경로 상세 조회 | 출발/도착 좌표 | 경로 정보 |
| `compare_officetel_by_commute` | 매물 비교 | 오피스텔 ID 목록 | 비교 테이블 |
| `get_area_recommendation` | 지역 추천 | 회사 위치, 우선순위 | 추천 지역 |
| `simulate_commute` | 출퇴근 시뮬레이션 | 오피스텔 ID, 시간대 | 시간대별 소요시간 |
| `geocode_location` | 주소→좌표 변환 | 주소/역명 | 좌표 |
| `get_nearby_stations` | 근처 역 찾기 | 좌표, 반경 | 역 목록 |
| `calculate_route` | 경로 계산 (ODsay) | 출발/도착 역 | 경로 |

### 5.2 핵심 툴 상세 설계

#### calculate_route (ODsay API 래퍼)

```python
async def calculate_route(
    origin: dict,  # {"lat": 37.xxx, "lng": 127.xxx, "name": "선릉역"}
    destination: dict,
    max_time: int = 60,
    max_transfers: int = 2
) -> dict | None:
    """
    ODsay API를 사용하여 두 지점 간 대중교통 경로를 계산합니다.

    캐싱 전략:
    - origin_id + destination_id를 키로 사용
    - 1시간 캐시 (교통 상황 변동 고려)
    """

    cache_key = f"route:{origin['id']}:{destination['id']}"

    # 캐시 확인
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # ODsay API 호출
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.odsay.com/v1/api/searchPubTransPath",
            params={
                "apiKey": ODSAY_API_KEY,
                "SX": origin["lng"],
                "SY": origin["lat"],
                "EX": destination["lng"],
                "EY": destination["lat"]
            }
        )
        data = response.json()

    if not data.get("result") or not data["result"].get("path"):
        return None

    # 첫 번째 경로 선택 (최적 경로)
    path = data["result"]["path"][0]

    # 경로 파싱
    duration = path["info"]["totalTime"]  # 분

    if duration > max_time:
        return None

    # 환승 횟수 계산
    transfers = len([s for s in path["subPath"] if s["trafficType"] == 1]) - 1

    if transfers > max_transfers:
        return None

    # 상세 경로 추출
    steps = []
    for i, sub_path in enumerate(path["subPath"]):
        if sub_path["trafficType"] == 1:  # 지하철
            steps.append({
                "type": "subway",
                "line": sub_path["lane"][0]["name"],  # 호선명
                "start_station": sub_path["startName"],
                "end_station": sub_path["endName"],
                "station_count": sub_path["stationCount"],
                "duration": sub_path["sectionTime"]
            })
        elif sub_path["trafficType"] == 2:  # 버스
            steps.append({
                "type": "bus",
                "bus_no": sub_path["lane"][0]["busNo"],
                "start_station": sub_path["startName"],
                "end_station": sub_path["endName"],
                "station_count": sub_path["stationCount"],
                "duration": sub_path["sectionTime"]
            })
        elif sub_path["trafficType"] == 3:  # 도보
            steps.append({
                "type": "walk",
                "distance": sub_path["distance"],
                "duration": sub_path["sectionTime"]
            })

    result = {
        "duration_minutes": duration,
        "transfers": transfers,
        "fare": path["info"]["payment"],
        "summary": " → ".join([
            s["line"] if s["type"] == "subway" else f"{s['bus_no']}번"
            for s in steps if s["type"] in ["subway", "bus"]
        ]),
        "steps": steps
    }

    # 캐시 저장 (1시간)
    await redis.setex(cache_key, 3600, json.dumps(result))

    return result
```

---

## 6. 상태 관리 전략

### 6.1 대화 컨텍스트 관리

#### Option A: 서버 세션 (Redis)

```python
import redis.asyncio as aioredis
from datetime import timedelta

redis_client = aioredis.from_url("redis://localhost")

class ConversationManager:
    """대화 컨텍스트 관리"""

    @staticmethod
    async def save_context(user_id: str, context: dict):
        """컨텍스트 저장 (30분 TTL)"""
        key = f"conversation:{user_id}"
        await redis_client.setex(
            key,
            timedelta(minutes=30),
            json.dumps(context, ensure_ascii=False)
        )

    @staticmethod
    async def get_context(user_id: str) -> dict | None:
        """컨텍스트 조회"""
        key = f"conversation:{user_id}"
        data = await redis_client.get(key)
        return json.loads(data) if data else None

    @staticmethod
    async def update_context(user_id: str, updates: dict):
        """컨텍스트 부분 업데이트"""
        context = await ConversationManager.get_context(user_id) or {}
        context.update(updates)
        await ConversationManager.save_context(user_id, context)
```

#### Option B: 클라이언트 세션 (LocalStorage)

```typescript
// Frontend (React)
interface ConversationContext {
  companyLocation?: string;
  companyCoords?: { lat: number; lng: number };
  maxCommuteMinutes?: number;
  budget?: { deposit: number; monthly: number };
  roomType?: string;
  lastSearchResults?: Array<any>;
  conversationHistory?: Array<{ role: string; content: string }>;
}

class ContextManager {
  private static KEY = "estate_hub_context";

  static save(context: ConversationContext): void {
    localStorage.setItem(this.KEY, JSON.stringify(context));
  }

  static load(): ConversationContext | null {
    const data = localStorage.getItem(this.KEY);
    return data ? JSON.parse(data) : null;
  }

  static update(updates: Partial<ConversationContext>): void {
    const current = this.load() || {};
    this.save({ ...current, ...updates });
  }

  static clear(): void {
    localStorage.removeItem(this.KEY);
  }
}
```

### 6.2 멀티턴 대화 처리

```python
async def handle_multiturn_conversation(
    user_message: str,
    user_id: str
) -> str:
    """
    멀티턴 대화 처리
    """

    # 이전 컨텍스트 로드
    context = await ConversationManager.get_context(user_id) or {}
    conversation_history = context.get("history", [])

    # 엔티티 추출
    extractor = EntityExtractor()
    entities = {
        "location": extractor.extract_location(user_message),
        "time": extractor.extract_time(user_message),
        "budget": extractor.extract_budget(user_message),
        "room_type": extractor.extract_room_type(user_message)
    }

    # 컨텍스트 업데이트
    if entities["location"]:
        context["company_location"] = entities["location"]
    if entities["time"]:
        context["max_commute_minutes"] = entities["time"]
    if entities["budget"][0]:
        context["budget_deposit"] = entities["budget"][0]
    if entities["budget"][1]:
        context["budget_monthly"] = entities["budget"][1]
    if entities["room_type"]:
        context["room_type"] = entities["room_type"]

    # 필수 정보 체크
    missing_fields = []
    if not context.get("company_location"):
        missing_fields.append("회사 위치")

    if missing_fields:
        # 추가 정보 요청
        response = f"{', '.join(missing_fields)}를 알려주시겠어요?"
    else:
        # 검색 실행
        result = await search_officetel_by_commute(
            company_location=context["company_location"],
            max_commute_minutes=context.get("max_commute_minutes", 30),
            budget_deposit_max=context.get("budget_deposit"),
            budget_monthly_max=context.get("budget_monthly"),
            room_type=context.get("room_type")
        )

        # LLM으로 응답 생성
        response = await format_search_results(result)

        # 검색 결과 저장
        context["last_search_results"] = result["results"]

    # 대화 기록 업데이트
    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": response})
    context["history"] = conversation_history[-20:]  # 최근 20개만 유지

    # 컨텍스트 저장
    await ConversationManager.save_context(user_id, context)

    return response
```

---

## 7. 최종 추천 및 구현 가이드

### 7.1 최종 추천: **OpenAI Function Calling**

**이유:**
1. ✅ 서버리스 환경 (Vercel)에 최적화
2. ✅ 빠른 응답 속도 (1-2초)
3. ✅ 낮은 비용 (월 $10~30)
4. ✅ 구현 및 디버깅 쉬움
5. ✅ 우리 프로젝트의 복잡도에 적합

**LangGraph는 언제?**
- MVP 검증 후 복잡한 워크플로우 추가 시 (Phase 2-3)
- 예: 매물 협상 봇, 계약 지원 등

### 7.2 구현 순서

#### Week 1: 핵심 함수 구현
```python
# 1. 기본 함수
✓ geocode_location()
✓ get_nearby_stations()
✓ calculate_route()

# 2. 메인 함수
✓ search_officetel_by_commute()
```

#### Week 2: OpenAI 통합
```python
# 1. Function Calling 설정
✓ 함수 정의 작성
✓ chat_with_agent() 구현

# 2. Vercel Function 배포
✓ /api/chat 엔드포인트
✓ 환경변수 설정
```

#### Week 3: Frontend 연결
```typescript
// 1. 채팅 UI
✓ ChatInterface 컴포넌트
✓ 메시지 렌더링

// 2. 상태 관리
✓ ContextManager
✓ LocalStorage 저장
```

### 7.3 코드 템플릿

#### 전체 시스템 (main.py)

```python
# main.py - 전체 시스템 통합

import os
from openai import AsyncOpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 초기화
app = FastAPI()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 요청/응답 스키마
class ChatRequest(BaseModel):
    message: str
    user_id: str
    history: list[dict] = []

class ChatResponse(BaseModel):
    response: str
    history: list[dict]

# 메인 엔드포인트
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        result = await chat_with_agent(
            user_message=request.message,
            user_id=request.user_id,
            conversation_history=request.history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 에이전트 로직
async def chat_with_agent(
    user_message: str,
    user_id: str,
    conversation_history: list[dict]
):
    # [위의 구현 코드 사용]
    ...

# 함수들
async def search_officetel_by_commute(...):
    # [위의 구현 코드 사용]
    ...

# 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 📝 요약

### LangGraph vs OpenAI Function Calling

| 특성 | LangGraph | Function Calling |
|------|-----------|-----------------|
| **추천도** | ⭐⭐⭐ (Phase 2-3) | ⭐⭐⭐⭐⭐ (MVP) |
| **난이도** | 높음 | 낮음 |
| **비용** | 높음 | 낮음 |
| **속도** | 느림 | 빠름 |
| **유연성** | 매우 높음 | 충분함 |

### 구현 체크리스트

- [ ] OpenAI API 키 발급
- [ ] ODsay API 키 발급
- [ ] 카카오맵 API 키 발급
- [ ] Supabase 데이터베이스 구축
- [ ] 5개 핵심 함수 구현
- [ ] Function Calling 정의 작성
- [ ] Vercel Function 배포
- [ ] Frontend 채팅 UI
- [ ] 컨텍스트 관리 (LocalStorage)
- [ ] 테스트 및 디버깅

---

**다음 단계**: 이 아키텍처로 바로 구현을 시작하시겠습니까? 🚀
