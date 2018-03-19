# $Id$

import os
from xml.dom import minidom
from abaqus import session, CANCEL
from abaqusConstants import *

xmldoc = None   # Settings in memory
xmlFileName = '~/.legendScale.xml'  # Settings file name
__version__ = 0.7 # Version of settings file format

def setup_scale(vpName, maxScale, minScale, guide, reverse,
        color1, color2):
    """Set the Abaqus/Viewer contour legend scale to even increments.
    
    Carl Osterwisch <carl.osterwisch@avlna.com> 2006"""
    import math
    debug = os.environ.has_key('DEBUG')

    viewport = session.viewports[vpName]
    if 'contourOptions' in dir(viewport.odbDisplay):
        contourOptions = viewport.odbDisplay.contourOptions
        symbolOptions = viewport.odbDisplay.symbolOptions
        
        if minScale > maxScale:
            minScale, maxScale = maxScale, minScale # swap if necessary
        span = maxScale - minScale
        order = 10.0**math.floor(math.log10(span))
        tic = order*5
        for x in [2, 1, 0.50, 0.25, 0.20, 0.10, 0.05]:
            if span/(x*order) <= guide:
                tic = x*order
        minScale = tic*(math.ceil(minScale/tic))
        maxScale = tic*(math.floor(maxScale/tic))
        intervals = int((maxScale - minScale)/tic + 0.1)
        
        if contourOptions.outsideLimitsMode==SPECTRUM:
            if maxScale < contourOptions.autoMaxValue:
                intervals += 1
            if minScale > contourOptions.autoMinValue:
                intervals += 1
            
        contourOptions.setValues(minValue = minScale, maxValue = maxScale,
                minAutoCompute=OFF, maxAutoCompute=OFF,
                intervalType=UNIFORM,
                numIntervals=intervals)
        symbolOptions.setValues(vectorMinValue = minScale,
                vectorMaxValue = maxScale,
                vectorMinValueAutoCompute=OFF, vectorMaxValueAutoCompute=OFF,
                vectorIntervalNumber=intervals,
                tensorMinValue = minScale, tensorMaxValue = maxScale,
                tensorMinValueAutoCompute=OFF, tensorMaxValueAutoCompute=OFF,
                tensorIntervalNumber=intervals)

        if reverse:
            contourOptions.setValues(
                spectrumType=REVERSED_RAINBOW, 
                outsideLimitsAboveColor=color1, 
                outsideLimitsBelowColor=color2)
            symbolOptions.setValues(
                tensorColorSpectrum='Reversed rainbow', 
                vectorColorSpectrum='Reversed rainbow') 
        else:
            contourOptions.setValues(
                spectrumType=RAINBOW, 
                outsideLimitsAboveColor=color2, 
                outsideLimitsBelowColor=color1)
            symbolOptions.setValues(
                tensorColorSpectrum='Rainbow', 
                vectorColorSpectrum='Rainbow') 

        annotationOptions = viewport.viewportAnnotationOptions
        try:
            if FIXED == annotationOptions.legendNumberFormat:
                decPlaces = 0
                ticStr = '%g'%tic
                decIndex = ticStr.find('.')
                if decIndex > 0:
                    decPlaces = len(ticStr) - decIndex - 1
                if debug:
                    print repr(ticStr), len(ticStr), decIndex, decPlaces
                annotationOptions.setValues(legendDecimalPlaces=decPlaces)
            else:
                if debug:
                    print annotationOptions.legendNumberFormat, 'not FIXED'
                annotationOptions.setValues(legendDecimalPlaces=3)
        except NameError as e:
            # Abaqus CAE version < 6.6
            pass
            if debug:
                print 'NameError', e
        return True


def readXmlFile():
    "Read xmldoc or create a new xmldoc if necessary"
    global xmldoc
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
                (CANCEL, ))
    xmldoc = doc


def setValues(vpName, maxScale, minScale, guide, reverse,
        color1, color2):
    "Set scale and save these settings for future recall"

    if not setup_scale(vpName, maxScale, minScale, guide, reverse,
            color1, color2):
        return  # Skip the rest if error
    readXmlFile()
    viewport = session.viewports[vpName]
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
    fo.appendChild(xmldoc.createElement('format')).appendChild(
            xmldoc.createTextNode(repr(
        viewport.viewportAnnotationOptions.legendNumberFormat)))

    # Save settings to disk
    open(os.path.expanduser(xmlFileName), 'w').write(xmldoc.toxml())


def recall(vpName):
    "Read previous settings for this primaryVariable"

    viewport = session.viewports[vpName]
    if not 'contourOptions' in dir(viewport.odbDisplay):
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
        fmt = eval(fo.getElementsByTagName("format")[0].
                childNodes[0].data)
        viewport.viewportAnnotationOptions.setValues(
                legendNumberFormat=fmt)
        setup_scale(vpName, maxScale, minScale, guide, reverse,
                color1, color2)


def restore_defaults(vpName):
    """Set the contour legend scale to the default values."""
    viewport = session.viewports[vpName]
    if 'contourOptions' in dir(viewport.odbDisplay):
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
