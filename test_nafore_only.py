from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import re
import os
import json
from datetime import datetime, timedelta

# 나포레 호텔만 테스트
HOTELS = {
    'hotel_nafore': {
        'name': '나포레호텔 (경쟁사)',
        'url': 'https://www.agoda.com/ko-kr/hotel-nafore/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1719676&numberOfBedrooms=&familyMode=false&adults=1&children=0&rooms=1&maxRooms=0&checkIn=2026-01-04&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=0&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&flightSearchCriteria=%5Bobject+Object%5D&tspTypes=16&los=1&searchrequestid=9bb7cbfd-fba8-4ee5-bb93-bb85a746dae1&ds=vLcBmFEZaDK0SVrG'
    }
}

OUTPUT_DIR = r"c:\Users\User\Downloads\파이썬기초"

def clean_room_name(text):
    m = re.search(r'^([^(]*\([^)]*\))', text)
    if m:
        return m.group(1).strip()
    return text.strip()

def scrape_hotel(hotel_id, hotel_info, checkin_date, driver):
    """특정 호텔의 가격 수집"""
    print(f"\n{'='*100}")
    print(f"🏨 {hotel_info['name']}")
    print(f"{'='*100}")
    
    url = hotel_info['url'].replace('checkIn=2026-01-04', f'checkIn={checkin_date}')
    
    print("URL 접속 중...")
    driver.get(url)
    
    print("페이지 로딩 대기 중... (15초)")
    time.sleep(15)
    
    print("페이지 스크롤하여 모든 콘텐츠 로드 중...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)
    
    rooms = []
    h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
    print(f"총 {len(h4_elements)}개의 h4 태그 발견\n")
    
    other_rooms_list = []
    for h4 in h4_elements:
        try:
            h4_text = h4.text.strip()
            if h4_text:
                room_name = clean_room_name(h4_text)
                if room_name and room_name not in other_rooms_list:
                    other_rooms_list.append(room_name)
        except:
            pass
    
    for h4 in h4_elements:
        try:
            h4_text = h4.text.strip()
            if not h4_text:
                continue
            
            room_name = clean_room_name(h4_text)
            if not room_name:
                continue
            
            print(f"\n[{room_name}]")
            
            # 부모 컨테이너 찾기
            current_element = h4
            room_card = None
            for level in range(40):
                current_element = current_element.find_element(By.XPATH, '..')
                if room_name in current_element.text:
                    has_other_rooms = any(
                        other in current_element.text 
                        for other in other_rooms_list 
                        if other != room_name
                    )
                    if not has_other_rooms:
                        room_card = current_element
                        break
                else:
                    break
            
            if not room_card:
                print(f"  ✗ 가격 정보 없음")
                continue
            
            # === 가격 추출 ===
            original_price = None
            discounted_price = None
            discount_rate = None
            
            # 1. 할인율 찾기
            card_text = room_card.text
            discount_match = re.search(r'-(\d+)%', card_text)
            if discount_match:
                discount_rate = int(discount_match.group(1))
                print(f"  ✓ 할인율: {discount_rate}%")
            
            # 2. 할인가 찾기 (여러 방법 시도)
            # 방법 A: rareFind 컨테이너에서 우선 검색 (특별 할인 객실)
            if not discounted_price:
                try:
                    rare_containers = room_card.find_elements(By.CSS_SELECTOR, 'div[class*="rareFind"]')
                    for container in rare_containers:
                        spans = container.find_elements(By.TAG_NAME, 'span')
                        for span in spans:
                            span_text = span.text.strip()
                            # 숫자로 시작하는 span 찾기 (순수 숫자 또는 ₩ 포함)
                            if span_text and re.search(r'^\d{3}', span_text):
                                match = re.search(r'₩?\s*([\d,]+)', span_text)
                                if match:
                                    price = int(match.group(1).replace(',', ''))
                                    if 10000 <= price <= 1000000:
                                        discounted_price = price
                                        print(f"  ✓ 할인가 (rareFind): ₩{discounted_price:,}")
                                        break
                        if discounted_price:
                            break
                except:
                    pass
            
            # 방법 B: iwOmxK span (일반 객실)
            if not discounted_price:
                try:
                    price_spans = room_card.find_elements(By.CSS_SELECTOR, 'span.iwOmxK')
                    for span in price_spans:
                        span_text = span.text.strip()
                        # ₩ 기호가 있을 수도, 없을 수도 있음
                        match = re.search(r'₩?\s*([\d,]+)', span_text)
                        if match:
                            price_val = int(match.group(1).replace(',', ''))
                            if 10000 <= price_val <= 1000000:
                                discounted_price = price_val
                                print(f"  ✓ 할인가: ₩{discounted_price:,}")
                                break
                except:
                    pass
            
            # 방법 C: PriceDisplay 클래스 - 모든 span 검색
            if not discounted_price:
                try:
                    all_spans = room_card.find_elements(By.TAG_NAME, 'span')
                    price_candidates = []
                    for span in all_spans:
                        span_text = span.text.strip()
                        # 쉼표가 있는 숫자 (5자리 이상)
                        if re.match(r'^[\d,]+$', span_text) and len(span_text.replace(',', '')) >= 5:
                            price_val = int(span_text.replace(',', ''))
                            if 10000 <= price_val <= 1000000:
                                price_candidates.append(price_val)
                    
                    if price_candidates:
                        # 여러 가격 중에서 선택
                        if original_price:
                            # 원가보다 작은 것 중 가장 큰 것 (할인가)
                            valid = [p for p in price_candidates if p < original_price]
                            if valid:
                                discounted_price = max(valid)
                        else:
                            # 원가가 없으면 가장 작은 것을 할인가로
                            discounted_price = min(price_candidates)
                except:
                    pass
            
            if not discounted_price:
                print(f"  ✗ 할인가를 찾을 수 없습니다")
                continue
            
            # 3. 원가 찾기
            # 방법 A: pd-crossedout-container의 모든 인스턴스 검색
            if not original_price:
                try:
                    price_containers = room_card.find_elements(By.CSS_SELECTOR, 'div.pd-crossedout-container')
                    for container in price_containers:
                        spans = container.find_elements(By.TAG_NAME, 'span')
                        if len(spans) >= 2:
                            price_text = spans[1].text.strip()
                            match = re.search(r'₩?\s*([\d,]+)', price_text)
                            if match:
                                price = int(match.group(1).replace(',', ''))
                                if price > discounted_price and 10000 <= price <= 1000000:
                                    original_price = price
                                    print(f"  ✓ 원가: ₩{original_price:,}")
                                    break
                except:
                    pass
            
            # 방법 B: pd-crossedout-container 텍스트에서 모든 숫자 추출
            if not original_price:
                try:
                    price_containers = room_card.find_elements(By.CSS_SELECTOR, 'div.pd-crossedout-container')
                    for container in price_containers:
                        container_text = container.text
                        numbers = re.findall(r'\d{5,}', container_text.replace(',', ''))
                        for num_str in numbers:
                            price = int(num_str)
                            if price > discounted_price and 10000 <= price <= 1000000:
                                original_price = price
                                break
                        if original_price:
                            break
                except:
                    pass
            
            # 방법 C: 할인율로 역계산
            if not original_price and discount_rate:
                original_price = int(discounted_price / (1 - discount_rate / 100))
                print(f"  ✓ 원가 (역계산): ₩{original_price:,}")
            
            # 방법 D: "할인 없음"으로 표시된 경우 재검색
            if not original_price:
                try:
                    all_spans = room_card.find_elements(By.TAG_NAME, 'span')
                    for span in all_spans:
                        span_text = span.text.strip()
                        if '₩' in span_text and re.search(r'\d{5,}', span_text):
                            match = re.search(r'₩\s*([\d,]+)', span_text)
                            if match:
                                price = int(match.group(1).replace(',', ''))
                                if price > discounted_price and 10000 <= price <= 1000000:
                                    original_price = price
                                    print(f"  ✓ 원가 (재검색): ₩{original_price:,}")
                                    break
                except:
                    pass
            
            # 최종 처리
            if not original_price:
                original_price = discounted_price
                print(f"  ℹ️  할인 없음 (정가): ₩{original_price:,}")
            
            calculated_discount = int((1 - discounted_price / original_price) * 100) if original_price > 0 else 0
            savings = original_price - discounted_price
            
            rooms.append({
                'hotel_id': hotel_id,
                'hotel_name': hotel_info['name'],
                'room_name': room_name,
                'original_price': original_price,
                'discounted_price': discounted_price,
                'discount_rate': calculated_discount,
                'savings': savings
            })
            
        except Exception as e:
            continue
    
    print(f"\n✅ {hotel_info['name']}: {len(rooms)}개 객실 수집 완료\n")
    return rooms

def main():
    print(f"\n{'='*100}")
    print(f"🏨 나포레호텔 테스트")
    print(f"{'='*100}\n")
    
    checkin_date = input("체크인 날짜를 입력하세요 (YYYY-MM-DD, 예: 2026-01-04): ").strip()
    
    # 날짜 유효성 검사
    try:
        input_date = datetime.strptime(checkin_date, '%Y-%m-%d')
        today = datetime.now().date()
        
        if input_date.date() < today:
            print(f"❌ 오류: 과거 날짜({checkin_date})는 입력할 수 없습니다.")
            return
        
        if input_date.date() > today + timedelta(days=365):
            print(f"⚠️  경고: 1년 이상 미래 날짜입니다. 계속 진행합니다.")
        
        print(f"✅ 날짜 확인: {checkin_date}")
    except ValueError:
        print(f"❌ 오류: 잘못된 날짜 형식입니다. YYYY-MM-DD 형식으로 입력해주세요.")
        return
    
    print(f"\n📅 체크인 날짜: {checkin_date}")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Chrome 드라이버 설정
    print("Chrome 드라이버 시작 중...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        all_rooms = []
        for hotel_id, hotel_info in HOTELS.items():
            rooms = scrape_hotel(hotel_id, hotel_info, checkin_date, driver)
            all_rooms.extend(rooms)
        
        print(f"\n✅ 총 {len(all_rooms)}개 객실 정보 수집 완료!")
        
        # 결과 출력
        print(f"\n{'='*100}")
        print("📋 수집된 객실 정보")
        print(f"{'='*100}")
        for room in all_rooms:
            print(f"\n{room['room_name']}")
            print(f"  원가: ₩{room['original_price']:,}")
            print(f"  할인가: ₩{room['discounted_price']:,}")
            print(f"  할인율: {room['discount_rate']}%")
            print(f"  절감액: ₩{room['savings']:,}")
        
    finally:
        print("\n브라우저 종료")
        driver.quit()
    
    print(f"\n{'='*100}")
    print("✅ 모든 작업 완료!")
    print(f"🕐 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*100}")

if __name__ == "__main__":
    main()
