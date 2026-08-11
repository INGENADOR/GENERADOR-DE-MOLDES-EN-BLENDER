"""
Generador de moldes de 2 piezas para Blender
==============================================

QUE HACE
    Toma un objeto (tu pieza, ya importada en la escena) y genera
    automaticamente un molde dividido en dos mitades, con:
      - Una cavidad que sigue exactamente la forma de tu pieza
      - Un embudo de vertido en la parte de arriba (opcional)
      - Llaves de alineacion (pines + huecos) para que las dos
        mitades siempre encajen en la misma posicion
    Al final exporta las dos mitades como archivos STL listos
    para imprimir.

    Los parametros (grosor de pared, eje de particion, tamano de
    las llaves, etc.) se ajustan desde un panel en la barra
    lateral del viewport 3D -- no hace falta tocar el codigo.

COMO USARLO
    1. Importa tu STL en Blender (Archivo > Importar > STL).
    2. Guarda tu archivo .blend al menos una vez (para que la
       carpeta de exportacion relativa funcione bien).
    3. Abre la pestana "Scripting" arriba en Blender.
    4. Abre este archivo con "Open", o pega su contenido en un
       Text nuevo.
    5. Dale al boton Run Script (el triangulo de play). Esto NO
       genera el molde todavia -- solo registra el panel.
    6. Vuelve al viewport 3D, presiona "N" para abrir la barra
       lateral, y busca la pestana "Molde".
    7. Elige tu pieza en el campo "Pieza" (o dejalo vacio y
       selecciona la pieza directamente en la escena).
    8. Ajusta los demas valores a gusto.
    9. Dale al boton "Generar molde". Aparecen dos objetos nuevos,
       Mold_A y Mold_B, y se exportan como STL en la carpeta
       indicada.

NOTAS
    - No se pudo probar este script dentro de Blender real (este
      entorno no tiene Blender instalado), asi que la primera vez
      revisalo con calma. Si algo da error, copia el mensaje
      completo y pegalo en el chat -- se resuelve desde ahi.
    - Pensado para Blender 4.1+ (usa el exportador STL nuevo,
      wm.stl_export). Si tu Blender es mas viejo, el script cae
      automaticamente al exportador clasico (export_mesh.stl).
    - Si tu pieza es muy pequena (menos de ~2 cm), baja "Radio de
      llave" y "Profundidad de llave" en el panel para que los
      pines no se salgan de la pared.
    - Si vuelves a correr el script (Run Script) para recargar
      cambios, el panel se re-registra solo sin duplicarse.
    - "Orientar Mold_A para impresion" (activado por defecto) exporta
      mold_A.stl ya girado 180 grados para que el slicer (Cura,
      PrusaSlicer, etc.) no meta soportes dentro de la cavidad ni del
      embudo -- ahi quedarian atrapados y no se podrian sacar. Es
      normal ver mold_A.stl "boca abajo" en el slicer respecto a como
      se ve Mold_A encajado con Mold_B en Blender; el objeto Mold_A de
      la escena no se modifica, solo el STL exportado.
"""

import bpy
import os
import math
from mathutils import Vector


def world_bbox(obj):
    """Bounding box del objeto en coordenadas del mundo -> (min, max)."""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def get_master(context, settings):
    obj = settings.master_object
    if obj is not None:
        if obj.type != 'MESH':
            raise RuntimeError(f"'{obj.name}' no es un objeto tipo malla.")
        return obj
    sel = [o for o in context.selected_objects if o.type == 'MESH']
    if len(sel) == 1:
        return sel[0]
    raise RuntimeError(
        "Selecciona tu pieza en la escena (un solo objeto tipo malla), "
        "o elígela en el campo 'Pieza' del panel."
    )


def make_box(name, mn, mx):
    size = mx - mn
    center = (mn + mx) / 2
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def duplicate(obj, name):
    new_obj = obj.copy()
    new_obj.data = obj.data.copy()
    new_obj.name = name
    bpy.context.collection.objects.link(new_obj)
    return new_obj


