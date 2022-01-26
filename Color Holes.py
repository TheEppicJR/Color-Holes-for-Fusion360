#Author-Ian Rist
#Description-Color holes by their size

from os import name
from random import random
import adsk.core, adsk.fusion, adsk.cam, traceback
import math

_app: adsk.core.Application = None
_ui: adsk.core.UserInterface = None
_handlers = []

def run(context):
    try:
        global _app, _ui
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        # Create the command definition for the feature create.
        colorHoleCreateCmdDef = _ui.commandDefinitions.addButtonDefinition('irColorHoles', 'Color Holes', 'Color Holes based on DIA', 'Resources/Button')

        # Add the create button the user interface.
        createPanel = _ui.allToolbarPanels.itemById('InspectPanel')
        cntrl: adsk.core.CommandControl = createPanel.controls.addCommand(colorHoleCreateCmdDef, 'MeasureSurface', False)
        cntrl.isPromoted = True
        cntrl.isPromotedByDefault = False

        # Connect the handler to the command created event for the clean create.
        onCommandCreated = CHCreateCommandCreatedHandler()
        colorHoleCreateCmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    _ui = None
    try:
        _app = adsk.core.Application.get()
        _ui: adsk.core.UserInterface  = _app.userInterface
        createPanel = _ui.allToolbarPanels.itemById('InspectPanel')
        cmdCntrl = createPanel.controls.itemById('irColorHoles')
        if cmdCntrl:
            cmdCntrl.deleteMe()

        colorHoleCreateCmdDef = _ui.commandDefinitions.itemById('irColorHoles')
        if colorHoleCreateCmdDef:
            colorHoleCreateCmdDef.deleteMe()

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class CHCreateCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.CommandCreatedEventArgs.cast(args)
            des: adsk.fusion.Design = _app.activeProduct
            cmd = eventArgs.command
            inputs = cmd.commandInputs

            # Add the inputs to the command dialog.
            bodiesSelInput = inputs.addSelectionInput('bodies', 'Bodies', 'Select the bodies to analyse.')
            bodiesSelInput.addSelectionFilter('Bodies')
            bodiesSelInput.isFullWidth = True


            semiCmd = inputs.addBoolValueInput('semi', 'Color Partial Surfaces', True, "", True)
            previewCmd = inputs.addBoolValueInput('preview', 'Preview Selection', True, "", True)

            onExecutePreview = CreateExecutePreviewHandler()
            cmd.executePreview.add(onExecutePreview)
            _handlers.append(onExecutePreview)

            onExecute = CreateExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class CreateExecutePreviewHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.CommandEventArgs.cast(args)
            cmd = eventArgs.command
            inputs = cmd.commandInputs

            # Get the inputs.
            bodiesSel: adsk.core.SelectionCommandInput = inputs.itemById('bodies')
            semiInput: adsk.core.BoolValueCommandInput = inputs.itemById('semi')
            previewInput: adsk.core.BoolValueCommandInput = inputs.itemById('preview')

            if previewInput.value == True:
                # Color them in
                create_color(bodiesSel, semiInput.value)

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class CreateExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.CommandEventArgs.cast(args)
            cmd = eventArgs.command
            inputs = cmd.commandInputs

            # Get the inputs.
            bodiesSel: adsk.core.SelectionCommandInput = inputs.itemById('bodies')
            semiInput: adsk.core.BoolValueCommandInput = inputs.itemById('semi')
            previewInput: adsk.core.BoolValueCommandInput = inputs.itemById('preview')

            # Color them in
            create_color(bodiesSel, semiInput.value)

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class rgbCl:
    def __init__(self, r, g, b, o, n):
        self.r = r
        self.g = g
        self.b = b
        self.o = o
        self.n = n
        self.rgb = f"{r}-{g}-{b}-{o}"
        self.name = f"CH_{self.n}_{self.rgb}"


def mk_color(rgb: rgbCl):
    app = adsk.core.Application.get()
    ui  = app.userInterface
    design = adsk.fusion.Design.cast(app.activeProduct)
    favoriteAppearances = design.appearances
    try:
        myColor = favoriteAppearances.itemByName(rgb.name)
    except:
        myColor = None
    if myColor:
        return myColor
    else:
        # Get the existing Yellow appearance.            
        fusionMaterials = app.materialLibraries.itemByName('Fusion 360 Appearance Library')
        yellowColor = fusionMaterials.appearances.itemByName('Paint - Enamel Glossy (Yellow)')
        
        # Copy it to the design, giving it a new name.
        newColor = design.appearances.addByCopy(yellowColor, rgb.name)
                    
        # Change the color of the appearance to red.
        colorProp = adsk.core.ColorProperty.cast(newColor.appearanceProperties.itemByName('Color'))
        colorProp.value = adsk.core.Color.create(rgb.r, rgb.g, rgb.b, rgb.o)
        # Assign it to the body.            
        return newColor

def trt_str(rad):
    return str(round(rad, 6))

def create_color(bodies, semi: bool):
    holes = []
    fiq = []
    for j in range(0, bodies.selectionCount):
        body =  bodies.selection(j).entity
        faces = body.faces
        for i in range(faces.count):
            face = faces.item(i)
            cylinderface = adsk.core.Cylinder.cast(face.geometry)
            if cylinderface:
                res, origin, axis, radius = cylinderface.getData()
                holes.append([j, i, radius, origin.x, origin.y, origin.z, axis.x, axis.y, axis.z])
                fiq.append(face)
                # _ui.messageBox('origin: ({}, {}, {}), axis: ({}, {}, {}), radius: {}'.format(origin.x, origin.y, origin.z, axis.x, axis.y, axis.z, radius))
    sizes = {}
    for hole in holes:
        if trt_str(hole[2]) not in sizes.keys():
            sizes[trt_str(hole[2])] = [int(random()*255), int(random()*255), int(random()*255)] 
    
    for face in fiq:
        cylinderface = adsk.core.Cylinder.cast(face.geometry)
        if cylinderface:
            res, origin, axis, radius = cylinderface.getData()
            rgb = sizes[trt_str(radius)]
            color = rgbCl(rgb[0], rgb[1], rgb[2], 0, trt_str(radius))
            app = mk_color(color)
            face.appearance = app

            
    

    
    