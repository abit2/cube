# -*- coding: utf-8 -*-
# Author: Mateo Inchaurrandieta <mateo.inchaurrandieta@gmail.com>
# pylint: disable=E1101, C0330
"""
Utilities used in the sunpy.cube.cube module. Moved here to prevent clutter and
aid readability.
"""

from __future__ import absolute_import
import numpy as np
from sunpycube import wcs_util
from astropy import units as u
from copy import deepcopy


def orient(array, wcs, *extra_arrs):
    # This is mostly lifted from astropy's spectral cube.
    """
    Given a 3 or 4D cube and a WCS, swap around the axes so that the
    axes are in the correct order: the first in Numpy notation, and the last
    in WCS notation.

    Parameters
    ----------
    array : `~numpy.ndarray`
        The input 3- or 4-d array with two position dimensions and one spectral
        dimension.
    wcs : `~sunpy.wcs.WCS`
        The input 3- or 4-d WCS with two position dimensions and one spectral
        dimension.
   extra_arrs: one or more ndarrays, optional
        Extra arrays to orient, corresponding to uncertainties and errors in
        the data.
    """
    if wcs.oriented:  # If this wcs has already been oriented.
        return (array, wcs) + extra_arrs

    if array.ndim != 3 and array.ndim != 4:
        raise ValueError("Input array must be 3- or 4-dimensional")

    if not ((wcs.wcs.naxis == 3 and array.ndim == 3) or
            (wcs.wcs.naxis == 4 and array.ndim == 4 and not wcs.was_augmented)
            or (wcs.wcs.naxis == 4 and array.ndim == 3 and wcs.was_augmented)):
        raise ValueError("WCS must have the same dimensions as the array")

    axtypes = list(wcs.wcs.ctype)

    if wcs.was_augmented:
        array_order = select_order(axtypes[2::-1])
    else:
        array_order = select_order(axtypes)
    result_array = array.transpose(array_order)
    wcs_order = np.array(select_order(axtypes))

    result_wcs = wcs_util.reindex_wcs(wcs, wcs_order)
    result_wcs.was_augmented = wcs.was_augmented
    result_wcs.oriented = True
    result_extras = [arr.transpose(array_order) for arr in extra_arrs]
    return (result_array, result_wcs) + tuple(result_extras)


def select_order(axtypes):
    """
    Returns the indices of the correct axis priority for the given list of WCS
    CTYPEs. For example, given ['HPLN-TAN', 'TIME', 'WAVE'] it will return
    [1, 2, 0] because index 1 (time) has the highest priority, followed by
    wavelength and finally solar-x. When two or more celestial axes are in the
    list, order is preserved between them (i.e. only TIME, UTC and WAVE are
    moved)

    Parameters
    ----------
    axtypes: str list
        The list of CTYPEs to be modified.
    """
    order = [(0, t) if t in ['TIME', 'UTC'] else
             (1, t) if t == 'WAVE' else
             (2, t) if t == 'HPLT-TAN' else
             (axtypes.index(t) + 3, t) for t in axtypes]
    order.sort()
    result = [axtypes.index(s) for (_, s) in order]
    return result


def iter_isinstance(obj, *type_tuples):
    """
    Given an iterable object and a list of tuples of types, classes or tuples
    of types and classes determine if the given object's items are instances of
    the given types. iter_isinstance(obj, types_1, types_2) is shorthand
    for iter_isinstance(obj, types_1) or iter_isinstance(obj, types_2).

    Parameters
    ----------
    obj: tuple
        The object to check
    *types: any number of types or classes
        The classes to check against
    """
    result = False
    if not isinstance(obj, (tuple, list)):
        return False
    for types in type_tuples:
        if len(obj) != len(types):
            continue
        result |= all(isinstance(o, t) for o, t in zip(obj, types))
    return result


