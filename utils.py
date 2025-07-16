import os
import sys
import math
import fiona

import networkx as nx

from shapely import Point, LineString

from plotting_functions import *

def blockPrint():
    '''This method is used to disable print() messages.
    '''
    sys.stdout = open(os.devnull, 'w')


def enablePrint():
    '''This method restores print() messages.
    '''
    sys.stdout = sys.__stdout__


# Print iterations progress
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd='\r'):
    r'''Call in a loop to create terminal progress bar.

    Parameters
    ----------
    iteration : int
        current iteration
    total : Int
        total iterations
    prefix : str, optional
        prefix str, by default ''
    suffix : str, optional
        suffix str, by default ''
    decimals : int, optional
        positive number of decimals in percent complete, by default 1
    length : int, optional
        character length of bar, by default 100
    fill : str, optional
        bar fill character, by default '█'
    printEnd : str, optional
        end character (e.g. '\\r', '\\r\\n'), by default '\\r'

    '''

    percent = ('{0:.' + str(decimals) + 'f}').format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)

    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end=printEnd)
    # Print New Line on Complete
    if iteration >= total:
        print()


def distFrom(lng1, lat1, lng2, lat2):
    '''Returns the distance between two points in meters.

    Parameters
    ----------
    lng1 : float
        This float is the longitude of the source.
    lat1 : float
        This float is the latitude of the source.
    lng2 : float
        This float is the longitude of the target.
    lat2 : float
        This float is the latitude of the target.


    Notes
    -----
    This function calculates the distance between two gps points.
    The result is not 100% correct as the function does not consider the elipsis-like shape of the earth. Instead it just uses an earth radius of 6371000 meters for the calculation.

    A more accurate calculation of the distance can be done in QGIS. For more details, please visit: http://www.qgistutorials.com/en/docs/calculating_line_lengths.html
    However, this function was used to be able to run the code independently of QGIS.

    Examples
    --------

    >>> myDist = distFrom(-122.115, 37.115, -122.111, 37.111)
    >>> myDist
    568.8872918546489
    >>> distFrom(-122.115, 37.115, -122.111, 37.111)
    568.8872918546489


    Returns
    --------
    dist : int
        The distance between two points in meters.

    '''

    earthRadius = 6371000  # meters
    dLat = math.radians(lat2-lat1)
    dLng = math.radians(lng2-lng1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * \
        math.sin(dLng/2) * math.sin(dLng/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist = earthRadius * c

    return dist

def get_tmp_edges(line, point):
    """Accepts a line and a point that falls on/near that line, then computes
    start and end edges for the point.
    TODO: Update docstring
    """
    # Convert to Shapely objects
    ls = LineString(line)
    pt = Point(point)

    # Get the distance between the point and the closest point on line
    dist = ls.project(pt)

    # First, we cut the line in 2, where the first segment goes from the
    # beginning of target_ls to d_target, then the second goes from
    # d_target to target_pt
    cut_line = cut(ls, dist, pt)
    # Now for each of our (presumably 2) line segments, we get a list of
    # the coordinates of the points on the segment
    cut_line_lst = [list(x.coords) for x in cut_line]
    # We then look at the first segment. The final point in this segment is
    # target_pt, so the one before that is the closest point that is part
    # of the actual linestring (I think??)
    len_line_segment = len(cut_line_lst[0])
    edge_start = cut_line_lst[0][len_line_segment-2]
    # Finally, the second point in the second line segment is the other end
    # of an edge
    edge_end = cut_line_lst[1][1]

    return edge_start, edge_end

def cut(line, distance, point):
    '''Cuts a line in two at a distance from its starting point.

    Parameters
    ----------
    line : Shapely 'LineString' object
        [description]
    distance : float
        [description]
    point : Shapely Point object
        [description]

    Notes
    -----
    'line.interpolate(distance)' should be equal to the parameter 'point'. However, due to precision errors 'point' is used.

    Returns
    -------
    list with LineStrings
        Two LineStrings are returned. 'point' is the end point of the first LineString and the start point of the second LineString.
    '''
    # check if point lies on line. If not, return uncut line.
    # TODO: Should we not tell the user this is happening? What does it mean
    # for the code that uses this function when we return just one line instead of 2?
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)

    # loop through all all points (nodes) of the linestring
    for i, p in enumerate(coords):
        # i is the index
        # p is the point on the line
        # pdist is the distance of point p on the line
        pdist = line.project(Point(p))
        # pdist==distance means that point where the line should be cut is already a point on the line at index i (= so this means that there is a linesegment in the line which has the point as a starting or end point)
        if (pdist == distance):
            # return two lines (whithout cutting any line segment)
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        # pdist>distance means that a line segment of the line has to be cut
        # If the line is a circle (start of the line equals the end of the line) and the line has to be cut in the last line segment 'pdist>distance' is not enough as pdist=0.0 for the end point.
        if (pdist > distance or (i != 0 and pdist == 0.0 and coords[0] == coords[len(coords)-1])):
            # return the cut line
            return [
                LineString(coords[:i] + [(point.x, point.y)]),
                LineString([(point.x, point.y)] + coords[i:])]


def createGraphFromSHPInput(filepath_shp):
    '''Creates a directed graph from a shp file.

    Parameters
    ----------
    filepath_shp : str
        The path where the shp file (which contains the street data) is stored.


    Notes
    -----
    This graph is only initialized once in the beginning of the script. The DiGraph contains all linesegment of the shp file (i.e. streetsegments) as directed edges. The start and end node of each edge are tuples containing the coordinates of the position. The weight of an edge is the air_line_distance from the start to the end of the linesegment. Each edge containes the following attributes:

    - id : int
        The id of the street (LineString) which the linesegment belongs to according to the shapefile.
    - oneway : {'B', 'F', 'T'}
        The 'oneway'-property of the street (LineString) which the linesegment belongs to according to the shapefile. The 'oneway'-property indicates if a street is bi-directional (B), or one way heading from the from-node to the to-node (F), or one way heading from the to-node to the from-node (T).

    Depending on the 'oneway'-property of the street either one or two edges are added to the graph. For 'B', two directed edges (from-node --> to-node AND to-node --> from-node) are added. For 'F' or 'T', only one directed edge is added to the graph.

    Returns
    -------
    Directed Graph
        The Directed Graph which contains all linesegments of the shapefiles as edges is returned.
    '''

    GraphFromSHP = nx.DiGraph()

    counter = 0

    # calculate how many street segments the shp file contains
    nr_elements_in_SHP_file = 0
    with fiona.open(filepath_shp) as street_lines:
        nr_elements_in_SHP_file = sum(1 for street_segment in street_lines)

    # Initial call to print 0% progress ProgressBar
    suffix = '| SHP file street segments: {}/{}'.format(
        counter+1, nr_elements_in_SHP_file)
    printProgressBar(0, nr_elements_in_SHP_file,
                     prefix='The Graph is being created:', suffix=suffix, length=50)

    with fiona.open(filepath_shp) as street_lines:

        # loop through all streets
        for street_segment in list(street_lines):

            previous_segment = (0, 0)
            # get the attributes from the street
            id = street_segment['id']
            # TODO FIXME Assume oneway is bidirectional for every edge
            #oneway = street_segment['properties']['oneway']
            oneway = 'B'

            # loop through all segments of a street
            for segment in street_segment['geometry']['coordinates']:

                if (previous_segment != (0, 0)):

                    # calculate the length of a street segment
                    calculated_length = distFrom(
                        segment[0], segment[1], previous_segment[0], previous_segment[1])

                    # add streetsegments as edges (depending on the oneway property)
                    if(oneway == 'B'):
                        # create two directed edges for both directions
                        GraphFromSHP.add_edge(
                            segment, previous_segment, weight=calculated_length, id=id, oneway=oneway)
                        GraphFromSHP.add_edge(
                            previous_segment, segment, weight=calculated_length, id=id, oneway=oneway)
                    elif(oneway == 'F'):
                        # create a directed edge from the from-node to the to-node
                        GraphFromSHP.add_edge(
                            previous_segment, segment, weight=calculated_length, id=id, oneway=oneway)
                    elif(oneway == 'T'):
                        # create a directed edge from the to-node to the from-node
                        GraphFromSHP.add_edge(
                            segment, previous_segment, weight=calculated_length, id=id, oneway=oneway)

                previous_segment = segment

            # Increment Progress Bar
            suffix = '| SHP file street segments: {}/{}'.format(
                counter+1, nr_elements_in_SHP_file)
            printProgressBar(counter + 1, nr_elements_in_SHP_file,
                             prefix='The Graph is being created:', suffix=suffix, length=50)

            counter += 1

    print('The graph was created and contains {} edges.'.format(
        GraphFromSHP.number_of_edges()))

    return GraphFromSHP


def air_line_distance(source, target):
    '''Heuristic function for A star algorithm: returns the air line distance from the source to the target.

    Parameters
    ----------
    source : tuple (float, float)
        This is the source point. It is a tuple of the form (lng1, lat1) where lng1 is the longitude of the source and lat1 is the latitude of the source.
    target : tuple (float, float)
        This is the source point. It is a tuple of the form (lng2, lat2) where lng2 is the longitude of the target and lat2 is the latitude of the target.

    Notes
    -----
    This function is only called in the following function: :func:`~gps2net.getShortestPathAStar`

    This function is used as the heuristic function for the A Star algorithm.
    It calculates the air line distance between two gps points.
    The result is not 100% correct as the function does not consider the elipsis-like shape of the earth. Instead it just uses an earth radius of 6371000 meters for the calculation.

    Examples
    --------

    >>> myAirLineDist = air_line_distance((-122.115, 37.115), (-122.111, 37.111))
    >>> myAirLineDist
    568.8872918546489


    Returns
    -------
    int
        The air line distance between two points (source and target) in meters.
    '''
    distance = distFrom(source[0], source[1], target[0], target[1])
    return distance


def getTimeDifferences(filepath, timestampPosition):
    """Get the time differences of taxi mobility traces in a txt file.

    Parameters
    ----------
    filepath : str
        The path where the txt file (which contains the taxi mobility trace) is stored.
    timestampPosition : int
        The position on which the timestamp is (assuming that each line contains one measured GPS position and that values in each line are seperated by a space).

    Notes
    -----
    This method assumes that each line contains one measured GPS position and that values in each line are seperated by a space. Further, it assumes that time is in UNIX epoch format.
    Examples
    --------
    >>> myPath = 'Data/testData/testTaxi.txt'
    >>> myTimeDifferences = getTimeDifferences(myPath, 3)
    >>> myTimeDifferences
    [28, 119]

    Returns
    -------
    list
        Time differences in seconds.
    """

    # initialise empty list
    timeDifferences = []
    # set previousTimestamp to 0
    previousTimestamp = 0

    # open the file
    with open(filepath, 'r') as f:
        mylist = f.read().splitlines()

        # loop through the txt file
        for lines in mylist:
            values = lines.split(' ')
            # get the timestamp of the current line
            timestamp = int(values[timestampPosition])

            # if it't not the forst entry of the txt file, append the difference to the set
            if(previousTimestamp != 0):
                timeDifferences.append(previousTimestamp-timestamp)

            previousTimestamp = timestamp

    return timeDifferences

def getPathFromUnmappedGpsPositions(filepath, new_filename):
    """Creates a new file which includes path, path length, path time, and velocity without considering the underlying street network.

    TODO: NOTE: This doesn't fully belong in utils, but is clutter in the main
    file, so putting it here until an obviously better place comes up

    Parameters
    ----------
    filepath : str
        The path where the txt file (which contains the taxi mobility trace) is stored.
    new_filename : str
        The filename of the new solution.

    Notes
    -----
    This function created a txt file which (in addition to the input values) contains additional parameters which are NOT based on the underlying street network, such as:

    - path : Linestring
        Linear path with start=current_position and end=next_position.
    - path length : float
        Distance between current and next position in meters.
    - path time : float
        Time between measurement at current and next position in seconds.
    - velocity : float
        Velocity in meters/second.
    """

    header = [
        "latitude(y);longitude(x);hasPassenger;time;path;path_length;path_time;velocity_m_s\n"]

    path = ''
    path_length = ''
    path_time = ''
    velocity_m_s = ''
    time_previous = None

    with open(filepath, "r") as f:
        mylist = f.read().splitlines()

        # this saves a new text file which includes the calculated parameters
        with open(new_filename, 'w') as new_file:

            # write the header to the new txt file
            new_file.writelines(header)

            for line in mylist:

                # read the values from the txt file and transform the strings to float/int

                values = line.split(" ")
                x = float(values[1])
                y = float(values[0])
                time_current = int(values[3])
                lines_withoutspaces = str(line).replace(" ", ";")

                # no values are added to the first line of the file
                if (time_previous != None):

                    # check if data is sorted by time
                    # we start with newest data point, so if previous data time was earlier in time, it is not sorted
                    if (time_previous < time_current):
                        print('')
                        print('Algorithm cannot run since DATA IS NOT SORTED!')
                        print('Time of current position ({}) is before time of previous position ({}).'.format(
                            time_previous, time_current))
                        print(
                            'Please adjust your input file. The newest gps signal should be the first line.')
                        print('')
                        sys.exit('Execution of the algorithm stopped.')

                    else:
                        start_pt = Point(x_previous, y_previous)
                        end_pt = Point(x, y)
                        path = LineString(
                            [(start_pt.x, start_pt.y), (end_pt.x, end_pt.y)])
                        path_length = distFrom(x_previous, y_previous, x, y)
                        path_time = abs(time_previous-time_current)

                        velocity_m_s = path_length/path_time

                # write the initial values to the new file
                new_file.write(lines_withoutspaces)

                # write the new values to the new file
                new_file.write(';')
                new_file.write(str(path))
                new_file.write(';')
                new_file.write(str(path_length))
                new_file.write(';')
                new_file.write(str(path_time))
                new_file.write(';')
                new_file.write(str(velocity_m_s))
                new_file.write('\n')

                x_previous = x
                y_previous = y
                time_previous = time_current

def write_solution_output(new_filename_solution, myCalculatedSolution):
    """Writes solution to new_filename_solution
    """
    # set the header of the output txt file which will contain the calculated solution.
    header = ['latitude(y);longitude(x);hasPassenger;time;closest_intersection_x;closest_intersection_y;relative_position;relative_position_normalized;intersected_line_oneway;intersected_line_as_linestring;linestring_adjustment_visualization;path_time;path_as_linestring;path_length;air_line_length;path_length/air_line_length;velocity_m_s;pathIDs;solution_id;solution_index;path_from_target_to_source;taxi_did_not_move;second_best_solution_yields_more_found_paths;NO_PATH_FOUND;outlier;comment\n']
    var_list = ["y", "x", "passenger", "timestamp",
            "closest_intersection_x", "closest_intersection_y",
            "relative_position", "relative_position_normalized",
                        "intersected_line_oneway", "intersected_line",
                        "linestring_adjustment_visualization", "path_time",
                        "path", "path_length", "air_line_length",
                        "path_length/air_line_length", "velocity_m_s",
                        "pathIDs", "solution_id", "solution_index",
                        "path_from_target_to_source", "taxi_did_not_move",
                        "second_best_solution_yields_more_found_paths",
                        "NO_PATH_FOUND", "outlier", "comment"]

    # this saves a new text file which includes the calculated parameters
    with open(new_filename_solution, 'w') as new_file:
        # write the header to the new txt file
        new_file.writelines(header)
        # write the calculated solution to the new txt file
        for location_result in myCalculatedSolution:
            for idx, var in enumerate(var_list):
                new_file.write(str(location_result[var]))
                if idx < len(var_list)-1:
                    new_file.write(";")
                else:
                    new_file.write("\n")

def generate_velocity_histogram(new_filename_velocities, myCalculatedSolution):
    velocities = []
    velocities_none_counter = 0

    # get all velocities of the solution
    for location_result in myCalculatedSolution:
        if (location_result['velocity_m_s'] == ''):
            velocities_none_counter += 1
        else:
            velocities.append(float(location_result['velocity_m_s']))

    # plot the timeDifferences in a histogram
    plotAndSaveHistogram(velocities, 0, 80, 5, new_filename_velocities,
                         'Histogram of velocities between gps points', 'velocity in m/s')

    # TODO: FIXME: This means we have to generate the plot to get this count.
    # Consider whether we actually need to report this number in general, or if
    # it should be up to the user to compute it themselves from the output.
    return velocities_none_counter


def generate_distances_histogram(new_filename_path_length_air_line_length, myCalculatedSolution):
    # initialise empty lists
    path_length_air_line_length = []

    # get all velocities of the solution
    for location_result in myCalculatedSolution:
        if (location_result['path_length/air_line_length'] != ''):
            path_length_air_line_length.append(
                float(location_result['path_length/air_line_length']))

    # plot the the path_length/air_line_length in a histogram
    plotAndSaveHistogram(path_length_air_line_length, 1.0, 2.5, 0.1, new_filename_path_length_air_line_length,
                         'Histogram of path lengths divided by air line lengths', 'path length / air line length')

def write_statistics(new_filename_statistics, filepath_shp, filepath,
                     new_filename_solution, mySolutionStatistics,
                     velocities_none_counter):
    """Write statistics to file.
    TODO: NOTE: This is an unstructured file that is somewhat useful for
    humans, but would be better if it was structured into a CSV or similar to
    be easily read into code.
    """
    # SAVE STATISTICS IN NEW FILE
    with open(new_filename_statistics, 'w') as new_file:
        # write statistics to the file
        new_file.write('path of shp file: ')
        new_file.write(str(filepath_shp))
        new_file.write('\n')
        new_file.write('path of old file: ')
        new_file.write(str(filepath))
        new_file.write('\n')
        new_file.write('path of new file: ')
        new_file.write(str(new_filename_solution))
        new_file.write('\n')

        # calculate the number of lines in the txt file
        with open(filepath, 'r') as f:
            num_lines = sum(1 for line in f)
        new_file.write('number of lines in txt file: ')
        new_file.write(str(num_lines))

        new_file.write('\n')
        new_file.write('\n')

        # write the statistics whcih were returned from the algorithm to the file
        for item in mySolutionStatistics.items():
            new_file.write(str(item[0]))
            new_file.write(': ')
            new_file.write(str(item[1]))
            new_file.write('\n')

        new_file.write('\n')
        new_file.write('VELOCITIES PLOT: ')
        new_file.write('\n')
        new_file.write('The Velocity plot contains velocities from {} data points. For the remaining {} data points the velocity could not be calculated (e.g. because it is an outlier).'.format(
            num_lines-velocities_none_counter, velocities_none_counter))
        new_file.write('\n')
        new_file.write('\n')
