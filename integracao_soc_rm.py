import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pandas as pd
import requests

from config import (
    SOC_ENDPOINT,
    SOC_USUARIO,
    SOC_SENHA,
    SOC_CODIGO_EMPRESA_PRINCIPAL,
    SOC_CODIGO_RESPONSAVEL,
    EMPRESA_CODCOLIGADA,
    MAPA_CODTP_ATESTADO,
    data_inicio,
)
from totvs_utils import buscar_codpessoa_por_chapa, buscar_seqatestado, gerar_xml_saverecord, enviar_saverecord, atualizar_se_existir_diferenca
from ws_security import gerar_ws_security


def executar_integracao():
    for cod_empresa_soc, codcoligada_rm in EMPRESA_CODCOLIGADA.items():
        print(f"\n==== Iniciando consulta para empresa SOC {cod_empresa_soc} (RM coligada {codcoligada_rm}) ====")

        ws_security = gerar_ws_security(SOC_USUARIO, SOC_SENHA)
        hoje = datetime.now().strftime("%d/%m/%Y")
        data_obj = datetime.strptime(hoje, "%d/%m/%Y")
        data_menos_15 = data_obj - timedelta(days=2)
        data_menos_15.strftime("%d/%m/%Y")

        soap_body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://services.soc.age.com/">
                <soapenv:Header>{ws_security}</soapenv:Header>
                <soapenv:Body>
                    <ser:consultarMovimentacoesLicencasMedicas>
                        <consultaAfastamentoLote>
                            <codigoEmpresaFuncionario>{cod_empresa_soc}</codigoEmpresaFuncionario>
                            <dataFicha>{data_inicio}</dataFicha>
                            <identificacaoVo>
                                <chaveAcesso>{SOC_SENHA}</chaveAcesso>
                                <codigoEmpresaPrincipal>{SOC_CODIGO_EMPRESA_PRINCIPAL}</codigoEmpresaPrincipal>
                                <codigoResponsavel>{SOC_CODIGO_RESPONSAVEL}</codigoResponsavel>
                                <codigoUsuario>{SOC_USUARIO}</codigoUsuario>
                            </identificacaoVo>
                            <dataInicioAlteracao>{data_inicio}</dataInicioAlteracao>
                            <dataFimAlteracao>{hoje}</dataFimAlteracao>
                            <tipoAlteracao>TODOS</tipoAlteracao>
                        </consultaAfastamentoLote>
                    </ser:consultarMovimentacoesLicencasMedicas>
                </soapenv:Body>
            </soapenv:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "",
        }

        response = requests.post(SOC_ENDPOINT, data=soap_body.encode("utf-8"), headers=headers, timeout=60)
        ns = {"soap": "http://schemas.xmlsoap.org/soap/envelope/", "ns2": "http://services.soc.age.com/"}
        root = ET.fromstring(response.content)

        registros = []
        for afast in root.findall(".//ns2:consultarMovimentacoesLicencasMedicasResponse/Afastamento", ns):
            registro = {}
            for tag in afast:
                tag_name = tag.tag.split("}")[-1]
                if tag_name == "infoAfastamento":
                    for info in tag:
                        info_name = info.tag.split("}")[-1]
                        registro[info_name] = info.text.strip() if info.text else ""
                else:
                    registro[tag_name] = tag.text.strip() if tag.text else ""
            registro["CODCOLIGADA"] = codcoligada_rm
            registros.append(registro)

        df = pd.DataFrame(registros)
        print(f"Afastamentos retornados para empresa {cod_empresa_soc}: {len(df)}")

        for _, row in df.iterrows():
            chapa = row["matriculaFuncionario"]
            codcoligada = row["CODCOLIGADA"]
            print(f"\nProcessando matrícula {chapa} (coligada {codcoligada})...")

            codpessoa = buscar_codpessoa_por_chapa(chapa, codcoligada)
            print(f"CODPESSOA encontrado: {codpessoa}")
            if not codpessoa:
                print(f"Funcionário {chapa} não encontrado na coligada {codcoligada}")
                continue

            dtini = row["dataInicioAfastamento"]
            seq, codtp_atestado, dados_atuais = buscar_seqatestado(codpessoa, dtini, codcoligada)
            print(f"SEQ retornado: {seq}")
            if seq:
                print(f"Afastamento já existe! SEQATESTADO: {seq} - UPDATE")
                atualizado = atualizar_se_existir_diferenca(row, codpessoa, seq, codtp_atestado, dados_atuais, codcoligada, cod_empresa_soc, chapa)
                if atualizado:
                    continue
            else:
                seq = -1
                print("Afastamento não existe. Será incluído (insert).")
                xml_save = gerar_xml_saverecord(row, codpessoa, seq, codcoligada)
                dtfim = row.get("dataFimAfastamento", "").strip()
                dtfim_fmt = datetime.strptime(dtfim, "%d/%m/%Y").strftime("%Y-%m-%dT00:00:00") if dtfim else dtfim
                enviar_saverecord(xml_save, codcoligada, acao="Inclusão", empresa_soc=cod_empresa_soc, codpessoa=codpessoa, chapa=chapa, dtinicio=dtini, dtfinal=dtfim_fmt)