def handle_slice_to_spectrum(cube, item):
    """
    Given a cube and a getitem argument, with the knowledge that that slice
    represents a spectrum, return the spectrum that corresponds to that slice.

    Parameters
    ----------
    cube: sunpy.cube.Cube
        The cube to slice
    item: int or slice object or tuple of these
        The slice to make
    """
    if cube.data.ndim == 3:
        if isinstance(item, int):
            spec = cube.slice_to_spectrum(item, None)
        elif iter_isinstance(item, (int, slice, int)):
            spec = cube.slice_to_spectrum(item[0], item[2])
        elif iter_isinstance(item, (slice, int, int)):
            spec = cube.slice_to_spectrum(item[1], item[2])
        else:
            spec = cube.slice_to_spectrum(item[0], None)
    else:
        if iter_isinstance(item, (int, slice, int, int)):
            spec = cube.slice_to_spectrum(item[0], item[2], item[3])
        elif iter_isinstance(item, (int, slice, int, slice),
                             (int, slice, int)):
            spec = cube.slice_to_spectrum(item[0], item[2], None)
        elif iter_isinstance(item, (int, slice, slice, int)):
            spec = cube.slice_to_spectrum(item[0], None, item[3])
    return spec


def handle_slice_to_lightcurve(cube, item):
    """
    Given a cube and a getitem argument, with the knowledge that that slice
    represents a lightcurve, return the lightcurve that corresponds to that
    slice.

    Parameters
    ----------
    cube: sunpy.cube.Cube
        The cube to slice
    item: int or slice object or tuple of these
        The slice to make
    """
    if cube.data.ndim == 3:
        if iter_isinstance(item, (slice, int, int)):
            lightc = cube.slice_to_lightcurve(item[1], item[2])
        else:
            lightc = cube.slice_to_lightcurve(item[1])
    else:
        if iter_isinstance(item, (slice, int, int, int)):
            lightc = cube.slice_to_lightcurve(item[1], item[2], item[3])
        elif iter_isinstance(item, (slice, int, slice, int)):
            lightc = cube.slice_to_lightcurve(item[1], x_coord=item[3])
        else:
            lightc = cube.slice_to_lightcurve(item[1], y_coord=item[2])
    return lightc


def handle_slice_to_map(cube, item):
    """
    Given a cube and a getitem argument, with the knowledge that that slice
    represents a map, return the map that corresponds to that slice.

    Parameters
    ----------
    cube: sunpy.cube.Cube
        The cube to slice
    item: int or slice object or tuple of these
        The slice to convert
    """
    if cube.data.ndim == 3:
        if isinstance(item, int):
            gmap = cube.slice_to_map(item)
        else:
            gmap = cube.slice_to_map(item[0])
    else:
        gmap = cube.slice_to_map(item[0], item[1])
    return gmap


def handle_slice_to_cube(hypcube, item):
    """
    Given a hypercube and a getitem argument, with the knowledge that the slice
    represents a 3D cube, return the cube that corresponds to that slice.

    Parameters
    ----------
    hypcube: sunpy.cube.Cube
        The 4D hypercube to slice
    item: int or slice, or tuple of these
        The slice to convert
    """
    if isinstance(item, int):
        chunk = item
        axis = 0
    else:
        chunk = [i for i in item if isinstance(i, int)][0]
        axis = item.index(chunk)
    return hypcube.slice_to_cube(axis, chunk)


def reduce_dim(cube, axis, keys):
    """
    Given an axis and a slice object, returns a new cube with the slice
    applied along the given dimension. For example, in a time-x-y cube,
    a reduction along the x axis (axis 1) with a slice value (1, 4, None)
    would return a cube where the only x values were 1 to 3 of the original
    cube.

    Parameters
    ----------
    cube: sunpy.cube.Cube
        The cube to reduce
    axis: int
        The dimension to reduce
    keys: slice object
        The slicing to apply
    """
    start = keys.start if keys.start is not None else 0
    stop = keys.stop if keys.stop is not None else cube.data.shape[axis]
    if stop > cube.data.shape[axis]:
        stop = cube.data.shape[axis]
    if start < 0:
        start = 0
    step = keys.step if keys.step is not None else 1
    indices = range(start, stop, step)
    newdata = cube.data.take(indices, axis=axis)
    newwcs = cube.axes_wcs.deepcopy()

    wcs_slice_data = [slice(start, stop)]
    for i in range(axis-1, -1, -1):
        wcs_slice_data.insert(0, slice(0, cube.data.shape[i]))
    newwcs = newwcs.slice(wcs_slice_data)

    kwargs = {'meta': cube.meta, 'unit': cube.unit}
    if cube.uncertainty is not None:
        errors = deepcopy(cube.uncertainty)
        errors.array = errors.array.take(indices, axis=axis)
        kwargs.update({'errors': errors})
    if cube.mask is not None:
        mask = cube.mask.take(indices, axis=axis)
        kwargs.update({'mask': mask})

    newcube = cube._new_instance(data=newdata, wcs=newwcs, **kwargs)
    return newcube


