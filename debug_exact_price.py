from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re

URL = "https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1439847&numberOfBedrooms=&familyMode=false&adults=2&children=0&rooms=1&maxRooms=0&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=1&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&tag=4f122210-314e-4c70-b18b-ac93fc25b69f&flightSearchCriteria=%5Bobject%20Object%5D&los=1&searchrequestid=1db7a87b-052d-42f2-8e2b-353298d15809&utm_medium=banner&utm_source=naver&utm_campaign=naverbz&utm_content=nbz10&utm_term=nbz10&ds=qbRdfmY8zNLy%2B9RI&checkin=2026-01-04"

print("Chrome 드라이버 시작 중...")
options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=options)

try:
    print(f"URL 접속 중...\n")
    driver.get(URL)
    time.sleep(10)
    
    # 첫 번째 h4 찾기
    h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
    
    if h4_elements:
        h4 = h4_elements[0]
        room_name = h4.text[:40]
        print(f"[{room_name}]\n")
        
        # h4로부터 부모 찾기
        current = h4
        for depth in range(20):
            try:
                current = current.find_element(By.XPATH, '..')
                
                # 현재 레벨의 모든 텍스트 찾기
                all_text = current.text
                
                # 76850 같은 패턴 찾기
                prices = re.findall(r'₩?\s*(\d{2,6}(?:,\d{3})*)', all_text)
                
                if any('76' in p or '85' in p for p in prices):
                    print(f"깊이 {depth}: 가격 정보 발견")
                    print(f"  모든 텍스트:\n{all_text[:800]}\n")
                    
                    # 이 레벨의 모든 span, div 찾기
                    for elem in current.find_elements(By.CSS_SELECTOR, 'span, div'):
                        text = elem.text.strip()
                        if text and any(x in text for x in ['76', '85', '232', '850', '-10']):
                            tag = elem.tag_name
                            classes = elem.get_attribute('class')
                            print(f"  {tag}.{classes[:50]}: {text[:100]}")
                    
                    break
                    
            except:
                pass

finally:
    driver.quit()