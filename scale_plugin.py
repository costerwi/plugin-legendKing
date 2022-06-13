"""Define the AFXForm class to handle scale dialog box events.

Carl Osterwisch <carl.osterwisch@avlna.com> October 2006
$Id$
"""

__version__ = '0.9.0'

from abaqusGui import *
from abaqusConstants import *
from kernelAccess import session

class myQuery:
    "Object used to register/unregister Queries"
    def __init__(self, object, subroutine):
        "register the query when this object is created"
        self.object = object
        self.subroutine = subroutine
        object.registerQuery(subroutine)
    def __del__(self):
        "unregister the query when this object is deleted"
        self.object.unregisterQuery(self.subroutine)

###########################################################################
# Dialog box definition
###########################################################################
class scaleDB(AFXDataDialog):
    """The scale dialog box class

    scaleForm will create an instance of this class when the user requests it.
    """

    [
        ID_RESTORE,
        ID_DEFAULTS,
        ID_LAST
    ] = range(AFXDataDialog.ID_LAST, AFXDataDialog.ID_LAST + 3)

    def __init__(self, form):
        # Construct the base class.
        AFXDataDialog.__init__(self, form, "Legend Scale Manager",
                self.APPLY, DIALOG_NORMAL)

        self.appendActionButton(text='Reset', tgt=self, sel=self.ID_DEFAULTS)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_DEFAULTS, scaleDB.onDefaults)

        self.vpNameKw = form.vpNameKw # local reference

        mainframe = FXVerticalFrame(self, LAYOUT_FILL_X)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        self.max = AFXTextField(p=buttonframe,
                ncols=6,
                labelText='Max',
                tgt=form.maxKw,
                opts=LAYOUT_FILL_X | AFXTEXTFIELD_FLOAT)
        FXCheckButton(p=buttonframe,
                text='Exactly',
                tgt=form.maxExactKw)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        self.min = AFXTextField(p=buttonframe,
                ncols=6,
                labelText='Min',
                tgt=form.minKw,
                opts=LAYOUT_FILL_X | AFXTEXTFIELD_FLOAT)
        FXCheckButton(p=buttonframe,
                text='Exactly',
                tgt=form.minExactKw)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        FXCheckButton(p=buttonframe,
                text='Reverse Rainbow',
                tgt=form.reverseKw)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        FXRadioButton(buttonframe, 'Linear Ticks', form.logKw, LINEAR.getId())
        FXRadioButton(buttonframe, 'Log', form.logKw, LOG.getId())

        guide = AFXSlider(p=mainframe, tgt=form.guideKw,
                opts=AFXSLIDER_HORIZONTAL | AFXSLIDER_INSIDE_BAR | LAYOUT_FILL_X)
        guide.setRange(3, 24)
        guide.setIncrement(1)
        guide.setMinLabelText('Fewer Intervals')
        guide.setMaxLabelText('More')
        guide.setValue(15)


    def show(self):
        "Called to display the dialog box"
        self.vpNameKw.setValueToDefault() # Forces update in onSessionChanged()
        self.primaryVariable = None
        self.minmax = None
        self.sessionQuery = myQuery(session, self.onSessionChanged)
        AFXDataDialog.show(self)

    def hide(self):
        "Called to remove the dialog box"
        self.variableQuery = None
        self.sessionQuery = None
        self.minmaxQuery = None
        AFXDataDialog.hide(self)

    def onSessionChanged(self):
        if session.currentViewportName != self.vpNameKw.getValue():
            # If the current viewport changes then the contourQuery needs
            # to be updated.
            viewport = session.viewports[session.currentViewportName]
            self.vpNameKw.setValue(viewport.name)
            if hasattr(viewport.displayedObject, 'steps'):
                # Seems to be an odb display
                plotState = viewport.odbDisplay.display.plotState
                self.odbDisplay = viewport.odbDisplay
                self.contourOptions = viewport.odbDisplay.contourOptions
                self.symbolOptions = viewport.odbDisplay.symbolOptions
                self.variableQuery = myQuery(viewport.odbDisplay,
                        self.onDisplayChanged)
                if SYMBOLS_ON_DEF in plotState or SYMBOLS_ON_UNDEF in plotState:
                    # Symbol plot
                    self.minmaxQuery = myQuery(self.symbolOptions,
                        self.onSymbolChanged)
                else:
                    # Assume contour plot
                    self.minmaxQuery = myQuery(self.contourOptions,
                        self.onContourChanged)
            else:
                # Other display object (xyplot, etc)
                self.minmaxQuery = None

    def onDisplayChanged(self):
        "Changed odbDisplay; recall previous settings"
        if not hasattr(self.odbDisplay, 'primaryVariable'):
            return
        if self.primaryVariable != self.odbDisplay.primaryVariable:
            self.primaryVariable = self.odbDisplay.primaryVariable
            sendCommand("scale.recall(%r)"%self.vpNameKw.getValue())

    def onContourChanged(self):
        minmax = (self.contourOptions.autoMinValue,
                self.contourOptions.autoMaxValue)
        if minmax != self.minmax and isinstance(minmax[0], float):
            inc = (minmax[1] - minmax[0])/10
            if self.min.getTarget():
                self.min.getTarget().setValue(minmax[0])
                self.max.getTarget().setValue(minmax[1])
            self.minmax = minmax

    def onSymbolChanged(self):
        minmax = (self.symbolOptions.autoVectorMinValue,
                self.symbolOptions.autoVectorMaxValue)
        if minmax != self.minmax and isinstance(minmax[0], float):
            inc = (minmax[1] - minmax[0])/10
            self.min.getTarget().setValue(minmax[0])
            self.max.getTarget().setValue(minmax[1])
            self.minmax = minmax

    def onDefaults(self, sender, sel, ptr):
        "User requested return to default settings."
        sendCommand("scale.restore_defaults(%r)"%self.vpNameKw.getValue())
        return 1

