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






