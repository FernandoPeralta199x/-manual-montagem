# spec.json — referência

O `spec.json` descreve um pedido: de onde vêm os arquivos, como cada peça do modelo vira um código (P01…), as ferragens, os conflitos e os textos do manual. O código lê a geometria do `.skp` e calcula tudo o que é medida e desenho. O spec guarda o que exige julgamento.

Exemplo completo: [`examples/74391/spec.json`](../examples/74391/spec.json).

## Marcação de texto

Em qualquer texto do spec:

| Marcação | Resultado |
|---|---|
| `{E}` `{C}` `{I}` `{A}` | Selo de origem: Encontrado, Calculado, Inferido, Ausente |
| `{!C02}` | Destaque laranja "⚠ C02" |
| HTML simples (`<b>`, `<br>`) | Permitido |

Regra: toda informação que não vem do modelo, da lista de corte ou do PDF leva `{I}` ou `{A}`. Nada é inventado.

## Campos

### `projeto`
```json
{"cliente": "...", "codigo": "74391", "pedido": "581885-74391 - Moveis", "data_venda": "06/10/2026",
 "fabricante": null, "endereco": null,
 "arquivos": {"skp": "modelo.skp", "csv": "lista.csv", "pdf": "venda.pdf"},
 "arquivos_desc": {"Modelo 3D": "...", "Desenho de venda": "...", "Lista de corte": "..."}}
```
Caminhos de `arquivos` são relativos à pasta do spec. `fabricante`/`endereco` nulos aparecem como "Não informado {A}".

### `modulos[]`
| Campo | Uso |
|---|---|
| `id` | `M01`, `M02`… |
| `nome`, `sub`, `rotulo` | Títulos. `rotulo` é o cabeçalho em caixa alta |
| `raizes` | Lista de trechos do nome da definição (ou índices) dos componentes da raiz do modelo que pertencem ao módulo. Ex.: um armário + a porta avulsa + a prateleira avulsa |
| `gabster`, `pdf_spec` | Texto de origem (componente Gábster; especificações do PDF) |
| `componentes` | Lista da página "Vista do móvel montado" |
| `nota_montado`, `nota_medidas` | Notas das páginas 3 e 4 |
| `cotas` | Cotas extras das vistas: `cadeia_esquerda` (códigos cujas alturas formam a cota em cadeia), `cadeia_extra` (alturas adicionais), `cadeia_direita` (códigos cotados à direita, ex. porta), `folga_lateral` (código), `recuo_topo` (código: recuo frontal na vista lateral), `recuo_base` (código: recuo do rodapé) |
| `origem_z` | Opcional. Padrão 0 = piso do modelo |

A origem de cada módulo é o canto frontal-esquerdo da caixa (peças com `funcao` `caixa`/`fundo`). Todas as cotas são relativas a ela; alturas são a partir do piso.

### `pecas[]`
| Campo | Uso |
|---|---|
| `code` | `P01`… em ordem de módulo |
| `mod` | Módulo |
| `nome` | Nome no manual |
| `sel` | Nome do componente no modelo (rótulo `_name` do Gábster, ou nome da definição sem `#nn`). Pode ser lista, ou `{"nome": "...", "caminho": "trecho do caminho"}` para desambiguar |
| `funcao` | `caixa`, `fundo`, `frente`, `gaveta`, `prateleira`, `divisoria`, `outro`. `frente` ativa as medidas de folga/puxador/dobradiça |
| `ids` | IDs da lista de corte (8ª coluna do CSV) desta peça |
| `mdf_pdf` | `true` se o PDF especifica MDF para esta peça |
| `conflitos` | IDs de conflito citados nos alertas automáticos (`["C01"]`) |
| `alerta_espessura` | Força alerta de espessura |
| `obs` | Observações extras na lista de peças |
| `furacao`, `recortes`, `veio` | Substituem os textos padrão do cartão da peça |
| `filtro_z` | `[zmin, zmax]` em coordenadas do modelo, para separar peças de mesmo nome |

Peças idênticas usam um código só; a quantidade vem do número de instâncias visíveis no modelo.

