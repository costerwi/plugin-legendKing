"""Define the AFXForm class to handle scale dialog box events.

Carl Osterwisch <carl.osterwisch@avlna.com> October 2006
$Id$
"""

__version__ = 0.5

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
        ID_DEFAULTS,
        ID_LAST
    ] = range(AFXDataDialog.ID_LAST, AFXDataDialog.ID_LAST + 2)

    def __init__(self, form):
        # Construct the base class.
        AFXDataDialog.__init__(self, form, "Legend Scale Manager", 
                self.OK | self.APPLY | self.DISMISS, DIALOG_NORMAL)

        self.appendActionButton(text='Reset', tgt=self, sel=self.ID_DEFAULTS)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_DEFAULTS, scaleDB.onDefaults)

        self.vpNameKw = form.vpNameKw # local reference

        mainframe = FXVerticalFrame(self, LAYOUT_FILL_X)
        
        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)
        self.min = AFXTextField(p=buttonframe, 
                ncols=6, 
                labelText='Min', 
                tgt=form.minKw,
                opts=LAYOUT_FILL_X | AFXTEXTFIELD_FLOAT)

        self.max = AFXTextField(p=buttonframe,
                ncols=6, 
                labelText='Max', 
                tgt=form.maxKw,
                opts=LAYOUT_FILL_X | AFXTEXTFIELD_FLOAT)

        guide = AFXSlider(p=mainframe, tgt=form.guideKw,
                opts=AFXSLIDER_HORIZONTAL | AFXSLIDER_INSIDE_BAR | LAYOUT_FILL_X) 
        guide.setRange(3, 24)
        guide.setIncrement(1)
        guide.setMinLabelText('Fewer Intervals')
        guide.setMaxLabelText('More')
        guide.setValue(15)

        buttonframe = FXHorizontalFrame(mainframe, LAYOUT_FILL_X)

        s = AFXComboBox(p=buttonframe,
                ncols=0,
                nvis=3,
                text='Format',
                tgt=form.formatKw)
        for v in (SCIENTIFIC, ENGINEERING, FIXED):
            s.appendItem(text=v.getText(), sel=v.getId())
        
        AFXColorButton(p=buttonframe, text='', tgt=form.color1Kw)
        AFXColorButton(p=buttonframe, text='', tgt=form.color2Kw)

        FXCheckButton(p=buttonframe, 
                text='Reverse',
                tgt=form.reverseKw)

    def show(self):
        "Called to display the dialog box"
        self.vpNameKw.setValueToDefault()
        self.minmax = None
        self.sessionQuery = myQuery(session, self.onSessionChanged)
        AFXDataDialog.show(self)

    def hide(self):
        "Called to remove the dialog box"
        del self.sessionQuery, self.contourQuery
        AFXDataDialog.hide(self)

    def onSessionChanged(self):
        if session.currentViewportName != self.vpNameKw.getValue():
            # If the current viewport changes then the contourQuery needs
            # to be updated.
            viewport = session.viewports[session.currentViewportName]
            self.vpNameKw.setValue(viewport.name)
            if hasattr(viewport.odbDisplay, 'contourOptions'):
                self.contourOptions = viewport.odbDisplay.contourOptions
                self.contourQuery = myQuery(self.contourOptions, 
                        self.onContourChanged)
            else:
                self.contourQuery = None

    def onContourChanged(self):
        minmax = (self.contourOptions.autoMinValue,
                self.contourOptions.autoMaxValue)
        if minmax != self.minmax:
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

        # viewportAnnotationOptions command
        vpAnnotations = AFXGuiCommand(mode=self,
                method='setValues',
                objectName='session.viewports[%s].viewportAnnotationOptions',
                registerQuery=TRUE)

        self.formatKw = AFXSymConstKeyword(
                command=vpAnnotations,
                name='legendNumberFormat',
                isRequired=TRUE,
                defaultValue=FIXED.getId())
                
        # setup_scale kernel command
        setup_scale = AFXGuiCommand(mode=self, 
                method='setup_scale', 
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

        self.color1Kw = AFXStringKeyword(command=setup_scale,
                name='color1',
                isRequired=TRUE,
                defaultValue='Grey80')

        self.color2Kw = AFXStringKeyword(command=setup_scale,
                name='color2',
                isRequired=TRUE,
                defaultValue='#800000')

    def getFirstDialog(self):
        return scaleDB(self)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
toolset = getAFXApp().getAFXMainWindow().getPluginToolset()

toolset.registerGuiMenuButton(buttonText='&Legend Scale Manager', 
                              object=scaleForm(toolset),
                              kernelInitString='import scale',
                              author='Carl Osterwisch',
                              version=str(__version__),
                              applicableModules=['Visualization'],
                              description='Configure legend scale.'
                              )

# Version 0.2, August 2007: Added color buttons
# Version 0.3, May 2008: Added defaults button
# Version 0.4, July 2008: Added format box, removed max/min
# Version 0.5, December 2008: Changed default to FIXED
