from datetime import datetime


def formatar_para_ddmmaaaa(valor):
    if not valor:
        return None
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%YT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(valor, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue
    return valor
