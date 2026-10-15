import base64
import html
import xml.etree.ElementTree as ET
from datetime import date, datetime

import requests

from config import RM_ENDPOINT, RM_USER, RM_PASS, MAPA_CODTP_ATESTADO, MAPA_MOTIVO_AFAST


def _auth_headers():
    auth_str = f"{RM_USER}:{RM_PASS}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    return {
        "Content-Type": "text/xml;charset=UTF-8",
        "SOAPAction": '"http://www.totvs.com/IwsDataServer/ReadView"',
        "Authorization": f"Basic {auth_b64}",
    }


def buscar_codpessoa_por_chapa(chapa, codcoligada):
    headers = _auth_headers()

    xml = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tot="http://www.totvs.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <tot:ReadView>
        <tot:DataServerName>FopFuncData</tot:DataServerName>
        <tot:Filtro>PFUNC.CODCOLIGADA = {codcoligada} AND PFUNC.CHAPA = '{chapa}'</tot:Filtro>
        <tot:Contexto>CODCOLIGADA={codcoligada},CODSISTEMA=S,CODUSUARIO={RM_USER}</tot:Contexto>
        </tot:ReadView>
    </soapenv:Body>
    </soapenv:Envelope>"""

    resp = requests.post(RM_ENDPOINT, data=xml.encode("utf-8"), headers=headers)
    resp.raise_for_status()
    if not resp.encoding:
        resp.encoding = "utf-8"

    root = ET.fromstring(resp.text)
    ns = {"s": "http://schemas.xmlsoap.org/soap/envelope/", "tot": "http://www.totvs.com/"}
    rv = root.find(".//tot:ReadViewResult", ns)
    if rv is None or not (rv.text or "").strip():
        return None

    inner_xml = rv.text.strip()
    data_root = ET.fromstring(inner_xml)
    return data_root.findtext(".//CODPESSOA")


def buscar_medico_rm(medico, codcoligada):
    headers = _auth_headers()

    xml = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tot="http://www.totvs.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <tot:ReadView>
        <tot:DataServerName>SmtProfissionalSaudeData</tot:DataServerName>
        <tot:Filtro>VPROFISSIONALSAUDE.NOMEPROFISSIONAL LIKE '%{medico}%'</tot:Filtro>
        <tot:Contexto>CODCOLIGADA={codcoligada},CODSISTEMA=S,CODUSUARIO={RM_USER}</tot:Contexto>
        </tot:ReadView>
    </soapenv:Body>
    </soapenv:Envelope>"""

    resp = requests.post(RM_ENDPOINT, data=xml.encode("utf-8"), headers=headers)
    if resp.status_code != 200:
        print("Erro no request:", resp.text)
        return None

    root = ET.fromstring(resp.content)
    readview_result = next((n.text for n in root.iter() if n.tag.endswith("ReadViewResult")), None)
    if not readview_result:
        return None

    unescaped_xml = html.unescape(readview_result)
    data_root = ET.fromstring(unescaped_xml)

    for el in data_root.iter():
        if el.tag.endswith("CODIGO"):
            return el.text.strip()

    return None


