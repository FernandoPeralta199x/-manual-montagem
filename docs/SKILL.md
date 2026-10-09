---
name: manual-montagem
description: Gera manual de montagem (PDF A4 + página) de móveis planejados a partir do .skp Gábster, lista de corte CSV e PDF de venda. Use quando pedirem manual de montagem ou /manual-montagem.
---

# /manual-montagem

Gera o manual de montagem de um pedido de móveis planejados com a ferramenta do repositório `FernandoPeralta199x/-manual-montagem` (template Luciano Lâminas). O código lê a geometria do `.skp`, calcula medidas e desenha. Você faz a parte de julgamento: ligar cada peça do modelo a um código e às linhas da lista de corte, identificar conflitos entre as fontes e escrever os textos.

Responda ao usuário em português do Brasil.

## Regra fundamental

**NÃO INVENTE.** Toda informação do manual vem do modelo 3D, da lista de corte ou do PDF de venda. O que não estiver lá aparece como "Não identificado no modelo" / "Não especificado no projeto". Marque a origem com `{E}` encontrado, `{C}` calculado, `{I}` inferido, `{A}` ausente. Quando as fontes divergem, registre um conflito e não escolha um valor por conta própria.

## Entradas

`.skp` (obrigatório, SketchUp 2021+), lista de corte `.csv` (obrigatória), PDF de venda e observações do usuário. Se faltar o `.skp` ou o `.csv`, peça antes de começar.

## Como executar

1. Diga em uma frase o que vai fazer e crie uma lista de tarefas.
2. Anexe o repositório com `add_repo` (owner `FernandoPeralta199x`, repo `-manual-montagem`, acesso `read`; `push` só se for alterar o código) e clone uma vez: `git clone --depth 1 https://github.com/FernandoPeralta199x/-manual-montagem /home/claude/-manual-montagem`.
3. Leia `docs/PROCEDIMENTO.md` e `docs/SPEC.md` do clone e siga o procedimento: preparar → analisar (inventário, PDF, lista de corte) → escrever `spec.json` → `checar` e `medidas` → `gerar` e revisar as miniaturas → verificação independente por subagente → entregar (PDF + página publicada + resumo dos conflitos).
4. Os comandos rodam com `cd /home/claude/-manual-montagem && python3 -m mm <inventario|checar|medidas|gerar> ...`.

O procedimento detalhado e o template ficam no repositório, então melhorias feitas lá valem nas próximas execuções sem mudar este skill.
