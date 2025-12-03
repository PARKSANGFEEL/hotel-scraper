from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import re
import os
import json
from datetime import datetime

# 호텔 설정
HOTELS = {
    'hotel_rian': {
        'name': '리안호텔 (경쟁사)',
        'url': 'https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1439847&numberOfBedrooms=&familyMode=false&adults=2&children=0&rooms=1&maxRooms=0&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=1&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&tag=4f122210-314e-4c70-b18b-ac93fc25b69f&flightSearchCriteria=%5Bobject%20Object%5D&los=1&searchrequestid=1db7a87b-052d-42f2-8e2b-353298d15809&utm_medium=banner&utm_source=naver&utm_campaign=naverbz&utm_content=nbz10&utm_term=nbz10&ds=qbRdfmY8zNLy%2B9RI&checkin=2026-01-04'
    },
    'grid_inn': {
        'name': '그리드인 호텔 (우리)',
        'url': 'https://www.agoda.com/ko-kr/grid-inn/hotel/seoul-kr.html?asq=46IF%20cRFj4y4BDwHsggAopufa9Vwpz6XltTHq4n%209gNTE7xxbUyivb6kJfSq5SJCQePARA0hTuzFMP08%20pmCoRvYV6rul7urWDIqqrLix%2FAjp8KRnuZ17JKIQGaaXkoQPlf0DiAWc27mEpbHtIADfF4sl%2FP%2FByd40g43x6GjslUwOZKzBk6g0AELDqy5uZrQBgUtJQsPt5TbKA%20nP5BtVDPf0vSJuFYXa8M%20K1VbW4kPuFgAg81zFV%2FrrekpX65iZdO%20vquVfbkOvNTVI3PtInZvFKwwWQLG%204xywNOKwvxKiWUGfCWjVKNB5PVwA%2FRR&hotel=1709863&ds=vLcBmFEZaDK0SVrG&checkin=2026-01-04&los=1'
    },
    'hotel_nafore': {
        'name': '나포레호텔 (경쟁사)',
        'url': 'https://www.agoda.com/ko-kr/hotel-nafore/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1719676&numberOfBedrooms=&familyMode=false&adults=1&children=0&rooms=1&maxRooms=0&checkIn=2026-01-04&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=0&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&flightSearchCriteria=%5Bobject+Object%5D&tspTypes=16&los=1&searchrequestid=9bb7cbfd-fba8-4ee5-bb93-bb85a746dae1&ds=vLcBmFEZaDK0SVrG'
    }
}

OUTPUT_DIR = r"c:\Users\User\Downloads\파이썬기초"
PRICE_HISTORY_FILE = os.path.join(OUTPUT_DIR, "price_history_multi.json")

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

def scrape_hotel(hotel_id, hotel_info, checkin_date, driver):
    """특정 호텔의 가격 수집"""
    print(f"\n{'='*100}")
    print(f"🏨 {hotel_info['name']}")
    print(f"{'='*100}")
    
    try:
        # URL의 날짜 부분 교체
        url = hotel_info['url']
        # 다양한 날짜 형식 처리
        url = re.sub(r'checkin=[\d-]+', f'checkin={checkin_date}', url)
        url = re.sub(r'checkIn=[\d-]+', f'checkIn={checkin_date}', url)
        
        print(f"URL 접속 중...")
        driver.get(url)
        time.sleep(12)
        
        h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
        print(f"총 {len(h4_elements)}개의 h4 태그 발견\n")
        
        results = []
        processed_rooms = set()
        
        for h4 in h4_elements:
            try:
                room_name_raw = h4.text.strip()
                room_name = clean_room_name(room_name_raw)
                
                # 룸 타입 필터링 (한글/영문 모두)
                if not any(kw in room_name for kw in ['룸', 'Room', 'Twin', 'Double', 'Deluxe', 'Family', 
                                                        '스탠다드', '디럭스', '패밀리', 'Standard', 'Suite']):
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
                
                # 할인가 추출
                discounted_price = None
                coupon_discount = None
                
                try:
                    all_text = room_card.text
                    
                    # 쿠폰 할인액 찾기
                    coupon_match = re.search(r'₩\s*([\d,]+)\s*적용됨', all_text)
                    if coupon_match:
                        coupon_discount = int(coupon_match.group(1).replace(',', ''))
                        print(f"  ✓ 쿠폰 할인: ₩{coupon_discount:,}")
                    
                    if not coupon_discount:
                        coupon_match = re.search(r'₩\s*([\d,]+)\s*할인', all_text)
                        if coupon_match:
                            coupon_discount = int(coupon_match.group(1).replace(',', ''))
                            print(f"  ✓ 쿠폰 할인: ₩{coupon_discount:,}")
                    
                    if coupon_discount and original_price:
                        orig_val = int(original_price)
                        discounted_price = orig_val - coupon_discount
                        print(f"  ✓ 할인가: ₩{discounted_price:,}")
                    else:
                        print(f"  ✗ 쿠폰 할인 정보 없음")
                
                except Exception as e:
                    print(f"  ✗ 할인가 추출 실패: {e}")
                
                if discounted_price and original_price:
                    savings = int(original_price) - discounted_price
                    discount_rate = int((savings / int(original_price)) * 100)
                    
                    results.append({
                        'hotel': hotel_info['name'],
                        'hotel_id': hotel_id,
                        'room_type': room_name,
                        'original_price': int(original_price),
                        'discounted_price': discounted_price,
                        'savings': savings,
                        'discount_rate': discount_rate
                    })
                
                print()
                
            except Exception as e:
                print(f"  ❌ 오류: {e}\n")
                continue
        
        print(f"✅ {hotel_info['name']}: {len(results)}개 객실 수집 완료\n")
        return results
        
    except Exception as e:
        print(f"❌ {hotel_info['name']} 스크래핑 오류: {e}\n")
        import traceback
        traceback.print_exc()
        return []

