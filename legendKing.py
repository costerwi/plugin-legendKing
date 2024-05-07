from __future__ import print_function, with_statement
import os
import sys
from abaqusConstants import *

settings = {}   # Settings in memory
jsonFileName = os.path.join(os.path.expanduser('~'), '.legendKing.json') # Settings file name
DEBUG = 'DEBUG' in os.environ


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


def linearScale(maxValue, minValue, guide=15):
    """Find a reasonable set of ticks for given range

    >>> linearScale(200, 0)
    [20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0, 200.0]
    >>> linearScale(10055, 1)
    [1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0, 8000.0, 9000.0, 10000.0]
    """
    from math import floor, ceil, log10
    span = maxValue - minValue
    if span <= 0:
        raise ValueError('span is <= 0')
    order = 10.0**int(floor(log10(span)))
    delta = 5*order
    for x in 2, 1, 0.50, 0.25, 0.20, 0.10, 0.05:
        if span/(x*order) > guide:
            break # too many ticks would be needed
        delta = x*order
    ticks = [ delta*int(ceil(minValue/delta)) ] # starting tick
    while ticks[-1] < maxValue - 0.95*delta:
        ticks.append(ticks[0] + len(ticks)*delta)
    if abs(ticks[0]) < 0.05*delta: # fist tick is nearly 0
        ticks.pop(0) # let CAE show minimum value as first tick
    if abs(ticks[-1]) < 0.05*delta: # last tick is nearly 0
        ticks.pop() # let CAE show maximum value as last tick
    return ticks


def logScale(maxValue, minValue, guide=15):
    """Find a reasonable set of ticks for given range

    >>> logScale(200, 0)
    [1e-14, 1e-12, 1e-10, 1e-08, 1e-06, 0.0001, 0.01, 1, 100]
    >>> logScale(0, -1)
    [1e-16, 1e-14, 1e-12, 1e-10, 1e-08, 1e-06, 0.0001, 0.01, 1]
    >>> logScale(10, 1) # TODO make smarter ticks for small ranges
    [0.1, 1, 10]
    >>> logScale(10055, 1)
    [1, 10, 100, 1000, 10000]
    """
    from math import floor, ceil, log10
    if maxValue <= 0:
        # avoid math domain error
        maxOrder = 0
    else:
        maxOrder = int(floor(log10(maxValue)))
    if minValue <= 0:
        # avoid math domain error
        minOrder = maxOrder - guide - 1
    else:
        minOrder = min(
                maxOrder - 2, # at least 2 orders of magnitude
                int(ceil(log10(minValue)))
        )
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


if sys.version_info.major >= 3:
    def toAbaqusString(unicodeString):
        "Do nothing for Python3, Abaqus >=2024"
        return unicodeString
    def fromAbaqusString(unicodeString):
        "Do nothing for Python3, Abaqus >=2024"
        return unicodeString
else:
    def toAbaqusString(unicodeString):
        "Convert unicode to str for Abaqus <2024"
        return unicodeString.encode('latin1')
    def fromAbaqusString(unicodeString):
        "Convert str to unicode for Abaqus <2024"
        return unicodeString.decode('latin1')


def fieldName(viewport):
    "Return unique fieldoutput name for specified viewport"
    primaryVariable = viewport.odbDisplay.primaryVariable
    return fromAbaqusString(' '.join((primaryVariable[0], primaryVariable[5])).strip())


def setup_legend(viewport):
    """Set the Abaqus/Viewer contour legend scale to even increments.

    Carl Osterwisch, 2006"""

    from abaqus import session
    from math import log10

    legendSettings = settings.get(fieldName(viewport), {})
    contourOptions = viewport.odbDisplay.contourOptions
    symbolOptions = viewport.odbDisplay.symbolOptions
    annotationOptions = viewport.viewportAnnotationOptions

    spectrum = fromAbaqusString(legendSettings.get('spectrum', contourOptions.spectrum))
    if spectrum and not spectrum in session.spectrums:
        # spectrum is not yet defined in the session; try to recall saved version
        spectrums = settings.get(' spectrums')
        if spectrums and spectrum in spectrums: # spectrum exists in settings
            session.Spectrum(name=toAbaqusString(spectrum),
                colors=[toAbaqusString(color) for color in spectrums[spectrum]])
        else:
            spectrum = None # undefined in session and not available in settings

    options = {
            'outsideLimitsAboveColor': legendSettings.get('above'),
            'outsideLimitsBelowColor': legendSettings.get('below'),
            'spectrum': spectrum,
        }
    contourOptions.setValues(**{option:toAbaqusString(value)
                for option, value in options.items() if value is not None})

    # Save spectrum colors in case they are needed later
    if spectrum:
        settings[' spectrums'][spectrum] = session.spectrums[toAbaqusString(spectrum)].colors

    if all(option in legendSettings for option in ('minValue', 'maxValue', 'guide')):
        minValue = legendSettings['minValue']
        maxValue = legendSettings['maxValue']
        guide = legendSettings['guide']

        if minValue > maxValue: # swap if necessary
            minValue, maxValue = maxValue, minValue
            minExact, maxExact = maxExact, minExact
        elif minValue == maxValue:
            raise ValueError('max scale == min scale')

        if legendSettings.get('log'):
            ticks = logScale(maxValue, minValue, guide)
            contourOptions.setValues(intervalType=LOG)
        else:
            ticks = linearScale(maxValue, minValue, guide)
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
        if legendSettings.get('minExact') and minValue < ticks[0]:
            ticks.insert(0, minValue)
        if legendSettings.get('maxExact') and maxValue > ticks[-1]:
            ticks.append(maxValue)
        if len(ticks) != contourOptions.numIntervals + 1:
            contourOptions.setValues(
                intervalType=USER_DEFINED,
                intervalValues=ticks,
                )
        if legendSettings.get('log'):
            fmt, decPlaces = SCIENTIFIC, 1
        else:
            fmt, decPlaces = tickFormat(ticks)
        annotationOptions.setValues(
                legendNumberFormat=fmt,
                legendDecimalPlaces=decPlaces,
                )
        if DEBUG:
            print(legendSettings.get('log', 'linear'),
                  minValue, maxValue,
                  legendSettings.get('minExact'), legendSettings.get('maxExact'))
            print(ticks, fmt, decPlaces)


