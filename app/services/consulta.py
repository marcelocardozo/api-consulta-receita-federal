import re

from app.services.parser import parse_comprovante, parse_qsa, parse_erro
from app.services.browser import BrowserManager


def formatar_cnpj(cnpj: str) -> str:
    """Formata e valida um CNPJ (apenas dígitos) retornando no formato XX.XXX.XXX/XXXX-XX."""
    numeros = re.sub(r"\D", "", cnpj)
    if len(numeros) != 14:
        raise ValueError(f"CNPJ deve ter 14 dígitos, recebido: {len(numeros)}")
    if not _validar_cnpj(numeros):
        raise ValueError("CNPJ inválido (dígito verificador incorreto)")
    return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"


def _validar_cnpj(cnpj: str) -> bool:
    """Valida dígitos verificadores do CNPJ."""
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    d1 = 11 - (soma1 % 11)
    d1 = 0 if d1 >= 10 else d1
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    d2 = 11 - (soma2 % 11)
    d2 = 0 if d2 >= 10 else d2
    return cnpj[-2:] == f"{d1}{d2}"


async def consultar_cnpj(cnpj: str, browser_manager: BrowserManager) -> dict:
    """Orquestra a consulta de um CNPJ na Receita Federal."""
    cnpj_formatado = formatar_cnpj(cnpj)
    resultado = await browser_manager.solve_and_query(cnpj_formatado)

    if resultado["tipo"] == "erro":
        erro_msg = parse_erro(resultado.get("html", "") + resultado.get("url", ""))
        return {"sucesso": False, "erro": erro_msg or "Erro desconhecido"}

    dados = parse_comprovante(resultado["html_comprovante"])

    if resultado.get("html_qsa"):
        qsa = parse_qsa(resultado["html_qsa"])
        dados["capital_social"] = qsa.get("capital_social", "")
        dados["socios"] = qsa.get("socios", [])

    dados["sucesso"] = True
    return dados
