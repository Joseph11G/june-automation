import time
import os
import random
import json
import shutil
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
AI_WEBSITE_URL = "https://askjune.ai/app/chat"
INPUT_BOX_XPATH = "//textarea[@placeholder='Type your question here...']"
SEND_BUTTON_XPATH = "//button[@aria-label='submit']"
MODEL_SELECTOR_XPATH = "//button[@data-tour='model-selector']"
HEADLESS = False
PROGRESS_FILE = "progress.json"
MODEL_TRACKING_FILE = "model_tracking.json"
PERSISTENT_PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")

# Model configurations
MODELS = [
    "Qwen3 235B A22B",
    "June Qwen3 32B", 
    "DeepSeek R1",
    "OpenAI GPT OSS 120B",
    "OpenAI o4 mini (high)",
    "Grok 4",
    "Claude Sonnet 4",
    "Gemini 2.5 Flash"
]

MODEL_USAGE_LIMIT_HOURS = 5
MODEL_COOLDOWN_HOURS = 4

# Response detection selectors - try multiple approaches
RESPONSE_SELECTORS = [
    ".message",
    "[class*='message']",
    "[class*='response']",
    "[class*='answer']",
    "[class*='output']",
    "[class*='ai-message']",
    "[class*='assistant']",
    "div[data-message-author='assistant']",
    "div[role='article']",
    ".prose",
    "div[class*='markdown']"
]

# --- Load questions from file ---
try:
    with open("questions.txt", "r", encoding="utf-8") as f:
        QUESTIONS = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print("❌ questions.txt file not found. Creating a sample file...")
    QUESTIONS = ["What is artificial intelligence?", "How does machine learning work?"]
    with open("questions.txt", "w", encoding="utf-8") as f:
        for q in QUESTIONS:
            f.write(q + "\n")
    print("✅ Created questions.txt with sample questions")

# --- Progress Management ---
def load_progress():
    """Load saved progress and model tracking."""
    start_index = 0
    model_data = {}
    
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                start_index = data.get("last_index", 0)
        except Exception:
            start_index = 0
    
    if os.path.exists(MODEL_TRACKING_FILE):
        try:
            with open(MODEL_TRACKING_FILE, "r", encoding="utf-8") as f:
                model_data = json.load(f)
        except Exception:
            model_data = {}
    
    return start_index, model_data

def save_progress(index):
    """Save current progress to file."""
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_index": index}, f)
    except Exception as ex:
        print(f"⚠️ Could not save progress: {ex}")

def save_model_tracking(model_data):
    """Save model usage tracking."""
    try:
        with open(MODEL_TRACKING_FILE, "w", encoding="utf-8") as f:
            json.dump(model_data, f, indent=2)
    except Exception as ex:
        print(f"⚠️ Could not save model tracking: {ex}")

