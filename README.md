# E-ST.LV Smart Meter Data Scraper

Automated tool for extracting electricity consumption and production data from your [AS Sadales tīkls](https://mans.e-st.lv) smart meter portal. Built with Selenium to handle modern web security and bot protection.

## 🚀 Features

- 📊 Extract daily, monthly, or yearly consumption data
- 🔋 Supports both consumption (A+) and production (A-) metrics
- 🤖 Bypasses WAF and bot protection using Selenium stealth mode
- 🔐 Secure credential management via environment variables
- 📁 Auto-generates organized output files (`st_YYYYMMDD.json`)
- 🎯 Clean JSON output format for easy data analysis
- 🔇 Suppressed browser warnings for cleaner console output

## 📋 Prerequisites

- Python 3.12+
- Google Chrome browser
- Active account on [mans.e-st.lv](https://mans.e-st.lv) with simple login and password (2FA not supported)
- Smart electricity meter installed

## 🛠️ Installation

1. **Clone or download this repository**

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials**:

   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your credentials:
   ```env
   EST_USERNAME="your_email@example.com"
   EST_PASSWORD="your_password"
   EST_OBJECT_ID="your_st_object_id"
   EST_METER_ID="your_st_meter_id"
   ```

### 🔍 Finding Your IDs

1. Log in to [mans.e-st.lv](https://mans.e-st.lv)
2. Navigate to **Objektu pārskats** (Objects Overview)
3. Find:
   - **Object EIC code** (Objekta EIC kods) → `EST_OBJECT_ID`
   - **Meter number** (Skaitītāja numurs) → `EST_METER_ID`

## 📖 Usage

### Basic Commands

**Get current month data**:
```bash
python scraper.py
```

**Get specific month**:
```bash
python scraper.py --month 9 --year 2025
```
*Output: `st_202509.json`*

**Get month data with hourly granularity**:
```bash
python scraper.py --month 9 --year 2025 --granularity H
```
*Output: `st_202509.json` (with hourly data points)*

**Get specific day**:
```bash
python scraper.py --period day --day 15 --month 9 --year 2025
```
*Output: `st_20250915.json`*

**Get entire year**:
```bash
python scraper.py --period year --year 2025
```
*Output: `st_2025.json`*

**Debug mode** (show browser):
```bash
python scraper.py --month 9 --year 2025 --debug
```

**Custom output file**:
```bash
python scraper.py --month 9 --year 2025 --outfile custom_name.json
```

### Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--period` | Data period: `day`, `month`, `year` | `month` |
| `--year` | Target year | Current year |
| `--month` | Target month (1-12) | Current month |
| `--day` | Target day (1-31) | Current day |
| `--granularity` | Data granularity: `D` (daily), `H` (hourly) | `D` for month, `H` for day |
| `--outfile` | Custom output filename | Auto-generated |
| `--debug` | Show browser window | Headless mode |

## 📄 Output Format

Data is exported in clean JSON format:

```json
[
  {
    "date": "2025-09-01 00:00",
    "consumption": 19.179,
    "production": 27.41
  },
  {
    "date": "2025-09-02 00:00",
    "consumption": 17.384,
    "production": 31.317
  }
]
```

### Data Fields

- **date**: Timestamp in `YYYY-MM-DD HH:mm` format
- **consumption**: Energy consumed (kWh) - A+ meter reading
- **production**: Energy produced (kWh) - A- meter reading (solar/wind)

> **Note**: `production` field only appears if you have energy generation equipment installed

## 🔧 Troubleshooting

### Authentication Issues

If login fails:
1. Run with `--debug` flag to see browser
2. Verify credentials in `.env` file
3. Check if account requires 2FA (not currently supported)
4. Ensure no CAPTCHA is blocking login

### ChromeDriver Issues

**Error**: ChromeDriver version mismatch
```bash
pip install --upgrade selenium
```

**Error**: Chrome not found
- Install Google Chrome browser
- Selenium will auto-download compatible ChromeDriver

### Missing Data

- Verify meter ID and object ID are correct
- Check date range has available data on the portal
- Some historical data may not be available

### Rate Limiting

The portal may throttle requests. If you get blocked:
- Wait 5-10 minutes between runs
- Avoid rapid consecutive requests
- Use `--debug` to see actual error messages

## 📦 Dependencies

- `selenium` - Browser automation
- `python-dotenv` - Environment variable management

Full list in `requirements.txt`

## 🔒 Security Notes

- Never commit `.env` file to version control
- `.env` is already in `.gitignore`
- Keep credentials secure and private
- Script runs in headless mode by default for security

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📝 License

MIT License - feel free to use and modify

## ⚠️ Disclaimer

This tool is for personal use only. Respect the terms of service of mans.e-st.lv. The author is not responsible for any misuse or violations of the portal's terms.

---

**Made with ❤️ for smart energy monitoring**
