import os
import pandas as pd
from datetime import datetime

class LogHandler:
    def __init__(self, access_allowed_file='../access_allowed.csv'):
        self.access_allowed_file = access_allowed_file
        self.access_allowed = self.read_csv_access_allowed()
        self.file_path = '../log/{date}_illegal_log.csv'
        self.file = self.file_path.format(date=datetime.now().strftime('%Y%m%d'))

    def read_csv_access_allowed(self):
        try:
            df = pd.read_csv(self.access_allowed_file)
            return set(df['allowed_traffic_license_plate'].str.strip().str.upper())
        except FileNotFoundError:
            print(f"Not Found: {self.access_allowed_file}")
            return set()

    def validate_is_plate_allowed(self, license_plate_input):
        if not license_plate_input:
            print("No Plate entered")
            return False
        license_plate_input = license_plate_input.strip().upper()
        if license_plate_input in self.access_allowed:
            print("Plate exists")
            return True
        else:
            print("Plate does not exist")
            return False

    def log_denied_access(self, license_plate, screenshot_path):
        log_entry = pd.DataFrame({
            'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'illegal_traffic_license_plate': [license_plate],
            'screenshot_path': [screenshot_path or 'N/A']
        })
        os.makedirs(os.path.dirname(self.file), exist_ok=True)
        if os.path.exists(self.file):
            log_entry.to_csv(self.file, mode='a', header=False, index=False)
        else:
            log_entry.to_csv(self.file, mode='w', header=True, index=False)
        print(f"Logging plate: {license_plate}")