# --- Model Management ---
class ModelManager:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait
        self.model_data = {}
        self.current_model = None
        self.load_model_data()
    
    def load_model_data(self):
        """Load model tracking data."""
        if os.path.exists(MODEL_TRACKING_FILE):
            try:
                with open(MODEL_TRACKING_FILE, "r", encoding="utf-8") as f:
                    self.model_data = json.load(f)
            except Exception:
                self.model_data = {}
    
    def get_available_model(self):
        """Get next available model based on usage and cooldown."""
        current_time = datetime.now()
        
        for model in MODELS:
            if model not in self.model_data:
                return model
            
            model_info = self.model_data[model]
            last_start = datetime.fromisoformat(model_info.get("last_start", "2020-01-01T00:00:00"))
            usage_time = model_info.get("usage_time", 0)
            
            # Check if model is in cooldown
            if usage_time >= MODEL_USAGE_LIMIT_HOURS * 3600:
                cooldown_end = last_start + timedelta(hours=MODEL_USAGE_LIMIT_HOURS + MODEL_COOLDOWN_HOURS)
                if current_time < cooldown_end:
                    continue
                else:
                    # Reset model after cooldown
                    self.model_data[model] = {"usage_time": 0}
                    return model
            else:
                return model
        
        return None
    
    def switch_model(self, target_model=None):
        """Switch to a different model."""
        try:
            print(f"🔄 Attempting to switch model...")
            
            # Human-like delay
            time.sleep(random.uniform(1, 3))
            
            # Click model selector dropdown
            model_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, MODEL_SELECTOR_XPATH))
            )
            
            # Scroll to element if needed
            self.driver.execute_script("arguments[0].scrollIntoView(true);", model_button)
            time.sleep(0.5)
            
            # Try different click methods
            try:
                model_button.click()
            except ElementClickInterceptedException:
                self.driver.execute_script("arguments[0].click();", model_button)
            
            time.sleep(random.uniform(1, 2))
            
            # Select target model or first available
            if not target_model:
                target_model = self.get_available_model()
            
            if not target_model:
                print("⚠️ No available models at this time")
                return False
            
            # Try to find and click the model option
            model_xpath = f"//span[text()='{target_model}']"
            try:
                model_option = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, model_xpath))
                )
                
                # Hover before clicking (more human-like)
                actions = ActionChains(self.driver)
                actions.move_to_element(model_option).pause(0.5).click().perform()
                
                print(f"✅ Switched to model: {target_model}")
                
                # Update tracking
                self.current_model = target_model
                if target_model not in self.model_data:
                    self.model_data[target_model] = {}
                self.model_data[target_model]["last_start"] = datetime.now().isoformat()
                if "usage_time" not in self.model_data[target_model]:
                    self.model_data[target_model]["usage_time"] = 0
                
                save_model_tracking(self.model_data)
                return True
                
            except TimeoutException:
                print(f"⚠️ Could not find model option: {target_model}")
                # Try to close dropdown
                try:
                    self.driver.find_element(By.TAG_NAME, "body").click()
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"⚠️ Error switching model: {e}")
            return False
    
    def update_usage_time(self, elapsed_seconds):
        """Update usage time for current model."""
        if self.current_model and self.current_model in self.model_data:
            self.model_data[self.current_model]["usage_time"] += elapsed_seconds
            save_model_tracking(self.model_data)
    
    def should_switch_model(self):
        """Check if we should switch to a different model."""
        if not self.current_model:
            return True
        
        if self.current_model not in self.model_data:
            return False
        
        usage_time = self.model_data[self.current_model].get("usage_time", 0)
        return usage_time >= (MODEL_USAGE_LIMIT_HOURS * 3600 - 600)  # Switch 10 min before limit

# --- Response Detection ---
def wait_for_response_improved(driver, timeout=10, check_interval=1):
    """
    Improved response detection using multiple strategies.
    """
    print("⏳ Waiting for AI to finish responding...")
    end_time = time.time() + timeout
    last_text = ""
    stable_count = 0
    required_stable_checks = 3  # Text must be stable for 3 checks
    
    # Strategy 1: Try multiple selectors
    while time.time() < end_time:
        for selector in RESPONSE_SELECTORS:
            try:
                # Get all message elements
                messages = driver.find_elements(By.CSS_SELECTOR, selector)
                if not messages:
                    continue
                
                # Get the last message (most recent response)
                current_text = messages[-1].text.strip()
                
                # Check if text is stable
                if current_text and current_text == last_text:
                    stable_count += 1
                    if stable_count >= required_stable_checks:
                        print("✅ Response finished (text stable).")
                        return True
                else:
                    stable_count = 0
                    last_text = current_text
                
                # Alternative: Check for typing indicators
                typing_indicators = [
                    "[class*='typing']",
                    "[class*='loading']", 
                    "[class*='pending']",
                    "[class*='generating']",
                    ".dots",
                    ".spinner"
                ]
                
                for indicator in typing_indicators:
                    typing_elements = driver.find_elements(By.CSS_SELECTOR, indicator)
                    if typing_elements and any(e.is_displayed() for e in typing_elements):
                        stable_count = 0  # Reset if still typing
                        break
                
                break  # If we found messages with this selector, don't try others
                
            except Exception:
                continue
        
        # Strategy 2: Check for stop/regenerate button appearance
        try:
            stop_buttons = driver.find_elements(By.CSS_SELECTOR, "[class*='stop'], [class*='regenerate'], button[aria-label*='stop']")
            if stop_buttons:
                for btn in stop_buttons:
                    if "regenerate" in btn.text.lower() or btn.get_attribute("aria-label") and "regenerate" in btn.get_attribute("aria-label").lower():
                        print("✅ Response finished (regenerate button appeared).")
                        return True
        except:
            pass
        
        # Strategy 3: Check page activity (JavaScript execution)
        try:
            is_loading = driver.execute_script("""
                return document.readyState !== 'complete' || 
                       document.querySelector('[class*="loading"]') !== null ||
                       document.querySelector('[class*="typing"]') !== null;
            """)
            if not is_loading and last_text:
                stable_count += 1
            else:
                stable_count = 0
        except:
            pass
        
        time.sleep(check_interval)
    
    print("⚠️ Timeout waiting for response - proceeding anyway.")
    return False

