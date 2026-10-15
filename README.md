# Integração SOC x TOTVS RM — Atestados Médicos

Automação que sincroniza afastamentos/atestados médicos cadastrados no **SOC**
(Software Integrado de Gestão Ocupacional) com o **TOTVS RM** (Folha de
Pagamento), eliminando o lançamento manual entre os dois sistemas.

## O que o projeto faz

1. Consulta no SOC, via SOAP (WS-Security), as licenças médicas lançadas/alteradas
   nos últimos dias, para cada empresa configurada.
2. Para cada afastamento retornado, localiza o funcionário correspondente no
   TOTVS RM (`CODPESSOA`) a partir da chapa.
3. Verifica se já existe um atestado lançado no RM para aquele período:
   - Se não existir, faz o **insert** via `SaveRecord`.
   - Se existir mas houver divergência de data fim ou CID, faz o **update**.
   - Se já estiver processado e sem divergência, apenas registra o log.
4. Grava o resultado de cada processamento (sucesso, atualização ou erro) em
   uma tabela de log no SQL Server, evitando reprocessar o mesmo registro no
   mesmo dia.

## Stack

- Python
- `requests` para consumo dos web services SOAP do SOC e do TOTVS RM
- `pandas` para tratamento tabular dos afastamentos retornados
- `pyodbc` para gravação do log em SQL Server
- Autenticação WS-Security (UsernameToken + PasswordDigest) implementada manualmente

## Estrutura

```
config.py             # variáveis de ambiente, mapeamentos de negócio
date_utils.py         # normalização de datas entre os formatos SOC/RM
ws_security.py         # geração do header WS-Security para o SOC
totvs_utils.py          # consultas e gravação (ReadView/SaveRecord) no TOTVS RM
db_logger.py           # log de processamento em SQL Server
integracao_soc_rm.py   # orquestração do fluxo completo
main.py                # ponto de entrada
```

## Configuração

1. Copie `.env.example` para `.env` e preencha com as credenciais do seu ambiente:

```bash
cp .env.example .env
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Execute:

```bash
python main.py
```

> Este repositório é uma versão sanitizada de uma automação usada em produção:
> credenciais, hosts e códigos internos de empresa foram removidos/anonimizados
> e passam a ser lidos de variáveis de ambiente.
