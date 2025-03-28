"""
Migration script to add cascade delete to user activity foreign keys
"""
import os
import sys
from sqlalchemy import create_engine, MetaData, Table, Column, String, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import reflection
from sqlalchemy.schema import DropConstraint, ForeignKeyConstraint

def run_migration():
    """Update foreign key to add cascade delete"""
    # Get database URL from environment variable
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create SQLAlchemy engine
    engine = create_engine(database_url)
    
    # Create metadata object
    metadata = MetaData()
    
    # Reflect existing tables
    metadata.reflect(bind=engine)
    
    # Get inspector for finding constraints
    inspector = reflection.Inspector.from_engine(engine)
    
    # Find the foreign key constraint we want to replace
    fk_constraint_name = None
    for fk in inspector.get_foreign_keys('user_activity'):
        if fk['referred_table'] == 'document':
            fk_constraint_name = fk['name']
            break
    
    if not fk_constraint_name:
        print("Foreign key constraint for document_id not found")
        sys.exit(1)
    
    print(f"Found constraint to update: {fk_constraint_name}")
    
    # Use raw SQL to update the constraint
    print("Updating foreign key constraint with ON DELETE CASCADE...")
    update_constraint_with_raw_sql(
        engine,
        table_name='user_activity',
        column_name='document_id',
        ref_table='document',
        ref_column='id',
        constraint_name=fk_constraint_name
    )
    
    print("Migration completed successfully")

# Helper class for constraint management
# For PostgreSQL, it's simpler to use raw SQL for constraint modification
def update_constraint_with_raw_sql(engine, table_name, column_name, ref_table, ref_column, constraint_name):
    """Use raw SQL to update a constraint with CASCADE delete"""
    with engine.begin() as conn:
        # Drop the existing constraint
        drop_sql = text(f"""
        ALTER TABLE {table_name} 
        DROP CONSTRAINT IF EXISTS {constraint_name};
        """)
        conn.execute(drop_sql)
        
        # Add the new constraint with CASCADE
        add_sql = text(f"""
        ALTER TABLE {table_name}
        ADD CONSTRAINT {constraint_name}
        FOREIGN KEY ({column_name}) REFERENCES {ref_table}({ref_column}) ON DELETE CASCADE;
        """)
        conn.execute(add_sql)
        
if __name__ == '__main__':
    run_migration()