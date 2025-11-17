# Dashboard & Reports Guide

## 📊 Overview
The Dashboard provides a comprehensive view of all statistics, demographics, and performance metrics for the GenAI Academy 2.0 program.

**Access:** `http://192.168.1.60:5000/dashboard`

---

## 🎯 Key Features

### **1. Overview Statistics Cards**

Four high-level metrics at the top:

| Metric | Description |
|--------|-------------|
| **Total Users** | Total registered users in the system |
| **Total Badges** | Total badge submissions with verification rate |
| **Total Profiles** | Total Skillboost profiles with verification rate |
| **Masterclass Attendance** | Total masterclass views with unique class count |

---

### **2. Verification Status Panels**

#### **Badge Verification Status**
Visual progress bars showing:
- ✅ **Verified**: Successfully verified badges (Green)
- ⏳ **Pending**: Awaiting verification (Yellow)
- ❌ **Failed**: Failed verification (Red)

Each bar shows:
- Count (e.g., "1,250")
- Percentage of total (e.g., "75%")

#### **Profile Verification Status**
Same format as badges, showing Skillboost profile verification breakdown.

---

### **3. Demographics Section**

#### **Gender Distribution** (Doughnut Chart)
- Visual breakdown by gender
- Shows count and percentage for each category
- Interactive hover to see exact numbers

#### **Occupation Distribution** (Pie Chart)
- Top 10 occupations
- Color-coded by category
- Shows professional diversity

#### **Top 10 States** (Horizontal Bar Chart)
- Geographic distribution by state
- Sorted by user count (highest to lowest)
- Helps identify regional participation

#### **Top 10 Cities** (Horizontal Bar Chart)
- City-level geographic breakdown
- Sorted by user count
- Identifies key urban centers

---

### **4. Performance & Engagement Section**

#### **Top 10 Performers**
Leaderboard showing users with most verified badges:
- **Rank**: #1, #2, #3, etc.
- **Name**: User's full name
- **Email**: User's email address
- **Badge Count**: Number of verified badges

Format:
```
#1  John Doe                    🏆 15
    john@example.com

#2  Jane Smith                  🏆 12
    jane@example.com
```

#### **Course Badge Statistics** (Stacked Bar Chart)
- Top 10 courses by submission count
- Shows verified, pending, and failed badges per course
- Helps identify:
  - Most popular courses
  - Courses with high failure rates
  - Verification bottlenecks

#### **Masterclass Attendance** (Stacked Bar Chart)
- All masterclasses with attendance breakdown
- **Live**: Attended live session (Blue)
- **Recorded**: Watched recording (Yellow)
- Helps identify:
  - Most popular masterclasses
  - Live vs recorded preference
  - Engagement patterns

---

## 🔄 Real-Time Updates

The dashboard loads data from the API endpoint:
```
GET /api/dashboard/stats
```

**To refresh data:**
- Simply reload the page (F5)
- Dashboard automatically fetches latest statistics

---

## 📈 Data Visualization

### **Chart Types Used**

| Chart Type | Use Case | Interactive |
|------------|----------|-------------|
| **Doughnut** | Gender distribution | ✅ Hover for details |
| **Pie** | Occupation breakdown | ✅ Hover for details |
| **Horizontal Bar** | State/City rankings | ✅ Hover for details |
| **Stacked Bar** | Course/Masterclass stats | ✅ Hover for details |
| **Progress Bar** | Verification status | ❌ Static |

### **Chart.js Features**
- **Responsive**: Adapts to screen size
- **Tooltips**: Hover to see exact values
- **Legend**: Click to show/hide datasets
- **Colors**: Consistent with app theme

---

## 📊 Statistics Breakdown

### **User Statistics**
```json
{
  "total": 10000,              // Total registered users
  "with_verified_profiles": 9500,  // Users with verified Skillboost profiles
  "with_verified_badges": 8000     // Users with at least one verified badge
}
```

### **Badge Statistics**
```json
{
  "total": 25000,              // Total badge submissions
  "verified": 20000,           // Successfully verified
  "failed": 2000,              // Failed verification
  "pending": 3000,             // Awaiting verification
  "verification_rate": 80.0    // Percentage verified
}
```

### **Profile Statistics**
```json
{
  "total": 10000,              // Total profile submissions
  "verified": 9500,            // Successfully verified
  "failed": 200,               // Failed verification
  "pending": 300,              // Awaiting verification
  "verification_rate": 95.0    // Percentage verified
}
```

### **Masterclass Statistics**
```json
{
  "total_attendance": 15000,   // Total attendance records
  "unique_attendees": 8000,    // Unique users who attended
  "unique_classes": 20,        // Number of different masterclasses
  "avg_per_user": 1.9         // Average masterclasses per user
}
```

---

## 🎨 Color Coding

The dashboard uses consistent color coding:

| Color | Meaning | Hex Code |
|-------|---------|----------|
| 🟢 **Green** | Success/Verified | `#34a853` |
| 🔵 **Blue** | Primary/Info | `#4285f4` |
| 🟡 **Yellow** | Warning/Pending | `#fbbc04` |
| 🔴 **Red** | Danger/Failed | `#ea4335` |

---

## 💡 Use Cases