def getitem_3d(cube, item):
    """
    Handles Cube's __getitem__ method for 3-dimensional cubes.

    Parameters
    ----------
    cube: sunpy.cube object
        The cube to get the item from
    item: int, slice object, or tuple of these
        The item to get from the cube
    """
    axes = cube.axes_wcs.wcs.ctype
    slice_to_map = (axes[1] != 'WAVE' and
                    (isinstance(item, int) or
                     iter_isinstance(item, (int, slice), (int, slice, slice))))
    slice_to_spectrum = (((isinstance(item, int) or
                           iter_isinstance(item, (int, slice),
                                           (int, slice, slice),
                                           (int, slice, int)))
                          and axes[1] == 'WAVE')
                         or (axes[0] == 'WAVE' and
                             iter_isinstance(item, (slice, int, int))))
    slice_to_spectrogram = (iter_isinstance(item, (slice, slice, int)) and
                            axes[1] == 'WAVE')
    slice_to_lightcurve = (axes[1] == 'WAVE' and
                           (iter_isinstance(item, (slice, int, int),
                                            (slice, int),
                                            (slice, int, slice))))
    stay_as_cube = (isinstance(item, slice) or
                    (isinstance(item, tuple) and
                     not any(isinstance(i, int) for i in item)))
    reducedcube = reduce_dim(cube, 0, slice(None, None, None))
    # XXX: We're not actually reducing a cube, just a way of copying the cube.
    if isinstance(item, tuple):
        for i in range(len(item)):
            if isinstance(item[i], slice):
                reducedcube = reduce_dim(reducedcube, i, item[i])

    if isinstance(item, slice):
        reducedcube = reduce_dim(reducedcube, 0, item)

    if slice_to_map:
        result = handle_slice_to_map(reducedcube, item)
    elif slice_to_spectrum:
        result = handle_slice_to_spectrum(reducedcube, item)
    elif slice_to_spectrogram:
        result = reducedcube.slice_to_spectrogram(item[2])
    elif slice_to_lightcurve:
        result = handle_slice_to_lightcurve(reducedcube, item)
    elif stay_as_cube:
        result = reducedcube
    else:
        result = cube.data[item]
    return result


def getitem_4d(cube, item):
    """
    Handles Cube's __getitem__ method for 4-dimensional hypercubes.

    Parameters
    ----------
    cube: sunpy.cube object
        The cube to get the item from
    item: int, slice object, or tuple of these
        The item to get from the cube
    """
    slice_to_map = iter_isinstance(item, (int, int), (int, int, slice),
                                   (int, int, slice, slice))
    slice_to_spectrogram = iter_isinstance(item, (slice, slice, int, int))
    slice_to_spectrum = iter_isinstance(item, (int, slice, int, int),
                                        (int, slice, int),
                                        (int, slice, int, slice),
                                        (int, slice, slice, int))
    slice_to_cube = (isinstance(item, int) or
                     (isinstance(item, tuple) and
                      len([i for i in item if isinstance(i, int)]) == 1))
    slice_to_lightcurve = iter_isinstance(item, (slice, int, int, int),
                                          (slice, int, int),
                                          (slice, int, int, slice),
                                          (slice, int, slice, int))
    stay_as_hypercube = (isinstance(item, slice) or
                         (isinstance(item, tuple) and
                          not any(isinstance(i, int) for i in item)))
    reducedcube = reduce_dim(cube, 0, slice(None, None, None))
    if isinstance(item, tuple):
        for i in range(len(item)):
            if isinstance(item[i], slice):
                reducedcube = reduce_dim(reducedcube, i, item[i])

    if isinstance(item, slice):
        reducedcube = reduce_dim(reducedcube, 0, item)

    if slice_to_map:
        result = handle_slice_to_map(reducedcube, item)
    elif slice_to_spectrum:
        result = handle_slice_to_spectrum(reducedcube, item)
    elif slice_to_spectrogram:
        result = reducedcube.slice_to_spectrogram(item[2], item[3])
    elif slice_to_lightcurve:
        result = handle_slice_to_lightcurve(reducedcube, item)
    elif slice_to_cube:
        result = handle_slice_to_cube(reducedcube, item)
    elif stay_as_hypercube:
        result = reducedcube
    else:
        result = cube.data[item]
    return result