def boolean(target, cutter, operation='DIFFERENCE', delete_cutter=True):
    mod = target.modifiers.new("Bool", 'BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    mod.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if delete_cutter:
        bpy.data.objects.remove(cutter, do_unlink=True)


def export_stl(obj, filepath):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        # Exportador nativo, Blender 4.1+
        bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=True)
    except (AttributeError, TypeError):
        try:
            # Exportador clasico (add-on legacy en versiones viejas)
            bpy.ops.export_mesh.stl(filepath=filepath, use_selection=True)
        except AttributeError as e:
            raise RuntimeError(
                "No encontre un operador de exportacion STL en esta version "
                "de Blender. Expórtalo a mano: selecciona el objeto y usa "
                "Archivo > Exportar > STL."
            ) from e
    print(f"  -> Exportado: {filepath}")


def flip_for_print(obj, axis_index):
    """Gira `obj` 180 grados alrededor de `axis_index`, pivotando en su
    propio origen (que coincide con el centro de su cara de particion),
    y hornea la rotacion en la malla.

    Sirve para que la cavidad de Mold_A quede con su lado mas ancho
    hacia arriba al imprimir -- igual que ya le pasa a Mold_B de forma
    natural -- y el slicer no necesite soportes dentro de la cavidad.
    """
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.rotation_euler[axis_index] = math.pi
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)