def buscar_seqatestado(codpessoa, dtinicio, codcoligada):
    headers = _auth_headers()

    dtinicio_fmt = datetime.strptime(dtinicio, "%d/%m/%Y").strftime("%Y-%m-%dT00:00:00")
    filtro = (
        f"VATESTADO.CODPESSOA = '{codpessoa}' AND "
        f"TRUNC(VATESTADO.DTINICIO) = TO_DATE('{dtinicio_fmt}',"
        f" 'YYYY-MM-DD\"T\"HH24:MI:SS')"
    )

    xml = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                    xmlns:tot="http://www.totvs.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <tot:ReadView>
            <tot:DataServerName>SmtAtestadoData</tot:DataServerName>
            <tot:Filtro>{filtro}</tot:Filtro>
            <tot:Contexto>CODCOLIGADA={codcoligada},CODSISTEMA=S,CODUSUARIO={RM_USER}</tot:Contexto>
        </tot:ReadView>
    </soapenv:Body>
    </soapenv:Envelope>"""

    print(f"[DEBUG] Filtro ReadView: {filtro}")

    try:
        resp = requests.post(RM_ENDPOINT, data=xml.encode("utf-8"), headers=headers, timeout=30)
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] não foi possível buscar SEQ para {codpessoa}, pulando.")
        return None, None

    if resp.status_code != 200:
        print("[ERRO] status", resp.status_code, resp.text)
        return None, None

    readview = next(
        (n.text for n in ET.fromstring(resp.content).iter() if n.tag.endswith("ReadViewResult")),
        None,
    )
    if not readview:
        return None, None

    data_root = ET.fromstring(html.unescape(readview))

    seq = None
    codtp_atestado = None
    dados = {}
    for el in data_root.iter():
        tag = el.tag.upper()
        txt = el.text.strip() if el.text else ""
        if tag.endswith("SEQATESTADO"):
            seq = txt
        elif tag.endswith("CODTPATESTADO"):
            codtp_atestado = txt
        elif tag.endswith("DTINICIO"):
            dados["DTINICIO_COMPLETO"] = txt
        elif tag.endswith("DTFINAL"):
            dados["DTFINAL"] = txt[:10]
        elif tag.endswith("CID"):
            dados["CID"] = txt

    if seq is None:
        return None, None, None

    return seq, codtp_atestado, dados


def gerar_xml_saverecord(afast, codpessoa, seqatestado, codcoligada, hora_rm=None, codtp_atestado=None):
    dtini = afast["dataInicioAfastamento"]
    date_part = datetime.strptime(dtini, "%d/%m/%Y").strftime("%Y-%m-%d")
    time_part = "00:00:00"
    if hora_rm:
        try:
            time_part = hora_rm.split("T")[1]
        except Exception:
            pass
    dtini_fmt = f"{date_part}T{time_part}"

    dtfim = afast.get("dataFimAfastamento", "").strip()
    if dtfim:
        dtfim_fmt = datetime.strptime(dtfim, "%d/%m/%Y").strftime("%Y-%m-%dT00:00:00")
        dtfinal_tag = f"<DTFINAL>{dtfim_fmt}</DTFINAL>"
    else:
        dtfinal_tag = "<DTFINAL/>"

    if codtp_atestado:
        codtp_rm = codtp_atestado
    else:
        codtp_soc = afast.get("codigoSocTipoDeAfastamento", "").strip()
        codtp_rm = MAPA_CODTP_ATESTADO.get(codtp_soc, "01")

    dt_ini = datetime.strptime(dtini, "%d/%m/%Y").date()
    dt_end = datetime.strptime(dtfim, "%d/%m/%Y").date() if dtfim else None
    data_hoje = date.today()

    # Define se o atestado mantém o funcionário ativo ou altera a situação,
    # de acordo com a duração do afastamento.
    if dt_end:
        diferenca = (dt_end - dt_ini).days
    else:
        diferenca = (date.today() - dt_ini).days

    if diferenca <= 15 or (dt_end is not None and dt_end < data_hoje):
        codsituacao = "<RETORNOAUTOMATICO>-1</RETORNOAUTOMATICO>"
    else:
        codsituacao = "<RETORNOAUTOMATICO>0</RETORNOAUTOMATICO>"

    chapa = afast["matriculaFuncionario"]
    nome = afast.get("nomeSolicitante", "")
    codmedico = buscar_medico_rm(nome, codcoligada)
    cid = afast.get("cidESocial", afast.get("cids", ""))
    regconselho = afast["conselhoClasse"]
    descricao = "Atestado via integração SOC"

    codmot_soc = afast.get("codigoSocMotivoAfastamento", "").strip()
    codmot_rm = MAPA_MOTIVO_AFAST.get(codmot_soc, "32")

    xml_codmedico = f"<CODMEDICO>{codmedico}</CODMEDICO>" if codmedico else ""
    xml_nomemedico = f"<NOMEMEDICO>{nome}</NOMEMEDICO>"

    return f"""<SmtAtestado xmlns="http://tempuri.org/SmtAtestado.xsd">
  <vAtestado>
    <CODPESSOA>{codpessoa}</CODPESSOA>
    <SEQATESTADO>{seqatestado}</SEQATESTADO>
    <DTINICIO>{dtini_fmt}</DTINICIO>
    {dtfinal_tag}
    <HORAINICIO>0</HORAINICIO>
    <HORAFINAL>0</HORAFINAL>
    <CODTPATESTADO>{codtp_rm}</CODTPATESTADO>
    <CID>{cid}</CID>
    <OBSERVACOES>{descricao}</OBSERVACOES>
    {xml_codmedico}
    {xml_nomemedico}
    <REGCONSELHO>{regconselho}</REGCONSELHO>
    <CODCOLIGADA>{codcoligada}</CODCOLIGADA>
    <CODORGAOCLASSE>{afast.get('siglaConselhoSolicitante', '')}</CODORGAOCLASSE>
    <CODUFREGISTRO>{afast.get('ufConselhoClasse', '')}</CODUFREGISTRO>
  </vAtestado>
  <VCHAPAATESTADO>
    <CODPESSOA>{codpessoa}</CODPESSOA>
    <SEQATESTADO>{seqatestado}</SEQATESTADO>
    <CODCOLIGADA>{codcoligada}</CODCOLIGADA>
    <CHAPA>{chapa}</CHAPA>
    <MOTIVOAFAST>{codmot_rm}</MOTIVOAFAST>
    <DTINICIO>{dtini_fmt}</DTINICIO>
    <CODTPATESTADO>{codtp_rm}</CODTPATESTADO>
    {codsituacao}
    <DESCRICAO>{descricao}</DESCRICAO>
    <ORIGEMALTERACAO>0</ORIGEMALTERACAO>
  </VCHAPAATESTADO>