def pixelize_slice(item, wcs, _source='cube'):
    """
    Given a getitem slice that may or may not contain astropy units and a wcs,
    convert these to pixels. Raises a CubeError if the units don't match.
    This assumes that the array is not rotated.

    Parameters
    ----------
    item: int, astropy.Quantity, slice, or tuple of these
        The slice to convert to pixels.
    wcs: Sunpy.wcs.wcs.WCS
        The WCS object representing the array
    """
    if isinstance(item, tuple):
        result = list(range(len(item)))
        for axis in range(len(item)):
            if isinstance(item[axis], slice):
                result[axis] = _convert_slice(item[axis], wcs,
                                              axis, _source=_source)
            elif isinstance(item[axis], u.Quantity):
                result[axis] = convert_point(item[axis].value,
                                             item[axis].unit, wcs, axis,
                                             _source=_source)
            else:
                result[axis] = item[axis]
        result = tuple(result)
    elif isinstance(item, u.Quantity):
        result = convert_point(item.value, item.unit, wcs, 0)
    elif isinstance(item, slice):
        result = _convert_slice(item, wcs, 0, _source=_source)
    else:
        result = item

    return result


def convert_point(value, unit, wcs, axis, _source='cube'):
    """
    Takes a point on an axis specified by the given wcs and returns the pixel
    coordinate.

    Parameters
    ----------
    value: int or float
        The magnitude of the specified point.
    unit: astropy.unit.Unit
        The unit for the given value. Note this doesn't take in a quantity to
        simplify _convert_slice.
    wcs: sunpy.wcs.wcs.WCS
        The WCS describing the axes system.
    axis: int
        The axis the value corresponds to, in numpy-style ordering (i.e.
        opposite WCS convention)
    """
    if value is None:
        return None  # This is used to simplify None coordinates during slicing
    if unit is None or unit == u.pix or unit == u.pixel:
        return int(value)
    if isinstance(value, u.Quantity):
        value = value.value
        unit = value.unit
    if _source == 'cube':
        wcsaxis = -1 - axis if not wcs.was_augmented else -2 - axis
    else:
        wcsaxis = 1 - axis
    cunit = u.Unit(wcs.wcs.cunit[wcsaxis])
    crpix = wcs.wcs.crpix[wcsaxis]
    crval = wcs.wcs.crval[wcsaxis] * cunit
    cdelt = wcs.wcs.cdelt[wcsaxis] * cunit
    point = (value * unit).to(cunit)
    pointdelta = ((point - crval) / cdelt).value
    point = crpix + pointdelta
    return int(np.round(point))


def pixelize(coord, wcs, axis):
    '''shorthand for convert_point'''
    unit = coord.unit if isinstance(coord, u.Quantity) else None
    return convert_point(coord, unit, wcs, axis)


