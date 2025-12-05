from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re

# 나포레 호텔 설정
HOTEL_URL = 'https://www.agoda.com/ko-kr/hotel-nafore/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1719676&numberOfBedrooms=&familyMode=false&adults=1&children=0&rooms=1&maxRooms=0&checkIn=2026-01-04&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=0&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&flightSearchCriteria=%5Bobject+Object%5D&tspTypes=16&los=1&searchrequestid=9bb7cbfd-fba8-4ee5-bb93-bb85a746dae1&ds=vLcBmFEZaDK0SVrG'
TARGET_ROOM = '디럭스 트리플 (Deluxe Triple)'

def clean_room_name(text):
    m = re.search(r'^([^(]*\([^)]*\))', text)
    if m:
        return m.group(1).strip()
    return text.strip()

def debug_nafore_deluxe_triple():
    print(f"\n{'='*100}")
    print(f"🔍 나포레호텔 - 디럭스 트리플 디버깅")
    print(f"{'='*100}\n")
    
    # Chrome 드라이버 설정
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("URL 접속 중...")
        driver.get(HOTEL_URL)
        
        print("페이지 로딩 대기 중... (15초)")
        time.sleep(15)
        
        print("페이지 스크롤하여 모든 콘텐츠 로드 중...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # 모든 h4 태그 찾기
        h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
        print(f"총 {len(h4_elements)}개의 h4 태그 발견\n")
        
        target_room_found = False
        
        for h4 in h4_elements:
            try:
                h4_text = h4.text.strip()
                if not h4_text:
                    continue
                
                room_name = clean_room_name(h4_text)
                
                if TARGET_ROOM in room_name or room_name in TARGET_ROOM:
                    target_room_found = True
                    print(f"\n{'='*100}")
                    print(f"✅ 타겟 객실 발견: {room_name}")
                    print(f"{'='*100}")
                    
                    # 부모 컨테이너 찾기
                    current_element = h4
                    room_card = None
                    candidate_containers = []
                    
                    print("\n🔍 부모 컨테이너 탐색 중...")
                    for level in range(40):
                        try:
                            current_element = current_element.find_element(By.XPATH, '..')
                        except:
                            print(f"  ✗ Level {level}: 더 이상 부모 요소 없음")
                            break
                            
                        container_text = current_element.text[:200] if len(current_element.text) > 200 else current_element.text
                        
                        if room_name in current_element.text:
                            # 다른 객실 이름이 포함되어 있는지 확인
                            other_rooms = ['슈페리어 더블', '슈페리어 트윈', '디럭스 더블룸', '디럭스룸 (트윈베드)', '패밀리트윈']
                            has_other_rooms = any(other in current_element.text and other not in room_name for other in other_rooms)
                            
                            if not has_other_rooms:
                                # span 개수 확인
                                spans_count = len(current_element.find_elements(By.TAG_NAME, 'span'))
                                candidate_containers.append({
                                    'level': level,
                                    'element': current_element,
                                    'spans_count': spans_count,
                                    'text_sample': container_text
                                })
                                print(f"  후보 Level {level}: spans={spans_count}, 텍스트={container_text[:50]}...")
                            else:
                                # 다른 객실명이 나타나기 시작하면 탐색 중단
                                print(f"  ✗ Level {level}: 다른 객실명 포함됨, 탐색 중단")
                                break
                        else:
                            print(f"  ✗ Level {level}: 현재 객실명 없음, 탐색 중단")
                            break
                    
                    # span이 많은 컨테이너 선택 (가격 정보가 더 많을 가능성)
                    if candidate_containers:
                        best_container = max(candidate_containers, key=lambda x: x['spans_count'])
                        room_card = best_container['element']
                        print(f"\n✅ 최적 컨테이너 선택: Level {best_container['level']} (spans={best_container['spans_count']})")
                    else:
                        print("\n❌ 적합한 컨테이너를 찾을 수 없습니다!")
                        continue
                    
                    if not room_card:
                        print("❌ 적합한 room_card를 찾을 수 없습니다!")
                        continue
                    
                    print(f"\n✅ room_card 확정")
                    
                    # === 할인된 가격 추출 ===
                    print("\n" + "="*100)
                    print("💰 할인된 가격 (Discounted Price) 추출")
                    print("="*100)
                    
                    discounted_price = None
                    discount_rate_text = None
                    
                    # 방법 1: rareFind 컨테이너에서 찾기 (우선순위)
                    print("\n[방법 1] rareFind 컨테이너에서 검색...")
                    try:
                        rare_containers = room_card.find_elements(By.CSS_SELECTOR, 'div[class*="rareFind"]')
                        print(f"  발견된 rareFind 컨테이너: {len(rare_containers)}개")
                        
                        for idx, container in enumerate(rare_containers):
                            container_class = container.get_attribute('class')
                            print(f"\n  === rareFind Container #{idx + 1} ===")
                            print(f"  Class: {container_class}")
                            
                            # rareFind 컨테이너 내부의 모든 span 찾기
                            spans = container.find_elements(By.TAG_NAME, 'span')
                            print(f"  내부 span 개수: {len(spans)}")
                            
                            for span_idx, span in enumerate(spans):
                                span_text = span.text.strip()
                                span_class = span.get_attribute('class')
                                if span_text and re.search(r'\d', span_text):
                                    print(f"    Span #{span_idx}: '{span_text}' (class: {span_class[:50] if span_class else 'None'}...)")
                                
                                # 가격 추출 시도
                                if span_text and re.search(r'^\d{3}', span_text):  # 숫자로 시작
                                    match = re.search(r'₩?\s*([\d,]+)', span_text)
                                    if match:
                                        price = int(match.group(1).replace(',', ''))
                                        if 30000 <= price <= 500000:
                                            discounted_price = price
                                            print(f"  ✅ rareFind에서 할인가 발견: ₩{price:,}")
                                            break
                            
                            if discounted_price:
                                break
                    except Exception as e:
                        print(f"  ✗ 방법 1 실패: {str(e)}")
                    
                    # 방법 2: span.iwOmxK 찾기
                    if not discounted_price:
                        print("\n[방법 2] span.iwOmxK 검색...")
                        try:
                            price_span = room_card.find_element(By.CSS_SELECTOR, 'span.iwOmxK')
                            price_text = price_span.text.strip()
                            print(f"  ✓ span.iwOmxK 발견: '{price_text}'")
                            
                            # ₩ 기호가 있을 수도, 없을 수도 있음
                            match = re.search(r'₩?\s*([\d,]+)', price_text)
                            if match:
                                discounted_price = int(match.group(1).replace(',', ''))
                                print(f"  ✓ 추출된 할인가: ₩{discounted_price:,}")
                        except Exception as e:
                            print(f"  ✗ span.iwOmxK 찾기 실패: {str(e)}")
                    
                    # 방법 2: 모든 span에서 가격 찾기
                    if not discounted_price:
                        print("\n[방법 3] 모든 span 태그에서 가격 검색...")
                        all_spans = room_card.find_elements(By.TAG_NAME, 'span')
                        print(f"  총 {len(all_spans)}개의 span 발견")
                        
                        for idx, span in enumerate(all_spans):
                            span_text = span.text.strip()
                            if '₩' in span_text and re.search(r'\d{5,}', span_text):
                                match = re.search(r'₩\s*([\d,]+)', span_text)
                                if match:
                                    price = int(match.group(1).replace(',', ''))
                                    if 30000 <= price <= 500000:
                                        discounted_price = price
                                        print(f"  ✓ Span #{idx}: '{span_text}' → ₩{price:,}")
                                        break
                    
                    if discounted_price:
                        print(f"\n✅ 최종 할인가: ₩{discounted_price:,}")
                    else:
                        print("\n❌ 할인가를 찾을 수 없습니다!")
                        continue
                    
                    # === 할인율 추출 ===
                    print("\n" + "="*100)
                    print("📊 할인율 (Discount Rate) 추출")
                    print("="*100)
                    
                    all_spans = room_card.find_elements(By.TAG_NAME, 'span')
                    print(f"\n총 {len(all_spans)}개의 span 검색 중...")
                    
                    for idx, span in enumerate(all_spans):
                        span_text = span.text.strip()
                        if '%' in span_text:
                            print(f"  Span #{idx}: '{span_text}'")
                            discount_match = re.search(r'-(\d+)%', span_text)
                            if discount_match:
                                discount_rate_text = span_text
                                print(f"  ✓ 할인율 발견: {discount_rate_text}")
                                break
                    
                    # === 원가 추출 ===
                    print("\n" + "="*100)
                    print("💵 원가 (Original Price) 추출")
                    print("="*100)
                    
                    original_price = None
                    
                    # 방법 A: pd-crossedout-container의 모든 인스턴스 검색
                    print("\n[방법 A] pd-crossedout-container의 모든 span 검색...")
                    try:
                        price_containers = room_card.find_elements(By.CSS_SELECTOR, 'div.pd-crossedout-container')
                        print(f"  발견된 pd-crossedout-container 개수: {len(price_containers)}")
                        
                        for container_idx, container in enumerate(price_containers):
                            print(f"\n  === Container #{container_idx + 1} ===")
                            container_class = container.get_attribute('class')
                            print(f"  Class: {container_class}")
                            
                            spans = container.find_elements(By.TAG_NAME, 'span')
                            print(f"  내부 span 개수: {len(spans)}")
                            
                            for span_idx, span in enumerate(spans):
                                span_text = span.text.strip()
                                span_class = span.get_attribute('class')
                                print(f"    Span #{span_idx}: '{span_text}' (class: {span_class})")
                            
                            # 두 번째 span 추출 시도
                            if len(spans) >= 2:
                                price_text = spans[1].text.strip()
                                print(f"\n  ✓ spans[1] (두 번째 span) 텍스트: '{price_text}'")
                                
                                match = re.search(r'₩?\s*([\d,]+)', price_text)
                                if match:
                                    price = int(match.group(1).replace(',', ''))
                                    if price > discounted_price and 30000 <= price <= 500000:
                                        original_price = price
                                        print(f"  ✅ 원가 추출 성공: ₩{original_price:,}")
                                        break
                    except Exception as e:
                        print(f"  ✗ 방법 A 실패: {str(e)}")
                    
                    # 방법 B: pd-crossedout-container 텍스트에서 모든 숫자 추출
                    if not original_price:
                        print("\n[방법 B] pd-crossedout-container 전체 텍스트에서 숫자 추출...")
                        try:
                            price_containers = room_card.find_elements(By.CSS_SELECTOR, 'div.pd-crossedout-container')
                            for container in price_containers:
                                container_text = container.text
                                print(f"  컨테이너 텍스트: '{container_text}'")
                                
                                numbers = re.findall(r'\d{5,}', container_text.replace(',', ''))
                                print(f"  발견된 숫자들: {numbers}")
                                
                                for num_str in numbers:
                                    price = int(num_str)
                                    if price > discounted_price and 30000 <= price <= 500000:
                                        original_price = price
                                        print(f"  ✓ 원가 후보: ₩{price:,}")
                                        break
                                if original_price:
                                    break
                        except Exception as e:
                            print(f"  ✗ 방법 B 실패: {str(e)}")
                    
                    # 방법 C: 할인율로 역계산
                    if not original_price and discount_rate_text:
                        print("\n[방법 C] 할인율로 역계산...")
                        discount_match = re.search(r'-(\d+)%', discount_rate_text)
                        if discount_match:
                            discount_rate = int(discount_match.group(1))
                            original_price = int(discounted_price / (1 - discount_rate / 100))
                            print(f"  할인율: {discount_rate}%")
                            print(f"  ✓ 역계산된 원가: ₩{original_price:,}")
                    
                    # 방법 D: "할인 없음"으로 표시된 경우 재검색
                    if not original_price:
                        print("\n[방법 D] 전체 span에서 할인가보다 큰 가격 재검색...")
                        all_spans = room_card.find_elements(By.TAG_NAME, 'span')
                        for span in all_spans:
                            span_text = span.text.strip()
                            if '₩' in span_text and re.search(r'\d{5,}', span_text):
                                match = re.search(r'₩\s*([\d,]+)', span_text)
                                if match:
                                    price = int(match.group(1).replace(',', ''))
                                    if price > discounted_price and 30000 <= price <= 500000:
                                        original_price = price
                                        print(f"  ✓ 재검색으로 발견: '{span_text}' → ₩{original_price:,}")
                                        break
                    
                    # === 최종 결과 ===
                    print("\n" + "="*100)
                    print("📋 최종 결과")
                    print("="*100)
                    print(f"객실명: {room_name}")
                    print(f"할인율: {discount_rate_text if discount_rate_text else '정보 없음'}")
                    print(f"할인가: ₩{discounted_price:,}")
                    if original_price:
                        print(f"원가: ₩{original_price:,}")
                        calculated_discount = int((1 - discounted_price / original_price) * 100)
                        savings = original_price - discounted_price
                        print(f"실제 할인율: {calculated_discount}%")
                        print(f"절감액: ₩{savings:,}")
                    else:
                        print(f"원가: 할인 없음 (정가 ₩{discounted_price:,})")
                    print("="*100)
                    
                    break
                    
            except Exception as e:
                continue
        
        if not target_room_found:
            print(f"\n❌ '{TARGET_ROOM}' 객실을 찾을 수 없습니다!")
        
    finally:
        print("\n브라우저 종료")
        driver.quit()

if __name__ == "__main__":
    debug_nafore_deluxe_triple()
