import math
import numpy as np
import matplotlib.pyplot as plt

def plotAndSaveHistogram(data, minXLabel, maxXLabel, binSize, filename, title, xlabel):
    """Plots a histogram with a specified max x-value. Values bigger that the max x-value are clipped to the interval edge.

    Parameters
    ----------
    data : list of int or float
        Values which should be plottet in a histogram.
    minXLabel : int or float
        The min x-value of the plot.
    maxXLabel : [type]
        The max x-value of the plot.
    binSize : int
        The size of the plotted bins.
    filename : str
        Path and filename of the plot --> this specifies where and under which name the plot should be saved.
    title : str
        Title of the plot.
    xlabel : str
        X axis label of the plot.

    Notes
    -----
    The plot is saved in PNG format.
    """
    # get the max value of the imputs
    maxInput = max(data)

    # check if datas are floats (as in the case of velocities)
    if isinstance(maxInput, float):
        # round the float to the next higher number and then convert it to int
        maxInput = int(math.ceil(maxInput))

    # create the bins (as a range from 0 to maxXLabel or maxInput depending on which one is smaller). +2 is needed to display also the max number.
    if isinstance(binSize, float):
        # create a range with floats
        myBins = np.arange(minXLabel, min(
            maxXLabel, maxInput)+(min(2*binSize, 2)), binSize)
    else:
        # create a range with ints
        myBins = range(minXLabel, min(maxXLabel, maxInput) +
                       (min(2*binSize, 2)), binSize)

    # initialize the figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)

    # plot the histogram. 'np.clip' makes sure that the time differences which are bigger then the max X value are visualized in the last bin.
    n, bins, patches = ax.hist(x=np.clip(
        data, 0, myBins[-1]), bins=myBins, color='#0504aa', alpha=0.7, rwidth=0.85)

    plt.grid(axis='y', alpha=0.75)
    plt.xlabel(xlabel)
    plt.ylabel('Frequency')
    plt.title(title)

    try:
        maxfreq = n.max()
        # Set a clean upper y-axis limit.
        plt.ylim(ymax=np.ceil(maxfreq / 10) * 10 if maxfreq %
                 10 else maxfreq + 10)

        if isinstance(binSize, float):
            xlabels = bins[0:].astype('|S3')
        else:
            xlabels = bins[0:].astype(str)

        # remove the last x label
        xlabels = xlabels[:-1]
        # add a '+' to the label of the last bin to visualize that this bin contains all timeDifferences  which are equal or bigger than the xTick.
        if not isinstance(binSize, float):
            xlabels[-1] += '+'

        myXTicks = np.array(myBins)
        # set the x ticks for the figure
        plt.xticks(myXTicks, xlabels)

    except ValueError:  # raised if `n` is empty.
        pass

    # save the figure in the folder of the current taxi
    plt.savefig(filename)
    # the figure could be shown with 'plt.show()'. However, this is not necessary as it is saved anyway.
    # close the current figure
    plt.close()


