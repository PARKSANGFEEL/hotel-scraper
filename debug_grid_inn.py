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
    'grid_inn': {
        'name': '그리드인 호텔 (우리)',
        'url': 'https://www.agoda.com/ko-kr/grid-inn/hotel/seoul-kr.html?asq=46IF%20cRFj4y4BDwHsggAopufa9Vwpz6XltTHq4n%209gNTE7xxbUyivb6kJfSq5SJCQePARA0hTuzFMP08%20pmCoRvYV6rul7urWDIqqrLix%2FAjp8KRnuZ17JKIQGaaXkoQPlf0DiAWc27mEpbHtIADfF4sl%2FP%2FByd40g43x6GjslUwOZKzBk6g0AELDqy5uZrQBgUtJQsPt5TbKA%20nP5BtVDPf0vSJuFYXa8M%20K1VbW4kPuFgAg81zFV%2FrrekpX65iZdO%20vquVfbkOvNTVI3PtInZvFKwwWQLG%204xywNOKwvxKiWUGfCWjVKNB5PVwA%2FRR&hotel=1709863&ds=vLcBmFEZaDK0SVrG&checkin=2026-01-04&los=1'
    }
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

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
        driver.save_screenshot(os.path.join(OUTPUT_DIR, "debug_grid_inn_screenshot.png"))
        with open(os.path.join(OUTPUT_DIR, "debug_grid_inn.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"  📸 디버깅용 스크린샷 및 HTML 저장 완료")
        
        results = []
        processed_rooms = {}
        
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
                
                # 디버깅 출력
                print(f"\n[DEBUG] Room: {room_name}")
                print(f"[DEBUG] Card Text Snippet: {card_text[:100].replace(chr(10), ' ')}...")

                original_price = None
                discounted_price = None
                
                # 카드 내 텍스트에서 가격 추출
                card_text = room_card.text
                
                # 1. 원가 추출 (취소선 가격)
                try:
                    crossed_out = room_card.find_elements(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"], [data-testid="crossout-price"]')
                    if crossed_out:
                        original_price_text = crossed_out[0].text
                        m = re.search(r'([\d,]+)', original_price_text)
                        if m:
                            original_price = int(m.group(1).replace(',', ''))
                            print(f"[DEBUG] Found crossed-out price: {original_price}")
                except:
                    pass
                
                # 2. 할인가 추출
                # 줄 단위로 분리하여 '월' 또는 'month'가 포함된 줄의 가격은 제외
                lines = card_text.split('\n')
                price_values = []
                
                for line in lines:
                    # 할부/월 납입 관련 텍스트가 있는 줄은 건너뜀
                    if any(x in line for x in ['월', 'month', 'installments', '또는']):
                        print(f"[DEBUG] Ignoring line with installment info: {line.strip()}")
                        continue
                        
                    found = re.findall(r'₩\s*([\d,]+)', line)
                    for p in found:
                        try:
                            val = int(p.replace(',', ''))
                            price_values.append(val)
                        except:
                            pass
                
                if not price_values:
                    # Fallback: if strict filtering removed everything, try loose extraction
                    print("[DEBUG] Strict filtering removed all prices. Falling back to loose extraction.")
                    prices = re.findall(r'₩\s*([\d,]+)', card_text)
                    for p in prices:
                        try:
                            val = int(p.replace(',', ''))
                            price_values.append(val)
                        except:
                            pass

                print(f"[DEBUG] Valid prices found: {price_values}")

                if price_values:
                        if original_price:
                            candidates = [p for p in price_values if p < original_price]
                            if candidates:
                                discounted_price = max(candidates)
                            else:
                                discounted_price = min(price_values)
                        else:
                            price_values.sort(reverse=True)
                            if len(price_values) >= 2:
                                original_price = price_values[0]
                                discounted_price = price_values[1]
                            else:
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
                
                results.append({
                    'hotel': hotel_info['name'],
                    'hotel_id': hotel_id,
                    'room_type': room_name,
                    'original_price': original_price,
                    'discounted_price': discounted_price,
                })
                
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

def main():
    print("Chrome 드라이버 시작 중...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        scrape_hotel('grid_inn', HOTELS['grid_inn'], '2025-12-10', driver)
    finally:
        driver.quit()

if __name__ == '__main__':
    main()
