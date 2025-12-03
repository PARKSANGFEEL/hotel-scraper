from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import re
import os
import json
from datetime import datetime

# 설정
BASE_URL = "https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1439847&numberOfBedrooms=&familyMode=false&adults=2&children=0&rooms=1&maxRooms=0&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=1&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&tag=4f122210-314e-4c70-b18b-ac93fc25b69f&flightSearchCriteria=%5Bobject%20Object%5D&los=1&searchrequestid=1db7a87b-052d-42f2-8e2b-353298d15809&utm_medium=banner&utm_source=naver&utm_campaign=naverbz&utm_content=nbz10&utm_term=nbz10&ds=qbRdfmY8zNLy%2B9RI&checkin=2026-01-04"
OUTPUT_DIR = r"c:\Users\User\Downloads\파이썬기초"
PRICE_HISTORY_FILE = os.path.join(OUTPUT_DIR, "price_history.json")

def load_price_history():
    """이전 가격 기록 불러오기"""
    if os.path.exists(PRICE_HISTORY_FILE):
        try:
            with open(PRICE_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_price_history(history):
    """가격 기록 저장"""
    with open(PRICE_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def clean_room_name(text):
    """룸 이름에서 불필요한 문구 제거"""
    m = re.search(r'^([^(]*\([^)]*\))', text)
    if m:
        return m.group(1).strip()
    return text.strip()

def scrape_agoda(checkin_date):
    """Agoda에서 실시간 가격 수집"""
    print(f"\n{'='*80}")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 체크인 날짜: {checkin_date}")
    print(f"{'='*80}\n")
    
    print("Chrome 드라이버 시작 중...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--headless')  # 테스트용으로 주석 처리
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        url_with_date = BASE_URL.replace("2026-01-04", checkin_date)
        
        print(f"URL 접속 중...\n")
        driver.get(url_with_date)
        time.sleep(12)
        
        h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
        print(f"총 {len(h4_elements)}개의 h4 태그 발견\n")
        
        results = []
        processed_rooms = set()
        price_history = load_price_history()
        price_drops = []
        
        for idx, h4 in enumerate(h4_elements, 1):
            try:
                room_name_raw = h4.text.strip()
                room_name = clean_room_name(room_name_raw)
                
                # 디버깅: 처음 5개 h4 태그 내용 출력
                if idx <= 5:
                    print(f"[DEBUG {idx}] h4 내용: '{room_name_raw}'")
                
                if not any(kw in room_name for kw in ['룸', 'Room', 'Twin', 'Double', 'Deluxe', 'Family']):
                    continue
                
                if room_name in processed_rooms:
                    continue
                processed_rooms.add(room_name)
                
                print(f"[{room_name}]")
                
                current = h4
                room_card = None
                for _ in range(20):
                    try:
                        current = current.find_element(By.XPATH, '..')
                        if current.find_element(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"]'):
                            room_card = current
                            break
                    except:
                        pass
                
                if not room_card:
                    print(f"  ✗ 객실 카드 못 찾음\n")
                    continue
                
                # 원가 추출
                original_price = None
                try:
                    crossed_out = room_card.find_element(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"]')
                    original_price_text = crossed_out.text
                    m = re.search(r'₩\s*([\d,]+)', original_price_text)
                    if m:
                        original_price = m.group(1).replace(',', '')
                        print(f"  ✓ 원가: ₩{int(original_price):,}")
                except:
                    pass
                
                # 할인가 추출 - 원가 - 쿠폰 할인액 방식
                discounted_price = None
                coupon_discount = None
                
                try:
                    # 전체 텍스트에서 쿠폰 할인액 찾기
                    all_text = room_card.text
                    print(f"  🔍 카드 텍스트 검색 중...")
                    
                    # 패턴 1: "₩ 10050 적용됨" 형식
                    coupon_match = re.search(r'₩\s*([\d,]+)\s*적용됨', all_text)
                    if coupon_match:
                        coupon_discount = int(coupon_match.group(1).replace(',', ''))
                        print(f"  ✓ 쿠폰 할인: ₩{coupon_discount:,} (패턴1: '적용됨')")
                    
                    # 패턴 2: "₩ 10,050 할인!" 형식
                    if not coupon_discount:
                        coupon_match = re.search(r'₩\s*([\d,]+)\s*할인', all_text)
                        if coupon_match:
                            coupon_discount = int(coupon_match.group(1).replace(',', ''))
                            print(f"  ✓ 쿠폰 할인: ₩{coupon_discount:,} (패턴2: '할인')")
                    
                    if coupon_discount and original_price:
                        orig_val = int(original_price)
                        discounted_price = orig_val - coupon_discount
                        print(f"  ✅ 할인가 계산: ₩{orig_val:,} - ₩{coupon_discount:,} = ₩{discounted_price:,}")
                        
                        # 검증: 할인가가 원가의 50%~95% 범위인지
                        percentage = (discounted_price / orig_val) * 100
                        if 50 <= percentage <= 95:
                            print(f"  ✅ 검증 통과: 원가의 {percentage:.1f}%")
                        else:
                            print(f"  ⚠️ 검증 실패: 원가의 {percentage:.1f}% (이상함)")
                            # 그래도 사용
                    else:
                        print(f"  ✗ 쿠폰 할인 정보 없음")
                
                except Exception as e:
                    print(f"  ✗ 할인가 추출 실패: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 가격 비교
                if discounted_price and original_price:
                    history_key = f"{checkin_date}_{room_name}"
                    if history_key in price_history:
                        prev_price = price_history[history_key]
                        if discounted_price < prev_price:
                            price_drop = prev_price - discounted_price
                            price_drop_percent = int((price_drop / prev_price) * 100)
                            print(f"  🔻 가격 하락! ₩{prev_price:,} → ₩{discounted_price:,} (▼{price_drop_percent}%)")
                            
                            price_drops.append({
                                'room': room_name,
                                'date': checkin_date,
                                'prev_price': prev_price,
                                'current_price': discounted_price,
                                'drop_amount': price_drop,
                                'drop_percent': price_drop_percent
                            })
                        elif discounted_price > prev_price:
                            price_increase = discounted_price - prev_price
                            print(f"  🔺 가격 상승! ₩{prev_price:,} → ₩{discounted_price:,} (₩{price_increase:,} 상승)")
                        else:
                            print(f"  ➡️ 가격 동일: ₩{discounted_price:,}")
                    else:
                        print(f"  ℹ️ 첫 수집")
                    
                    # 현재 가격 저장
                    price_history[history_key] = discounted_price
                    
                    # 결과 저장
                    savings = int(original_price) - discounted_price
                    discount_rate = int((savings / int(original_price)) * 100)
                    
                    results.append({
                        'room_type': room_name,
                        'original_price': original_price,
                        'discounted_price': str(discounted_price),
                        'savings': str(savings),
                        'discount_rate': str(discount_rate)
                    })
                
                print()
                
            except Exception as e:
                print(f"  ❌ 오류: {e}\n")
                continue
        
        # 가격 기록 저장
        save_price_history(price_history)
        
        # CSV 저장
        print(f"{'='*80}")
        print(f"수집된 객실: {len(results)}개\n")
        
        if results:
            print(f"{'룸 타입':<45} {'원가':<12} {'할인가':<12} {'절약금액':<12} {'할인율':<8}")
            print("-" * 80)
            for item in results:
                orig = f"₩{item['original_price']}" if item['original_price'] else "-"
                disc = f"₩{item['discounted_price']}" if item['discounted_price'] else "-"
                save = f"₩{item['savings']}" if item['savings'] else "-"
                rate = f"{item['discount_rate']}%" if item['discount_rate'] else "-"
                print(f"{item['room_type']:<45} {orig:<12} {disc:<12} {save:<12} {rate:<8}")
        
        csv_filename = os.path.join(OUTPUT_DIR, f"results_{checkin_date}_test.csv")  # 파일명 변경
        print(f"\n결과를 CSV로 저장: {csv_filename}")
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, 
                                   fieldnames=['room_type', 'original_price', 'discounted_price', 'savings', 'discount_rate'])
            writer.writeheader()
            writer.writerows(results)

        print(f"완료! {len(results)}개 객실 정보가 저장되었습니다.")
        
        # 가격 하락 요약
        if price_drops:
            print(f"\n🔔 가격 하락 알림: {len(price_drops)}개 객실")
            for drop in price_drops:
                print(f"  • {drop['room']}: ₩{drop['drop_amount']:,} 하락 (▼{drop['drop_percent']}%)")
        
        return results, price_drops
        
    except Exception as e:
        print(f"❌ 스크래핑 오류: {e}")
        return [], []
    finally:
        print("\n브라우저 종료")
        driver.quit()

if __name__ == '__main__':
    print("="*80)
    print("🏨 Agoda 호텔 가격 수집 (테스트 모드)")
    print("="*80)
    
    # 테스트할 날짜
    test_date = "2026-01-04"
    
    scrape_agoda(test_date)
    
    print(f"\n{'='*80}")
    print("✅ 테스트 완료!")
    print(f"{'='*80}")