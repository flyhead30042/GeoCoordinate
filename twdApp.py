from typing import Dict, Hashable, Any

import pandas as pd
import logging
import yaml
from tabulate import tabulate


from twd_converter import Twd

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
                    )
logger = logging.getLogger(__name__)

file = "./config.yaml"

with open(file, "r", encoding="UTF-8") as f:
    config: Dict[Hashable, Any] = yaml.load(f)

DEBUG= config["twd"]["debug"]
data = config["twd"]["data"]
crs = Twd.CRS_LIST[ config["twd"]["crs"] ]
prefix_x = config["twd"]["prefix_x"]
prefix_y = config["twd"]["prefix_y"]
post_x = config["twd"]["post_x"]
post_y = config["twd"]["post_y"]



if __name__ == "__main__":

    '''
        A static Series contains the prefix and postfix for each points
        Note 4 values must exist, assign "" if not needed
    '''
    normalization = pd.Series({"prefix_x":prefix_x, "prefix_y":prefix_y, "post_x":post_x, "post_y":post_y})
    # normalization = pd.Series({"prefix_x":"3", "prefix_y":"27", "post_x":"0", "post_y":"0"})
    # normalization = pd.Series({"prefix_x":"2", "prefix_y":"27", "post_x":"0", "post_y":"0"})
    if DEBUG:
        logger.setLevel(logging.DEBUG)

    a_twd = Twd(crs, data, normalization)
    a_twd.clean_data()
    a_twd.normalize()
    # gpx = a_twd.to_gpxfile("data/aaa.gpx")
    a_twd.to_gpx()
    print(tabulate(a_twd.df, headers="keys", tablefmt='pretty', showindex=False))


