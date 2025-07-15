"""
    Call as in:
        python gps2net_convert.py /Users/tl2574/git/PROJ-2025-NetMob/data/netmob-data/extracted_trajectories_by_mode/PRIV_CAR_DRIVER/ extracted_trajectories_by_mode/PRIV_CAR_DRIVER/
"""
import sys
import glob
import pandas as pd
import geopandas as gpd

def convert_file(filename, output_filename):
    df = gpd.read_file(filename)
    df["occupancy"] = 0
    df["epoch"] = [pd.Timestamp(dt).timestamp() for dt in df["UTC DATETIME"]]
    df["epoch"] = df["epoch"].astype('int')
    df = df[['LATITUDE', 'LONGITUDE', "occupancy", "epoch"]]
    df.sort_values("epoch", inplace=True, ascending=False)
    df.to_csv(output_filename, sep=" ", header=False, index=False)

if __name__ == "__main__":
    # Read filenames
    input_base = sys.argv[1]
    input_files = glob.glob(f"{input_base}/*.csv")

    output_filepath = sys.argv[2]

    # For each file
    for input_filepath in input_files:
        input_filename = input_filepath.split("/")[-1]
        output_filename = output_filepath + f"{input_filename[0:len(input_filename)-3]}txt"
        # Convert to gps2net format
        convert_file(input_filepath, output_filename)