def human_like_typing(element, text, min_delay=0.05, max_delay=0.15):
    """Type text in a more human-like manner."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))
        
        # Occasionally pause longer (thinking)
        if random.random() < 0.1:
            time.sleep(random.uniform(0.5, 1.0))

def ask_login_check():
    """Ask user if logged in (pause until user confirms)."""
    while True:
        logged_in = input("\n👤 Are you logged in? (yes/no): ").strip().lower()
        if logged_in == "yes":
            print("✅ Continuing automation...")
            return
        elif logged_in == "no":
            input("⏸ Please log in manually in the opened browser, then press Enter to continue...")
            print("🔑 Continuing after manual login...")
            return
        else:
            print("⚠️ Please type 'yes' or 'no'.")

# --- Main Automation ---
def run_automation():
    print("🚀 Starting enhanced automation...")
    
    # Load progress and model tracking
    START_INDEX, model_tracking = load_progress()
    
    # Setup persistent profile
    if not os.path.exists(PERSISTENT_PROFILE_DIR):
        os.makedirs(PERSISTENT_PROFILE_DIR, exist_ok=True)
        print(f"ℹ️ Created persistent profile folder: {PERSISTENT_PROFILE_DIR}")
    else:
        print(f"ℹ️ Using existing profile folder: {PERSISTENT_PROFILE_DIR}")
    
    # Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PERSISTENT_PROFILE_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    
    # Anti-detection measures
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Random window size for more human-like behavior
    window_sizes = [(1920, 1080), (1680, 1050), (1440, 900), (1366, 768)]
    width, height = random.choice(window_sizes)
    options.add_argument(f"--window-size={width},{height}")
    
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    
    driver = None
    service = None
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Hide webdriver detection
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)
        
        print(f"🌍 Navigating to {AI_WEBSITE_URL}...")
        driver.get(AI_WEBSITE_URL)
        
        wait = WebDriverWait(driver, 60)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Random delay (human-like)
        time.sleep(random.uniform(3, 5))
        
        # Login check
        ask_login_check()
        
        # Initialize model manager
        model_manager = ModelManager(driver, wait)
        
        # Initial model setup
        if model_manager.should_switch_model():
            model_manager.switch_model()
        
        # Find input box with multiple strategies
        selectors_to_try = [
            (By.XPATH, INPUT_BOX_XPATH),
            (By.CSS_SELECTOR, "textarea[placeholder*='Type']"),
            (By.CSS_SELECTOR, "textarea[placeholder*='question']"),
            (By.CSS_SELECTOR, "textarea[placeholder*='Ask']"),
            (By.CSS_SELECTOR, "input[type='text'][placeholder*='Type']"),
            (By.TAG_NAME, "textarea")
        ]
        
        input_box = None
        for by, selector in selectors_to_try:
            try:
                input_box = wait.until(EC.presence_of_element_located((by, selector)))
                print(f"✅ Input box found using: {selector}")
                break
            except TimeoutException:
                continue
        
        if not input_box:
            print("❌ Could not find input box. Exiting.")
            return
        
        print(f"✅ Resuming from Q{START_INDEX + 1}...")
        
        # Main question loop
        session_start = time.time()
        questions_this_session = 0
        
        for i, question in enumerate(QUESTIONS[START_INDEX:], start=START_INDEX + 1):
            try:
                # Check if model switch needed
                if model_manager.should_switch_model():
                    print("🔄 Model usage limit approaching, switching...")
                    if not model_manager.switch_model():
                        print("⚠️ Could not switch model, continuing with current")
                    time.sleep(random.uniform(3, 5))
                
                print(f"\n❓ Sending Q{i}: {question}")
                
                # Clear and type question (human-like)
                input_box.clear()
                time.sleep(random.uniform(0.5, 1))
                
                # Human-like typing
                human_like_typing(input_box, question)
                time.sleep(random.uniform(0.5, 1.5))
                
                # Send question
                send_button = None
                button_selectors = [
                    (By.XPATH, SEND_BUTTON_XPATH),
                    (By.CSS_SELECTOR, "button[aria-label='submit']"),
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(@class, 'send')]"),
                    (By.CSS_SELECTOR, "button svg[class*='send']")
                ]
                
                for by, selector in button_selectors:
                    try:
                        send_button = driver.find_element(by, selector)
                        if send_button.is_enabled():
                            break
                    except:
                        continue
                
                if send_button and send_button.is_enabled():
                    send_button.click()
                else:
                    input_box.send_keys(Keys.RETURN)
                
                print("✅ Question sent.")
                
                # Wait for response
                response_received = wait_for_response_improved(driver)
                
                # Update model usage time
                elapsed = time.time() - session_start
                model_manager.update_usage_time(elapsed)
                session_start = time.time()
                
                # Save progress
                save_progress(i)
                questions_this_session += 1
                
                # Random pause (human-like behavior)
                if random.random() < 0.7:  # 70% short pause
                    pause = random.uniform(5, 7)
                else:  # 30% medium pause
                    pause = random.uniform(8, 10)
                
                print(f"⏸ Pausing for {pause:.1f} seconds...")
                time.sleep(pause)
                
                # Longer break patterns
                if questions_this_session % 10 == 0:  # Every 10 questions
                    long_pause = random.uniform(60, 90)  # 2-5 minutes
                    print(f"☕ Taking a short break for {long_pause/60:.1f} minutes...")
                    time.sleep(long_pause)
                    
                    # Sometimes refresh page
                    if random.random() < 0.2:
                        print("🔄 Refreshing page...")
                        driver.refresh()
                        time.sleep(random.uniform(5, 10))
                
                if questions_this_session % 30 == 0:  # Every 30 questions
                    long_pause = random.uniform(1000, 1800)  # 30-60 minutes
                    print(f"😴 Taking a long break for {long_pause/60:.1f} minutes...")
                    time.sleep(long_pause)
                
                # Re-find input box (DOM might have changed)
                for by, selector in selectors_to_try:
                    try:
                        input_box = driver.find_element(by, selector)
                        if input_box:
                            break
                    except:
                        continue
                
                # Random mouse movements (human-like)
                if random.random() < 0.3:
                    actions = ActionChains(driver)
                    x = random.randint(100, width - 100)
                    y = random.randint(100, height - 100)
                    actions.move_by_offset(x, y).perform()
                    time.sleep(0.5)
                    actions.move_by_offset(-x, -y).perform()
                
            except Exception as e:
                print(f"⚠️ Error with Q{i}: {e}. Continuing...")
                save_progress(i)
                time.sleep(random.uniform(5, 10))
                continue
        
        print("\n🎉 All questions processed successfully!")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        if driver:
            try:
                print("\n🔒 Closing browser in 5 seconds...")
                time.sleep(5)
                driver.quit()
            except:
                pass
        
        print(f"ℹ️ Persistent profile retained at: {PERSISTENT_PROFILE_DIR}")
        print(f"ℹ️ Progress saved. You can resume from Q{START_INDEX + 1}")

if __name__ == "__main__":
    run_automation()