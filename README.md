# Procure-Me Pricing Calculator

A Python-based Streamlit application that automates vendor quote processing with margin and tax calculations to generate client-facing spreadsheets.

## Features

- **Excel File Processing**: Upload and parse vendor quote Excel files
- **Automatic Calculations**: Apply margin (10%) and tax (8.25%) to vendor costs
- **Clean Client Output**: Generate client-facing quotes without tax breakdown
- **Configurable Rates**: Adjust tax and margin rates as needed
- **Web Interface**: Easy-to-use Streamlit web app

## How It Works

1. Upload your vendor quote Excel file
2. Select the sheet containing the data (e.g., "Vendor Quote Sheet")
3. The app automatically:
   - Extracts vendor unit costs
   - Adds 0% - 50% margin (sliding calculator) 
   - Adds 0% - 10% tax (sliding calculator) 
   - Creates composite unit rates
4. Download clean client-ready spreadsheets

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd procure-me
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
streamlit run app.py
```

## Usage

### Local Development
```bash
streamlit run app.py
```
Then open http://localhost in your browser.

### Deployment to Streamlit Cloud

1. Push your code to GitHub
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/)
3. Connect your GitHub repository
4. Deploy!

## Supported Formats

The app supports standard vendor quote formats including:
- Material Description
- Part Number
- BOM Quantity
- BOM Unit
- Quote Quantity
- Vendor Unit Cost

It also supports generic Excel formats with automatic column detection.

## Calculation Formula

```
Composite Unit Rate = Vendor Cost × (1 + Margin) × (1 + Tax)

```

## Project Structure

```
procure-me/
├── src/
│   ├── pricing_calculator.py  # Core calculation logic
│   └── excel_parser.py        # Excel file parsing
├── app.py                     # Streamlit web application
├── requirements.txt           # Python dependencies
├── README.md                 # This file
└── examples/                 # Example files
```

## Dependencies

- streamlit: Web interface framework
- pandas: Data processing
- numpy: Numerical calculations
- openpyxl: Excel file reading
- xlsxwriter: Excel file writing with formatting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
