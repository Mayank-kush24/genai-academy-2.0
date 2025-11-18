"""
Optimized database queries for common operations
"""
from datetime import date
from sqlalchemy import func, case, and_, or_
from app.database import UserPII, Course, SkillboostProfile, MasterClass, MasterLog

# Minimum required completion date for badges to be considered valid
MIN_BADGE_COMPLETION_DATE = date(2025, 10, 27)

def is_badge_valid(course):
    """
    Check if a badge is valid considering both the valid flag and completion date requirement.
    A badge is valid only if:
    1. valid = True
    2. AND completion_date >= 2025-10-27 (or completion_date IS NULL for badges verified before date requirement)
    
    Note: Badges with completion_date = NULL are considered valid only if they were verified
    before the date requirement was added. Once a date is extracted, it must be >= 2025-10-27.
    """
    if course.valid is not True:
        return False
    
    # Safely check completion_date - handle case where column might not exist yet
    try:
        completion_date = course.completion_date
    except (AttributeError, KeyError):
        # Column doesn't exist in database yet - consider valid for backward compatibility
        return True
    
    # If completion_date is None, consider it valid for backward compatibility
    # (old records that don't have completion_date yet - they need to be re-verified)
    # However, if the badge was recently updated and still has no date, it might be invalid
    # For now, we'll consider NULL dates as valid to avoid breaking existing data
    # But badges should be re-verified to extract dates
    if completion_date is None:
        return True
    
    # Check if completion date is on or after the minimum required date
    return completion_date >= MIN_BADGE_COMPLETION_DATE


def get_user_complete_profile(session, email):
    """Get complete user profile with all related data"""
    user = session.query(UserPII).filter_by(email=email).first()
    
    if not user:
        return None
    
    # Get all courses
    courses = session.query(Course).filter_by(email=email).all()
    
    # Get skillboost profiles
    profiles = session.query(SkillboostProfile).filter_by(email=email).all()
    
    # Get masterclasses
    masterclasses = session.query(MasterClass).filter_by(email=email).all()
    
    return {
        'user': user,
        'courses': courses,
        'skillboost_profiles': profiles,
        'masterclasses': masterclasses
    }


def search_users(session, search_term, limit=50):
    """Search users by name, email, or phone"""
    search_pattern = f"%{search_term}%"
    
    users = session.query(UserPII).filter(
        or_(
            UserPII.name.ilike(search_pattern),
            UserPII.email.ilike(search_pattern),
            UserPII.phone_number.ilike(search_pattern)
        )
    ).limit(limit).all()
    
    return users


def get_verification_statistics(session):
    """Get overall verification statistics"""
    
    # Profile verification stats
    profile_stats = session.query(
        func.count(SkillboostProfile.email).label('total'),
        func.sum(case((SkillboostProfile.valid == True, 1), else_=0)).label('verified'),
        func.sum(case((SkillboostProfile.valid == False, 1), else_=0)).label('failed'),
        func.sum(case((SkillboostProfile.valid.is_(None), 1), else_=0)).label('pending')
    ).first()
    
    # Badge verification stats (considering date requirement)
    # Count badges that are truly valid (valid=True AND date requirement met)
    all_courses = session.query(Course).all()
    verified_count = sum(1 for c in all_courses if is_badge_valid(c))
    failed_count = sum(1 for c in all_courses if c.valid is False)
    pending_count = sum(1 for c in all_courses if c.valid.is_(None))
    total_count = len(all_courses)
    
    badge_stats = type('obj', (object,), {
        'total': total_count,
        'verified': verified_count,
        'failed': failed_count,
        'pending': pending_count
    })()
    
    # User stats
    user_stats = session.query(
        func.count(UserPII.email).label('total_users')
    ).first()
    
    # Masterclass stats
    masterclass_stats = session.query(
        func.count(MasterClass.email).label('total_attendance')
    ).first()
    
    return {
        'profiles': {
            'total': profile_stats.total or 0,
            'verified': profile_stats.verified or 0,
            'failed': profile_stats.failed or 0,
            'pending': profile_stats.pending or 0
        },
        'badges': {
            'total': badge_stats.total or 0,
            'verified': badge_stats.verified or 0,
            'failed': badge_stats.failed or 0,
            'pending': badge_stats.pending or 0
        },
        'users': {
            'total': user_stats.total_users or 0
        },
        'masterclasses': {
            'total_attendance': masterclass_stats.total_attendance or 0
        }
    }


