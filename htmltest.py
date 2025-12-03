import pandas as pd
from datetime import date, timedelta
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def analyze_page_structure():
    """페이지 구조 분석용"""
    print("웹 드라이버 설정 중...")
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.maximize_window()
    except Exception as e:
        print(f"드라이버 초기화 오류: {e}")
        return

    check_in_date = date(2026, 1, 4)
    check_out_date = date(2026, 1, 5)
    
    HOTEL_RIAN_URL = "https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?locale=ko-kr&prid=0&currency=KRW&languageId=9&origin=KR&stateCode=11&cid=-1&whitelabelid=1&loginLvl=0&storefrontId=3&currencyId=26&currencyCode=KRW&htmlLanguage=ko-kr&cultureInfoName=ko-kr&rooms=1&adults=2&childs=0&priceCur=KRW&los=1&productType=-1&travellerType=1&familyMode=off"
    
    url_with_dates = f"{HOTEL_RIAN_URL}&checkIn={check_in_date.strftime('%Y-%m-%d')}&checkOut={check_out_date.strftime('%Y-%m-%d')}"

    try:
        driver.get(url_with_dates)
        time.sleep(8)

        # 스크롤
        for _ in range(8):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(0.5)

        # 전체 HTML 저장
        with open("debug_structure.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("✓ 전체 HTML 저장: debug_structure.html\n")

        # 페이지 텍스트에서 가격 관련 텍스트 찾기
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        print("[가격 관련 키워드 검색]")
        keywords = ['1박', '총 금액', '원래 요금', '세금', '수수료', '요금', '가격']
        for keyword in keywords:
            count = page_text.count(keyword)
            print(f"  '{keyword}': {count}개")

        print("\n[h4 태그 내용 (룸 타입)]")
        h4_elements = driver.find_elements(By.TAG_NAME, "h4")
        for idx, elem in enumerate(h4_elements[:10]):
            text = elem.text.strip()
            if text:
                print(f"  [{idx}] {text}")

        print("\n[div 요소 중 ₩ 포함하는 것들]")
        divs_with_won = driver.find_elements(By.XPATH, "//div[contains(text(), '₩')]")
        for idx, elem in enumerate(divs_with_won[:10]):
            text = elem.text.strip()[:150]
            print(f"  [{idx}] {text}")

        print("\n[span 요소 중 가격 관련 텍스트]")
        spans = driver.find_elements(By.TAG_NAME, "span")
        for idx, elem in enumerate(spans):
            text = elem.text.strip()
            if ('₩' in text or '요금' in text or '가격' in text) and len(text) < 100:
                print(f"  [{idx}] {text}")
                if idx > 15:
                    break

        print("\n[data-testid 속성 포함하는 요소들]")
        elements_with_testid = driver.find_elements(By.XPATH, "//*[@data-testid]")
        testid_list = set()
        for elem in elements_with_testid[:50]:
            testid = elem.get_attribute('data-testid')
            if testid and ('price' in testid.lower() or 'room' in testid.lower() or 'fee' in testid.lower()):
                testid_list.add(testid)
        
        for testid in list(testid_list)[:20]:
            print(f"  - {testid}")

    except Exception as e:
        print(f"오류: {str(e)}")
    finally:
        driver.quit()


if __name__ == '__main__':
    analyze_page_structure()