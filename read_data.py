import glob
import numpy as np
import csv
from netCDF4 import Dataset
import datetime
from datetime import timezone


def get_correct_time(tai93_timestamp: float) -> str:
    """
    Convert Timestamp from TAI93 to UNIX format.

    The timestamp in ISS LIS NQC files is defined as time since 1993/01/01.
    This function converts TAI93 timestamp into standard UNIX timestamp

    :param tai93_timestamp: timestamp in TAI93 format
    :return: UNIX timestamp
    """


    d1 = datetime.datetime(year=1992, month=1, day=1, hour=23, minute=59, second=59)
    timestamp1 = d1.replace(tzinfo=timezone.utc).timestamp()

    d2 = datetime.datetime.utcfromtimestamp(tai93_timestamp)
    timestamp2 = d2.replace(tzinfo=timezone.utc).timestamp()

    d3 = datetime.datetime.utcfromtimestamp(timestamp2 + timestamp1)

    return str(d3)


def convert_timestamp(tai93_timestamp_array: list) -> list:
    """
    This function takes a list of timestamps in TAI93 format and converts them all to unix timestamps

    :param tai93_timestamp_array: list of TAI93 timestamps
    :return: UNIX timestamps
    """

    dates = []

    for x in tai93_timestamp_array:
        dates.append(get_correct_time(x))

    return dates


def read_netcdf_file(f: str) -> dict:
    """
    Read NetCDF file

    :param f: path to NetCDF file
    :return: dictionary object with variables necessary to plot points on the map
    """

    datafile = Dataset(f)
    np_variables = {"flash_start_time": [], "flash_observe_time": [],"flash_latitude": [],"flash_longitude": []}

    try:

        np_variables["flash_start_time"] = np.array(convert_timestamp(datafile.variables["lightning_flash_TAI93_time"][:]))
        np_variables["flash_observe_time"] = np.array(datafile.variables["lightning_flash_observe_time"][:])
        np_variables["flash_latitude"] = np.array(datafile.variables["lightning_flash_lat"][:])
        np_variables["flash_longitude"] = np.array(datafile.variables["lightning_flash_lon"][:])

    except KeyError:
        print("Warning: At least one of the required variable doesn't exists in " + f)

    return np_variables


def generate_lightning_csv(data_folder: str, csv_file: str) -> int:
    """
    Create CSV file with lightning data points

    :param data_folder: folder containing ISS LIS NQC NetCDF files
    :param csv_file: temporary file location to put generated CSV file
    :return: count of data points written to the CSV file
    """

    files = glob.glob(data_folder + "*.nc")
    data_points_counts = 0

    with open(csv_file, "w") as my_file:

        writer = csv.writer(my_file)
        writer.writerows(
            zip(["flash_latitude"], ["flash_longitude"], ["flash_start_time"], ["flash_observe_time"]))  # write headers

        for f in files:
            np_variables = read_netcdf_file(f)
            writer.writerows(
                zip(np_variables["flash_latitude"], np_variables["flash_longitude"],np_variables["flash_start_time"], np_variables["flash_observe_time"])) # write data rows
            data_points_counts += len(np_variables["flash_latitude"])

    return data_points_counts
