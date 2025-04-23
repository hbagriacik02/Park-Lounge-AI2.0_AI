#!/bin/python3

import sys
import datetime
import pandas as pd
import ultralytics as yolo

license_plate_input = sys.argv[1]
illegal_dataFrame = pd.DataFrame(columns=['illegal_traffic_license_plate'])

filepath = '../log/{date}_illegal_log.csv'
file = filepath.format(date=datetime.datetime.now().strftime('%Y-%m-%d'))

def main():
    print(validate_is_plate_allowed())

def validate_is_plate_allowed():
    car_plate_data = read_csv_access_allowed()
    if license_plate_input in car_plate_data.values:
        print("Exist")
        return True
    else:
        print("Not Exist")
        illegal_dataFrame.loc[len(illegal_dataFrame)] = license_plate_input
        illegal_dataFrame.to_csv(file, index=False)
        return False

def read_csv_access_allowed():
    return pd.read_csv('../access_allowed.csv')

if __name__ == '__main__':
    main()