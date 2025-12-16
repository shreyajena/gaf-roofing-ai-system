# GAF Scraper Selectors Reference

This document tracks the HTML selectors that need to be filled in based on actual GAF page inspection.

## Listing Scraper (`app/scraper/listing_scraper.py`)

### Selectors to Update:

1. **Contractor listing container**
   - Current placeholder: `div.contractor-listing`
   - Location: `_parse_listing_element()` method
   - Needed for: Finding individual contractor cards on search results page

2. **Contractor name**
   - Current placeholder: `.contractor-name`
   - Location: `_extract_text(element, ".contractor-name")`
   - Returns: String

3. **Rating**
   - Current placeholder: `data-rating` attribute or `.rating` class
   - Location: `_extract_rating()` method
   - Returns: Float (e.g., 4.5)
   - Notes: May be in aria-label, data attribute, or text content

4. **Review count**
   - Current placeholder: `.review-count`
   - Location: `_extract_review_count()` method
   - Returns: Integer
   - Notes: May contain text like "42 reviews"

5. **City**
   - Current placeholder: `.city`
   - Location: `_extract_text(element, ".city")`
   - Returns: String

6. **State**
   - Current placeholder: `.state`
   - Location: `_extract_text(element, ".state")`
   - Returns: String (will be normalized to 2-letter code)

7. **Certification badges**
   - Current placeholder: `.certification-badge`
   - Location: `_extract_certifications()` method
   - Returns: List of strings
   - Notes: Extract from alt text, title attribute, data attribute, or text content

8. **Profile URL link**
   - Current placeholder: `a.contractor-link`
   - Location: `_extract_profile_url()` method
   - Returns: Full URL string
   - Notes: May need to join with base URL

## Profile Scraper (`app/scraper/profile_scraper.py`)

### Selectors to Update:

1. **Years in business**
   - Current placeholder: `.years-in-business`
   - Location: `_extract_years_in_business()` method
   - Returns: Integer
   - Notes: May be formatted as "X years" or "Since YYYY"

2. **Business start year**
   - Current placeholder: `.business-start-year`
   - Location: `_extract_business_start_year()` method
   - Returns: Integer (YYYY)
   - Notes: Can also be derived from years_in_business if not directly available

3. **Employee range**
   - Current placeholder: `.employee-count`
   - Location: `_extract_employee_range()` method
   - Returns: String (e.g., "1-10", "11-50")
   - Notes: May need to normalize from various formats

4. **State license number**
   - Current placeholder: `.license-number`
   - Location: `_extract_license_number()` method
   - Returns: String

5. **Address**
   - Current placeholder: `.address, .business-address`
   - Location: `_extract_address()` method
   - Returns: String (full address)

6. **Phone number**
   - Current placeholder: `a[href^='tel:'], .phone`
   - Location: `_extract_phone()` method
   - Returns: String (digits only)
   - Notes: May be in tel: link href or text content

7. **About text**
   - Current placeholder: `.about-section, .business-description`
   - Location: `_extract_about_text()` method
   - Returns: String (full text)

8. **Review snippets**
   - Current placeholder: `.review-item, .review-snippet`
   - Location: `_extract_review_snippets()` method
   - Returns: List of strings (top 3-5 reviews)
   - Notes: May need nested selector for review text within review item

## Testing Checklist

After updating selectors:

1. Run listing scraper on search results page
2. Verify all listing fields are extracted correctly
3. Run profile scraper on individual contractor pages
4. Verify all profile fields are extracted correctly
5. Check that external_contractor_id is extracted from URLs correctly
6. Verify data confidence calculation is working

## Usage

Once selectors are updated, run:

```bash
python scrape_main.py
```

This will:
1. Initialize SQLite database
2. Scrape 10 contractors from ZIP 10013, 25-mile radius
3. Store all data in SQLite tables
4. Print summary of scraped data

