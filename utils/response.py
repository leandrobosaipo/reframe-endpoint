"""
Helper para respostas JSON padronizadas.
"""
from flask import jsonify
from config import Config


def success_response(data=None, message="Success", status_code=200):
    """
    Retorna resposta JSON padronizada de sucesso.
    
    Args:
        data: Dados a serem retornados
        message: Mensagem de sucesso
        status_code: Código HTTP (padrão: 200)
    
    Returns:
        tuple: (jsonify response, status_code)
    """
    response = {
        "status": "success",
        "message": message,
        "data": data,
        "build": Config.get_build_info()
    }
    return jsonify(response), status_code


def error_response(message="Error", status_code=400, error_code=None):
    """
    Retorna resposta JSON padronizada de erro.
    
    Args:
        message: Mensagem de erro
        status_code: Código HTTP (padrão: 400)
        error_code: Código de erro opcional
    
    Returns:
        tuple: (jsonify response, status_code)
    """
    response = {
        "status": "error",
        "message": message,
        "build": Config.get_build_info()
    }
    if error_code:
        response["error_code"] = error_code
    return jsonify(response), status_code


def queued_response(data=None, message="Queued", job_id=None):
    """
    Retorna resposta JSON padronizada para job enfileirado.
    
    Args:
        data: Dados adicionais
        message: Mensagem
        job_id: ID do job
    
    Returns:
        tuple: (jsonify response, 202)
    """
    response = {
        "status": "queued",
        "message": message,
        "build": Config.get_build_info()
    }
    if job_id:
        response["job_id"] = job_id
    if data:
        response["data"] = data
    return jsonify(response), 202

