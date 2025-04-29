import sys
import datetime
import pandas as pd

license_plate_input = sys.argv[1]
illegal_dataFrame = pd.DataFrame(columns=['illegal_traffic_license_plate'])

FILE_PATH = '../log/{date}_illegal_log.csv'
FILE = FILE_PATH.format(date=datetime.datetime.now().strftime('%Y-%m-%d'))

def read_csv_access_allowed():
    return pd.read_csv('../access_allowed.csv')

def validate_is_plate_allowed():
    car_plate_data = read_csv_access_allowed()
    if license_plate_input in car_plate_data.values:
        print("Plate exist")
        return True
    else:
        print("Plate not Exist")
        illegal_dataFrame.loc[len(illegal_dataFrame)] = license_plate_input
        illegal_dataFrame.to_csv(FILE, index=False)
        return False