def readSettings():
    "Read settings file or create a new settings if necessary"
    import json
    if settings:
        return  # Already read
    try:
        with open(jsonFileName) as f:
            settings.update(json.load(f))
    except Exception as e:
        if DEBUG:
            print('readSettings', e)
    meta = settings.setdefault(' meta', {})
    meta.setdefault('ignore', False) # used to disable memory of previous settings
    meta.update({
            'description': 'This file stores recently used settings according to field output',
            'plugin': os.path.dirname(__file__),
        })
    spectrums = settings.setdefault(' spectrums', {}) # store custom spectrums
    spectrums.update({
            ' note': 'Only used if spectrum is undefined when requested',
        })
    if not meta.get('ignore'):
        print('Using Legend King plugin settings file', jsonFileName)


def writeSettings():
    "Save settings to disk"
    import json
    if not settings.get(' meta', {}).get('ignore'):
        try:
            with open(jsonFileName, 'w') as f:
                json.dump(settings, f, indent=2, sort_keys=True)
        except Exception as e:
            if DEBUG:
                print('writeSettings', e)


def setValues(vpName, maxValue, minValue, guide,
        maxExact=None, minExact=None, log=False):
    """Set scale and save these settings for future recall

    Called directly by CAE

    Note the spectrum name, above, and below colors are set directly to
    contourOptions but the current values are also saved by this method.
    """

    from abaqus import session
    viewport = session.viewports[vpName]
    if not hasattr(viewport.odbDisplay, 'contourOptions'):
        return
    readSettings()  # make sure settings are loaded
    name = fieldName(viewport)
    spectrum = viewport.odbDisplay.contourOptions.spectrum
    settings[name] = {
            'maxValue': maxValue,
            'minValue': minValue,
            'guide': guide,
            'maxExact': bool(maxExact),
            'minExact': bool(minExact),
            'log': log==LOG,
            'spectrum': spectrum,
            'above': viewport.odbDisplay.contourOptions.outsideLimitsAboveColor,
            'below': viewport.odbDisplay.contourOptions.outsideLimitsBelowColor,
        }

    setup_legend(viewport)
    writeSettings()


def recall(vpName):
    "Read previous settings for this primaryVariable"

    from abaqus import session
    viewport = session.viewports[vpName]
    if not hasattr(viewport.odbDisplay, 'contourOptions'):
        return
    readSettings()
    if not settings.get(' meta', {}).get('ignore'):
        setup_legend(viewport)


def reverse_spectrum(vpName):
    """Reverse the current color spectrum"""
    from abaqus import session
    viewport = session.viewports[vpName]
    if not hasattr(viewport.odbDisplay, 'contourOptions'):
        return  # abort if no odb displayed

    contourOptions = viewport.odbDisplay.contourOptions
    colors = list(reversed(session.spectrums[contourOptions.spectrum].colors))
    for spectrum in session.spectrums.values():
        if not len(spectrum.colors) == len(colors):
            continue
        if all(a == b for a, b in zip(colors, spectrum.colors)):
            break # found an existing match
    else:
        # New reversed spectrum must be created
        spectrum = session.Spectrum(
                name='Reversed ' + contourOptions.spectrum,
                colors=colors)

    name = fieldName(viewport)
    settings.setdefault(name, {}).update(
        {
            'spectrum': spectrum.name,
            'above': contourOptions.outsideLimitsBelowColor,
            'below': contourOptions.outsideLimitsAboveColor,
        }
    )
    setup_legend(viewport)
    writeSettings()


def restore_defaults(vpName):
    """Set the contour legend scale to the default values."""
    from abaqus import session
    viewport = session.viewports[vpName]
    if not hasattr(viewport.odbDisplay, 'contourOptions'):
        return
    default = session.defaultOdbDisplay.contourOptions
    viewport.odbDisplay.contourOptions.setValues(
            minAutoCompute=default.minAutoCompute,
            maxAutoCompute=default.maxAutoCompute,
            intervalType=default.intervalType,
            numIntervals=default.numIntervals,
            spectrum=default.spectrum,
            outsideLimitsAboveColor=default.outsideLimitsAboveColor,
            outsideLimitsBelowColor=default.outsideLimitsBelowColor)

    default = session.defaultOdbDisplay.symbolOptions
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
