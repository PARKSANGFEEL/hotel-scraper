import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
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

class AgodaScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🏨 Agoda 호텔 가격 모니터링")
        self.root.geometry("900x700")
        self.root.resizable(False, False)
        
        # 변수 초기화
        self.is_running = False
        self.scheduler_thread = None
        
        # URL 및 파일 경로
        self.base_url = "https://www.agoda.com/ko-kr/hotel-rian/hotel/seoul-kr.html?countryId=212&finalPriceView=1&isShowMobileAppPrice=false&cid=1439847&numberOfBedrooms=&familyMode=false&adults=2&children=0&rooms=1&maxRooms=0&isCalendarCallout=false&childAges=&numberOfGuest=0&missingChildAges=false&travellerType=1&showReviewSubmissionEntry=false&currencyCode=KRW&isFreeOccSearch=false&tag=4f122210-314e-4c70-b18b-ac93fc25b69f&flightSearchCriteria=%5Bobject%20Object%5D&los=1&searchrequestid=1db7a87b-052d-42f2-8e2b-353298d15809&utm_medium=banner&utm_source=naver&utm_campaign=naverbz&utm_content=nbz10&utm_term=nbz10&ds=qbRdfmY8zNLy%2B9RI&checkin=2026-01-04"
        self.output_dir = r"c:\Users\HP\Desktop\파이썬기초"
        self.price_history_file = os.path.join(self.output_dir, "price_history.json")
        
        self.create_widgets()
        
    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 타이틀
        title_label = ttk.Label(main_frame, text="🏨 Agoda 호텔 가격 모니터링", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # 설정 프레임
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ 설정", padding="10")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 체크인 날짜
        ttk.Label(config_frame, text="체크인 날짜:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.dates_entry = ttk.Entry(config_frame, width=40)
        self.dates_entry.insert(0, "2026-01-04, 2026-01-11, 2026-01-18")
        self.dates_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # 이메일 설정
        ttk.Label(config_frame, text="발신 이메일:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sender_email = ttk.Entry(config_frame, width=40)
        self.sender_email.insert(0, "your_email@gmail.com")
        self.sender_email.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Label(config_frame, text="앱 비밀번호:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.sender_password = ttk.Entry(config_frame, width=40, show="*")
        self.sender_password.insert(0, "your_app_password")
        self.sender_password.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Label(config_frame, text="수신 이메일:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.receiver_email = ttk.Entry(config_frame, width=40)
        self.receiver_email.insert(0, "receiver@gmail.com")
        self.receiver_email.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # 스케줄 설정
        ttk.Label(config_frame, text="실행 시간:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.schedule_label = ttk.Label(config_frame, text="오전 1~3시 사이 랜덤", foreground="blue")
        self.schedule_label.grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="▶️ 즉시 실행", command=self.run_now, width=15)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.schedule_button = ttk.Button(button_frame, text="⏰ 자동 스케줄 시작", 
                                         command=self.start_scheduler, width=20)
        self.schedule_button.grid(row=0, column=1, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ 중지", command=self.stop_scheduler, 
                                     width=15, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, padx=5)
        
        # 상태 표시
        status_frame = ttk.LabelFrame(main_frame, text="📊 상태", padding="10")
        status_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(status_frame, text="대기 중...", foreground="gray")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.next_run_label = ttk.Label(status_frame, text="다음 실행: -", foreground="blue")
        self.next_run_label.grid(row=1, column=0, sticky=tk.W)
        
        # 프로그레스 바
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=860)
        self.progress.grid(row=2, column=0, pady=5)
        
        # 로그 출력
        log_frame = ttk.LabelFrame(main_frame, text="📝 로그", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=100, height=20, 
                                                  font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 하단 정보
        info_label = ttk.Label(main_frame, text="💡 Tip: 첫 실행 후 두 번째부터 가격 비교가 시작됩니다", 
                              foreground="gray", font=('Arial', 9))
        info_label.grid(row=5, column=0, columnspan=3, pady=5)
        
    def log(self, message):
        """로그 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def load_price_history(self):
        """이전 가격 기록 불러오기"""
        if os.path.exists(self.price_history_file):
            try:
                with open(self.price_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_price_history(self, history):
        """가격 기록 저장"""
        with open(self.price_history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def send_email(self, subject, body):
        """이메일 알림 전송"""
        try:
            sender = self.sender_email.get()
            password = self.sender_password.get()
            receiver = self.receiver_email.get()
            
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            
            self.log(f"✉️ 이메일 전송 완료: {subject}")
        except Exception as e:
            self.log(f"✗ 이메일 전송 실패: {e}")
    
    def clean_room_name(self, text):
        """룸 이름에서 불필요한 문구 제거"""
        m = re.search(r'^([^(]*\([^)]*\))', text)
        if m:
            return m.group(1).strip()
        return text.strip()
    
    def scrape_agoda(self, checkin_date):
        """Agoda에서 실시간 가격 수집"""
        self.log(f"\n{'='*50}")
        self.log(f"📅 체크인 날짜: {checkin_date}")
        self.log(f"{'='*50}")
        
        self.log("Chrome 드라이버 시작 중...")
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--headless')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=options)
        
        try:
            url_with_date = self.base_url.replace("2026-01-04", checkin_date)
            
            self.log(f"URL 접속 중...")
            driver.get(url_with_date)
            time.sleep(12)
            
            h4_elements = driver.find_elements(By.TAG_NAME, 'h4')
            self.log(f"총 {len(h4_elements)}개의 h4 태그 발견")
            
            results = []
            processed_rooms = set()
            price_history = self.load_price_history()
            price_drops = []
            
            for h4 in h4_elements:
                try:
                    room_name_raw = h4.text.strip()
                    room_name = self.clean_room_name(room_name_raw)
                    
                    if not any(kw in room_name for kw in ['룸', 'Room', 'Twin', 'Double', 'Deluxe', 'Family']):
                        continue
                    
                    if room_name in processed_rooms:
                        continue
                    processed_rooms.add(room_name)
                    
                    self.log(f"\n[{room_name}]")
                    
                    current = h4
                    room_card = None
                    for _ in range(20):
                        try:
                            current = current.find_element(By.XPATH, '..')
                            if current.find_element(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"]'):
                                room_card = current
                                break
                        except:
                            pass
                    
                    if not room_card:
                        self.log(f"  ✗ 객실 카드 못 찾음")
                        continue
                    
                    # 원가 추출
                    original_price = None
                    try:
                        crossed_out = room_card.find_element(By.CSS_SELECTOR, '[data-testid="crossed-out-price-text"]')
                        original_price_text = crossed_out.text
                        m = re.search(r'₩\s*([\d,]+)', original_price_text)
                        if m:
                            original_price = m.group(1).replace(',', '')
                            self.log(f"  ✓ 원가: ₩{int(original_price):,}")
                    except:
                        pass
                    
                    # 할인가 추출 - 실제 표시 가격 직접 찾기
                    discounted_price = None
                    try:
                        # JavaScript로 모든 가격 요소 수집 (큰 폰트순)
                        all_prices = driver.execute_script("""
                            const card = arguments[0];
                            const allElems = card.querySelectorAll('span, div, strong, p, b');
                            const prices = [];
                            
                            for (const elem of allElems) {
                                const txt = elem.textContent.trim();
                                // ₩ 포함 + 순수 숫자만 (제외 키워드 필터)
                                if (!txt.includes('₩')) continue;
                                if (txt.includes('원래') || txt.includes('총') || txt.includes('적용') || 
                                    txt.includes('할인') || txt.includes('쿠폰') || txt.includes('로그인')) continue;
                                if (txt.length > 20) continue;
                                if (elem.children.length > 0) continue;
                                
                                const cs = window.getComputedStyle(elem);
                                const fs = parseFloat(cs.fontSize.replace('px','')) || 0;
                                const fw = parseInt(cs.fontWeight) || 400;
                                
                                // 가격 추출
                                const match = txt.match(/₩\\s*([\\d,]+)/);
                                if (match) {
                                    prices.push({
                                        text: txt,
                                        value: parseInt(match[1].replace(/,/g, '')),
                                        fontSize: fs,
                                        fontWeight: fw
                                    });
                                }
                            }
                            
                            // 폰트 크기 + 굵기순 정렬
                            prices.sort((a, b) => {
                                const scoreA = a.fontSize * 2 + a.fontWeight / 100;
                                const scoreB = b.fontSize * 2 + b.fontWeight / 100;
                                return scoreB - scoreA;
                            });
                            
                            return prices.slice(0, 10);
                        """, room_card)
                        
                        # 디버그: 발견된 가격들 출력
                        if all_prices:
                            self.log(f"  🔍 발견된 가격들 (상위 5개):")
                            for idx, p in enumerate(all_prices[:5]):
                                self.log(f"    [{idx+1}] ₩{p['value']:,} ({p['fontSize']}px, fw:{p['fontWeight']}) - '{p['text'][:20]}'")
                        
                        # 원가보다 작은 첫 번째 가격 = 할인가
                        if all_prices and original_price:
                            orig_val = int(original_price)
                            for p in all_prices:
                                val = p['value']
                                # 원가보다 작고, 50% 이상인 가격
                                if orig_val > val > orig_val * 0.5:
                                    discounted_price = val
                                    self.log(f"  ✓ 할인가: ₩{discounted_price:,} (페이지 표시 가격)")
                                    break
                        
                        if not discounted_price:
                            self.log(f"  ✗ 할인가를 찾을 수 없음")
                    
                    except Exception as e:
                        self.log(f"  ✗ 할인가 추출 실패: {e}")
                    
                    # 가격 비교
                    if discounted_price and original_price:
                        history_key = f"{checkin_date}_{room_name}"
                        if history_key in price_history:
                            prev_price = price_history[history_key]
                            if discounted_price < prev_price:
                                price_drop = prev_price - discounted_price
                                price_drop_percent = int((price_drop / prev_price) * 100)
                                self.log(f"  🔻 가격 하락! ₩{prev_price:,} → ₩{discounted_price:,} (▼{price_drop_percent}%)")
                                
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
                                self.log(f"  🔺 가격 상승! ₩{prev_price:,} → ₩{discounted_price:,} (₩{price_increase:,} 상승)")
                            else:
                                self.log(f"  ➡️ 가격 동일: ₩{discounted_price:,}")
                        else:
                            self.log(f"  ℹ️ 첫 수집")
                        
                        # 현재 가격 저장
                        price_history[history_key] = discounted_price
                        
                        # 결과 저장
                        savings = int(original_price) - discounted_price
                        discount_rate = int((savings / int(original_price)) * 100)
                        
                        results.append({
                            'room_type': room_name,
                            'original_price': original_price,
                            'discounted_price': str(discounted_price),
                            'savings': str(savings),
                            'discount_rate': str(discount_rate)
                        })
                    
                except Exception as e:
                    self.log(f"  ❌ 오류: {e}")
                    continue
            
            # 가격 기록 저장
            self.save_price_history(price_history)
            
            # CSV 저장
            if results:
                csv_filename = os.path.join(self.output_dir, f"results_{checkin_date}.csv")
                with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.DictWriter(csvfile, 
                                           fieldnames=['room_type', 'original_price', 'discounted_price', 'savings', 'discount_rate'])
                    writer.writeheader()
                    writer.writerows(results)
                self.log(f"\n✅ CSV 저장 완료: {csv_filename}")
                self.log(f"📊 수집된 객실: {len(results)}개")
            
            # 가격 하락 알림
            if price_drops:
                email_subject = f"🔔 가격 하락! {len(price_drops)}개 객실"
                email_body = f"체크인: {checkin_date}\n\n"
                for drop in price_drops:
                    email_body += f"{drop['room']}\n"
                    email_body += f"  이전: ₩{drop['prev_price']:,} → 현재: ₩{drop['current_price']:,}\n"
                    email_body += f"  하락: ₩{drop['drop_amount']:,} (▼{drop['drop_percent']}%)\n\n"
                
                self.send_email(email_subject, email_body)
            
            return results, price_drops
            
        except Exception as e:
            self.log(f"❌ 스크래핑 오류: {e}")
            return [], []
        finally:
            driver.quit()
    
    def run_scraping_job(self):
        """스크래핑 작업 실행"""
        try:
            self.status_label.config(text="🚀 실행 중...", foreground="green")
            self.progress.start()
            
            dates = [d.strip() for d in self.dates_entry.get().split(',')]
            total_price_drops = []
            
            for date in dates:
                results, price_drops = self.scrape_agoda(date)
                total_price_drops.extend(price_drops)
                time.sleep(5)
            
            self.log(f"\n{'='*50}")
            self.log(f"✅ 모든 작업 완료!")
            self.log(f"가격 하락 객실: {len(total_price_drops)}개")
            self.log(f"{'='*50}\n")
            
            self.status_label.config(text="✅ 완료!", foreground="blue")
            
        except Exception as e:
            self.log(f"❌ 오류: {e}")
            self.status_label.config(text="❌ 오류 발생", foreground="red")
        finally:
            self.progress.stop()
    
    def run_now(self):
        """즉시 실행"""
        self.log_text.delete(1.0, tk.END)
        self.log("▶️ 즉시 실행 시작...")
        
        thread = threading.Thread(target=self.run_scraping_job, daemon=True)
        thread.start()
    
    def scheduler_loop(self):
        """스케줄러 루프"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)
    
    def schedule_job(self):
        """스케줄 작업"""
        self.log("⏰ 예약된 작업 실행 중...")
        self.run_scraping_job()
        
        # 다음 랜덤 시간 설정
        self.setup_random_schedule()
    
    def setup_random_schedule(self):
        """랜덤 스케줄 설정"""
        hour = random.randint(1, 2)
        minute = random.randint(0, 59)
        schedule_time = f"{hour:02d}:{minute:02d}"
        
        schedule.clear()
        schedule.every().day.at(schedule_time).do(self.schedule_job)
        
        next_run = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run < datetime.now():
            next_run += timedelta(days=1)
        
        next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S')
        self.next_run_label.config(text=f"다음 실행: {next_run_str}")
        self.log(f"⏰ 다음 실행 예정: {next_run_str}")
    
    def start_scheduler(self):
        """자동 스케줄 시작"""
        if not self.is_running:
            self.is_running = True
            self.log_text.delete(1.0, tk.END)
            self.log("⏰ 자동 스케줄 시작...")
            
            self.setup_random_schedule()
            
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            self.status_label.config(text="⏰ 스케줄 실행 중...", foreground="green")
            self.schedule_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.DISABLED)
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        if self.is_running:
            self.is_running = False
            schedule.clear()
            
            self.log("⏹️ 스케줄러 중지됨")
            self.status_label.config(text="⏹️ 중지됨", foreground="gray")
            self.next_run_label.config(text="다음 실행: -")
            
            self.schedule_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.start_button.config(state=tk.NORMAL)

if __name__ == '__main__':
    root = tk.Tk()
    app = AgodaScraperGUI(root)
    root.mainloop()