# Procure-Me Pricing Calculator

A Python-based Streamlit application that automates vendor quote processing with margin and tax calculations to generate client-facing spreadsheets.

## Features

- 📊 **Excel File Processing**: Upload and parse vendor quote Excel files
- 💰 **Automatic Calculations**: Apply margin (10%) and tax (8.25%) to vendor costs
- 🧾 **Clean Client Output**: Generate client-facing quotes without tax breakdown
- 🎛️ **Configurable Rates**: Adjust tax and margin rates as needed
- 📱 **Web Interface**: Easy-to-use Streamlit web app

## How It Works

1. Upload your vendor quote Excel file
2. Select the sheet containing the data (e.g., "HAMMON OSP_UG_TAK")
3. The app automatically:
   - Extracts vendor unit costs
   - Adds 10% margin
   - Adds 8.25% tax
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
Then open http://localhost:8501 in your browser.

### Deployment to Streamlit Cloud

1. Push your code to GitHub
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/)
3. Connect your GitHub repository
4. Deploy!

## Supported Formats

The app is optimized for the "HAMMON OSP_UG_TAK" format which includes:
- Material Description
- Part Number
- BOM Quantity
- BOM Unit
- Quote Quantity
- Tak Cost Per Unit

It also supports generic Excel formats with automatic column detection.

## Calculation Formula

```
Composite Unit Rate = Vendor Cost × (1 + Margin) × (1 + Tax)

Default values:
- Margin: 10%
- Tax: 8.25%
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
## As-Built Scanner (OCR)

The **📐 As-Built Scanner** tab turns a scanned or plotted as-built (PDF, PNG, JPG, TIFF) into a verified takeoff and a priced bill of materials.

1. **Scan** – uses the PDF text layer when a plot has one, otherwise local OCR ([RapidOCR](https://github.com/RapidAI/RapidOCR), no system install). Scans are auto-straightened, large sheets are read in overlapping tiles with two tilings merged, and vertical route labels are read natively. Optional Mistral OCR engine when `MISTRAL_API_KEY` is set.
2. **Extract** – title block (project / sheet / date / revision ...), footage callouts like `(2) 2" HDPE BY DIRECTIONAL BORE 1,250 LF` (duct count × length), stationing runs (`STA 10+00 TO 22+50`, never double-counted against a matching callout), structures (HH-12, poles, cabinets, flowerpots), and `4 EA ...` quantity tables. Pole heights and cover/depth notes are not mistaken for footage.
3. **Verify** – every item is boxed on the drawing, color-coded by category, with OCR confidence and flags (`low-confidence`, `possible duplicate callout`, `type/size from nearby text - verify`). The takeoff table is editable.
4. **Price** – items map to the Materials List (conduit and strand by size, handholes by nearest size - flagged `APPROX`), then run through the same margin/tax pricing as the other tabs. Download the takeoff workbook or **Send to Build Quote**.

OCR output always needs a human check against the drawing before it is used to buy material.
