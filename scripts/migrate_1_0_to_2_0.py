#!/usr/bin/env python
"""
Migrate Colandr 1.0 database to 2.0 schema.

The v1 database schema should match v2's initial migration
(d225d270af3f). This script:
1. Sets alembic_version to d225d270af3f (the initial migration)
2. Runs migrations normally from there
3. This gives us a clean Alembic state for future migrations

Note: If the initial migration fails (tables already exist), we fall back to
setting alembic_version to 1c023402f9d8 and running from there.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from colandr.app import create_app
from colandr.extensions import db

app = create_app()

with app.app_context():
    # Step 0: Clean up duplicate rows in users_to_reviews (if any)
    print("Checking for duplicate rows in users_to_reviews...")
    result = db.session.execute(db.text("""
        SELECT review_id, user_id, COUNT(*) as cnt
        FROM users_to_reviews
        GROUP BY review_id, user_id
        HAVING COUNT(*) > 1
    """))
    duplicates = result.fetchall()
    if duplicates:
        print(f"Found {len(duplicates)} duplicate(s), removing...")
        db.session.execute(db.text("""
            DELETE FROM users_to_reviews a
            USING users_to_reviews b
            WHERE a.ctid < b.ctid
            AND a.review_id = b.review_id
            AND a.user_id = b.user_id
        """))
        db.session.commit()
        print("✓ Duplicates removed")
    else:
        print("✓ No duplicates found")
    
    # Step 1: Set alembic_version to initial migration (d225d270af3f)
    print("\nSetting alembic_version to d225d270af3f (initial migration)...")
    db.session.execute(db.text("UPDATE alembic_version SET version_num = 'd225d270af3f'"))
    db.session.commit()
    print("✓ alembic_version set to initial migration")
    
    # Step 2: Run migrations normally
    # Alembic will upgrade from d225d270af3f to head
    print("\nRunning migrations from initial to head...")
    from flask_migrate import upgrade
    try:
        upgrade()
        print("✓ Migrations complete - database is now at head revision")
        print("✓ Future Alembic migrations will work normally")
    except Exception as e:
        print(f"\n⚠ Migration failed: {e}")
        print("\nFalling back to alternative approach...")
        print("Setting alembic_version to 1c023402f9d8 (skipping initial migration)...")
        db.session.execute(db.text("UPDATE alembic_version SET version_num = '1c023402f9d8'"))
        db.session.commit()
        upgrade()
        print("✓ Migrations complete (using fallback approach)")
