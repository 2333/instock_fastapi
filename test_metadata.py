#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/zhangkai/projects/instock_fastapi')

# Set up minimal env
import os
os.environ.setdefault('DATABASE_URL', 'postgresql://user:pass@localhost/db')

# Import and call
from app.services.selection_service import SelectionService

metadata = SelectionService.get_screening_metadata()
print("Metadata keys:", list(metadata.keys()))
print("Filter fields count:", len(metadata.get('filter_fields', [])))
print("Filter field keys:", [f['key'] for f in metadata.get('filter_fields', [])])
