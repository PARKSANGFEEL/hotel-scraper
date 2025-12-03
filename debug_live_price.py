from selenium import webdriver
from selenium.webdriver.common.by import By
import time

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
        print(f"[{h4.text[:40]}]\n")
        
        # h4의 부모 찾기
        current = h4
        for i in range(15):
            current = current.find_element(By.XPATH, '..')
            try:
                crossed = current.find_element(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"]')
                print(f"깊이 {i}에서 crossed-out-price-text 발견\n")
                
                # crossed-out 요소의 모든 속성 출력
                print("crossed-out-price-text 속성들:")
                for attr in ['data-room-price', 'data-element-value', 'data-element-cor']:
                    val = crossed.get_attribute(attr)
                    print(f"  {attr}: {val}")
                
                # 부모 컨테이너의 모든 텍스트 출력
                print("\n부모 컨테이너 내 모든 텍스트:")
                for elem in current.find_elements(By.XPATH, './/*[text()]'):
                    text = elem.text.strip()
                    if text and '₩' in text:
                        print(f"  '{text}'")
                        # 해당 요소의 속성
                        for attr in elem.get_attribute('outerHTML').split():
                            if 'data-' in attr or 'class' in attr:
                                print(f"    {attr}")
                
                # 페이지 소스 일부 출력 (현재 요소 근처)
                print("\n현재 요소의 outerHTML (처음 1500자):")
                html = current.get_attribute('outerHTML')
                print(html[:1500])
                
                break
            except:
                pass

finally:
    driver.quit()