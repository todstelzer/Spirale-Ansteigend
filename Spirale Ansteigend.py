import adsk.core, adsk.fusion, adsk.cam, math, traceback

def get_user_parameters(ui):
    try:
        # Create input fields using Fusion's input dialogs
        result = ui.inputBox('Enter number of turns', 'Turns', '5')
        if result[1]:  # User clicked Cancel
            return None
        turns = result[0]
        
        result = ui.inputBox('Enter points per turn', 'Points per Turn', '30')
        if result[1]:
            return None
        points_per_turn = result[0]
        
        result = ui.inputBox('Enter start radius (mm)', 'Start Radius', '5.0')
        if result[1]:
            return None
        start_radius = result[0]
        
        result = ui.inputBox('Enter end radius (mm)', 'End Radius', '10.0')
        if result[1]:
            return None
        end_radius = result[0]
        
        result = ui.inputBox('Enter start pitch (mm/turn)', 'Start Pitch', '2.0')
        if result[1]:
            return None
        start_pitch = result[0]
        
        result = ui.inputBox('Enter end pitch (mm/turn)', 'End Pitch', '5.0')
        if result[1]:
            return None
        end_pitch = result[0]
        
        result = ui.inputBox('Enter wire diameter (mm)', 'Wire Diameter', '1.3')
        if result[1]:
            return None
        wire_diameter = result[0]
        
        # Return the parameters as a dictionary with proper type conversion
        return {
            'turns': int(float(turns)),
            'points_per_turn': int(float(points_per_turn)),
            'start_radius': float(start_radius),
            'end_radius': float(end_radius),
            'start_pitch': float(start_pitch),
            'end_pitch': float(end_pitch),
            'wire_diameter': float(wire_diameter)
        }
        
    except:
        if ui:
            ui.messageBox('Failed to get user parameters:\n{}'.format(traceback.format_exc()))
        return None

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        # Get user parameters
        params = get_user_parameters(ui)
        if not params:
            return
            
        # Get the design references
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent

        # Use the parameters from user input
        turns = params['turns']
        points_per_turn = params['points_per_turn']
        total_points = int(turns * points_per_turn + 1)  # Ensure total_points is an integer
        start_radius = params['start_radius'] / 10.0  # Convert mm to cm
        end_radius = params['end_radius'] / 10.0      # Convert mm to cm
        start_pitch = params['start_pitch']
        end_pitch = params['end_pitch']
        wire_diameter = params['wire_diameter'] / 10.0  # Convert mm to cm

        # ---------------------------------------------------
        # 1. Erzeuge eine Liste von Point3D-Objekten für die Helix
        # ---------------------------------------------------
        points = []
        current_z = 0.0
        for i in range(total_points):
            fraction = i / float(total_points - 1)
            # Lineare Interpolation der Steigung
            current_pitch = start_pitch + (end_pitch - start_pitch) * fraction
            angle = 2 * math.pi * (i / float(points_per_turn))
            # Interpolierter Radius
            current_radius = start_radius + (end_radius - start_radius) * fraction
            if i > 0:
                delta_z = current_pitch / points_per_turn
                current_z += delta_z
            x = current_radius * math.cos(angle)
            y = current_radius * math.sin(angle)
            pt = adsk.core.Point3D.create(x, y, current_z)
            points.append(pt)

        # ---------------------------------------------------
        # 2. Erstelle eine NURBS-Kurve (NurbsCurve3D) aus den Punkten
        # ---------------------------------------------------
        degree = 3
        n = len(points)
        if n < degree + 1:
            degree = n - 1
        # Erzeuge einen einfachen, clamped, uniformen Knotenvector:
        knots = []
        total_knots = n + degree + 1
        for i in range(total_knots):
            knots.append(i / (total_knots - 1))  # Range [0.0, 1.0]
        knots = sorted(knots)

        # Gewichte aller Kontrollpunkte = 1
        weights = [1.0] * n

        #nurbsCurve = adsk.core.NurbsCurve3D.create(points, knots, weights, degree, False)

        # ---------------------------------------------------
        # 2. Create a 3D Sketch and Fit a Spline to the Points
        # ---------------------------------------------------
        app = adsk.core.Application.get()
        design = app.activeProduct
        rootComp = design.rootComponent

        # Create a 3D sketch
        sketches = rootComp.sketches
        sketch = sketches.add(rootComp.xYConstructionPlane)
        sketch.name = "Helix Path"

        # Convert points to a list of Point3D objects
        fitPoints = adsk.core.ObjectCollection.create()
        for pt in points:
            fitPoints.add(pt)

        # Create a fitted spline (approximates the NURBS curve)
        fittedSpline = sketch.sketchCurves.sketchFittedSplines.add(fitPoints)

        # Create path directly from the sketch curve
        path = rootComp.features.createPath(fittedSpline)

        # ---------------------------------------------------
        # 4. Erstelle ein Profil (kleiner Kreis) für den Sweep
        # ---------------------------------------------------
        sketches = rootComp.sketches
        # Create sketch on XZ plane instead of XY plane
        profileSketch = sketches.add(rootComp.xZConstructionPlane)
        
        # Create circle at origin of sketch - adjusted for XZ plane
        profileCenter = adsk.core.Point3D.create(start_radius, 0, 0)
        circle = profileSketch.sketchCurves.sketchCircles.addByCenterRadius(profileCenter, wire_diameter/2)
        profile = profileSketch.profiles.item(0)

        # ---------------------------------------------------
        # 5. Erzeuge das Sweep-Feature (über den Pfad)
        # ---------------------------------------------------
        sweepFeatures = rootComp.features.sweepFeatures
        sweepInput = sweepFeatures.createInput(profile, path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        sweep = sweepFeatures.add(sweepInput)

        ui.messageBox('Progressiver Coil wurde erfolgreich erstellt!')
    
    except Exception as e:
        if ui:
            ui.messageBox('Fehler:\n{}'.format(traceback.format_exc()))
