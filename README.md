##########################
# Installation and Setup #
##########################

Installation of the Python dependencies is simple with `pip`:

    $ python setup.py install

#######################################
## Installing in a Virtual Environment

Installation in a Python virtual environment (with `virtualenv`) is recommended but not required.
To install `virtualenv`:

    $ sudo easy_install pip
    $ sudo pip install virtualenv

The recommended location for your Python virtual environments is:

    /usr/local/pythonenv

But if you choose to put them elsewhere, just modify the variable on the first line of this next part.
**To install the Python API in a virtual environment:**

    $ VENV_DIR=/usr/local/pythonenv
    $ virtualenv $VENV_DIR/flux-python-api-env
    $ source $VENV_DIR/flux-python-api-env/bin/activate
    $ python setup.py install

To put the `fluxpy` on your Python path:

    $ echo "/usr/local/project/flux-python-api/" > /usr/local/pythonenv/flux-python-api-env/lib/python2.7/site-packages/fluxpy.pth

########################
# API Quick References #
########################

###############################
## Loading Data with Mediators

Given the examples of gridded (kriged) carbon concentration data (XCO2) in a Matlab file,
here is the process for loading these data into the MongoDB database.

    from fluxpy.mediators import Grid3DMediator
    from fluxpy.models import XCO2Matrix
    
    # The mediator understands how 3D gridded data should be stored
    mediator = Grid3DMediator()
    
    # Create an instance of the XCO2Matrix data model; parameters are loaded
    #   from a parameter file with the same name (e.g. xco2_data.json) if it
    #   exsists but otherwise are set as optional keyword arguments
    xco2 = KrigedXCO2Matrix('xco2_data.mat', timestamp='2009-06-15')
    
    # Save it to the database using the collection name provided
    mediator.save('test_r2_xco2', xco2)

#############################
## Loading Data with a Suite

Sometimes, a dataset is more complicated than currently defined Models and Mediators are designed to handle.
For complicated use cases or bulk imports, a `Suite` class is available as a demonstration in the `utils` module.
The `Suite` class has helpful methods like `get_listing()` which returns a file listing for files of a certain type in a certain location (useful for iterating over files in bulk).
`Suite` should be extended for your use case (see `workflow.py`), but each `Suite` instance or subclass instance should have a `main()` function that is called to load data into MongoDB.
**The `main()` function is where your special needs are defined.**
For example, if you need to calculate something based on all of the files before loading them in one by one, use `main()` to preempt the call to your Mediator's `save()` method with whatever you need to do e.g.:

    def main(self):
        files_to_be_imported = self.get_listing()

        for each in files_to_be_imported:
            self.do_something(each)

        result = self.get_result()

        for each in files_to_be_imported:
            instance = self.model(each)
            self.mediator.save(collection_name, each, bulk_property=result)


