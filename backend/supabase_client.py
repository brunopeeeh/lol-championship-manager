"""Minimal PostgREST adapter. Public reads never use an administrative credential."""
import logging
import httpx
from .settings import supabase_config
log=logging.getLogger('lcm.supabase')

class DatabaseUnavailable(RuntimeError):
    pass

def request(method,resource,*,params=None,json=None,token=None,admin=False,headers=None):
    try:
        url,key=supabase_config(admin)
    except RuntimeError as exc:
        raise DatabaseUnavailable('Supabase não configurado. Preencha URL e chave publicável ou selecione SQLite.') from exc
    h={'apikey':key,'Accept':'application/json',**(headers or {})}
    if token:
        h['Authorization']='Bearer '+token
    elif admin:
        h['Authorization']='Bearer '+key
    try:
        with httpx.Client(timeout=45) as client:
            r=client.request(method,url+resource,params=params,json=json,headers=h)
        r.raise_for_status()
        return r
    except httpx.HTTPError as exc:
        log.error('supabase_request_failed',extra={'resource':resource,'status':getattr(getattr(exc,'response',None),'status_code',None)})
        raise DatabaseUnavailable('Falha ao consultar o Supabase. Tente novamente.') from exc

def select(table,params=None,*,token=None):
    return request('GET','/rest/v1/'+table,params=params,token=token).json()
