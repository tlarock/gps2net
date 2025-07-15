import sys
import pandas as pd

if __name__ == "__main__":
    input_filename = sys.argv[1]
    df_traj = pd.read_csv(input_filename, sep=";")
    df_traj["path_as_linestring"][df_traj["path_as_linestring"].notna()].to_csv(f"{input_filename[0:len(input_filename)-4]}_notna.csv", header=False, index=False)
