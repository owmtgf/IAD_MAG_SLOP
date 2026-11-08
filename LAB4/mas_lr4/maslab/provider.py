"""Minimal adapter for endpoints implementing the contract in docs/PROVIDER.md."""
import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

class ProviderError(Exception):
    pass

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,response,code,message,headers,new_url):
        # A redirect can change POST to GET, downgrade HTTPS, or forward the key
        # to another host. The configured endpoint must handle the exact POST.
        return None

class HTTPProvider:
    def __init__(self,config):
        self.config = config
        base = os.environ.get('MAS_LLM_BASE_URL','').rstrip('/')
        parsed = urllib.parse.urlparse(base)
        if not base or parsed.scheme not in ('https','http') or not parsed.hostname:
            raise ProviderError('Set MAS_LLM_BASE_URL to an API base URL ending in /v1')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ProviderError('Credentials and query strings are forbidden in base URL')
        # Local experiment endpoint on the user's LAN (shared by all roles).
        if parsed.scheme == 'http' and parsed.hostname not in ('localhost','127.0.0.1','::1','192.168.3.42'):
            raise ProviderError('Remote API requires HTTPS')
        self.url = base+'/chat/completions'
        self.key = os.environ.get('MAS_LLM_API_KEY','')
        if config['model'] in ('SET_MODEL',''):
            raise ProviderError('Set model in config.json before calling the API')
        self.opener = urllib.request.build_opener(_NoRedirectHandler())

    def complete(self,messages,max_output_tokens,seed):
        body = {'model':self.config['model'],'messages':messages,
                'max_tokens':max_output_tokens,'temperature':self.config['temperature']}
        if self.config.get('send_seed',False):
            body['seed'] = seed
        started = time.monotonic()
        try:
            request = urllib.request.Request(self.url,data=json.dumps(body).encode(),
                headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+self.key} if self.key else {})})
            with self.opener.open(request,timeout=self.config['request_timeout_seconds']) as response:
                raw = response.read(2000001)
            if len(raw)>2000000:
                raise ProviderError('Provider response exceeds 2 MB')
            obj = json.loads(raw)
            if type(obj) is not dict:
                raise ProviderError('Provider response must be a JSON object')
            # Preserve usage even when the completed response has a malformed
            # assistant envelope. The engine charges it before rejecting content.
            content = None
            choices = obj.get('choices')
            if type(choices) is list and choices and type(choices[0]) is dict:
                message = choices[0].get('message')
                if type(message) is dict and type(message.get('content')) is str:
                    content = message['content']
            return {'content':content,'usage':obj.get('usage'),
                    'seconds':time.monotonic()-started,
                    'model':obj.get('model'),'id':obj.get('id')}
        except urllib.error.HTTPError as exc:
            # Do not echo a provider body or credentials into logs.
            raise ProviderError('HTTP '+str(exc.code)) from None
        except (urllib.error.URLError,http.client.HTTPException,TimeoutError,OSError,
                ValueError,KeyError,IndexError,TypeError) as exc:
            raise ProviderError('Provider transport/schema error: '+type(exc).__name__) from None

def parse_usage(usage):
    if type(usage) is not dict:
        raise ValueError('usage is absent')
    values = [usage.get(k) for k in ('prompt_tokens','completion_tokens','total_tokens')]
    if any(type(x) is not int or x<0 for x in values):
        raise ValueError('usage must contain three nonnegative integer counts')
    if values[0]+values[1] != values[2] or values[2] == 0:
        raise ValueError('inconsistent usage')
    return tuple(values)
