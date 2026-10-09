# Procedimento — /manual-montagem

Gera o manual de montagem de um pedido de móveis planejados com a ferramenta do repositório `FernandoPeralta199x/-manual-montagem`. O código lê a geometria do `.skp`, calcula medidas e desenha. Você faz a parte de julgamento: ligar cada peça do modelo a um código e às linhas da lista de corte, identificar conflitos entre as fontes e escrever os textos.

Responda ao usuário em português do Brasil.

## Regra fundamental

**NÃO INVENTE.** Toda informação do manual vem do modelo 3D, da lista de corte ou do PDF de venda. O que não estiver lá aparece como "Não identificado no modelo" / "Não especificado no projeto". Marque cada informação com o selo de origem: `{E}` encontrado, `{C}` calculado do modelo, `{I}` inferido (confirmar), `{A}` ausente. Quando as fontes divergem, registre um conflito e **não escolha um valor** por conta própria.

## Entradas

- `.skp` do pedido (obrigatório; SketchUp 2021+). O `.skb` é backup: ignore se for igual.
- Lista de corte `.csv` da produção (obrigatória para quantidades, medidas de corte e IDs).
- PDF de venda do LayOut (especificações de material, puxador, medidas gerais).
- Observações do usuário.

Se faltar o `.skp` ou o `.csv`, peça antes de começar.

## Passo a passo

### 1. Preparar
1. Diga em uma frase o que vai fazer e crie uma lista de tarefas.
2. Anexe o repositório com `add_repo` (owner `FernandoPeralta199x`, repo `-manual-montagem`, acesso `read`; use `push` só se for alterar o código). Clone uma vez: `git clone --depth 1 https://github.com/FernandoPeralta199x/-manual-montagem /home/claude/-manual-montagem`. Rode os comandos com `cd /home/claude/-manual-montagem && python3 -m mm ...`.
3. Confira dependências: `python3 -c "import playwright, PIL"` e `which pdftoppm`. Instale o que faltar (`pip install --break-system-packages -r requirements.txt`). O Chromium do ambiente já serve ao Playwright.
4. Crie a pasta do pedido no scratchpad (ex.: `<scratchpad>/pedido-<código>/`) e copie para ela os arquivos recebidos, sem renomear.

### 2. Analisar (antes de escrever qualquer coisa)
1. `python3 -m mm inventario <pasta>/<modelo>.skp --csv <pasta>/<lista>.csv -o <pasta>/inventario.txt` e leia o arquivo inteiro. Ele mostra:
   - componentes da raiz (módulos, portas e prateleiras avulsas);
   - camadas ocultas (as variantes de puxador e dobradiça que NÃO estão no móvel);
   - parâmetros Gábster de cada módulo (tipo de corrediça, de porta, de dobradiça, ferragem das prateleiras…);
   - a árvore de peças visíveis com tamanho e posição, com sugestões `≈ CSV <ID>` por medida.
2. Leia o PDF de venda: `pdftotext -layout` e, para as cotas e o desenho, `pdftoppm -r 110 -png` e veja as páginas.
3. Leia a lista de corte completa (está no fim do inventário).
4. Cruze tudo: módulos, peças, quantidades, medidas, espessuras, materiais, puxador, dobradiças, corrediças. Anote cada divergência.
5. Envie ao usuário (SendUserMessage) um resumo curto: módulos encontrados e os conflitos principais. Ele pode responder algum ponto enquanto você continua.

