# 🌎 Guia Turístico Colaborativo

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![Status](https://img.shields.io/badge/Status-Em%20desenvolvimento-yellow?style=flat-square)

## 📌 Sobre o projeto

Aplicação web **Full Stack**, desenvolvida durante o curso Técnico em Desenvolvimento de Sistemas do SENAI, com o objetivo de criar uma plataforma colaborativa para descoberta, cadastro e avaliação de pontos turísticos brasileiros.

O projeto integra backend em Python, banco de dados MySQL, autenticação de usuários, APIs externas e mapas interativos.

## 🛠️ Tecnologias

- **Backend:** Python, Flask, PyMySQL
- **Frontend:** HTML5, CSS3, JavaScript
- **Banco de dados:** MySQL (Aiven)
- **Integrações:** Leaflet, OpenStreetMap e API do IBGE
- **Ferramentas:** Git, GitHub e DBeaver

## ⚙️ Funcionalidades

**Implementadas:**
- Cadastro e autenticação de usuários com hash de senhas.
- Login, logout e gerenciamento de sessões.
- Controle de acesso por perfis (`usuario` e `admin`).
- Integração Flask + MySQL com conexão SSL.
- Mapa interativo utilizando Leaflet.
- Seleção dinâmica de estados e municípios via API do IBGE.

**Em desenvolvimento:**
- Cadastro completo de pontos turísticos com imagens.
- Aprovação de locais pelo administrador.
- Avaliações, comentários e filtros de busca.
- Documentação Swagger e deploy no Render.

## 🗄️ Banco de dados

Modelagem relacional com cinco tabelas: `usuarios`, `pontos_turisticos`, `avaliacoes`, `categorias` e `ponto_categoria`.

Utilização de chaves primárias, estrangeiras, relacionamentos 1:N e N:N e consultas SQL parametrizadas.

## 🚀 Executando localmente

```bash
git clone https://github.com/bernardoleitao27/guia-turistico-colaborativo.git
cd guia-turistico-colaborativo
python -m pip install flask pymysql python-dotenv
```

Configure as variáveis de ambiente no `.env`, o banco MySQL e seu certificado SSL (`ca.pem`).

Depois execute:

```bash
python app.py
```

Acesse `http://127.0.0.1:5000`.

> Projeto em desenvolvimento. Algumas funcionalidades ainda não estão disponíveis.

## 👨‍💻 Desenvolvedor

**Bernardo Messias da Silva Leitão**  
Técnico em Desenvolvimento de Sistemas — SENAI SP (em formação)

[GitHub](https://github.com/bernardoleitao27)