def generate_mold(context, settings):
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except RuntimeError:
        pass

    master = get_master(context, settings)
    mn, mx = world_bbox(master)
    wall = settings.wall_thickness
    pad = Vector((wall,) * 3)
    outer_mn, outer_mx = mn - pad, mx + pad
    mid = (outer_mn + outer_mx) / 2
    axis_idx = {'X': 0, 'Y': 1, 'Z': 2}[settings.split_axis]

    print("Generando molde...")

    # 1) Caja solida que envuelve la pieza
    mold = make_box("Mold_temp", outer_mn, outer_mx)

    # 2) Restar la pieza para crear la cavidad
    master_copy = duplicate(master, "MasterCopy_temp")
    boolean(mold, master_copy, 'DIFFERENCE')

    # 3) Embudo de vertido, centrado arriba
    if settings.add_spout:
        top_center = Vector(((outer_mn.x + outer_mx.x) / 2,
                              (outer_mn.y + outer_mx.y) / 2,
                              outer_mx.z))
        bpy.ops.mesh.primitive_cone_add(
            radius1=settings.spout_radius * 2, radius2=settings.spout_radius,
            depth=wall * 2, location=top_center
        )
        spout = bpy.context.active_object
        spout.name = "Spout_temp"
        boolean(mold, spout, 'DIFFERENCE')

    # 4) Dividir en dos mitades con cajas cortadoras
    margin = 5.0
    upper_mn = outer_mn - Vector((margin,) * 3)
    upper_mx = outer_mx + Vector((margin,) * 3)
    upper_mn[axis_idx] = mid[axis_idx]

    lower_mn = outer_mn - Vector((margin,) * 3)
    lower_mx = outer_mx + Vector((margin,) * 3)
    lower_mx[axis_idx] = mid[axis_idx]

    mold_a = duplicate(mold, "Mold_A")   # sera la mitad de ARRIBA
    mold_b = duplicate(mold, "Mold_B")   # sera la mitad de ABAJO
    bpy.data.objects.remove(mold, do_unlink=True)

    cutter_upper = make_box("CutterUpper_temp", upper_mn, upper_mx)
    boolean(mold_b, cutter_upper, 'DIFFERENCE')   # a B le quitamos arriba

    cutter_lower = make_box("CutterLower_temp", lower_mn, lower_mx)
    boolean(mold_a, cutter_lower, 'DIFFERENCE')   # a A le quitamos abajo

    # 5) Llaves de alineacion en las 4 esquinas del plano de particion
    other_axes = [i for i in range(3) if i != axis_idx]
    a0, a1 = other_axes
    m = wall * 0.6
    lo = [outer_mn[a0] + m, outer_mn[a1] + m]
    hi = [outer_mx[a0] - m, outer_mx[a1] - m]

    # El cilindro por defecto queda con su eje en Z; hay que rotarlo para
    # que apunte a lo largo del eje de particion y realmente atraviese el
    # plano de corte (si no, el pin queda plano justo sobre el corte).
    key_rotation = {
        0: (0.0, math.radians(90.0), 0.0),  # eje X
        1: (math.radians(90.0), 0.0, 0.0),  # eje Y
        2: (0.0, 0.0, 0.0),                 # eje Z
    }[axis_idx]

    for i, (u, v) in enumerate([(lo[0], lo[1]), (lo[0], hi[1]),
                                  (hi[0], lo[1]), (hi[0], hi[1])]):
        pos = Vector((0.0, 0.0, 0.0))
        pos[a0], pos[a1] = u, v
        pos[axis_idx] = mid[axis_idx]

        # Pin solido -> se une a la mitad B
        bpy.ops.mesh.primitive_cylinder_add(
            radius=settings.key_radius, depth=settings.key_depth * 2,
            location=pos, rotation=key_rotation
        )
        pin = bpy.context.active_object
        pin.name = f"Pin_{i}_temp"
        boolean(mold_b, pin, 'UNION')

        # Hueco un poco mas ancho -> se resta de la mitad A (con holgura)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=settings.key_radius + settings.key_clearance,
            depth=settings.key_depth * 2, location=pos, rotation=key_rotation
        )
        socket = bpy.context.active_object
        socket.name = f"Socket_{i}_temp"
        boolean(mold_a, socket, 'DIFFERENCE')

    # 6) Exportar a STL
    export_dir = settings.export_dir or "//mold_stls/"
    export_dir_abs = bpy.path.abspath(export_dir)
    if not bpy.data.filepath and export_dir.startswith("//"):
        export_dir_abs = os.path.join(os.path.expanduser("~"), "mold_stls")
        print(f"Aviso: guarda tu archivo .blend para usar rutas relativas. "
              f"Exportando en su lugar a: {export_dir_abs}")
    os.makedirs(export_dir_abs, exist_ok=True)

    # Mold_B ya queda naturalmente con la cavidad abierta hacia arriba
    # (lado ancho arriba, angosto abajo), asi que se exporta tal cual.
    # Mold_A es al reves: su cavidad se abre hacia abajo, y si se
    # imprime tal cual el slicer mete soportes DENTRO de la cavidad
    # (y del embudo) que despues no se pueden sacar. Por eso, para
    # exportar, se usa una copia de Mold_A girada 180 grados -- el
    # objeto Mold_A de la escena no se toca, sigue encajando con
    # Mold_B tal como se ve en el visor 3D.
    if settings.orient_for_printing:
        export_a = duplicate(mold_a, "Mold_A_print_temp")
        flip_for_print(export_a, a0)
    else:
        export_a = mold_a

    export_stl(export_a, os.path.join(export_dir_abs, "mold_A.stl"))
    if export_a is not mold_a:
        bpy.data.objects.remove(export_a, do_unlink=True)

    export_stl(mold_b, os.path.join(export_dir_abs, "mold_B.stl"))

    print("Listo! Molde generado: Mold_A (arriba) y Mold_B (abajo).")
    if settings.orient_for_printing:
        print("  Nota: mold_A.stl se exporto girado 180 grados a proposito "
              "para imprimir sin soportes internos. Es normal que en el "
              "slicer se vea 'boca abajo' respecto a Mold_B en Blender.")


# ============================================================
# INTERFAZ -- panel en la barra lateral del viewport 3D
# ============================================================

