"""Define the AFXForm class to handle scale dialog box events.

Carl Osterwisch, October 2006
"""

__version__ = '0.11.0'

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
    def __repr__(self):
        return 'myQuery {}'.format(self.subroutine.__doc__)

###########################################################################
# Dialog box definition
###########################################################################
class scaleDB(AFXDataDialog):
    """The scale dialog box class

    scaleForm will create an instance of this class when the user requests it.
    """

    [
        ID_REVERSE,
        ID_RESET,
        ID_LAST
    ] = range(AFXDataDialog.ID_LAST, AFXDataDialog.ID_LAST + 3)

    def __init__(self, form):
        # Construct the base class.
        AFXDataDialog.__init__(self, form, "Legend King",
                self.APPLY, DIALOG_NORMAL)

        self.appendActionButton(text='Reverse', tgt=self, sel=self.ID_REVERSE)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_REVERSE, scaleDB.onReverse)

        self.appendActionButton(text='Reset', tgt=self, sel=self.ID_RESET)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_RESET, scaleDB.onReset)

        self.vpNameKw = form.vpNameKw # local reference

        mainframe = FXVerticalFrame(self, LAYOUT_FILL_X)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        self.max = AFXTextField(p=buttonframe,
                ncols=8,
                labelText='Max',
                tgt=form.maxKw,
                opts=LAYOUT_FILL_X | AFXTEXTFIELD_FLOAT)
        FXCheckButton(p=buttonframe,
                text='Exactly',
                tgt=form.maxExactKw)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        self.min = AFXTextField(p=buttonframe,
                ncols=8,
                labelText='Min',
                tgt=form.minKw,
                opts=LAYOUT_FILL_X | AFXTEXTFIELD_FLOAT)
        FXCheckButton(p=buttonframe,
                text='Exactly',
                tgt=form.minExactKw)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        FXRadioButton(buttonframe, 'Linear', form.logKw, LINEAR.getId())
        FXRadioButton(buttonframe, 'Log Scale', form.logKw, LOG.getId())

        guide = AFXSlider(p=mainframe, tgt=form.guideKw,
                opts=AFXSLIDER_HORIZONTAL | AFXSLIDER_INSIDE_BAR | LAYOUT_FILL_X,
                pb=10)
        guide.setRange(3, 24)
        guide.setIncrement(1)
        guide.setMinLabelText('Fewer Intervals')
        guide.setMaxLabelText('More')
        guide.setValue(15)

        buttonframe = AFXVerticalAligner(mainframe, LAYOUT_FILL_X)

        AFXColorButton(p=buttonframe,
                text='Color above max',
                tgt=form.outsideAboveKw,
                opts=LAYOUT_FILL_X)

        spectrumCombo = AFXComboBox(p=buttonframe,
                ncols=5,
                nvis=10,
                text='',
                tgt=form.spectrumKw,
                opts=LAYOUT_FILL_X)
        for spectrum in session.spectrums.keys():
            spectrumCombo.appendItem(spectrum)

        AFXColorButton(p=buttonframe,
                text='Color below min',
                tgt=form.outsideBelowKw,
                opts=LAYOUT_FILL_X)


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
        "Recalculate settings based on a new session"
        if session.currentViewportName == self.vpNameKw.getValue():
            return
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
            self.primaryVariable = '' # force an update
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
            sendCommand("legendKing.recall(%r)"%self.vpNameKw.getValue())

    def onContourChanged(self):
        "Set GUI TextField to current min min"
        minmax = (self.contourOptions.autoMinValue,
                self.contourOptions.autoMaxValue)
        if minmax != self.minmax and isinstance(minmax[0], float):
            if self.min.getTarget():
                self.min.getTarget().setValue(minmax[0])
                self.max.getTarget().setValue(minmax[1])
            self.minmax = minmax

    def onSymbolChanged(self):
        "Set GUI TextField to current min min"
        minmax = (self.symbolOptions.autoVectorMinValue,
                self.symbolOptions.autoVectorMaxValue)
        if minmax != self.minmax and isinstance(minmax[0], float):
            if self.min.getTarget():
                self.min.getTarget().setValue(minmax[0])
                self.max.getTarget().setValue(minmax[1])
            self.minmax = minmax

    def onReverse(self, sender, sel, ptr):
        "User requested reverse spectrum colors."
        sendCommand("legendKing.reverse_spectrum(%r)"%self.vpNameKw.getValue())
        return 1

    def onReset(self, sender, sel, ptr):
        "User requested return to default settings."
        sendCommand("legendKing.restore_defaults(%r)"%self.vpNameKw.getValue())
        return 1

###########################################################################
# Form definition
###########################################################################
class scaleForm(AFXForm):
    "Class to launch the scale GUI"

    def __init__(self, owner):

        AFXForm.__init__(self, owner) # Construct the base class.

        # color spectrum
        contourOptions = AFXGuiCommand(
                mode=self,
                method='setValues',
                objectName='session.viewports[%s].odbDisplay.contourOptions',
                registerQuery=TRUE)

        self.outsideAboveKw = AFXStringKeyword(
                command=contourOptions,
                name='outsideLimitsAboveColor',
                isRequired=FALSE)

        self.outsideBelowKw = AFXStringKeyword(
                command=contourOptions,
                name='outsideLimitsBelowColor',
                isRequired=FALSE)

        self.spectrumKw = AFXStringKeyword(
                command=contourOptions,
                name='spectrum',
                isRequired=FALSE)

        # setup_scale kernel command
        setup_scale = AFXGuiCommand(mode=self,
                method='setValues',
                objectName='legendKing',
                registerQuery=FALSE)

        self.maxKw = AFXFloatKeyword(command=setup_scale,
                name='maxValue',
                isRequired=TRUE,
                defaultValue=100.)

        self.minKw = AFXFloatKeyword(command=setup_scale,
                name='minValue',
                isRequired=TRUE,
                defaultValue=0.)

        self.guideKw = AFXIntKeyword(command=setup_scale,
                name='guide',
                isRequired=TRUE,
                defaultValue=15)

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

toolset.registerGuiMenuButton(
        buttonText='&Legend King',
        object=scaleForm(toolset),
        kernelInitString='import legendKing',
        author='Carl Osterwisch',
        version=__version__,
        applicableModules=['Visualization'],
        description='Setup a reasonable legend scale quick and easy.',
        helpUrl='https://github.com/costerwi/plugin-legendKing',
        ) 
