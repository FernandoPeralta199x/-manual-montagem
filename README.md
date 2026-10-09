# manual-montagem

Gera o **manual de montagem** de móveis planejados (PDF A4 paisagem, pronto para impressão, e versão HTML) a partir de:

- o modelo **SketchUp** (`.skp`, SketchUp 2021 ou mais novo, modelado com Gábster);
- a **lista de corte** da produção (`.csv` separado por `;`);
- o **PDF de venda** (LayOut), como fonte de especificações.

O `.skp` é lido direto, sem SketchUp instalado: geometria de cada peça, camadas visíveis/ocultas e parâmetros dos componentes Gábster. As medidas, posições e desenhos (perspectiva, vistas cotadas, explodidas com balões, etapas, desenho de cada peça) vêm do modelo. O que exige julgamento — qual peça é qual, conflitos entre fontes, textos das etapas — fica num `spec.json` por pedido.

Usado pelo comando `/manual-montagem` do Claude, que escreve o `spec.json` de cada pedido.

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt` e `python -m playwright install chromium` (para o PDF)
- `pdftoppm` (poppler) opcional, para as miniaturas de revisão

## Uso

```bash
# 1. Inventário do modelo (árvore de peças visíveis, sugestões de ligação com a lista de corte)
python -m mm inventario pedido/modelo.skp --csv pedido/lista.csv -o pedido/inventario.txt

# 2. Escrever pedido/spec.json (ver docs/SPEC.md e examples/74391/spec.json)

# 3. Checagens automáticas (todas as linhas da lista ligadas, quantidades, medidas, espessuras)
python -m mm checar pedido/spec.json

# 4. Medidas calculadas para escrever os textos (posições, folgas, centros de puxador, eixos de dobradiça)
python -m mm medidas pedido/spec.json

# 5. Gerar
python -m mm gerar pedido/spec.json --saida pedido/saida
```

Saída: `Manual de Montagem <código> - <cliente>.pdf`, `Manual de Montagem <código>.html` (versão para publicar), `manual_print.html` e `png/revisao_XX.png` (miniaturas para conferência visual).

## Estrutura

```
mm/skp.py        leitor do formato SketchUp 2021+ (ZIP + árvore TLV de model.dat)
mm/cutlist.py    lista de corte (CSV)
mm/model.py      inventário, Project (spec → peças, ferragens, origens), checagens, medidas
mm/draw.py       motor de desenho vetorial (axonometria, vistas ortográficas, cotas, balões)
mm/views.py      desenhos do manual
mm/manual.py     montagem das folhas (16 seções + anexos)
mm/assets/       CSS e fontes (Barlow, Barlow Condensed, IBM Plex Mono — SIL OFL)
docs/SPEC.md     referência do spec.json
examples/74391/  spec do pedido 74391 (os arquivos do cliente não ficam no repositório)
```

## Limites conhecidos

- O leitor de `.skp` foi feito por engenharia reversa e testado com SketchUp 2024 (24.0.553). Arquivos anteriores ao SketchUp 2021 não são suportados.
- Funciona melhor com modelos Gábster (componentes paramétricos com nomes e camadas de variantes). Modelos desenhados à mão podem precisar de mais ajuste no spec.
- Furação (posição, diâmetro, profundidade) não existe no modelo e aparece como "não identificada".
- As peças são desenhadas como caixas (bounding box de cada peça); ferragens podem usar a malha real.
