from app.main import app

openapi = app.openapi()
for path, methods in list(openapi.get('paths', {}).items()):
    for method, details in methods.items():
        responses = details.get('responses', {})
        for code, resp in responses.items():
            if code in ['400', '401', '403', '404', '409', '422', '500']:
                content = resp.get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    if '$ref' in schema:
                        print(method.upper(), path, code, schema['$ref'])