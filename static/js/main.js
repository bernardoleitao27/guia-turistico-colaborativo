const mapa = L.map('mapa').setView([-22.3145, -49.0587], 12);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(mapa);

const iconePonto = L.icon({
    iconUrl: '/static/img/marker-icon.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
let marcador = null;

mapa.on('click', function (evento) {
    if (marcador) {
        mapa.removeLayer(marcador);
    }

    marcador = L.marker(evento.latlng, {
        icon: iconePonto
    }).addTo(mapa);
});

const estado = document.getElementById('estado');
const cidade = document.getElementById('cidade');

fetch('https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome')
    .then(resposta => resposta.json())
    .then(estados => {
        estados.forEach(uf => {
            estado.add(new Option(uf.nome, uf.sigla));
        });
    })
    .catch(erro => console.error('Erro ao carregar estados:', erro));

estado.addEventListener('change', function () {
    const uf = estado.value;

    cidade.innerHTML = '<option value="">Selecione a cidade</option>';
    cidade.disabled = true;
    cidade.dispatchEvent(new Event("change"));

    if (!uf) return;

    fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${uf}/municipios`)
        .then(resposta => resposta.json())
        .then(municipios => {
            municipios.forEach(municipio => {
                cidade.add(new Option(municipio.nome, municipio.id));
            });

            cidade.disabled = false;
        })
        .catch(erro => console.error('Erro ao carregar cidades:', erro));
});

fetch("/api/pontos")
    .then(resposta => resposta.json())
    .then(dados => {

        const listaPontos = document.getElementById("lista-pontos");
        listaPontos.replaceChildren();

        const registros = [];

        dados.pontos.forEach(ponto => {
            const icone = L.icon({
                iconUrl: "/static/img/marker-icon.png",
                iconSize: [25, 41],
                iconAnchor: [12, 41]
            });

            const popup = document.createElement("div");

            const titulo = document.createElement("strong");
            titulo.textContent = ponto.nome;

            const localizacao = document.createElement("p");
            localizacao.textContent = `${ponto.cidade} - ${ponto.uf}`;

            popup.appendChild(titulo);
            popup.appendChild(localizacao);

            const marcador = L.marker([ponto.latitude, ponto.longitude], {
                icon: icone
            })
                .addTo(mapa)
                .bindPopup(popup);

            const card = document.createElement("div");
            card.className = "card";

            const imagemCard = document.createElement("img");

            imagemCard.src = ponto.foto
                ? `/static/${ponto.foto}`
                : "/static/img/sem-foto.png";
            
            imagemCard.alt = `Fotografia de ${ponto.nome}`;
            imagemCard.className = "card-imagem";
            imagemCard.loading = "lazy";
            
            imagemCard.onerror = function () {
                imagemCard.onerror = null;
                imagemCard.src = "/static/img/sem-foto.png";
            };
            
            card.appendChild(imagemCard);

            const tituloCard = document.createElement("h3");
            tituloCard.textContent = ponto.nome;

            const cidadeCard = document.createElement("p");
            cidadeCard.textContent = `${ponto.cidade} - ${ponto.uf}`;

            const descricaoCard = document.createElement("p");
            descricaoCard.textContent = ponto.descricao;

            card.appendChild(tituloCard);
            card.appendChild(cidadeCard);
            card.appendChild(descricaoCard);

            const avaliacaoCard = document.createElement("p");
            avaliacaoCard.className = "card-avaliacao";

            if (ponto.quantidade_avaliacoes > 0) {
                avaliacaoCard.textContent =
                    `★ ${Number(ponto.media).toFixed(1).replace(".", ",")} (${ponto.quantidade_avaliacoes} avaliações)`;
            } else {
                avaliacaoCard.textContent = "Ainda não avaliado";
            }

            card.appendChild(avaliacaoCard);

            const linkDetalhes = document.createElement("a");

            linkDetalhes.href = `/ponto/${ponto.id}`;
            linkDetalhes.textContent = "Ver detalhes";
            linkDetalhes.className = "btn-detalhes";

            card.appendChild(linkDetalhes);






            listaPontos.appendChild(card);

            registros.push({
                ponto: ponto,
                marcador: marcador,
                card: card
            });
        });
        const estadoFiltro = document.getElementById("estado");
        const cidadeFiltro = document.getElementById("cidade");

        function filtrarPontos() {
            const ufSelecionada = estadoFiltro.value;
            const cidadeSelecionada = cidadeFiltro.value;

            registros.forEach(registro => {
                const correspondeEstado =
                    !ufSelecionada || registro.ponto.uf === ufSelecionada;

                console.log("Cidade selecionada:", cidadeSelecionada);
                console.log("Código IBGE no MySQL:", registro.ponto.codigo_ibge);
                console.log("Nome da cidade:", registro.ponto.cidade);

                const correspondeCidade =
                    !cidadeSelecionada ||
                    Number(registro.ponto.codigo_ibge) === Number(cidadeSelecionada);

                const mostrar = correspondeEstado && correspondeCidade;

                console.log("Estado corresponde:", correspondeEstado);
                console.log("Cidade corresponde:", correspondeCidade);
                console.log("Mostrar ponto:", mostrar);

                registro.card.style.display = mostrar ? "" : "none";

                if (mostrar) {
                    registro.marcador.addTo(mapa);
                } else {
                    mapa.removeLayer(registro.marcador);
                }

                console.log(
                    "Marcador está no mapa:",
                    mapa.hasLayer(registro.marcador)
                );

                console.log(
                    "Cartão está visível:",
                    registro.card.style.display !== "none"
                );



            });
        }


        const ordenacaoFiltro = document.getElementById("ordenacao");

        function ordenarPontos() {
            const tipo = ordenacaoFiltro.value;

            registros.sort((a, b) => {
                if (tipo === "melhores") {
                    return Number(b.ponto.media || 0) - Number(a.ponto.media || 0);
                }

                if (tipo === "piores") {
                    return Number(a.ponto.media || 0) - Number(b.ponto.media || 0);
                }

                if (tipo === "recentes") {
                    return b.ponto.id - a.ponto.id;
                }

                return 0;
            });

            registros.forEach(registro => {
                listaPontos.appendChild(registro.card);
            });
        }

        ordenacaoFiltro.addEventListener("change", ordenarPontos);

        ordenarPontos();

        estadoFiltro.addEventListener("change", filtrarPontos);
        cidadeFiltro.addEventListener("change", filtrarPontos);
    })
    .catch(erro => {
        console.error("Erro ao carregar pontos turísticos:", erro);
    });










