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

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
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
        print("페이지 로딩 대기 중... (20초)")
        time.sleep(20)
        
        print(f"페이지 스크롤하여 모든 콘텐츠 로드 중...")
        
        # 1. 객실 리스트 영역으로 명시적 스크롤 시도
        room_grid = None
        for grid_id in ["roomGrid", "roomGridContent", "property-room-grid-root"]:
            try:
                room_grid = driver.find_element(By.ID, grid_id)
                driver.execute_script("arguments[0].scrollIntoView(true);", room_grid)
                print(f"  ✓ {grid_id} 영역으로 이동")
                time.sleep(2)
                break
            except:
                pass
        
        if not room_grid:
            print("  ℹ️ roomGrid 관련 ID를 찾을 수 없음, 전체 스크롤 진행")

        # 2. 전체 스크롤 (Lazy Loading 유도)
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(5): # 횟수 늘림
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        # 3. 다시 위로 조금 올리기 (헤더 등에 가려지는 것 방지)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 디버깅용 스크린샷 및 HTML 저장
        driver.save_screenshot(os.path.join(OUTPUT_DIR, "debug_screenshot.png"))
        with open(os.path.join(OUTPUT_DIR, "debug_page.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"  📸 디버깅용 스크린샷 및 HTML 저장 완료")
        
        # Fallback 요소 확인
        fallbacks = driver.find_elements(By.CSS_SELECTOR, '[data-testid="room-item-fallback"]')
        if fallbacks:
            print(f"  ⚠️ {len(fallbacks)}개의 로딩 중인 객실(fallback) 발견. 페이지가 완전히 로드되지 않았거나 차단되었을 수 있습니다.")

        # 매진 여부 확인
        page_source = driver.page_source
        if "선택한 날짜의 객실이 매진되었습니다" in page_source or "아고다 객실 판매 완료!" in page_source:
            print("  ⚠️ 선택한 날짜에 객실이 매진되었습니다.")

        results = []
        processed_rooms = {}
        
        # 객실 이름 후보 요소 찾기
        # h4 외에도 h3, span 등 다양한 태그에서 키워드 검색
        # 검색 범위를 room_grid로 제한하면 좋지만, 없으면 body 전체
        search_scope = room_grid if room_grid else driver.find_element(By.TAG_NAME, 'body')
        
        # h3, h4, span 태그 수집
        potential_elements = search_scope.find_elements(By.CSS_SELECTOR, 'h3, h4, span, div')
        print(f"총 {len(potential_elements)}개의 태그 검사 중 (키워드 필터링)...")
        
        count = 0
        for element in potential_elements:
            try:
                text = element.text.strip()
                if not text: continue
                
                # 1. 제외 키워드 필터링 (객실 상세 정보 등 제외)
                if any(kw in text for kw in ['m²', '성인', '개', '크기', '전망', '침대', '흡연', '샤워', '욕조']):
                    continue
                
                # 2. 필수 키워드 필터링 (객실 이름에 포함될 법한 단어)
                # 'Bed', '베드'는 제외 (침대 정보와 혼동됨)
                # '싱글'도 '싱글베드' 때문에 위험하므로 '싱글룸'으로 변경하거나 주의
                valid_keywords = ['룸', 'Room', 'Twin', 'Double', 'Deluxe', 'Family', 
                                '스탠다드', '디럭스', '패밀리', 'Standard', 'Suite', '도미토리', 
                                'Studio', '스튜디오', 'Villa', '빌라', 'Cottage', '코티지']
                
                if not any(kw in text for kw in valid_keywords):
                    continue
                
                # 너무 긴 텍스트는 제외 (설명글일 수 있음)
                if len(text) > 50: continue
                
                # 숫자만 있거나 너무 짧은 경우 제외
                if len(text) < 3 or text.replace(',', '').isdigit(): continue

                room_name = clean_room_name(text)
                
                # h4로부터 상위로 올라가며 객실 카드 컨테이너 찾기
                current = element
                room_card = None
                for _ in range(10):
                    try:
                        current = current.find_element(By.XPATH, '..')
                        # 가격 정보가 있는 컨테이너 찾기 (₩ 기호 포함)
                        card_text = current.text
                        if '₩' in card_text and ('박' in card_text or 'night' in card_text or '요금' in card_text):
                            room_card = current
                            break
                    except:
                        pass
                
                if not room_card:
                    continue
                
                # 이미 처리한 카드인지 확인 (같은 카드 내에 여러 키워드가 있을 수 있음)
                # 카드의 WebElement ID를 사용할 수도 있지만, 여기서는 room_name + price 조합으로 중복 체크
                
                original_price = None
                discounted_price = None
                
                # 카드 내 텍스트에서 가격 추출
                card_text = room_card.text
                
                # 1. 원가 추출 (취소선 가격) - 할부 가격 제외
                try:
                    crossed_out = room_card.find_elements(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"], [data-testid="crossout-price"]')
                    if crossed_out:
                        original_price_text = crossed_out[0].text
                        # 할부 관련 텍스트 제외
                        if not any(x in original_price_text for x in ['월', 'month', '또는', 'installment']):
                            m = re.search(r'([\d,]+)', original_price_text)
                            if m:
                                price_candidate = int(m.group(1).replace(',', ''))
                                # 10,000원 이상의 합리적인 가격만 원가로 인정
                                if price_candidate >= 10000:
                                    original_price = price_candidate
                except:
                    pass
                
                # 2. 할인가 추출
                # "₩ 123,456" 패턴 찾기
                # 줄 단위로 분리하여 '월' 또는 'month'가 포함된 줄의 가격은 제외 (할부 가격 오인 방지)
                lines = card_text.split('\n')
                price_values = []
                
                for line in lines:
                    # 할부/월 납입 관련 텍스트가 있는 줄은 건너뜀
                    if any(x in line for x in ['월', 'month', 'installments', '또는', '부터', '개월']):
                        continue
                        
                    found = re.findall(r'₩\s*([\d,]+)', line)
                    for p in found:
                        try:
                            val = int(p.replace(',', ''))
                            # 50,000원 미만은 할부 월 금액일 가능성 높음
                            if val >= 50000:
                                price_values.append(val)
                        except:
                            pass
                
                if not price_values:
                     # Fallback: if strict filtering removed everything, try loose extraction
                    prices = re.findall(r'₩\s*([\d,]+)', card_text)
                    for p in prices:
                        try:
                            val = int(p.replace(',', ''))
                            price_values.append(val)
                        except:
                            pass

                if price_values:
                    # 중복 제거 및 정렬
                    price_values = sorted(list(set(price_values)), reverse=True)
                    
                    if original_price:
                        # 원가가 있는 경우: 원가보다 작은 가격 중 가장 큰 값이 할인가
                        candidates = [p for p in price_values if p < original_price and p != original_price]
                        if candidates:
                            discounted_price = max(candidates)
                        else:
                            # 원가보다 작은 가격이 없으면 가장 작은 가격을 할인가로
                            discounted_price = min(price_values)
                    else:
                        # 원가가 없는 경우: 가격이 2개 이상이면 큰 값=원가, 작은 값=할인가
                        if len(price_values) >= 2:
                            original_price = price_values[0]
                            discounted_price = price_values[1]
                        else:
                            # 가격이 1개만 있으면 그것이 할인가
                            discounted_price = price_values[0]
                            original_price = discounted_price

                if not discounted_price:
                    continue
                    
                if not original_price:
                    original_price = discounted_price

                # 중복 체크
                room_key = f"{room_name}_{discounted_price}"
                if room_key in processed_rooms:
                    continue
                processed_rooms[room_key] = True
                
                print(f"[{room_name}]")
                print(f"  ✓ 원가: ₩{original_price:,}")
                print(f"  ✓ 할인가: ₩{discounted_price:,}")
                
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
                count += 1
                
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
    
    # 기본값 설정 (오늘 날짜)
    default_date = datetime.now().strftime('%Y-%m-%d')
    
    while True:
        checkin_date = input(f"체크인 날짜를 입력하세요 (YYYY-MM-DD, Enter for {default_date}): ").strip()
        if not checkin_date:
            checkin_date = default_date
        
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