def _convert_slice(item, wcs, axis, _source='cube'):
    """
    Takes in a slice object that may or may not contain units and translates it
    to pixel coordinates along the given wcs and axis. If there are no units,
    returns the same slice; if there is more than one non-identical unit,
    raises a CubeError.

    Parameters
    ----------
    item: slice object
        The slice to convert to pixels. It may be composed of Nones, ints,
        floats or astropy Quantities, in any combination (with the restriction
        noted above)
    wcs: sunpy.wcs.wcs.WCS
        The WCS describing this system
    axis: int
        The axis the slice corresponds to, in numpy-style ordering (i.e.
        opposite WCS convention)
    """
    if _source == 'cube':
        wcs_ax = -2 - axis if wcs.was_augmented else -1 - axis
    else:
        wcs_ax = 1 - axis
    steps = [item.start, item.stop, item.step]
    values = [None, None, None]
    unit = None
    for i in range(3):
        if isinstance(steps[i], u.Quantity):
            if unit is not None and steps[i].unit != unit:
                raise CubeError(5, "Only one unit per axis may be given")
            else:
                unit = steps[i].unit
                values[i] = steps[i].value
        else:
            values[i] = steps[i]
    if unit is None:
        return item

    if values[2] is None:
        delta = None
    else:
        cunit = u.Unit(wcs.wcs.cunit[wcs_ax])
        cdelt = wcs.wcs.cdelt[wcs_ax] * cunit
        delta = int(np.round(((values[2] * unit).to(cunit) / cdelt).value))

    if values[0] is None:
        start = None
    else:
        start = convert_point(values[0], unit, wcs, axis, _source=_source)

    if values[1] is None:
        end = None
    else:
        end = convert_point(values[1], unit, wcs, axis, _source=_source)

    return slice(start, end, delta)

def get_cube_from_sequence(cubesequence, item):
    """
    Handles CubeSequence's __getitem__ method for list of cubes.

    Parameters
    ----------
    cubesequence: sunpycube.CubeSequence object
        The cubesequence to get the item from
    item: int, slice object, or tuple of these
        The item to get from the cube
    """
    if isinstance(item, int):
        return cubesequence.data[item]
    return cubesequence.data[item[0]][item[1::]]

def get_cube_from_sequence(cubesequence, item):
    """
    Handles CubeSequence's __getitem__ method for list of cubes.

    Parameters
    ----------
    cubesequence: sunpycube.CubeSequence object
        The cubesequence to get the item from
    item: int, slice object, or tuple of these
        The item to get from the cube
    """
    if isinstance(item, int):
        result = cubesequence.data[item]
    if isinstance(item, slice):
        data = cubesequence.data[item]
        result = cubesequence._new_instance(
            data, meta=cubesequence.meta, common_axis=cubesequence.common_axis)
    if isinstance(item, tuple):
        # if the 0th index is int.
        if isinstance(item[0], int):
            # to satisfy something like cubesequence[0,0] this should have data type
            # as cubesequence[0][0]
            if len(item[1::]) is 1:
                result = cubesequence.data[item[0]][item[1]]
            else:
                result = cubesequence.data[item[0]][item[1::]]
        # if the 0th index is slice.
        # used for the index_sequence_as_cube function. Slicing across cubes.
        # item represents (slice(start_cube_index, end_cube_index, None),
        # [slice_of_start_cube, slice_of_end_cube]) if end cube is not sliced then length is 1.
        if isinstance(item[0], slice):
            data = cubesequence.data[item[0]]
            # applying the slice in the start of cube.
            data[0] = data[0][item[1][0]]
            if len(item[1]) is 2:
                # applying the slice in the end of cube.
                data[-1] = data[-1][item[1][-1]]
            # applying the rest of the item in all the cubes.
            for i, cube in enumerate(data):
                if len(item[2::]) is 1:
                    data[i] = cube[item[2]]
                else:
                    data[i] = cube[item[2::]]
            result = cubesequence._new_instance(
                data, meta=cubesequence.meta, common_axis=cubesequence.common_axis)
    return result


