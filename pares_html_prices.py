import re
import csv
from bs4 import BeautifulSoup

INPUT_FILE = r"c:\Users\HP\Desktop\파이썬기초\debug_structure.html"
OUTPUT_CSV = r"c:\Users\HP\Desktop\파이썬기초\results.csv"

def extract_price_number(text):
    """₩ 12,345 형태에서 숫자만 추출"""
    if not text:
        return None
    m = re.search(r'₩\s*([\d,]+)', str(text))
    if m:
        return m.group(1).replace(',', '')
    return None

def clean_room_name(text):
    """룸 이름에서 불필요한 문구 제거"""
    m = re.search(r'^([^(]*\([^)]*\))', text)
    if m:
        return m.group(1).strip()
    return text.strip()

def get_room_prices(soup):
    """각 h4 룸 타입별로 원가, 할인가, 할인율 추출"""
    results = []
    
    h4_tags = soup.find_all('h4')
    print(f"총 {len(h4_tags)}개의 h4 태그 발견\n")
    
    for h4 in h4_tags:
        room_name_raw = h4.get_text(strip=True)
        room_name = clean_room_name(room_name_raw)
        
        # 룸 타입 필터링
        if not any(kw in room_name for kw in ['룸', 'Room', 'Twin', 'Double', 'Deluxe', 'Family']):
            continue
        
        original_price = None
        discounted_price = None
        discount_rate = None
        savings = None
        
        print(f"[{room_name}]")
        
        # h4로부터 상위로 올라가며 crossed-out-price-text를 포함하는 컨테이너 찾기
        current = h4.parent
        room_container = None
        
        for _ in range(15):
            if not current:
                break
            if current.find(attrs={"data-testid": "crossed-out-price-text"}):
                room_container = current
                break
            current = current.parent
        
        if not room_container:
            print(f"  ✗ room_container를 찾지 못함\n")
            continue
        
        # 1. 원래 가격 찾기
        crossed_out = room_container.find(attrs={"data-testid": "crossed-out-price-text"})
        if crossed_out:
            crossed_text = crossed_out.get_text(strip=True)
            original_price = extract_price_number(crossed_text)
            print(f"  ✓ 원가 발견: ₩{original_price}")
        else:
            print(f"  ✗ 원가 없음\n")
            continue
        
        # 2. 할인가 찾기 (data-room-price 속성)
        # crossed_out 요소 내에서 data-room-price 찾기
        room_price_value = crossed_out.get('data-room-price')
        if room_price_value:
            discounted_price = room_price_value
            print(f"  ✓ 할인가 발견 (data-room-price): ₩{discounted_price}")
        
        # 3. 절약 금액 계산
        if original_price and discounted_price:
            try:
                savings = int(original_price) - int(discounted_price)
                print(f"  ✓ 절약 금액: ₩{savings}")
            except:
                pass
        
        # 4. 할인율 계산
        if original_price and savings:
            try:
                orig = float(original_price)
                sav = float(savings)
                if orig > 0:
                    calc_rate = int((sav / orig) * 100)
                    if calc_rate >= 0:
                        discount_rate = str(calc_rate)
                        print(f"  ✓ 할인율: {discount_rate}%")
            except:
                pass
        
        print()
        
        # 결과 저장
        results.append({
            'room_type': room_name,
            'original_price': original_price or '',
            'discounted_price': discounted_price or '',
            'savings': savings or '',
            'discount_rate': discount_rate or ''
        })
    
    return results

def main():
    print("파일 읽는 중:", INPUT_FILE)
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')

    print("\n[룸 타입별 가격 수집 중...]\n")
    room_data = get_room_prices(soup)
    
    print(f"{'='*100}")
    print(f"수집된 객실: {len(room_data)}개\n")
    if room_data:
        print(f"{'룸 타입':<40} {'원가':<12} {'할인가':<12} {'절약금액':<12} {'할인율':<8}")
        print("-" * 100)
        for item in room_data:
            orig = f"₩{item['original_price']}" if item['original_price'] else "-"
            disc = f"₩{item['discounted_price']}" if item['discounted_price'] else "-"
            save = f"₩{item['savings']}" if item['savings'] else "-"
            rate = f"{item['discount_rate']}%" if item['discount_rate'] else "-"
            print(f"{item['room_type']:<40} {orig:<12} {disc:<12} {save:<12} {rate:<8}")

    # CSV 저장
    print(f"\n결과를 CSV로 저장: {OUTPUT_CSV}")
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, 
                               fieldnames=['room_type', 'original_price', 'discounted_price', 'savings', 'discount_rate'])
        writer.writeheader()
        writer.writerows(room_data)
    
    print(f"완료! {len(room_data)}개 객실 정보가 저장되었습니다.\n")

if __name__ == '__main__':
    main()