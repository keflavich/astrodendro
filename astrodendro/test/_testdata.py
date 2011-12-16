"""
Realistic data for unit tests and benchmarks
This module provides a 107x107x602 pixel data cube where all the flux values
greater than 1.4 represent real data from L1448 13co, but all other (lesser)
values are randomly generated.
"""

import numpy as np
import os.path
import gzip
import cPickle

# First, load the data cube from the file:
_datafile_path = os.path.join(os.path.dirname(__file__), 'sample-data-hl.pkl.gz')
_datafile = gzip.open(_datafile_path, 'rb')
 
# data file contains pickled flux_values and coords from L1448 13co,
# a data cube which originally had a shape of (107, 107, 602) 
# but filtered to only include data points above value of 1.4

_flux_values = cPickle.load(_datafile)
_coords = cPickle.load(_datafile)
_datafile.close()
 
# Create a new data cube filled with random values no greater than 1.4
# (these will later be filtered out, but that filtering should be part of
# the benchmark)
 
data = np.random.normal(0,0.25, (107,107,602))

for i in range(_flux_values.size):
    data[tuple(_coords[i])] = _flux_values[i]