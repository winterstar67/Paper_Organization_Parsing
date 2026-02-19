import os
from datetime import datetime

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SRC_DIR)
RUN_DATE = datetime.now().strftime('%Y-%m-%d')

def results_dir(phase: str) -> str:
    path = os.path.join(PROJECT_DIR, 'results', RUN_DATE, phase)
    os.makedirs(path, exist_ok=True)
    return path

def backup_dir(phase: str) -> str:
    path = os.path.join(PROJECT_DIR, 'backup', RUN_DATE, phase)
    os.makedirs(path, exist_ok=True)
    return path

def master_id_table_path() -> str:
    path = os.path.join(PROJECT_DIR, 'results')
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, 'ID_TABLE.csv')
