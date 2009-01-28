# $Id$

from abaqus import *
from abaqusConstants import *

def setup_scale(vpName, maxScale, minScale, guide, reverse,
        color1, color2):
    """Set the Abaqus/Viewer contour legend scale to even increments.
    
    Carl Osterwisch <carl.osterwisch@avlna.com> 2006"""
    import math

    viewport = session.viewports[vpName]
    if hasattr(viewport.odbDisplay, 'contourOptions'):
        contourOptions = viewport.odbDisplay.contourOptions
        
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

        if reverse:
            contourOptions.setValues(
                spectrumType=REVERSED_RAINBOW, 
                outsideLimitsAboveColor=color1, 
                outsideLimitsBelowColor=color2)
        else:
            contourOptions.setValues(
                spectrumType=RAINBOW, 
                outsideLimitsAboveColor=color2, 
                outsideLimitsBelowColor=color1)

        decPlaces = int(max(-math.floor(math.log10(tic)), 0))
        annotationOptions = viewport.viewportAnnotationOptions
        try:
            if FIXED == annotationOptions.legendNumberFormat:
                # Abaqus CAE 6.6, fixed format legend
                annotationOptions.setValues(legendDecimalPlaces=decPlaces)
            else:
                annotationOptions.setValues(legendDecimalPlaces=3)
        except NameError:
            # Abaqus CAE version < 6.6
            pass


def restore_defaults(vpName):
    """Set the contour legend scale to the default values."""
    viewport = session.viewports[vpName]
    if hasattr(viewport.odbDisplay, 'contourOptions'):
        contourOptions = viewport.odbDisplay.contourOptions
        default = session.defaultOdbDisplay.contourOptions
        contourOptions.setValues(
                minAutoCompute=default.minAutoCompute,
                maxAutoCompute=default.maxAutoCompute,
                intervalType=default.intervalType,
                numIntervals=default.numIntervals)
