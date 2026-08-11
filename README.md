# Generador de Moldes en Blender

Addon/script de Python para Blender que genera automáticamente un **molde de dos piezas** (Mold_A / Mold_B) a partir de cualquier objeto 3D importado, con embudo de vertido y llaves de alineación, listo para exportar a STL e imprimir en 3D.

## ¿Qué hace?

A partir de una pieza (malla) ya presente en la escena de Blender, el script genera un panel en la barra lateral del viewport 3D que permite crear, con un clic, un molde de dos mitades para esa pieza:

- **Cavidad** que sigue exactamente la forma de la pieza original.
- **Embudo de vertido** opcional en la parte superior del molde.
- **Llaves de alineación** (pines + huecos) en las 4 esquinas del plano de partición, para que las dos mitades siempre encajen en la misma posición.
- **Exportación automática a STL** de ambas mitades (`mold_A.stl` y `mold_B.stl`), con orientación opcional pensada para imprimir sin necesidad de soportes dentro de la cavidad.

Todos los parámetros (grosor de pared, eje de partición, tamaño de llaves, radio del embudo, carpeta de exportación, etc.) se ajustan desde el panel, sin tocar código.

## Requisitos

- **Blender 4.1 o superior** (usa el exportador STL nuevo `wm.stl_export`). Si tu versión es anterior, el script cae automáticamente al exportador clásico `export_mesh.stl`.
- La pieza a moldear debe ser un objeto de tipo **malla (mesh)**, ya importada en la escena (por ejemplo, vía `Archivo > Importar > STL`).

## Instalación / Uso

1. Importa tu modelo en Blender (`Archivo > Importar > STL` u otro formato compatible).
2. Guarda tu archivo `.blend` al menos una vez, para que la carpeta de exportación relativa (`//mold_stls/`) funcione correctamente.
3. Abre la pestaña **Scripting** en la parte superior de Blender.
4. Abre `main_moldes.py` con **Open**, o copia y pega su contenido en un **Text** nuevo dentro del editor de texto de Blender.
5. Presiona el botón **Run Script** (el triángulo de play). Esto no genera el molde todavía, solo registra el panel y el operador en Blender.
6. Vuelve al viewport 3D, presiona **N** para abrir la barra lateral, y busca la pestaña **"Molde"**.
7. En el panel:
   - Elige tu pieza en el campo **"Pieza"** (o déjalo vacío y selecciona la pieza directamente en la escena antes de generar).
   - Ajusta **grosor de pared**, **eje de partición** (X, Y o Z), embudo de vertido, llaves de alineación y carpeta de exportación según lo necesites.
8. Presiona **"Generar molde"**. Se crean dos objetos nuevos en la escena, `Mold_A` y `Mold_B`, y se exportan automáticamente como STL en la carpeta indicada.

## Parámetros del panel

| Parámetro | Descripción |
|---|---|
| Pieza | Objeto a moldear. Si se deja vacío, usa el objeto seleccionado en la escena. |
| Grosor de pared | Grosor de pared alrededor de la pieza (mismas unidades que tu malla, normalmente mm). |
| Eje de partición | Eje (X, Y o Z) por el que se divide el molde en dos mitades. |
| Agregar embudo | Activa/desactiva el embudo de vertido en la parte superior. |
| Radio de embudo | Radio del embudo de vertido. |
| Radio de llave | Radio de los pines de alineación. |
| Profundidad de llave | Cuánto entra el pin en la otra mitad. |
| Holgura de llave | Holgura extra en el hueco del pin, para que las piezas encajen sin forzar. |
| Orientar Mold_A para impresión | Exporta `mold_A.stl` girado 180° para que el slicer no genere soportes dentro de la cavidad o el embudo (donde quedarían atrapados). El objeto `Mold_A` de la escena no se modifica, solo el STL exportado. |
| Carpeta de exportación | Carpeta donde se guardan `mold_A.stl` y `mold_B.stl` (por defecto `//mold_stls/`, relativa al archivo `.blend`). |

## Notas y solución de problemas

- Si tu pieza es muy pequeña (menos de ~2 cm), reduce **"Radio de llave"** y **"Profundidad de llave"** para que los pines no se salgan de la pared del molde.
- Si vuelves a correr **Run Script** para recargar cambios en el código, el panel se re-registra solo, sin duplicarse.
- Es normal ver `mold_A.stl` "boca abajo" en el slicer (Cura, PrusaSlicer, etc.) respecto a cómo se ve `Mold_A` encajado con `Mold_B` en el viewport de Blender — es intencional, para evitar soportes atrapados dentro de la cavidad.
- Si Blender reporta un error al generar el molde, copia el mensaje completo de la consola/reporte para poder diagnosticarlo.

## Estructura del proyecto

```
GENERADOR DE MOLDES EN BLENDER/
├── main_moldes.py     # Script principal / addon de Blender
├── README.md          # Este manual
├── .gitignore
└── .gitattributes
```

## Estado

Script funcional escrito y documentado, pendiente de verificación dentro de un entorno real de Blender (no se pudo ejecutar Blender durante el desarrollo). Se recomienda probarlo con una pieza sencilla antes de usarlo en modelos complejos o de producción.
