"""
Script to initialize badge data in the database
"""
from main import app
from models import db, Badge

def create_badges():
    """
    Create badge records for all types and levels
    """
    print("Initializing badge data...")
    
    # Check if badges already exist
    badge_count = Badge.query.count()
    if badge_count > 0:
        print(f"{badge_count} badges already exist. Skipping initialization.")
        return
    
    # Badge configuration data
    badge_configs = [
        # Reader badges
        {
            'type': Badge.TYPE_READER,
            'level': Badge.LEVEL_BRONZE,
            'name': 'Bronze Reader',
            'description': 'Read 5 documents',
            'criteria_count': 5,
            'icon': '/static/img/badges/reader_bronze.svg'
        },
        {
            'type': Badge.TYPE_READER,
            'level': Badge.LEVEL_SILVER,
            'name': 'Silver Reader',
            'description': 'Read 15 documents',
            'criteria_count': 15,
            'icon': '/static/img/badges/reader_silver.svg'
        },
        {
            'type': Badge.TYPE_READER,
            'level': Badge.LEVEL_GOLD,
            'name': 'Gold Reader',
            'description': 'Read 30 documents',
            'criteria_count': 30,
            'icon': '/static/img/badges/reader_gold.svg'
        },
        {
            'type': Badge.TYPE_READER,
            'level': Badge.LEVEL_PLATINUM,
            'name': 'Platinum Reader',
            'description': 'Read 50 documents',
            'criteria_count': 50,
            'icon': '/static/img/badges/reader_platinum.svg'
        },
        
        # Searcher badges
        {
            'type': Badge.TYPE_SEARCHER,
            'level': Badge.LEVEL_BRONZE,
            'name': 'Bronze Searcher',
            'description': 'Perform 5 searches',
            'criteria_count': 5,
            'icon': '/static/img/badges/searcher_bronze.svg'
        },
        {
            'type': Badge.TYPE_SEARCHER,
            'level': Badge.LEVEL_SILVER,
            'name': 'Silver Searcher',
            'description': 'Perform 15 searches',
            'criteria_count': 15,
            'icon': '/static/img/badges/searcher_silver.svg'
        },
        {
            'type': Badge.TYPE_SEARCHER,
            'level': Badge.LEVEL_GOLD,
            'name': 'Gold Searcher',
            'description': 'Perform 30 searches',
            'criteria_count': 30,
            'icon': '/static/img/badges/searcher_gold.svg'
        },
        {
            'type': Badge.TYPE_SEARCHER,
            'level': Badge.LEVEL_PLATINUM,
            'name': 'Platinum Searcher',
            'description': 'Perform 50 searches',
            'criteria_count': 50,
            'icon': '/static/img/badges/searcher_platinum.svg'
        },
        
        # Contributor badges
        {
            'type': Badge.TYPE_CONTRIBUTOR,
            'level': Badge.LEVEL_BRONZE,
            'name': 'Bronze Contributor',
            'description': 'Upload 2 documents',
            'criteria_count': 2,
            'icon': '/static/img/badges/contributor_bronze.svg'
        },
        {
            'type': Badge.TYPE_CONTRIBUTOR,
            'level': Badge.LEVEL_SILVER,
            'name': 'Silver Contributor',
            'description': 'Upload 5 documents',
            'criteria_count': 5,
            'icon': '/static/img/badges/contributor_silver.svg'
        },
        {
            'type': Badge.TYPE_CONTRIBUTOR,
            'level': Badge.LEVEL_GOLD,
            'name': 'Gold Contributor',
            'description': 'Upload 10 documents',
            'criteria_count': 10,
            'icon': '/static/img/badges/contributor_gold.svg'
        },
        {
            'type': Badge.TYPE_CONTRIBUTOR,
            'level': Badge.LEVEL_PLATINUM,
            'name': 'Platinum Contributor',
            'description': 'Upload 20 documents',
            'criteria_count': 20,
            'icon': '/static/img/badges/contributor_platinum.svg'
        },
        
        # Summarizer badges
        {
            'type': Badge.TYPE_SUMMARIZER,
            'level': Badge.LEVEL_BRONZE,
            'name': 'Bronze Summarizer',
            'description': 'Generate 3 document summaries',
            'criteria_count': 3,
            'icon': '/static/img/badges/summarizer_bronze.svg'
        },
        {
            'type': Badge.TYPE_SUMMARIZER,
            'level': Badge.LEVEL_SILVER,
            'name': 'Silver Summarizer',
            'description': 'Generate 8 document summaries',
            'criteria_count': 8,
            'icon': '/static/img/badges/summarizer_silver.svg'
        },
        {
            'type': Badge.TYPE_SUMMARIZER,
            'level': Badge.LEVEL_GOLD,
            'name': 'Gold Summarizer',
            'description': 'Generate 15 document summaries',
            'criteria_count': 15,
            'icon': '/static/img/badges/summarizer_gold.svg'
        },
        {
            'type': Badge.TYPE_SUMMARIZER,
            'level': Badge.LEVEL_PLATINUM,
            'name': 'Platinum Summarizer',
            'description': 'Generate 25 document summaries',
            'criteria_count': 25,
            'icon': '/static/img/badges/summarizer_platinum.svg'
        },
    ]
    
    # Create badge records
    for config in badge_configs:
        badge = Badge(
            name=config['name'],
            description=config['description'],
            type=config['type'],
            level=config['level'],
            criteria_count=config['criteria_count'],
            icon=config['icon']
        )
        db.session.add(badge)
    
    # Commit changes
    db.session.commit()
    print(f"Created {len(badge_configs)} badge records.")

if __name__ == '__main__':
    with app.app_context():
        create_badges()