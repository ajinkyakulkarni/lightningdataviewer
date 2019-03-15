import unittest
import read_data
import os
import fnmatch
import tempfile
import helper
import application as app_file
import numpy


class BasicTests(unittest.TestCase):

    def setUp(self):
        self.cesium_key = app_file.app.config['CESIUM_KEY']
        self.data_dir = app_file.app.config['DATA_DIR']
        self.data_path = os.path.join(app_file.app.root_path, self.data_dir)
        self.date = app_file.app.config['DATE']
        self.file_count = len(fnmatch.filter(os.listdir(self.data_path), '*.nc'))
        self.sample_file = self.data_path + "/ISS_LIS_SC_P0.2_20190304_NQC_12315.nc"

    def tearDown(self):
        pass

    def test_tai93_timestamp_conversion(self):
        self.assertEqual(read_data.get_correct_time(825845071.2741437), '2018-03-04 09:24:30.274144')

    def test_data_dir_exists(self):
        self.assertEquals(os.path.isdir(self.data_path), True)

    def test_data_dir_data_exists(self):
        self.assertEquals(self.file_count > 0, True)

    def test_convert_timestamp(self):
        self.assertEqual(read_data.convert_timestamp([825845071.2741437, 825845125.0890851]),
                         ['2018-03-04 09:24:30.274144', '2018-03-04 09:25:24.089085'])

    def test_sample_file_exists(self):
        self.assertEquals(os.path.isfile(self.sample_file), True)

    def test_read_netcdf_file(self):
        np_variables = read_data.read_netcdf_file(self.sample_file)
        self.assertEquals(np_variables["flash_start_time"][0], "2018-03-04 09:24:30.274144")
        self.assertEquals(np_variables["flash_observe_time"][0], 93)
        self.assertEquals(np_variables["flash_latitude"][0], numpy.float32(2.8195734))
        self.assertEquals(np_variables["flash_longitude"][0], numpy.float32(34.484116))

    def test_generate_lightning_csv(self):
        _, csv_file = tempfile.mkstemp()
        try:
            data_path = os.path.join(app_file.app.root_path, self.data_path)
            data_points_counts = read_data.generate_lightning_csv(data_path, csv_file)
            with open(csv_file, "r") as my_file:
                row_count = sum(1 for row in my_file)

            with app_file.app.app_context():
                response_json = helper.csv_to_json(csv_file)

        finally:
            os.remove(csv_file)

        self.assertEquals(data_points_counts+1, row_count) # + 1 accounts for the CSV header row
        self.assertEquals(data_points_counts, len(response_json.json))



if __name__ == "__main__":
    unittest.main()
