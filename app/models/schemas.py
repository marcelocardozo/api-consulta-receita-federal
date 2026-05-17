from pydantic import BaseModel


class QSAPartner(BaseModel):
    nome: str = ""
    qualificacao: str = ""


class CNPJResponse(BaseModel):
    sucesso: bool = True
    cnpj: str = ""
    tipo: str = ""
    data_abertura: str = ""
    razao_social: str = ""
    nome_fantasia: str = ""
    porte: str = ""
    cnae_principal: str = ""
    cnaes_secundarios: list[str] = []
    natureza_juridica: str = ""
    logradouro: str = ""
    numero: str = ""
    complemento: str = ""
    cep: str = ""
    bairro: str = ""
    municipio: str = ""
    uf: str = ""
    email: str = ""
    telefone: str = ""
    efr: str = ""
    situacao_cadastral: str = ""
    data_situacao_cadastral: str = ""
    motivo_situacao_cadastral: str = ""
    situacao_especial: str = ""
    data_situacao_especial: str = ""
    capital_social: str = ""
    socios: list[QSAPartner] = []
    tempo_segundos: float = 0.0


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    gemini_keys: int
    ips_ativos: int
