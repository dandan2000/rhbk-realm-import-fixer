import json
import argparse
import sys
import os

def fix_protocol_mappers(entities, entity_type):
    fixes_made = 0
    for entity in entities:
        if 'protocolMappers' in entity:
            seen_keys = set()
            
            for mapper in entity['protocolMappers']:
                protocol = mapper.get('protocol')
                name = mapper.get('name')
                
                if protocol and name:
                    key = (protocol, name)
                    original_name = name
                    counter = 1
                    
                    while key in seen_keys:
                        new_name = f"{original_name}_dup{counter}"
                        mapper['name'] = new_name
                        key = (protocol, new_name)
                        counter += 1
                        fixes_made += 1
                        
                        entity_id = entity.get('clientId', entity.get('name', 'desconocido'))
                        print(f"[-] Corregido mapper en {entity_type} '{entity_id}': ")
                        print(f"    Renombrado '{original_name}' -> '{new_name}' (Protocolo: {protocol})")
                    
                    seen_keys.add(key)
                    
    return fixes_made

def remove_js_policies_and_dependencies(clients):
    fixes_made = 0
    for client in clients:
        auth_settings = client.get('authorizationSettings')
        if not auth_settings or 'policies' not in auth_settings:
            continue
            
        policies_list = auth_settings['policies']
        client_id = client.get('clientId', 'desconocido')
        
        # 1. Identificar nombres de políticas JS a borrar
        js_policy_names = {p.get('name') for p in policies_list if p.get('type') == 'js'}
        
        if not js_policy_names:
            continue
            
        # Filtramos para eliminar las políticas JS de la lista principal
        remaining_policies = [p for p in policies_list if p.get('type') != 'js']
        removed_js = len(policies_list) - len(remaining_policies)
        fixes_made += removed_js
        print(f"[-] Eliminadas {removed_js} políticas JS en Cliente '{client_id}'")
        
        # 2. Limpiar las dependencias ocultas en el bloque 'config' -> 'applyPolicies'
        final_policies = []
        for p in remaining_policies:
            keep_policy = True
            config = p.get('config', {})
            
            # Verificamos si este permiso aplica otras políticas
            if 'applyPolicies' in config:
                apply_val = config['applyPolicies']
                parsed_policies = []
                is_string = False
                
                # Keycloak a veces lo guarda como string JSON: "[\"Default Policy\"]"
                if isinstance(apply_val, str):
                    try:
                        parsed_policies = json.loads(apply_val)
                        is_string = True
                    except json.JSONDecodeError:
                        parsed_policies = []
                # O a veces como lista normal: ["Default Policy"]
                elif isinstance(apply_val, list):
                    parsed_policies = apply_val
                    
                if parsed_policies:
                    original_len = len(parsed_policies)
                    # Filtramos los nombres de las políticas JS que ya borramos
                    filtered = [dep for dep in parsed_policies if dep not in js_policy_names]
                    
                    # Si dependía de la política JS y ahora queda vacío, este permiso ya no sirve
                    if original_len > 0 and len(filtered) == 0:
                        print(f"    -> Eliminado permiso huérfano '{p.get('name')}' (dependía de la política JS borrada)")
                        keep_policy = False
                        fixes_made += 1
                    else:
                        # Si aún tiene dependencias válidas, lo volvemos a guardar con su formato original
                        if is_string:
                            config['applyPolicies'] = json.dumps(filtered)
                        else:
                            config['applyPolicies'] = filtered
            
            if keep_policy:
                final_policies.append(p)
                
        # Guardamos la lista limpia en el cliente
        auth_settings['policies'] = final_policies
        
    return fixes_made

def process_realm(input_file, output_file):
    print(f"Analizando el archivo: {input_file}...\n")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            realm_data = json.load(f)
    except FileNotFoundError:
        print(f"[!] Error: No se encontró el archivo '{input_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[!] Error: El archivo '{input_file}' no es un JSON válido.")
        sys.exit(1)

    total_fixes = 0

    if 'clients' in realm_data:
        total_fixes += fix_protocol_mappers(realm_data['clients'], "Cliente")
        total_fixes += remove_js_policies_and_dependencies(realm_data['clients'])
    
    if 'clientScopes' in realm_data:
        total_fixes += fix_protocol_mappers(realm_data['clientScopes'], "Client Scope")

    if total_fixes > 0:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(realm_data, f, indent=2)
            print(f"\n[+] ¡Éxito! Se realizaron {total_fixes} correcciones en total.")
            print(f"[+] El Realm corregido se guardó en: {output_file}")
        except Exception as e:
            print(f"[!] Error al escribir el archivo {output_file}: {e}")
    else:
        print("[!] No se encontraron problemas. El archivo no requirió modificaciones.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corrige errores de exportación de Keycloak (mappers, scripts JS y dependencias en applyPolicies).")
    parser.add_argument("input", help="Ruta al archivo JSON original del Realm de Keycloak")
    parser.add_argument("-o", "--output", help="Ruta para el archivo JSON de salida (Opcional)")
    
    args = parser.parse_args()
    
    if args.output:
        final_output = args.output
    else:
        base_name, extension = os.path.splitext(args.input)
        final_output = f"{base_name}-FIXED{extension}"
        
    process_realm(args.input, final_output)
