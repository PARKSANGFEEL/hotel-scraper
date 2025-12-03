import json
import pandas as pd
from datetime import date, timedelta
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def extract_price_from_text(price_text):
    """가격 텍스트에서 숫자만 추출"""
    if not price_text:
        return None
    numbers = re.sub(r'[^\d]', '', price_text)
    return int(numbers) if numbers else None

def scrape_daily_agoda_price(start_day: date, end_day: date, hotel_url: str):
    print("웹 드라이버 설정 중...")
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.maximize_window()
    except Exception as e:
        print(f"드라이버 초기화 오류: {e}")
        return

    price_data = []
    current_day = start_day

    while current_day <= end_day:
        check_in_date = current_day
        check_out_date = current_day + timedelta(days=1)
        
        print(f"\n[{check_in_date}] 가격 검색 시도 중...")
        
        url_with_dates = f"{hotel_url}&checkIn={check_in_date.strftime('%Y-%m-%d')}&checkOut={check_out_date.strftime('%Y-%m-%d')}"
        print(f"URL: {url_with_dates}\n")

        try:
            driver.get(url_with_dates)
            time.sleep(6)

            # 스크롤 및 로딩 유도
            for _ in range(8):
                driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(0.5)

            # 1. 모든 h4 태그(룸 이름) 찾기
            room_elements = driver.find_elements(By.TAG_NAME, "h4")
            
            # 2. 모든 div에서 "1박당 총 금액" 텍스트를 포함한 가격 찾기
            price_divs = driver.find_elements(By.XPATH, "//div[contains(text(), '1박당 총 금액')]")
            
            print(f"  ✓ 발견된 룸: {len(room_elements)}개")
            print(f"  ✓ 발견된 가격 정보: {len(price_divs)}개")

            # 룸 이름 추출 (중복 제거, 의미있는 것만)
            room_names = []
            for elem in room_elements:
                try:
                    text = elem.text.strip()
                    # "Room" 관련 텍스트만 필터링
                    if 'room' in text.lower() or '룸' in text:
                        room_names.append(text)
                except:
                    pass
            
            room_names = list(set(room_names))  # 중복 제거
            
            # 가격 추출
            fee_rate = 0.10
            room_price_list = []
            
            for price_div in price_divs:
                try:
                    price_text = price_div.text.strip()
                    # "1박당 총 금액 ₩ 118,944" 형식에서 가격만 추출
                    match = re.search(r'₩\s*([\d,]+)', price_text)
                    if match:
                        price_str = match.group(1).replace(',', '')
                        price_num = int(price_str)
                        fee_included = int(round(price_num * (1 + fee_rate)))
                        room_price_list.append({
                            'price_text': f'₩ {price_str}',
                            'price_num': price_num,
                            'fee_included_num': fee_included
                        })
                except Exception as e:
                    print(f"  ⚠ 가격 파싱 오류: {e}")
                    continue
            
            print(f"  ✓ 추출된 가격: {len(room_price_list)}개")

            # 데이터 조합 (룸 이름과 가격 매칭)
            for idx in range(max(len(room_names), len(room_price_list))):
                room_name = room_names[idx] if idx < len(room_names) else f"룸 {idx+1}"
                if idx < len(room_price_list):
                    price_info = room_price_list[idx]
                    price_data.append({
                        '체크인 날짜': check_in_date.strftime('%Y-%m-%d'),
                        '체크아웃 날짜': check_out_date.strftime('%Y-%m-%d'),
                        '룸 타입': room_name,
                        '실제 가격 (텍스트)': price_info['price_text'],
                        '실제 가격 (숫자)': price_info['price_num'],
                        '수수료 포함 가격 (10%)': price_info['fee_included_num']
                    })
                    print(f"  ✓ {room_name}: {price_info['price_text']} (수수료포함: {price_info['fee_included_num']}원)")
            
            if not room_price_list:
                print(f"  ⚠ 가격 정보를 찾을 수 없습니다")
                price_data.append({
                    '체크인 날짜': check_in_date.strftime('%Y-%m-%d'),
                    '체크아웃 날짜': check_out_date.strftime('%Y-%m-%d'),
                    '룸 타입': '정보 없음',
                    '실제 가격 (텍스트)': '추출 실패',
                    '실제 가격 (숫자)': None,
                    '수수료 포함 가격 (10%)': None
                })

        except Exception as e:
            print(f"실패: {check_in_date.strftime('%Y-%m-%d')} - {str(e)[:100]}")
            price_data.append({
                '체크인 날짜': check_in_date.strftime('%Y-%m-%d'),
                '체크아웃 날짜': check_out_date.strftime('%Y-%m-%d'),
                '룸 타입': '오류',
                '실제 가격 (텍스트)': '추출 실패',
                '실제 가격 (숫자)': None,
                '수수료 포함 가격 (10%)': None
            })

        current_day += timedelta(days=1)
        time.sleep(2)

    driver.quit()
    
    df = pd.DataFrame(price_data)
    filename = "Agoda_HotelRian_DailyPrices_Dec.xlsx"
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"\n✓ 결과가 '{filename}' 파일로 저장되었습니다. (총 {len(df)}행)")


if __name__ == '__main__':
    START_DATE = date(2026, 1, 4)
    END_DATE = date(2026, 1, 4)
    HOTEL_RIAN_URL = "https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?locale=ko-kr&prid=0&currency=KRW&languageId=9&origin=KR&stateCode=11&cid=-1&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=26&currencyCode=KRW&htmlLanguage=ko-kr&cultureInfoName=ko-kr&rooms=1&adults=2&childs=0&priceCur=KRW&los=1&productType=-1&travellerType=1&familyMode=off"
    scrape_daily_agoda_price(START_DATE, END_DATE, HOTEL_RIAN_URL)