import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import schedule
import logging

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='car_tracker.log')
logger = logging.getLogger('CarTracker')

class CarPriceTracker:
    def __init__(self, db_path='car_prices.db'):
        self.db_path = db_path
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
        }
        self.initialize_db()
        
    def initialize_db(self):
        """Create the database and tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create cars table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY,
            listing_id TEXT,
            website TEXT,
            title TEXT,
            make TEXT,
            model TEXT,
            year INTEGER,
            mileage INTEGER,
            location TEXT,
            url TEXT UNIQUE,
            seller_type TEXT,
            features TEXT,
            first_seen DATE
        )
        ''')
        
        # Create prices table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY,
            car_id INTEGER,
            price REAL,
            date DATE,
            FOREIGN KEY (car_id) REFERENCES cars (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def scrape_patiotuerca(self, max_pages=3):
        """Scrape data from PatioTuerca"""
        new_listings = 0
        updated_prices = 0
        
        try:
            for page in range(1, max_pages + 1):
                url = f"https://ecuador.patiotuerca.com/usados?page={page}"
                response = requests.get(url, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to get page {page} from PatioTuerca. Status code: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                car_listings = soup.select('div.listing-card')
                
                for listing in car_listings:
                    try:
                        # Extract listing details
                        listing_id = listing.get('id', '')
                        title_elem = listing.select_one('h2.listing-card__title')
                        title = title_elem.text.strip() if title_elem else ""
                        
                        # Extract URL
                        url_elem = listing.select_one('a.listing-card__link')
                        url = "https://ecuador.patiotuerca.com" + url_elem['href'] if url_elem else ""
                        
                        # Extract price
                        price_elem = listing.select_one('span.listing-card__price')
                        price_text = price_elem.text.strip() if price_elem else "0"
                        # Remove currency symbol and commas
                        price = float(''.join(filter(lambda x: x.isdigit() or x == '.', price_text)) or 0)
                        
                        # Extract details
                        details = listing.select('span.listing-card__characteristics')
                        year = 0
                        mileage = 0
                        location = ""
                        
                        if len(details) >= 1:
                            year_text = details[0].text.strip()
                            year = int(year_text) if year_text.isdigit() else 0
                        
                        if len(details) >= 2:
                            mileage_text = ''.join(filter(lambda x: x.isdigit(), details[1].text.strip()))
                            mileage = int(mileage_text) if mileage_text.isdigit() else 0
                        
                        if len(details) >= 3:
                            location = details[2].text.strip()
                        
                        # Parse make and model from title
                        make = ""
                        model = ""
                        if title:
                            parts = title.split(' ', 1)
                            make = parts[0]
                            model = parts[1] if len(parts) > 1 else ""
                        
                        # Store data in database
                        result = self.store_data('PatioTuerca', listing_id, title, make, model, year, mileage, location, url, 'Unknown', "", price)
                        if result == 'new':
                            new_listings += 1
                        elif result == 'updated':
                            updated_prices += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing listing: {e}")
                
                # Be respectful with the website
                time.sleep(2)
        
        except Exception as e:
            logger.error(f"Error scraping PatioTuerca: {e}")
        
        return new_listings, updated_prices
    
    def scrape_olx(self, max_pages=3):
        """Scrape data from OLX Ecuador"""
        new_listings = 0
        updated_prices = 0
        
        try:
            for page in range(1, max_pages + 1):
                url = f"https://www.olx.com.ec/autos_c378?page={page}"
                response = requests.get(url, headers=self.headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to get page {page} from OLX. Status code: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                car_listings = soup.select('li.EIR5N')
                
                for listing in car_listings:
                    try:
                        # Extract listing details
                        listing_id = listing.get('data-id', '')
                        
                        # Extract title
                        title_elem = listing.select_one('h2.fTGKY')
                        title = title_elem.text.strip() if title_elem else ""
                        
                        # Extract URL
                        url_elem = listing.select_one('a.fhlkh')
                        url = url_elem['href'] if url_elem else ""
                        if url and not url.startswith('http'):
                            url = "https://www.olx.com.ec" + url
                        
                        # Extract price
                        price_elem = listing.select_one('span.PXdHY')
                        price_text = price_elem.text.strip() if price_elem else "0"
                        # Remove currency symbol and commas
                        price = float(''.join(filter(lambda x: x.isdigit() or x == '.', price_text)) or 0)
                        
                        # Parse details
                        details_elems = listing.select('span.zLvFQ')
                        year = 0
                        mileage = 0
                        location = ""
                        
                        # Find the year
                        for detail in details_elems:
                            text = detail.text.strip()
                            if text.isdigit() and 1950 <= int(text) <= datetime.now().year:
                                year = int(text)
                                break
                        
                        # Location is usually the last detail
                        if details_elems:
                            location = details_elems[-1].text.strip()
                        
                        # Parse make and model from title
                        make = ""
                        model = ""
                        if title:
                            parts = title.split(' ', 1)
                            make = parts[0]
                            model = parts[1] if len(parts) > 1 else ""
                        
                        # Store data
                        result = self.store_data('OLX', listing_id, title, make, model, year, mileage, location, url, 'Unknown', "", price)
                        if result == 'new':
                            new_listings += 1
                        elif result == 'updated':
                            updated_prices += 1
                    
                    except Exception as e:
                        logger.error(f"Error processing OLX listing: {e}")
                
                # Be respectful with rate limits
                time.sleep(3)
        
        except Exception as e:
            logger.error(f"Error scraping OLX: {e}")
        
        return new_listings, updated_prices
    
    def store_data(self, website, listing_id, title, make, model, year, mileage, location, url, seller_type, features, price):
        """Store car data and price in the database"""
        today = datetime.now().date()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = None
        
        try:
            # Check if car exists
            cursor.execute('SELECT id FROM cars WHERE url = ?', (url,))
            car_result = cursor.fetchone()
            
            if car_result:
                # Car exists, get its ID
                car_id = car_result[0]
                
                # Check if price has changed
                cursor.execute('''
                SELECT price FROM prices 
                WHERE car_id = ? 
                ORDER BY date DESC LIMIT 1
                ''', (car_id,))
                
                last_price_result = cursor.fetchone()
                
                if last_price_result and last_price_result[0] != price:
                    # Price has changed, insert new price
                    cursor.execute('''
                    INSERT INTO prices (car_id, price, date) 
                    VALUES (?, ?, ?)
                    ''', (car_id, price, today))
                    result = 'updated'
            else:
                # New car, insert into cars table
                cursor.execute('''
                INSERT INTO cars (listing_id, website, title, make, model, year, mileage, location, url, seller_type, features, first_seen) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (listing_id, website, title, make, model, year, mileage, location, url, seller_type, features, today))
                
                car_id = cursor.lastrowid
                
                # Insert initial price
                cursor.execute('''
                INSERT INTO prices (car_id, price, date) 
                VALUES (?, ?, ?)
                ''', (car_id, price, today))
                
                result = 'new'
            
            conn.commit()
        
        except Exception as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
        
        finally:
            conn.close()
        
        return result
    
    def get_price_changes(self, days=1):
        """Get cars with price changes in the last X days"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        today = datetime.now().date()
        
        cursor.execute('''
        SELECT c.id, c.title, c.make, c.model, c.year, c.url, 
               p1.price as current_price, 
               p2.price as previous_price,
               ((p1.price - p2.price) / p2.price * 100) as price_change_percent
        FROM cars c
        JOIN prices p1 ON c.id = p1.car_id
        JOIN (
            SELECT car_id, MAX(date) as max_date
            FROM prices
            GROUP BY car_id
        ) latest ON p1.car_id = latest.car_id AND p1.date = latest.max_date
        JOIN (
            SELECT p.car_id, p.price
            FROM prices p
            JOIN (
                SELECT car_id, MAX(date) as max_date
                FROM prices
                WHERE date < (SELECT MAX(date) FROM prices GROUP BY car_id HAVING car_id = p.car_id)
                GROUP BY car_id
            ) previous ON p.car_id = previous.car_id AND p.date = previous.max_date
        ) p2 ON c.id = p2.car_id
        WHERE p1.price != p2.price
        AND julianday(p1.date) - julianday(?) <= ?
        ORDER BY price_change_percent
        ''', (today, days))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def get_average_prices(self, make=None, model=None):
        """Get average prices by make and model"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
        SELECT c.make, c.model, c.year, 
               AVG(p.price) as avg_price, 
               MIN(p.price) as min_price, 
               MAX(p.price) as max_price,
               COUNT(*) as count
        FROM cars c
        JOIN (
            SELECT car_id, MAX(date) as max_date
            FROM prices
            GROUP BY car_id
        ) latest ON c.id = latest.car_id
        JOIN prices p ON latest.car_id = p.car_id AND latest.max_date = p.date
        '''
        
        params = []
        if make:
            query += ' WHERE c.make = ?'
            params.append(make)
            if model:
                query += ' AND c.model = ?'
                params.append(model)
        
        query += ' GROUP BY c.make, c.model, c.year ORDER BY c.make, c.model, c.year'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def send_email_notification(self, to_email, subject, message):
        """Send email notification"""
        # Configure with your email settings
        from_email = "your_email@gmail.com"
        password = "your_app_password"  # Use app password for Gmail
        
        try:
            msg = MIMEText(message, 'html')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(from_email, password)
            server.send_message(msg)
            server.quit()
            logger.info(f"Email notification sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def generate_report(self, output_file='car_prices_report.html'):
        """Generate an HTML report of current data"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) as count FROM cars")
        total_cars = cursor.fetchone()['count']
        
        cursor.execute("""
        SELECT COUNT(*) as count FROM (
            SELECT DISTINCT car_id FROM prices 
            GROUP BY car_id 
            HAVING COUNT(*) > 1
        )
        """)
        cars_with_price_changes = cursor.fetchone()['count']
        
        # Get top makes
        cursor.execute("""
        SELECT make, COUNT(*) as count 
        FROM cars 
        GROUP BY make 
        ORDER BY count DESC 
        LIMIT 10
        """)
        top_makes = cursor.fetchall()
        
        # Get recent price drops
        cursor.execute("""
        SELECT c.make || ' ' || c.model || ' ' || c.year as car,
               p_old.price as old_price,
               p_new.price as new_price,
               ((p_new.price - p_old.price) / p_old.price * 100) as change_percent,
               c.url
        FROM cars c
        JOIN prices p_new ON c.id = p_new.car_id
        JOIN (
            SELECT car_id, MAX(date) as max_date
            FROM prices
            GROUP BY car_id
        ) latest ON p_new.car_id = latest.car_id AND p_new.date = latest.max_date
        JOIN (
            SELECT p.car_id, p.price
            FROM prices p
            JOIN (
                SELECT car_id, MAX(date) as max_date
                FROM prices
                WHERE date < (SELECT MAX(date) FROM prices GROUP BY car_id HAVING car_id = p.car_id)
                GROUP BY car_id
            ) previous ON p.car_id = previous.car_id AND p.date = previous.max_date
        ) p_old ON c.id = p_old.car_id
        WHERE p_new.price < p_old.price
        ORDER BY change_percent
        LIMIT 10
        """)
        recent_price_drops = cursor.fetchall()
        
        conn.close()
        
        # Generate HTML report
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Used Car Price Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ display: flex; gap: 20px; margin-bottom: 20px; }}
                .summary-card {{ background-color: #f2f2f2; padding: 15px; border-radius: 5px; flex: 1; }}
                .price-drop {{ color: green; }}
            </style>
        </head>
        <body>
            <h1>Used Car Price Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            
            <div class="summary">
                <div class="summary-card">
                    <h3>Total Listings</h3>
                    <p>{total_cars}</p>
                </div>
                <div class="summary-card">
                    <h3>Cars with Price Changes</h3>
                    <p>{cars_with_price_changes}</p>
                </div>
            </div>
            
            <h2>Top Car Makes</h2>
            <table>
                <tr>
                    <th>Make</th>
                    <th>Count</th>
                </tr>
        """
        
        for make in top_makes:
            html += f"""
                <tr>
                    <td>{make['make']}</td>
                    <td>{make['count']}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Recent Price Drops</h2>
            <table>
                <tr>
                    <th>Car</th>
                    <th>Old Price ($)</th>
                    <th>New Price ($)</th>
                    <th>Change (%)</th>
                </tr>
        """
        
        for drop in recent_price_drops:
            html += f"""
                <tr>
                    <td><a href="{drop['url']}" target="_blank">{drop['car']}</a></td>
                    <td>{drop['old_price']:.2f}</td>
                    <td>{drop['new_price']:.2f}</td>
                    <td class="price-drop">{drop['change_percent']:.2f}%</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Report generated: {output_file}")
        return output_file
    
    def run_daily_job(self, email=None):
        """Run daily scraping job and send notification"""
        logger.info("Starting daily scraping job")
        
        # Scrape websites
        new_pt, updated_pt = self.scrape_patiotuerca()
        new_olx, updated_olx = self.scrape_olx()
        
        total_new = new_pt + new_olx
        total_updated = updated_pt + updated_olx
        
        logger.info(f"Scraping completed: {total_new} new listings, {total_updated} price updates")
        
        # Generate report
        report_file = self.generate_report()
        
        # Send email notification if requested
        if email:
            subject = f"Daily Car Price Report - {datetime.now().strftime('%Y-%m-%d')}"
            message = f"""
            <p>Daily car price scraping has completed:</p>
            <ul>
                <li>{total_new} new listings added</li>
                <li>{total_updated} price updates detected</li>
            </ul>
            <p>See attached report for details.</p>
            """
            
            self.send_email_notification(email, subject, message)
        
        return total_new, total_updated

# Main execution
if __name__ == "__main__":
    tracker = CarPriceTracker()
    
    # Schedule daily job
    schedule.every().day.at("07:00").do(tracker.run_daily_job, email="your_email@example.com")
    
    # Initial run
    tracker.run_daily_job()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)