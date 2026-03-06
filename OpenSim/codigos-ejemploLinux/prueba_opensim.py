import opensim as osim
import time

def test_visualizer():
    print("Creando modelo de prueba...")
    
    # 1. Crear un modelo vacio
    model = osim.Model()
    model.setName("Prueba_Visualizacion")
    model.setUseVisualizer(True) 

    # 2. Crear un cuerpo (un bloque)
    # Body(nombre, masa, centro_masa, inercia)
    body = osim.Body("bloque", 10.0, osim.Vec3(0), osim.Inertia(1))
    
    # --- AQUÍ ESTABA EL ERROR, LO HE CORREGIDO ---
    # Agregamos la geometría (un ladrillo) sin usar keywords raros
    brick_geom = osim.Brick(osim.Vec3(0.1, 0.1, 0.1))
    brick_geom.setColor(osim.Vec3(1, 0, 0)) # Lo ponemos rojo para verlo mejor
    body.attachGeometry(brick_geom)
    
    model.addBody(body)

    # 3. Crear una articulación (PinJoint) para colgarlo del suelo
    # PinJoint(nombre, padre, loc_padre, ori_padre, hijo, loc_hijo, ori_hijo)
    joint = osim.PinJoint("joint", 
                          model.getGround(), 
                          osim.Vec3(0, 1, 0), 
                          osim.Vec3(0), 
                          body, 
                          osim.Vec3(0, 0, 0), 
                          osim.Vec3(0))
    model.addJoint(joint)

    # 4. Inicializar
    print("Inicializando sistema...")
    state = model.initSystem()

    # 5. Visualizar
    print("Intentando abrir ventana 3D... (Espera unos segundos)")
    
    # Configuramos el manager para simular
    manager = osim.Manager(model)
    manager.initialize(state)
    
    # Simulamos 5 segundos
    # Verás el bloque rojo caer y balancearse
    manager.integrate(5.0)
    print("Prueba finalizada.")

if __name__ == "__main__":
    test_visualizer()
