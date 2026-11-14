from flask import Flask, render_template, request, session, redirect, url_for, abort
from flask_wtf.csrf import CSRFProtect
import os
import json
import gzip
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from io import BytesIO
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
import pymysql
import ssl
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal, InvalidOperation

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
csrf = CSRFProtect(app)
PASTA_FOTOS = os.path.join(app.static_folder, "uploads")
os.makedirs(PASTA_FOTOS, exist_ok=True)

TAMANHO_MAXIMO_FOTO = 5 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024


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

    if len(nome) > 150 or len(cidade) > 150:
        return "Nome ou cidade muito longo.", 400

    if len(uf) != 2 or not uf.isalpha():
        return "Sigla do estado inválida.", 400

    uf = uf.upper()

    if codigo_ibge < 1000000 or codigo_ibge > 9999999:
        return "Código IBGE inválido.", 400

    if len(descricao) > 2000:
        return "A descrição deve ter no máximo 2000 caracteres.", 400

    url_ibge = (
    f"https://servicodados.ibge.gov.br/api/v1/"
    f"localidades/estados/{uf}/municipios"
    )

    try:
        with urlopen(url_ibge, timeout=5) as resposta:
            conteudo_ibge = resposta.read()

            if conteudo_ibge.startswith(b"\x1f\x8b"):
                conteudo_ibge = gzip.decompress(conteudo_ibge)

            municipios = json.loads(conteudo_ibge.decode("utf-8"))

    except HTTPError as erro:
        app.logger.error("Erro HTTP na API do IBGE: %s", erro)

        if erro.code == 404:
            return "Estado inválido.", 400

        return "Não foi possível consultar o IBGE.", 503

    except (URLError, TimeoutError, ValueError) as erro:
        app.logger.error("Erro ao consultar o IBGE: %s", erro)
        return "Não foi possível consultar o IBGE.", 503


    cidade_valida = any(
        municipio["id"] == codigo_ibge
        and municipio["nome"].casefold() == cidade.casefold()
        for municipio in municipios
    )

    if not cidade_valida:
        return "Estado, cidade ou código IBGE não correspondem.", 400

    foto = request.files.get("foto")
    nome_foto = None
    caminho_foto = None

    if foto and foto.filename:

        conteudo = foto.read(TAMANHO_MAXIMO_FOTO + 1)

        if len(conteudo) > TAMANHO_MAXIMO_FOTO:
            return "A fotografia deve ter no máximo 5 MB.", 400

        try:
            with Image.open(BytesIO(conteudo)) as imagem:
                formato = imagem.format
                imagem.verify()

        except (UnidentifiedImageError, OSError, ValueError):
            return "Arquivo de imagem inválido.", 400

        if formato not in ("JPEG", "PNG"):
            return "Envie uma fotografia JPG ou PNG.", 400

        extensao = ".jpg" if formato == "JPEG" else ".png"

        nome_foto = f"{uuid4().hex}{extensao}"
        caminho_foto = os.path.join(PASTA_FOTOS, nome_foto)

    conexao = conectar_banco()

    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pontos_turisticos
                (usuario_id, nome, descricao, uf, cidade,
                 codigo_ibge, latitude, longitude, status, foto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    "pendente",
                    f"uploads/{nome_foto}" if nome_foto else None
                )
            )

        if caminho_foto:
            with open(caminho_foto, "wb") as arquivo:
                arquivo.write(conteudo)

        conexao.commit()
        return "Ponto turístico enviado para aprovação!", 201

    except Exception:
        conexao.rollback()

        if caminho_foto and os.path.exists(caminho_foto):
            os.remove(caminho_foto)

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


@app.route("/api/pontos")
def listar_pontos():
    conexao = conectar_banco()

    try:
        with conexao.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT
                    p.id,
                    p.nome,
                    p.descricao,
                    p.cidade,
                    p.uf,
                    p.codigo_ibge,
                    p.latitude,
                    p.longitude,
                    p.foto,
                    ROUND(AVG(a.estrelas), 1) AS media,
                    COUNT(a.id) AS quantidade_avaliacoes
                FROM pontos_turisticos p
                LEFT JOIN avaliacoes a
                    ON p.id = a.ponto_id
                WHERE p.status = %s
                GROUP BY
                    p.id, p.nome, p.descricao, p.cidade, p.uf,
                    p.codigo_ibge, p.latitude, p.longitude, p.foto
            """, ("aprovado",))

            pontos = cursor.fetchall()

    finally:
        conexao.close()

    return {"pontos": pontos}


@app.route("/ponto/<int:ponto_id>")
def detalhes_ponto(ponto_id):
    conexao = conectar_banco()

    try:
        with conexao.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT id, nome, descricao, cidade, uf,
                       latitude, longitude, foto
                FROM pontos_turisticos
                WHERE id = %s AND status = %s
            """, (ponto_id, "aprovado"))

            ponto = cursor.fetchone()

            # Buscar avaliações do ponto turístico
            cursor.execute("""
                SELECT usuarios.nome, avaliacoes.estrelas,
                       avaliacoes.comentario
                FROM avaliacoes
                INNER JOIN usuarios
                    ON avaliacoes.usuario_id = usuarios.id
                WHERE avaliacoes.ponto_id = %s
                ORDER BY avaliacoes.id DESC
            """, (ponto_id,))

            avaliacoes = cursor.fetchall()

            ja_avaliou = False

            if "usuario_id" in session:
                cursor.execute("""
                    SELECT id
                    FROM avaliacoes
                    WHERE usuario_id = %s AND ponto_id = %s
                """, (session["usuario_id"], ponto_id))

                ja_avaliou = cursor.fetchone() is not None

    finally:
        conexao.close()

    if not ponto:
        abort(404)

    # Calcular média das avaliações
    quantidade = len(avaliacoes)

    if quantidade > 0:
        media = sum(
            avaliacao["estrelas"] for avaliacao in avaliacoes
        ) / quantidade
    else:
        media = 0

    return render_template(
        "detalhes.html",
        ponto=ponto,
        avaliacoes=avaliacoes,
        media=media,
        quantidade=quantidade,
        ja_avaliou=ja_avaliou,
        logado="usuario_id" in session
    )


@app.route("/avaliar/<int:ponto_id>", methods=["POST"])
def salvar_avaliacao(ponto_id):
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    estrelas = request.form.get("estrelas", "")
    comentario = request.form.get("comentario", "").strip()

    if estrelas not in ["1", "2", "3", "4", "5"]:
        return "Selecione uma nota válida.", 400

    if len(comentario) > 1000:
        return "Comentário muito longo.", 400

    conexao = conectar_banco()

    try:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM pontos_turisticos
                WHERE id = %s AND status = %s
            """, (ponto_id, "aprovado"))

            if not cursor.fetchone():
                abort(404)

            cursor.execute("""
                INSERT INTO avaliacoes
                (usuario_id, ponto_id, estrelas, comentario)
                VALUES (%s, %s, %s, %s)
            """, (
                session["usuario_id"],
                ponto_id,
                int(estrelas),
                comentario
            ))

        conexao.commit()

    except pymysql.err.IntegrityError:
        conexao.rollback()
        return "Você já avaliou este ponto turístico.", 409

    finally:
        conexao.close()

    return redirect(url_for("detalhes_ponto", ponto_id=ponto_id))


if __name__ == '__main__':
    app.run(debug=True)
