from bs4 import BeautifulSoup

INPUT_FILE = r"c:\Users\HP\Desktop\파이썬기초\debug_structure.html"

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

# crossed-out-price-text 찾기
print("[crossed-out-price-text 요소들]\n")
crossed_outs = soup.find_all(attrs={"data-testid": "crossed-out-price-text"})
print(f"총 {len(crossed_outs)}개 발견\n")

for i, elem in enumerate(crossed_outs[:3]):  # 처음 3개만
    print(f"[{i}] 내용: {elem.get_text(strip=True)}")
    print(f"    태그: {elem.name}")
    print(f"    부모: {elem.parent.name}")
    print(f"    부모의 부모: {elem.parent.parent.name}")
    # 부모 체인 출력
    current = elem.parent
    depth = 0
    print(f"    상위 체인:")
    while current and depth < 5:
        print(f"      {'  '*depth}{current.name} (class={current.get('class', [])})")
        current = current.parent
        depth += 1
    print()

# h4 태그 위치 확인
print("\n[h4 태그들]\n")
h4_tags = soup.find_all('h4')
for i, h4 in enumerate(h4_tags[:5]):
    room_text = h4.get_text(strip=True)
    if '룸' in room_text or 'Room' in room_text:
        print(f"[{i}] {room_text[:40]}")
        print(f"    부모: {h4.parent.name}")
        print(f"    부모의 부모: {h4.parent.parent.name}")
        # 부모 체인
        current = h4.parent
        depth = 0
        print(f"    상위 체인:")
        while current and depth < 5:
            print(f"      {'  '*depth}{current.name}")
            current = current.parent
            depth += 1
        print()