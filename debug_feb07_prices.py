from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re

# 문제가 있는 호텔들
HOTELS = {
    'hotel_rian': {
        'name': '리안호텔',
        'url': 'https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?finalPriceView=1&adults=2&children=0&rooms=1&los=1&checkin=2026-02-07',
        'rooms': ['스탠다드 더블룸', '스탠다드 트윈룸', '디럭스 더블']
    },
    'grid_inn': {
        'name': '그리드인 호텔',
        'url': 'https://www.agoda.com/ko-kr/grid-inn/hotel/seoul-kr.html?finalPriceView=1&adults=2&children=0&rooms=1&los=1&checkin=2026-02-07',
        'rooms': ['싱글룸', '트윈룸', '이코노믹 더블', '더블룸', '트리플룸']
    },
    'hotel_nafore': {
        'name': '나포레호텔',
        'url': 'https://www.agoda.com/ko-kr/hotel-nafore/hotel/seoul-kr.html?finalPriceView=1&adults=2&children=0&rooms=1&los=1&checkin=2026-02-07',
        'rooms': ['슈페리어 더블', '슈페리어 트윈', '디럭스 더블룸']
    }
}

def clean_room_name(text):
    m = re.search(r'^([^(]*\([^)]*\))', text)
    if m:
        return m.group(1).strip()
    return text.strip()

def debug_hotel(hotel_id, hotel_info, driver):
    print(f"\n{'='*100}")
    print(f"🏨 {hotel_info['name']}")
    print(f"{'='*100}")
    
    driver.get(hotel_info['url'])
    time.sleep(15)
    
    # 스크롤
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)
    
    # roomGrid로 스크롤
    try:
        room_grid = driver.find_element(By.ID, 'roomGrid')
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", room_grid)
        time.sleep(2)
    except:
        pass
    
    # 모든 요소 검사
    all_elements = driver.find_elements(By.XPATH, '//*')
    print(f"총 {len(all_elements)}개 요소 검사 중...")
    
    target_rooms = hotel_info['rooms']
    
    for target_room in target_rooms:
        print(f"\n{'='*100}")
        print(f"🔍 타겟 객실: {target_room}")
        print(f"{'='*100}")
        
        found = False
        
        for elem in all_elements:
            try:
                elem_text = elem.text.strip()
                if not elem_text or len(elem_text) > 500:
                    continue
                
                if target_room in elem_text:
                    # 가격 패턴 찾기
                    prices = re.findall(r'₩\s*([\d,]+)', elem_text)
                    
                    if prices:
                        print(f"\n발견된 요소 텍스트:")
                        print(f"  {elem_text[:200]}")
                        print(f"\n추출된 가격들:")
                        for p in prices:
                            price_val = int(p.replace(',', ''))
                            if 10000 <= price_val <= 500000:
                                print(f"  ₩{price_val:,}")
                        
                        # pd-crossedout-container 찾기
                        try:
                            containers = elem.find_elements(By.CSS_SELECTOR, 'div.pd-crossedout-container')
                            if containers:
                                print(f"\n  ✓ pd-crossedout-container 발견: {len(containers)}개")
                                for idx, container in enumerate(containers):
                                    print(f"\n  === Container #{idx + 1} ===")
                                    spans = container.find_elements(By.TAG_NAME, 'span')
                                    for span_idx, span in enumerate(spans):
                                        span_text = span.text.strip()
                                        if span_text:
                                            print(f"    Span #{span_idx}: {span_text}")
                        except:
                            pass
                        
                        # rareFind 찾기
                        try:
                            rare_finds = elem.find_elements(By.CSS_SELECTOR, 'div[class*="rareFind"]')
                            if rare_finds:
                                print(f"\n  ✓ rareFind 발견: {len(rare_finds)}개")
                                for idx, rare in enumerate(rare_finds):
                                    rare_class = rare.get_attribute('class')
                                    print(f"    rareFind #{idx + 1}: {rare_class}")
                        except:
                            pass
                        
                        # installment 키워드 확인
                        if 'installment' in elem_text.lower() or '할부' in elem_text:
                            print(f"\n  ⚠️ 할부 가격 포함됨!")
                        
                        found = True
                        break
                        
            except:
                continue
        
        if not found:
            print(f"  ✗ 객실을 찾을 수 없습니다")

def main():
    print("Chrome 드라이버 시작...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        for hotel_id, hotel_info in HOTELS.items():
            debug_hotel(hotel_id, hotel_info, driver)
            time.sleep(3)
    finally:
        driver.quit()
        print("\n브라우저 종료")

if __name__ == "__main__":
    main()
