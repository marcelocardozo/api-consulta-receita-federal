import html
import re
import unicodedata

from bs4 import BeautifulSoup


def _normalizar_chave(s: str) -> str:
    """Remove acentos e converte para uppercase para matching confiável."""
    s = re.sub(r"<[^>]+>", "", s)
    s = " ".join(s.split()).strip()
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.category(c).startswith("M")).upper()


def _limpar(texto: str) -> str:
    """Remove tags HTML e normaliza espaços."""
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = " ".join(texto.split())
    return texto.strip()


def parse_comprovante(html_content: str) -> dict[str, str | list[str]]:
    """Extrai dados estruturados do comprovante de inscrição CNPJ.

    A página da Receita Federal usa font-size 6pt para labels e 8pt bold
    para valores — regex é usado aqui por ser mais preciso que seletores CSS
    para esse layout específico.
    """
    pairs = re.findall(
        r'font-size:\s*6pt[^>]*>\s*(.*?)\s*</font>.*?font-size:\s*8pt[^>]*>\s*<b>(.*?)</b>',
        html_content,
        re.DOTALL,
    )

    campos: dict[str, str] = {}
    for label, value in pairs:
        key = _normalizar_chave(label)
        value = _limpar(value)
        if key:
            campos[key] = value

    if not campos:
        return {"erro": "Não foi possível extrair os dados do comprovante"}

    # CNAEs secundários
    cnaes_sec: list[str] = []
    cnae_pattern = re.compile(r"^\d{2}\.\d{2}-\d-\d{2}")
    all_bolds = re.findall(r'font-size:\s*8pt[^>]*>\s*<b>(.*?)</b>', html_content, re.DOTALL)
    cnae_principal = campos.get("CODIGO E DESCRICAO DA ATIVIDADE ECONOMICA PRINCIPAL", "")
    for b in all_bolds:
        b_clean = _limpar(b)
        if cnae_pattern.match(b_clean) and b_clean != cnae_principal:
            cnaes_sec.append(b_clean)

    return {
        "cnpj": campos.get("NUMERO DE INSCRICAO", ""),
        "tipo": "MATRIZ" if re.search(r"<b>\s*MATRIZ\s*</b>", html_content, re.IGNORECASE) else "FILIAL",
        "data_abertura": campos.get("DATA DE ABERTURA", ""),
        "razao_social": campos.get("NOME EMPRESARIAL", ""),
        "nome_fantasia": campos.get("TITULO DO ESTABELECIMENTO (NOME DE FANTASIA)", ""),
        "porte": campos.get("PORTE", ""),
        "cnae_principal": cnae_principal,
        "cnaes_secundarios": cnaes_sec,
        "natureza_juridica": campos.get("CODIGO E DESCRICAO DA NATUREZA JURIDICA", ""),
        "logradouro": campos.get("LOGRADOURO", ""),
        "numero": campos.get("NUMERO", ""),
        "complemento": campos.get("COMPLEMENTO", ""),
        "cep": campos.get("CEP", ""),
        "bairro": campos.get("BAIRRO/DISTRITO", ""),
        "municipio": campos.get("MUNICIPIO", ""),
        "uf": campos.get("UF", ""),
        "email": campos.get("ENDERECO ELETRONICO", ""),
        "telefone": campos.get("TELEFONE", ""),
        "efr": campos.get("ENTE FEDERATIVO RESPONSAVEL (EFR)", ""),
        "situacao_cadastral": campos.get("SITUACAO CADASTRAL", ""),
        "data_situacao_cadastral": campos.get("DATA DA SITUACAO CADASTRAL", ""),
        "motivo_situacao_cadastral": campos.get("MOTIVO DE SITUACAO CADASTRAL", ""),
        "situacao_especial": campos.get("SITUACAO ESPECIAL", ""),
        "data_situacao_especial": campos.get("DATA DA SITUACAO ESPECIAL", ""),
    }


def parse_qsa(html_content: str) -> dict[str, str | list[dict[str, str]]]:
    """Extrai dados do QSA (Quadro de Sócios e Administradores)."""
    soup = BeautifulSoup(html_content, "html.parser")

    info: dict[str, str | list[dict[str, str]]] = {}
    rows = soup.select(".alert-info .row")
    for row in rows:
        label_el = row.select_one("b")
        divs = row.select("div")
        if label_el and len(divs) >= 2:
            label = label_el.get_text(strip=True).rstrip(":")
            value = divs[-1].get_text(strip=True)
            if label == "CNPJ":
                info["cnpj"] = value
            elif label == "NOME EMPRESARIAL":
                info["razao_social"] = value
            elif label == "CAPITAL SOCIAL":
                info["capital_social"] = value

    socios: list[dict[str, str]] = []
    blocos = soup.select(".alert-warning")
    for bloco in blocos:
        socio: dict[str, str] = {}
        bloco_rows = bloco.select(".row")
        for row in bloco_rows:
            label_el = row.select_one("b")
            divs = row.select("div")
            if label_el and len(divs) >= 2:
                label = label_el.get_text(strip=True).rstrip(":")
                value = divs[1].get_text(strip=True)
                if "Nome" in label:
                    socio["nome"] = value
                elif "Qualifica" in label:
                    socio["qualificacao"] = value
        if socio:
            socios.append(socio)

    info["socios"] = socios
    return info


def parse_erro(html_content: str) -> str | None:
    """Extrai mensagem de erro da página de resposta."""
    match = re.search(r"erro='(.*?)'", html_content)
    if match:
        return html.unescape(match.group(1))

    soup = BeautifulSoup(html_content, "html.parser")
    alert = soup.select_one(".alert-danger, .alert-warning")
    if alert:
        return alert.get_text(strip=True)

    return None
