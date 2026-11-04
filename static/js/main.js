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

mapa.on('click', function(evento) {
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

estado.addEventListener('change', function() {
    const uf = estado.value;

    cidade.innerHTML = '<option value="">Selecione a cidade</option>';
    cidade.disabled = true;

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