def index_sequence_as_cube(cubesequence, item):
    """
    Enables CubeSequence to be indexed as a single Cube.

    This is only possible if cubesequence.common_axis is set,
    i.e. if the Cubes are sequence in order along one of the Cube axes.
    For example, if cubesequence.common_axis=1 where the first axis is
    time, and the Cubes are sequence chronologically such that the last
    time slice of one Cube is directly followed in time by the first time
    slice of the next Cube, then this function allows the CubeSequence to
    be indexed as though all Cubes were combined into one ordered along
    the time axis.

    Parameters
    ----------
    cubesequence: sunpycube.CubeSequence object
        The cubesequence to get the item from
    item: int, slice object, or tuple of these
        The item to get from the cube.  If tuple length must be <= number
        of dimensions in single Cube.

    Example
    -------
    >>> # Say we have three Cubes each cube has common_axis=1 is time and shape=(3,3,3)
    >>> data_list = [cubeA, cubeB, cubeC]
    >>> cs = CubeSequence(data_list, meta=None, common_axis=1)
    >>> # return zeroth time slice of cubeB in via normal CubeSequence indexing.
    >>> cs[1,:,0,:]
    >>> # Return same slice using this function
    >>> index_sequence_as_cube(cs, (slice(0, cubeB.shape[0]), 0, (slice(0, cubeB.shape[2]))

    """
    # Determine starting slice of each cube along common axis.
    cumul_cube_lengths = np.cumsum(np.array([c.data.shape[cubesequence.common_axis]
                                             for c in cubesequence.data]))
    # Case 1: Item is int and common axis is 0. Not yet supported.
    if isinstance(item, int):
        if cubesequence.common_axis != 0:
            raise ValueError("Input can only be indexed with an int if "
                             "CubeSequence's common axis is 0. common "
                             "axis = {0}".format(cubesequence.common_axis))
        else:
            sequence_index, cube_index = _convert_cube_like_index_to_sequence_indices(
                item, cumul_cube_lengths)
            item_list = [item]
    # Case 2: Item is slice and common axis is 0.
    elif isinstance(item, slice):
        if cubesequence.common_axis != 0:
            raise ValueError("Input can only be sliced with a single slice if "
                             "CubeSequence's common axis is 0. common "
                             "axis = {0}".format(cubesequence.common_axis))
        else:
            sequence_index, cube_index = _convert_cube_like_slice_to_sequence_slices(
                item, cumul_cube_lengths)
            item_list = [item]
    # Case 3: Item is tuple and common axis index is int.
    elif isinstance(item[cubesequence.common_axis], int):
        # Since item must be a tuple, convert to list to
        # make ensure it's mutable for next cases.
        item_list = list(item)
        # Check item is long enough to include common axis.
        if len(item_list) < cubesequence.common_axis:
            raise ValueError("Input item not long enough to include common axis."
                             "Must have length of of between "
                             "{0} and {1} inclusive.".format(
                                 cubesequence.common_axis, len(cubesequence[0].data.shape)))
        sequence_index, cube_index = _convert_cube_like_index_to_sequence_indices(
            item_list[cubesequence.common_axis], cumul_cube_lengths)
    # Case 4: Item is tuple and common axis index is slice.
    elif isinstance(item[cubesequence.common_axis], slice):
        # Since item must be a tuple, convert to list to
        # make ensure it's mutable for next cases.
        item_list = list(item)
        # Check item is long enough to include common axis.
        if len(item_list) < cubesequence.common_axis:
            raise ValueError("Input item not long enough to include common axis."
                             "Must have length of of between "
                             "{0} and {1} inclusive.".format(
                                 cubesequence.common_axis, len(cubesequence[0].data.shape)))
        sequence_index, cube_index = _convert_cube_like_slice_to_sequence_slices(
            item_list[cubesequence.common_axis], cumul_cube_lengths)
    else:
        raise ValueError("Invalid index/slice input.")
    # Replace common axis index/slice with corresponding
    # index/slice with cube.
    item_list[cubesequence.common_axis] = cube_index
    # Insert corresponding index/slice of required cube in sequence.
    item_list.insert(0, sequence_index)
    item_tuple = tuple(item_list)
    return cubesequence[item_tuple]


