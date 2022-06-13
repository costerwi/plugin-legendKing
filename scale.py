from __future__ import print_function, with_statement
import os
import json
from abaqusConstants import *

settings = {}   # Settings in memory
jsonFileName = os.path.expanduser('~/.legendScale.json') # Settings file name
__version__ = 0.8 # Version of settings file format
DEBUG = os.environ.has_key('DEBUG')


def almostWhole(x, epsilon=1e-6):
    """Determine if a number x is within epsilon of a whole number

    >>> almostWhole(30.01, 0.1)
    True
    >>> almostWhole(30.01, 0.001)
    False
    """
    rounded = round(x)
    return (((rounded - epsilon) <= x) and ((rounded + epsilon) >= x))


def significantDigits(x):
    """Determine decimal places required to express x in fixed decimal

    >>> significantDigits(30.01)
    2
    >>> significantDigits(30.0001)
    4
    """
    x = abs(x)
    digits = 0
    if x > 0:
        while x < 0.99 or not almostWhole(x, 1e-6):
            x *= 10
            digits += 1
    return digits


def linearScale(maxScale, minScale, guide=15):
    """Find a reasonable set of ticks for given range

    >>> linearScale(200, 0)
    [20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0, 200.0]
    >>> linearScale(10055, 1)
    [1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0, 8000.0, 9000.0, 10000.0]
    """
    from math import floor, ceil, log10
    span = maxScale - minScale
    if span <= 0:
        raise ValueError('span is 0')
    order = 10.0**floor(log10(span))
    delta = 5*order
    for x in 2, 1, 0.50, 0.25, 0.20, 0.10, 0.05:
        if span/(x*order) > guide:
            break # too many ticks would be needed
        delta = x*order
    ticks = [ delta*(ceil(minScale/delta)) ] # starting tick
    while ticks[-1] <= maxScale - delta:
        ticks.append(ticks[0] + len(ticks)*delta)
    if abs(ticks[0]) < 0.1*delta:
        ticks.pop(0)
    if abs(ticks[-1]) < 0.1*delta:
        ticks.pop()
    return ticks


def logScale(maxScale, minScale, guide=15):
    """Find a reasonable set of ticks for given range

    >>> logScale(200, 0)
    [1e-16, 1e-14, 1e-12, 1e-10, 1e-08, 1e-06, 0.0001, 0.01, 1, 100]
    >>> logScale(10055, 1)
    [1, 10, 100, 1000, 10000]
    """
    from math import floor, ceil, log10
    #maxScale = max(1e-8, maxScale) # must be positive
    minOrder = int(ceil(log10(max(1e-16, minScale))))
    maxOrder = int(floor(log10(max(1e-8, maxScale))))
    stepOrder = 1 + (maxOrder - minOrder)//guide

    ticks = [10**e for e in range(minOrder, maxOrder + 1, stepOrder)]
    return ticks


def tickFormat(ticks):
    """Find a reasonable format to display ticks

    >>> tickFormat([1, 1.5, 2, 2.5])
    (FIXED, 1)
    >>> tickFormat([0, 100000, 200000])
    (SCIENTIFIC, 0)
    >>> tickFormat([0, 5.5e-8, 11e-8])
    (SCIENTIFIC, 2)
    """
    from math import floor, ceil, log10
    if len(ticks) < 2:
        raise ValueError('less than 2 ticks')
    delta = min([ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1)])
    if delta <= 0:
        raise ValueError('nonpositive tick increment')
    numDecimal = -1 * ceil(log10(delta)) # approximate exponent of delta
    numDecimal += significantDigits(delta * 10**numDecimal)

    minOrder = min([log10(abs(i)) for i in ticks if abs(i) > 0.1*delta])
    maxOrder = max([log10(abs(i)) for i in ticks if abs(i) > 0.1*delta])

    if maxOrder > 5 or minOrder < -3: # very large or small
        maxTick = max([abs(tick) for tick in ticks])
        numDecimal += floor(log10(abs(maxTick))) # relative
        numDecimal = min(max(numDecimal, 0), 9)
        return SCIENTIFIC, int(numDecimal)

    numDecimal = min(max(numDecimal, 0), 9)
    return FIXED, int(numDecimal)


