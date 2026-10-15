import pyodbc

from config import SQL_SERVER_CONN_STR
from date_utils import formatar_para_ddmmaaaa


def inserir_log_sqlserver(empresa_soc, codcoligada, codpessoa, chapa, acao, dtinicio, dtfinal, status):
    dtinicio_str = formatar_para_ddmmaaaa(dtinicio)
    dtfinal_str = formatar_para_ddmmaaaa(dtfinal)

    try:
        conn = pyodbc.connect(SQL_SERVER_CONN_STR)
        cursor = conn.cursor()

        check_sql = """
            SELECT 1
            FROM dbo.PROCESSAMENTO_API
            WHERE DTCRIACAO    = CAST(GETDATE() AS DATE)
              AND CODCOLIGADA  = ?
              AND CHAPA        = ?
              AND DTINICIO     = ?
        """
        cursor.execute(check_sql, codcoligada, chapa, dtinicio_str)
        if cursor.fetchone():
            print(f"[LOG] registro já existe para hoje: coligada={codcoligada}, chapa={chapa}, acao={acao}, dtinicio={dtinicio_str}")
            cursor.close()
            conn.close()
            return

        insert_sql = """
            INSERT INTO dbo.PROCESSAMENTO_API
            (DTCRIACAO, HRCRIACAO, EMPRESA_SOC, CODCOLIGADA, CODPESSOA, CHAPA, STATUS, ACAO, DTINICIO, DTFINAL)
            VALUES
            (CAST(GETDATE() AS DATE), CONVERT(TIME, GETDATE()), ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_sql, empresa_soc, codcoligada, codpessoa, chapa, status, acao, dtinicio_str, dtfinal_str)
        conn.commit()
    except Exception as e:
        print(f"[ERRO INSERT LOG] {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass
