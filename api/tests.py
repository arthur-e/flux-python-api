from api import core

def test_casa_gfed_stats():
    assert core.casa_gfed_stats() == {
        "std": 1.4207932683672087, 
        "min": -58.2154307932539, 
        "max": 11.880844558999808,
        "median": 0.3698203314372373,
        "mean_values_2std": [-2.848721543997022, 2.8344515294718127],
        "median_values_2std": [-2.47176620529718, 3.2114068681716548],
        "timestamp_start": "2003-12-22T03:00:00",
        "mean_values_1std": [-1.427928275629813, 1.4136582611046042],
        "median_values_1std": [-1.0509729369299714, 1.790613599804446],
        "timestamp_end": "2005-01-01T00:00:00",
        "mean": -0.007135007262604506
    }