def setup_scale(vpName, maxScale, minScale, guide, reverse=None,
        maxExact=None, minExact=None, log=False):
    """Set the Abaqus/Viewer contour legend scale to even increments.

    Carl Osterwisch, 2006"""
    import abaqus
    from math import log10

    viewport = abaqus.session.viewports[vpName]
    if hasattr(viewport.odbDisplay, 'contourOptions'):
        contourOptions = viewport.odbDisplay.contourOptions
        symbolOptions = viewport.odbDisplay.symbolOptions
        annotationOptions = viewport.viewportAnnotationOptions

        if minScale > maxScale:
            minScale, maxScale = maxScale, minScale # swap if necessary
        elif minScale == maxScale:
            raise ValueError('max scale == min scale')

        # Load defaults
        if None == reverse and contourOptions.spectrum.startswith('Reversed'):
            reverse = True

        if log:
            ticks = logScale(maxScale, minScale, guide)
            contourOptions.setValues(intervalType=LOG)
        else:
            ticks = linearScale(maxScale, minScale, guide)
            contourOptions.setValues(intervalType=UNIFORM)

        contourOptions.setValues(
                minValue = ticks[0], maxValue = ticks[-1],
                minAutoCompute=OFF, maxAutoCompute=OFF,
                numIntervals=len(ticks) - 1,
                )
        symbolOptions.setValues(
                vectorMinValue = ticks[0],
                vectorMaxValue = ticks[-1],
                vectorMinValueAutoCompute=OFF, vectorMaxValueAutoCompute=OFF,
                vectorIntervalNumber=len(ticks) - 1,
                tensorMinValue = ticks[0],
                tensorMaxValue = ticks[-1],
                tensorMinValueAutoCompute=OFF, tensorMaxValueAutoCompute=OFF,
                tensorIntervalNumber=len(ticks) - 1,
                )
        if minExact and minScale < ticks[0]:
            ticks.insert(0, minScale)
        if maxExact and maxScale > ticks[-1]:
            ticks.append(maxScale)
        if len(ticks) != contourOptions.numIntervals + 1:
            contourOptions.setValues(
                intervalType=USER_DEFINED,
                intervalValues=ticks,
                )
        if log:
            fmt, decPlaces = SCIENTIFIC, 1
        else:
            fmt, decPlaces = tickFormat(ticks)
        annotationOptions.setValues(
                legendNumberFormat=fmt,
                legendDecimalPlaces=decPlaces,
                )
        if DEBUG:
            print(maxScale, minScale, maxExact, minExact)
            print(ticks, fmt, decPlaces)

        if minScale*maxScale >= 0:
            color1 = 'Grey80'
        else:
            color1 = '#000080' # dark blue
        color2 = '#800000' # dark red

        if reverse:
            contourOptions.setValues(
                spectrum='Reversed rainbow',
                outsideLimitsAboveColor=color1,
                outsideLimitsBelowColor=color2)
            symbolOptions.setValues(
                tensorColorSpectrum='Reversed rainbow',
                vectorColorSpectrum='Reversed rainbow')
        else:
            contourOptions.setValues(
                spectrum='Rainbow',
                outsideLimitsAboveColor=color2,
                outsideLimitsBelowColor=color1)
            symbolOptions.setValues(
                tensorColorSpectrum='Rainbow',
                vectorColorSpectrum='Rainbow')


def readSettings():
    "Read settings file or create a new settings if necessary"
    if settings:
        return  # Already read
    try:
        with open(jsonFileName) as f:
            settings.update(json.load(f))
    except Exception as e:
        if DEBUG:
            print(e)
    meta = settings.setdefault(' meta', {})
    meta.setdefault('ignore', False) # used to disable memory of previous settings
    meta.update({
            'description': 'This file stores recently used settings according to field output',
            'plugin': os.path.dirname(__file__),
        })


def setValues(vpName, maxScale, minScale, guide, reverse=None,
        maxExact=None, minExact=None, log=False):
    "Set scale and save these settings for future recall"

    import abaqus
    try:
        setup_scale(vpName, maxScale, minScale, guide, reverse,
            maxExact, minExact, log==LOG)
    except ValueError as e:
        if DEBUG:
            print(e)
    readSettings()
    viewport = abaqus.session.viewports[vpName]
    primaryVariable = viewport.odbDisplay.primaryVariable
    name = ' '.join((primaryVariable[0], primaryVariable[5])).strip()
    settings[name] = {
            'maxScale': maxScale,
            'minScale': minScale,
            'guide': guide,
            'reverse': bool(reverse),
            'maxExact': bool(maxExact),
            'minExact': bool(minExact),
            'log': log==LOG,
        }

    # Save settings to disk
    if not settings.get(' meta', {}).get('ignore'):
        try:
            with open(jsonFileName, 'w') as f:
                json.dump(settings, f, indent=2, sort_keys=True)
        except Exception as e:
            if DEBUG:
                print(e)


def recall(vpName):
    "Read previous settings for this primaryVariable"

    import abaqus
    viewport = abaqus.session.viewports[vpName]
    if not hasattr(viewport.odbDisplay, 'contourOptions'):
        return
    readSettings()
    primaryVariable = viewport.odbDisplay.primaryVariable
    name = ' '.join( (primaryVariable[0], primaryVariable[5]) ).strip()
    fo = settings.get(name)
    if fo and not settings.get(' meta', {}).get('ignore'):
        setup_scale(vpName, **fo)


def restore_defaults(vpName):
    """Set the contour legend scale to the default values."""
    import abaqus
    viewport = abaqus.session.viewports[vpName]
    if not hasattr(viewport.odbDisplay, 'contourOptions'):
        return
    default = abaqus.session.defaultOdbDisplay.contourOptions
    viewport.odbDisplay.contourOptions.setValues(
            minAutoCompute=default.minAutoCompute,
            maxAutoCompute=default.maxAutoCompute,
            intervalType=default.intervalType,
            numIntervals=default.numIntervals,
            spectrum=default.spectrum,
            outsideLimitsAboveColor=default.outsideLimitsAboveColor,
            outsideLimitsBelowColor=default.outsideLimitsBelowColor)

    default = abaqus.session.defaultOdbDisplay.symbolOptions
    viewport.odbDisplay.symbolOptions.setValues(
            vectorMinValueAutoCompute=default.vectorMinValueAutoCompute,
            vectorMaxValueAutoCompute=default.vectorMaxValueAutoCompute,
            vectorIntervalNumber=default.vectorIntervalNumber,
            vectorColorSpectrum=default.vectorColorSpectrum)

    viewport.viewportAnnotationOptions.setValues(   # TODO: read actual default values
            legendNumberFormat=SCIENTIFIC,  # Not compatible with versions < 6.7
            legendDecimalPlaces=3)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
