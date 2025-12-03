from bs4 import BeautifulSoup
import re

INPUT_FILE = r"c:\Users\HP\Desktop\파이썬기초\debug_structure.html"

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

h4_tags = soup.find_all('h4')

print("각 h4별 가격 정보 분석:\n")

for i, h4 in enumerate(h4_tags[:5]):
    room_text = h4.get_text(strip=True)
    if '룸' not in room_text and 'Room' not in room_text:
        continue
    
    print(f"[{room_text[:40]}]")
    
    # h4의 가장 가까운 부모 컨테이너 찾기 (li, div 등)
    current = h4.parent
    for _ in range(10):
        if not current:
            break
        if current.name in ['li', 'article']:
            break
        current = current.parent
    
    if not current:
        print("  컨테이너 못 찾음\n")
        continue
    
    print(f"  컨테이너: {current.name}")
    
    # 이 컨테이너 내 모든 가격 정보 출력
    print("  컨테이너 내 ₩ 정보:")
    for elem in current.find_all(string=re.compile(r'₩')):
        text = elem.strip()
        parent = elem.parent
        print(f"    '{text}'")
        # 부모의 모든 속성 출력
        if parent.attrs:
            for key, val in parent.attrs.items():
                if len(str(val)) < 100:
                    print(f"      {key}: {val}")
    
    # data- 속성들 찾기
    print("  data-* 속성들:")
    for elem in current.find_all():
        for key, val in elem.attrs.items():
            if key.startswith('data-') and 'price' in key.lower():
                print(f"    {elem.name} - {key}: {val}")
    
    print()