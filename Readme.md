# Used Car Price Tracker for Ecuador

A Python web scraper that tracks used car prices across major Ecuadorian automotive marketplaces.

## Features

- **Multi-site Scraping:** Collects data from PatioTuerca and OLX Ecuador with expandable architecture for additional sites
- **Price Tracking:** Monitors price changes over time for all listings
- **Data Analysis:** Calculates average prices, identifies deals, and tracks market trends
- **Automated Notifications:** Sends email alerts for price drops and new listings
- **Reporting:** Generates HTML reports with market insights and significant price changes
- **Scheduling:** Runs daily jobs automatically to keep data current

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/ecuador-car-price-tracker.git
   cd ecuador-car-price-tracker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure email settings:
   - Open `car_price_tracker.py`
   - Update the email configuration in the `send_email_notification` method
   - If using Gmail, create an app password in your Google account security settings

## Usage

### Basic Usage

Run the script once:

```bash
python car_price_tracker.py
```

This will:
- Scrape car listings from supported websites
- Store data in a SQLite database (`car_prices.db`)
- Generate an HTML report (`car_prices_report.html`)
- Send an email notification if configured

### Continuous Monitoring

To run the tracker continuously with scheduled jobs:

#### Linux/Mac:
```bash
nohup python car_price_tracker.py > car_tracker.log 2>&1 &
```

#### Windows:
Create a batch file `run_tracker.bat`:
```batch
@echo off
cd C:\path\to\script\directory
python car_price_tracker.py
```
Add this to Windows Task Scheduler to run at system startup.

## Customization

### Adding New Websites

1. Create a new scraping method following the pattern of existing ones:
   ```python
   def scrape_new_site(self, max_pages=3):
       # Implementation here
       return new_listings, updated_prices
   ```

2. Add a call to your new method in the `run_daily_job` method

### Modifying Email Alerts

Customize the email alert criteria in the `run_daily_job` method to match your preferences.

### Adjusting Scraping Frequency

Modify the scheduling in the main section:
```python
# Change from daily to every 12 hours
schedule.every(12).hours.do(tracker.run_daily_job, email="your_email@example.com")
```

## Database Schema

The script uses SQLite with two main tables:

### Cars Table
- `id`: Primary key
- `listing_id`: Original ID from the source website
- `website`: Source website name
- `title`: Listing title
- `make`: Car manufacturer
- `model`: Car model
- `year`: Manufacturing year
- `mileage`: Odometer reading
- `location`: City/region in Ecuador
- `url`: Original listing URL
- `seller_type`: Dealer or private
- `features`: Additional features
- `first_seen`: Date first discovered

### Prices Table
- `id`: Primary key
- `car_id`: Foreign key to cars table
- `price`: Price in USD
- `date`: Date the price was recorded

## Reports

The HTML report includes:
- Total number of listings
- Number of cars with price changes
- Top car makes by popularity
- Recent price drops with links to listings

## Logging

The script logs all activities to `car_tracker.log`, including:
- Scraping starts and completions
- Database operations
- Errors and exceptions
- Email notifications

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This script is for educational purposes only. Please review and respect the Terms of Service of each website before deploying this scraper.