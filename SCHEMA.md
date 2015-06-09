###################
# Metadata Schema #
###################

Last updated: June 4, 2015.

########################################
## Required Parameters for Web Client ##

```
{
    "columns": [String],        // Array of well-known column identifiers, in order
                                // e.g. "x", "y", "value", "error"

    "gridres": {
        "units": String,        // Grid cell units 
        "x": Number,            // Grid cell resolution in the x direction
        "y": Number             // Grid cell resolution in the y direction
    },
        
    "header": [String],         // Array of human-readable column headers, in order

    "parameters": [String],     // Array of well-known variable names e.g.
                                // "values", "value", "errors" or "error"

    "span": String,             // The length of time, as a Pandas "freq" code, 
                                // that an observation spans

    "step": Number,             // The length of time, in seconds, between each
                                // observation to be imported

    "timestamp": String,        // An ISO 8601 timestamp for the first observation

    "title": String,            // Human-readable "pretty" name for the data set 
    
    "units": Object,            // The measurement units, per parameter

    "var_name": String          // The name of the variable in the hierarchical
                                // file which stores the data
}
```

########################################
## Optional Parameters for Python API ##

All of these parameters can be configured on the fly; none are required provided
the data model (TransformationInterface) is compatible.

```
{
    "columns": [String],        // Array of well-known column identifiers, in order
                                // e.g. "x", "y", "value", "error"

    "formats": Object,          // An associative array (mapping) of parameter
                                //  names to the string formatting (or
                                //  decimal-precision formatting) for the
                                //  corresponding parameter's value

    "geometry": {               // Implies data are not on a structured grid

        // Also specifies whether each document is a FeatureCollection and stored
        //  as one document (for collections i.e. "Multi-" types and FeatureCollection
        //  type; otherwise, each row is stored as a separate document
        //  (a separate simple feature)
        "type": ("Point"|"LineString"|"Polygon"|"MultiPoint"|"MultiLineString"|"MultiPolygon"|"FeatureCollection")

    },

    "gridded": Boolean,         // Indicates the data are on a grid

    "grid": {                   // Grid resolution, if data are gridded

        "units": ("degrees"|"meters"),

        "x": Number,            // Grid resolution in the x-direction

        "y": Number             // Grid resolution in the y-direction

    },

    "header": [String],         // Array of human-readable column headers, in order

    "parameters": [String],     // Array of well-known variable names e.g.
                                // "values", "value", "errors" or "error"

    "precision": Number,        // Used with univariate (single-valued) input
                                //  i.e. only one variable in input data;
                                //  the decimal precision to apply to the "values"
                                //  and "errors" parameters, if not specified
                                //  elsewhere

    "regex": {                  // A regular expression that can be used to parse
                                //  the filename (given by "path") which often
        "regex": String,        //  has information about the data

        "map": Object           // The "map" Object maps config parameter names
                                //  (e.g. "timestamp") to additional format strings
                                //  (e.g. date format strings) depending on the
                                //  parameter
    },

    "spans": Array,             // The length of time, in seconds, 
                                // that an observation spans

    "steps": Array,             // The length of time, in seconds, between each
                                // observation to be imported

    "timestamp": String,        // An ISO 8601 timestamp for the first observation

    "title": String,                    // Human-readable "pretty" name for the data set 
    
    "units": Object,            // The measurement units, per parameter

    "var_name": String          // The name of the variable in the hierarchical
                                // file which stores the data

}
```