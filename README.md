# Mobilidade Urbana e Transporte Público no Brasil (2015 - 2024)

Projeto da Avaliação G1 - Linguagem de Programação: Análise e Visualização de Dados com Python.

- **Dashboard:** https://ro-louzas.streamlit.app/
- **Notebook:** `notebooks/analise_mobilidade_urbana.ipynb`

## Problema
Investigar padrões de mobilidade urbana: fluxo de passageiros, tempo de deslocamento, congestionamento, comparação entre regiões, cidades e meios de transporte, e emissões de CO₂.

## Base de dados
`dados/simulacao_mobilidade_urbana_brasil.csv` - 4.440 registros (mês × cidade × meio de transporte), 37 cidades, 6 meios de transporte, 2015–2024. Dataset **simulado**; não contém hora do dia nem população.

## Funcionalidades
- **Intermediárias:** filtros múltiplos, KPIs dinâmicos, gráficos interativos (Plotly), análise temporal, dashboard em seções (abas), visualizações comparativas.
- **Avançadas:** persistência em SQLite com SQLAlchemy (`database/mobilidade.db`) e correlação estatística (Pearson e matriz de correlação).

## Estrutura
```
app.py · requirements.txt · README.md · index.html
dados/ · database/ · notebooks/ · imagens/
```

## Como executar
```bash
pip install -r requirements.txt
streamlit run app.py
```