def compare_hotels(all_results, checkin_date):
    """호텔 간 가격 비교"""
    print(f"\n{'='*100}")
    print(f"📊 호텔 가격 비교 분석 - {checkin_date}")
    print(f"{'='*100}\n")
    
    if not all_results:
        print("수집된 데이터가 없습니다.")
        return
    
    # 호텔별 평균 가격
    print("1️⃣ 호텔별 가격 요약")
    print("-" * 100)
    hotel_stats = {}
    for result in all_results:
        hotel = result['hotel']
        if hotel not in hotel_stats:
            hotel_stats[hotel] = {'prices': [], 'rooms': 0}
        hotel_stats[hotel]['prices'].append(result['discounted_price'])
        hotel_stats[hotel]['rooms'] += 1
    
    print(f"{'호텔명':<35} {'객실수':<10} {'평균가격':<15} {'최저가':<15} {'최고가':<15}")
    print("-" * 100)
    for hotel, stats in hotel_stats.items():
        avg_price = sum(stats['prices']) / len(stats['prices'])
        min_price = min(stats['prices'])
        max_price = max(stats['prices'])
        print(f"{hotel:<35} {stats['rooms']:<10} ₩{avg_price:>12,.0f} ₩{min_price:>12,} ₩{max_price:>12,}")
    
    # 최저가 객실 TOP 10
    print(f"\n2️⃣ 전체 최저가 객실 TOP 10")
    print("-" * 100)
    sorted_results = sorted(all_results, key=lambda x: x['discounted_price'])[:10]
    
    print(f"{'순위':<8} {'호텔':<30} {'객실':<35} {'할인가':<15}")
    print("-" * 100)
    for idx, result in enumerate(sorted_results, 1):
        hotel_display = result['hotel'][:28] + '..' if len(result['hotel']) > 30 else result['hotel']
        room_display = result['room_type'][:33] + '..' if len(result['room_type']) > 35 else result['room_type']
        print(f"{idx:<8} {hotel_display:<30} {room_display:<35} ₩{result['discounted_price']:>12,}")
    
    # 그리드인 vs 경쟁사 비교
    print(f"\n3️⃣ 그리드인 호텔 경쟁력 분석")
    print("-" * 100)
    
    grid_inn_prices = [r['discounted_price'] for r in all_results if r['hotel_id'] == 'grid_inn']
    competitor_prices = [r['discounted_price'] for r in all_results if r['hotel_id'] != 'grid_inn']
    
    if grid_inn_prices and competitor_prices:
        grid_avg = sum(grid_inn_prices) / len(grid_inn_prices)
        grid_min = min(grid_inn_prices)
        comp_avg = sum(competitor_prices) / len(competitor_prices)
        comp_min = min(competitor_prices)
        
        print(f"그리드인 호텔 (우리)")
        print(f"  • 평균 가격: ₩{grid_avg:,.0f}")
        print(f"  • 최저 가격: ₩{grid_min:,}")
        print(f"  • 객실 수: {len(grid_inn_prices)}개\n")
        
        print(f"경쟁사 (리안 + 나포레)")
        print(f"  • 평균 가격: ₩{comp_avg:,.0f}")
        print(f"  • 최저 가격: ₩{comp_min:,}")
        print(f"  • 객실 수: {len(competitor_prices)}개\n")
        
        if grid_avg < comp_avg:
            diff = comp_avg - grid_avg
            percent = (diff / comp_avg) * 100
            print(f"✅ 우리가 평균 ₩{diff:,.0f} ({percent:.1f}%) 저렴합니다!")
        else:
            diff = grid_avg - comp_avg
            percent = (diff / grid_avg) * 100
            print(f"⚠️ 경쟁사가 평균 ₩{diff:,.0f} ({percent:.1f}%) 저렴합니다.")
        
        if grid_min < comp_min:
            diff = comp_min - grid_min
            print(f"✅ 우리의 최저가가 ₩{diff:,} 더 저렴합니다!")
        else:
            diff = grid_min - comp_min
            print(f"⚠️ 경쟁사의 최저가가 ₩{diff:,} 더 저렴합니다.")
    elif grid_inn_prices:
        print("⚠️ 경쟁사 데이터가 수집되지 않았습니다.")
    else:
        print("⚠️ 그리드인 호텔 데이터가 수집되지 않았습니다.")

