from bs4 import BeautifulSoup
import re

INPUT_FILE = r"c:\Users\HP\Desktop\파이썬기초\debug_structure.html"

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

crossed_outs = soup.find_all(attrs={"data-testid": "crossed-out-price-text"})

if crossed_outs:
    first_crossed = crossed_outs[0]
    
    # 부모 체인 5단계 올라가기
    container = first_crossed
    for i in range(7):
        container = container.parent
    
    print("=" * 80)
    print("[첫 번째 방의 전체 가격 정보]\n")
    
    # 모든 속성 출력
    print("crossed-out-price-text 속성들:")
    for key, value in first_crossed.attrs.items():
        print(f"  {key}: {value}")
    
    print("\n\n컨테이너 내 모든 텍스트 (₩ 포함):")
    for elem in container.find_all(string=re.compile(r'₩|%')):
        text = elem.strip()
        parent = elem.parent
        print(f"  '{text}'")
        print(f"    부모: {parent.name}, class: {parent.get('class', [])}")
        print(f"    data-testid: {parent.get('data-testid', 'N/A')}")
        # 부모의 속성도 출력
        for key, val in parent.attrs.items():
            if 'price' in key.lower() or 'data-' in key.lower():
                print(f"      {key}: {val}")
    
    print("\n\n HTML 전체 (처음 3000자):")
    print(container.prettify()[:3000])