###########################################################################
# Form definition
###########################################################################
class scaleForm(AFXForm):
    "Class to launch the scale GUI"

    def __init__(self, owner):

        AFXForm.__init__(self, owner) # Construct the base class.

        # setup_scale kernel command
        setup_scale = AFXGuiCommand(mode=self,
                method='setValues',
                objectName='scale',
                registerQuery=FALSE)

        self.maxKw = AFXFloatKeyword(command=setup_scale,
                name='maxScale',
                isRequired=TRUE,
                defaultValue=100.)

        self.minKw = AFXFloatKeyword(command=setup_scale,
                name='minScale',
                isRequired=TRUE,
                defaultValue=0.)

        self.guideKw = AFXIntKeyword(command=setup_scale,
                name='guide',
                isRequired=TRUE,
                defaultValue=15)

        self.reverseKw = AFXBoolKeyword(command=setup_scale,
                name='reverse',
                isRequired=TRUE)

        self.vpNameKw = AFXStringKeyword(command=setup_scale,
                name='vpName',
                isRequired=TRUE,
                defaultValue=None)

        self.maxExactKw = AFXBoolKeyword(command=setup_scale,
                name='maxExact',
                defaultValue=OFF,
                isRequired=TRUE)

        self.minExactKw = AFXBoolKeyword(command=setup_scale,
                name='minExact',
                defaultValue=OFF,
                isRequired=TRUE)

        self.logKw = AFXSymConstKeyword(command=setup_scale,
                name='log',
                defaultValue=LINEAR.getId(),
                isRequired=TRUE)


    def getFirstDialog(self):
        return scaleDB(self)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerGuiMenuButton(buttonText='&Legend Scale Manager',
                              object=scaleForm(toolset),
                              kernelInitString='import scale',
                              author='Carl Osterwisch',
                              version=__version__,
                              applicableModules=['Visualization'],
                              description='Configure legend scale.'
                              )

# Version 0.2, August 2007: Added color buttons
# Version 0.3, May 2008: Added defaults button
# Version 0.4, July 2008: Added format box, removed max/min
# Version 0.5, December 2008: Changed default to FIXED
# Version 0.6, September 2010: Better checking for odb in display, better reset
# Version 0.7, April 2012: Save setings for each primary variable
