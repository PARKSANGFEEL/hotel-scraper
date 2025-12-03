from bs4 import BeautifulSoup

INPUT_FILE = r"c:\Users\HP\Desktop\파이썬기초\debug_structure.html"

with open(INPUT_FILE, 'r', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')

# 모든 lowest-price-you-seen 찾기
lowest_elems = soup.find_all(attrs={"data-element-name": "lowest-price-you-seen"})
print(f"총 {len(lowest_elems)}개의 LowestPriceYouSeen 발견\n")

for i, elem in enumerate(lowest_elems):
    print(f"[{i}] data-current-price: {elem.get('data-current-price')}")

print("\n\n모든 h4 찾기:")
h4_tags = soup.find_all('h4')
for i, h4 in enumerate(h4_tags[:5]):
    room_text = h4.get_text(strip=True)
    if '룸' in room_text or 'Room' in room_text:
        print(f"\n[{i}] {room_text[:40]}")
        
        # h4의 부모로부터 relative positioning으로 가장 가까운 lowest-price-you-seen 찾기
        current = h4.parent
        found = False
        
        for depth in range(20):
            if not current:
                break
            
            # 현재 레벨에서 찾기
            lowest = current.find(attrs={"data-element-name": "lowest-price-you-seen"})
            if lowest:
                print(f"  ✓ 깊이 {depth}에서 발견: ₩{lowest.get('data-current-price')}")
                found = True
                break
            
            current = current.parent
        
        if not found:
            print(f"  ✗ 찾지 못함")