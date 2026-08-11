# Otimizacoes do SCOZ News

Status: ajustes imediatos aplicados localmente em 2026-05-08.

Este documento registra oportunidades para reduzir tamanho de codigo, custo de manutencao e consumo de tokens no fluxo de consulta e curadoria de noticias.

## Diagnostico Rapido

Arquivos atuais:

| Arquivo | Tamanho |
|---|---:|
| `index.html` antes | 963.150 bytes |
| `index.html` depois | 624.229 bytes |
| Reducao no HTML | 338.921 bytes |
| `noticias-data.json` | 242.697 bytes |
| `build_html.py` depois | 33.738 bytes |
| `noticias-cache.json` | 48.986 bytes |

Conteudo atual:

| Medida | Valor |
|---|---:|
| Semanas | 7 |
| Noticias | 323 |
| Caracteres em titulos | 30.772 |
| Caracteres em resumos | 123.498 |
| Caracteres em URLs | 24.064 |
| Caracteres em fontes | 6.295 |

O principal peso do HTML nao estava so nas noticias. O arquivo publicado repetia SVGs inline para cada item:

| Medida | Valor |
|---|---:|
| Ocorrencias de `<svg>` antes | 1.299 |
| SVGs unicos antes | 7 |
| Caracteres ocupados por SVGs antes | 432.619 |
| Caracteres repetidos de SVG antes | 430.540 |
| Data image do logo antes, repetida 2 vezes | 17.108 caracteres |
| `<symbol>` depois | 7 |
| `<use href>` depois | 1.299 |

## Ajustes Aplicados

### 1. Sprite SVG em vez de repetir SVG inline

Cada noticia repetia os mesmos icones de acessar, copiar, check e chevron. Agora:

- O HTML declara um unico sprite com 7 `<symbol>`.
- Cada instancia usa `<use href="#icon-name">`.
- As dimensoes e strokes ficam em classes CSS `.ico`, `.ico-11`, `.ico-13`, `.ico-14`, `.ico-16` e `.sw-2`.

Impacto medido: o `index.html` caiu de 963.150 bytes para 624.229 bytes, mesmo apos os novos ajustes de runtime.

### 2. Logo SVG leve

O gerador deixou de criar PNG base64 via PIL e passou a usar um SVG textual leve em data URI.

### 3. Escaping de campos vindos do JSON

`build_html.py` agora usa `html.escape` para `title`, `source`, `date`, `url`, `summary` e `week_id`.

Motivo: uma noticia com aspas, `<`, `&` ou HTML inesperado pode quebrar markup ou abrir risco de injection no arquivo final.

### 4. Variaveis mortas removidas

`badge_text` e `count_label` foram removidas.

### 5. Configuracao de categorias centralizada

`CATEGORIES` agora alimenta:

- CSS de tabs ativas.
- CSS de background por categoria.
- CSS de borda/sombra do accordion.
- HTML dos botoes de tab.
- Camadas de background.
- Contagem total no build.

### 6. Cache local de noticias processadas

O build agora gera `noticias-cache.json` com:

- `last_week_id`.
- `seen_urls`.
- `seen_titles`.

No estado atual, o cache gerado tem 173 URLs unicas e 323 titulos. O arquivo esta no `.gitignore`, porque e artefato local de apoio ao fluxo de curadoria.

### 7. Performance de renderizacao e uso geral

Foram aplicados ajustes de runtime sem alterar o visual desktop:

- Reducao de `backdrop-filter` no breakpoint mobile, com fundos mais opacos para preservar leitura.
- Recalculo dos offsets sticky em `resize` e `orientationchange` usando `requestAnimationFrame`.
- Busca com indice precomputado em `WeakMap`, evitando `querySelector` em todos os itens a cada tecla.
- Debounce de 100ms na busca.
- Delegacao de eventos para tabs, accordions, copiar resumo e expandir tudo.
- Desativacao temporaria de transicoes do accordion durante expandir/recolher em lote.
- `content-visibility` nao foi aplicado por decisao de escopo.

## Reducao de Tokens na Consulta de Noticias

### Regra principal