### `hardware`
Geometria das ferragens que aparecem nos desenhos. A chave é o código (`F01`) ou código + sufixo (`F03_M01`); o rótulo nos desenhos usa só o código.
```json
"F01": {"mod": "M01", "sel": ["CorE", "CorD"], "render": "box"},
"F02": {"mod": "M02", "sel": ["Dobradiça"], "render": "mesh", "mostrar_montado": false, "vistas": false}
```
`render`: `box` (caixa) ou `mesh` (faces reais). `mostrar_montado: false` tira da perspectiva montada; `vistas: false` tira das vistas ortográficas.

### `ferragens[]`
Tabela da seção 6: `code`, `nome`, `qtd` (texto), `origem_qtd` (`E`/`A`…), `aplicacao`, `origem`, `obs`. Ferragem não especificada: `qtd` "—", `obs` "Ferragem não especificada no projeto."

### `conflitos[]`
`id`, `prioridade` (`ALTA`/`MÉDIA`/`BAIXA`), `titulo`, `fontes` (lista de `[fonte, o que diz]`), `tratamento`. Nunca escolher um valor: dizer o que cada fonte informa e como o manual trata.

### `info_gerais.blocos[]`
`{titulo, texto}` da coluna direita da seção 2 (veio, ferragens, tampo, ferramentas…).

### `explodidas[]`
```json
{"mod": "M01", "sub": "caixa", "tamanho": [200, 160], "inst": null,
 "pecas": {"P01": [-330, 0, 0], "P02": {"lados": [[-300,0,0],[300,0,0]]}},
 "hw": [{"key": "F01", "idx": [0, 1], "offset_lados": [[-270,0,0],[270,0,0]], "sub": "×4 pares"}],
 "rotulos": {"P21": "×3"}, "legenda": {"pecas": [...], "ferragens": [...]}, "nota": "..."}
```
Deslocamentos em mm: x = direita, y = para trás (negativo = para a frente), z = para cima. `inst` mostra só a instância k de cada peça (ex.: uma gaveta). `offset_lados` usa o 1º vetor para o que está à esquerda do centro do módulo e o 2º para a direita.

### `etapas[]`
```json
{"id": "E01", "mod": "M01", "titulo": "...", "mostrar": ["P01"], "novas": ["P02"],
 "offsets": {"P02": [260, 0, 0]}, "hw_mostrar": ["F01"], "hw_novas": [{"key": "F03_M01", "offset": [0, -160, 0]}],
 "inst": {"P09": [0]}, "setas": ["P13"], "so_rotulos": ["P13"], "rotulos": {"P13": "×4 corpos"},
 "desc": "...", "obs": "..."}
```
`mostrar` = já instaladas (cinza). `novas` = desta etapa (laranja, deslocadas por `offsets`, com seta). Duas etapas por folha.

### `detalhes`
- `portas[]`: `porta`, `inst`, `dobradicas` (chave hardware), `puxador` (chave hardware), `contexto` (códigos ao redor), `corte_z`, `sub`, `linhas` (`[[rótulo, texto]]`), `nota`. Desenho e cotas (eixos das dobradiças, posição) são automáticos.
- `gavetas[]`: `mod`, `sub`, `linhas`, `ordem`.
- `puxadores`: `sub`, `itens` (`{painel, inst, hw, hw_idx, legenda}` — centro calculado), `tabela` (`cabecalho`, `linhas`; linha com 2 itens ocupa as colunas restantes).
Sem itens, a seção sai como "Não se aplica a este projeto".

### `regulagem`, `conferencia`, `cuidados`, `auditoria`
- `regulagem`: `{intro, linhas: [[item, referência, selo, observação]]}`
- `conferencia`: `[[módulo, verificação, valor esperado, selo]]`
- `cuidados`: `{sub, colunas: [[{titulo, itens: [...]}]]}` (2 colunas)
- `auditoria`: `[[pergunta, resposta]]` — as 17 perguntas do controle de qualidade, respondidas depois da verificação

### `cores` (opcional)
`{"Nome do padrão": "#hex"}` para padrões que o código não reconhece. Reconhece branco, madeirados (carvalho, freijó, nogueira…) e cinzas (manhattan, grafite…).
