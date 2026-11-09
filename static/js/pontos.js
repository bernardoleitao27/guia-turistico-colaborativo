const estadoPonto = document.getElementById("estado-ponto");
const cidadePonto = document.getElementById("cidade-ponto");

fetch("https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome")
    .then(resposta => resposta.json())
    .then(estados => {
        estados.forEach(estado => {
            estadoPonto.innerHTML +=
                `<option value="${estado.sigla}">${estado.nome}</option>`;
        });
    });

estadoPonto.addEventListener("change", () => {
    const uf = estadoPonto.value;

    cidadePonto.innerHTML = '<option value="">Selecione uma cidade</option>';
    cidadePonto.disabled = true;
    document.getElementById("nome-cidade").value = "";

    if (!uf) return;

    fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${uf}/municipios?orderBy=nome`)
        .then(resposta => resposta.json())
        .then(cidades => {
            cidades.forEach(cidade => {
                cidadePonto.innerHTML +=
                    `<option value="${cidade.id}">${cidade.nome}</option>`;
            });

            cidadePonto.disabled = false;
        });
});

const mapaPonto = L.map("mapa-ponto").setView([-22.3145, -49.0587], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap"
}).addTo(mapaPonto);

let marcadorPonto;

mapaPonto.on("click", (evento) => {
    const latitude = evento.latlng.lat;
    const longitude = evento.latlng.lng;

    if (marcadorPonto) {
        mapaPonto.removeLayer(marcadorPonto);
    }

    const iconePonto = L.icon({
        iconUrl: "/static/img/marker-icon.png",
        iconSize: [25, 41],
        iconAnchor: [12, 41]
    });
    
    marcadorPonto = L.marker([latitude, longitude], {
        icon: iconePonto
    }).addTo(mapaPonto);

    document.getElementById("latitude").value = latitude;
    document.getElementById("longitude").value = longitude;

    document.getElementById("coordenadas").textContent =
    `Latitude: ${latitude.toFixed(6)} | Longitude: ${longitude.toFixed(6)}`;
});

cidadePonto.addEventListener("change", function () {
    const nomeCidade = cidadePonto.options[cidadePonto.selectedIndex].text;

    document.getElementById("nome-cidade").value = nomeCidade;
});

