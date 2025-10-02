"""
Smart electricity meter consumption data scraper for e-st.lv
Uses Selenium to bypass bot protection and WAF

Usage:
    python scraper.py --month 9 --year 2025 --outfile data.json
    python scraper.py --month 9 --year 2025 --outfile data.json --debug  # Show browser
"""

import json
import argparse
import time
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Load environment variables
load_dotenv()


class ElectricityScraper:
    """Electricity consumption data scraper for e-st.lv"""

    BASE_HOST = 'https://mans.e-st.lv'
    LOGIN_URL = BASE_HOST + '/lv/private/user-authentification/'
    DATA_URL = BASE_HOST + '/lv/private/paterini-un-norekini/paterinu-grafiki/'

    PERIOD_DAY = 'D'
    PERIOD_MONTH = 'M'
    PERIOD_YEAR = 'Y'

    GRANULARITY_HOUR = 'H'
    GRANULARITY_DAY = 'D'

    def __init__(self, login, password, object_id, meter_id, headless=True):
        """
        Initialize scraper

        :param login: Username (email)
        :param password: Password
        :param object_id: Object EIC ID
        :param meter_id: Smart meter ID
        :param headless: Run browser in background (default: True)
        """
        self.login = login
        self.password = password
        self.object_id = object_id
        self.meter_id = meter_id
        self.driver = None
        self.headless = headless

    def _init_driver(self):
        """Initialize Chrome WebDriver with stealth options"""
        if self.driver is not None:
            return

        options = Options()
        if self.headless:
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')

        # Suppress Chrome logs and warnings
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])

        # Stealth options to avoid detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})

        self.driver = webdriver.Chrome(options=options)

        # Additional stealth - hide automation flags
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'lv']})")

    def _get_current_date(self):
        """Get current date components"""
        now = datetime.now()
        return {'year': now.strftime('%Y'), 'month': now.strftime('%m'), 'day': now.strftime('%d')}

    def _get_data_url(self, period=None, year=None, month=None, day=None, granularity=None):
        """Build data URL with query parameters"""
        params = {
            'objectEic': self.object_id,
            'counterNumber': self.meter_id,
            'period': period
        }

        year = year or self._get_current_date()['year']

        if period == self.PERIOD_YEAR:
            params['year'] = year

        if period == self.PERIOD_MONTH:
            params['year'] = year
            params['month'] = month or self._get_current_date()['month']
            params['granularity'] = granularity

        if period == self.PERIOD_DAY:
            month = month or self._get_current_date()['month']
            day = day or self._get_current_date()['day']
            params['date'] = f'{day}.{month}.{year}'
            params['granularity'] = granularity

        return self.DATA_URL + '?' + urlencode(params)

    @staticmethod
    def _format_timestamp(timestamp):
        """Convert JS timestamp to human-readable datetime"""
        return datetime.fromtimestamp(
            int(timestamp) / 1000.0, tz=timezone(timedelta(hours=0))
        ).strftime('%Y-%m-%d %H:%M:%S')

    def _format_response(self, response_data, neto=True):
        """Parse and format the chart data"""
        response_cons_data = response_data['values']['A+']['total']['data']

        # Check if generation data (A-) exists
        if "A-" in response_data['values'].keys():
            response_neto_data = response_data['values']['A-']['total']['data']
        else:
            neto = False

        # Create a mapping of timestamps to production values
        production_map = {}
        if neto:
            for item in response_neto_data:
                production_map[item['timestamp']] = item['value']

        # Format data as array with consumption and production
        formatted_data = []
        for item in response_cons_data:
            timestamp = item['timestamp']
            date_str = self._format_timestamp(timestamp)[:-3]  # Remove seconds

            data_point = {
                'date': date_str,
                'consumption': item['value']
            }

            if neto:
                data_point['production'] = production_map.get(timestamp, 0)

            formatted_data.append(data_point)

        return formatted_data

    def _login(self):
        """Perform login"""
        self._init_driver()

        print(f"Opening login page: {self.LOGIN_URL}")
        self.driver.get(self.LOGIN_URL)
        time.sleep(3)

        try:
            wait = WebDriverWait(self.driver, 20)

            # Handle cookie consent banner
            try:
                print("Checking for cookie consent banner...")
                cookie_selectors = [
                    "button#accept",
                    "button[data-action='consent'][data-action-type='accept']",
                    "button.uc-accept-button",
                    "button[aria-label*='Piekrītu']",
                    "//button[contains(text(), 'Piekrītu')]",
                    "//button[contains(@aria-label, 'Piekrītu')]",
                ]

                for selector in cookie_selectors:
                    try:
                        if selector.startswith("//"):
                            accept_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            accept_button = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        self.driver.execute_script("arguments[0].click();", accept_button)
                        print("[OK] Accepted cookies")
                        time.sleep(2)
                        break
                    except:
                        continue
            except:
                print("No cookie banner or already accepted")

            # Wait for and fill login form
            login_input = wait.until(EC.presence_of_element_located((By.NAME, "login")))
            password_input = self.driver.find_element(By.NAME, "password")

            print("Filling login form...")
            login_input.send_keys(self.login)
            password_input.send_keys(self.password)

            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            try:
                submit_button.click()
            except:
                print("Using JavaScript click...")
                self.driver.execute_script("arguments[0].click();", submit_button)

            time.sleep(5)
            print(f"Current URL after login: {self.driver.current_url}")
            print("[OK] Login submitted, session should be active")
            return True

        except TimeoutException:
            print("ERROR: Login form not found - possible bot detection")
            with open('login_timeout.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            return False

    def _fetch_remote_data(self, **kwargs):
        """Fetch data from the website"""
        if self.driver is None:
            if not self._login():
                raise Exception("Login failed")

        # Navigate to data page
        url = self._get_data_url(**kwargs)
        print(f"Fetching data from: {url}")
        self.driver.get(url)

        print("Waiting for chart to load...")
        time.sleep(5)

        # Check if redirected back to login
        if "authentification" in self.driver.current_url or "login" in self.driver.current_url.lower():
            print("WARNING: Redirected back to login page, attempting re-login...")
            self._login()
            self.driver.get(url)
            time.sleep(5)

        try:
            wait = WebDriverWait(self.driver, 20)
            chart_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.chart")))

            data_values = chart_div.get_attribute('data-values')

            if data_values:
                print("[OK] Chart data found")
                return json.loads(data_values)
            else:
                print("ERROR: Chart data-values attribute is empty")
                with open('chart_empty.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                raise Exception("Chart data not found")

        except TimeoutException:
            print("ERROR: Chart not found on page")
            with open('chart_not_found.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            raise Exception("Chart element not found")

    def get_day_data(self, neto=True, year=None, month=None, day=None):
        """Get consumption data for a specific day"""
        response = self._fetch_remote_data(
            period=self.PERIOD_DAY,
            month=month,
            year=year,
            day=day,
            granularity=self.GRANULARITY_HOUR
        )
        return self._format_response(response, neto)

    def get_month_data(self, neto=True, year=None, month=None, granularity=None):
        """Get consumption data for a specific month"""
        response = self._fetch_remote_data(
            period=self.PERIOD_MONTH,
            month=month,
            year=year,
            granularity=granularity or self.GRANULARITY_DAY
        )
        return self._format_response(response, neto)

    def get_year_data(self, neto=True, year=None):
        """Get consumption data for a specific year"""
        response = self._fetch_remote_data(period=self.PERIOD_YEAR, year=year)
        return self._format_response(response, neto)

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='e-st.lv electricity consumption data scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get September 2025 data (auto-saves as st_202509.json)
  python scraper.py --month 9 --year 2025

  # Run with visible browser for debugging
  python scraper.py --month 9 --year 2025 --debug

  # Get day data (auto-saves as st_20250915.json)
  python scraper.py --period day --day 15 --month 9 --year 2025

  # Get year data (auto-saves as st_2025.json)
  python scraper.py --period year --year 2025

Note: Credentials must be set in .env file (see .env.example)
        """
    )

    parser.add_argument('--period', default='month', choices=['day', 'month', 'year'], help='Data period (default: month)')
    parser.add_argument('--year', type=int, default=None, help='Year (default: current year)')
    parser.add_argument('--month', type=int, default=None, help='Month (1-12)')
    parser.add_argument('--day', type=int, default=None, help='Day (1-31)')
    parser.add_argument('--granularity', default=None, choices=['D', 'H'], help='Data granularity: D=daily, H=hourly (default: D for month, H for day)')
    parser.add_argument('--neto', action='store_true', default=True, help='Include generation data (A-)')
    parser.add_argument('--outfile', default=None, help='Output JSON file (default: auto-generated)')
    parser.add_argument('--debug', action='store_true', help='Show browser window (default: run in background)')

    args = parser.parse_args()

    # Load credentials from environment variables
    username = os.getenv('EST_USERNAME')
    password = os.getenv('EST_PASSWORD')
    object_id = os.getenv('EST_OBJECT_ID')
    meter_id = os.getenv('EST_METER_ID')

    # Check if all required environment variables are set
    missing_vars = []
    if not username:
        missing_vars.append('EST_USERNAME')
    if not password:
        missing_vars.append('EST_PASSWORD')
    if not object_id:
        missing_vars.append('EST_OBJECT_ID')
    if not meter_id:
        missing_vars.append('EST_METER_ID')

    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease create a .env file with:")
        print("EST_USERNAME=your_email")
        print("EST_PASSWORD=your_password")
        print("EST_OBJECT_ID=your_object_eic_id")
        print("EST_METER_ID=your_meter_id")
        return

    # Headless by default, visible only in debug mode
    headless = not args.debug

    print("="*60)
    print("E-ST.LV ELECTRICITY DATA SCRAPER")
    print("="*60)
    if args.debug:
        print("DEBUG MODE: Browser window will be visible")
    print()

    with ElectricityScraper(username, password, object_id, meter_id, headless) as scraper:
        # Fetch data based on period
        if args.period == 'year':
            data = scraper.get_year_data(args.neto, args.year)
            year_val = args.year or datetime.now().year
            auto_filename = f"st_{year_val}.json"
        elif args.period == 'month':
            data = scraper.get_month_data(args.neto, args.year, args.month, args.granularity)
            year_val = args.year or datetime.now().year
            month_val = args.month or datetime.now().month
            auto_filename = f"st_{year_val}{month_val:02d}.json"
        elif args.period == 'day':
            data = scraper.get_day_data(args.neto, args.year, args.month, args.day)
            year_val = args.year or datetime.now().year
            month_val = args.month or datetime.now().month
            day_val = args.day or datetime.now().day
            auto_filename = f"st_{year_val}{month_val:02d}{day_val:02d}.json"
        else:
            raise ValueError(f"Invalid period: {args.period}")

        # Output data
        outfile = args.outfile or auto_filename
        if outfile:
            with open(outfile, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n[OK] Data saved to {outfile}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))

    print("\n" + "="*60)
    print("DONE")
    print("="*60)


if __name__ == '__main__':
    main()
