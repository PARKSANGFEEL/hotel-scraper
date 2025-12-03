from bs4 import BeautifulSoup
import re

INPUT_FILE = r"c:\Users\HP\Desktop\파이썬기초\debug_structure.html"

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

# 첫 번째 방의 crossed-out-price-text 찾기
crossed_outs = soup.find_all(attrs={"data-testid": "crossed-out-price-text"})
print(f"[첫 번째 방의 가격 분석]\n")

if crossed_outs:
    first_crossed = crossed_outs[0]
    parent = first_crossed.parent
    
    # 부모의 부모로 이동 (더 큰 컨테이너)
    container = first_crossed
    for _ in range(5):
        container = container.parent
    
    print("컨테이너 내 모든 텍스트 노드 (₩ 포함):")
    for elem in container.find_all(string=re.compile(r'₩')):
        print(f"  '{elem.strip()}'")
        print(f"    부모: {elem.parent.name}, data-testid: {elem.parent.get('data-testid', 'N/A')}")
    
    print("\n\n컨테이너의 HTML 구조 (처음 2000자):")
    print(container.prettify()[:2000])