def get_pending_verifications(session, limit=100):
    """Get records pending verification"""
    
    # Pending profiles
    pending_profiles = session.query(SkillboostProfile).filter(
        SkillboostProfile.valid.is_(None)
    ).limit(limit).all()
    
    # Pending badges
    pending_badges = session.query(Course).filter(
        Course.valid.is_(None),
        Course.share_skill_badge_public_link.isnot(None)
    ).limit(limit).all()
    
    return {
        'profiles': pending_profiles,
        'badges': pending_badges
    }


def get_failed_verifications(session, limit=100):
    """Get records with failed verification"""
    
    # Failed profiles
    failed_profiles = session.query(SkillboostProfile).filter(
        SkillboostProfile.valid == False
    ).limit(limit).all()
    
    # Failed badges
    failed_badges = session.query(Course).filter(
        Course.valid == False
    ).limit(limit).all()
    
    return {
        'profiles': failed_profiles,
        'badges': failed_badges
    }


def get_course_statistics(session):
    """Get statistics by course/problem statement"""
    
    stats = session.query(
        Course.problem_statement,
        func.count(Course.email).label('total_submissions'),
        func.sum(case((Course.valid == True, 1), else_=0)).label('verified'),
        func.sum(case((Course.valid == False, 1), else_=0)).label('failed'),
        func.sum(case((Course.valid.is_(None), 1), else_=0)).label('pending')
    ).group_by(Course.problem_statement).all()
    
    return stats


def get_masterclass_statistics(session):
    """Get detailed statistics by masterclass with live and recorded breakdown"""
    
    stats = session.query(
        MasterClass.master_class_name,
        func.count(MasterClass.email).label('total_attendees'),
        func.sum(case((MasterClass.live == True, 1), else_=0)).label('live_valid'),
        func.sum(case((MasterClass.live == False, 1), else_=0)).label('live_invalid'),
        func.sum(case((MasterClass.recorded == True, 1), else_=0)).label('recorded_valid'),
        func.sum(case((MasterClass.recorded == False, 1), else_=0)).label('recorded_invalid'),
        func.sum(case((MasterClass.live.is_(None) & MasterClass.recorded.is_(None), 1), else_=0)).label('pending')
    ).group_by(MasterClass.master_class_name).order_by(MasterClass.master_class_name).all()
    
    return stats


def get_user_course_count(session, email):
    """Get count of courses for a user"""
    
    # Count valid courses considering date requirement
    user_courses = session.query(Course).filter(Course.email == email).all()
    valid_count = sum(1 for c in user_courses if is_badge_valid(c))
    
    return valid_count


def get_recent_changes(session, limit=50):
    """Get recent changes from master log"""
    
    logs = session.query(MasterLog).order_by(
        MasterLog.changed_at.desc()
    ).limit(limit).all()
    
    return logs


def get_users_with_course_completion(session, min_courses=1, limit=100):
    """Get users who have completed at least N courses (considering date requirement)"""
    
    # Get all users with their courses and filter by valid badges (considering date requirement)
    all_users_courses = session.query(UserPII, Course).join(
        Course, UserPII.email == Course.email
    ).all()
    
    # Group by user and count valid badges
    user_badge_counts = {}
    for user, course in all_users_courses:
        if user.email not in user_badge_counts:
            user_badge_counts[user.email] = {'name': user.name, 'email': user.email, 'count': 0}
        if is_badge_valid(course):
            user_badge_counts[user.email]['count'] += 1
    
    # Filter users with at least min_courses valid badges
    filtered_users = [
        type('obj', (object,), {'email': u['email'], 'name': u['name'], 'course_count': u['count']})()
        for u in user_badge_counts.values() if u['count'] >= min_courses
    ]
    
    # Sort by badge count descending and limit
    filtered_users.sort(key=lambda x: x.course_count, reverse=True)
    
    return filtered_users[:limit]


