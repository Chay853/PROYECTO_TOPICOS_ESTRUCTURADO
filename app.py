from datetime import timedelta
import os
from flask import Flask, render_template,request,session,redirect,url_for, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
from werkzeug.utils import secure_filename
from functools import wraps
import traceback

app = Flask(__name__)
app.secret_key = "david"
app.permanent_session_lifetime = timedelta(days=1)

# Configuración para almacenar imágenes
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def get_bd_connection():
    return mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "",
        database = "tienda_da"

    )

# Función para verificar extensiones de archivos permitidas
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#funcion que hace que requiera que seas admin y protega los privilegios del admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session or session.get("tipo") != "admin":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def usuario_required(g):
    @wraps(g)
    def decorated_function(*args, **kwargs):
        if "usuario" not in session or session.get("tipo") != "usuario":
            return redirect(url_for("login"))
        return g(*args, **kwargs)
    return decorated_function


@app.route('/')# para mostrar la tabla en index, se borra en caso de no funcionar
def home():
    conn = get_bd_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jerseys")
    miresultado = cursor.fetchall()

    # Convertir los datos a diccionario
    insertObject = []
    columnNames = [column[0] for column in cursor.description]
    for record in miresultado:
        insertObject.append(dict(zip(columnNames, record)))

    cursor.close()
    conn.close()
    return render_template("index.html", dato=insertObject)# muestra index.html  



#Ruta o clases para el login, administradores y usuarios

#ruta para crear administradores es temporal ya que los admin ya estan completos y agregados
@app.route('/crear_admin')
@admin_required
def crear_admin():
    LIMITE_ADMINS = 2  # Puedes cambiar este número, es la cantidad de admin que permite

    conn = get_bd_connection()
    cursor = conn.cursor(dictionary=True)

    # Contar cuántos administradores hay
    cursor.execute("SELECT COUNT(*) AS total FROM usuario WHERE tipo = 'admin'")
    cantidad_admins = cursor.fetchone()["total"]

    if cantidad_admins >= LIMITE_ADMINS:
        cursor.close()
        conn.close()
        return "<h3>🔒 Límite de administradores alcanzado. No se pueden crear más.</h3>"

    # Crear un nuevo admin genérico
    nuevo_nombre = f"David"
    nuevo_correo = f"may876518@gmail.com"
    contraseña = "admin123"
    contraseña_hasheada = generate_password_hash(contraseña)

    try:
        cursor.execute(
            "INSERT INTO usuario (nombre, correo, contraseña, tipo) VALUES (%s, %s, %s, %s)",
            (nuevo_nombre, nuevo_correo, contraseña_hasheada, "admin")
        )
        conn.commit()
        mensaje = f" Admin creado: {nuevo_correo} / {contraseña}"
    except Exception as e:
        mensaje = f" Error al crear el admin: {e}"
    finally:
        cursor.close()
        conn.close()

    return f"<h3>{mensaje}</h3>"


#Para registrar a nuevos usuarios o personas
@app.route("/registro", methods=["GET","POST"])
def registro():
    if request.method == "POST":
        Nombre = request.form["nombre"]
        Correo = request.form["correo"]
        Contraseña = request.form["contraseña"]

        contraseña_hasheada = generate_password_hash(Contraseña)

        conn =  get_bd_connection()
        cursor = conn.cursor()
        #insertar nuevo usuario 
        try:
            cursor.execute("INSERT INTO usuario (nombre, correo, contraseña) VALUES (%s, %s, %s)",
                           (Nombre, Correo, contraseña_hasheada))
            conn.commit()
            return redirect(url_for("login"))
        except mysql.connector.Error as err:
            return render_template("registro.html", error="El correo ya está registrado")
        finally:
            cursor.close()
            conn.close()
    return render_template("registro.html")


#Para loguear al usuario o admin
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["correo"]
        password = request.form["contraseña"]

        conn = get_bd_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuario WHERE correo = %s",(email,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()

        #en este caso usuario es el tipo rol que tendra, ya que tambien mi base de datos se llama usuario para no confundir
        if usuario and check_password_hash(usuario["contraseña"],password):
            if request.form.get("remember"): #si se marca el checbox
                session.permanent = True
            else:
                session.permanent = False

            session["usuario"] = usuario["id_u"]
            session["nombre"] = usuario["nombre"]
            session["tipo"] = usuario ["tipo"]
            if usuario ["tipo"] == "admin":
                return redirect(url_for("admin"))
            else:
                return redirect(url_for("usuario")) 
        else:
            return render_template("login.html", error="Datos incorrectos")
    return render_template('login.html')  # muestra login.html

