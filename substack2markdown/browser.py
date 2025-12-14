"""
Browser automation module using Selenium.
Handles Chrome browser setup, login, and page navigation.
"""

import time
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

from config import Config


class SubstackBrowser:
    """Manages browser automation for Substack scraping."""
    
    def __init__(self, config: Config):
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self._is_logged_in = False
    
    def setup(self) -> bool:
        """Initialize the Chrome browser with appropriate options."""
        try:
            options = Options()

            # Basic options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')

            # Headless mode
            if self.config.headless:
                options.add_argument('--headless=new')

            # Avoid detection
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)

            # Set user agent
            options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )

            # Optional: reuse a Chrome profile (copied/unlocked directory)
            if self.config.chrome_user_data_dir:
                options.add_argument(f"--user-data-dir={self.config.chrome_user_data_dir}")
            if self.config.chrome_profile:
                options.add_argument(f"--profile-directory={self.config.chrome_profile}")

            # Initialize driver with webdriver-manager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(self.config.page_timeout)
            
            # Execute script to hide webdriver property
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            print("[OK] Browser initialized successfully")
            return True
            
        except WebDriverException as e:
            print(f"[FAIL] Failed to initialize browser: {e}")
            return False
    
    def login(self) -> bool:
        """Log into Substack using provided credentials or existing session."""
        if not self.driver:
            print("[FAIL] Browser not initialized")
            return False
        
        try:
            # Navigate to Substack login page
            login_url = f"{self.config.substack_url}/sign-in"
            print(f"Navigating to: {login_url}")
            self.driver.get(login_url)
            time.sleep(3)
            
            # Wait for manual login
            if self.config.use_browser_session:
                return self._wait_for_manual_login()
            
            # Automated login with email/password
            if self.config.email and self.config.password:
                return self._automated_login()
            
            print("[FAIL] No login method available")
            return False
            
        except Exception as e:
            print(f"[FAIL] Login error: {e}")
            return False
    
    def _automated_login(self) -> bool:
        """Perform automated login with email and password."""
        try:
            # Find and fill email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
            )
            email_field.clear()
            email_field.send_keys(self.config.email)
            
            # Click continue/next button
            continue_btn = self.driver.find_element(
                By.CSS_SELECTOR, 
                'button[type="submit"], .button.primary'
            )
            continue_btn.click()
            time.sleep(2)
            
            # Find and fill password field
            password_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
            )
            password_field.clear()
            password_field.send_keys(self.config.password)
            
            # Click login button
            login_btn = self.driver.find_element(
                By.CSS_SELECTOR, 
                'button[type="submit"], .button.primary'
            )
            login_btn.click()
            time.sleep(5)
            
            # Check for CAPTCHA or 2FA
            if self._check_for_challenge():
                print("\n" + "="*60)
                print("CAPTCHA OR 2FA DETECTED")
                print("="*60)
                print("Please complete the challenge in the browser window.")
                print("Press Enter in this terminal when done...")
                print("="*60 + "\n")
                input()
            
            if self._check_logged_in():
                print("[OK] Automated login successful")
                self._is_logged_in = True
                return True
            else:
                print("[FAIL] Automated login failed")
                return False
                
        except TimeoutException:
            print("[FAIL] Login form not found or timed out")
            return False
        except Exception as e:
            print(f"[FAIL] Automated login error: {e}")
            return False

    def _wait_for_manual_login(self) -> bool:
        """Provide a stable window for manual login without extra navigation."""
        wait_seconds = max(self.config.manual_login_wait, 30)

        print("\n" + "=" * 60)
        print("MANUAL LOGIN REQUIRED")
        print("=" * 60)
        print("Please log in to Substack in the browser window.")
        print(f"The script will wait {wait_seconds} seconds before continuing.")
        print("Do not close the browser tab; the script will continue automatically.")
        print("=" * 60 + "\n")

        remaining = wait_seconds
        step = 15

        while remaining > 0:
            print(f"  Waiting {remaining} seconds...")
            sleep_time = min(step, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time

            if not self._driver_alive():
                print("[FAIL] Browser session closed during login wait")
                return False

        print("  Proceeding with scraping...")
        self._is_logged_in = True
        return True
    
    def _check_logged_in(self) -> bool:
        """Check if currently logged into Substack."""
        try:
            # Navigate to account settings - only accessible when logged in
            self.driver.get(f"{self.config.substack_url}/account")
            time.sleep(2)
            
            # Check for elements that indicate logged-in state
            page_source = self.driver.page_source.lower()
            
            logged_in_indicators = [
                'account settings',
                'sign out',
                'subscription',
                'billing',
                'manage subscription'
            ]
            
            for indicator in logged_in_indicators:
                if indicator in page_source:
                    return True
            
            # Check URL - if redirected to sign-in, not logged in
            if 'sign-in' in self.driver.current_url:
                return False
            
            return False
            
        except Exception:
            return False
    
    def _check_for_challenge(self) -> bool:
        """Check if CAPTCHA or 2FA challenge is present."""
        page_source = self.driver.page_source.lower()
        challenge_indicators = [
            'captcha',
            'recaptcha',
            'verification',
            'two-factor',
            '2fa',
            'verify your identity'
        ]
        return any(indicator in page_source for indicator in challenge_indicators)
    
    def get_page(self, url: str, retry: int = 0) -> Optional[str]:
        """Navigate to a URL and return the page source."""
        if not self.driver:
            return None
        
        try:
            self.driver.get(url)
            time.sleep(self.config.request_delay)
            
            # Check for rate limiting
            if 'too many requests' in self.driver.page_source.lower():
                if retry < self.config.max_retries:
                    wait_time = (retry + 1) * 15
                    print(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    return self.get_page(url, retry + 1)
                else:
                    print("[FAIL] Rate limit exceeded maximum retries")
                    return None
            
            return self.driver.page_source
            
        except TimeoutException:
            if retry < self.config.max_retries:
                print(f"Timeout loading {url}. Retrying...")
                return self.get_page(url, retry + 1)
            return None
        except Exception as e:
            print(f"Error loading page: {e}")
            return None

    def _driver_alive(self) -> bool:
        """Best-effort check that the browser session is still active."""
        if not self.driver:
            return False

        try:
            # A no-op script still fails quickly if the session died
            self.driver.execute_script("return 1")
            return True
        except Exception:
            return False
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the page to load lazy content."""
        if not self.driver:
            return
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def close(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
                print("[OK] Browser closed")
            except Exception:
                pass
            self.driver = None
    
    @property
    def is_logged_in(self) -> bool:
        """Check if logged in."""
        return self._is_logged_in
    
    def __enter__(self):
        """Context manager entry."""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