def export_all_data(session):
    """Export all data for reporting"""
    
    # Query to get comprehensive user data
    results = session.query(
        UserPII.email,
        UserPII.name,
        UserPII.phone_number,
        UserPII.gender,
        UserPII.country,
        UserPII.state,
        UserPII.city,
        UserPII.designation,
        UserPII.occupation,
        func.count(func.distinct(Course.problem_statement)).label('courses_completed'),
        func.count(func.distinct(MasterClass.master_class_name)).label('masterclasses_attended')
    ).outerjoin(
        Course, UserPII.email == Course.email
    ).outerjoin(
        MasterClass, UserPII.email == MasterClass.email
    ).group_by(
        UserPII.email,
        UserPII.name,
        UserPII.phone_number,
        UserPII.gender,
        UserPII.country,
        UserPII.state,
        UserPII.city,
        UserPII.designation,
        UserPII.occupation
    ).all()
    
    return results


def get_demographic_statistics(session):
    """Get demographic breakdown statistics"""
    
    # Gender distribution
    gender_stats = session.query(
        UserPII.gender,
        func.count(UserPII.email).label('count')
    ).filter(
        UserPII.gender.isnot(None)
    ).group_by(UserPII.gender).all()
    
    # Country distribution
    country_stats = session.query(
        UserPII.country,
        func.count(UserPII.email).label('count')
    ).filter(
        UserPII.country.isnot(None)
    ).group_by(UserPII.country).order_by(func.count(UserPII.email).desc()).limit(10).all()
    
    # State distribution
    state_stats = session.query(
        UserPII.state,
        func.count(UserPII.email).label('count')
    ).filter(
        UserPII.state.isnot(None)
    ).group_by(UserPII.state).order_by(func.count(UserPII.email).desc()).limit(10).all()
    
    # City distribution
    city_stats = session.query(
        UserPII.city,
        func.count(UserPII.email).label('count')
    ).filter(
        UserPII.city.isnot(None)
    ).group_by(UserPII.city).order_by(func.count(UserPII.email).desc()).limit(10).all()
    
    # Occupation distribution
    # Note: SCHOOL_STUDENT is consolidated with COLLEGE_STUDENT
    occupation_stats_raw = session.query(
        UserPII.occupation,
        func.count(UserPII.email).label('count')
    ).filter(
        UserPII.occupation.isnot(None)
    ).group_by(UserPII.occupation).order_by(func.count(UserPII.email).desc()).limit(10).all()
    
    # Consolidate SCHOOL_STUDENT with COLLEGE_STUDENT
    occupation_consolidated = {}
    for occ in occupation_stats_raw:
        # Normalize: treat SCHOOL_STUDENT as COLLEGE_STUDENT
        normalized_occ = 'COLLEGE_STUDENT' if occ.occupation == 'SCHOOL_STUDENT' else occ.occupation
        
        if normalized_occ in occupation_consolidated:
            occupation_consolidated[normalized_occ] += occ.count
        else:
            occupation_consolidated[normalized_occ] = occ.count
    
    # Convert to list format for return
    occupation_stats = [
        {'label': occ, 'count': count} 
        for occ, count in sorted(occupation_consolidated.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # Academy 1.0 participation
    academy1_stats = session.query(
        UserPII.participated_in_academy_1,
        func.count(UserPII.email).label('count')
    ).group_by(UserPII.participated_in_academy_1).all()
    
    return {
        'gender': [{'label': g.gender, 'count': g.count} for g in gender_stats],
        'country': [{'label': c.country, 'count': c.count} for c in country_stats],
        'state': [{'label': s.state, 'count': s.count} for s in state_stats],
        'city': [{'label': c.city, 'count': c.count} for c in city_stats],
        'occupation': occupation_stats,
        'academy1': [{'label': 'Yes' if a.participated_in_academy_1 else 'No', 'count': a.count} for a in academy1_stats]
    }


def get_dashboard_statistics(session):
    """Get comprehensive statistics for dashboard"""
    
    # Total users
    total_users = session.query(func.count(UserPII.email)).scalar() or 0
    
    # Total badges
    total_badges = session.query(func.count(Course.email)).scalar() or 0
    # Count truly valid badges (considering date requirement)
    all_courses = session.query(Course).all()
    verified_badges = sum(1 for c in all_courses if is_badge_valid(c))
    failed_badges = session.query(func.count(Course.email)).filter(Course.valid == False).scalar() or 0
    pending_badges = session.query(func.count(Course.email)).filter(Course.valid.is_(None)).scalar() or 0
    
    # Total profiles
    total_profiles = session.query(func.count(SkillboostProfile.email)).scalar() or 0
    verified_profiles = session.query(func.count(SkillboostProfile.email)).filter(SkillboostProfile.valid == True).scalar() or 0
    failed_profiles = session.query(func.count(SkillboostProfile.email)).filter(SkillboostProfile.valid == False).scalar() or 0
    pending_profiles = session.query(func.count(SkillboostProfile.email)).filter(SkillboostProfile.valid.is_(None)).scalar() or 0
    
    # Total masterclass attendance
    total_masterclass = session.query(func.count(MasterClass.email)).scalar() or 0
    unique_masterclass_attendees = session.query(func.count(func.distinct(MasterClass.email))).scalar() or 0
    unique_masterclasses = session.query(func.count(func.distinct(MasterClass.master_class_name))).scalar() or 0
    
    # Users with verified profiles
    users_with_verified_profiles = session.query(func.count(func.distinct(SkillboostProfile.email))).filter(
        SkillboostProfile.valid == True
    ).scalar() or 0
    
    # Users with verified badges (considering date requirement)
    all_courses = session.query(Course).all()
    users_with_valid_badges = set()
    for c in all_courses:
        if is_badge_valid(c):
            users_with_valid_badges.add(c.email)
    users_with_verified_badges = len(users_with_valid_badges)
    
    # Top performers (users with most verified badges, considering date requirement)
    all_courses_with_users = session.query(Course, UserPII).join(
        UserPII, Course.email == UserPII.email
    ).all()
    
    # Count valid badges per user
    user_badge_counts = {}
    for course, user in all_courses_with_users:
        if is_badge_valid(course):
            if user.email not in user_badge_counts:
                user_badge_counts[user.email] = {'name': user.name, 'email': user.email, 'count': 0}
            user_badge_counts[user.email]['count'] += 1
    
    # Sort and get top 10
    top_performers = sorted(user_badge_counts.values(), key=lambda x: x['count'], reverse=True)[:10]
    # Convert to list of objects with badge_count attribute for compatibility
    top_performers = [type('obj', (object,), {'name': p['name'], 'email': p['email'], 'badge_count': p['count']})() for p in top_performers]
    
    return {
        'users': {
            'total': total_users,
            'with_verified_profiles': users_with_verified_profiles,
            'with_verified_badges': users_with_verified_badges
        },
        'badges': {
            'total': total_badges,
            'verified': verified_badges,
            'failed': failed_badges,
            'pending': pending_badges,
            'verification_rate': round((verified_badges / total_badges * 100) if total_badges > 0 else 0, 1)
        },
        'profiles': {
            'total': total_profiles,
            'verified': verified_profiles,
            'failed': failed_profiles,
            'pending': pending_profiles,
            'verification_rate': round((verified_profiles / total_profiles * 100) if total_profiles > 0 else 0, 1)
        },
        'masterclasses': {
            'total_attendance': total_masterclass,
            'unique_attendees': unique_masterclass_attendees,
            'unique_classes': unique_masterclasses,
            'avg_per_user': round((total_masterclass / unique_masterclass_attendees) if unique_masterclass_attendees > 0 else 0, 1)
        },
        'top_performers': [{'name': p.name, 'email': p.email, 'badges': p.badge_count} for p in top_performers]
    }


def get_badge_statistics_breakdown(session):
    """Get detailed badge statistics with breakdown by occupation/category"""
    import re
    
    # Track name mappings from problem_statement prefixes to display names
    track_prefix_map = {
        '[Dev Ops]': 'Dev Ops Track',
        '[DevOps]': 'Dev Ops Track',
        '[Security]': 'Security Track',
        '[Networking]': 'Networking Track',
        '[AI/ML]': 'AI/ML Track',
        '[Data]': 'Data Track',
        '[Serverless]': 'Serverless Track'
    }
    
    # Get all badge submissions with user occupation
    # Query full Course objects to access all attributes including completion_date
    all_badges = session.query(
        Course,
        UserPII.occupation
    ).outerjoin(
        UserPII, Course.email == UserPII.email
    ).all()
    
    # Parse and organize badges by track
    parsed_badges = []
    for course_obj, occupation in all_badges:
        # Extract track and badge name from problem_statement
        # Format: "[Track] Badge Name" or just "Badge Name"
        match = re.match(r'\[(.*?)\]\s*(.*)', course_obj.problem_statement.strip())
        if match:
            track_prefix = f"[{match.group(1)}]"
            badge_name = match.group(2).strip().rstrip(',').strip()
            track_display = track_prefix_map.get(track_prefix, f"{match.group(1)} Track")
        else:
            # No prefix, try to infer or use "Other"
            track_display = 'Other Track'
            badge_name = course_obj.problem_statement.strip().rstrip(',').strip()
        
        # Check if badge is truly valid (considering date requirement)
        is_valid = is_badge_valid(course_obj)
        
        parsed_badges.append({
            'track': track_display,
            'badge_name': badge_name,
            'valid': is_valid,  # Use computed validity instead of raw valid flag
            'occupation': occupation
        })
    
    # Organize data by tracks
    badge_data = {}
    
    # Group by track
    tracks = {}
    for badge in parsed_badges:
        track_name = badge['track']
        if track_name not in tracks:
            tracks[track_name] = []
        tracks[track_name].append(badge)
    
    # Process each track
    for track_name, track_badges in tracks.items():
        # Get unique badge names in this track
        badge_names = {}
        for badge in track_badges:
            if badge['badge_name'] not in badge_names:
                badge_names[badge['badge_name']] = []
            badge_names[badge['badge_name']].append(badge)
        
        track_info = {
            'track_total': 0,
            'track_valid': 0,
            'track_invalid': 0,
            'badges': []
        }
        
        # Process each unique badge
        for badge_name, submissions in badge_names.items():
            total = len(submissions)
            valid = sum(1 for b in submissions if b['valid'] == True)
            invalid = sum(1 for b in submissions if b['valid'] == False)
            
            # Breakdown by occupation
            # Map database values to display labels
            # Note: SCHOOL_STUDENT is treated as COLLEGE_STUDENT
            occupation_mapping = {
                'COLLEGE_STUDENT': 'College Student',
                'SCHOOL_STUDENT': 'College Student',  # Consolidated: school students are treated as college students
                'PROFESSIONAL': 'Professional',
                'STARTUP': 'Startup',
                'FREELANCE': 'Freelance'
            }
            
            breakdown = {}
            categories_display = ['College Student', 'Freelance', 'Professional', 'Startup']
            
            for display_category in categories_display:
                # Find all database values that map to this display category
                db_values = [k for k, v in occupation_mapping.items() if v == display_category]
                
                # Get submissions matching any of the database values
                category_submissions = [b for b in submissions if b['occupation'] in db_values]
                
                breakdown[display_category] = {
                    'valid': sum(1 for b in category_submissions if b['valid'] == True),
                    'invalid': sum(1 for b in category_submissions if b['valid'] == False)
                }
            
            track_info['badges'].append({
                'name': badge_name,
                'total': total,
                'valid': valid,
                'invalid': invalid,
                'breakdown': breakdown
            })
            
            track_info['track_total'] += total
            track_info['track_valid'] += valid
            track_info['track_invalid'] += invalid
        
        # Sort badges by name
        track_info['badges'].sort(key=lambda x: x['name'])
        
        badge_data[track_name] = track_info
    
    # Get summary statistics
    # Count total profile records (not distinct emails) to match dashboard
    total_profiles = session.query(func.count(SkillboostProfile.email)).scalar() or 0
    valid_profiles = session.query(func.count(SkillboostProfile.email)).filter(
        SkillboostProfile.valid == True
    ).scalar() or 0
    
    total_badges = session.query(func.count(Course.email)).scalar() or 0
    # Count truly valid badges (considering date requirement)
    all_courses = session.query(Course).all()
    valid_badges = sum(1 for c in all_courses if is_badge_valid(c))
    invalid_badges = session.query(func.count(Course.email)).filter(Course.valid == False).scalar() or 0
    
    summary = {
        'total_profiles': total_profiles,
        'valid_profiles': valid_profiles,
        'valid_badges': valid_badges,
        'total_badges': total_badges,
        'invalid_badges': invalid_badges
    }
    
    return {
        'badge_data': badge_data,
        'summary': summary
    }


def get_certificate_eligible_users(session, track_name):
    """
    Get users eligible for certificate in a specific track
    
    Eligibility criteria:
    1. User must have completed ALL courses under that track (valid = TRUE)
    2. User must have attended the master class for that track (live = TRUE OR recorded = TRUE)
    
    Args:
        session: Database session
        track_name: Track name (e.g., "AI/ML", "Data", "Dev Ops", "Security", "Networking", "Serverless")
    
    Returns:
        List of eligible users with their PII data
    """
    import re
    
    # Map track names to problem_statement prefixes
    track_to_prefix = {
        'AI/ML': ['[AI/ML]'],
        'Data': ['[Data]'],
        'Dev Ops': ['[Dev Ops]', '[DevOps]'],
        'Security': ['[Security]'],
        'Networking': ['[Networking]'],
        'Serverless': ['[Serverless]']
    }
    
    # Map track names to master class names
    track_to_masterclass = {
        'AI/ML': 'AI/ML Track - Master Class',
        'Data': 'Data Track - Master Class',
        'Dev Ops': 'Dev Ops Track - Master Class',
        'Security': 'Security Track - Master Class',
        'Networking': 'Networking Track - Master Class',
        'Serverless': 'Serverless Track - Master Class'
    }
    
    if track_name not in track_to_prefix:
        return []
    
    prefixes = track_to_prefix[track_name]
    master_class_name = track_to_masterclass[track_name]
    
    # Get all courses for this track
    all_track_courses = []
    for prefix in prefixes:
        # Find courses that start with this prefix
        courses = session.query(Course.problem_statement).filter(
            Course.problem_statement.like(f'{prefix}%')
        ).distinct().all()
        
        for course in courses:
            # Parse to get clean course name
            match = re.match(r'\[(.*?)\]\s*(.*)', course.problem_statement.strip())
            if match:
                all_track_courses.append(course.problem_statement)
    
    if not all_track_courses:
        return []
    
    # Get all users who have at least one course in this track
    users_with_courses = session.query(Course.email).filter(
        Course.problem_statement.in_(all_track_courses)
    ).distinct().all()
    
    eligible_users = []
    
    for (user_email,) in users_with_courses:
        # Check if user has ALL courses for this track with valid=TRUE
        user_courses = session.query(Course).filter(
            Course.email == user_email,
            Course.problem_statement.in_(all_track_courses)
        ).all()
        
        # Count valid courses (considering both valid flag and completion date)
        valid_courses = [c for c in user_courses if is_badge_valid(c)]
        
        # Check if user has all required courses validated
        if len(valid_courses) < len(all_track_courses):
            continue  # User hasn't completed all courses
        
        # Check if user has master class attendance (live OR recorded = TRUE)
        master_class = session.query(MasterClass).filter(
            MasterClass.email == user_email,
            MasterClass.master_class_name == master_class_name
        ).first()
        
        if not master_class:
            continue  # User hasn't attended master class
        
        if master_class.live != True and master_class.recorded != True:
            continue  # Master class not validated
        
        # User is eligible! Get their PII data
        user = session.query(UserPII).filter_by(email=user_email).first()
        if user:
            # Normalize occupation: Convert SCHOOL_STUDENT to COLLEGE_STUDENT
            normalized_occupation = 'COLLEGE_STUDENT' if user.occupation == 'SCHOOL_STUDENT' else user.occupation
            
            eligible_users.append({
                'email': user.email,
                'name': user.name,
                'phone_number': user.phone_number,
                'gender': user.gender,
                'country': user.country,
                'state': user.state,
                'city': user.city,
                'occupation': normalized_occupation,
                'linkedin': user.linkedin,
                'courses_completed': len(valid_courses),
                'total_courses': len(all_track_courses),
                'master_class_attended': True,
                'master_class_type': 'Live' if master_class.live == True else 'Recorded'
            })
    
    return eligible_users

