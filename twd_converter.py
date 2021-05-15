from typing import Dict, Hashable, Any, List

import pyproj
from pyproj import Proj
import gpxpy
import gpxpy.gpx
from gpxpy.gpx import GPXWaypoint
import os.path
import pandas as pd
import numpy as np
from datetime import datetime
import logging



logger = logging.getLogger(__name__)

'''
    crs: coordination system including twd67, twd97, wgs84
    point_file: source point file, CSV format supporting column of x, y, name  
    nomalization: Series used to normalize the points to 13 digits
    normalize(): normalize and valid the points
    clean_data(): strip and aggregate the points  
    to_gpx(): read point file, convert to wgs84 and generate gpx file
'''
class Twd(object):
    # CRS_TWD67 = Proj("+proj=tmerc +lat_0=0 +lon_0=121 +k=0.9999 +x_0=250000 +y_0=0 +ellps=aust_SA +units=m +no_defs")
    CRS_TWD67 = Proj(
        "+proj=tmerc +ellps=GRS67 +towgs84=-752,-358,-179,-.0000011698,.0000018398,.0000009822,.00002329 +lon_0=121 +x_0=250000 +k=0.9999 +to +proj=tmerc +datum=WGS84 +lon_0=121 +x_0=250000 +k=0.9999")
    CRS_TWD97 = Proj(
        "+proj=tmerc +lat_0=0 +lon_0=121 +k=0.9999 +x_0=250000 +y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs")
    CRS_WGS84 = Proj("+proj=longlat +datum=WGS84 +no_defs")
    CRS_GOOGLE900913 = Proj(
        "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs")

    # CRS_LIST = [CRS_TWD67, CRS_TWD97, CRS_WGS84, CRS_GOOGLE900913]
    CRS_LIST = {"CRS_TWD67": CRS_TWD67,
                "CRS_TWD97": CRS_TWD97,
                "CRS_WGS84": CRS_WGS84,
                "CRS_GOOGLE900913": CRS_GOOGLE900913}

    def __init__(self, crs, point_file, normalization):
        self.crs = crs
        self.point_file = point_file   #csv file
        assert self.point_file and os.path.isfile(self.point_file), "Invalid csv"
        self.normalization = normalization

        st = os.stat(self.point_file)
        logger.info("{0:s}, size {1:d}".format(self.point_file, st.st_size))

        self.df = pd.read_csv(self.point_file, names=["x", "y", "ele", "name"], dtype={"x":np.object, "y":np.object, "ele":np.object,"name":np.object}, comment='#')
        self.gpx = None


    def normalize(self):
        # add prefix and postfix to each point which has 6+7 digits
        self.df["x"] = self.df["x"].map(lambda x: self.normalization["prefix_x"] + x + self.normalization["post_x"])
        assert self.df[self.df["x"].str.len() != 6].empty, "invalid point, prefix_x or post_x"

        self.df["y"] = self.df["y"].map(lambda y: self.normalization["prefix_y"] + y + self.normalization["post_y"])
        assert self.df[self.df["y"].str.len() != 7].empty, "invalid point, prefix_y or post_y"

    def _agg_name(self, g):
        g["name"] = ",".join(g["name"])
        return g

    def clean_data(self):
        # remove space
        self.df = self.df.apply(lambda r: r.str.strip())

        # remove duplicates
        self.df.drop_duplicates(inplace=True)

        # aggregate the names with identical x, y and ele
        grouped = self.df.groupby(["x", "y", "ele"])
        df3 = grouped.apply(self._agg_name)
        logger.debug(df3.duplicated())
        self.df = df3.drop_duplicates()

        # logger.info(self.df)
        # print(tabulate(self.df, headers = "keys", tablefmt='pretty', showindex=False))


    def to_gpx(self):
        #Transfer coordination from x,y/TWD to ll/WGS84

        x3list:List =[]
        y3list: List = []
        gpx = gpxpy.gpx.GPX()
        for index, r in self.df.iterrows():
            if len(r) != 0:
                '''
                In fact, the ll supported by all GPS tool (ex. Map Generation Tool) is based wgs84 rather than twd67/97
                Can't correctly show coordination on GPS　if only the format is changed
                '''
                x3, y3 = pyproj.transform(self.crs, Twd.CRS_WGS84, r['x'], r['y'])
                logger.info("{:5.8f},{:5.8f}, name={}".format(y3, x3, r['name']))

                x3list.append(x3)
                y3list.append(y3)
                wp = GPXWaypoint(longitude=x3, latitude=y3, name=r['name'], elevation=r["ele"], time=np.datetime64("now").astype(object),symbol="Waypoint")
                gpx.waypoints.append(wp)

        self.gpx = gpx
        logger.debug(gpx.to_xml())

        self.df.insert(1, "lon",x3, True)
        self.df.insert(3, "lat", y3, True)
        # print(tabulate(self.df, headers = "keys", tablefmt='pretty', showindex=False))

        # #writ to gpx file
        # gpx_file = os.path.splitext(self.point_file)[0] +"_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".gpx"  # rename the source file with .gpx extension
        # # name = os.path.splitext(self.point_file)[0] +"_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".gpx"  # rename the source file with .gpx extension
        # # path = os.path.abspath(self.point_file)
        # # gpx_file = os.path.join(path, name)
        #
        # logger.info("writing xml to {}".format(gpx_file))
        # with open(gpx_file, "w+", encoding='utf8') as f:
        #     f.write(gpx.to_xml(version="1.1"))
        # logger.info("Gpx generation done")

    def to_gpxfile(self, gpx_file:str=None):

        self.to_gpx()

        if gpx_file is None:
            gpx_file = os.path.splitext(self.point_file)[0] +"_" + datetime.now().strftime("%Y%m%d%H%M%S") + ".gpx"  # rename the source file with .gpx extension

        logger.info("writing xml to {}".format(gpx_file))
        with open(gpx_file, "w+", encoding='utf8') as f:
            f.write(self.gpx.to_xml(version="1.1"))
        logger.info("Gpx generation done")

# def main_to_gpx(input, crs, normalization, debug):
#     if debug:
#         logger.setLevel(logging.DEBUG)
#
#     a_twd = Twd(crs, input, normalization)
#     a_twd.clean_data()
#     a_twd.normalize()
#     a_twd.to_gpx()
#
#
#
# if __name__ == "__main__":
#     input= "D:/workspace/citest\PythonPractice\data/data/little15_team6.csv"
#
#     '''
#         A static Series contains the prefix and postfix for each points
#         Note 4 values must exist, assign "" if not needed
#     '''
#     normalization = pd.Series({"prefix_x":"3", "prefix_y":"27", "post_x":"0", "post_y":"0"})
#     # normalization = pd.Series({"prefix_x":"2", "prefix_y":"27", "post_x":"0", "post_y":"0"})
#     main_to_gpx(input,Twd.CRS_TWD97, normalization, debug=False)
#