#ruta para el inicio de session de usuarios normales
@app.route("/usuario")
def usuario():
    if "usuario" in session and session.get("tipo")=="usuario":
        conn = get_bd_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jerseys")
        miresultado = cursor.fetchall()

        # Convertir los datos a diccionario
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in miresultado:
            insertObject.append(dict(zip(columnNames, record)))

        cursor.close()
        conn.close()
        return render_template("usuario.html", session=session, dato = insertObject)
    return redirect(url_for("login"))

#ruta para proteger el inicio de sesion del admin
@app.route("/admin")
def admin():
    if "usuario" in session and session.get("tipo")=="admin":
        conn = get_bd_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jerseys")
        miresultado = cursor.fetchall()

        # Convertir los datos a diccionario
        insertObject = []
        columnNames = [column[0] for column in cursor.description]
        for record in miresultado:
            insertObject.append(dict(zip(columnNames, record)))

        cursor.close()
        conn.close()
        return render_template("admin.html", session=session, dato=insertObject)
    return redirect(url_for("login"))



@app.route("/logouta")
def logouta():
    session.pop("tipo", None)
    return redirect(url_for("home"))


#Clases o rutas donde se realiza el crud

#clase para agregar los productos en admin
@app.route("/agregar", methods=["POST"])
@admin_required
def agregar():
    Nombre = request.form["nombre_p"]
    Cantidad = int(request.form["cantidad_p"])
    Descripcion = request.form["descripcion"]
    Precio = float(request.form["precio_p"])

    if "imagen" in request.files:
        file = request.files["imagen"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        else:
            filename = "default.jpg"
    else:
        filename = "default.jpg"

    conn = get_bd_connection()
    cursor = conn.cursor(dictionary=True)

    # Comparación sin distinguir mayúsculas/minúsculas
    cursor.execute("SELECT * FROM jerseys WHERE LOWER(nombre_p) = LOWER(%s)", (Nombre,))
    existente = cursor.fetchone()

    if existente:
        cursor.close()
        conn.close()
        return render_template("agregar_producto.html", error="⚠️ El producto ya existe y no se puede volver a agregar.")

    cursor.execute(
        "INSERT INTO jerseys (nombre_p, cantidad_p, descripcion, precio_p, imagen) VALUES (%s, %s, %s, %s, %s)",
        (Nombre, Cantidad, Descripcion, Precio, filename)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("home"))



#ruta para iniciar el html de los productos a agregar
@app.route("/agregar_producto", methods=["GET"])
def form_agregar_producto():
    if "usuario" in session and session.get("tipo") == "admin":
        return render_template("agregar_producto.html")
    return redirect(url_for("login"))

#clase donde busca el producto y ahi mismo edita y eliminar
@app.route("/buscar_producto", methods=["GET", "POST"])
@admin_required
def buscar_producto():
    productos = []
    mensaje = ""
    #verifica que el usuario este logiado como admin
    if "usuario" not in session or session.get("tipo") != "admin":
        return redirect(url_for("login"))

    conn = get_bd_connection()
    cursor = conn.cursor(dictionary=True)
    

    if request.method == "POST":
        if "buscar" in request.form:
            nombre_busqueda = request.form["nombre_busqueda"]
            cursor.execute("SELECT * FROM jerseys WHERE nombre_p LIKE %s", (f"%{nombre_busqueda}%",))
            productos = cursor.fetchall()
            #Aqui es donde se actualizaran los datos una vez los busque
        elif "actualizar" in request.form:
            id = request.form["id_p"]
            nombre = request.form["nombre_p"]
            cantidad = int(request.form["cantidad_p"])
            descripcion = request.form["descripcion"]
            precio = Decimal(request.form["precio_p"])

            if "imagen" in request.files and request.files["imagen"].filename != "":
                imagen = request.files["imagen"]
                if allowed_file(imagen.filename):
                    filename = secure_filename(imagen.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    imagen.save(file_path)

                    cursor.execute("""UPDATE jerseys SET nombre_p=%s, cantidad_p=%s, descripcion=%s, precio_p=%s, imagen=%s WHERE id_p=%s""",
                                   (nombre, cantidad, descripcion, precio, filename, id))
            else:
                cursor.execute("""UPDATE jerseys SET nombre_p=%s, cantidad_p=%s, descripcion=%s, precio_p=%s WHERE id_p=%s""",
                               (nombre, cantidad, descripcion, precio, id))
            conn.commit()
            mensaje = "Producto actualizado correctamente ✅"
        #Aqui si ya esta encontrado el producto podra eliminarlo de igual manera
        elif "eliminar" in request.form:
            id = request.form["id_p"]

            # Verificar si el producto está en algún pedido
            cursor.execute("SELECT COUNT(*) AS total FROM pedido_items WHERE id_p = %s", (id,))
            resultado = cursor.fetchone()

            if resultado["total"] > 0:
                mensaje = "❌ No se puede eliminar este producto porque ya ha sido registrado en pedidos realizados."
            else:
                cursor.execute("DELETE FROM jerseys WHERE id_p=%s", (id,))
                conn.commit()
                mensaje = "Producto eliminado ❌"
                    # Mostrar todos los productos si aún no se ha hecho una búsqueda
    if not productos:
        cursor.execute("SELECT * FROM jerseys")
        productos = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("buscar_producto.html", productos=productos, mensaje=mensaje)




#Clases o rutas destinadas al carrito

#ruta para que valide que le carrito este limpio
def limpiar_carrito(carrito):
    """Elimina entradas inválidas del carrito"""
    carrito_limpio = {}
    for key, item in carrito.items():
        if isinstance(item, dict) and "precio_p" in item and "cantidad" in item:
            carrito_limpio[key] = item
    return carrito_limpio


#ruta para el carrito
@app.route('/agregar_carrito/<int:id_p>', methods=["POST"])
@usuario_required
def agregar_al_carrito(id_p):
    conn = get_bd_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM jerseys WHERE id_p = %s", (id_p,))
    producto = cursor.fetchone()
    cursor.close()
    conn.close()

    if producto:
        carrito = session.get('carrito', {})
        id_str = str(producto['id_p'])

        stock_disponible = producto['cantidad_p']
        cantidad_actual = carrito.get(id_str, {}).get('cantidad', 0)

        if cantidad_actual < stock_disponible:
            if id_str in carrito and isinstance(carrito[id_str], dict):
                carrito[id_str]['cantidad'] += 1
            else:
                carrito[id_str] = {
                    'id_p': producto['id_p'],
                    'nombre_p': producto['nombre_p'],
                    'precio_p': float(producto['precio_p']),
                    'cantidad': 1
                }
            session['carrito'] = carrito
        else:
            flash("No hay suficiente stock para agregar más unidades de este producto.", "warning")

    return redirect(url_for('home'))


#ruta para mostrar el carrito
@app.route('/carrito')
@usuario_required
def ver_carrito():
    carrito = session.get('carrito', {})
    total = 0

    # Asegurarse que todo en el carrito tenga la estructura correcta
    carrito_limpio = {}
    for key, item in carrito.items():
        if isinstance(item, dict) and "precio_p" in item and "cantidad" in item:
            try:
                total += item["precio_p"] * item["cantidad"]
                carrito_limpio[key] = item
            except Exception as e:
                print(f"Error en item del carrito: {item} - {e}")

    # Reemplazar el carrito dañado con uno limpio
    session["carrito"] = carrito_limpio

    return render_template('carrito.html', carrito=carrito_limpio, total=total)

#ruta para eliminar productos en el carrito
@app.route("/eliminar_del_carrito/<int:id_p>")
def eliminar_del_carrito(id_p):
    carrito = session.get("carrito", {})
    id_str = str(id_p)
    if id_str in carrito:
        del carrito[id_str]
        session["carrito"] = carrito
    return redirect(url_for("ver_carrito"))

#ruta para vaciar todo el carrito
@app.route("/vaciar_carrito")
def vaciar_carrito():
    session.pop("carrito", None)
    return redirect(url_for("ver_carrito"))

#ruta para aumentar la cantidad del producto
@app.route('/aumentar_cantidad/<int:id_p>')
def aumentar_cantidad(id_p):
    carrito = limpiar_carrito(session.get("carrito", {}))
    id_str = str(id_p)

    conn = get_bd_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT cantidad_p FROM jerseys WHERE id_p = %s", (id_p,))
    producto = cursor.fetchone()
    cursor.close()
    conn.close()

    if id_str in carrito:
        if carrito[id_str]["cantidad"] < producto["cantidad_p"]:
            carrito[id_str]["cantidad"] += 1
            session["carrito"] = carrito
        else:
            flash("No puedes agregar más, no hay suficiente stock.", "warning")

    return redirect(url_for("ver_carrito"))


#ruta para disminuir la cantidad del producto
@app.route('/disminuir_cantidad/<int:id_p>')
def disminuir_cantidad(id_p):
    carrito = limpiar_carrito(session.get("carrito", {}))
    id_str = str(id_p)
    if id_str in carrito:
        if carrito[id_str]["cantidad"] > 1:
            carrito[id_str]["cantidad"] -= 1
        else:
            del carrito[id_str]  # Si baja de 1, se elimina el producto del carrito
        session["carrito"] = carrito
    return redirect(url_for("ver_carrito"))

#ruta para realizar la compra
@app.route('/realizar_compra')
@usuario_required
def realizar_compra():
     # 1 Obtener usuario y carrito
    id_u = session.get("usuario")
    carrito = session.get("carrito", {})
    if not carrito:
        flash("Tu carrito está vacío.", "warning")
        return redirect(url_for("ver_carrito"))

    conn = get_bd_connection()
    cursor = conn.cursor()

    try:
        # 2 Validar stock de cada ítem
        for item in carrito.values():
            cursor.execute(
                "SELECT cantidad_p FROM jerseys WHERE id_p = %s",
                (item['id_p'],)
            )
            stock = cursor.fetchone()[0]
            if stock < item['cantidad']:
                flash(f"No hay suficiente stock para “{item['nombre_p']}”.", "warning")
                return redirect(url_for("ver_carrito"))

        # 3 Crear registro en pedidos
        total = sum(item["precio_p"] * item["cantidad"] for item in carrito.values())
        cursor.execute(
            "INSERT INTO pedidos (id_u, total) VALUES (%s, %s)",
            (id_u, total)
        )
        id_pedido = cursor.lastrowid

        # 4 Insertar cada detalle y restar stock
        for item in carrito.values():
            cursor.execute(
                """
                INSERT INTO pedido_items
                  (id_pedido, id_p, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s)
                """,
                (id_pedido, item['id_p'], item['cantidad'], item['precio_p'])
            )
            cursor.execute(
                "UPDATE jerseys SET cantidad_p = cantidad_p - %s WHERE id_p = %s",
                (item['cantidad'], item['id_p'])
            )

        conn.commit()

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error al procesar compra: {e}")
        flash("Ocurrió un error al procesar tu compra.", "danger")
        return redirect(url_for("ver_carrito"))

    finally:
        cursor.close()
        conn.close()

    # 5 Preparar datos para la vista
    detalles = [
        {
            'nombre': item['nombre_p'],
            'cantidad': item['cantidad'],
            'precio_unitario': item['precio_p'],
            'subtotal': item['precio_p'] * item['cantidad']
        }
        for item in carrito.values()
    ]
    session.pop("carrito", None)

    return render_template(
        "compra_exitosa.html",
        id_pedido=id_pedido,
        detalles=detalles,
        total=total
    )

#ruta de nosotros 
@app.route('/nosotros')
@usuario_required
def nosotros():
    if "usuario" not in session or session.get("tipo") != "usuario":
        return redirect(url_for("login"))
    return render_template("nosotros.html")

#ruta para compra exitosa
@app.route('/compra_producto')
def compra():
    return render_template("compra_exitosa.html")


#ruta para limpiar sesion cuando tenga basura la session
@app.route('/limpiar_sesion')
def limpiar_sesion():
    session.clear()
    return "Sesión limpiada"

#Para arrancar el entorno
if __name__ == '__main__':
    app.run(debug=True)