### **1. Program Overview**
- Quick glance at total participation
- Verification completion rates
- Overall engagement metrics

### **2. Demographic Analysis**
- Understand audience composition
- Geographic distribution
- Professional backgrounds

### **3. Performance Tracking**
- Identify top performers
- Course completion rates
- Masterclass engagement

### **4. Quality Assurance**
- Monitor verification failure rates
- Identify problematic courses/profiles
- Track pending verifications

### **5. Reporting**
- Generate insights for stakeholders
- Track program growth over time
- Identify areas for improvement

---

## 📱 Responsive Design

The dashboard is fully responsive and works on:
- **Desktop**: Full layout with all charts
- **Tablet**: Adjusted layout, stacked charts
- **Mobile**: Single column, optimized for scrolling

---

## 🔍 Technical Details

### **Backend Query Functions**

Located in `app/queries.py`:

1. **`get_dashboard_statistics(session)`**
   - Overview stats (users, badges, profiles, masterclasses)
   - Top performers list
   - Calculated metrics (verification rates, averages)

2. **`get_demographic_statistics(session)`**
   - Gender distribution
   - Top 10 countries, states, cities
   - Top 10 occupations
   - Academy 1.0 participation

3. **`get_course_statistics(session)`**
   - Badge submissions by course
   - Verification status per course
   - Grouped by problem statement

4. **`get_masterclass_statistics(session)`**
   - Attendance by masterclass
   - Live vs recorded breakdown
   - Grouped by masterclass name

### **Frontend Components**

Located in `app/templates/dashboard.html`:

- **Stat Cards**: Overview metrics with animations
- **Progress Bars**: Verification status visualization
- **Chart.js**: Interactive charts
- **Top Performers List**: Scrollable leaderboard

### **API Endpoint**

```python
@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    # Returns JSON with all statistics
    return {
        'success': True,
        'stats': {...},
        'demographics': {...},
        'courses': [...],
        'masterclasses': [...]
    }
```

---

## 🐛 Troubleshooting

### **Dashboard shows "Loading..."**
- Check if Flask server is running
- Verify database connection
- Check browser console for errors

### **Charts not displaying**
- Ensure Chart.js CDN is accessible
- Check browser console for JavaScript errors
- Verify data is being returned from API

### **Zero values everywhere**
- Ensure data has been imported
- Check database tables are populated
- Verify verification script has run

### **Slow loading**
- Dashboard may take 3-5 seconds with large datasets (10k+ users)
- Consider adding data caching if needed
- Optimize SQL queries if performance degrades

---

## 📊 Sample Dashboard Metrics

**For a program with 10,000 participants:**

```
Overview:
- Total Users: 10,000
- Total Badges: 25,000 (80% verified)
- Total Profiles: 10,000 (95% verified)
- Masterclass Attendance: 15,000 (20 unique classes)

Top Performer:
- Name: John Doe
- Email: john@example.com
- Verified Badges: 15

Demographics:
- Gender: Male (60%), Female (38%), Other (2%)
- Top State: Maharashtra (2,500 users)
- Top City: Mumbai (1,200 users)
- Top Occupation: Student (4,000 users)

Course Stats:
- Most Popular: "Build a Website" (3,000 submissions, 90% verified)
- Highest Failure: "Cloud Architecture" (500 submissions, 40% failed)

Masterclass Stats:
- Most Attended: "Introduction to AI" (2,000 attendees, 60% live)
- Least Attended: "Advanced ML" (200 attendees, 80% recorded)
```

---

## 🎯 Best Practices

1. **Regular Monitoring**
   - Check dashboard daily for verification progress
   - Monitor failure rates to identify issues
   - Track pending verifications

2. **Data Analysis**
   - Use demographic data for targeted outreach
   - Identify popular courses for future planning
   - Analyze masterclass engagement patterns

3. **Performance Optimization**
   - Run verification scripts regularly
   - Keep pending queues low
   - Address failed verifications promptly

4. **Reporting**
   - Take screenshots for stakeholder reports
   - Export data for deeper analysis
   - Track metrics over time

---

## 🔗 Related Pages

- **Profiles**: `/profiles` - View individual user profiles
- **View Data**: `/view-data` - Browse raw data tables
- **Import**: `/import` - Import new data
- **Export**: `/export` - Export data for analysis

---

## 📝 Notes

- Dashboard data is **real-time** (no caching by default)
- All charts are **interactive** - hover for details
- **Top 10 limits** applied to keep charts readable
- **Stacked charts** show category breakdowns clearly
- **Color consistency** across all visualizations

---

## 🚀 Future Enhancements

Potential additions:
- [ ] Time-series charts (trends over time)
- [ ] Export dashboard as PDF/Image
- [ ] Custom date range filters
- [ ] Drill-down capabilities
- [ ] Real-time updates (WebSocket)
- [ ] Custom dashboard layouts
- [ ] Comparison views (month-over-month)
- [ ] Alert system for anomalies

---

## 📞 Support

If you encounter issues:
1. Check browser console for errors
2. Verify Flask server is running
3. Ensure database is accessible
4. Check data has been imported
5. Run verification scripts if needed

---

**Version:** 1.0  
**Last Updated:** November 2024  
**Tested On:** Chrome, Firefox, Edge, Safari

