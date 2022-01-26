#Author-Ian Rist
#Description-Color holes by their size

import os
from random import random
from pathlib import Path
import adsk.core, adsk.fusion, adsk.cam, traceback
import math
import csv

_app: adsk.core.Application = None
_ui: adsk.core.UserInterface = None
_handlers = []
_holes: list = None


def loadHoles():
    tmplist = []
    holepath = os.path.join(Path(__file__).resolve().parent, 'HoleSizes.csv')
    with open(holepath, newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        header = next(csvreader)
        for row in csvreader:
            tmplist.append(row)
    return tmplist

def run(context):
    try:
        global _app, _ui, _holes
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface
        _holes = loadHoles()

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
        try:
            onActiveSelectionChanged = ArgSelectHandler()
            _ui.activeSelectionChanged.add(onActiveSelectionChanged)
            _handlers.append(onActiveSelectionChanged)
        except:
            _ui.messageBox('Hover over creation failed:\n{}'.format(traceback.format_exc()))

        

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


class ArgSelectHandler(adsk.core.ActiveSelectionEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.ActiveSelectionEventArgs.cast(args)
            sels = eventArgs.currentSelection
            if len(sels) == 1 and sels[0].entity.objectType == "adsk::fusion::BRepFace":
                ent: adsk.fusion.BRepFace = sels[0].entity
                cylinderface = adsk.core.Cylinder.cast(ent.geometry)
                if cylinderface and continuous_edges(ent):
                    app = ent.appearance
                    apptxt = app.name
                    if apptxt.__contains__("CH_"):
                        _ui.messageBox(apptxt[3:].replace(" or ", "\nor\n"), "Hole Information")

        except:
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
        self.name = f"CH_{self.n}"


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
                    
        
        # _ui.messageBox(f"Hole Size: {newColor.appearanceProperties.itemByName('Image').isReadOnly}")

        # Change the color of the appearance to red.
        colorProp = adsk.core.ColorProperty.cast(newColor.appearanceProperties.itemByName('Color'))
        colorProp.value = adsk.core.Color.create(rgb.r, rgb.g, rgb.b, rgb.o)
        # Assign it to the body.            
        return newColor

def trt_str(rad):
    return str(round(rad, 6))

def findNear(rad):
    posSizes = []
    for row in _holes:
        dif = abs(float(row[1]) - rad*20) # multiply by 2 to get dia then mult by 10 to get from cm to mm
        #_ui.messageBox(f"Hole Size: {rad}\nCompaired Size: {row[1]}\nDif: {dif}")
        if dif < 0.00011:
            posSizes.append(row[0])
    return posSizes

def continuous_edges(face):
    firstLoopArr = []
    secondLoopArr = []
    edges = face.edges
    useSecondLoop = False
    # for edge in edges:
    #     if  edge in firstLoopArr or edge in secondLoopArr:
    #         pass
    #     elif len(firstLoopArr) == 0:
    #         firstLoopArr.append(edge)
    #         tempprofile = edge.tangentiallyConnectedEdges
    #         startIndex = tempprofile.find(edge)
    #         profLen = tempprofile.count
    #         for i in range(startIndex+1,profLen):
    #             curEdge = tempprofile.item(i)
    #             if curEdge in edges and not curEdge in firstLoopArr:
    #                 firstLoopArr.append(curEdge)
    #         for i in range(0, startIndex-1):
    #             curEdge = tempprofile.item(i)
    #             if curEdge in edges and not curEdge in firstLoopArr:
    #                 firstLoopArr.append(curEdge)
    #     elif (firstLoopArr[0].endVertex == firstLoopArr[-1].startVertex or firstLoopArr[-1].endVertex == firstLoopArr[0].startVertex):
    #         if len(secondLoopArr) == 0:
    #             useSecondLoop = True
    #             secondLoopArr.append(edge)
    #         tempprofile = edge.tangentiallyConnectedEdges
    #         startIndex = tempprofile.find(edge)
    #         profLen = tempprofile.count
    #         for i in range(startIndex+1,profLen):
    #             curEdge = tempprofile.item(i)
    #             if curEdge in edges and not curEdge in secondLoopArr:
    #                 secondLoopArr.append(curEdge)
    #         for i in range(0, startIndex-1):
    #             curEdge = tempprofile.item(i)
    #             if curEdge in edges and not curEdge in secondLoopArr:
    #                 secondLoopArr.append(curEdge)
    if face.loops.count > 1:
        useSecondLoop = True
    return useSecondLoop


def create_color(bodies, semi: bool):

    holes = []
    fiq = []
    for j in range(0, bodies.selectionCount):
        body =  bodies.selection(j).entity
        faces = body.faces
        for i in range(faces.count):
            face = faces.item(i)
            cylinderface = adsk.core.Cylinder.cast(face.geometry)
            if cylinderface and continuous_edges(face):
                res, origin, axis, radius = cylinderface.getData()
                holes.append([j, i, radius, origin.x, origin.y, origin.z, axis.x, axis.y, axis.z])
                fiq.append(face)
    sizes = {}

    for hole in holes:
        if trt_str(hole[2]) not in sizes.keys():
            posSize = findNear(hole[2])
            if len(posSize) == 0:
                name = trt_str(hole[2]*10)
            elif len(posSize) == 1:
                name = posSize[0]
            else:
                name = posSize[0]
                for n in posSize[1:]:
                    name = f"{name} or {n}"
            sizes[trt_str(hole[2])] = rgbCl(int(random()*255), int(random()*255), int(random()*255), 0, name) 
    
    for face in fiq:
        cylinderface = adsk.core.Cylinder.cast(face.geometry)
        if cylinderface:
            res, origin, axis, radius = cylinderface.getData()
            color = sizes[trt_str(radius)]
            app = mk_color(color)
            face.appearance = app

            
    

    
    