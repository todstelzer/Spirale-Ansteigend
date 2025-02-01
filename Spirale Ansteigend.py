import adsk.core, adsk.fusion, adsk.cam, math, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        # Zugriff auf Fusion 360
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent


        # ---------------------------------------------------
        # Parameter für den progressiven Coil
        # ---------------------------------------------------
        turns = 5
        points_per_turn = 30
        total_points = turns * points_per_turn + 1

        start_radius = 5.0   # z. B. 5 mm
        end_radius   = 10.0  # z. B. 10 mm (progressiv größer)
        start_pitch  = 2.0   # Erhöht auf 2.0 mm/Umdrehung um Selbstüberschneidung zu vermeiden
        end_pitch    = 5.0   # Endsteigung (mm/Umdrehung)
        wire_diameter = 1.3  # Reduziert auf 0.3 mm Durchmesser

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
