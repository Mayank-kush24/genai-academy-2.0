# Reports Directory

This directory contains automatically generated reports from:

- CSV import operations (`import_report_*.txt`)
- Certificate eligibility calculations (`certificate_eligibility_*.txt`)
- Any exported data files

Reports are automatically created with timestamps.

## Auto-generated Files

- `import_report_YYYYMMDD_HHMMSS.txt` - Import summary
- `certificate_eligibility_YYYYMMDD_HHMMSS.txt` - Certificate reports

## Cleanup

Periodically delete old reports to save disk space:

```powershell
# Delete reports older than 30 days (Windows)
forfiles /P reports /M *.txt /D -30 /C "cmd /c del @path"
```

