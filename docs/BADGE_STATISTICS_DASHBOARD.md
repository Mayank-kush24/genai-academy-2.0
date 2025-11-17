# Badge Statistics Dashboard

## 📊 Overview
The Badge Statistics Dashboard provides a comprehensive breakdown of skill badge submissions organized by tracks, with validation status (Valid/Invalid) and demographic breakdowns.

**Access:** `http://122.180.240.47:5000/badge-statistics`

**Permission Required:** `view_dashboard`

---

## 🎯 Features

### **1. Data Overview Tile**
Summary statistics displayed at the top:
- **Skills Boost Profile Submissions**: Total profile submissions
- **Total Validated/Correct Profiles**: Verified profiles count
- **Total Valid Skill Badges**: Successfully validated badges

### **2. Skill Badge Submission Table**
Main summary table showing:
- **Organized by Tracks**: Dev Ops, Security, Networking, AI/ML, Data, Serverless
- **Each Badge Listed**: Individual badge names under each track
- **Columns**:
  - Total Submission
  - Valid Count (TRUE)
  - Incorrect Links (FALSE)
- **Track Totals**: Aggregated counts per track
- **Grand Total**: Overall statistics

### **3. Detailed Badge Breakdown**
Comprehensive breakdown for each badge showing:
- **Breakdown by Category**:
  - College Student
  - Freelance
  - Professional
  - Startup
- **Valid vs Invalid Counts** for each category
- **Grand Totals** per badge

---

## 📋 Track Mappings

The system organizes badges into the following tracks:

### **Dev Ops Track**
- Implement CI/CD Pipelines on Google Cloud
- Manage Kubernetes in Google Cloud

### **Security Track**
- Get Started with Sensitive Data Protection
- Create a Secure Data Lake on Cloud Storage

### **Networking Track**
- Develop Your Google Cloud Network
- Build a Secure Google Cloud Network

### **AI/ML Track**
- Prepare Data for ML APIs on Google Cloud
- Automate Data Capture at Scale with Document AI

### **Data Track**
- Share Data Using Google Data Cloud
- Streaming Analytics into BigQuery
- Store, Process, and Manage Data on Google Cloud - Command Line

### **Serverless Track**
- Cloud Run Functions: 3 Ways
- Develop Serverless Applications on Cloud Run
- Develop Serverless Apps with Firebase

---

## 🎨 Visual Design

