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
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)

    # loop through all all points (nodes) of the linestring
    for i, p in enumerate(coords):
        # i is the index
        # p is the point on the line
        # pd is the distance of point p on the line
        pd = line.project(Point(p))
        # pd==distance means that point where the line should be cut is already a point on the line at index i (= so this means that there is a linesegment in the line which has the point as a starting or end point)
        if (pd == distance):
            # return two lines (whithout cutting any line segment)
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        # pd>distance means that a line segment of the line has to be cut
        # If the line is a circle (start of the line equals the end of the line) and the line has to be cut in the last line segment 'pd>distance' is not enough as pd=0.0 for the end point.
        if (pd > distance or (i != 0 and pd == 0.0 and coords[0] == coords[len(coords)-1])):
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

            # Update Progress Bar
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