def _convert_cube_like_index_to_sequence_indices(cube_like_index, cumul_cube_lengths):
    # so that it returns the correct sequence_index and cube_index as
    # np.where(cumul_cube_lengths <= cube_like_index) returns NULL.
    if cube_like_index < cumul_cube_lengths[0]:
        sequence_index = 0
        cube_index = cube_like_index
    else:
        sequence_index = np.where(cumul_cube_lengths <= cube_like_index)[0][-1]
        # if the cube is out of range then return the last index
        if cube_like_index > cumul_cube_lengths[-1] - 1:
            cube_index = cumul_cube_lengths[0] - 1
        else:
            cube_index = cube_like_index - cumul_cube_lengths[sequence_index]
        # sequence_index should be plus one as the sequence_index earlier is
        # previous index if it is not already the last cube index.
        if sequence_index < cumul_cube_lengths.size - 1:
            sequence_index += 1
    return sequence_index, cube_index


def _convert_cube_like_slice_to_sequence_slices(cube_like_slice, cumul_cube_lengths):
    if cube_like_slice.start is not None:
        sequence_start_index, cube_start_index = _convert_cube_like_index_to_sequence_indices(
            cube_like_slice.start, cumul_cube_lengths)
    else:
        sequence_start_index, cube_start_index = _convert_cube_like_index_to_sequence_indices(
            0, cumul_cube_lengths)
    if cube_like_slice.stop is not None:
        sequence_stop_index, cube_stop_index = _convert_cube_like_index_to_sequence_indices(
            cube_like_slice.stop, cumul_cube_lengths)
    else:
        sequence_stop_index, cube_stop_index = _convert_cube_like_index_to_sequence_indices(
            cumul_cube_lengths[-1], cumul_cube_lengths)
    if cube_like_slice.stop is not None:
        if not cube_like_slice.stop < cumul_cube_lengths[-1]:
            # as _convert_cube_like_index_to_sequence_indices function returns last
            # cube index so we need to increment it by one and set the cube_stop_index
            # as 0 as the function returns the last index of the cube.
            cube_stop_index = 0
            sequence_stop_index += 1
    # if the start and end sequence index are not equal implies slicing across cubes.
    if sequence_start_index != sequence_stop_index:
        # the first slice of cube_slice will be cube_start_index and the length of
        # that cube's end index
        # only storing those cube_slice that needs to be changed.
        # Like if sequence_slice is slice(0, 3) meaning - 0, 1, 2 cubes this means we will
        # store only 0th index slice and 2nd index slice in this list.
        cube_slice = [slice(cube_start_index, cumul_cube_lengths[
                            sequence_start_index], cube_like_slice.step)]

        # for cube over which slices occur appending them
        # for i in range(sequence_start_index+1, sequence_stop_index):
        #     cube_slice.append(slice(0, cumul_cube_lengths[i]-cumul_cube_lengths[i-1]))
        # if the stop index is 0 then slice(0, 0) is not taken. slice(0,3)
        # represent 0,1,2 not 0,1,2,3.
        if int(cube_stop_index) is not 0:
            cube_slice.append(slice(0, cube_stop_index, cube_like_slice.step))
            sequence_slice = slice(sequence_start_index,
                                   sequence_stop_index+1, cube_like_slice.step)
        else:
            sequence_slice = slice(sequence_start_index, sequence_stop_index, cube_like_slice.step)
    else:
        cube_slice = slice(cube_start_index, cube_stop_index, cube_like_slice.step)
        sequence_slice = slice(sequence_start_index, sequence_stop_index+1, cube_like_slice.step)
    return sequence_slice, cube_slice


class CubeError(Exception):
    """
    Class for handling Cube errors.
    """
    errors = {0: 'Unspecified error',
              1: 'Time dimension not present',
              2: 'Spectral dimension not present',
              3: 'Insufficient spatial dimensions',
              4: 'Dimension error',
              5: 'Slicing unit error',
              6: 'Unaligned array error'}

    def __init__(self, value, msg):
        Exception.__init__(self, msg)
        self.value = value
        self.message = msg

    def __str__(self):
        return 'ERROR ' + repr(self.value) + ' (' \
               + self.errors.get(self.value, '') + '): ' + self.message