Nunca usar `index.html` como contexto para consulta ou atualizacao de noticias. O HTML tem quase 1 MB e contem muita repeticao estrutural. O contexto para IA deve vir de dados compactos e apenas do periodo necessario.

### 1. Consultar apenas a semana nova

Hoje o historico total tem 323 noticias. A semana mais recente tem 23 noticias e cerca de 14.800 caracteres nos campos essenciais. Uma semana cheia de 50 noticias fica perto de 31.900 caracteres.

Usar somente a semana nova em vez do historico completo reduz drasticamente o contexto enviado a cada rodada.

### 2. Manter cache de URLs ja processadas

Arquivo local gerado pelo build:

```json
{
  "seen_urls": ["https://..."],
  "seen_titles": ["..."],
  "last_week_id": "2026-04-28"
}
```

Antes de resumir com IA:

- Remover URLs ja vistas.
- Remover titulos quase duplicados.
- Manter so candidatos novos.

### 3. Usar formato compacto durante coleta

O JSON atual e bom para leitura humana, mas caro como contexto. Um formato intermediario compacto pode usar listas ou chaves curtas:

```json
{
  "w": [
    {
      "id": "2026-04-28",
      "i": [
        [0, "Titulo", "Fonte", "Apr 28, 2026", "https://...", "Resumo"]
      ]
    }
  ],
  "c": ["meta", "google", "ppc", "mkt", "ia"]
}
```

Estimativa no arquivo atual:

| Formato | Tamanho |
|---|---:|
| JSON atual pretty | 238.642 caracteres |
| JSON atual minificado | 207.910 caracteres |
| Formato compacto minificado | 195.219 caracteres |

A economia estrutural e moderada, cerca de 18% contra o pretty atual. O maior ganho vem de incrementalidade, deduplicacao e limite de resumo.

### 4. Separar entrada de IA de saida publicada

Para pedir curadoria ou resumo, usar um payload menor que o JSON publicado:

```json
{
  "week": "2026-05-05",
  "category": "meta",
  "items": [
    {
      "t": "titulo bruto",
      "u": "url",
      "src": "fonte",
      "notes": ["ponto 1", "ponto 2"]
    }
  ]
}
```

Depois da resposta aprovada, expandir para o formato publicado com `title`, `source`, `date`, `url`, `summary`.

### 5. Limitar tamanho dos resumos

Resumo atual medio: 382 caracteres por noticia. Isso e bom para leitura, mas pode ser controlado por contrato:

- Titulo: ate 110 caracteres.
- Resumo: 280 a 420 caracteres.
- Sem introducoes genericas.
- Sempre responder impacto pratico para marketing, midia paga ou IA.

### 6. Processar por categoria

Em vez de mandar todas as categorias juntas, processar lotes:

- 10 a 15 candidatos por categoria.
- Retornar no maximo 4 a 10 itens finais por categoria.
- Rodar deduplicacao global ao final.

Isso reduz tokens por chamada e melhora controle editorial.

## Mudancas Estruturais Opcionais

### Separar artefatos

Se o deploy permitir multiplos arquivos:

- `index.html`: estrutura.
- `styles.css`: visual HAZE.
- `app.js`: filtros e accordion.
- `noticias-data.json`: carregado em runtime.

Vantagem: `index.html` fica pequeno e o navegador pode cachear CSS/JS.

Tradeoff: publicar deixa de ser um arquivo unico. Para o fluxo atual, manter HTML unico ainda faz sentido.

### Renderizar noticias no cliente

Outra opcao e publicar um HTML pequeno que carrega JSON e monta os accordions via JS.

Vantagem: reduz repeticao de markup no HTML.

Tradeoff: exige que o ambiente sirva JSON corretamente e aumenta dependencia de JS em runtime.

## Ordem Recomendada Restante

1. Passar a alimentar a IA somente com a semana nova.
2. Usar `noticias-cache.json` para remover URLs e titulos ja vistos antes de pedir resumo.
3. Avaliar formato compacto apenas se o fluxo ainda estiver caro.
4. Se o deploy permitir, considerar separar CSS/JS/data em arquivos cacheaveis.
