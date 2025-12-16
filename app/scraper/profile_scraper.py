"""Scraper for individual GAF contractor profile pages"""

import time
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import tempfile

from app.config import get_settings

settings = get_settings()


class ProfileScraper:
    """Scrapes detailed data from individual contractor profile pages"""
    
    def __init__(self, delay: float = 2.0):
        """
        Initialize profile scraper
        
        Args:
            delay: Delay between requests in seconds
        """
        self.delay = delay
        self.driver = None
    
    def _setup_driver(self):
        """Set up Chrome WebDriver with appropriate options"""
        if self.driver:
            return self.driver
        
        chrome_options = Options()
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={user_agent}")
        chrome_options.add_argument("--accept-language=en-US,en;q=0.9")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        temp_dir = tempfile.mkdtemp(prefix="gaf_profile_chrome_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride", {"userAgent": user_agent}
            )
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """
                },
            )
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(20)
            return self.driver
        except Exception as e:
            print(f"Error setting up Chrome WebDriver: {e}")
            return None
    
    def _safe_navigate(self, url: str, max_retries: int = 3) -> bool:
        """Safely navigate with retry and anti-access-denied logic"""
        if not self.driver:
            self._setup_driver()
        
        if not self.driver:
            return False
        
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                WebDriverWait(self.driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                if "Access Denied" in self.driver.title or "Forbidden" in self.driver.title:
                    print("Access denied, retrying...")
                    time.sleep(random.uniform(5, 10))
                    continue
                
                # Scroll to load content
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                return True
                
            except Exception as e:
                print(f"Navigation error: {e}")
                time.sleep(random.uniform(2, 5))
        
        return False
    
    def scrape_profile(self, profile_url: str) -> Dict:
        """
        Scrape detailed profile data from contractor profile page
        
        Args:
            profile_url: Full URL to contractor profile page
            
        Returns:
            Dictionary with profile-level structured and unstructured data
        """
        profile_data = {
            "years_in_business": None,
            "business_start_year": None,
            "employee_range": None,
            "state_license_number": None,
            "address": None,
            "phone": None,
            "about_text": None,
            "review_snippets": []
        }
        
        try:
            if not self._safe_navigate(profile_url):
                print(f"Failed to navigate to profile {profile_url}")
                return profile_data
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "lxml")
            
            # Extract structured data
            # Extract start year first, then calculate years in business
            profile_data["business_start_year"] = self._extract_business_start_year(soup, None)
            profile_data["years_in_business"] = self._extract_years_in_business(soup, profile_data["business_start_year"])
            profile_data["employee_range"] = self._extract_employee_range(soup)
            profile_data["state_license_number"] = self._extract_license_number(soup)
            profile_data["address"] = self._extract_address(soup)
            profile_data["phone"] = self._extract_phone(soup)
            
            # Extract unstructured data
            profile_data["about_text"] = self._extract_about_text(soup)
            profile_data["review_snippets"] = self._extract_review_snippets(soup, limit=5)
            
            # Rate limiting
            time.sleep(self.delay)
            
        except Exception as e:
            print(f"Error parsing profile {profile_url}: {e}")
            import traceback
            traceback.print_exc()
        
        return profile_data
    
    def cleanup(self):
        """Clean up the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _extract_years_in_business(self, soup: BeautifulSoup, start_year: Optional[int]) -> Optional[int]:
        """
        Calculate years in business from start year
        
        Args:
            soup: BeautifulSoup object (not used here, kept for consistency)
            start_year: Business start year if available
            
        Returns:
            Years in business or None
        """
        if start_year:
            from datetime import datetime
            current_year = datetime.now().year
            return current_year - start_year
        
        return None
    
    def _extract_business_start_year(self, soup: BeautifulSoup, years_in_business: Optional[int]) -> Optional[int]:
        """
        Extract business start year from Details section
        Looks for "Years in Business" title with description like "In business since 2009"
        
        Args:
            soup: BeautifulSoup object
            years_in_business: Years in business if already extracted (not used here)
            
        Returns:
            Start year (e.g., 2009) or None
        """
        # Extract from Details section
        details_section = soup.select_one("section.contractor-details .contractor-details__content")
        if details_section:
            info_items = details_section.select("div.contractor-details__info")
            for item in info_items:
                title_elem = item.select_one("h3.contractor-details__title")
                if title_elem:
                    title_text = title_elem.get_text(strip=True).lower()
                    # Check if this is "Years in Business" field
                    if "years in business" in title_text:
                        desc_elem = item.select_one("p.contractor-details__description")
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            # Extract year from patterns like "In business since 2009"
                            match = re.search(r'(?:since|in business since)\s+(\d{4})', desc_text, re.IGNORECASE)
                            if match:
                                year = int(match.group(1))
                                # Sanity check: reasonable year range
                                if 1800 <= year <= 2024:
                                    return year
        
        return None
    
    def _extract_employee_range(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract employee range from Details section
        Handles formats like "More than 5", "5-10", "11-50", etc.
        Note: This field may not be present on all profiles - returns None if not found
        """
        details_section = soup.select_one("section.contractor-details .contractor-details__content")
        if details_section:
            info_items = details_section.select("div.contractor-details__info")
            for item in info_items:
                title_elem = item.select_one("h3.contractor-details__title")
                if title_elem:
                    title_text = title_elem.get_text(strip=True).lower()
                    # Check if this is employee-related
                    if "employee" in title_text and "number" in title_text:
                        desc_elem = item.select_one("p.contractor-details__description")
                        if desc_elem:
                            text = desc_elem.get_text(strip=True)
                            
                            # Handle text descriptions
                            text_lower = text.lower()
                            if "more than" in text_lower or "over" in text_lower:
                                # Extract number and convert to range
                                match = re.search(r'(\d+)', text)
                                if match:
                                    num = int(match.group(1))
                                    if num < 5:
                                        return "1-10"
                                    elif num < 11:
                                        return "11-50"
                                    elif num < 51:
                                        return "51-200"
                                    else:
                                        return "201+"
                            elif "less than" in text_lower or "under" in text_lower:
                                match = re.search(r'(\d+)', text)
                                if match:
                                    num = int(match.group(1))
                                    if num <= 11:
                                        return "1-10"
                                    else:
                                        return "11-50"
                            
                            # Try to extract numeric range (e.g., "5-10", "11-50")
                            range_match = re.search(r'(\d+[-–]\d+)', text)
                            if range_match:
                                return range_match.group(1)
                            
                            # Try single number - convert to range
                            single_match = re.search(r'(\d+)', text)
                            if single_match:
                                num = int(single_match.group(1))
                                if num <= 10:
                                    return "1-10"
                                elif num <= 50:
                                    return "11-50"
                                elif num <= 200:
                                    return "51-200"
                                else:
                                    return "201+"
                            
                            # If no numeric pattern, store the text as-is
                            # Could be "More than 5", "Small team", etc.
                            return text.strip()
        
        return None
    
    def _extract_license_number(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract state license number from Details section
        Looks for div.contractor-details__info where title is "State License Number"
        Note: This field may not be present on all profiles - returns None if not found
        """
        # Note: Details section may only have some fields, not all
        details_section = soup.select_one("section.contractor-details .contractor-details__content")
        if details_section:
            info_items = details_section.select("div.contractor-details__info")
            for item in info_items:
                title_elem = item.select_one("h3.contractor-details__title")
                if title_elem:
                    title_text = title_elem.get_text(strip=True).lower()
                    # Check if this is the license number field
                    if "license" in title_text and "state" in title_text:
                        desc_elem = item.select_one("p.contractor-details__description")
                        if desc_elem:
                            license_text = desc_elem.get_text(strip=True)
                            return license_text if license_text else None
        
        return None
    
    def _extract_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract full address from address.image-masthead-carousel__address"""
        address_elem = soup.select_one("address.image-masthead-carousel__address")
        
        if address_elem:
            # Get text content (format: "20 Parish Dr, Wayne NJ, 07470 USA")
            address_text = address_elem.get_text(strip=True)
            return address_text if address_text else None
        
        return None
    
    def _extract_phone(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract phone number from a[href^='tel:'] in .image-masthead-carousel__links
        Prefer extracting from href (tel:+19735663007), fallback to text content
        """
        # Look for tel: link in the masthead links section
        phone_link = soup.select_one(".image-masthead-carousel__links a[href^='tel:']")
        
        if phone_link:
            # Get from href first (cleaner format: tel:+19735663007)
            href = phone_link.get("href", "")
            if href.startswith("tel:"):
                # Remove "tel:" prefix and any spaces
                phone = href.replace("tel:", "").strip()
                # Remove +1 if present (US country code)
                if phone.startswith("+1"):
                    phone = phone[2:]
                elif phone.startswith("1") and len(phone) == 11:
                    phone = phone[1:]
                return phone
        
        return None
    
    def _extract_about_text(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract about section text from section.about-us-block .rtf.about-us-block__description
        Gets text from all <p> tags in the description
        """
        about_elem = soup.select_one("section.about-us-block .rtf.about-us-block__description")
        
        if about_elem:
            # Get all paragraph text
            paragraphs = about_elem.find_all("p")
            if paragraphs:
                # Join paragraphs with double newline
                return "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            # Fallback: get all text directly
            text = about_elem.get_text(separator=" ", strip=True)
            return text if text else None
        
        return None
    
    def _extract_review_snippets(self, soup: BeautifulSoup, limit: int = 5) -> List[str]:
        """
        Extract top N review snippets from section.contractor-reviews
        Gets review text from span.contractor-reviews__quote-text
        """
        review_elements = soup.select("section.contractor-reviews ul.contractors-reviews__list > li.contractor-reviews__item")[:limit]
        
        snippets = []
        for review_item in review_elements:
            # Extract review text from span.contractor-reviews__quote-text
            quote_text_elem = review_item.select_one("span.contractor-reviews__quote-text")
            if quote_text_elem:
                text = quote_text_elem.get_text(strip=True)
                if text:
                    snippets.append(text)
            else:
                # Fallback: try p.contractor-reviews__quote
                quote_elem = review_item.select_one("p.contractor-reviews__quote")
                if quote_elem:
                    text = quote_elem.get_text(strip=True)
                    if text:
                        snippets.append(text)
        
        return snippets

