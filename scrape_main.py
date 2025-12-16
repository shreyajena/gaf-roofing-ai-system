"""
Main script for scraping GAF contractors and storing in SQLite

Usage:
    python scrape_main.py
"""

import sys
from app.models import init_db, get_db
from app.scraper import ListingScraper, ProfileScraper
from app.storage import ContractorStorage
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main scraping workflow"""
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    
    # Configuration
    zipcode = "10013"
    distance = 25
    limit = 10  # Scrape 5-10 contractors as requested
    
    # Initialize components
    listing_scraper = ListingScraper(zipcode=zipcode, distance=distance)
    profile_scraper = ProfileScraper()
    
    # Get database session
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        storage = ContractorStorage(db)
        
        # Step 1: Scrape listings
        logger.info(f"Scraping contractor listings for ZIP {zipcode}, {distance} mile radius...")
        listings = listing_scraper.scrape_listings(limit=limit)
        logger.info(f"Found {len(listings)} contractor listings")
        
        if not listings:
            logger.warning("No listings found. Check selectors and page structure.")
            return
        
        # Step 2: Scrape profiles and save
        saved_count = 0
        try:
            for idx, listing in enumerate(listings, 1):
                profile_url = listing.get("profile_url")
                if not profile_url:
                    logger.warning(f"Listing {idx} has no profile URL, skipping...")
                    continue
                
                logger.info(f"Processing contractor {idx}/{len(listings)}: {listing.get('contractor_name')}")
                
                # Scrape profile data
                logger.info(f"  Scraping profile: {profile_url}")
                profile_data = profile_scraper.scrape_profile(profile_url)
                
                # Save to database
                logger.info(f"  Saving to database...")
                contractor = storage.save_contractor(listing, profile_data)
                
                if contractor:
                    saved_count += 1
                    logger.info(f"  ✓ Saved contractor ID: {contractor.id}, confidence: {contractor.data_confidence}")
                else:
                    logger.warning(f"  ✗ Failed to save contractor")
        finally:
            # Ensure scrapers cleanup
            listing_scraper.cleanup()
            profile_scraper.cleanup()
        
        # Summary
        logger.info("")
        logger.info("=" * 50)
        logger.info(f"Scraping complete!")
        logger.info(f"  Listings scraped: {len(listings)}")
        logger.info(f"  Contractors saved: {saved_count}")
        logger.info(f"  Total in database: {storage.count_contractors()}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Error in main workflow: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

