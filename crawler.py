import requests
import pandas as pd
import json
import time
import os
import argparse

# HTTP 요청 헤더 설정
HEADERS = {
    "Accept-Encoding": "gzip",
    "Host": "new.land.naver.com",
    "Referer": "https://new.land.naver.com/complexes/102378?ms=37.5018495,127.0438028,16&a=APT&b=A1&e=RETAIL",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
}

def fetch_data(url, params=None):
    """
    지정된 URL에서 데이터를 가져옵니다. 5초의 지연 시간을 포함합니다.
    """
    time.sleep(5)
    try:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        return r.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"데이터를 가져오는 중 오류 발생: {e}")
        return None

def get_region_list(cortar_no="0000000000"):
    """
    시/도, 시/군/구, 읍/면/동의 지역 코드 목록을 가져옵니다.
    """
    url = "https://new.land.naver.com/api/regions/list"
    params = {'cortarNo': cortar_no, 'sameAddressGroup': 'false'}
    data = fetch_data(url, params)
    return data.get("regionList", []) if data else []

def get_apt_list(cortar_no):
    """
    특정 동의 아파트 단지 목록을 가져옵니다.
    """
    url = "https://new.land.naver.com/api/regions/complexes"
    params = {'cortarNo': cortar_no, 'realEstateType': 'APT', 'order': ''}
    data = fetch_data(url, params)
    return data.get("complexList", []) if data else []

def get_complex_info(complex_no):
    """
    특정 아파트 단지의 상세 정보를 가져옵니다.
    """
    url = f"https://new.land.naver.com/api/complexes/{complex_no}"
    params = {'sameAddressGroup': 'false'}
    return fetch_data(url, params)

def main():
    # 1. 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description="네이버 부동산 아파트 정보를 크롤링합니다.")
    parser.add_argument("sido", type=str, help="시/도 이름 (예: 서울특별시)")
    parser.add_argument("gungu", type=str, help="시/군/구 이름 (예: 강남구)")
    parser.add_argument("dong", type=str, help="읍/면/동 이름 (예: 개포동)")
    args = parser.parse_args()

    sido_name = args.sido
    gungu_name = args.gungu
    dong_name = args.dong

    # 2. 지역 코드 찾기
    sido_list = get_region_list()
    sido = next((item for item in sido_list if item["cortarName"] == sido_name), None)
    if not sido:
        print(f"'{sido_name}'을(를) 찾을 수 없습니다.")
        return

    gungu_list = get_region_list(sido["cortarNo"])
    gungu = next((item for item in gungu_list if item["cortarName"] == gungu_name), None)
    if not gungu:
        print(f"'{gungu_name}'을(를) 찾을 수 없습니다.")
        return

    dong_list = get_region_list(gungu["cortarNo"])
    dong = next((item for item in dong_list if item["cortarName"] == dong_name), None)
    if not dong:
        print(f"'{dong_name}'을(를) 찾을 수 없습니다.")
        return

    # 3. 아파트 목록 가져오기
    apt_list = get_apt_list(dong["cortarNo"])
    if not apt_list:
        print(f"{sido_name} {gungu_name} {dong_name}에서 아파트 정보를 찾을 수 없습니다.")
        return

    print(f"총 {len(apt_list)}개의 아파트 단지를 찾았습니다. 상세 정보를 수집합니다.")

    # 4. 아파트 정보 수집
    apartments_data = []
    for apt in apt_list:
        complex_info = get_complex_info(apt["complexNo"])
        if complex_info and "complexDetail" in complex_info and "complexPyeongDetailList" in complex_info:
            detail = complex_info["complexDetail"]
            pyeong_list = complex_info["complexPyeongDetailList"]

            for pyeong_info in pyeong_list:
                stats = pyeong_info.get("articleStatistics", {})
                apartments_data.append({
                    "아파트명": detail.get("complexName", ""),
                    "주소": detail.get("address", "") + " " + detail.get("detailAddress", ""),
                    "총세대수": detail.get("totalHouseholdCount", ""),
                    "입주년월": detail.get("useApproveYm", ""),
                    "평형": pyeong_info.get("pyeongName", ""),
                    "공급면적 (㎡)": pyeong_info.get("supplyArea", ""),
                    "전용면적 (㎡)": pyeong_info.get("exclusiveArea", ""),
                    "매매호가": stats.get("dealPriceString", "N/A"),
                    "전세호가": stats.get("leasePriceString", "N/A"),
                    "월세호가": stats.get("rentPriceString", "N/A"),
                })
            print(f"- {detail.get('complexName', '')} ({len(pyeong_list)}개 평형) 정보 수집 완료")
        else:
            print(f"- {apt.get('complexName', apt.get('complexNo'))}의 상세 정보 수집 실패")


    # 5. 데이터프레임으로 변환하고 CSV 파일로 저장
    if not apartments_data:
        print("수집된 아파트 정보가 없습니다.")
        return

    df = pd.DataFrame(apartments_data)

    # 파일명 생성
    filename = f"{sido_name}_{gungu_name}_{dong_name}_아파트_매물.csv"

    # CSV 파일 저장
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n아파트 정보가 '{os.path.abspath(filename)}' 파일로 저장되었습니다.")

    # 결과 출력
    print("\n--- 수집된 아파트 정보 ---")
    print(df.head())


if __name__ == "__main__":
    main()
