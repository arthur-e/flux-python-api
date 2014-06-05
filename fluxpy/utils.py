import os
import sys
import re
import pandas as pd
import numpy as np
from pymongo.errors import DuplicateKeyError

class Suite(object):
    def __init__(self):
        pass    

    def get_listing(self, path=None, regex=None):
        '''Gets a sequence of matching file paths'''
        path = path or self.path
        regex = regex or self.file_matcher
        paths = []
        for filename in os.listdir(path):
            if regex.match(filename) is not None:
                paths.append(os.path.join(path, filename))

        return tuple(paths)

    def define_common_grid(self, model=None):
        '''Defines a common XY grid for multiple DataFrames'''

        # It is likely that a new model needs to be provided (probably a
        #   superclass of the correct data model; otherwise, an extract()
        #   method that relies on a common grid will create a circular reference
        model = model or self.model
        instances = map(model, self.get_listing())

        # Get the first data frame as a target
        dfm = instances[0].extract()
        dfm_xy = dfm.ix[dfm.index, ['x', 'y']]

        # Recursively merge each succeeding DataFrame with the target
        for instance in instances[1:]:
            try:
                df = instance.extract()

            except AssertionError:
                continue

            df_xy = df.ix[df.index, ['x', 'y']]
            dfm_xy = pd.merge(dfm_xy, df_xy, on=['x', 'y'], how='outer')

        # Create a MultiIndex on the two columns
        dfm_xy = dfm_xy.set_index(['x', 'y'])

        return dfm_xy


