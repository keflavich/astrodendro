import timeit
import os
import astrodendro
from astrodendro.test._testdata import data

def benchmark_compute():    
    print("Data loaded. Starting dendrogram computations...")

    def test1():
        astrodendro.Dendrogram(data, minimum_npix=4, minimum_flux=1.4, minimum_delta=0.3, verbose=False)
        print("  Completed an iteration of test1.")
    def test2():
        astrodendro.Dendrogram(data, minimum_npix=8, minimum_flux=1.4, verbose=False)
        print("  Completed an iteration of test2.")
       
    num = 3
    
    t1 = timeit.timeit(test1, number=num) / num
    t2 = timeit.timeit(test2, number=num) / num

    print("test1 average over {num} computations: {result:.3} s".format(num=num, result=t1))
    print("test2 average over {num} computations: {result:.3} s".format(num=num, result=t2))
    
    print("Total average compute time: {0:.3}s".format((t1+t2)/2))
    
def benchmark_hdf5():    
    print("\nGenerating complex dendrogram for HDF5 import/export...")
    d = astrodendro.Dendrogram(data, minimum_npix=2, minimum_flux=1.4, minimum_delta=0.01, verbose=False)
    print("Dendrogram generated. Testing import and export...")
    
    filename = '.astrodendro-hdf5-benchmark.hdf5'
    if os.path.exists(filename):
        os.remove(filename)
    num = 2
    
    def testHDF5():
        print('Exporting...')
        d.to_hdf5(filename)
        print('Importing...')
        d2 = astrodendro.Dendrogram()
        d2.from_hdf5(filename)
        os.remove(filename)

    t = timeit.timeit(testHDF5, number=num) / num

    print("Total average export+import time: {0:.3}s".format(t))
    
def benchmark_plot():    
    print("\nGenerating complex dendrogram for plotting test...")
    d = astrodendro.Dendrogram(data, minimum_npix=2, minimum_flux=1.4, minimum_delta=0.01, verbose=False)
    print("Using test dendrogram with {0} leaves to test plotting speed...".format(len(d.get_leaves())))
    
    num = 100
    
    def testP():
        d.make_plot(axes=None)

    tP = timeit.timeit(testP, number=num) / num

    print("Total average plot time: {0:.3}s".format(tP))

if __name__ == '__main__':
    try:
        benchmark_compute()
        benchmark_hdf5()
        benchmark_plot()
    except KeyboardInterrupt:
        print("Cancelled.")