### **Color Coding**
- **Track Headers**: Blue gradient (#5a9fd4)
- **Valid Counts**: Green background (#d4edda)
- **Invalid Counts**: Red background (#f8d7da)
- **Grand Totals**: Gray background (#e9ecef)
- **Data Tile**: Purple gradient (#667eea to #764ba2)

### **Layout**
- **Summary Section**: Data tile + main table
- **Breakdown Section**: Grid layout with individual badge tables
- **Responsive Design**: Adapts to different screen sizes

---

## 📊 Data Interpretation

### **Valid (TRUE)**
Badge submissions where:
- `courses.valid = TRUE`
- Badge link was verified successfully
- Badge name matches problem statement
- No errors in verification

### **Invalid (FALSE)**
Badge submissions where:
- `courses.valid = FALSE`
- Badge link failed verification
- Link broken or inaccessible
- Badge name mismatch
- Incorrect domain

### **Categories**
Breakdown based on `user_pii.occupation`:
- **College Student**: Student participants
- **Freelance**: Freelance professionals
- **Professional**: Full-time professionals
- **Startup**: Startup employees/founders

---

## 🔍 Sample Data View

### **Summary Table Example**
```
┌─────────────────────────────────────────────────────────────┐
│ Dev Ops Track                 │ 150 │  135 │   15           │
│   Implement CI/CD Pipelines   │  80 │   72 │    8           │
│   Manage Kubernetes           │  70 │   63 │    7           │
├─────────────────────────────────────────────────────────────┤
│ Security Track                │ 200 │  180 │   20           │
│   Sensitive Data Protection   │ 100 │   90 │   10           │
│   Secure Data Lake            │ 100 │   90 │   10           │
├─────────────────────────────────────────────────────────────┤
│ Grand Total                   │ 350 │  315 │   35           │
└─────────────────────────────────────────────────────────────┘
```

### **Breakdown Table Example**
```
┌───────────────────────────────────────────┐
│ Implement CI/CD Pipelines on Google Cloud│
├──────────────────┬──────────┬─────────────┤
│ Contents         │  Valid   │  In-Valid   │
├──────────────────┼──────────┼─────────────┤
│ College Student  │    40    │      5      │
│ Freelance        │    15    │      1      │
│ Professional     │    12    │      2      │
│ Startup          │     5    │      0      │
├──────────────────┼──────────┼─────────────┤
│ Grand Total      │    72    │      8      │
└──────────────────┴──────────┴─────────────┘
```

---

## 🔧 Customization

### **Adding New Tracks**
Edit `app/queries.py` → `get_badge_statistics_breakdown()`:

```python
track_mappings = {
    'Your New Track': [
        'Badge Name 1',
        'Badge Name 2'
    ],
    # ... existing tracks
}
```

### **Changing Categories**
Modify the `categories` list in `get_badge_statistics_breakdown()`:

```python
categories = ['College Student', 'Freelance', 'Professional', 'Startup']
# Change to:
categories = ['Category1', 'Category2', 'Category3']
```

### **Adjusting Colors**
Edit `app/templates/badge_statistics.html` CSS section:

```css
.valid-col {
    background-color: #d4edda;  /* Change green shade */
    color: #155724;
}

.invalid-col {
    background-color: #f8d7da;  /* Change red shade */
    color: #721c24;
}
```

---

## 📈 Use Cases

### **1. Program Monitoring**
- Track overall badge completion rates
- Identify tracks with high failure rates
- Monitor verification success by demographic

### **2. Quality Assurance**
- Spot badges with unusually high invalid rates
- Identify categories struggling with specific badges
- Track improvement over time

### **3. Reporting**
- Generate statistics for stakeholders
- Compare performance across tracks
- Analyze demographic participation patterns

### **4. Resource Allocation**
- Identify tracks needing more support
- Focus verification efforts on high-failure badges
- Target specific demographics for training

---

## 🔗 Related Pages

- **Main Dashboard**: `/dashboard` - Overall system statistics
- **Profiles**: `/profiles` - Individual user profiles
- **View Data**: `/view-data` - Raw data tables
- **Verification Queue**: `/verification-queue` - Pending verifications

---

## 💡 Tips

1. **Refresh Data**: Reload the page to see latest statistics
2. **Export**: Use browser print or save as PDF for reports
3. **Drill Down**: Click on badge names (if implemented) to see individual submissions
4. **Track Mappings**: Update badge names if problem statements change
5. **Categories**: Ensure occupation field is populated for accurate breakdowns

---

## 🐛 Troubleshooting

### **No Data Showing**
- Check if courses have been imported
- Verify badge names match track mappings
- Ensure verification has been run

### **Category Breakdown Empty**
- Check if `user_pii.occupation` field is populated
- Verify spelling matches exactly (case-sensitive)
- Update categories list if using different values

### **Incorrect Counts**
- Re-run verification script
- Check for duplicate submissions
- Verify data import was successful

---

## 📊 Technical Details

### **Backend Query**
- **Function**: `get_badge_statistics_breakdown(session)`
- **Location**: `app/queries.py`
- **Database Tables**:
  - `courses` - Badge submissions
  - `user_pii` - User occupation data

### **Route**
- **URL**: `/badge-statistics`
- **Method**: GET
- **Permission**: `view_dashboard`
- **Template**: `badge_statistics.html`

### **Data Structure**
```python
{
    'badge_data': {
        'Track Name': {
            'track_total': int,
            'track_valid': int,
            'track_invalid': int,
            'badges': [
                {
                    'name': str,
                    'total': int,
                    'valid': int,
                    'invalid': int,
                    'breakdown': {
                        'Category': {
                            'valid': int,
                            'invalid': int
                        }
                    }
                }
            ]
        }
    },
    'summary': {
        'total_profiles': int,
        'valid_profiles': int,
        'valid_badges': int,
        'total_badges': int,
        'invalid_badges': int
    }
}
```

---

## 🎯 Future Enhancements

Potential features to add:
- [ ] Export to Excel with formatting
- [ ] Date range filtering
- [ ] Trend analysis over time
- [ ] Click-through to individual submissions
- [ ] Comparison between time periods
- [ ] Demographic filtering
- [ ] Custom track creation via UI

---

**Version:** 1.0  
**Last Updated:** November 2024  
**Author:** GenAI Academy 2.0 Development Team

