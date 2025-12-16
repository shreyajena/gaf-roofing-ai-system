"""
Quick database check script - shows schema and sample rows for each table
"""

from app.models import get_db, Contractor, Certification, ContractorText
from sqlalchemy import inspect

def print_schema_and_sample(table_class, table_name):
    """Print table schema and a sample row"""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Get table schema
        inspector = inspect(table_class)
        columns = inspector.columns
        
        print("=" * 80)
        print(f"TABLE: {table_name}")
        print("=" * 80)
        print("\nSCHEMA:")
        print("-" * 80)
        for col in columns:
            col_type = str(col.type)
            nullable = "NULL" if col.nullable else "NOT NULL"
            print(f"  {col.name:30} {col_type:20} {nullable}")
        
        # Get sample row
        sample = db.query(table_class).first()
        if sample:
            print("\nSAMPLE ROW:")
            print("-" * 80)
            for col in columns:
                value = getattr(sample, col.name, None)
                if value is None:
                    value_str = "NULL"
                elif isinstance(value, str) and len(value) > 60:
                    value_str = value[:57] + "..."
                else:
                    value_str = str(value)
                print(f"  {col.name:30} = {value_str}")
        else:
            print("\nSAMPLE ROW: (No data in table)")
        
        # Count rows
        count = db.query(table_class).count()
        print(f"\nTotal rows: {count}")
        print()
        
    finally:
        db.close()


def main():
    print("\n" + "=" * 80)
    print("DATABASE CHECK - SCHEMA AND SAMPLE ROWS")
    print("=" * 80 + "\n")
    
    # Check each table
    print_schema_and_sample(Contractor, "contractors")
    print_schema_and_sample(Certification, "certifications")
    print_schema_and_sample(ContractorText, "contractor_text")
    
    print("=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

