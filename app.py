from flask import Flask, render_template, request, session, redirect, url_for, abort
import os
import pymysql
import ssl
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

def conectar_banco():
    contexto_ssl = ssl.create_default_context(cafile="ca.pem")
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        ssl=contexto_ssl,
        connect_timeout=10)


@app.route('/')
def inicio():
        return render_template(
        "inicio.html",
        logado="usuario_id" in session
    )

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/teste-banco")
def teste_banco():
    conexao = conectar_banco()
    try:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT 1")
            resultado = cursor.fetchone()
        return f"Conexão funcionando! Resultado: {resultado[0]}"
    finally:
        conexao.close()

@app.route("/teste-usuarios")
def teste_usuarios():
    conexao = conectar_banco()

    try:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            resultado = cursor.fetchone()

        return f"Usuários cadastrados: {resultado[0]}"

    finally:
        conexao.close()

@app.route("/cadastro", methods=["POST"])
def cadastrar_usuario():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    senha = request.form.get("senha", "")

    if not nome or not email or len(senha) < 8:
        return "Preencha os campos corretamente.", 400
    
        email = email.lower()
    senha_protegida = generate_password_hash(senha)

    conexao = conectar_banco()

    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (%s, %s, %s, %s)",
                (nome, email, senha_protegida, "usuario")
            )

        conexao.commit()
        return "Usuário cadastrado com sucesso!", 201

    except pymysql.err.IntegrityError:
        conexao.rollback()
        return "Este e-mail já está cadastrado.", 409

    finally:
        conexao.close()

@app.route("/entrar", methods=["POST"])
def entrar():
    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")

    conexao = conectar_banco()

    try:
        with conexao.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT id, nome, senha_hash, perfil FROM usuarios WHERE email = %s",
                (email,)
            )
            usuario = cursor.fetchone()
    finally:
        conexao.close()

    if not usuario or not check_password_hash(usuario["senha_hash"], senha):
        return "E-mail ou senha incorretos.", 401

    session.clear()
    session["usuario_id"] = usuario["id"]
    session["perfil"] = usuario["perfil"]

    return redirect(url_for("inicio"))

@app.route("/sair", methods=["POST"])
def sair():
    session.clear()
    return redirect(url_for("inicio"))

@app.route("/pontos")
def meus_pontos():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    return render_template("pontos.html")

@app.route("/admin")
def painel_admin():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("perfil") != "admin":
        abort(403)

    return render_template("admin.html")

if __name__ == '__main__':
    app.run(debug=True)







