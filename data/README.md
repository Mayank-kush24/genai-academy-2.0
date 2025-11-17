# Data Directory

Place your CSV/Excel files here for import.

## Files

- Weekly submission files
- Initial data loads
- Any data exports

## Usage

```powershell
# Import a file from this directory
python scripts/import_csv.py --file data/your_file.csv
```

Or use the batch file:
```powershell
import_data.bat data\your_file.csv
```

## Supported Formats

- CSV (.csv)
- Excel (.xlsx, .xls)

## Note

Large data files are excluded from version control (.gitignore).

