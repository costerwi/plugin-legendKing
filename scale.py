from __future__ import print_function
import os
from xml.dom import minidom
from abaqusConstants import *

xmldoc = None   # Settings in memory
xmlFileName = '~/.legendScale.xml'  # Settings file name
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
    [0.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 140.0, 160.0, 180.0]
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
    if -0.1*delta < ticks[0] < delta:
        ticks.pop(0)
    if -delta < ticks[-1] < 0.1*delta:
        ticks.pop()
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

    span = ticks[-1] - ticks[0]
    if span <= 1e-3 or span >= 1e5: # very small or very large; use scientific format
        maxTick = max([abs(tick) for tick in ticks])
        numDecimal += floor(log10(abs(maxTick))) # relative
        numDecimal = min(max(numDecimal, 0), 9)
        return SCIENTIFIC, int(numDecimal)

    numDecimal = min(max(numDecimal, 0), 9)
    return FIXED, int(numDecimal)


def setup_scale(vpName, maxScale, minScale, guide, reverse=None,
        color1=None, color2=None, maxExact=None, minExact=None):
    """Set the Abaqus/Viewer contour legend scale to even increments.

    Carl Osterwisch, 2006"""
    import abaqus
    import math

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
        if None == color1:
            color1 = contourOptions.outsideLimitsBelowColor
        if None == color2:
            color2 = contourOptions.outsideLimitsAboveColor

        ticks = linearScale(maxScale, minScale, guide)

        if LOG == contourOptions.intervalType:
            minScale = 10**minScale
            maxScale = 10**maxScale
        contourOptions.setValues(
                minValue = ticks[0], maxValue = ticks[-1],
                minAutoCompute=OFF, maxAutoCompute=OFF,
                numIntervals=len(ticks) - 1,
                intervalType=UNIFORM,
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
        fmt, decPlaces = tickFormat(ticks)
        annotationOptions.setValues(
                legendNumberFormat=fmt,
                legendDecimalPlaces=decPlaces,
                )
        if DEBUG:
            print(maxScale, minScale, maxExact, minExact)
            print(ticks, fmt, decPlaces)

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


def readXmlFile():
    "Read xmldoc or create a new xmldoc if necessary"
    global xmldoc
    import abaqus
    if xmldoc:
        return  # Already read
    if os.path.exists(os.path.expanduser(xmlFileName)):
        doc = minidom.parse(os.path.expanduser(xmlFileName))
    else:
        # Create a new document
        doc = minidom.parseString('<?xml version="1.0" ?>\n'
            '<!DOCTYPE legendScale [<!ATTLIST primaryVariable name ID #IMPLIED>]>\n'
            '<!-- Saved settings for the legendScale Abaqus plugin -->\n'
            '<legendScale version="%s" />'%__version__)
        doc.changed = True
    fileType = doc.documentElement.tagName
    if not "legendScale" == fileType:
        return abaqus.getWarningReply(
                '%r is not legendScale file format'%fileType,
                (abaqus.CANCEL, ))
    xmldoc = doc


def setValues(vpName, maxScale, minScale, guide, reverse=None,
        color1=None, color2=None, maxExact=None, minExact=None):
    "Set scale and save these settings for future recall"

    import abaqus
    try:
        setup_scale(vpName, maxScale, minScale, guide, reverse,
            color1, color2, maxExact, minExact)
    except ValueError:
        return  # Skip the rest if error
    readXmlFile()
    viewport = abaqus.session.viewports[vpName]
    primaryVariable = viewport.odbDisplay.primaryVariable
    name = '_'.join((primaryVariable[0], primaryVariable[5])).lower()
    fo = xmldoc.getElementById(name)
    if fo:
        fo.parentNode.removeChild(fo)   # Remove if already exists

    # Create element for this primary variable
    fo = xmldoc.documentElement.appendChild(
            xmldoc.createElement('primaryVariable'))
    fo.setAttribute('name', name)

    # Save settings under the new element
    fo.appendChild(xmldoc.createElement('maxScale')).appendChild(
            xmldoc.createTextNode(repr(maxScale)))
    fo.appendChild(xmldoc.createElement('minScale')).appendChild(
            xmldoc.createTextNode(repr(minScale)))
    fo.appendChild(xmldoc.createElement('guide')).appendChild(
            xmldoc.createTextNode(repr(guide)))
    fo.appendChild(xmldoc.createElement('reverse')).appendChild(
            xmldoc.createTextNode(repr(reverse)))
    fo.appendChild(xmldoc.createElement('color1')).appendChild(
            xmldoc.createTextNode(repr(color1)))
    fo.appendChild(xmldoc.createElement('color2')).appendChild(
            xmldoc.createTextNode(repr(color2)))
    fo.appendChild(xmldoc.createElement('maxExact')).appendChild(
            xmldoc.createTextNode(repr(maxExact)))
    fo.appendChild(xmldoc.createElement('minExact')).appendChild(
            xmldoc.createTextNode(repr(minExact)))

    # Save settings to disk
    open(os.path.expanduser(xmlFileName), 'w').write(xmldoc.toxml())


def recall(vpName):
    "Read previous settings for this primaryVariable"

    import abaqus
    viewport = abaqus.session.viewports[vpName]
    if not hasattr(viewport.odbDisplay, 'contourOptions'):
        return
    readXmlFile()
    primaryVariable = viewport.odbDisplay.primaryVariable
    name = '_'.join((primaryVariable[0], primaryVariable[5])).lower()
    fo = xmldoc.getElementById(name)
    if fo:
        maxScale = float(fo.getElementsByTagName("maxScale")[0].
                childNodes[0].data)
        minScale = float(fo.getElementsByTagName("minScale")[0].
                childNodes[0].data)
        guide = int(fo.getElementsByTagName("guide")[0].
                childNodes[0].data)
        reverse = eval(fo.getElementsByTagName("reverse")[0].
                childNodes[0].data)
        color1 = eval(fo.getElementsByTagName("color1")[0].
                childNodes[0].data)
        color2 = eval(fo.getElementsByTagName("color2")[0].
                childNodes[0].data)
        maxExact = eval(fo.getElementsByTagName("maxExact")[0].
                childNodes[0].data)
        minExact = eval(fo.getElementsByTagName("minExact")[0].
                childNodes[0].data)
        setup_scale(vpName, maxScale, minScale, guide, reverse,
                color1, color2, maxExact, minExact)


def restore_defaults(vpName):
    """Set the contour legend scale to the default values."""
    import abaqus
    viewport = abaqus.session.viewports[vpName]
    if hasattr(viewport.odbDisplay, 'contourOptions'):
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