class MoldSettings(bpy.types.PropertyGroup):
    master_object: bpy.props.PointerProperty(
        name="Pieza",
        description="Objeto a moldear. Vacio = usa el objeto seleccionado en la escena",
        type=bpy.types.Object,
    )
    wall_thickness: bpy.props.FloatProperty(
        name="Grosor de pared",
        description="Grosor de pared alrededor de la pieza, en las mismas unidades que tu malla (normalmente mm)",
        default=6.0, min=0.1,
    )
    split_axis: bpy.props.EnumProperty(
        name="Eje de particion",
        description="Eje por el que se parte el molde en dos mitades",
        items=[
            ('X', "X", "Partir por el eje X"),
            ('Y', "Y", "Partir por el eje Y"),
            ('Z', "Z", "Partir por el eje Z (arriba / abajo)"),
        ],
        default='Z',
    )
    key_radius: bpy.props.FloatProperty(
        name="Radio de llave",
        description="Radio de los pines de alineacion",
        default=3.0, min=0.1,
    )
    key_depth: bpy.props.FloatProperty(
        name="Profundidad de llave",
        description="Cuanto entra el pin en la otra mitad",
        default=5.0, min=0.1,
    )
    key_clearance: bpy.props.FloatProperty(
        name="Holgura de llave",
        description="Holgura extra en el hueco del pin",
        default=0.15, min=0.0,
    )
    add_spout: bpy.props.BoolProperty(
        name="Agregar embudo",
        description="Agrega un embudo de vertido en la parte de arriba",
        default=True,
    )
    spout_radius: bpy.props.FloatProperty(
        name="Radio de embudo",
        description="Radio del embudo de vertido",
        default=5.0, min=0.1,
    )
    export_dir: bpy.props.StringProperty(
        name="Carpeta de exportacion",
        description="Carpeta donde se guardan mold_A.stl y mold_B.stl",
        default="//mold_stls/",
        subtype='DIR_PATH',
    )
    orient_for_printing: bpy.props.BoolProperty(
        name="Orientar Mold_A para impresion (evita soportes internos)",
        description=(
            "Exporta mold_A.stl usando una copia girada 180 grados, para "
            "que la cavidad quede con el lado ancho hacia arriba (como ya "
            "le pasa a Mold_B) y el slicer no meta soportes dentro de la "
            "cavidad o del embudo, donde quedarian atrapados. El objeto "
            "Mold_A que ves en la escena no se modifica"
        ),
        default=True,
    )


class MOLD_OT_generate(bpy.types.Operator):
    bl_idname = "mold.generate"
    bl_label = "Generar molde"
    bl_description = "Genera las dos mitades del molde y las exporta a STL"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.mold_settings
        try:
            generate_mold(context, settings)
        except RuntimeError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        self.report({'INFO'}, "Molde generado y exportado correctamente.")
        return {'FINISHED'}


class MOLD_PT_panel(bpy.types.Panel):
    bl_label = "Generador de moldes"
    bl_idname = "MOLD_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Molde"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.mold_settings

        layout.prop(settings, "master_object")

        box = layout.box()
        box.label(text="Molde")
        box.prop(settings, "wall_thickness")
        box.prop(settings, "split_axis")

        box = layout.box()
        box.label(text="Embudo de vertido")
        box.prop(settings, "add_spout")
        sub = box.column()
        sub.enabled = settings.add_spout
        sub.prop(settings, "spout_radius")

        box = layout.box()
        box.label(text="Llaves de alineacion")
        box.prop(settings, "key_radius")
        box.prop(settings, "key_depth")
        box.prop(settings, "key_clearance")

        box = layout.box()
        box.label(text="Impresion 3D")
        box.prop(settings, "orient_for_printing")

        layout.prop(settings, "export_dir")

        layout.separator()
        layout.operator("mold.generate", icon='MOD_BOOLEAN')


classes = (
    MoldSettings,
    MOLD_OT_generate,
    MOLD_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mold_settings = bpy.props.PointerProperty(type=MoldSettings)


def unregister():
    del bpy.types.Scene.mold_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    try:
        unregister()
    except (RuntimeError, AttributeError):
        pass
    register()
