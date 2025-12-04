from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import re
import os
import json
from datetime import datetime, timedelta

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
    if os.path.exists(PRICE_HISTORY_FILE):
        try:
            with open(PRICE_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_price_history(history):
    with open(PRICE_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

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
    
    try:
        url = hotel_info['url']
        url = re.sub(r'checkin=[\d-]+', f'checkin={checkin_date}', url)
        url = re.sub(r'checkIn=[\d-]+', f'checkIn={checkin_date}', url)
        
        print(f"URL 접속 중...")
        driver.get(url)
        print(f"페이지 로딩 대기 중... (15초)")
        time.sleep(15)
        
        print(f"페이지 스크롤하여 모든 콘텐츠 로드 중...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        results = []
        processed_rooms = {}
        
        h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
        print(f"총 {len(h4_elements)}개의 h4 태그 발견\n")
        
        for h4 in h4_elements:
            try:
                room_name_raw = h4.text.strip()
                room_name = clean_room_name(room_name_raw)
                
                if not any(kw in room_name for kw in ['룸', 'Room', 'Twin', 'Double', 'Deluxe', 'Family', 
                                                        '스탠다드', '디럭스', '패밀리', 'Standard', 'Suite', '싱글']):
                    continue
                
                print(f"[{room_name}]")
                
                # 상위 컨테이너 찾기 - 객실 이름이 포함된 가장 작은 가격 컨테이너
                current = h4
                room_card = None
                
                for level in range(40):
                    try:
                        current = current.find_element(By.XPATH, '..')
                        card_text = current.text
                        
                        # 조건: 
                        # 1. 현재 객실 이름이 포함되어 있어야 함
                        # 2. 가격 정보(5자리 이상 숫자)가 있어야 함
                        # 3. 너무 크지 않아야 함 (다른 객실 포함 방지)
                        if room_name in card_text and re.search(r'[\d,]{5,}', card_text):
                            # 다른 객실 이름이 포함되어 있으면 너무 큰 컨테이너
                            other_rooms_found = False
                            for other_h4 in h4_elements:
                                if other_h4 != h4:
                                    other_name = clean_room_name(other_h4.text.strip())
                                    if other_name and other_name != room_name and other_name in card_text:
                                        other_rooms_found = True
                                        break
                            
                            if not other_rooms_found:
                                room_card = current
                                break
                    except:
                        break
                
                if not room_card:
                    print(f"  ✗ 객실 카드 못 찾음\n")
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
                # 방법 A: iwOmxK span (가장 정확)
                if not discounted_price:
                    try:
                        price_spans = room_card.find_elements(By.CSS_SELECTOR, 'span.iwOmxK')
                        for span in price_spans:
                            span_text = span.text.strip()
                            if re.match(r'^[\d,]+$', span_text):
                                price_val = int(span_text.replace(',', ''))
                                if 10000 <= price_val <= 1000000:
                                    discounted_price = price_val
                                    print(f"  ✓ 할인가: ₩{discounted_price:,}")
                                    break
                    except:
                        pass
                
                # 방법 B: PriceDisplay 클래스 - 모든 span 검색
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
                            
                            if discounted_price:
                                print(f"  ✓ 할인가 (방법2): ₩{discounted_price:,}")
                    except Exception as e:
                        pass
                
                # 3. 원가 찾기 (정확도 순서대로 시도)
                # 방법 A: pd-crossedout-container의 두 번째 span (가장 정확)
                if not original_price:
                    try:
                        # rareFind 클래스 포함 여부와 상관없이 찾기
                        price_containers = room_card.find_elements(By.CSS_SELECTOR, 'div.pd-crossedout-container')
                        for container in price_containers:
                            try:
                                spans = container.find_elements(By.TAG_NAME, 'span')
                                if len(spans) >= 2:
                                    price_text = spans[1].text.strip()  # 두 번째 span
                                    m = re.search(r'([\d,]+)', price_text)
                                    if m:
                                        price_val = int(m.group(1).replace(',', ''))
                                        if 10000 <= price_val <= 10000000:
                                            original_price = price_val
                                            print(f"  ✓ 원가: ₩{original_price:,}")
                                            break
                            except:
                                continue
                    except:
                        pass
                
                # 방법 B: pd-crossedout-container 전체에서 큰 숫자 추출
                if not original_price:
                    try:
                        crossedout = room_card.find_element(By.CSS_SELECTOR, 'div.pd-crossedout-container')
                        # 모든 숫자 찾기
                        all_numbers = re.findall(r'([\d,]+)', crossedout.text)
                        for num_str in all_numbers:
                            try:
                                num = int(num_str.replace(',', ''))
                                # 합리적인 가격 범위의 가장 큰 값이 원가
                                if 10000 <= num <= 10000000:
                                    if not original_price or num > original_price:
                                        original_price = num
                            except:
                                pass
                        if original_price:
                            print(f"  ✓ 원가 (방법2): ₩{original_price:,}")
                    except:
                        pass
                
                # 방법 C: 할인율로 역산
                if not original_price and discount_rate and discounted_price:
                    original_price = int(discounted_price * 100 / (100 - discount_rate))
                    print(f"  ✓ 원가 (역산): ₩{original_price:,}")
                
                # 방법 D: 할인 없는 경우
                if not original_price and discounted_price and not discount_rate:
                    # 마지막으로 한번 더 원가 찾기 시도 (모든 span에서)
                    try:
                        all_spans = room_card.find_elements(By.TAG_NAME, 'span')
                        price_candidates = []
                        for span in all_spans:
                            span_text = span.text.strip()
                            if re.match(r'^[\d,]+$', span_text):
                                try:
                                    price_val = int(span_text.replace(',', ''))
                                    if 10000 <= price_val <= 10000000:
                                        price_candidates.append(price_val)
                                except:
                                    pass
                        
                        # 할인가보다 큰 가격이 있으면 그것이 원가
                        bigger_prices = [p for p in price_candidates if p > discounted_price]
                        if bigger_prices:
                            original_price = min(bigger_prices)  # 할인가와 가장 가까운 값
                            print(f"  ✓ 원가 (재검색): ₩{original_price:,}")
                        else:
                            original_price = discounted_price
                            print(f"  ℹ️  할인 없음 (정가): ₩{original_price:,}")
                    except:
                        original_price = discounted_price
                        print(f"  ℹ️  할인 없음 (정가): ₩{original_price:,}")
                
                # 검증
                if not discounted_price:
                    print(f"  ✗ 가격 정보 없음\n")
                    continue
                
                if not original_price:
                    original_price = discounted_price
                
                # 중복 체크
                room_key = f"{room_name}_{discounted_price}"
                if room_key in processed_rooms:
                    print(f"  ⚠️ 중복 건너뜀\n")
                    continue
                processed_rooms[room_key] = True
                
                savings = original_price - discounted_price
                discount_rate_final = int((savings / original_price) * 100) if original_price > 0 else 0
                
                results.append({
                    'hotel': hotel_info['name'],
                    'hotel_id': hotel_id,
                    'room_type': room_name,
                    'original_price': original_price,
                    'discounted_price': discounted_price,
                    'savings': savings,
                    'discount_rate': discount_rate_final
                })
                
                print()
                
            except Exception as e:
                continue
        
        print(f"✅ {hotel_info['name']}: {len(results)}개 객실 수집 완료\n")
        return results
        
    except Exception as e:
        print(f"❌ {hotel_info['name']} 스크래핑 오류: {e}\n")
        import traceback
        traceback.print_exc()
        return []

def compare_hotels(all_results, checkin_date):
    print(f"\n{'='*100}")
    print(f"📊 호텔 가격 비교 분석 - {checkin_date}")
    print(f"{'='*100}\n")
    
    if not all_results:
        print("수집된 데이터가 없습니다.")
        return
    
    print("1️⃣ 호텔별 가격 요약")
    print("-" * 100)
    hotel_stats = {}
    for result in all_results:
        hotel = result['hotel']
        if hotel not in hotel_stats:
            hotel_stats[hotel] = {'prices': [], 'count': 0}
        hotel_stats[hotel]['prices'].append(result['discounted_price'])
        hotel_stats[hotel]['count'] += 1
    
    print(f"{'호텔명':<40} {'객실수':>10} {'평균가격':>15} {'최저가':>15} {'최고가':>15}")
    print("-" * 100)
    for hotel, stats in hotel_stats.items():
        avg_price = sum(stats['prices']) / len(stats['prices'])
        min_price = min(stats['prices'])
        max_price = max(stats['prices'])
        print(f"{hotel:<40} {stats['count']:>10} ₩{avg_price:>14,.0f} ₩{min_price:>14,} ₩{max_price:>14,}")
    
    print(f"\n2️⃣ 전체 최저가 객실 TOP 10")
    print("-" * 100)
    sorted_results = sorted(all_results, key=lambda x: x['discounted_price'])
    print(f"{'순위':>5} {'호텔':<40} {'객실':<45} {'할인가':>15}")
    print("-" * 100)
    for i, result in enumerate(sorted_results[:10], 1):
        print(f"{i:>5} {result['hotel']:<40} {result['room_type']:<45} ₩{result['discounted_price']:>14,}")
    
    print(f"\n3️⃣ 그리드인 호텔 경쟁력 분석")
    print("-" * 100)
    grid_results = [r for r in all_results if '그리드인' in r['hotel']]
    competitor_results = [r for r in all_results if '그리드인' not in r['hotel']]
    
    if grid_results and competitor_results:
        grid_avg = sum(r['discounted_price'] for r in grid_results) / len(grid_results)
        grid_min = min(r['discounted_price'] for r in grid_results)
        comp_avg = sum(r['discounted_price'] for r in competitor_results) / len(competitor_results)
        comp_min = min(r['discounted_price'] for r in competitor_results)
        
        print(f"그리드인 호텔 (우리)")
        print(f"  • 평균 가격: ₩{grid_avg:,.0f}")
        print(f"  • 최저 가격: ₩{grid_min:,}")
        print(f"  • 객실 수: {len(grid_results)}개")
        print(f"\n경쟁사 (리안 + 나포레)")
        print(f"  • 평균 가격: ₩{comp_avg:,.0f}")
        print(f"  • 최저 가격: ₩{comp_min:,}")
        print(f"  • 객실 수: {len(competitor_results)}개")
        
        diff = comp_avg - grid_avg
        diff_pct = (diff / comp_avg) * 100
        if diff > 0:
            print(f"\n✅ 우리가 평균 ₩{diff:,.0f} ({diff_pct:.1f}%) 저렴합니다!")
        
        min_diff = comp_min - grid_min
        if min_diff > 0:
            print(f"✅ 우리의 최저가가 ₩{min_diff:,} 더 저렴합니다!")

def save_results(all_results, checkin_date):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f"hotel_comparison_{checkin_date}_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['호텔', '객실 타입', '원가', '할인가', '할인액', '할인율'])
        
        for result in all_results:
            writer.writerow([
                result['hotel'],
                result['room_type'],
                f"₩{result['original_price']:,}",
                f"₩{result['discounted_price']:,}",
                f"₩{result['savings']:,}",
                f"{result['discount_rate']}%"
            ])
    
    print(f"\n💾 결과 저장: {filepath}")
    print(f"✅ {len(all_results)}개 객실 정보 저장 완료!")

def check_price_changes(all_results, checkin_date):
    history = load_price_history()
    
    changes = {'increased': [], 'decreased': [], 'new': []}
    
    for result in all_results:
        key = f"{checkin_date}_{result['hotel_id']}_{result['room_type']}"
        current_price = result['discounted_price']
        
        if key in history:
            old_price = history[key]
            if current_price > old_price:
                diff = current_price - old_price
                pct = int((diff / old_price) * 100)
                changes['increased'].append((result, old_price, diff, pct))
            elif current_price < old_price:
                diff = old_price - current_price
                pct = int((diff / old_price) * 100)
                changes['decreased'].append((result, old_price, diff, pct))
        else:
            changes['new'].append(result)
        
        history[key] = current_price
    
    save_price_history(history)
    
    if any(changes.values()):
        print(f"\n{'='*100}")
        print("💰 가격 변동 알림")
        print(f"{'='*100}\n")
        
        if changes['decreased']:
            print(f"🔻 가격 하락: {len(changes['decreased'])}개 객실")
            print("-" * 100)
            for result, old_price, diff, pct in changes['decreased']:
                print(f"{result['hotel']:<40} {result['room_type']}")
                print(f"  ₩{old_price:,} → ₩{result['discounted_price']:,} (▼₩{diff:,} / {pct}%)")
        
        if changes['increased']:
            print(f"\n🔺 가격 상승: {len(changes['increased'])}개 객실")
            print("-" * 100)
            for result, old_price, diff, pct in changes['increased']:
                print(f"{result['hotel']:<40} {result['room_type']}")
                print(f"  ₩{old_price:,} → ₩{result['discounted_price']:,} (▲₩{diff:,} / {pct}%)")

def main():
    print(f"{'='*100}")
    print("🏨 다중 호텔 가격 비교 시스템")
    print(f"{'='*100}\n")
    
    while True:
        checkin_date = input("체크인 날짜를 입력하세요 (YYYY-MM-DD, 예: 2026-01-04): ").strip()
        
        try:
            input_date = datetime.strptime(checkin_date, '%Y-%m-%d')
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if input_date < today:
                print(f"❌ 과거 날짜는 입력할 수 없습니다. 오늘({today.strftime('%Y-%m-%d')}) 이후의 날짜를 입력하세요.")
                continue
            
            one_year_later = today + timedelta(days=365)
            if input_date > one_year_later:
                print(f"⚠️ 1년 이상 먼 날짜입니다. 정말 진행하시겠습니까? (y/n): ", end="")
                confirm = input().strip().lower()
                if confirm != 'y':
                    continue
            
            print(f"✅ 날짜 확인: {checkin_date}")
            break
            
        except ValueError:
            print("❌ 잘못된 날짜 형식입니다. YYYY-MM-DD 형식으로 입력하세요. (예: 2026-01-04)")
            continue
    
    print(f"\n📅 체크인 날짜: {checkin_date}")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("Chrome 드라이버 시작 중...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        all_results = []
        
        for hotel_id, hotel_info in HOTELS.items():
            results = scrape_hotel(hotel_id, hotel_info, checkin_date, driver)
            all_results.extend(results)
            time.sleep(3)
        
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
