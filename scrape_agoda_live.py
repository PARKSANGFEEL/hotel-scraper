from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import re
import schedule
import random
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

URL = "https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1439847&numberOfBedrooms=&familyMode=false&adults=2&children=0&rooms=1&maxRooms=0&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=1&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&tag=4f122210-314e-4c70-b18b-ac93fc25b69f&flightSearchCriteria=%5Bobject%20Object%5D&los=1&searchrequestid=1db7a87b-052d-42f2-8e2b-353298d15809&utm_medium=banner&utm_source=naver&utm_campaign=naverbz&utm_content=nbz10&utm_term=nbz10&ds=qbRdfmY8zNLy%2B9RI&checkin=2026-01-04"
OUTPUT_CSV = r"c:\Users\HP\Desktop\파이썬기초\results.csv"
PRICE_HISTORY_FILE = r"c:\Users\HP\Desktop\파이썬기초\price_history.json"

# 이메일 설정 (Gmail 기준)
EMAIL_SENDER = "your_email@gmail.com"  # 발신자 이메일
EMAIL_PASSWORD = "your_app_password"    # Gmail 앱 비밀번호
EMAIL_RECEIVER = "receiver@gmail.com"   # 수신자 이메일

def load_price_history():
    """이전 가격 기록 불러오기"""
    if os.path.exists(PRICE_HISTORY_FILE):
        try:
            with open(PRICE_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_price_history(history):
    """가격 기록 저장"""
    with open(PRICE_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_email(subject, body):
    """이메일 알림 전송"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✉️ 이메일 전송 완료: {subject}")
    except Exception as e:
        print(f"✗ 이메일 전송 실패: {e}")

def clean_room_name(text):
    """룸 이름에서 불필요한 문구 제거"""
    m = re.search(r'^([^(]*\([^)]*\))', text)
    if m:
        return m.group(1).strip()
    return text.strip()

def scrape_agoda(checkin_date):
    """Agoda에서 실시간 가격 수집"""
    
    print(f"\n{'='*100}")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 체크인 날짜: {checkin_date}")
    print(f"{'='*100}\n")
    
    print("Chrome 드라이버 시작 중...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')  # 백그라운드 실행
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        # 날짜에 따라 URL 수정
        url_with_date = URL.replace("2026-01-04", checkin_date)
        
        print(f"URL 접속 중...\n")
        driver.get(url_with_date)
        time.sleep(12)
        
        # 모든 h4 태그 (객실 제목) 찾기
        h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
        print(f"총 {len(h4_elements)}개의 h4 태그 발견\n")
        
        results = []
        processed_rooms = set()
        
        # 이전 가격 기록 불러오기
        price_history = load_price_history()
        price_drops = []  # 가격 하락 목록
        
        for h4 in h4_elements:
            try:
                room_name_raw = h4.text.strip()
                room_name = clean_room_name(room_name_raw)
                
                # 룸 타입 필터링
                if not any(kw in room_name for kw in ['룸', 'Room', 'Twin', 'Double', 'Deluxe', 'Family']):
                    continue
                
                # 중복 제거
                if room_name in processed_rooms:
                    continue
                processed_rooms.add(room_name)
                
                print(f"[{room_name}]")
                
                original_price = None
                discounted_price = None
                savings = None
                discount_rate = None
                
                # h4로부터 상위로 올라가며 객실 카드 컨테이너 찾기
                current = h4
                room_card = None
                for _ in range(20):
                    try:
                        current = current.find_element(By.XPATH, '..')
                        # 원가 정보 포함하는 카드 찾기
                        if current.find_element(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"]'):
                            room_card = current
                            break
                    except:
                        pass
                
                if not room_card:
                    print(f"  ✗ 객실 카드 못 찾음\n")
                    continue
                
                # 원가 추출
                try:
                    crossed_out = room_card.find_element(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"]')
                    original_price_text = crossed_out.text
                    m = re.search(r'₩\s*([\d,]+)', original_price_text)
                    if m:
                        original_price = m.group(1).replace(',', '')
                        print(f"  ✓ 원가: ₩{original_price}")
                except:
                    pass
                
                # 할인가 추출 - 원가 - 쿠폰 할인액
                try:
                    coupon_discount = None
                    
                    # 쿠폰 할인액 찾기
                    all_text = room_card.text
                    coupon_match = re.search(r'₩\s*([\d,]+)\s*할인', all_text)
                    if coupon_match and original_price:
                        coupon_discount = int(coupon_match.group(1).replace(',', ''))
                        discounted_price = int(original_price) - coupon_discount
                        print(f"  ✓ 쿠폰 할인: ₩{coupon_discount}")
                        print(f"  ✓ 할인가(계산): ₩{discounted_price}")
                        
                        # 이전 가격과 비교
                        history_key = f"{checkin_date}_{room_name}"
                        if history_key in price_history:
                            prev_price = price_history[history_key]
                            if discounted_price < prev_price:
                                price_drop = prev_price - discounted_price
                                price_drop_percent = int((price_drop / prev_price) * 100)
                                print(f"  🔻 가격 하락! 이전: ₩{prev_price:,} → 현재: ₩{discounted_price:,} (₩{price_drop:,} / {price_drop_percent}% 하락)")
                                
                                price_drops.append({
                                    'room': room_name,
                                    'date': checkin_date,
                                    'prev_price': prev_price,
                                    'current_price': discounted_price,
                                    'drop_amount': price_drop,
                                    'drop_percent': price_drop_percent
                                })
                            elif discounted_price > prev_price:
                                price_increase = discounted_price - prev_price
                                print(f"  🔺 가격 상승! 이전: ₩{prev_price:,} → 현재: ₩{discounted_price:,} (₩{price_increase:,} 상승)")
                            else:
                                print(f"  ➡️ 가격 동일: ₩{discounted_price:,}")
                        else:
                            print(f"  ℹ️ 첫 수집 - 이전 가격 없음")
                        
                        # 현재 가격 저장
                        price_history[history_key] = discounted_price
                        
                    else:
                        print(f"  ✗ 쿠폰 할인 정보 없음")
                    
                except Exception as e:
                    print(f"  ✗ 할인가 추출 실패: {e}")
                
                # 절약금액 계산
                if original_price and discounted_price:
                    try:
                        savings = int(original_price) - int(discounted_price)
                        print(f"  ✓ 절약금액: ₩{savings}")
                    except:
                        pass
                
                # 할인율 계산
                if original_price and savings:
                    try:
                        calc_rate = int((float(savings) / float(original_price)) * 100)
                        discount_rate = str(calc_rate)
                        print(f"  ✓ 할인율: {discount_rate}%")
                    except:
                        pass
                
                print()
                
                results.append({
                    'room_type': room_name,
                    'original_price': original_price or '',
                    'discounted_price': discounted_price or '',
                    'savings': savings or '',
                    'discount_rate': discount_rate or ''
                })
                
            except Exception as e:
                print(f"  ❌ 오류: {e}\n")
                continue
        
        # 가격 기록 저장
        save_price_history(price_history)
        
        # CSV 저장
        print(f"{'='*100}")
        print(f"수집된 객실: {len(results)}개\n")
        
        if results:
            print(f"{'룸 타입':<40} {'원가':<12} {'할인가':<12} {'절약금액':<12} {'할인율':<8}")
            print("-" * 100)
            for item in results:
                orig = f"₩{item['original_price']}" if item['original_price'] else "-"
                disc = f"₩{item['discounted_price']}" if item['discounted_price'] else "-"
                save = f"₩{item['savings']}" if item['savings'] else "-"
                rate = f"{item['discount_rate']}%" if item['discount_rate'] else "-"
                print(f"{item['room_type']:<40} {orig:<12} {disc:<12} {save:<12} {rate:<8}")
        
        # CSV 저장 (날짜별 파일명)
        csv_filename = OUTPUT_CSV.replace('.csv', f'_{checkin_date}.csv')
        print(f"\n결과를 CSV로 저장: {csv_filename}")
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, 
                                   fieldnames=['room_type', 'original_price', 'discounted_price', 'savings', 'discount_rate'])
            writer.writeheader()
            writer.writerows(results)

        print(f"완료! {len(results)}개 객실 정보가 저장되었습니다.")
        
        # 가격 하락 알림 이메일
        if price_drops:
            email_subject = f"🔔 가격 하락 알림! {len(price_drops)}개 객실 - {checkin_date}"
            email_body = f"""
Hotel Rian 가격 하락 알림!

체크인 날짜: {checkin_date}
가격 하락 객실 수: {len(price_drops)}개

"""
            for idx, drop in enumerate(price_drops, 1):
                email_body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{idx}. {drop['room']}
   이전 가격: ₩{drop['prev_price']:,}
   현재 가격: ₩{drop['current_price']:,}
   하락 금액: ₩{drop['drop_amount']:,} (▼{drop['drop_percent']}%)
"""
            
            email_body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

지금 예약하세요: {url_with_date}

수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            send_email(email_subject, email_body)
            print(f"📧 가격 하락 알림 이메일 전송됨 ({len(price_drops)}개 객실)")
        
        return results, price_drops
        
    except Exception as e:
        print(f"❌ 스크래핑 오류: {e}")
        return [], []
    finally:
        driver.quit()
        print("브라우저 종료\n")

def daily_job():
    """매일 실행될 작업"""
    print(f"\n{'#'*100}")
    print(f"🚀 자동 스크래핑 시작")
    print(f"{'#'*100}")
    
    # 3개 날짜 스크래핑
    dates = ["2026-01-04", "2026-01-11", "2026-01-18"]
    all_results = []
    total_price_drops = []
    
    for date in dates:
        results, price_drops = scrape_agoda(date)
        all_results.extend(results)
        total_price_drops.extend(price_drops)
        time.sleep(5)  # 다음 날짜 전 대기
    
    # 일일 요약 이메일
    summary = f"""
오늘의 스크래핑 완료!

수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
총 객실 수: {len(all_results)}개
검색 날짜: {', '.join(dates)}
가격 하락 객실: {len(total_price_drops)}개

다음 실행 예정: 내일 오전 1~3시 사이
"""
    
    if total_price_drops:
        summary += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n가격 하락 요약:\n"
        for drop in total_price_drops:
            summary += f"• {drop['room']} ({drop['date']}): ₩{drop['drop_amount']:,} 하락 (▼{drop['drop_percent']}%)\n"
    
    send_email("📊 Agoda 일일 스크래핑 완료", summary)
    
    print(f"\n{'#'*100}")
    print(f"✅ 모든 작업 완료!")
    print(f"{'#'*100}\n")
    
    # 다음 랜덤 시간 스케줄링
    schedule_random_time()

def schedule_random_time():
    """다음 날 오전 1~3시 사이 랜덤 시간 스케줄링"""
    # 오전 1시 ~ 3시 사이 랜덤 시간 (분 단위)
    hour = random.randint(1, 2)  # 1시 또는 2시
    minute = random.randint(0, 59)
    
    schedule_time = f"{hour:02d}:{minute:02d}"
    
    # 기존 스케줄 모두 제거
    schedule.clear()
    
    # 새 스케줄 등록
    schedule.every().day.at(schedule_time).do(daily_job)
    
    next_run = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run < datetime.now():
        next_run += timedelta(days=1)
    
    print(f"⏰ 다음 실행 예정 시간: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    return schedule_time

def run_scheduler():
    """스케줄러 실행"""
    print(f"\n{'='*100}")
    print(f"🤖 Agoda 자동 스크래핑 스케줄러 시작")
    print(f"{'='*100}\n")
    
    # 첫 실행 시간 설정
    schedule_random_time()
    
    print("💡 스케줄러가 백그라운드에서 실행 중입니다...")
    print("💡 종료하려면 Ctrl+C를 누르세요.\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == '__main__':
    # 실행 모드 선택
    print("실행 모드를 선택하세요:")
    print("1. 즉시 실행 (테스트)")
    print("2. 자동 스케줄링 시작 (매일 오전 1~3시)")
    
    choice = input("선택 (1 또는 2): ").strip()
    
    if choice == "1":
        # 즉시 실행
        daily_job()
    elif choice == "2":
        # 스케줄러 시작
        run_scheduler()
    else:
        print("잘못된 입력입니다. 프로그램을 종료합니다.")