# coding: utf-8
from __future__ import print_function, with_statement
import os
import json
from abaqusConstants import *

settings = {}   # Settings in memory
jsonFileName = os.path.expanduser('~/.legendKing.json') # Settings file name
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
    [1e-16, 1e-14, 1e-12, 1e-10, 1e-08, 1e-06, 0.0001, 0.01, 1, 100]
    >>> logScale(10055, 1)
    [1, 10, 100, 1000, 10000]
    """
    from math import floor, ceil, log10
    maxOrder = int(floor(log10(max(1e-8, maxValue))))
    minOrder = int(ceil(min(maxOrder - 2, log10(minValue))))
    stepOrder = 1 + (maxOrder - minOrder)//guide

    ticks = [10**e for e in range(minOrder, maxOrder + 1, stepOrder)]
    return ticks


def tickFormat(ticks,colormap):
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
        print(ticks)
        raise ValueError('nonpositive tick increment')
    numDecimal = -1 * ceil(log10(delta)) # approximate exponent of delta
    numDecimal += significantDigits(delta * 10**numDecimal)

    minOrder = min([log10(abs(i)) for i in ticks if abs(i) > 0.1*delta])
    maxOrder = max([log10(abs(i)) for i in ticks if abs(i) > 0.1*delta])

    # (TS) Symmetric distribution kind of breaks this logic
    if maxOrder > 5 or minOrder < -3 and colormap != 'Symmetric': # very large or small
        maxTick = max([abs(tick) for tick in ticks])
        numDecimal += floor(log10(abs(maxTick))) # relative
        numDecimal = min(max(numDecimal, 0), 9)
        return SCIENTIFIC, int(numDecimal)
    
    numDecimal = min(max(numDecimal, 0), 9)
    #(TS) need to pull that median tick value and make sure we have enough decimal points to rpresent
    if colormap=='Symmetric' and numDecimal == 0:
        numDecimal += 1  #guarantee at least one decimal point
    return FIXED, int(numDecimal)


def setup_scale(vpName, maxValue, minValue, guide, reverse=None,colormap=None,
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

        if minValue > maxValue: # swap if necessary
            minValue, maxValue = maxValue, minValue
            minExact, maxExact = maxExact, minExact
        elif minValue == maxValue:
            raise ValueError('max scale == min scale')
        # (TS)
        elif colormap == 'Symmetric':  #Symmetric about 0
            minValue = -1*maxValue

        # Load defaults
        if reverse == None and contourOptions.spectrum.startswith('Reversed'):
            reverse = True
    
         # (TS)
        if colormap == 'Symmetric':
            if guide % 2 == 0: #we have an even number; incompatible w/ Symmetric distribution
                guide += 1

        if log:
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
        if minExact and minValue < ticks[0]:
            ticks.insert(0, minValue)
        if maxExact and maxValue > ticks[-1]:
            ticks.append(maxValue)
        if len(ticks) != contourOptions.numIntervals + 1:
            contourOptions.setValues(
                intervalType=USER_DEFINED,
                intervalValues=ticks,
                )
         # (TS)
        if colormap == 'Symmetric':
            median_tick_index = len(ticks) // 2 # e.g. len(ticks) = 15 .: 15 // 2 = 7
            positive_small_num = ticks[median_tick_index + 1] * .01 #number slightly larger
            negative_small_num = ticks[median_tick_index - 1] * .01
            
            ticks.insert(median_tick_index, negative_small_num)
            ticks.insert(median_tick_index+2, positive_small_num) #need to add 2 to account for negative_small_num in list
            ticks.pop(median_tick_index+1)  
            
            contourOptions.setValues(
                intervalType=USER_DEFINED,
                intervalValues=ticks,
                )
                
        create_cmap(colormap, reverse, len(ticks))
        #else: #for all cases other than symmetric, we'll use a different function
        #    create_cmap(colormap,reverse,len(ticks))
        if log:
            fmt, decPlaces = SCIENTIFIC, 1
        else:
            fmt, decPlaces = tickFormat(ticks,colormap)
        annotationOptions.setValues(
                legendNumberFormat=fmt,
                legendDecimalPlaces=decPlaces,
                )
        if DEBUG:
            print(maxValue, minValue, maxExact, minExact)
            print(ticks, fmt, decPlaces)

        
        # (TS) Color Extremes declaration zone
        if colormap == 'Rainbow':
            if minValue*maxValue >= 0 and reverse != True:
                color1 = 'Grey80'
            else:
                color1 = '#000080' # dark blue
            color2 = '#800000' # dark red
            
        elif colormap == 'Symmetric':
            color2 = '#800000' # dark red
            color1 = '#000080' # dark blue    

        #print(reverse)
        if reverse: 
            color1 , color2 = color2, color1
            
        # (TS) Reversed Rainbow corner-case
        colormap_name = colormap 
        if colormap == 'Rainbow' and reverse == True:
            colormap_name = 'Reversed rainbow'
        
        
        # (TS) Activate Colormap
        contourOptions.setValues(
                        spectrum=colormap_name, 
                        outsideLimitsAboveColor=color2,
                        outsideLimitsBelowColor=color1)
        symbolOptions.setValues(
                        tensorColorSpectrum=colormap_name,
                        vectorColorSpectrum=colormap_name)
                        
        # if reverse:   
        #     contourOptions.setValues(
        #         spectrum='Reversed rainbow',
        #         outsideLimitsAboveColor=color1,
        #         outsideLimitsBelowColor=color2)
        #     symbolOptions.setValues(
        #         tensorColorSpectrum='Reversed rainbow',
        #         vectorColorSpectrum='Reversed rainbow')
        # else:
        #     contourOptions.setValues(
        #         spectrum='Rainbow',
        #         outsideLimitsAboveColor=color2,
        #         outsideLimitsBelowColor=color1)
        #     symbolOptions.setValues(
        #         tensorColorSpectrum='Rainbow',
        #         vectorColorSpectrum='Rainbow')

# (TS)
def create_cmap(colormap,reverse,N):
    "generate the cmap according to the user-selection for non-Rainbow colors"
    
    import abaqus
    "STEP 1: Determine bounding colors"
    if colormap == 'Rainbow':
        return
        # color1= '#000080' # dark blue
        # color2= '#800000' # dark red
    
    elif colormap == 'Symmetric':
        color1_ext = (240,100,50) #00007F Darkest Blue
        color1_mid = (220,40,100) #99BAFF Lightest Blue
        color2_mid = (20, 40, 100)#FFBB99 Lightest red
        color2_ext = (0, 100, 50) #7F0000 Darkest Red
        
    "STEP 2: Check if the color map needs reversed"
    if (reverse == True) and colormap == 'Symmetric':
        color1_ext, color2_ext = color2_ext, color1_ext #Darkest swap w/ Darkest
        color1_mid, color2_mid = color2_mid, color1_mid #Lightest swap w/ Lightest

    elif (reverse == True) and colormap != 'Symmetric': #pull a quick swap there
        color1, color2 = color2, color1
    
    
    "STEP 3: Create interpolated list of hex colors between bounding colors"
    if colormap == 'Symmetric':
        bot_colors = generate_interpolated_hex_table(color1_ext,color1_mid,N)
        top_colors = generate_interpolated_hex_table(color2_mid,color2_ext,N)
        bot_colors.append('Grey80') #central pivot point should be grey
        bot_colors.extend( top_colors ) #merge the two lists
        
        hex_colors = bot_colors
    elif colormap == 'Rainbow':
        hex_colors = generate_interpolated_hex_table(color1, color2, N)
        
    "STEP 3: Create the session spectrum object with name associated with user choice earlier"
    if colormap in ['Symmetric','Cbs-cool','Cbs-warm']:
        abaqus.session.Spectrum( name=colormap, colors=hex_colors)
    
# (TS) 
def generate_interpolated_hex_table(color1, color2, N):
    """
    Pass this function 2 colors and it'll linearly ramp HSV values between the two
    >> No guarantee that this is isochromatic
    """
    import colorsys
    import numpy as np
    Hvals = np.linspace(color1[0],color2[0],N)
    Svals = np.linspace(color1[1],color2[1],N)
    Vvals = np.linspace(color1[2],color2[2],N)
    
    HSV_table = np.ones((N,3))*np.nan
    HSV_table[:,0] = Hvals
    HSV_table[:,1] = Svals
    HSV_table[:,2] = Vvals
    
    hex_colors = ['#{:02x}{:02x}{:02x}'.format(
            int(255 * colorsys.hsv_to_rgb(h/360, s/100, v/100)[0]),
            int(255 * colorsys.hsv_to_rgb(h/360, s/100, v/100)[1]),
            int(255 * colorsys.hsv_to_rgb(h/360, s/100, v/100)[2]))
            for h, s, v in HSV_table]   #ungodly list comprehension
    return list(hex_colors)


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


def setValues(vpName, maxValue, minValue, guide, reverse=None,colormap=None,
        maxExact=None, minExact=None, log=False):
    "Set scale and save these settings for future recall"

    import abaqus
    try:
        setup_scale(vpName, maxValue, minValue, guide, reverse,colormap,
            maxExact, minExact, log==LOG)
    except ValueError as e:
        if DEBUG:
            print(e)
    readSettings()
    viewport = abaqus.session.viewports[vpName]
    primaryVariable = viewport.odbDisplay.primaryVariable
    name = ' '.join((primaryVariable[0], primaryVariable[5])).strip()
    settings[name] = {
            'maxValue': maxValue,
            'minValue': minValue,
            'guide': guide,
            'reverse': bool(reverse),
            'maxExact': bool(maxExact),
            'minExact': bool(minExact),
            'colormap':colormap,
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
