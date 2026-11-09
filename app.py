from flask import Flask, render_template, request, session, redirect, url_for, abort
import os
import pymysql
import ssl
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal, InvalidOperation

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

    conexao = conectar_banco()

    try:
        with conexao.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT id, nome, descricao, cidade, uf
                FROM pontos_turisticos
                WHERE status = %s
                ORDER BY id DESC
            """, ("pendente",))

            pontos = cursor.fetchall()

    finally:
        conexao.close()

    return render_template("admin.html", pontos=pontos)


@app.route("/cadastrar-ponto", methods=["POST"])
def cadastrar_ponto():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip()
    uf = request.form.get("uf", "")
    codigo_ibge = request.form.get("codigo_ibge", "")

    cidade = request.form.get("cidade", "").strip()

    latitude = request.form.get("latitude", "")
    longitude = request.form.get("longitude", "")

    if not all([nome, descricao, uf, cidade, codigo_ibge, latitude, longitude]):
        return "Preencha todos os campos e selecione um local no mapa.", 400

    try:
        latitude = Decimal(latitude)
        longitude = Decimal(longitude)
        codigo_ibge = int(codigo_ibge)
    except (InvalidOperation, ValueError, TypeError):
        return "Coordenadas ou código IBGE inválidos.", 400

    if not (latitude.is_finite() and longitude.is_finite()):
        return "Coordenadas inválidas.", 400

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return "Localização inválida.", 400

    if len(nome) > 150 or len(cidade) > 150 or len(uf) != 2:
        return "Nome, cidade ou estado inválido.", 400

    if codigo_ibge <= 0:
        return "Código IBGE inválido.", 400

    conexao = conectar_banco()

    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pontos_turisticos
                (usuario_id, nome, descricao, uf, cidade,
                 codigo_ibge, latitude, longitude, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["usuario_id"],
                    nome,
                    descricao,
                    uf,
                    cidade,
                    codigo_ibge,
                    latitude,
                    longitude,
                    "pendente"
                )
            )

        conexao.commit()
        return "Ponto turístico enviado para aprovação!", 201

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao cadastrar ponto turístico")
        return "Erro ao salvar o ponto turístico.", 500

    finally:
        conexao.close()

@app.route("/admin/aprovar/<int:ponto_id>", methods=["POST"])
def aprovar_ponto(ponto_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("perfil") != "admin":
        abort(403)

    conexao = conectar_banco()

    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pontos_turisticos
                SET status = %s
                WHERE id = %s AND status = %s
                """,
                ("aprovado", ponto_id, "pendente")
            )

        conexao.commit()

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao aprovar ponto turístico")
        return "Erro ao aprovar o ponto turístico.", 500

    finally:
        conexao.close()

    return redirect(url_for("painel_admin"))

@app.route("/admin/rejeitar/<int:ponto_id>", methods=["POST"])
def rejeitar_ponto(ponto_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    if session.get("perfil") != "admin":
        abort(403)

    conexao = conectar_banco()

    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pontos_turisticos
                SET status = %s
                WHERE id = %s AND status = %s
                """,
                ("rejeitado", ponto_id, "pendente")
            )

        conexao.commit()

    except Exception:
        conexao.rollback()
        app.logger.exception("Erro ao rejeitar ponto turístico")
        return "Erro ao rejeitar o ponto turístico.", 500

    finally:
        conexao.close()

    return redirect(url_for("painel_admin"))


if __name__ == '__main__':
    app.run(debug=True)