### 3. Escrever o spec.json
Leia `docs/SPEC.md` e use `examples/74391/spec.json` como modelo. Crie `<pasta>/spec.json`:
- **Módulos:** um por móvel. `raizes` inclui os componentes avulsos que pertencem a ele (porta, prateleira).
- **Peças:** um código por peça distinta (P01…, ordenados por módulo). Peças idênticas usam um código só, e a quantidade vem do modelo. O `sel` é o rótulo do componente no inventário. Toda linha do CSV vai em exatamente um código (`ids`).
- **Ferragens:** só o que o modelo mostra (camadas visíveis + parâmetros Gábster). Quantidade contada no modelo. O que não aparece fica "Ferragem não especificada no projeto." com qtd "—".
- **Conflitos:** cada divergência vira um C0x com o que cada fonte informa e como o manual trata. Cite o conflito nas peças (`conflitos`). Por padrão o template **não imprime** a página de conflitos, as listas de peças e de ferragens, o aviso da capa nem o Anexo B (`ocultar`, ver `docs/SPEC.md`). Por isso:
  - escreva cada divergência por extenso onde ela importa: observação da etapa (`{!C0x}` vira só "⚠"), linha do detalhe de porta/gaveta/puxador e lista "Pendências do projeto" em `cuidados`;
  - não cite códigos C0x em texto corrido, nem códigos de ferragem que não aparecem nos desenhos (as "não especificadas");
  - para citar outra seção use `{sec:chave}` (ex.: `{sec:puxadores}`), porque a numeração muda conforme o que está oculto.
- **Etapas:** sequência lógica de montagem, marcada como sugerida `{I}` (o projeto não define a ordem). Típico: estrutura (laterais + base) → travessas/base superior → rodapé → fundo (conferir esquadro) → ferragens internas → prateleiras → gavetas (corpo → corrediça → frente → puxador) → portas (dobradiça → puxador).
- **Textos com números:** use somente valores do `medidas`, do inventário, do CSV ou do PDF.

### 4. Checar e medir
1. `python3 -m mm checar <pasta>/spec.json`: zero `ERRO`. Cada `DIVERGE` deve estar coberto por um conflito.
2. `python3 -m mm medidas <pasta>/spec.json`: posições, folgas entre frentes, afastamentos, centros de puxador e eixos de dobradiça. Use esses números nas etapas, nos detalhes (portas, gavetas, puxadores), na regulagem e na conferência final.

### 5. Gerar e revisar
1. `python3 -m mm gerar <pasta>/spec.json --saida <pasta>/saida`. O número de páginas do PDF deve ser igual ao de folhas; se não for, algum conteúdo transbordou: encurte o texto ou ajuste `tamanho`.
2. Veja todas as miniaturas `saida/png/revisao_XX.png`. Procure etiquetas sobrepostas, peças explodidas sobre outras, cotas cortadas e texto estourando. Corrija ajustando `offsets`, `tamanho` e textos, e gere de novo.
3. Verificação independente: lance um subagente que não escreveu o manual para conferir o PDF contra o CSV, o PDF de venda e a saída do `medidas`. Ele deve checar números, quantidades, IDs, materiais, conflitos e qualquer afirmação sem fonte. Corrija o que ele achar, regenere e preencha `auditoria` com as 17 perguntas do controle de qualidade (não sai impresso por padrão, mas o resultado vai na resposta final).

### 6. Entregar
1. Envie o PDF com SendUserFile (`Manual de Montagem <código> - <cliente>.pdf`).
2. Publique `Manual de Montagem <código>.html` com a ferramenta Artifact (ícone `tools`; descrição de uma frase). A página é privada até o usuário compartilhar.
3. Resposta final curta: o que foi gerado, os conflitos de prioridade ALTA/MÉDIA a resolver com a produção (eles não estão impressos no manual) e o que ficou como ausente no projeto. Sem recapitular os passos.

## Template

Marca Luciano Lâminas (logo, azul institucional, laranja de destaque) e itens ocultos por padrão. Para um pedido específico, `marca` e `ocultar` no spec mudam isso.

## Melhorias na ferramenta

Se aparecer um caso que o código não cobre (novo tipo de módulo, peça não reconhecida, desenho ruim), corrija no clone, teste com `examples/74391/spec.json` (os arquivos do cliente não ficam no repositório: peça-os se precisar) e, se tiver acesso de escrita, faça commit numa branch e abra PR. Não envie specs de novos pedidos ao repositório sem o usuário pedir (o exemplo 74391 já está lá como modelo).