def save_results(all_results, checkin_date):
    """결과를 CSV로 저장"""
    if not all_results:
        return
    
    # 전체 결과 저장
    csv_filename = os.path.join(OUTPUT_DIR, f"hotel_comparison_{checkin_date}.csv")
    print(f"\n💾 결과 저장: {csv_filename}")
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['hotel', 'room_type', 'original_price', 'discounted_price', 'savings', 'discount_rate']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in all_results:
            writer.writerow({
                'hotel': result['hotel'],
                'room_type': result['room_type'],
                'original_price': result['original_price'],
                'discounted_price': result['discounted_price'],
                'savings': result['savings'],
                'discount_rate': result['discount_rate']
            })
    
    print(f"✅ {len(all_results)}개 객실 정보 저장 완료!")

def check_price_changes(all_results, checkin_date):
    """가격 변동 체크"""
    price_history = load_price_history()
    price_drops = []
    price_increases = []
    
    for result in all_results:
        key = f"{checkin_date}_{result['hotel_id']}_{result['room_type']}"
        
        if key in price_history:
            prev_price = price_history[key]
            curr_price = result['discounted_price']
            
            if curr_price < prev_price:
                drop = prev_price - curr_price
                drop_percent = int((drop / prev_price) * 100)
                price_drops.append({
                    'hotel': result['hotel'],
                    'room': result['room_type'],
                    'prev': prev_price,
                    'curr': curr_price,
                    'drop': drop,
                    'percent': drop_percent
                })
            elif curr_price > prev_price:
                increase = curr_price - prev_price
                increase_percent = int((increase / prev_price) * 100)
                price_increases.append({
                    'hotel': result['hotel'],
                    'room': result['room_type'],
                    'prev': prev_price,
                    'curr': curr_price,
                    'increase': increase,
                    'percent': increase_percent
                })
        
        price_history[key] = result['discounted_price']
    
    save_price_history(price_history)
    
    # 가격 변동 출력
    if price_drops or price_increases:
        print(f"\n{'='*100}")
        print(f"💰 가격 변동 알림")
        print(f"{'='*100}\n")
        
        if price_drops:
            print(f"🔻 가격 하락: {len(price_drops)}개 객실")
            print("-" * 100)
            for drop in price_drops:
                print(f"{drop['hotel']:<35} {drop['room']:<35}")
                print(f"  ₩{drop['prev']:,} → ₩{drop['curr']:,} (▼₩{drop['drop']:,} / {drop['percent']}%)")
            print()
        
        if price_increases:
            print(f"🔺 가격 상승: {len(price_increases)}개 객실")
            print("-" * 100)
            for inc in price_increases:
                print(f"{inc['hotel']:<35} {inc['room']:<35}")
                print(f"  ₩{inc['prev']:,} → ₩{inc['curr']:,} (▲₩{inc['increase']:,} / {inc['percent']}%)")

def main():
    print("="*100)
    print("🏨 다중 호텔 가격 비교 시스템")
    print("="*100)
    
    # 체크인 날짜 설정
    checkin_date = "2026-01-04"  # 2026년 1월 4일로 고정
    
    print(f"\n📅 체크인 날짜: {checkin_date}")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Chrome 드라이버 시작
    print("Chrome 드라이버 시작 중...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--headless')  # 테스트를 위해 브라우저 표시
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        all_results = []
        
        # 각 호텔 순회
        for hotel_id, hotel_info in HOTELS.items():
            results = scrape_hotel(hotel_id, hotel_info, checkin_date, driver)
            all_results.extend(results)
            time.sleep(3)  # 호텔 간 대기
        
        # 결과 비교 및 저장
        compare_hotels(all_results, checkin_date)
        save_results(all_results, checkin_date)
        check_price_changes(all_results, checkin_date)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n브라우저 종료")
    
    print(f"\n{'='*100}")
    print("✅ 모든 작업 완료!")
    print(f"🕐 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*100}")

if __name__ == '__main__':
    main()