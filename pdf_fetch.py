from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import pandas as pd
import os
import glob
import logging
import random
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_download.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Configuration
MAX_RETRIES = 2
PAGE_LOAD_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 300  # 5 minutes max wait for download
WAIT_TIME_BETWEEN_DOWNLOADS = random.uniform(1.5, 3.0)  # Random delay to avoid being blocked

# 다운로드 경로 설정
download_dir = os.path.join(os.getcwd(), "pdf_downloads")
os.makedirs(download_dir, exist_ok=True)   # 없다면 생성

def setup_webdriver():
    """Set up and return the Chrome WebDriver with proper options."""
    options = Options()
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True
    })
    # options.add_argument('--headless')  # Uncomment for headless mode
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver

def is_download_completed():
    """Check if any new PDF file is being downloaded (looking for .crdownload or .part files)."""
    for file in os.listdir(download_dir):
        if file.endswith('.crdownload') or file.endswith('.part'):
            return False
    return True

def wait_for_download(timeout=DOWNLOAD_TIMEOUT):
    """Wait for download to complete with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_download_completed():
            # Check if new file exists and is a PDF
            files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
            if files:
                newest_file = max(files, key=os.path.getctime)
                if newest_file.endswith(".pdf") or newest_file.endswith(".PDF"):
                    return newest_file
        time.sleep(1)
    return None

def switch_to_iframe_safely(driver, locator, timeout=10):
    """Safely switch to an iframe with proper error handling."""
    try:
        iframe = WebDriverWait(driver, timeout).until(
            EC.frame_to_be_available_and_switch_to_it(locator)
        )
        return True
    except (TimeoutException, NoSuchElementException) as e:
        logger.warning(f"Failed to switch to iframe: {e}")
        return False

def get_downloaded_filename():
    """Get the most recently downloaded file in the download directory."""
    files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) 
             if os.path.isfile(os.path.join(download_dir, f))]
    if not files:
        return None
    return max(files, key=os.path.getctime)

def process_pdf_card(driver, card, retry_count=0):
    """Process a single PDF card with retry mechanism."""
    if retry_count >= MAX_RETRIES:
        logger.error("Maximum retry attempts reached. Skipping this card.")
        return False
    
    try:
        # 제목 가져오기
        title_element = card.find_element(By.CSS_SELECTOR, "div.card-right > a")
        title = title_element.text.strip().replace("/", "_").replace(":", "-").replace("\\", "_")
        title = title[:100] if len(title) > 100 else title  # Limit filename length
        # print(f"{title}")
        
        # "원문보기" 버튼 확인
        open_btn = card.find_element(By.CSS_SELECTOR, "a.btn.xsm.primary")
        open_btn_url = open_btn.get_attribute("href")
        
        if not open_btn_url:
            logger.warning(f"{title} - 원문보기 URL을 찾을 수 없음")
            return False
            
    except NoSuchElementException as e:
        logger.warning(f"{title} - 원문보기 버튼을 찾을 수 없음")
        return False
    
    # return True

    logger.info(f"{title} 다운로드 시도 중...")
    
    # Save the number of current windows before opening a new one
    original_window_handles = driver.window_handles
    original_window = driver.current_window_handle
    
    try:
        # 새로운 탭으로 열기
        driver.execute_script("window.open(arguments[0]);", open_btn_url)
        
        # Wait for the new window or tab to appear
        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: len(d.window_handles) > len(original_window_handles))
        
        # Switch to the new window
        new_window = [window for window in driver.window_handles if window not in original_window_handles][0]
        driver.switch_to.window(new_window)
        
        # Wait for page to load
        time.sleep(3)
        
        # Find all iframes
        iframes = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
        )
        
        # Find the outer iframe containing callPdf.do
        outer_iframe = None
        for iframe in iframes:
            try:
                src = iframe.get_attribute("src")
                if src and "callPdf.do" in src:
                    outer_iframe = iframe
                    break
            except:
                continue
        
        if not outer_iframe:
            logger.warning(f"{title} - callPdf.do iframe을 찾을 수 없음")
            driver.close()
            driver.switch_to.window(original_window)
            return process_pdf_card(driver, card, retry_count + 1)  # Retry
        
        # Switch to the outer iframe
        driver.switch_to.frame(outer_iframe)
        # logger.info(f"{title} - 첫 번째 iframe으로 전환 성공")
        
        # Now find the inner iframe
        try:
            inner_iframes = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
            )
            
            inner_iframe = None
            for iframe in inner_iframes:
                try:
                    src = iframe.get_attribute("src")
                    if src and "customLayoutNew3.jsp" in src:
                        inner_iframe = iframe
                        break
                except:
                    continue
            
            if not inner_iframe:
                logger.warning(f"{title} - customLayoutNew3.jsp iframe을 찾을 수 없음")
                driver.switch_to.default_content()
                driver.close()
                driver.switch_to.window(original_window)
                return process_pdf_card(driver, card, retry_count + 1)  # Retry
                
            # Switch to the inner iframe
            driver.switch_to.frame(inner_iframe)
            # logger.info(f"{title} - 두 번째 iframe으로 전환 성공")
            
            # Find and click the download button
            try:
                download_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "btnDownload"))
                )
                
                # Record the latest file before download
                files_before = set(os.listdir(download_dir))
                
                # Click the download button
                driver.execute_script("arguments[0].click();", download_btn)
                logger.info(f"{title} - 다운로드 버튼 클릭함")
                
                # Wait for download to complete
                time.sleep(3)  # Initial wait for download to start
                
                # Wait for the download to complete
                downloaded_file = wait_for_download()
                
                if downloaded_file:
                    # Find new files after download
                    files_after = set(os.listdir(download_dir))
                    new_files = files_after - files_before
                    
                    if new_files:
                        newest_file = os.path.join(download_dir, max(new_files))
                        new_path = os.path.join(download_dir, f"{title}.pdf")
                        
                        # If the destination file already exists, append a number
                        counter = 1
                        base_path = new_path
                        while os.path.exists(new_path):
                            new_path = base_path.replace(".pdf", f"_{counter}.pdf")
                            counter += 1
                        
                        # Rename the file
                        try:
                            os.rename(newest_file, new_path)
                            logger.info(f"다운로드 및 이름 변경 완료: {new_path}")
                            success = True
                        except OSError as e:
                            logger.error(f"파일 이름 변경 오류: {e}")
                            success = False
                    else:
                        logger.warning(f"{title} - 새로운 파일이 감지되지 않음")
                        success = False
                else:
                    logger.warning(f"{title} - 다운로드 시간 초과")
                    success = False
                    
            except Exception as e:
                logger.error(f"{title} - 다운로드 버튼 에러: {e}")
                success = False
                
        except Exception as e:
            logger.error(f"{title} - 내부 iframe 처리 실패: {e}")
            success = False
            
    except Exception as e:
        logger.error(f"{title} - 전체 프로세스 에러: {e}")
        success = False
    
    finally:
        # Clean up by closing the tab and switching back
        try:
            driver.switch_to.default_content()
            driver.close()
            driver.switch_to.window(original_window)
        except Exception as e:
            logger.error(f"탭 닫기 오류: {e}")
            
            # If we're stuck, try to recover by closing all but the first window
            try:
                current_handles = driver.window_handles
                for handle in current_handles:
                    if handle != original_window:
                        driver.switch_to.window(handle)
                        driver.close()
                driver.switch_to.window(original_window)
            except Exception as recovery_error:
                logger.critical(f"복구 시도 실패: {recovery_error}")
                # Last resort: quit and restart the driver
                try:
                    driver.quit()
                    driver = setup_webdriver()
                    driver.get("https://lib.rda.go.kr/search/returnFarmBookList.do")
                except:
                    logger.critical("드라이버 재시작 실패")
        
        # Add a small random delay between downloads
        time.sleep(WAIT_TIME_BETWEEN_DOWNLOADS)
    
    if not success and retry_count < MAX_RETRIES:
        logger.info(f"{title} - 재시도 중... ({retry_count + 1}/{MAX_RETRIES})")
        return process_pdf_card(driver, card, retry_count + 1)
    
    return success

def get_last_page_number(driver):
    """Extract the last page number from pagination."""
    try:
        # Find all pagination elements
        pagination_links = driver.find_elements(By.CSS_SELECTOR, "a.page-link")
        
        last_page = 1
        for link in pagination_links:
            href = link.get_attribute("href")
            if href:
                # Extract page number from href attribute
                match = re.search(r"[?&]pg=(\d+)", href)
                if match:
                    page_num = int(match.group(1))
                    if page_num > last_page:
                        last_page = page_num
        
        return last_page
    except Exception as e:
        logger.error(f"마지막 페이지 번호 추출 실패: {e}")
        return 1  # Default to 1 if we can't determine the last page

def go_to_page(driver, page_num):
    """Navigate directly to a specific page number."""
    try:
        # First check if we're already on the correct page
        try:
            active_page = driver.find_element(By.CSS_SELECTOR, "a.page-link.active")
            if active_page.text.strip() == str(page_num):
                logger.info(f"이미 페이지 {page_num}에 있습니다.")
                return True
        except NoSuchElementException:
            pass  # No active page element found, continue with navigation
        
        # Look for the link with the exact page number
        # We need to find elements with text matching our page number
        try:
            # First, try to find page links
            page_links = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.page-link"))
            )
            
            # Then find the one that exactly matches our page number
            page_link = None
            for link in page_links:
                # Check the text content first
                if link.text.strip() == str(page_num):
                    page_link = link
                    break
                    
                # If text doesn't match, check href attribute more carefully
                href = link.get_attribute("href")
                if href:
                    # Look for pg=X where X is our exact page number
                    # Use word boundary or non-digit characters to ensure exact match
                    pattern = r"[?&]pg=" + str(page_num) + r"(?:&|$)"
                    if re.search(pattern, href):
                        page_link = link
                        break
            
            if page_link:
                # Click the page link
                driver.execute_script("arguments[0].click();", page_link)
                logger.info(f"페이지 {page_num}으로 이동 중...")
                time.sleep(3)  # Wait for page to load
                return True
            else:
                # If we didn't find a matching link, fallback to URL modification
                raise TimeoutException("Page link not found in current view")
        except TimeoutException:
            # If the page link isn't visible in the current pagination view, click the next button
            next_btns = driver.find_elements(By.CSS_SELECTOR, "a.page-navi.next")
            
            if not next_btns:
                logger.info("더 이상 다음 페이지가 없습니다. 작업을 종료합니다.")
                return False

            next_btn = next_btns[0]
            # Click the next page button
            driver.execute_script("arguments[0].click();", next_btn)
            
            # Wait for the page to load
            time.sleep(3)

            return True
            
    except Exception as e:
        logger.error(f"페이지 {page_num}으로 이동 중 오류: {e}")
        return False

def main():
    logger.info("PDF 다운로더 시작")
    
    # Initialize driver
    driver = setup_webdriver()
    
    try:
        # 웹페이지 열기
        driver.get("https://lib.rda.go.kr/search/returnFarmBookList.do")
        time.sleep(3)  # Initial page load
        
        # Set display count to 60 items per page
        try:
            # Find the dropdown selector for items per page
            logger.info("페이지당 표시 항목 수를 60개로 설정 중...")
            select_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='cpp']"))
            )
            
            # Select the option with value "60"
            select_60_option = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='cpp'] option[value='60']"))
            )
            
            # Click on the option to select it
            driver.execute_script("arguments[0].selected = true; arguments[0].parentNode.dispatchEvent(new Event('change'));", select_60_option)
            
            logger.info("페이지당 60개 항목 표시 설정 완료")
            time.sleep(3)  # Wait for page to refresh with new item count
        except Exception as e:
            logger.warning(f"페이지당 항목 수 설정 실패: {e}")
            # Continue with default setting if this fails
        
        # Get the last page number
        last_page = get_last_page_number(driver)
        logger.info(f"총 페이지 수: {last_page}")
        
        # You can specify the start page here
        start_page = 1
        
        total_downloads = 0
        failed_downloads = 0
        
        # Process each page directly by page number
        for page_num in range(start_page, last_page + 1):
            # Navigate to the specific page
            if not go_to_page(driver, page_num):
                logger.error(f"페이지 {page_num}으로 이동 실패, 다음 페이지로 넘어갑니다.")
                continue
                
            logger.info(f"페이지 {page_num}/{last_page} 처리 중...")
            
            # 카드 목록 모두 찾기 (with retry if needed)
            cards = None
            for attempt in range(MAX_RETRIES):
                try:
                    cards = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.card-right"))
                    )
                    if cards:
                        break
                except TimeoutException:
                    logger.warning(f"페이지 {page_num}에서 카드를 찾을 수 없음. 재시도 {attempt+1}/{MAX_RETRIES}")
                    driver.refresh()
                    time.sleep(3)
            
            if not cards:
                logger.error(f"페이지 {page_num}에서 카드를 찾을 수 없어 다음 페이지로 넘어갑니다.")
                continue
                
            logger.info(f"현재 페이지에서 {len(cards)}개의 카드 찾음")
            
            # Process each card
            for index, card in enumerate(cards):
                try:
                    success = process_pdf_card(driver, card)
                    if success:
                        total_downloads += 1
                    else:
                        failed_downloads += 1
                except Exception as e:
                    logger.error(f"카드 처리 중 예외 발생: {e}")
                    failed_downloads += 1
    
    except Exception as e:
        logger.critical(f"주요 처리 오류: {e}")
    
    finally:
        # Clean up
        try:
            driver.quit()
        except:
            logger.error("드라이버 종료 오류")
        
        # 다운로드된 파일 확인
        downloaded_files = glob.glob(os.path.join(download_dir, "*.pdf"))
        logger.info(f"총 {len(downloaded_files)}개 파일 다운로드됨 (성공: {total_downloads}, 실패: {failed_downloads})")

if __name__ == "__main__":
    main()