</SmtAtestado>"""


def atualizar_se_existir_diferenca(afast, codpessoa, seqatestado, codtp_atestado, dados_atuais, codcoligada, empresa_soc, chapa):
    from db_logger import inserir_log_sqlserver

    print("[DEBUG] Entrou em atualizar_se_existir_diferenca")

    dtfim = afast.get("dataFimAfastamento", "").strip()
    if dtfim:
        dtfim_fmt = datetime.strptime(dtfim, "%d/%m/%Y").strftime("%Y-%m-%dT00:00:00")
    else:
        dtfim_fmt = dtfim

    if not dados_atuais:
        print("Dados atuais ausentes, forçando update.")
        xml_novo = gerar_xml_saverecord(afast, codpessoa, seqatestado, codcoligada, hora_rm=None, codtp_atestado=None)
        enviar_saverecord(xml_novo, codcoligada, acao="Alteração", empresa_soc=empresa_soc, codpessoa=codpessoa, chapa=chapa, dtinicio=afast["dataInicioAfastamento"], dtfinal=dtfim_fmt)
        return True

    campos_validar = ["DTFINAL", "CID"]

    dtini_soc = afast.get("dataInicioAfastamento", "").strip()
    dtfim_soc = afast.get("dataFimAfastamento", "").strip()
    cid_soc = afast.get("cidESocial", afast.get("cids", "")).strip()

    novo = {
        "DTINICIO": datetime.strptime(dtini_soc, "%d/%m/%Y").strftime("%Y-%m-%d") if dtini_soc else "",
        "DTFINAL": datetime.strptime(dtfim_soc, "%d/%m/%Y").strftime("%Y-%m-%d") if dtfim_soc else "",
        "CID": cid_soc,
    }

    divergente = False
    for campo in campos_validar:
        rm_val = dados_atuais.get(campo, "").strip()
        soc_val = novo[campo]
        if rm_val != soc_val:
            print(f"Diferença em {campo}: RM='{rm_val}' x SOC='{soc_val}'")
            divergente = True

    raw_dtini = afast.get("dataInicioAfastamento", "").strip()
    dtini_log = datetime.strptime(raw_dtini, "%d/%m/%Y").strftime("%d/%m/%Y")

    raw_dtfim = afast.get("dataFimAfastamento", "").strip()
    dtfim_log = datetime.strptime(raw_dtfim, "%d/%m/%Y").strftime("%d/%m/%Y") if raw_dtfim else None

    if divergente:
        print("Encontrou divergências, enviando update.")
        hora_rm = dados_atuais.get("DTINICIO_COMPLETO") if dados_atuais else None
        xml_novo = gerar_xml_saverecord(afast, codpessoa, seqatestado, codcoligada, hora_rm, codtp_atestado)
        enviar_saverecord(xml_novo, codcoligada, acao="Alteração", empresa_soc=empresa_soc, codpessoa=codpessoa, chapa=chapa, dtinicio=dtini_log, dtfinal=dtfim_log)
        return True

    print("Nenhuma divergência encontrada, registrando log e pulando.")
    inserir_log_sqlserver(
        empresa_soc,
        codcoligada,
        codpessoa,
        chapa,
        None,
        dtini_log,
        dtfim_log,
        "Afastamento Processado Anteriormente",
    )
    return False


def enviar_saverecord(xml_saverecord, codcoligada, acao, empresa_soc, codpessoa, chapa, dtinicio, dtfinal):
    import re
    from config import RM_AUTH
    from db_logger import inserir_log_sqlserver

    headers = _auth_headers()
    headers["SOAPAction"] = '"http://www.totvs.com/IwsDataServer/SaveRecord"'

    xml_env = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tot="http://www.totvs.com/">
    <soapenv:Header/>
    <soapenv:Body>
        <tot:SaveRecord>
            <tot:DataServerName>SmtAtestadoData</tot:DataServerName>
            <tot:XML><![CDATA[{xml_saverecord}]]></tot:XML>
            <tot:Contexto>CODCOLIGADA={codcoligada};CODUSUARIO={RM_USER};CODSISTEMA=S</tot:Contexto>
        </tot:SaveRecord>
    </soapenv:Body>
    </soapenv:Envelope>"""

    resp = requests.post(RM_ENDPOINT, data=xml_env.encode("utf-8"), headers=headers, auth=RM_AUTH)
    print("Resposta:\n", resp.text)

    try:
        root = ET.fromstring(resp.content)
        result_elem = root.find(".//{http://www.totvs.com/}SaveRecordResult")
        result_text = result_elem.text.strip() if result_elem is not None else resp.text.strip()
    except Exception:
        result_text = resp.text.strip()

    pk_pattern = re.compile(r"^\d+;\d+;\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2};\d+$")
    status_log = "SUCESSO" if pk_pattern.match(result_text) else result_text

    inserir_log_sqlserver(empresa_soc, codcoligada, codpessoa, chapa, acao, dtinicio, dtfinal, status_log)

    return bool(pk_pattern.match(result_text))
