# Computing Astronomical Dendrograms
# Copyright (c) 2011 Thomas P. Robitaille
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

# Notes:
# - An item is a leaf or a branch
# - An ancestor is the largest structure that an item is part of

import numpy as np

from astrodendro.components import Trunk, Branch, Leaf
from astrodendro.newick import parse_newick
try:
    import matplotlib
    import matplotlib.pylab
except ImportError:
    # The plot method won't work without matplotlib, but everything else will be fine
    pass


class Dendrogram(object):

    def __init__(self, *args, **kwargs):

        if len(args) == 1:
            self._compute(*args, **kwargs)


    def _compute(self, data, minimum_flux=-np.inf, minimum_npix=0, minimum_delta=0, verbose=True):

        # Initialize list of ancestors
        ancestor = {}

        # If array is 2D, recast to 3D
        if len(data.shape) == 2:
            self.n_dim = 2
            self.data = data.reshape(1, data.shape[0], data.shape[1])
        elif len(data.shape) == 3:
            self.n_dim = 3
            self.data = data
        else:
            raise Exception("Invalid # of dimensions")

        # Create a list of all points in the cube above minimum_flux
        keep = self.data.ravel() > minimum_flux
        flux_values = self.data.ravel()[keep]
        coords = np.array(np.unravel_index( np.arange(self.data.size)[keep] , self.data.shape)).transpose()
        
        if verbose:
            print "Number of points above minimum: %i" % len(flux_values)
            
        # Define index array indicating what item each cell is part of
        # We expand each dimension by one, so the last value of each
        # index (accessed with e.g. [nx,#,#] or [-1,#,#]) is always zero
        # This permits an optimization below when finding adjacent items
        self.index_map = np.zeros(np.add(self.data.shape, (1,1,1)), dtype=np.int32)

        # Dictionary of currently-defined items:
        items = {}

        # Loop from largest to smallest flux value. Each time, check if the 
        # pixel connects to any existing leaf. Otherwise, create new leaf.
        
        count = 0

        for i in np.argsort(flux_values)[::-1]:
            
            def next_idx():
                return i+1
                # Generate IDs index i. We add one to avoid ID 0
            
            flux = flux_values[i]
            coord = coords[i]
            z,y,x = coord
            
            # Print stats
            if verbose and count % 10000 == 0:
                print "%i..." % count
            count += 1

            # Check if point is adjacent to any leaf
            # We don't worry about the edges, because overflow or underflow in 
            # any one dimension will always land on an extra "padding" cell 
            # with value zero added above when index_map was created
            indices_adjacent = [(z,y,x-1),(z,y,x+1),(z,y-1,x),(z,y+1,x),(z-1,y,x),(z+1,y,x)]
            adjacent = [self.index_map[c] for c in indices_adjacent if self.index_map[c] != 0]
            
            # Replace adjacent elements by its ancestor
            for j in range(len(adjacent)):
                if ancestor[adjacent[j]] is not None:
                    adjacent[j] = ancestor[adjacent[j]]

            # Remove duplicates
            adjacent = list(set(adjacent))

            # Find how many unique adjacent structures there are
            n_adjacent = len(adjacent)

            if n_adjacent == 0:  # Create new leaf

                # Set absolute index of the new element
                idx = next_idx()

                # Create leaf
                leaf = Leaf(x, y, z, flux, idx=idx)

                # Add leaf to overall list
                items[idx] = leaf

                # Set absolute index of pixel in index map
                self.index_map[z, y, x] = idx

                # Create new entry for ancestor
                ancestor[idx] = None

            elif n_adjacent == 1:  # Add to existing leaf or branch

                # Get absolute index of adjacent element
                idx = adjacent[0]

                # Get adjacent item
                item = items[idx]

                # Add point to item
                item.add_point(x, y, z, flux)

                # Set absolute index of pixel in index map
                self.index_map[z, y, x] = idx

            else:  # Merge leaves

                # At this stage, the adjacent items might consist of an arbitrary
                # number of leaves and branches.

                # Find all leaves that are not important enough to be kept
                # separate. These leaves will now be treated the same as the pixel
                # under consideration
                merge = []
                for idx in adjacent:
                    if type(items[idx]) == Leaf:
                        leaf = items[idx]
                        if leaf.npix < minimum_npix or leaf.fmax - flux < minimum_delta:
                            merge.append(idx)

                # Remove merges from list of adjacent items
                for idx in merge:
                    adjacent.remove(idx)

                # Now, how many significant adjacent items are left?

                if len(adjacent) == 0:

                    # There are no separate leaves left (and no branches), so pick the
                    # first one as the reference and merge all the others onto it

                    idx = merge[0]
                    leaf = items[idx]

                    # Add current point to the leaf
                    leaf.add_point(x, y, z, flux)

                    # Set absolute index of pixel in index map
                    self.index_map[z, y, x] = idx

                    for i in merge[1:]:

                        # print "Merging leaf %i onto leaf %i" % (i, idx)

                        # Remove leaf
                        removed = items.pop(i)

                        # Merge old leaf onto reference leaf
                        leaf.merge(removed)

                        # Update index map
                        removed.add_footprint(self.index_map, idx)

                elif len(adjacent) == 1:
                    
                    # There is one significant adjacent leaf/branch left.
                    # Add the point under consideration and all insignificant
                    # leaves in 'merge' to the adjacent leaf/branch

                    idx = adjacent[0]
                    item = items[idx]  # Could be a leaf or a branch

                    # Add current point to the leaf/branch
                    item.add_point(x, y, z, flux)

                    # Set absolute index of pixel in index map
                    self.index_map[z, y, x] = idx

                    for i in merge:

                        # print "Merging leaf %i onto leaf/branch %i" % (i, idx)

                        # Remove leaf
                        removed = items.pop(i)

                        # Merge insignificant leaves onto the leftover leaf/branch
                        item.merge(removed)

                        # Update index map
                        removed.add_footprint(self.index_map, idx)

                else:

                    # Set absolute index of the new element
                    idx = next_idx()

                    # Create branch
                    branch = Branch([items[j] for j in adjacent], \
                                    x, y, z, flux, idx=idx)

                    # Add branch to overall list
                    items[idx] = branch

                    # Set absolute index of pixel in index map
                    self.index_map[z, y, x] = idx

                    # Create new entry for ancestor
                    ancestor[idx] = None

                    for i in merge:

                        # print "Merging leaf %i onto branch %i" % (i, idx)

                        # Remove leaf
                        removed = items.pop(i)

                        # Merge old leaf onto reference leaf
                        branch.merge(removed)

                        # Update index map
                        removed.add_footprint(self.index_map, idx)

                    for j in adjacent:
                        ancestor[j] = idx
                        for a in ancestor:
                            if ancestor[a] == j:
                                ancestor[a] = idx

        if verbose and not count % 10000 == 0:
            print "%i..." % count

        # Remove orphan leaves that aren't large enough
        remove = []
        for idx in items:
            item = items[idx]
            if type(item) == Leaf:
                if item.npix < minimum_npix or item.fmax - item.fmin < minimum_delta:
                    remove.append(idx)
        for idx in remove:
            items.pop(idx)

        # Create trunk from objects with no ancestors
        self.trunk = Trunk()
        for idx in items:
            if ancestor[idx] is None:
                self.trunk.append(items[idx])

        # Make map of leaves vs branches
        self.item_type_map = np.zeros(self.data.shape, dtype=np.uint8)
        for idx in items:
            item = items[idx]
            if type(item) == Leaf:
                item.add_footprint(self.item_type_map, 2)
            else:
                item.add_footprint(self.item_type_map, 1, recursive=False)

        # Re-cast to 2D if original dataset was 2D
        if self.n_dim == 2:
            self.data = self.data[0, :, :]
            self.index_map = self.index_map[0, :, :]
            self.item_type_map = self.item_type_map[0, :, :]

    def get_leaves(self):
        return self.trunk.get_leaves()

    def to_newick(self):
        return self.trunk.to_newick()

    def to_hdf5(self, filename):

        import h5py

        f = h5py.File(filename, 'w')

        f.attrs['n_dim'] = self.n_dim

        f.create_dataset('newick', data=self.to_newick())

        d = f.create_dataset('index_map', data=self.index_map, compression=True)
        d.attrs['CLASS'] = 'IMAGE'
        d.attrs['IMAGE_VERSION'] = '1.2'
        d.attrs['IMAGE_MINMAXRANGE'] = [self.index_map.min(), self.index_map.max()]

        d = f.create_dataset('item_type_map', data=self.item_type_map, compression=True)
        d.attrs['CLASS'] = 'IMAGE'
        d.attrs['IMAGE_VERSION'] = '1.2'
        d.attrs['IMAGE_MINMAXRANGE'] = [self.item_type_map.min(), self.item_type_map.max()]

        d = f.create_dataset('data', data=self.data, compression=True)
        d.attrs['CLASS'] = 'IMAGE'
        d.attrs['IMAGE_VERSION'] = '1.2'
        d.attrs['IMAGE_MINMAXRANGE'] = [self.data.min(), self.data.max()]

        f.close()

    def from_hdf5(self, filename):

        import h5py

        f = h5py.File(filename, 'r')

        self.n_dim = f.attrs['n_dim']

        # If array is 2D, reshape to 3D
        if self.n_dim == 2:
            self.data = f['data'].value.reshape(1, f['data'].shape[0], f['data'].shape[1])
            self.index_map = f['index_map'].value.reshape(1, f['data'].shape[0], f['data'].shape[1])
            self.item_type_map = f['item_type_map'].value.reshape(1, f['data'].shape[0], f['data'].shape[1])
        else:
            self.data = f['data'].value
            self.index_map = f['index_map'].value
            self.item_type_map = f['item_type_map'].value


        # Create arrays with pixel positions
        coords = np.array(np.unravel_index( np.arange(self.data.size), self.data.shape))
        coords = coords.transpose().reshape( self.data.shape + (3,))
        # Now coords has the same shape as data, and each entry is a (z,y,x) coordinate tuple

        tree = parse_newick(f['newick'].value)

        def construct_tree(d):
            items = []
            for idx in d:
                item_coords = coords[self.index_map == idx]
                x = item_coords[:,2]
                y = item_coords[:,1]
                z = item_coords[:,0]
                f = self.data[self.index_map == idx]
                if type(d[idx]) == tuple:
                    sub_items = construct_tree(d[idx][0])
                    b = Branch(sub_items, x[0], y[0], z[0], f[0], idx=idx)
                    for i in range(1, len(x)):
                        b.add_point(x[i], y[i], z[i], f[i])
                    items.append(b)
                else:
                    l = Leaf(x[0], y[0], z[0], f[0], idx=idx)
                    for i in range(1, len(x)):
                        l.add_point(x[i], y[i], z[i], f[i])
                    items.append(l)
            return items

        self.trunk = Trunk()
        for item in construct_tree(tree):
            self.trunk.append(item)

        # Re-cast to 2D if original dataset was 2D
        if self.n_dim == 2:
            self.data = self.data[0, :, :]
            self.index_map = self.index_map[0, :, :]
            self.item_type_map = self.item_type_map[0, :, :]
    
    def plot(self, line_width = 1, spacing = 5):
        axis = matplotlib.pylab.gca()
        plot = self.trunk.plot_dendrogram(line_width, spacing)
        axis.set_xlim([plot.xmin, plot.xmax]) 
        axis.set_ylim([plot.ymin, plot.ymax])
        axis.set_xticks([])
        axis.set_xticklabels([])
        if line_width > 1:
            # Y values will not be correct, so hide them:
            axis.set_yticks([])
            axis.set_yticklabels([])
        line_collection = matplotlib.collections.LineCollection(plot.lines, linewidths = line_width)
        axis.add_collection(line_collection)
        matplotlib.pylab.draw_if_interactive()
