import multiprocessing as mp
from functools import partial
from tqdm import tqdm

from gps2net import *

def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--shapefile",
                        help="Path to shapefile of road network.",
                        type=str,
                        default="Data/taxi_san_francisco/San Francisco Basemap Street Centerlines/geo_export_e5dd0539-2344-4e87-b198-d50274be8e1d.shp"
                        )
    parser.add_argument("--input-dir",
                        help="Path to location of input file(s).",
                        type=str,
                        default="Data/testData/"
                        )
    parser.add_argument("--input-filename",
                        help="Name of input file located in input-dir. If \
                        --filename-is-glob is also given, input-filename is \
                        assumed to be a regex pattern passed to Path.glob.",
                        type=str,
                        default="testTaxi.txt"
                        )
    parser.add_argument("--filename-is-glob",
                        help="If given, input-filename is assumed to be a regex \
                        pattern that will be passed into Path.glob.",
                        action="store_true"
                        )
    parser.add_argument("--output-dir",
                        help="Base output directory. Default is ./output/",
                        type=str,
                        default="output_files"
                        )
    parser.add_argument("--nprocs",
                        help="Number of processors for the multiprocessing \
                        Pool. Default is 1.",
                        type=int,
                        default=1)
    parser.add_argument("--generate-plots",
                        help="If given, generate histograms of velocities, \
                                time differences, and path lengths divided by \
                                air line lengths.",
                        action="store_true")
    parser.add_argument("--verbose",
                        help="If given, print more messages.",
                        action="store_true")
    parser.add_argument("--progress-bar",
                        help="If given, print a progress bar.",
                        action="store_true")

    args = parser.parse_args()

    return args

def process_file(filepath_shp, DG, output_dir, path,
                 run_unmapped=False, generate_plots=False, verbose=False):
    # TODO: FIXME: Only wrapping in try/except to avoid whole process exiting, should not do in general
    try:
        new_filename = path.stem

        dirName = output_dir / new_filename

        # Create target directory & all intermediate directories if don't exists
        dirName.mkdir(parents=True, exist_ok=True)
        new_filename_simple_solution = dirName / 'pathFromUnmappedGpsPositions.txt'

        new_filename_solution = dirName / 'calculatedSolution.txt'
        new_filename_statistics = dirName / 'statistics.txt'
        new_filename_velocities = dirName / 'velocitiesPLOT.png'
        new_filename_path_length_air_line_length = dirName / 'path_length_air_line_length_PLOT.png'

        if run_unmapped:
            # calculate and save the simple solution (path from exact gps positions without considering the underlying street network)
            getPathFromUnmappedGpsPositions(path, new_filename_simple_solution)

        # calculate and save the full solution (most likely paths) based on the underlying street network
        myCalculatedSolution, mySolutionStatistics = calculateMostLikelyPointAndPaths(
        path, filepath_shp, DG, minNumberOfLines=2, criticalVelocity=35.0, criticalPathLength=2.0,
        progress_bar=verbose)

        # Write the results
        write_solution_output(new_filename_solution, myCalculatedSolution)
        velocities_none_counter = generate_velocity_histogram(new_filename_velocities, myCalculatedSolution,
                                    make_plot=generate_plots)

        write_statistics(new_filename_statistics, filepath_shp, path,
                     new_filename_solution, mySolutionStatistics,
                     velocities_none_counter)

        if generate_plots:
            generate_distances_histogram(new_filename_path_length_air_line_length, myCalculatedSolution)
            # get all timestamp differences of a text file
            timeDifferences = getTimeDifferences(path, 3)

            timedifferencesFileName = dirName / 'timedifferencesPLOT.png'

            # plot the timeDifferences in a histogram
            plotAndSaveHistogram(timeDifferences, 0, 300, 25, timedifferencesFileName,
                                 'Histogram of time differences between gps points', 'time difference in seconds')

        # Convert to geometry file
        df_traj = pd.read_csv(new_filename_solution, sep=";")
        linestring_output_file = dirName / 'calculatedSolution_notna.csv'
        df_traj["path_as_linestring"][df_traj["path_as_linestring"].notna()].to_csv(linestring_output_file, header=False, index=False)

        if verbose:
            print('')
            print('The following files were created:')
            print('- ' + new_filename_simple_solution.as_posix())
            print('- ' + new_filename_solution.as_posix())
            print('- ' + linestring_output_file.as_posix())
            print('- ' + new_filename_statistics.as_posix())
            print('- ' + new_filename_velocities.as_posix())
            print('- ' + new_filename_path_length_air_line_length.as_posix())

    except Exception as e:
        import traceback
        print(traceback.format_exc())


if __name__ == '__main__':
    # parse arguments
    args = parse_args()

    # Get the shapefile name
    # TODO: As of now, shapefile is expected to have "oneway" property, but not
    # all shapefiles will have it. So it is being set to "B" for bidirectional.
    # Users should be warned if their file does not have all required data and
    # be able to specify behavior in such cases.
    filepath_shp = pl.Path(args.shapefile)
    if not filepath_shp.exists():
        print(f"No shapefile found at {filepath_shp}. Exiting.")
        sys.exit(1)

    # Create directed graph from shape file
    DG = createGraphFromSHPInput(filepath_shp,
                                 progress_bar=args.progress_bar,
                                 verbose=args.verbose)

    # Get the directory and name of the input GPS coordinate files
    input_dir = pl.Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Directory {input_dir} does not exist or is not a directory. Exiting.")
        sys.exit(1)

    if not args.filename_is_glob:
        input_filename = pl.Path(args.input_filename)
        # The input is a single file, so filepaths is a list containing only
        # the input file
        filepaths = [input_dir / input_filename]
    else:
        # The input is a pattern for glob, so use glob to read all input files
        # in the input directory.
        filepaths = list(input_dir.glob(args.input_filename))

        # Validate glob-based filepaths. Make sure filepaths:
        # 1. Is not an empty list
        if len(filepaths) == 0:
            print(f"No files returned based on glob pattern {input_dir}/{args.input_filename}. Exiting.")
            sys.exit(1)
        # TODO: 2. Contains non-empty files in an apporpriate format

    # Create the output directory
    output_dir = pl.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    number_of_txt_files = len(filepaths)
    print(f"Number of files identified: {number_of_txt_files}.")

    # loop through all the filepaths, either serially or in parallel
    if args.nprocs < 2:
        for path in tqdm(filepaths, disable=not args.progress_bar):
            process_file(filepath_shp, DG, output_dir, path,
                         verbose=args.verbose,
                         generate_plots=args.generate_plots)
    else:
        with mp.Pool(args.nprocs) as pool:
            part = partial(process_file, filepath_shp, DG, output_dir,
                           verbose=args.verbose, generate_plots=args.generate_plots)
            for _ in tqdm(pool.imap_unordered(part, filepaths), total=len(filepaths), disable=not args.progress_bar):
                pass
